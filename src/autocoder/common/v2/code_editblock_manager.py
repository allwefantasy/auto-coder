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
from autocoder.privacy.model_filter import ModelPathFilter
from autocoder.common.utils_code_auto_generate import chat_with_continue, stream_chat_with_continue, ChatWithContinueResult
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.stream_out_type import LintStreamOutType
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
        self.max_correction_attempts = args.auto_fix_lint_max_attempts
        self.printer = Printer()

        # Initialize sub-components
        self.code_generator = CodeAutoGenerateEditBlock(
            llm, args, action, fence_0, fence_1)
        self.code_merger = CodeAutoMergeEditBlock(llm, args, fence_0, fence_1)

        # Create shadow manager for linting
        self.shadow_manager = ShadowManager(args.source_dir, args.event_file)
        self.shadow_linter = ShadowLinter(self.shadow_manager, verbose=False)

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
        生成代码，运行linter，修复错误，最多尝试指定次数

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

        # 最多尝试修复5次
        for attempt in range(self.max_correction_attempts):
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
                max_correction_attempts=self.max_correction_attempts,
                error_count=error_count,
                formatted_issues=formatted_issues
            )

            get_event_manager(self.args.event_file).write_result(EventContentCreator.create_result(
                content=EventContentCreator.ResultContent(content=f"Lint attempt {attempt + 1}/{self.max_correction_attempts}: Found {error_count} issues:\n {formatted_issues}",
                                                          metadata={}
                                                          ).to_dict(),
                metadata={
                    "stream_out_type": LintStreamOutType.LINT.value,
                    "action_file": self.args.file
                }
            ))

            if attempt == self.max_correction_attempts - 1:
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
