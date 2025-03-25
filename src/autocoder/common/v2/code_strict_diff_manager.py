from typing import Dict
from autocoder.common.v2.code_manager import CodeManager
from autocoder.common.types import CodeGenerateResult
from autocoder.common.v2.code_auto_merge_strict_diff import CodeAutoMergeStrictDiff
from autocoder.common.v2.code_auto_generate_strict_diff import CodeAutoGenerateStrictDiff
import byzerllm
from autocoder.common import AutoCoderArgs

class CodeStrictDiffManager(CodeManager):
    """
    A class that combines code generation, linting, and merging with automatic error correction,
    specifically for strict diff-based code generation.
    """
    
    def __init__(
        self,
        llm: byzerllm.ByzerLLM,
        args: AutoCoderArgs,
        action=None,
    ) -> None:
        super().__init__(llm, args, action)
        
        # Initialize sub-components
        self.code_generator = CodeAutoGenerateStrictDiff(llm, args, action)
        self.code_merger = CodeAutoMergeStrictDiff(llm, args)

    def _create_shadow_files_from_edits(self, generation_result: CodeGenerateResult) -> Dict[str, str]:
        """
        从diff内容中提取代码并创建临时影子文件用于检查。
        
        参数:
            generation_result (CodeGenerateResult): 包含diff格式的内容
            
        返回:
            Dict[str, str]: 映射 {影子文件路径: 内容}
        """
        result = self.code_merger.choose_best_choice(generation_result)
        merge = self.code_merger._merge_code_without_effect(result.contents[0])        
        shadow_files = {}
        for file_path, new_content in merge.success_blocks:
            self.shadow_manager.update_file(file_path, new_content)
            shadow_files[self.shadow_manager.to_shadow_path(file_path)] = new_content

        return shadow_files

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
        请使用 unified diff 格式生成修复后的代码。

        # Unified Diff Rules:

        Every unified diff must use this format:
        1. The file path line starting with "--- " for the old file
        2. The file path line starting with "+++ " for the new file
        3. The hunk header line starting with "@@ " (with line numbers)
        4. Lines starting with " " for context lines
        5. Lines starting with "-" for lines to remove
        6. Lines starting with "+" for lines to add

        The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
        Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
        Make sure you mark all new or modified lines with `+`.
        Don't leave out any lines or the diff patch won't apply correctly.

        Indentation matters in the diffs!

        To make a new file, show a diff from `--- /dev/null` to `+++ path/to/new/file.ext`.
        """ 