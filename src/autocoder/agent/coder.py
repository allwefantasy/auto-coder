import byzerllm
from pydantic import BaseModel,Field

class ReactThink(BaseModel):
    thoughts:str = Field(...,description="Thoughts on current situation, reflect on how you should proceed to fulfill the user requirement")
    state: bool = Field(...,description="Decide whether you need to take more actions to complete the user requirement. Return true if you think so. Return false if you think the requirement has been completely fulfilled.")
        
class Coder:
    def __init__(self,llm:byzerllm.ByzerLLM) -> None:
        self.llm = llm 
        self.memory = []

    @byzerllm.prompt(llm=lambda self:self.llm)
    def react_think(self,user_requirement:str, context:str)->ReactThink:
        '''
        # User Requirement
        {user_requirement}
        
        # Context
        {context}
        '''
    
    def run(self,with_message):
        pass