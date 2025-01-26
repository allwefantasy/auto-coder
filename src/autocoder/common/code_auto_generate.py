from typing import List, Dict, Tuple
from autocoder.common.types import Mode
from autocoder.common import AutoCoderArgs
import byzerllm
from autocoder.utils.queue_communicate import queue_communicate, CommunicateEvent, CommunicateEventType
from autocoder.common import sys_prompt
from concurrent.futures import ThreadPoolExecutor
from autocoder.common.types import CodeGenerateResult
from autocoder.common.utils_code_auto_generate import chat_with_continue


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
    def multi_round_instruction(
        self, instruction: str, content: str, context: str = ""
    ) -> str:
        """
        {%- if structure %}
        {{ structure }}
        {%- endif %}

        {%- if content %}
        下面是一些文件路径以及每个文件对应的源码：
        <files>
        {{ content }}
        </files>
        {%- endif %}

        {%- if context %}
        <extra_context>
        {{ context }}
        </extra_context>
        {%- endif %}

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
        每次生成一个文件的代码，然后询问我是否继续，当我回复继续，继续生成下一个文件的代码。当没有后续任务时，请回复 "__完成__" 或者 "__EOF__"。
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

    @byzerllm.prompt(llm=lambda self: self.llm)
    def single_round_instruction(
        self, instruction: str, content: str, context: str = ""
    ) -> str:
        """
        {%- if structure %}
        {{ structure }}
        {%- endif %}

        {%- if content %}
        下面是一些文件路径以及每个文件对应的源码：

        {{ content }}
        {%- endif %}

        {%- if context %}
        {{ context }}
        {%- endif %}

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
        self, query: str, source_content: str
    ) -> Tuple[List[str], Dict[str, str]]:
        llm_config = {"human_as_model": self.args.human_as_model}

        if self.args.request_id and not self.args.skip_events:
            queue_communicate.send_event_no_wait(
                request_id=self.args.request_id,
                event=CommunicateEvent(
                    event_type=CommunicateEventType.CODE_GENERATE_START.value,
                    data=query,
                ),
            )

        if self.args.template == "common":
            init_prompt = self.single_round_instruction.prompt(
                instruction=query, content=source_content, context=self.args.context
            )
        elif self.args.template == "auto_implement":
            init_prompt = self.auto_implement_function.prompt(
                instruction=query, content=source_content
            )

        with open(self.args.target_file, "w") as file:
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
        if not self.args.human_as_model:
            with ThreadPoolExecutor(max_workers=len(self.llms) * self.generate_times_same_model) as executor:
                futures = []
                for llm in self.llms:
                    for _ in range(self.generate_times_same_model):
                        futures.append(executor.submit(
                            chat_with_continue, llm=llm, conversations=conversations, llm_config=llm_config))
                temp_results = [future.result() for future in futures]
                for result in temp_results:
                    results.append(result.content)
                    input_tokens_count += result.input_tokens_count
                    generated_tokens_count += result.generated_tokens_count
            
            for result in results:
                conversations_list.append(
                    conversations + [{"role": "assistant", "content": result}])
        else:            
            for _ in range(self.args.human_model_num):
                single_result = chat_with_continue(llm=self.llms[0], conversations=conversations, llm_config=llm_config)                
                results.append(single_result.content)
                input_tokens_count += single_result.input_tokens_count
                generated_tokens_count += single_result.generated_tokens_count
                conversations_list.append(conversations + [{"role": "assistant", "content": single_result.content}])
        
        statistics = {
            "input_tokens_count": input_tokens_count,
            "generated_tokens_count": generated_tokens_count
        }        
    
        if self.args.request_id and not self.args.skip_events:
            queue_communicate.send_event_no_wait(
                request_id=self.args.request_id,
                event=CommunicateEvent(
                    event_type=CommunicateEventType.CODE_GENERATE_END.value,
                    data=json.dumps(statistics, ensure_ascii=False),
                ),
            )

        return CodeGenerateResult(contents=results, conversations=conversations_list, metadata=statistics)

    def multi_round_run(
        self, query: str, source_content: str, max_steps: int = 10
    ) -> Tuple[List[str], List[Dict[str, str]]]:
        llm_config = {"human_as_model": self.args.human_as_model}
        result = []

        if self.args.template == "common":
            init_prompt = self.multi_round_instruction.prompt(
                instruction=query, content=source_content, context=self.args.context
            )
        elif self.args.template == "auto_implement":
            init_prompt = self.auto_implement_function.prompt(
                instruction=query, content=source_content
            )

        conversations = [{"role": "user", "content": init_prompt}]

        with open(self.args.target_file, "w") as file:
            file.write(init_prompt)

        t = self.llm.chat_oai(conversations=conversations, llm_config=llm_config)

        result.append(t[0].output)

        conversations.append({"role": "assistant", "content": t[0].output})

        if (
            "__完成__" in t[0].output
            or "/done" in t[0].output
            or "__EOF__" in t[0].output
        ):
            return result, conversations

        current_step = 0

        while current_step < max_steps:

            conversations.append({"role": "user", "content": "继续"})

            with open(self.args.target_file, "w") as file:
                file.write("继续")

            t = self.llm.chat_oai(conversations=conversations, llm_config=llm_config)

            result.append(t[0].output)
            conversations.append({"role": "assistant", "content": t[0].output})
            current_step += 1

            if (
                "__完成__" in t[0].output
                or "/done" in t[0].output
                or "__EOF__" in t[0].output
            ):
                return CodeGenerateResult(contents=["\n\n".join(result)], conversations=[conversations])

        return CodeGenerateResult(contents=["\n\n".join(result)], conversations=[conversations])
