
from typing import List, Optional
from pydantic import BaseModel
from typing import Dict,Any

class SourceCode(BaseModel):
    module_name: str
    source_code: str
    doc_type: str = "code"

class AutoCoderArgs(BaseModel):
    source_dir: Optional[str] = None
    git_url: Optional[str] = None
    target_file: Optional[str] = None
    query: Optional[str] = None
    template: Optional[str] = None
    project_type: Optional[str] = None
    execute: Optional[bool] = None
    package_name: Optional[str] = ""
    script_path: Optional[str] = ""
    model: Optional[str] = ""
    model_max_length: Optional[int] = 2000
    model_max_input_length: Optional[int] = 6000
    vl_model: Optional[str] = ""
    sd_model: Optional[str] = ""
    emb_model: Optional[str] = ""
    index_model: Optional[str] = ""
    index_model_max_length: Optional[int] = 0    
    index_model_max_input_length: Optional[int] = 0    
    index_model_anti_quota_limit:Optional[int] = 0
    index_filter_level: Optional[int] = 0
    index_filter_workers: Optional[int] = 1
    file: Optional[str] = ""
    ray_address: Optional[str] = ""
    anti_quota_limit: Optional[int] = 1
    skip_build_index: Optional[bool] = False
    print_request: Optional[bool] = False
    py_packages: Optional[str] = ""
    search_engine: Optional[str] = ""
    search_engine_token: Optional[str] = ""
    enable_rag_search: Optional[bool] = False
    enable_rag_context: Optional[bool] = False
    auto_merge: Optional[bool] = False
    image_file: Optional[str] = ""
    image_max_iter: Optional[int] = 1
    human_as_model:Optional[bool] = False
    urls: Optional[str] = ""
    urls_use_model: Optional[bool] = False
    enable_multi_round_generate: Optional[bool] = False
    command: Optional[str] = None
    doc_command: Optional[str] = None
    required_exts: Optional[str] = None
    collection: Optional[str] = "default"  # 新增 collection 字段，默认为 "default"
    collections: Optional[str] = "default"  # 新增 collections 字段，默认为 "default"
    description: Optional[str] = ""  # 新增 description 字段，默认为空字符串

class SearchSourceCode(BaseModel):
    doc_path: str
    source_code: str
    doc_type: str = "code"

class NamedData(BaseModel):
    name: str
    data: Any