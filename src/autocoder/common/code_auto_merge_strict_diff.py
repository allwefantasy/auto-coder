import os
import difflib
from autocoder.common import AutoCoderArgs,git_utils
from typing import List
import pydantic
import byzerllm
from loguru import logger
import hashlib
from byzerllm.utils.client import code_utils

class PathAndCode(pydantic.BaseModel):
    path: str
    content: str


no_match_error = """UnifiedDiffNoMatch: hunk failed to apply!

{path} does not contain lines that match the diff you provided!
Try again.
DO NOT skip blank lines, comments, docstrings, etc!
The diff needs to apply cleanly to the lines in {path}!

{path} does not contain these {num_lines} exact lines in a row:
```
{original}```
"""


not_unique_error = """UnifiedDiffNotUnique: hunk failed to apply!

{path} contains multiple sets of lines that match the diff you provided!
Try again.
Use additional ` ` lines to provide context that uniquely indicates which code needs to be changed.
The diff needs to apply to a unique set of lines in {path}!

{path} contains multiple copies of these {num_lines} lines:
```
{original}```
"""

other_hunks_applied = (
    "Note: some hunks did apply successfully. See the updated source code shown above.\n\n"
)

class CodeAutoMergeStrictDiff:
    def __init__(self, llm:byzerllm.ByzerLLM,args:AutoCoderArgs):
        self.llm = llm
        self.args = args        

    def merge_code(self, content: str,force_skip_git:bool=False):        
        total = 0
        
        file_content = open(self.args.file).read()
        md5 = hashlib.md5(file_content.encode('utf-8')).hexdigest()
        # get the file name 
        file_name = os.path.basename(self.args.file)
        
        if not force_skip_git:
            try:
                git_utils.commit_changes(self.args.source_dir, f"auto_coder_pre_{file_name}_{md5}")
            except Exception as e:            
                logger.error(self.git_require_msg(source_dir=self.args.source_dir,error=str(e)))
                return   
                     
        codes = code_utils.extract_code(content)
        diff_codes = []
        for [lang,code] in codes:
            if lang == "diff":
                diff_codes.append(code)            
        
        for diff_code in diff_codes:                        
            patch = difflib.patch_fromstring(diff_code)
            content, success = patch.apply(content)

            if not all(success):
                raise Exception(other_hunks_applied + patch)
            else:
                # 成功应用,写回文件
                self.io.write_text(full_path, "\n".join(content))

        logger.info(f"Merged {total} files into the project.")
        if not force_skip_git:
            git_utils.commit_changes(self.args.source_dir, f"auto_coder_{file_name}_{md5}")
