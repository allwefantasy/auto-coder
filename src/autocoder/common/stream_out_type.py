from enum import Enum

class AutoCommandStreamOutType(Enum):
    COMMAND_SUGGESTION = "command_suggestion"    
class IndexFilterStreamOutType(Enum):
    FILE_NUMBER_LIST = "file_number_list"

class AgenticFilterStreamOutType(Enum):
    AGENTIC_FILTER = "agentic_filter"


class CodeGenerateStreamOutType(Enum):
    CODE_GENERATE = "code_generate"

class CodeRankStreamOutType(Enum):
    CODE_RANK = "code_rank"

class LintStreamOutType(Enum):
    LINT = "lint"

class UnmergedBlocksStreamOutType(Enum):
    UNMERGED_BLOCKS = "unmerged_blocks"

class CompileStreamOutType(Enum):
    COMPILE = "compile"

class ContextMissingCheckStreamOutType(Enum):
    CONTEXT_MISSING_CHECK = "context_missing_check"

class IndexStreamOutType(Enum):
    INDEX_BUILD = "index_build"