from typing import List, Dict, Tuple
from autocoder.common.types import Mode
from autocoder.common import AutoCoderArgs
import byzerllm
from autocoder.utils.queue_communicate import queue_communicate, CommunicateEvent, CommunicateEventType
from autocoder.common import sys_prompt
from concurrent.futures import ThreadPoolExecutor
from autocoder.common.types import CodeGenerateResult
from autocoder.common.utils_code_auto_generate import chat_with_continue,stream_chat_with_continue,ChatWithContinueResult
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.stream_out_type import CodeGenerateStreamOutType
from autocoder.common.auto_coder_lang import get_message_with_format
import json
from autocoder.common.printer import Printer
from autocoder.rag.token_counter import count_tokens
from autocoder.utils import llms as llm_utils
from autocoder.common import SourceCodeList
from autocoder.privacy.model_filter import ModelPathFilter
from autocoder.memory.active_context_manager import ActiveContextManager
from autocoder.run_context import get_run_context,RunMode

class CodeAutoGenerate:
    def __init__(
        self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs, action=None
    ) -> None:
        self.llm = llm
        self.args = args
        self.action = action        
        self.generate_times_same_model = args.generate_times_same_model
        if not self.llm:
            raise ValueError(
                "Please provide a valid model instance to use for code generation."
            )
        self.llms = self.llm.get_sub_client("code_model") or [self.llm]
        if not isinstance(self.llms, list):
            self.llms = [self.llms]

    @byzerllm.prompt(llm=lambda self: self.llm)
    def auto_implement_function(self, instruction: str, content: str) -> str:
        """
        下面是一些文件路径以及每个文件对应的源码：

        {{ content }}

        请参考上面的内容，重新实现所有文件下方法体标记了如下内容的方法：

        ```python
        raise NotImplementedError("This function should be implemented by the model.")
        ```

        {{ instruction }}

        """
    

    @byzerllm.prompt(llm=lambda self: self.llm)
    def single_round_instruction(
        self, instruction: str, content: str, context: str = "", package_context: str = ""
    ) -> str:
        """
        {%- if structure %}
        ====
        {{ structure }}
        {%- endif %}

        {%- if content %}
        ====
        下面是一些文件路径以及每个文件对应的源码：

        {{ content }}
        {%- endif %}

        {%- if package_context %}
        ====
        下面是上面文件的一些信息（包括最近的变更情况）：
        <package_context>
        {{ package_context }}
        </package_context>
        {%- endif %}

        {%- if context %}
        ====
        {{ context }}
        {%- endif %}

        {%- if extra_docs %}
        ====

        RULES PROVIDED BY USER

        The following rules are provided by the user, and you must follow them strictly.

        {% for key, value in extra_docs.items() %}
        <user_rule>
        ##File: {{ key }}
        {{ value }}
        </user_rule>
        {% endfor %}        
        {% endif %}

        ====

        下面是用户的需求：

        {{ instruction }}

        如果你需要生成代码，你生成的代码要符合这个格式：

        ```{lang}
        ##File: {FILE_PATH}
        {CODE}
        ```

        ```{lang}
        ##File: {FILE_PATH}
        {CODE}
        ```

        其中，{lang}是代码的语言，{CODE}是代码的内容, {FILE_PATH} 是文件的路径(请尽量使用绝对路径)，他们都在代码块中，请严格按上面的格式进行内容生成。

        请确保每份代码的完整性，而不要只生成修改部分。
        """
        
        if not self.args.include_project_structure:
            return {
                "structure": "",                
            }
        
        return {
            "structure": (
                self.action.pp.get_tree_like_directory_structure()
                if self.action
                else ""
            )
        }

    def single_round_run(
        self, query: str, source_code_list: SourceCodeList
    ) -> Tuple[List[str], Dict[str, str]]:
        llm_config = {"human_as_model": self.args.human_as_model}

        # Apply model filter for code_llm  
        printer = Printer()      
        for llm in self.llms:
            model_filter = ModelPathFilter.from_model_object(llm, self.args)
            filtered_sources = []
            for source in source_code_list.sources:
                if model_filter.is_accessible(source.module_name):
                    filtered_sources.append(source)
                else:
                    printer.print_in_terminal("index_file_filtered", 
                                               style="yellow",
                                               file_path=source.module_name, 
                                               model_name=",".join(llm_utils.get_llm_names(llm)))
            
        source_code_list = SourceCodeList(filtered_sources)
        source_content = source_code_list.to_str()

        # 获取包上下文信息
        package_context = ""
        
        if self.args.enable_active_context:
            # 初始化活动上下文管理器
            active_context_manager = ActiveContextManager(self.llm, self.args.source_dir)
            # 获取活动上下文信息
            result = active_context_manager.load_active_contexts_for_files(
                [source.module_name for source in source_code_list.sources]
            )
            # 将活动上下文信息格式化为文本
            if result.contexts:
                package_context_parts = []
                for dir_path, context in result.contexts.items():
                    package_context_parts.append(f"<package_info>{context.content}</package_info>")
                
                package_context = "\n".join(package_context_parts)

        if self.args.template == "common":
            init_prompt = self.single_round_instruction.prompt(
                instruction=query, content=source_content, context=self.args.context,
                package_context=package_context
            )
        elif self.args.template == "auto_implement":
            init_prompt = self.auto_implement_function.prompt(
                instruction=query, content=source_content
            )

        with open(self.args.target_file, "w",encoding="utf-8") as file:
            file.write(init_prompt)

        conversations = []

        if self.args.system_prompt and self.args.system_prompt.strip() == "claude":
            conversations.append({"role": "system", "content": sys_prompt.claude_sys_prompt.prompt()})
        elif self.args.system_prompt:
            conversations.append({"role": "system", "content": self.args.system_prompt})
        
        conversations.append({"role": "user", "content": init_prompt})

        conversations_list = []
        results = []
        input_tokens_count = 0
        generated_tokens_count = 0
        input_tokens_cost = 0
        generated_tokens_cost = 0
        model_names = []

        printer = Printer()
        estimated_input_tokens = count_tokens(json.dumps(conversations, ensure_ascii=False))
        printer.print_in_terminal("estimated_input_tokens_in_generate", style="yellow",
                                  estimated_input_tokens_in_generate=estimated_input_tokens,
                                  generate_mode="wholefile"
                                  )

        if not self.args.human_as_model or get_run_context().mode == RunMode.WEB:
            with ThreadPoolExecutor(max_workers=len(self.llms) * self.generate_times_same_model) as executor:
                futures = []
                count = 0
                for llm in self.llms:
                    model_names_list = llm_utils.get_llm_names(llm) 
                    model_name = None
                    if model_names_list:
                        model_name = model_names_list[0]  

                    for _ in range(self.generate_times_same_model):
                        model_names.append(model_name)
                        if count == 0:
                            def job():
                                stream_generator = stream_chat_with_continue(
                                    llm=llm, 
                                    conversations=conversations, 
                                    llm_config=llm_config,
                                    args=self.args
                                )
                                full_response, last_meta = stream_out(
                                stream_generator,
                                model_name=model_name,
                                title=get_message_with_format(
                                    "code_generate_title", model_name=model_name),
                                args=self.args,
                                extra_meta={
                                    "stream_out_type": CodeGenerateStreamOutType.CODE_GENERATE.value
                                })
                                return ChatWithContinueResult(
                                    content=full_response,
                                    input_tokens_count=last_meta.input_tokens_count,
                                    generated_tokens_count=last_meta.generated_tokens_count
                                )
                            futures.append(executor.submit(job))
                        else:                                
                            futures.append(executor.submit(
                                chat_with_continue, 
                                llm=llm, 
                                conversations=conversations, 
                                llm_config=llm_config,
                                args=self.args
                            ))
                        count += 1
                temp_results = [future.result() for future in futures]
                for result in temp_results:
                    results.append(result.content)
                    input_tokens_count += result.input_tokens_count
                    generated_tokens_count += result.generated_tokens_count
                    model_info = llm_utils.get_model_info(model_name, self.args.product_mode)
                    input_cost = model_info.get("input_price", 0) if model_info else 0
                    output_cost = model_info.get("output_price", 0) if model_info else 0
                    input_tokens_cost += input_cost * result.input_tokens_count / 1000000
                    generated_tokens_cost += output_cost * result.generated_tokens_count / 1000000
            
            for result in results:
                conversations_list.append(
                    conversations + [{"role": "assistant", "content": result}])
        else:            
            for _ in range(self.args.human_model_num):
                single_result = chat_with_continue(
                    llm=self.llms[0], 
                    conversations=conversations, 
                    llm_config=llm_config,
                    args=self.args
                )                
                results.append(single_result.content)
                input_tokens_count += single_result.input_tokens_count
                generated_tokens_count += single_result.generated_tokens_count
                conversations_list.append(conversations + [{"role": "assistant", "content": single_result.content}])
        
        statistics = {
            "input_tokens_count": input_tokens_count,
            "generated_tokens_count": generated_tokens_count,
            "input_tokens_cost": input_tokens_cost,
            "generated_tokens_cost": generated_tokens_cost
        }        
    
        return CodeGenerateResult(contents=results, conversations=conversations_list, metadata=statistics)

    
