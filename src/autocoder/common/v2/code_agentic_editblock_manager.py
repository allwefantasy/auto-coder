from typing import List, Dict, Tuple, Optional, Any
import os
import time

import byzerllm

from autocoder.common.types import Mode, CodeGenerateResult, MergeCodeWithoutEffect
from autocoder.common import AutoCoderArgs,  SourceCodeList, SourceCode
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.common import sys_prompt
from autocoder.compilers.shadow_compiler import ShadowCompiler
from autocoder.privacy.model_filter import ModelPathFilter
from autocoder.common.utils_code_auto_generate import chat_with_continue, stream_chat_with_continue, ChatWithContinueResult
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.stream_out_type import LintStreamOutType, CompileStreamOutType, UnmergedBlocksStreamOutType, ContextMissingCheckStreamOutType
from autocoder.common.auto_coder_lang import get_message_with_format
from autocoder.common.printer import Printer
from autocoder.rag.token_counter import count_tokens
from autocoder.utils import llms as llm_utils
from autocoder.memory.active_context_manager import ActiveContextManager
from autocoder.common.v2.code_auto_generate_editblock import CodeAutoGenerateEditBlock
from autocoder.common.v2.code_auto_merge_editblock import CodeAutoMergeEditBlock
from autocoder.shadows.shadow_manager import ShadowManager
from autocoder.linters.shadow_linter import ShadowLinter
from autocoder.linters.models import IssueSeverity
from loguru import logger
from autocoder.common.global_cancel import global_cancel
from autocoder.linters.models import ProjectLintResult
from autocoder.common.token_cost_caculate import TokenCostCalculator
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events.event_types import Event, EventType, EventMetadata
from autocoder.events import event_content as EventContentCreator


class CodeEditBlockManager:
    """
    A class that combines code generation, linting, and merging with automatic error correction.
    It generates code, lints it, and if there are errors, regenerates the code up to 5 times
    before merging the final result.
    """

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
        self.auto_fix_lint_max_attempts = args.auto_fix_lint_max_attempts
        self.auto_fix_compile_max_attempts = args.auto_fix_compile_max_attempts
        self.printer = Printer()

        # Initialize sub-components
        self.code_generator = CodeAutoGenerateEditBlock(
            llm, args, action, fence_0, fence_1)
        self.code_merger = CodeAutoMergeEditBlock(llm, args, fence_0, fence_1)

        # Create shadow manager for linting
        self.shadow_manager = ShadowManager(
            args.source_dir, args.event_file, args.ignore_clean_shadows)
        self.shadow_linter = ShadowLinter(self.shadow_manager, verbose=False)
        self.shadow_compiler = ShadowCompiler(
            self.shadow_manager, verbose=False)

    @byzerllm.prompt()
    def fix_linter_errors(self, query: str, lint_issues: str) -> str:
        """        
        Linter 检测到的问题:
        <lint_issues>
        {{ lint_issues }}
        </lint_issues>

        用户原始需求:
        <user_query_wrapper>
        {{ query }}
        </user_query_wrapper>

        修复上述问题，请确保代码质量问题被解决，同时保持代码的原有功能。
        请严格遵守*SEARCH/REPLACE block*的格式。
        """
    @byzerllm.prompt()
    def fix_compile_errors(self, query: str, compile_errors: str) -> str:
        """
        编译错误:
        <compile_errors>
        {{ compile_errors }}
        </compile_errors>

        用户原始需求:
        <user_query_wrapper>
        {{ query }}
        </user_query_wrapper>

        修复上述问题，请确保代码质量问题被解决，同时保持代码的原有功能。
        请严格遵守*SEARCH/REPLACE block*的格式。
        """

    @byzerllm.prompt()
    def fix_missing_context(self, query: str, original_code: str, missing_files: str) -> str:
        """  
        下面是你根据格式要求输出的一份修改代码:
        <original_code>
        {{ original_code }}
        </original_code>

        我发现你尝试修改以下文件，但这些文件没有在上下文中提供，所以你无法看到它们的内容:
        <missing_files>
        {{ missing_files }}
        </missing_files>

        下面是用户原始的需求:
        <user_query_wrapper>
        {{ query }}
        </user_query_wrapper>

        我已经将这些文件添加到上下文中，请重新生成代码，确保使用SEARCH/REPLACE格式正确修改这些文件。
        对于每个文件，请确保SEARCH部分包含文件中的实际内容，而不是空的SEARCH块。
        """

    @byzerllm.prompt()
    def fix_unmerged_blocks(self, query: str, original_code: str, unmerged_blocks: str) -> str:
        """  

        下面是你根据格式要求输出的一份修改代码:
        <original_code>
        {{ original_code }}
        </original_code>

        但是我发现下面的代码块无法合并:
        <unmerged_blocks>
        {{ unmerged_blocks }}
        </unmerged_blocks>

        下面是用户原始的需求:
        <user_query_wrapper>
        {{ query }}
        </user_query_wrapper>

        请根据反馈，回顾之前的格式要求，重新生成一份修改代码，确保所有代码块都能够正确合并。
        """

    def _create_shadow_files_from_edits(self, generation_result: CodeGenerateResult) -> Dict[str, str]:
        """
        从编辑块内容中提取代码并创建临时影子文件用于检查。

        参数:
            generation_result (CodeGenerateResult): 包含SEARCH/REPLACE块的内容

        返回:
            Dict[str, str]: 映射 {影子文件路径: 内容}
        """
        result = self.code_merger.choose_best_choice(generation_result)
        merge = self.code_merger._merge_code_without_effect(result.contents[0])
        shadow_files = {}
        for file_path, new_content in merge.success_blocks:
            self.shadow_manager.update_file(file_path, new_content)
            shadow_files[self.shadow_manager.to_shadow_path(
                file_path)] = new_content

        return shadow_files

    def _format_lint_issues(self, lint_results: ProjectLintResult, levels: List[IssueSeverity] = [IssueSeverity.ERROR]) -> str:
        """
        将linter结果格式化为字符串供模型使用

        参数:
            lint_results: Linter结果对象
            level: 过滤问题的级别

        返回:
            str: 格式化的问题描述
        """
        formatted_issues = []

        for file_path, result in lint_results.file_results.items():
            file_has_issues = False
            file_issues = []

            for issue in result.issues:
                if issue.severity.value not in levels:
                    continue

                if not file_has_issues:
                    file_has_issues = True
                    file_issues.append(f"文件: {file_path}")

                severity = "错误" if issue.severity == IssueSeverity.ERROR else "警告" if issue.severity == IssueSeverity.WARNING else "信息"
                line_info = f"第{issue.position.line}行"
                if issue.position.column:
                    line_info += f", 第{issue.position.column}列"

                file_issues.append(
                    f"  - [{severity}] {line_info}: {issue.message} (规则: {issue.code})"
                )

            if file_has_issues:
                formatted_issues.extend(file_issues)
                formatted_issues.append("")  # 空行分隔不同文件

        return "\n".join(formatted_issues)

    def _count_errors(self, lint_results: ProjectLintResult, levels: List[IssueSeverity] = [IssueSeverity.ERROR]) -> int:
        """
        计算lint结果中的错误数量

        参数:
            lint_results: Linter结果对象

        返回:
            int: 错误数量
        """
        error_count = 0

        for _, result in lint_results.file_results.items():
            if IssueSeverity.ERROR in levels:
                error_count += result.error_count
            if IssueSeverity.WARNING in levels:
                error_count += result.warning_count
            if IssueSeverity.INFO in levels:
                error_count += result.info_count
            if IssueSeverity.HINT in levels:
                error_count += result.hint_count

        return error_count

    def _fix_missing_context(self, query: str, generation_result: CodeGenerateResult, source_code_list: SourceCodeList) -> CodeGenerateResult:
        """
        检查是否有空的SEARCH块但目标文件存在，如果有，将文件添加到动态上下文并重新生成代码

        参数:
            query (str): 用户查询
            generation_result (CodeGenerateResult): 生成的代码结果
            source_code_list (SourceCodeList): 源代码列表

        返回:
            CodeGenerateResult: 修复后的代码结果
        """
        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(
                content=self.printer.get_message_from_key("/context/check/start")),
            metadata={
                # Using a placeholder type, replace if ContextFixStreamOutType is defined
                "stream_out_type": ContextMissingCheckStreamOutType.CONTEXT_MISSING_CHECK.value,
                "action_file": self.args.file,
                "path": "/context/check/start"
            }
        )

        def write_end_event():
            get_event_manager(self.args.event_file).write_result(
                EventContentCreator.create_result(
                    content=self.printer.get_message_from_key("/context/check/end")),
                metadata={
                    # Using a placeholder type, replace if ContextFixStreamOutType is defined
                    "stream_out_type": ContextMissingCheckStreamOutType.CONTEXT_MISSING_CHECK.value,
                    "action_file": self.args.file,
                    "path": "/context/check/end"
                }
            )

        token_cost_calculator = TokenCostCalculator(args=self.args)

        # 获取编辑块
        codes = self.code_merger.get_edits(generation_result.contents[0])

        # 检查是否有空的SEARCH块但目标文件存在
        missing_files = []
        for file_path, head, update in codes:
            # 如果SEARCH块为空，检查文件是否存在但不在上下文中
            if not head and os.path.exists(file_path):
                # 检查文件是否已经在上下文中
                in_context = False
                if hasattr(self.args, 'urls') and self.args.urls:
                    in_context = file_path in self.args.urls
                if hasattr(self.args, 'dynamic_urls') and self.args.dynamic_urls and not in_context:
                    in_context = file_path in self.args.dynamic_urls

                # 如果文件存在但不在上下文中，添加到缺失文件列表
                if not in_context:
                    missing_files.append(file_path)
                    # 将文件添加到动态上下文中
                    if not hasattr(self.args, 'dynamic_urls'):
                        self.args.dynamic_urls = []
                    if file_path not in self.args.dynamic_urls:
                        self.args.dynamic_urls.append(file_path)

        # 如果没有缺失文件，直接返回原结果
        if not missing_files:
            write_end_event()
            return generation_result

        # 格式化缺失文件列表
        missing_files_text = "\n".join(missing_files)

        # 打印当前修复状态
        self.printer.print_in_terminal(
            "missing_context_attempt_status",
            style="yellow",
            missing_files=missing_files_text
        )

        # 更新源代码列表，包含新添加的文件
        updated_source_code_list = SourceCodeList([])
        for source in source_code_list.sources:
            updated_source_code_list.sources.append(source)

        # 添加缺失的文件到源代码列表
        for file_path in missing_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    file_content = f.read()
                source = SourceCode(module_name=file_path,
                                    source_code=file_content)
                updated_source_code_list.sources.append(source)

        # 更新action yml文件
        if missing_files and hasattr(self.args, 'dynamic_urls') and self.args.dynamic_urls:
            action_yml_file_manager = ActionYmlFileManager(
                self.args.source_dir)
            action_file_name = os.path.basename(self.args.file)
            update_yaml_success = action_yml_file_manager.update_yaml_field(
                action_file_name, "dynamic_urls", self.args.dynamic_urls)
            if not update_yaml_success:
                self.printer.print_in_terminal(
                    "yaml_save_error", style="red", yaml_file=action_file_name)

        # 准备修复提示
        fix_prompt = self.fix_missing_context.prompt(
            query=query,
            original_code=generation_result.contents[0],
            missing_files=missing_files_text
        )

        logger.info(f"fix_missing_context_prompt: {fix_prompt}")

        # 使用修复提示重新生成代码
        start_time = time.time()
        generation_result = self.code_generator.single_round_run(
            fix_prompt, updated_source_code_list)

        # 计算这次修复缺失上下文花费的token情况
        token_cost_calculator.track_token_usage_by_generate(
            llm=self.code_generator.llms[0],
            generate=generation_result,
            operation_name="code_generation_complete",
            start_time=start_time,
            end_time=time.time()
        )

        # 选择最佳结果
        generation_result = self.code_merger.choose_best_choice(
            generation_result)
        # 因为已经排完结果，就不要触发后面的排序了，所以只要保留第一个即可。
        generation_result = CodeGenerateResult(contents=[generation_result.contents[0]], conversations=[
                                               generation_result.conversations[0]], metadata=generation_result.metadata)

        write_end_event()
        return generation_result

    def _fix_unmerged_blocks(self, query: str, generation_result: CodeGenerateResult, source_code_list: SourceCodeList) -> CodeGenerateResult:
        """
        修复未合并的代码块，最多尝试指定次数

        参数:
            query (str): 用户查询
            generation_result (CodeGenerateResult): 生成的代码结果
            source_code_list (SourceCodeList): 源代码列表

        返回:
            CodeGenerateResult: 修复后的代码结果
        """
        token_cost_calculator = TokenCostCalculator(args=self.args)
        merge = self.code_merger._merge_code_without_effect(
            generation_result.contents[0])

        if not self.args.enable_auto_fix_merge or not merge.failed_blocks:
            return generation_result

        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(
                content=self.printer.get_message_from_key("/unmerged_blocks/check/start")),
            metadata={
                "stream_out_type": UnmergedBlocksStreamOutType.UNMERGED_BLOCKS.value,
                "action_file": self.args.file,
                "path": "/unmerged_blocks/check/start"
            }
        )

        def _format_blocks(merge: MergeCodeWithoutEffect) -> Tuple[str, str]:
            unmerged_formatted_text = ""
            for file_path, head, update in merge.failed_blocks:
                unmerged_formatted_text += "```lang\n"
                unmerged_formatted_text += f"##File: {file_path}\n"
                unmerged_formatted_text += "<<<<<<< SEARCH\n"
                unmerged_formatted_text += head
                unmerged_formatted_text += "=======\n"
                unmerged_formatted_text += update
                unmerged_formatted_text += ">>>>>>> REPLACE\n"
                unmerged_formatted_text += "```"
                unmerged_formatted_text += "\n"

            merged_formatted_text = ""
            if merge.merged_blocks:
                for file_path, head, update in merge.merged_blocks:
                    merged_formatted_text += "```lang\n"
                    merged_formatted_text += f"##File: {file_path}\n"
                    merged_formatted_text += head
                    merged_formatted_text += "=======\n"
                    merged_formatted_text += update
                    merged_formatted_text += "```"
                    merged_formatted_text += "\n"

            get_event_manager(self.args.event_file).write_result(EventContentCreator.create_result(
                content=EventContentCreator.ResultContent(content=f"Unmerged blocks:\n\n {unmerged_formatted_text}",
                                                          metadata={
                                                              "merged_blocks": merge.success_blocks,
                                                              "failed_blocks": merge.failed_blocks
                                                          }
                                                          ).to_dict(),
                metadata={
                    "stream_out_type": UnmergedBlocksStreamOutType.UNMERGED_BLOCKS.value,
                    "action_file": self.args.file,
                    "path": "/unmerged_blocks/check/message"
                }
            ))
            return (unmerged_formatted_text, merged_formatted_text)

        for attempt in range(self.args.auto_fix_merge_max_attempts):
            global_cancel.check_and_raise(token=self.args.event_file)
            unmerged_formatted_text, merged_formatted_text = _format_blocks(
                merge)
            fix_prompt = self.fix_unmerged_blocks.prompt(
                query=query,
                original_code=generation_result.contents[0],
                unmerged_blocks=unmerged_formatted_text
            )

            logger.info(f"fix_prompt: {fix_prompt}")

            # 打印当前修复尝试状态
            self.printer.print_in_terminal(
                "unmerged_blocks_attempt_status",
                style="yellow",
                attempt=(attempt + 1),
                max_correction_attempts=self.args.auto_fix_merge_max_attempts
            )

            get_event_manager(self.args.event_file).write_result(EventContentCreator.create_result(
                content=EventContentCreator.ResultContent(content=f"Unmerged blocks attempt {attempt + 1}/{self.args.auto_fix_merge_max_attempts}: {unmerged_formatted_text}",
                                                          metadata={}
                                                          ).to_dict(),
                metadata={
                    "stream_out_type": UnmergedBlocksStreamOutType.UNMERGED_BLOCKS.value,
                    "action_file": self.args.file,
                    "path": "/unmerged_blocks/check/message"
                }
            ))

            # 使用修复提示重新生成代码
            start_time = time.time()
            generation_result = self.code_generator.single_round_run(
                fix_prompt, source_code_list)

            # 计算这次修复未合并块花费的token情况
            token_cost_calculator.track_token_usage_by_generate(
                llm=self.code_generator.llms[0],
                generate=generation_result,
                operation_name="code_generation_complete",
                start_time=start_time,
                end_time=time.time()
            )

            # 检查修复后的代码是否仍有未合并块
            generation_result = self.code_merger.choose_best_choice(
                generation_result)
            # 因为已经排完结果，就不要触发后面的排序了，所以只要保留第一个即可。
            generation_result = CodeGenerateResult(contents=[generation_result.contents[0]], conversations=[
                                                   generation_result.conversations[0]], metadata=generation_result.metadata)
            merge = self.code_merger._merge_code_without_effect(
                generation_result.contents[0])

            # 如果没有失败的块，则修复成功，退出循环
            if not merge.failed_blocks:
                self.printer.print_in_terminal(
                    "unmerged_blocks_fixed", style="green")
                break

            # 如果是最后一次尝试仍未成功，打印警告
            if attempt == self.args.auto_fix_merge_max_attempts - 1:
                self.printer.print_in_terminal(
                    "max_unmerged_blocks_attempts_reached", style="yellow")
                get_event_manager(self.args.event_file).write_result(EventContentCreator.create_result(
                    content=EventContentCreator.ResultContent(content=self.printer.get_message_from_key("max_unmerged_blocks_attempts_reached"),
                                                              metadata={}
                                                              ).to_dict(),
                    metadata={
                        "stream_out_type": UnmergedBlocksStreamOutType.UNMERGED_BLOCKS.value,
                        "action_file": self.args.file
                    }
                ))
                raise Exception(self.printer.get_message_from_key(
                    "max_unmerged_blocks_attempts_reached"))

        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(
                content=self.printer.get_message_from_key("/unmerged_blocks/check/end")),
            metadata={
                "stream_out_type": UnmergedBlocksStreamOutType.UNMERGED_BLOCKS.value,
                "action_file": self.args.file,
                "path": "/unmerged_blocks/check/end"
            }
        )
        return generation_result

    def _fix_lint_errors(self, query: str, generation_result: CodeGenerateResult, source_code_list: SourceCodeList) -> CodeGenerateResult:
        """
        自动修复lint错误，最多尝试指定次数

        参数:
            query (str): 用户查询
            generation_result (CodeGenerateResult): 生成的代码结果
            source_code_list (SourceCodeList): 源代码列表

        返回:
            CodeGenerateResult: 修复后的代码结果
        """
        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(
                content=self.printer.get_message_from_key("/lint/check/start")),
            metadata={
                "stream_out_type": LintStreamOutType.LINT.value,
                "action_file": self.args.file,
                "path": "/lint/check/start"
            }
        )

        token_cost_calculator = TokenCostCalculator(args=self.args)

        for attempt in range(self.auto_fix_lint_max_attempts):
            global_cancel.check_and_raise(token=self.args.event_file)
            # 代码生成结果更新到影子文件里去
            self.shadow_manager.clean_shadows()
            shadow_files = self._create_shadow_files_from_edits(
                generation_result)

            if not shadow_files:
                self.printer.print_in_terminal(
                    "no_files_to_lint", style="yellow")
                break

            # 运行linter
            lint_results = self.shadow_linter.lint_all_shadow_files()
            error_count = self._count_errors(lint_results)

            # 如果没有错误则完成
            if error_count == 0:
                self.printer.print_in_terminal(
                    "no_lint_errors_found", style="green")
                break

            # 格式化lint问题
            formatted_issues = self._format_lint_issues(
                lint_results, [IssueSeverity.ERROR, IssueSeverity.WARNING])

            # 打印当前错误
            self.printer.print_in_terminal(
                "lint_attempt_status",
                style="yellow",
                attempt=(attempt + 1),
                max_correction_attempts=self.auto_fix_lint_max_attempts,
                error_count=error_count,
                formatted_issues=formatted_issues
            )

            # 把lint结果记录到事件系统
            get_event_manager(self.args.event_file).write_result(EventContentCreator.create_result(
                content=EventContentCreator.ResultContent(content=f"Lint attempt {attempt + 1}/{self.auto_fix_lint_max_attempts}: Found {error_count} issues:\n {formatted_issues}",
                                                          metadata={}
                                                          ).to_dict(),
                metadata={
                    "stream_out_type": LintStreamOutType.LINT.value,
                    "action_file": self.args.file,
                    "path": "/lint/check/message"
                }
            ))

            if attempt == self.auto_fix_lint_max_attempts - 1:
                self.printer.print_in_terminal(
                    "max_attempts_reached", style="yellow")
                break

            # 准备修复提示
            fix_prompt = self.fix_linter_errors.prompt(
                query=query,
                lint_issues=formatted_issues
            )

            # 将 shadow_files 转化为 source_code_list
            start_time = time.time()
            source_code_list = self.code_merger.get_source_code_list_from_shadow_files(
                shadow_files)
            generation_result = self.code_generator.single_round_run(
                fix_prompt, source_code_list)

            # 计算这次修复lint问题花费的token情况
            token_cost_calculator.track_token_usage_by_generate(
                llm=self.code_generator.llms[0],
                generate=generation_result,
                operation_name="code_generation_complete",
                start_time=start_time,
                end_time=time.time()
            )

        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(
                content=self.printer.get_message_from_key("/lint/check/end")),
            metadata={
                "stream_out_type": LintStreamOutType.LINT.value,
                "action_file": self.args.file,
                "path": "/lint/check/end"
            }
        )
        return generation_result

    def _fix_compile_errors(self, query: str, generation_result: CodeGenerateResult, source_code_list: SourceCodeList) -> CodeGenerateResult:
        """
        自动修复编译错误，最多尝试指定次数

        参数:
            query (str): 用户查询
            generation_result (CodeGenerateResult): 生成的代码结果
            source_code_list (SourceCodeList): 源代码列表

        返回:
            CodeGenerateResult: 修复后的代码结果
        """
        if not self.args.enable_auto_fix_compile:
            return generation_result

        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(
                content=self.printer.get_message_from_key("/compile/check/start")),
            metadata={
                "stream_out_type": CompileStreamOutType.COMPILE.value,
                "action_file": self.args.file,
                "path": "/compile/check/start"
            }
        )

        token_cost_calculator = TokenCostCalculator(args=self.args)

        for attempt in range(self.auto_fix_compile_max_attempts):
            global_cancel.check_and_raise(token=self.args.event_file)
            # 先更新增量影子系统的文件
            self.shadow_manager.clean_shadows()
            shadow_files = self._create_shadow_files_from_edits(
                generation_result)

            # 在影子系统生成完整的项目，然后编译
            compile_result = self.shadow_compiler.compile_all_shadow_files()

            # 如果编译成功，则退出，继续往后走
            if compile_result.success or compile_result.total_errors == 0:
                self.printer.print_in_terminal(
                    "compile_success", style="green")
                break

            # 如果有错误，则把compile结果记录到事件系统
            get_event_manager(self.args.event_file).write_result(EventContentCreator.create_result(
                content=EventContentCreator.ResultContent(content=f"Compile attempt {attempt + 1}/{self.auto_fix_compile_max_attempts}: Found {compile_result.total_errors} errors:\n {compile_result.to_str()}",
                                                          metadata={}
                                                          ).to_dict(),
                metadata={
                    "stream_out_type": CompileStreamOutType.COMPILE.value,
                    "action_file": self.args.file,
                    "path": "/compile/check/message"
                }
            ))

            if attempt == self.auto_fix_compile_max_attempts - 1:
                self.printer.print_in_terminal(
                    "max_compile_attempts_reached", style="yellow")
                break

            # 打印当前compile错误
            self.printer.print_in_terminal("compile_attempt_status",
                                           style="yellow",
                                           attempt=(attempt + 1), max_correction_attempts=self.auto_fix_compile_max_attempts,
                                           error_count=compile_result.total_errors,
                                           formatted_issues=compile_result.to_str())

            fix_compile_prompt = self.fix_compile_errors.prompt(
                query=query,
                compile_errors=compile_result.to_str()
            )

            # 将 shadow_files 转化为 source_code_list
            start_time = time.time()
            source_code_list = self.code_merger.get_source_code_list_from_shadow_files(
                shadow_files)
            generation_result = self.code_generator.single_round_run(
                fix_compile_prompt, source_code_list)

            # 计算这次修复compile问题花费的token情况
            token_cost_calculator.track_token_usage_by_generate(
                llm=self.code_generator.llms[0],
                generate=generation_result,
                operation_name="code_generation_complete",
                start_time=start_time,
                end_time=time.time()
            )

        # Log end only if enabled
        if self.args.enable_auto_fix_compile:
            get_event_manager(self.args.event_file).write_result(
                EventContentCreator.create_result(
                    content=self.printer.get_message_from_key("/compile/check/end")),
                metadata={  
                    "stream_out_type": CompileStreamOutType.COMPILE.value,
                    "action_file": self.args.file,
                    "path": "/compile/check/end"
                }
            )
        return generation_result

    def generate_and_fix(self, query: str, source_code_list: SourceCodeList) -> CodeGenerateResult:
        """
        生成代码，运行linter/compile，修复错误，最多尝试指定次数

        参数:
            query (str): 用户查询
            source_code_list (SourceCodeList): 源代码列表

        返回:
            CodeGenerateResult: 生成的代码结果
        """
        # 初始代码生成
        self.printer.print_in_terminal("generating_initial_code")
        start_time = time.time()
        generation_result = self.code_generator.single_round_run(
            query, source_code_list)

        token_cost_calculator = TokenCostCalculator(args=self.args)
        token_cost_calculator.track_token_usage_by_generate(
            llm=self.code_generator.llms[0],
            generate=generation_result,
            operation_name="code_generation_complete",
            start_time=start_time,
            end_time=time.time()
        )

        # 确保结果非空
        if not generation_result.contents:
            self.printer.print_in_terminal("generation_failed", style="red")
            return generation_result

        # 可能第一次触发排序
        generation_result = self.code_merger.choose_best_choice(
            generation_result)

        # 因为已经排完结果，就不要触发后面的排序了，所以只要保留第一个即可。
        generation_result = CodeGenerateResult(contents=[generation_result.contents[0]], conversations=[
                                               generation_result.conversations[0]], metadata=generation_result.metadata)

        # 修复缺少上下文的文件
        generation_result = self._fix_missing_context(
            query, generation_result, source_code_list)

        # 修复未合并的代码块
        generation_result = self._fix_unmerged_blocks(
            query, generation_result, source_code_list)

        # 修复lint错误
        generation_result = self._fix_lint_errors(
            query, generation_result, source_code_list)

        # 修复编译错误
        generation_result = self._fix_compile_errors(
            query, generation_result, source_code_list)

        # self.shadow_manager.clean_shadows()

        # 返回最终结果
        return generation_result

    def run(self, query: str, source_code_list: SourceCodeList) -> CodeGenerateResult:
        """
        执行完整的代码生成、修复、合并流程

        参数:
            query (str): 用户查询
            source_code_list (SourceCodeList): 源代码列表

        返回:
            CodeGenerateResult: 生成和修复的代码结果
        """
        # 生成代码并自动修复lint错误

        generation_result = self.generate_and_fix(query, source_code_list)
        global_cancel.check_and_raise(token=self.args.event_file)

        # 合并代码
        self.code_merger.merge_code(generation_result)

        return generation_result
