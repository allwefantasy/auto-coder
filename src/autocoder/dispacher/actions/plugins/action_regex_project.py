import byzerllm
from typing import Optional
from autocoder.common import AutoCoderArgs
from autocoder.common.code_auto_generate import CodeAutoGenerate
from autocoder.common.code_auto_merge import CodeAutoMerge
from autocoder.index.index import build_index_and_filter_files
from autocoder.regex_project import RegexProject
from loguru import logger

class ActionRegexProject:
    def __init__(self, args: AutoCoderArgs, llm: Optional[byzerllm.ByzerLLM] = None) -> None:
        self.args = args
        self.llm = llm

    def run(self):
        args = self.args        
        if not args.project_type.startswith("human://") and not args.project_type.startswith("regex://"):    
            return False 
        
        args = self.args
        pp = RegexProject(args=args, llm=self.llm)
        pp.run()
        source_code = pp.output()
        if self.llm:
            source_code = build_index_and_filter_files(llm=self.llm, args=args, sources=pp.sources)
        self.process_content(source_code)

    def process_content(self, content: str):
        args = self.args

        if args.execute and self.llm and not args.human_as_model:
            if len(content) > self.args.model_max_input_length:
                logger.warning(f"Content length is {len(content)}, which is larger than the maximum input length {self.args.model_max_input_length}. chunk it...")
                content = content[:self.args.model_max_input_length]

        if args.execute:
            generate = CodeAutoGenerate(llm=self.llm, args=self.args)
            if self.args.enable_multi_round_generate:
                result, _ = generate.multi_round_run(query=args.query, source_content=content)
            else:
                result, _ = generate.single_round_run(query=args.query, source_content=content)
            content = "\n\n".join(result)

        with open(args.target_file, "w") as file:
            file.write(content)

        if args.execute and args.auto_merge:
            logger.info("Auto merge the code...")
            code_merge = CodeAutoMerge(llm=self.llm, args=self.args)
            code_merge.merge_code(content=content)