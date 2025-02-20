import byzerllm
from byzerllm.utils.client import code_utils
from PIL import Image
import base64
import json
import os
import time
from autocoder.common.screenshots import gen_screenshots,ImageSize
from autocoder.common import AutoCoderArgs
from autocoder.common.code_auto_merge import CodeAutoMerge
from loguru import logger

class ImageToPageDirectly:
    def __init__(self,llm:byzerllm.ByzerLLM,args:AutoCoderArgs):        
        self.llm = llm
        self.vl_model = llm.get_sub_client("vl_model")
        if not self.vl_model:
            raise Exception("vl_model is required by  ImageToPage")

        self.args = args

    @byzerllm.prompt()
    def system_prompt(self):
        '''
        You are an expert Tailwind developer
        You take screenshots of a reference web page from the user, and then build single page apps 
        using Tailwind, HTML and JS.
        You might also be given a screenshot(The second image) of a web page that you have already built, and asked to
        update it to look more like the reference image(The first image).

        - Make sure the app looks exactly like the screenshot.
        - Pay close attention to background color, text color, font size, font family, 
        padding, margin, border, etc. Match the colors and sizes exactly.
        - Use the exact text from the screenshot.
        - Do not add comments in the code such as "<!-- Add other navigation links as needed -->" and "<!-- ... other news items ... -->" in place of writing the full code. WRITE THE FULL CODE.
        - Repeat elements as needed to match the screenshot. For example, if there are 15 items, the code should have 15 items. DO NOT LEAVE comments like "<!-- Repeat for each news item -->" or bad things will happen.
        - For images, use placeholder images from https://placehold.co and include a detailed description of the image in the alt text so that an image generation AI can generate the image later.

        In terms of libraries,

        - Use this script to include Tailwind: <script src="https://cdn.tailwindcss.com"></script>
        - You can use Google Fonts
        - Font Awesome for icons: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css"></link>

        Return only the full code in <html></html> tags.
        Do not include markdown "```" or "```html" at the start or end.
        ''' 

    def generate_html_directly(self,img_path:str,image_size:ImageSize)->str:
        image_path_ext = os.path.splitext(img_path)[1]
        with open(img_path, 'rb') as image_file:
            image = base64.b64encode(image_file.read()).decode('utf-8')
            image = f"data:image/{image_path_ext};base64,{image}"
        t = self.vl_model.chat_oai(conversations=[{
            "role":"system",
            "content": self.system_prompt.prompt()
            },
            {
            "role":"user",
            "content":json.dumps([{
                "image":image,
                "detail":"high",
                "text":f"Generate code for a web page that looks exactly like this(the image size is {image_size.DH}x{image_size.DW})."
            }],ensure_ascii=False)
        }])
        html = t[0].output
        return html
    
    @byzerllm.prompt()
    def update_prompt(self,html:str)->str:
        '''
        Here is HTML/Tailwind code for the second image:

        ```html
        {{ html }}
        ```

        Update the code for the second image to look more like the first image.
        Return only the full code in <html></html> tags.
        Do not include markdown "```" or "```html" at the start or end.
        '''

    def update_html_directly(self,origin_image:str,new_image:str,html:str)->str:
        
        with open(origin_image, 'rb') as image_file:
            origin_image = base64.b64encode(image_file.read()).decode('utf-8')
        with open(new_image, 'rb') as image_file:
            new_image = base64.b64encode(image_file.read()).decode('utf-8') 

        t = self.vl_model.chat_oai(conversations=[{
            "role":"system",
            "content": self.system_prompt.prompt()
            },
            {
            "role":"user",
            "content":json.dumps([{
                "image":origin_image,
                "detail":"high"
            },{
                "image":new_image,    
                "detail":"high"
            },
            {
                "text":self.update_prompt.prompt(html=html)
            }],ensure_ascii=False)
        }])
        html = t[0].output
        return html

    def run_then_iterate(self,origin_image:str,html_path:str,max_iter:int=1):

        with Image.open(origin_image) as ori_img:        
            width, height = ori_img.size                        
            image_size = ImageSize(DW=width,DH=height)        
        
        html = self.generate_html_directly(origin_image,image_size=image_size)                         
        
        origin_image_file_name = os.path.splitext(os.path.basename(origin_image))[0]
        html_file_name = os.path.splitext(os.path.basename(html_path))[0]
        html_dir = os.path.dirname(html_path)
        os.makedirs(html_dir, exist_ok=True)   

        counter = 1 
        target_html_path = os.path.join(html_dir,f"{html_file_name}-{counter}.html") 
        with open(target_html_path, "w",encoding="utf-8") as f:
            f.write(html)               
        
        while counter < max_iter:
            logger.info(f"iterate  {counter}/{max_iter}....")
            new_image_dir = os.path.join(os.path.dirname(origin_image),"images",f"{origin_image_file_name}-{counter}")
            os.makedirs(new_image_dir, exist_ok=True)              
            gen_screenshots(url=html_path,image_dir=new_image_dir,image_size=image_size)        
            file_name = os.path.splitext(os.path.basename(html_path))[0]            
            new_image = os.path.join(new_image_dir,f"{file_name}.png")  
            html = self.update_html_directly(origin_image,new_image,html=html)
            counter += 1
            
            target_html_path = os.path.join(html_dir,f"{html_file_name}-{counter}.html")
            logger.info(f"generate html: {target_html_path}")                
            with open(target_html_path, "w",encoding="utf-8") as f:
                f.write(html)            
        
        logger.info(f"finally generate html: {html_path}")
        with open(html_path, "w",encoding="utf-8") as f:
            f.write(html)    
             

class ImageToPage:
    
    def __init__(self,llm:byzerllm.ByzerLLM,args:AutoCoderArgs):        
        self.llm = llm
        self.vl_model = llm.get_sub_client("vl_model")
        if not self.vl_model:
            raise Exception("vl_model is required by  ImageToPage")

        self.args = args    
            
    def desc_image(self,img_path:str):   
        image_path_ext = os.path.splitext(img_path)[1]
        with open(img_path, 'rb') as image_file:
            image = base64.b64encode(image_file.read()).decode('utf-8')
            image = f"data:image/{image_path_ext};base64,{image}"
        t = self.vl_model.chat_oai(conversations=[{
            "role":"user",
            "content":json.dumps([{
                "image":image,
                "text":"这是一张网页截图,请描述该网页的布局结构,对于每个元素，请描述它位于页面所在的相对位置，大小，颜色。最后对网页整体特点做个总结。注意，不要吝啬词汇，尽量描述详细。"
            }],ensure_ascii=False)
        }])
        return t[0].output
    
    @byzerllm.prompt()
    def generate_html(self,desc:str,html_path:str)->str:
        '''
        下面是对一张网页的描述：

        {{ desc }}

        请根据上述描述，生成对应的HTML代码，对应的文件路径为: {{ html_path }} ,你生成的代码要符合这个格式：
    
        ```{lang}
        ##File: {FILE_PATH}
        {CODE}
        ```    

        其中，{lang}是代码的语言，{CODE}是HTML部分,{FILE_PATH} 是文件路径部分，他们都在代码块中，请严格按上面的格式进行内容生成。
        '''       

    
    @byzerllm.prompt()
    def get_optimize(self,desc:str)->str:
        '''
        根据下面的描述，为了让B页面更加趋近A页面，请描述B需要做出的调整：

        {{ desc }}
        '''

    @byzerllm.prompt()
    def optimize_html(self,desc:str,html:str,html_path:str)->str:
        '''
        ## HTML/CSS

        {{ html }}

        ## 需求

        {{ desc }}
        

        请根据需求修改上述 HTML/CSS，对应的文件路径为: {{ html_path }} ,你新生成的HTML代码要符合这个格式：
    
        ```{lang}
        ##File: {FILE_PATH}
        {CODE}
        ```    

        其中，{lang}是代码的语言，{CODE}是HTML部分,{FILE_PATH} 是文件路径部分，他们都在代码块中，请严格按上面的格式进行内容生成。
        '''    

    def score(self,origin_image:str,new_image:str):
        with open(origin_image, 'rb') as image_file:
            origin_image = base64.b64encode(image_file.read()).decode('utf-8')
        with open(new_image, 'rb') as image_file:
            new_image = base64.b64encode(image_file.read()).decode('utf-8')        
        return self.vl_model.chat_oai(conversations=[{
            "role":"user",
            "content":json.dumps([{
                "image":origin_image,                
            },{
                "image":new_image,                
            },
                {
                "text":"请描述第一张图片（后面都叫A）和第二张图片（后面我们叫B）的差异。尤其是布局结构的差异。",                
            }],ensure_ascii=False)
        }])[0].output 

    def write_code(self,code:str,file_path:str):
    
        file_modified_num = 0
        auto_merge = CodeAutoMerge(self.llm,self.args)
                
        codes =  code_utils.extract_code(code)

        for (lang,code) in codes:            
            parsed_blocks = auto_merge.parse_text(code)

            for block in parsed_blocks:
                file_path = block.path
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, "w",encoding="utf-8") as f:
                    logger.info(f"Upsert path: {file_path}")                                       
                    f.write(block.content)
                    file_modified_num += 1

        return file_modified_num            

    def run_then_iterate(self,origin_image:str,html_path:str,max_iter:int=1):

        extra_llm_config = {}        
        if self.args.human_as_model:
            extra_llm_config["human_as_model"] = True


        desc = self.desc_image(origin_image)
        logger.info(f"desc image: {origin_image} {desc}")

        ## generate html by image description        
        content_contains_html_prompt = self.generate_html.prompt(desc,html_path) 

        with open(self.args.target_file, "w",encoding="utf-8") as f:
            f.write(content_contains_html_prompt) 

        t = self.llm.chat_oai(conversations=[{
            "role":"user",
            "content":content_contains_html_prompt
        }],llm_config={**extra_llm_config})

        content_contains_html = t[0].output 

        with open(self.args.target_file, "w",encoding="utf-8") as f:
            f.write(content_contains_html)
        
        
        file_modified_num = self.write_code(content_contains_html,html_path)
        if file_modified_num == 0:
            logger.info(f"The html generated may not be correct, here is the prompt:\n {self.generate_html.prompt(desc,html_path)} \n\n result: \n {content_contains_html}")
            return
                
        logger.info(f"generate html: {html_path}")
        
        
        new_image_dir = os.path.join(os.path.dirname(origin_image),"new")
        os.makedirs(new_image_dir, exist_ok=True)
               

        for i in range(max_iter):
            logger.info(f"iterate  {i}")
            with open(html_path,"r",encoding="utf-8") as f:
                prev_html = f.read()

            gen_screenshots(url=html_path,image_dir=new_image_dir)        
            
            file_name = os.path.splitext(os.path.basename(html_path))[0]            
            new_image = os.path.join(new_image_dir,f"{file_name}.png")  

            logger.info(f"generate image from html: {html_path}  to {new_image}")

            ## get new description prompt by comparing old and new image
            new_desc_prompt = self.get_optimize(self.score(origin_image,new_image))

            with open(self.args.target_file, "w",encoding="utf-8") as f:
                f.write(new_desc_prompt) 

            t = self.llm.chat_oai(conversations=[{
                "role":"user",
                "content":new_desc_prompt
            }],llm_config={**extra_llm_config})

            new_desc = t[0].output 

            with open(self.args.target_file, "w",encoding="utf-8") as f:
                f.write(new_desc)            

            logger.info(f"score old/new image: {new_desc}")

            ## generate new html by new description
            optimze_html_prompt =  self.optimize_html.prompt(desc=new_desc,html=prev_html,html_path=html_path)                                    
            
            with open(self.args.target_file, "w",encoding="utf-8") as f:
                f.write(optimze_html_prompt) 

            t = self.llm.chat_oai(conversations=[{
                "role":"user",
                "content":optimze_html_prompt
            }],llm_config={**extra_llm_config}) 
            new_code = t[0].output
            
            with open(self.args.target_file, "w",encoding="utf-8") as f:
                f.write(new_code) 

            self.write_code(new_code,html_path)
            logger.info(f"generate new html: {html_path}")
            time.sleep(self.args.anti_quota_limit)
            


        return html_path    
            


        