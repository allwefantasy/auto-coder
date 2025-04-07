from pathlib import Path
from typing import List, Dict, Any
from autocoder.common.context_pruner import PruneContext
from autocoder.common import AutoCoderArgs
import byzerllm
from autocoder.utils.llms import get_single_llm
from autocoder.rag.variable_holder import VariableHolder
from tokenizers import Tokenizer    
import pkg_resources
import os
from autocoder.common import SourceCode
from autocoder.rag.token_counter import count_tokens
from autocoder.commands.tools import AutoCommandTools

try:
    tokenizer_path = pkg_resources.resource_filename(
        "autocoder", "data/tokenizer.json"
    )
    VariableHolder.TOKENIZER_PATH = tokenizer_path
    VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
except FileNotFoundError:
    tokenizer_path = None


args = AutoCoderArgs(
        source_dir=".",
        context_prune=True,
        context_prune_strategy="extract",
        conversation_prune_safe_zone_tokens=400,  # 设置较小的token限制以触发抽取逻辑
        context_prune_sliding_window_size=10,
        context_prune_sliding_window_overlap=2,
        query="如何实现加法和减法运算？"
    )

    # 获取LLM实例
llm = get_single_llm("v3_chat", product_mode="lite")


tools = AutoCommandTools(llm=llm, args=args)

print(tools.list_files(path="/Users/allwefantasy/projects/auto-coder/src"))

