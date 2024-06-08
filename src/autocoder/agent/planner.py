from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from byzerllm.apps.llama_index.byzerai import ByzerAI
import byzerllm

@byzerllm.prompt()
def coder():
    '''
    coder 主要撰写 autocoder yaml 文件。
    '''

class Planner:
    def __init__(self,llm: byzerllm.ByzerLLM):  
        self.llm = llm      
        coder_tool = FunctionTool.from_defaults(coder)
        self.tools = {"coder":coder_tool}

    def run(self, query: str):
        agent = ReActAgent.from_tools(
            tools=self.tools.values(),
            llm=ByzerAI(llm=self.llm),
            verbose=True,
            max_iterations=query.max_iterations,
            context=query.react_context,
        )
