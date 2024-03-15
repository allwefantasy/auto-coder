from autocoder.common import SourceCode,AutoCoderArgs
from autocoder.index import IndexManager
from typing import List

def build_index_and_filter_files(llm,args:AutoCoderArgs,sources:List[SourceCode])->str:
    final_files = []
    if not args.skip_build_index and llm:        
        index_manager = IndexManager(llm=llm,sources=sources,args=args)
        index_manager.build_index()
        target_files = index_manager.get_target_files_by_query(args.query)
        print(f"Target Files: {target_files.file_list}",flush=True)
        related_fiels = index_manager.get_related_files([file.file_path for file in target_files.file_list])        
        print(f"Related Files: {related_fiels.file_list}",flush=True)                

        for file in target_files.file_list + related_fiels.file_list:
            if file.file_path.strip().startswith("##"):
                final_files.append(file.file_path.strip()[2:])            
    else:
        final_files = [file.module_name for file in sources]

    source_code = "" 
    for file in sources:
        if file.module_name in final_files:
            source_code += f"##File: {file.module_name}\n"
            source_code += f"{file.source_code}\n\n" 
    return source_code         