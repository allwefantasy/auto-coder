from autocoder.index.index import IndexManager
from autocoder.suffixproject import SuffixProject
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
    logger.info("Related files:")
    for file in related_files.file_list:
        logger.info(f"- {file.file_path}")
    return    