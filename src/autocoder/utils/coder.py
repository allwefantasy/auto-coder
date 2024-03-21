
from autocoder.common import AutoCoderArgs
import byzerllm
import pydantic
from enum import Enum

class TaskTypeDef(pydantic.BaseModel):
    name: str
    desc: str = ""
    guidance: str = ""


class TaskType(Enum):
    """By identifying specific types of tasks, we can inject human priors (guidance) to help task solving"""
    
    @byzerllm.prompt(render="jinja2")
    def data_preprocess_prompt():
        '''
        The current task is about data preprocessing, please note the following:
        - Monitor data types per column, applying appropriate methods.
        - Ensure operations are on existing dataset columns.
        - Avoid writing processed data to files.
        - Avoid any change to label column, such as standardization, etc.
        - Prefer alternatives to one-hot encoding for categorical data.
        - Only encode or scale necessary columns to allow for potential feature-specific engineering tasks (like time_extract, binning, extraction, etc.) later.
        - Each step do data preprocessing to train, must do same for test separately at the same time.
        - Always copy the DataFrame before processing it and use the copy to process.
        '''

    @byzerllm.prompt(render="jinja2")
    def image2webpage_prompt():
        '''
        The current task is about converting image into webpage code. please note the following:
        - Single-Step Code Generation: Execute the entire code generation process in a single step, encompassing HTML, CSS, and JavaScript. Avoid fragmenting the code generation into multiple separate steps to maintain consistency and simplify the development workflow.
        - Save webpages: Be sure to use the save method provided.
        '''    
    
    DATA_PREPROCESS = TaskTypeDef(
        name="data preprocessing",
        desc="For preprocessing dataset in a data analysis or machine learning task ONLY,"
        "general data operation doesn't fall into this type",
        guidance=data_preprocess_prompt(),
    )
    
    IMAGE2WEBPAGE = TaskTypeDef(
        name="image2webpage",
        desc="For converting image into webpage code.",
        guidance=image2webpage_prompt(),
    )
    OTHER = TaskTypeDef(name="other", desc="Any tasks not in the defined categories")

    @property
    def type_name(self):
        return self.value.name

    @classmethod
    def get_type(cls, type_name):
        for member in cls:
            if member.type_name == type_name:
                return member.value
        return None

class Thought(pydantic.BaseModel):
    thoughts:str = pydantic.Field(...,description="Thoughts on current situation, reflect on how you should proceed to fulfill the user requirement")
    state:bool = pydantic.Field(...,description="Decide whether you need to take more actions to complete the user requirement. Return true if you think so. Return false if you think the requirement has been completely fulfilled.")

class Plan(pydantic.BaseModel):
    task_id:str = pydantic.Field(...,description="unique identifier for a task in plan, can be an ordinal")
    dependent_task_ids:list[str] = pydantic.Field(...,description="ids of tasks prerequisite to this task")
    instruction:str = pydantic.Field(...,description="what you should do in this task, one short phrase or sentence")
    task_type:str = pydantic.Field(...,description="type of this task, should be one of Available Task Types")

class Coder:
    def __init__(self,llm:byzerllm.ByzerLLM,args:AutoCoderArgs) -> None:
        self.llm = llm
        self.args = args
        self.working_memory = []

    def get_task_type_desc(self):
        task_type_desc = "\n".join([f"- **{tt.type_name}**: {tt.value.desc}" for tt in TaskType])    
        return task_type_desc
    
    @byzerllm.prompt(llm=lambda self:self.llm,render="jinja2")
    def write_plan(self,context:str,task_type_desc:str,max_tasks:int=3):
        '''
        # Context:
        {{ context }}
        # Available Task Types:
        {{ task_type_desc}}
        # Task:
        Based on the context, write a plan or modify an existing plan of what you should do to achieve the goal. A plan consists of one to {{ max_tasks }} tasks.
        If you are modifying an existing plan, carefully follow the instruction, don't make unnecessary changes. Give the whole plan unless instructed to modify only one task of the plan.
        If you encounter errors on the current task, revise and output the current single task only.
        Output a list of jsons following the format:
        ```json
        [
            {
                "task_id": str = "unique identifier for a task in plan, can be an ordinal",
                "dependent_task_ids": list[str] = "ids of tasks prerequisite to this task",
                "instruction": "what you should do in this task, one short phrase or sentence",
                "task_type": "type of this task, should be one of Available Task Types",
            },
            ...
        ]
        ```
        '''
        pass
     
    @byzerllm.prompt(llm=lambda self:self.llm,render="jinja2")
    def react_think(self,user_requirement:str,context:str)->str:
        '''
        # User Requirement
        {{ user_requirement }}
        # Context
        {{ context }}

        Output a json following the format:
        ```json
        {
            "thoughts": str = "Thoughts on current situation, reflect on how you should proceed to fulfill the user requirement",
            "state": bool = "Decide whether you need to take more actions to complete the user requirement. Return true if you think so. Return false if you think the requirement has been completely fulfilled."
        }
        ```
        '''
        pass