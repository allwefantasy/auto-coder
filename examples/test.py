from autocoder.utils.llms import get_single_llm
import byzerllm
llm = get_single_llm("ark_v3_0324_chat", product_mode="lite")

@byzerllm.prompt()
def hello()->str:
    '''
    你好
    '''

print(hello.with_llm(llm).run()) 


import openai


