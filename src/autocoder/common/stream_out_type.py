from enum import Enum

class AutoCommandStreamOutType(Enum):
    COMMAND_SUGGESTION = "command_suggestion"

class IndexFilterStreamOutType(Enum):
    FILE_NUMBER_LIST = "file_number_list"


class CodeGenerateStreamOutType(Enum):
    CODE_GENERATE = "code_generate"

class CodeRankStreamOutType(Enum):
    CODE_RANK = "code_rank"    
