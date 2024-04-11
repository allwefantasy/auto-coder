from autocoder.index.index import IndexManager,TargetFile
from autocoder.suffixproject import SuffixProject
import tabulate
from loguru import logger

def index_command(args,llm):   
    project = SuffixProject(args,llm) 
    project.run()
    sources = project.sources
    index_manager = IndexManager(llm=llm, sources=sources, args=args)
    index_manager.build_index()    

def index_query_command(args,llm):    
    project = SuffixProject(args,llm) 
    project.run()
    sources = project.sources  
    
    index_manager = IndexManager(llm=llm, sources=sources, args=args)
    related_files = index_manager.get_target_files_by_query(args.query)
    
    print("===================Filter FILEs=========================",flush=True)
    
    print(f"index_filter_level:{args.index_filter_level}, filter files by query: {args.query}",flush=True)

    headers =  TargetFile.model_fields.keys()
    table_data = [[getattr(file_item, name) for name in headers] for file_item in related_files.file_list]    
    table_output = tabulate.tabulate(table_data, headers, tablefmt="grid")    
    print(table_output,flush=True)        
    return    