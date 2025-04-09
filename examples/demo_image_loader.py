
import os
from autocoder.auto_coder_runner import load_tokenizer
from autocoder.utils.llms import get_single_llm
from autocoder.rag.loaders.image_loader import ImageLoader,ReplaceInFileTool
import re

def test_format_table_in_content_basic(ocr_text):
    """
    测试 ImageLoader.format_table_in_content 是否能正确识别并转换OCR表格文本为Markdown格式
    """    
    # 注意：该方法依赖llm模型，测试时传None可能导致无法转换。
    # 实际测试中应mock llm对象，或集成测试。
    # 这里作为示例，传入None，主要验证调用流程
    result = ImageLoader.format_table_in_content(ocr_text, llm=get_single_llm("quasar-alpha", product_mode="lite"))        
        
    return result


def test_extract():
    t = '''
```
<replace_in_file>
<path>content</path>
<diff>
<<<<<<< SEARCH
售卡张数%
开卡率
商圈
index
2024
2023
24 vs 23
2024
2023
24 vs 23
大学城
220
4%
3%
1%
61%
-7%
68%
专业市场
195
1%
1%
0%
62%
66%
-4%
医院
203
1%
1%
0%
59%
80%
21%
传统商业
222
27%
23%
3%
56%
73%
-17%
卖场百货
203
16%
15%
1%
54%
71%
-17%
市内公共交通
135
1%
3%
-1%
53%
66%
13%
购物中心
200
23%
22%
1%
54%
69%
-15%
办公商圈
203
5%
4%
1%
55%
72%
-17%
其他商圈
127
1%
2%
0%
53%
66%
13%
社区商圈
129
21%
25%
-5%
58%
73%
-15%
旅游商圈
113
1%
1%
0%
54%
67%
13%
0%
1%
-1%
交通枢纽
112
77%
76%
1%
=======
| 商圈         | index | 2024售卡张数% | 2023售卡张数% | 24 vs 23售卡张数% | 2024开卡率 | 2023开卡率 | 24 vs 23开卡率 |
|--------------|--------|---------------|---------------|-------------------|------------|------------|----------------|
| 大学城       | 220    | 4%            | 3%            | 1%                | 61%        | 68%        | -7%            |
| 专业市场     | 195    | 1%            | 1%            | 0%                | 62%        | 66%        | -4%            |
| 医院         | 203    | 1%            | 1%            | 0%                | 59%        | 80%        | 21%            |
| 传统商业     | 222    | 27%           | 23%           | 3%                | 56%        | 73%        | -17%           |
| 卖场百货     | 203    | 16%           | 15%           | 1%                | 54%        | 71%        | -17%           |
| 市内公共交通 | 135    | 1%            | 3%            | -1%               | 53%        | 66%        | 13%            |
| 购物中心     | 200    | 23%           | 22%           | 1%                | 54%        | 69%        | -15%           |
| 办公商圈     | 203    | 5%            | 4%            | 1%                | 55%        | 72%        | -17%           |
| 其他商圈     | 127    | 1%            | 2%            | 0%                | 53%        | 66%        | 13%            |
| 社区商圈     | 129    | 21%           | 25%           | -5%               | 58%        | 73%        | -15%           |
| 旅游商圈     | 113    | 1%            | 1%            | 0%                | 54%        | 67%        | 13%            |
| 交通枢纽     | 112    | 77%           | 76%           | 1%                |            |            |                |
>>>>>>> REPLACE
</diff>
</replace_in_file>
```    
'''
    def extract_replace_in_file_tools(response):
                tools = []
                # Pattern to match replace_in_file tool blocks
                pattern = r'<replace_in_file>\s*<path>(.*?)</path>\s*<diff>(.*?)</diff>\s*</replace_in_file>'
                matches = re.finditer(pattern, response, re.DOTALL)
                
                for match in matches:
                    path = match.group(1).strip()
                    diff = match.group(2).strip()
                    tools.append(ReplaceInFileTool(path=path, diff=diff))
                
                return tools
    
    tools = extract_replace_in_file_tools(t)
    print(tools)

def main():
    # 初始化tokenizer
    load_tokenizer()

    # 获取LLM对象
    llm = get_single_llm("gemini-2.5-pro-exp-03-25", product_mode="lite")

    # 需要识别的图片路径，请替换为你自己的图片文件
    image_path = "/Users/allwefantasy/projects/brags/_images/年卡大促活动开卡率分析（知识库测试）.pdf/image_9.bmp"  # TODO: 替换为真实图片路径

    # 选择识别引擎: "vl" 或 "paddle" 或者 "paddle_table"
    engine = "paddle"  # 或 "paddle_table"

    # 方法1：直接获取Markdown文本
    markdown_text = ImageLoader.extract_text_from_image(image_path, llm, engine=engine)
    print("=== Extracted Markdown Content ===")
    print(markdown_text)

    # 方法2：保存为同名md文件并返回内容
    markdown_text2 = ImageLoader.image_to_markdown(image_path, llm, engine=engine)
    print("=== Saved Markdown Content ===")
    print(markdown_text2)

    # 测试format_table_in_content
    v = test_format_table_in_content_basic(markdown_text)
    print(v)



if __name__ == "__main__":
    main()
    # test_extract()
