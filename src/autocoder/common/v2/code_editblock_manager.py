from typing import List, Dict, Tuple, Optional, Any
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor

import byzerllm
from byzerllm.utils.client import code_utils

from autocoder.common.types import Mode, CodeGenerateResult, MergeCodeWithoutEffect
from autocoder.common import AutoCoderArgs, git_utils, SourceCodeList
from autocoder.common import sys_prompt
from autocoder.compilers.shadow_compiler import ShadowCompiler
from autocoder.privacy.model_filter import ModelPathFilter
from autocoder.common.utils_code_auto_generate import chat_with_continue, stream_chat_with_continue, ChatWithContinueResult
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.stream_out_type import LintStreamOutType, CompileStreamOutType, UnmergedBlocksStreamOutType
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
            llm=self.llm,
            generate=generation_result,
            operation_name="code_generation_complete",
            start_time=start_time,
            end_time=time.time()
        )

        # 确保结果非空
        if not generation_result.contents:
            self.printer.print_in_terminal("generation_failed", style="red")
            return generation_result
        
        ## 可能第一次触发排序
        generation_result = self.code_merger.choose_best_choice(generation_result)
        merge = self.code_merger._merge_code_without_effect(generation_result.contents[0])

        ## 因为已经排完结果，就不要触发后面的排序了，所以只要保留第一个即可。
        generation_result = CodeGenerateResult(contents=[generation_result.contents[0]],conversations=[generation_result.conversations[0]],metadata=generation_result.metadata)

        if self.args.enable_auto_fix_merge and merge.failed_blocks:
            def _format_blocks(merge: MergeCodeWithoutEffect) -> Tuple[str, str]:
                unmerged_formatted_text = ""
                for file_path, head, update in merge.failed_blocks:
                    unmerged_formatted_text += "```lang"
                    unmerged_formatted_text += f"##File: {file_path}\n"
                    unmerged_formatted_text += "<<<<<<< SEARCH\n"
                    unmerged_formatted_text += head
                    unmerged_formatted_text += "=======\n"
                    unmerged_formatted_text += update
                    unmerged_formatted_text += ">>>>>>> REPLACE\n"
                    unmerged_formatted_text += "```"
                    unmerged_formatted_text += "\n"

                merged_formatted_text = ""
                for file_path, head, update in merge.merged_blocks:
                    merged_formatted_text += "```lang"
                    merged_formatted_text += f"##File: {file_path}\n"
                    merged_formatted_text += head
                    merged_formatted_text += "=======\n"
                    merged_formatted_text += update
                    merged_formatted_text += "```"
                    merged_formatted_text += "\n"

                get_event_manager(self.args.event_file).write_result(EventContentCreator.create_result(
                    content=EventContentCreator.ResultContent(content=f"Unmerged blocks:\\n {unmerged_formatted_text}",
                                                              metadata={
                                                                  "merged_blocks": merge.success_blocks,
                                                                  "failed_blocks": merge.failed_blocks
                                                              }
                                                              ).to_dict(),
                    metadata={
                        "stream_out_type": UnmergedBlocksStreamOutType.UNMERGED_BLOCKS.value,
                        "action_file": self.args.file
                    }
                ))
                return (unmerged_formatted_text, merged_formatted_text)

            for attempt in range(self.args.auto_fix_merge_max_attempts):
                global_cancel.check_and_raise()
                unmerged_formatted_text, merged_formatted_text = _format_blocks(
                    merge)
                fix_prompt = self.fix_unmerged_blocks.prompt(
                    query=query,
                    original_code=result.contents[0],
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
                        "action_file": self.args.file
                    }
                ))

                # 使用修复提示重新生成代码
                start_time = time.time()
                generation_result = self.code_generator.single_round_run(
                    fix_prompt, source_code_list)

                # 计算这次修复未合并块花费的token情况
                token_cost_calculator = TokenCostCalculator(args=self.args)
                token_cost_calculator.track_token_usage_by_generate(
                    llm=self.llm,
                    generate=generation_result,
                    operation_name="code_generation_complete",
                    start_time=start_time,
                    end_time=time.time()
                )

                # 检查修复后的代码是否仍有未合并块
                generation_result = self.code_merger.choose_best_choice(generation_result)
                ## 因为已经排完结果，就不要触发后面的排序了，所以只要保留第一个即可。
                generation_result = CodeGenerateResult(contents=[generation_result.contents[0]],conversations=[generation_result.conversations[0]],metadata=generation_result.metadata)
                merge = self.code_merger._merge_code_without_effect(
                    result.contents[0])

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

        # 接着开始看看 Lin他最多尝试修复5次
        for attempt in range(self.auto_fix_lint_max_attempts):
            global_cancel.check_and_raise()
            # 代码生成结果更新到影子文件里去
            shadow_files = self._create_shadow_files_from_edits(
                generation_result)

            if not shadow_files:
                self.printer.print_in_terminal(
                    "no_files_to_lint", style="yellow")
                break

            # 运行linter
            lint_results = self.shadow_linter.lint_all_shadow_files()
            error_count = self._count_errors(lint_results)
            # print(f"error_count: {error_count}")
            # print(f"lint_results: {json.dumps(lint_results.model_dump(), indent=4,ensure_ascii=False)}")

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
                    "action_file": self.args.file
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

            # for source in source_code_list.sources:
            #     print(f"file_path: {source.module_name}")
            # print(f"fix_prompt: {fix_prompt}")

            # 将 shadow_files 转化为 source_code_list
            start_time = time.time()
            source_code_list = self.code_merger.get_source_code_list_from_shadow_files(
                shadow_files)
            generation_result = self.code_generator.single_round_run(
                fix_prompt, source_code_list)

            # 计算这次修复lint 问题花费的token情况
            token_cost_calculator.track_token_usage_by_generate(
                llm=self.llm,
                generate=generation_result,
                operation_name="code_generation_complete",
                start_time=start_time,
                end_time=time.time()
            )

        # 如果开启了自动修复compile问题，则进行compile修复
        if self.args.enable_auto_fix_compile:
            for attempt in range(self.auto_fix_compile_max_attempts):
                global_cancel.check_and_raise()
                # 先更新增量影子系统的文件
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
                        "action_file": self.args.file
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

                # 计算这次修复compile 问题花费的token情况
                token_cost_calculator.track_token_usage_by_generate(
                    llm=self.llm,
                    generate=generation_result,
                    operation_name="code_generation_complete",
                    start_time=start_time,
                    end_time=time.time()
                )

        # 清理临时影子文件
        self.shadow_manager.clean_shadows()

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
        global_cancel.check_and_raise()

        # 合并代码
        self.code_merger.merge_code(generation_result)

        return generation_result
