from typing import List, Dict, Tuple
from autocoder.common.types import Mode, CodeGenerateResult
from autocoder.common import AutoCoderArgs
import byzerllm
from autocoder.common import sys_prompt
from autocoder.privacy.model_filter import ModelPathFilter
import json
from concurrent.futures import ThreadPoolExecutor
from autocoder.common.utils_code_auto_generate import chat_with_continue,stream_chat_with_continue,ChatWithContinueResult
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.stream_out_type import CodeGenerateStreamOutType
from autocoder.common.auto_coder_lang import get_message_with_format
from autocoder.common.printer import Printer
from autocoder.rag.token_counter import count_tokens
from autocoder.utils import llms as llm_utils
from autocoder.common import SourceCodeList
from autocoder.memory.active_context_manager import ActiveContextManager
from autocoder.common.rulefiles.autocoderrules_utils import get_rules
from loguru import logger
from autocoder.run_context import get_run_context,RunMode



class CodeAutoGenerateEditBlock:
    def __init__(
        self,
        llm: byzerllm.ByzerLLM,
        args: AutoCoderArgs,
        action=None,
        fence_0: str = "```",
        fence_1: str = "```",
    ) -> None:
        self.llm = llm
        self.args = args
        self.action = action
        self.fence_0 = fence_0
        self.fence_1 = fence_1
        self.generate_times_same_model = args.generate_times_same_model
        if not self.llm:
            raise ValueError(
                "Please provide a valid model instance to use for code generation."
            )
        self.llms = self.llm.get_sub_client("code_model") or [self.llm]
        if not isinstance(self.llms, list):
            self.llms = [self.llms]
    

    @byzerllm.prompt()
    def single_round_instruction(self, instruction: str, 
                                 content: str, 
                                 context: str = "",
                                 package_context: str = ""
                                 ) -> str:
        """
        如果你需要生成代码，对于每个需要更改的文件,你需要按 *SEARCH/REPLACE block* 的格式进行生成。

        # *SEARCH/REPLACE block* Rules:

        Every *SEARCH/REPLACE block* must use this format:
        1. The opening fence and code language, eg: {{ fence_0 }}python
        2. The file path alone on a line, starting with "##File:" and verbatim. No bold asterisks, no quotes around it, no escaping of characters, etc.
        3. The start of search block: <<<<<<< SEARCH
        4. A contiguous chunk of lines to search for in the existing source code
        5. The dividing line: =======
        6. The lines to replace into the source code
        7. The end of the replace block: >>>>>>> REPLACE
        8. The closing fence: {{ fence_1 }}

        Every *SEARCH* section must *EXACTLY MATCH* the existing source code, character for character, including all comments, docstrings, etc.

        *SEARCH/REPLACE* blocks will replace *all* matching occurrences.
        Include enough lines to make the SEARCH blocks unique.

        Include *ALL* the code being searched and replaced!

        To move code within a file, use 2 *SEARCH/REPLACE* blocks: 1 to delete it from its current location, 1 to insert it in the new location.

        If you want to put code in a new file, use a *SEARCH/REPLACE block* with:
        - A new file path, including dir name if needed
        - An empty `SEARCH` section
        - The new file's contents in the `REPLACE` section

        ONLY EVER RETURN CODE IN A *SEARCH/REPLACE BLOCK*!

        下面我们来看一个例子：

        当前项目目录结构：
        1. 项目根目录： /tmp/projects/mathweb
        2. 项目子目录/文件列表(类似tree 命令输出)
        flask/
            app.py
            templates/
                index.html
            static/
                style.css

        用户需求： Change get_factorial() to use math.factorial

        回答： To make this change we need to modify `/tmp/projects/mathweb/flask/app.py` to:

        1. Import the math package.
        2. Remove the existing factorial() function.
        3. Update get_factorial() to call math.factorial instead.

        Here are the *SEARCH/REPLACE* blocks:

        {{ fence_0 }}python
        ##File: /tmp/projects/mathweb/flask/app.py
        <<<<<<< SEARCH
        from flask import Flask
        =======
        import math
        from flask import Flask
        >>>>>>> REPLACE
        {{ fence_1 }}

        {{ fence_0 }}python
        ##File: /tmp/projects/mathweb/flask/app.py
        <<<<<<< SEARCH
        def factorial(n):
            "compute factorial"

            if n == 0:
                return 1
            else:
                return n * factorial(n-1)

        =======
        >>>>>>> REPLACE
        {{ fence_1 }}

        {{ fence_0 }}python
        ##File: /tmp/projects/mathweb/flask/app.py
        <<<<<<< SEARCH
            return str(factorial(n))
        =======
            return str(math.factorial(n))
        >>>>>>> REPLACE
        {{ fence_1 }}

        用户需求： Refactor hello() into its own file.

        回答：To make this change we need to modify `main.py` and make a new file `hello.py`:

        1. Make a new hello.py file with hello() in it.
        2. Remove hello() from main.py and replace it with an import.

        Here are the *SEARCH/REPLACE* blocks:

        {{ fence_0 }}python
        ##File: /tmp/projects/mathweb/hello.py
        <<<<<<< SEARCH
        =======
        def hello():
            "print a greeting"

            print("hello")
        >>>>>>> REPLACE
        {{ fence_1 }}

        {{ fence_0 }}python
        ##File: /tmp/projects/mathweb/main.py
        <<<<<<< SEARCH
        def hello():
            "print a greeting"

            print("hello")
        =======
        from hello import hello
        >>>>>>> REPLACE
        {{ fence_1 }}

        现在让我们开始一个新的任务:

        {%- if structure %}
        {{ structure }}
        {%- endif %}

        {%- if content %}
        ====
        下面是一些文件路径以及每个文件对应的源码：
        <files>
        {{ content }}
        </files>
        {%- endif %}
                
        {%- if package_context %}
        ====
        下面是上面文件的一些信息（包括最近的变更情况）：
        <package_context>
        {{ package_context }}
        </package_context>
        {%- endif %}

        {%- if context %}
        <extra_context>
        {{ context }}
        </extra_context>
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
        
        <user_instruction>
        {{ instruction }}
        </user_instruction>

        """
        if not self.args.include_project_structure:
            return {
                "structure": "",
                "fence_0": self.fence_0,
                "fence_1": self.fence_1,
            }  

        extra_docs = get_rules()          

        return {
            "structure": (
                self.action.pp.get_tree_like_directory_structure()
                if self.action
                else ""
            ),
            "fence_0": self.fence_0,
            "fence_1": self.fence_1,
            "extra_docs": extra_docs,
        }

    def single_round_run(
        self, query: str, source_code_list: SourceCodeList        
    ) -> CodeGenerateResult:
        
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
        
        llm_config = {"human_as_model": self.args.human_as_model}

        source_content = source_code_list.to_str()

        active_context_manager = ActiveContextManager(self.llm, self.args.source_dir)
       
        # 获取包上下文信息
        package_context = ""
        
        if self.args.enable_active_context and self.args.enable_active_context_in_generate:
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

        init_prompt = self.single_round_instruction.prompt(
            instruction=query, content=source_content, context=self.args.context, 
            package_context=package_context
        )        

        with open(self.args.target_file, "w",encoding="utf-8") as file:
            file.write(init_prompt)

        conversations = []

        if self.args.system_prompt and self.args.system_prompt.strip() == "claude":
            conversations.append(
                {"role": "system", "content": sys_prompt.claude_sys_prompt.prompt()})
        elif self.args.system_prompt:
            conversations.append(
                {"role": "system", "content": self.args.system_prompt})

        conversations.append({"role": "user", "content": init_prompt})        

        conversations_list = []
        results = []
        input_tokens_count = 0
        generated_tokens_count = 0

        input_tokens_cost = 0
        generated_tokens_cost = 0

        model_names = []

        printer = Printer()
        estimated_input_tokens = count_tokens(
            json.dumps(conversations, ensure_ascii=False))
        printer.print_in_terminal("estimated_input_tokens_in_generate",
                                  style="yellow",
                                  estimated_input_tokens_in_generate=estimated_input_tokens,
                                  generate_mode="editblock"
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
                        if count==0:
                            logger.info(f"code generation with model(Stream): {model_name}")
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
                            logger.info(f"code generation with model(Non-stream): {model_name}")
                            futures.append(executor.submit(
                                chat_with_continue, 
                                llm=llm, 
                                conversations=conversations, 
                                llm_config=llm_config,
                                args=self.args
                            ))
                        count += 1
                
                temp_results = [future.result() for future in futures]
                
                for result,model_name in zip(temp_results,model_names):
                    results.append(result.content)
                    input_tokens_count += result.input_tokens_count
                    generated_tokens_count += result.generated_tokens_count
                    model_info = llm_utils.get_model_info(model_name,self.args.product_mode)                    
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
                conversations_list.append(
                    conversations + [{"role": "assistant", "content": single_result.content}])

        statistics = {
            "input_tokens_count": input_tokens_count,
            "generated_tokens_count": generated_tokens_count,
            "input_tokens_cost": input_tokens_cost,
            "generated_tokens_cost": generated_tokens_cost
        }

        return CodeGenerateResult(contents=results, conversations=conversations_list, metadata=statistics)

    
