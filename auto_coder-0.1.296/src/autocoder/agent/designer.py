import byzerllm
from autocoder.common import AutoCoderArgs
from typing import Dict
from byzerllm.utils.client import code_utils
import json
import base64
import platform
import matplotlib.font_manager as fm
from pydantic import BaseModel
class LogoDesign(BaseModel):
    selectedStyle: str
    companyName: str
    selectedBackgroundColor: str
    selectedPrimaryColor: str
    additionalInfo: str

class LogoDesigner:
    def __init__(self, args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
        self.llm = llm
        if not args.sd_model:
            raise ValueError("sd_model is not set")
        self.sd_model_llm = self.llm.get_sub_client("sd_model")
        self.args = args
        
    @byzerllm.prompt()
    def extract_logo_info(self, query: str) -> str:
        """
        根据用户的需求，抽取相关信息，生成一个LogoDesign对象。生成的信息必须使用英文，对于没有提及的信息，请
        根据你对用户需求的理解，给出合理的默认值。

        用户需求:
        我想创建一个闪亮前卫的科技公司logo，我的公司名叫做"ByteWave"，喜欢深蓝色和白色的搭配。我们是一家专注于人工智能的公司。

        LogoDesign对象示例:

        ```json
        {
            "selectedStyle": "Tech",
            "companyName": "ByteWave", 
            "selectedBackgroundColor": "white",
            "selectedPrimaryColor": "dark blue",
            "additionalInfo": "AI technology focused company"
        }
        ```

        现在请根据如下用户需求生成一个LogoDesign Json对象:

        {{ query }}
        """
    
    @byzerllm.prompt()
    def enhance_logo_generate(
        self,
        selectedStyle:str,
        companyName,
        selectedBackgroundColor,
        selectedPrimaryColor,
        additionalInfo,
    ) -> str:
        """
        A single logo, high-quality, award-winning professional design, made for both digital and print media, only contains a few vector shapes, {{ selectedStyle }}

        Primary color is {{ selectedPrimaryColor }} and background color is {{ selectedBackgroundColor }}. The company name is {{ companyName }}, make sure to include the company name in the logo. {{ "Additional info: " + additionalInfo if additionalInfo else "" }}
        """
        style_lookup = {
            "Flashy": "Flashy, attention grabbing, bold, futuristic, and eye-catching. Use vibrant neon colors with metallic, shiny, and glossy accents.",
            "Tech": "highly detailed, sharp focus, cinematic, photorealistic, Minimalist, clean, sleek, neutral color pallete with subtle accents, clean lines, shadows, and flat.",
            "Modern": "modern, forward-thinking, flat design, geometric shapes, clean lines, natural colors with subtle accents, use strategic negative space to create visual interest.",
            "Playful": "playful, lighthearted, bright bold colors, rounded shapes, lively.",
            "Abstract": "abstract, artistic, creative, unique shapes, patterns, and textures to create a visually interesting and wild logo.",
            "Minimal": "minimal, simple, timeless, versatile, single color logo, use negative space, flat design with minimal details, Light, soft, and subtle.",
        }
        return {"selectedStyle": style_lookup[selectedStyle],"additionalInfo":self.enhance_query.prompt(additionalInfo)}

    @byzerllm.prompt()
    def enhance_query(self, query: str) -> str:
        """
        你非常擅长使用文生图模型，特别能把用户简单的需求具象化。你的目标是转化用户的需求，使得转化后的
        文本更加适合问生图模型生成符合用户需求的图片。

        特别注意：
        1. 无论用户使用的是什么语言，你的改进后的表达都需要是英文。

        用户需求：
        我想设计一个偏卡通类的游戏，AGI PoLang 的游戏应用界面。

        改进后的表达：

        ```text
        Design a vibrant game app interface titled 'AGI PoLang' with a soothing blue background featuring a lush landscape of towering trees and dense bushes framing the sides.
        At the heart of the screen, elegantly display the game's name in a golden,
        playful font that captivates attention.
        Beneath this, strategically place two interactive buttons labeled 'Play Game' and 'Quit Game',
        ensuring they are both visually appealing and user-friendly.
        Center stage, introduce an engaging scene where an orange wolf stands majestically on a verdant field,
        set against a serene blue sky dotted with fluffy white clouds.
        The entire design should radiate a fun and playful atmosphere,
        encapsulating the spirit of adventure and joy that 'AGI PoLang' promises to deliver.
        ```

        用户需求：
        帮我设计一个财务报告网页页面，要时尚美观。

        改进后的表达：
        ```text
        Create a web UI page. Design a sleek and intuitive financial reports web page,
        featuring a clean menu layout, seamless navigation,
        and a comprehensive display of reports.
        The website should embody a clear and organized typography, enhancing readability and user experience.
        Incorporate dynamic lighting effects to highlight key financial data, simulating the precision and clarity of a well-managed budget.
        The overall design should reflect the stability and growth of financial health,
        serving as a visual metaphor for the solid foundation and strategic planning required in personal and corporate finance.
        ```

        用户需求：

        生成一个在自然环境中展示的防晒产品的逼真模型。产品应置于画面中心，标签清晰可见。
        将产品置于一种原始风景的背景之前，该风景包括山脉、湖泊和生动的绿色植被。
        包括花朵、石头，可能还有一两只鹿在背景中，以增强户外、新鲜的感觉。
        使用明亮的自然光照强调产品，并确保构图平衡，色彩搭配和谐，与品牌设计相得益彰。

        改进后的表达：
        ```text
        Generate a photorealistic mockup of a sunscreen product displayed in a serene natural setting.
        The product should be centered in the frame, with its label clearly visible.
        Position the product against a backdrop of a pristine landscape featuring a mountain, a lake, and vibrant greenery.
        Include natural elements like flowers, rocks, and possibly a deer or two in the background to enhance the outdoor, fresh feel.
        Use bright, natural lighting to highlight the product, and ensure the composition is balanced with a harmonious color palette
        that complements the brand's design.
        ```

        用户需求:
        一个扎着双马尾、手持棒球棒的女人，走在走廊上。灯光转变为危险的红色，营造出紧张的黑色电影风格氛围。

        改进后的表达：
        ```text
        A slow dolly-in camera follows a woman with pigtails holding a baseball bat as she walks down a dimly lit hallway.
        The lighting shifts to a menacing red, creating a tense, noir-style atmosphere with echoing footsteps adding suspense.
        ```

        现在让我们开始一个新的任务。

        用户需求：
        {{ query }}

        改进后的表达（改进后的表达请用 ```text ```进行包裹）：
        """

    def run(self, query: str):
        logo_design = self.extract_logo_info.with_llm(self.llm).with_return_type(LogoDesign).run(query)
    
        enhanced_query_str = (
            self.enhance_logo_generate.with_llm(self.llm)
            .with_extractor(lambda x: code_utils.extract_code(x)[0][1])
            .run(selectedStyle = logo_design.selectedStyle,
                 companyName = logo_design.companyName,
                 selectedBackgroundColor = logo_design.selectedBackgroundColor,
                 selectedPrimaryColor = logo_design.selectedPrimaryColor,
                 additionalInfo = logo_design.additionalInfo)
        )        
        response = self.sd_model_llm.chat_oai(
            conversations=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {"input": enhanced_query_str, "size": "1024x1024"},
                        ensure_ascii=False,
                    ),
                }
            ]
        )

        image_data = base64.b64decode(response[0].output)
        with open("output.jpg", "wb") as f:
            f.write(image_data)    

class SDDesigner:
    def __init__(self, args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
        self.llm = llm
        if not args.sd_model:
            raise ValueError("sd_model is not set")
        self.sd_model_llm = self.llm.get_sub_client("sd_model")
        self.args = args

    @byzerllm.prompt()
    def enhance_logo_generate(
        self,
        selectedStyle:str,
        companyName,
        selectedBackgroundColor,
        selectedPrimaryColor,
        additionalInfo,
    ) -> str:
        """
        A single logo, high-quality, award-winning professional design, made for both digital and print media, only contains a few vector shapes, {{ selectedStyle }}

        Primary color is {{ selectedPrimaryColor }} and background color is {{ selectedBackgroundColor }}. The company name is {{ companyName }}, make sure to include the company name in the logo. {{ "Additional info: " + additionalInfo if additionalInfo else "" }}
        """
        style_lookup = {
            "Flashy": "Flashy, attention grabbing, bold, futuristic, and eye-catching. Use vibrant neon colors with metallic, shiny, and glossy accents.",
            "Tech": "highly detailed, sharp focus, cinematic, photorealistic, Minimalist, clean, sleek, neutral color pallete with subtle accents, clean lines, shadows, and flat.",
            "Modern": "modern, forward-thinking, flat design, geometric shapes, clean lines, natural colors with subtle accents, use strategic negative space to create visual interest.",
            "Playful": "playful, lighthearted, bright bold colors, rounded shapes, lively.",
            "Abstract": "abstract, artistic, creative, unique shapes, patterns, and textures to create a visually interesting and wild logo.",
            "Minimal": "minimal, simple, timeless, versatile, single color logo, use negative space, flat design with minimal details, Light, soft, and subtle.",
        }
        return {"selectedStyle": style_lookup[selectedStyle],"additionalInfo":self.enhance_query.prompt(additionalInfo)}

    @byzerllm.prompt()
    def enhance_query(self, query: str) -> str:
        """
        你非常擅长使用文生图模型，特别能把用户简单的需求具象化。你的目标是转化用户的需求，使得转化后的
        文本更加适合问生图模型生成符合用户需求的图片。

        特别注意：
        1. 无论用户使用的是什么语言，你的改进后的表达都需要是英文。

        用户需求：
        我想设计一个偏卡通类的游戏，AGI PoLang 的游戏应用界面。

        改进后的表达：

        ```text
        Design a vibrant game app interface titled 'AGI PoLang' with a soothing blue background featuring a lush landscape of towering trees and dense bushes framing the sides.
        At the heart of the screen, elegantly display the game's name in a golden,
        playful font that captivates attention.
        Beneath this, strategically place two interactive buttons labeled 'Play Game' and 'Quit Game',
        ensuring they are both visually appealing and user-friendly.
        Center stage, introduce an engaging scene where an orange wolf stands majestically on a verdant field,
        set against a serene blue sky dotted with fluffy white clouds.
        The entire design should radiate a fun and playful atmosphere,
        encapsulating the spirit of adventure and joy that 'AGI PoLang' promises to deliver.
        ```

        用户需求：
        帮我设计一个财务报告网页页面，要时尚美观。

        改进后的表达：
        ```text
        Create a web UI page. Design a sleek and intuitive financial reports web page,
        featuring a clean menu layout, seamless navigation,
        and a comprehensive display of reports.
        The website should embody a clear and organized typography, enhancing readability and user experience.
        Incorporate dynamic lighting effects to highlight key financial data, simulating the precision and clarity of a well-managed budget.
        The overall design should reflect the stability and growth of financial health,
        serving as a visual metaphor for the solid foundation and strategic planning required in personal and corporate finance.
        ```

        用户需求：

        生成一个在自然环境中展示的防晒产品的逼真模型。产品应置于画面中心，标签清晰可见。
        将产品置于一种原始风景的背景之前，该风景包括山脉、湖泊和生动的绿色植被。
        包括花朵、石头，可能还有一两只鹿在背景中，以增强户外、新鲜的感觉。
        使用明亮的自然光照强调产品，并确保构图平衡，色彩搭配和谐，与品牌设计相得益彰。

        改进后的表达：
        ```text
        Generate a photorealistic mockup of a sunscreen product displayed in a serene natural setting.
        The product should be centered in the frame, with its label clearly visible.
        Position the product against a backdrop of a pristine landscape featuring a mountain, a lake, and vibrant greenery.
        Include natural elements like flowers, rocks, and possibly a deer or two in the background to enhance the outdoor, fresh feel.
        Use bright, natural lighting to highlight the product, and ensure the composition is balanced with a harmonious color palette
        that complements the brand's design.
        ```

        用户需求:
        一个扎着双马尾、手持棒球棒的女人，走在走廊上。灯光转变为危险的红色，营造出紧张的黑色电影风格氛围。

        改进后的表达：
        ```text
        A slow dolly-in camera follows a woman with pigtails holding a baseball bat as she walks down a dimly lit hallway.
        The lighting shifts to a menacing red, creating a tense, noir-style atmosphere with echoing footsteps adding suspense.
        ```

        现在让我们开始一个新的任务。

        用户需求：
        {{ query }}

        改进后的表达（改进后的表达请用 ```text ```进行包裹）：
        """

    def run(self, query: str):
        enhanced_query_str = (
            self.enhance_query.with_llm(self.llm)
            .with_extractor(lambda x: code_utils.extract_code(x)[0][1])
            .run(query)
        )
        print(enhanced_query_str)
        response = self.sd_model_llm.chat_oai(
            conversations=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {"input": enhanced_query_str, "size": "1024x1024"},
                        ensure_ascii=False,
                    ),
                }
            ]
        )

        image_data = base64.b64decode(response[0].output)
        with open("output.jpg", "wb") as f:
            f.write(image_data)


class SVGDesigner:
    def __init__(self, args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
        self.llm = llm
        if args.designer_model:
            self.llm = self.llm.get_sub_client("designer_model")
        self.args = args
        self.system_info = self.get_system_info()

    def get_system_info(self):
        os_name = platform.system()
        fonts = [f.name for f in fm.fontManager.ttflist]
        return {
            "os": os_name,
            "fonts": ",".join(fonts),
        }

    def run(self, query: str):

        lisp_code = (
            self._design2lisp.with_llm(self.llm)
            .with_extractor(lambda x: code_utils.extract_code(x)[0][1])
            .run(query)
        )

        print(lisp_code)
        svg_code = (
            self._lisp2svg.with_llm(self.llm)
            .with_extractor(lambda x: code_utils.extract_code(x)[0][1])
            .run(lisp_code)
        )
        print(self._lisp2svg.prompt(lisp_code))
        print(svg_code)
        self._to_png(svg_code)

    def _to_png(self, svg_code: str):
        import cairosvg

        cairosvg.svg2svg(bytestring=svg_code, write_to="output.svg")
        cairosvg.svg2png(bytestring=svg_code, write_to="output.png")

    @byzerllm.prompt()
    def _lisp2svg(self, lisp_code: str) -> str:
        """
        系统信息:
        操作系统: {{ system_info['os'] }}
        可用字体: {{ system_info['fonts'] }}

        {{ lisp_code }}

        将上面的 lisp 代码转换为 svg 代码。使用 ```svg ```包裹输出。
        注意:
        1. 根据操作系统选择合适的可用字体,优先使用系统中可用的字体。
        2. 如果指定的字体不可用,请使用系统默认的字体。
        3. 对于中英文混合的文本，请使用不同的字体。
        """
        return {
            "system_info": self.system_info,
        }

    @byzerllm.prompt()
    def _design2lisp(self, query: str) -> str:
        """
        你是一个优秀的设计师，你非常擅长把一个简单的想法用程序的表达方式来进行具象化表达，尽量丰富细节。
        充分理解用户的需求，然后得到出符合主流思维的设计的程序表达。

        用户需求：
        设计一个单词记忆卡片

        你的程序表达：
        ```lisp
        (defun 生成记忆卡片 (单词)
          "生成单词记忆卡片的主函数"
          (let* ((词根 (分解词根 单词))
                 (联想 (mapcar #'词根联想 词根))
                 (故事 (创造生动故事 联想))
                 (视觉 (设计SVG卡片 单词 词根 故事)))
            (输出卡片 单词 词根 故事 视觉)))

        (defun 设计SVG卡片 (单词 词根 故事)
          "创建SVG记忆卡片"
          (design_rule "合理使用负空间，整体排版要有呼吸感")

          (自动换行 (卡片元素
           '(单词及其翻译 词根词源解释 一句话记忆故事 故事的视觉呈现 例句)))

          (配色风格
           '(温暖 甜美 复古))

          (设计导向
           '(网格布局 简约至上 黄金比例 视觉平衡 风格一致 清晰的视觉层次)))

        (defun start ()
          "初次启动时的开场白"
          (print "请提供任意英文单词, 我来帮你记住它!"))

        ;; 使用说明：
        ;; 1. 本Prompt采用类似Emacs Lisp的函数式编程风格，将生成过程分解为清晰的步骤。
        ;; 2. 每个函数代表流程中的一个关键步骤，使整个过程更加模块化和易于理解。
        ;; 3. 主函数'生成记忆卡片'协调其他函数，完成整个卡片生成过程。
        ;; 4. 设计SVG卡片时，请确保包含所有必要元素，并遵循设计原则以创建有效的视觉记忆辅助工具。
        ;; 5. 初次启动时, 执行 (start) 函数, 引导用户提供英文单词
        ```

        用户需求：
        创建一个极简主义天才设计师AI

        你的程序表达：

        ```lisp
        (defun 极简天才设计师 ()
          "创建一个极简主义天才设计师AI"
          (list
           (专长 '费曼讲解法)
           (擅长 '深入浅出解释)
           (审美 '宋朝审美风格)
           (强调 '留白与简约)))

        (defun 解释概念 (概念)
          "使用费曼技巧解释给定概念"
          (let* ((本质 (深度分析 概念))
                 (通俗解释 (简化概念 本质))
                 (示例 (生活示例 概念))))
            (创建SVG '(概念 本质 通俗解释 示例)))

        (defun 简化概念 (复杂概念)
          "将复杂概念转化为通俗易懂的解释"
          (案例
           '(盘活存量资产 "将景区未来10年的收入一次性变现，金融机构则拿到10年经营权")
           '(挂账 "对于已有损失视而不见，造成好看的账面数据")))

        (defun 创建SVG (概念 本质 通俗解释 示例)
          "生成包含所有信息的SVG图形"
          (design_rule "合理使用负空间，整体排版要有呼吸感")
          (配色风格 '((背景色 (宋朝画作审美 简洁禅意)))
                    (主要文字 (和谐 粉笔白)))

          (设置画布 '(宽度 800 高度 600 边距 20))
          (自动缩放 '(最小字号 12))
          (设计导向 '(网格布局 极简主义 黄金比例 轻重搭配))

          (禅意图形 '(注入禅意 (宋朝画作意境 示例)))
          (输出SVG '((标题居中 概念)
                     (顶部模块 本质)
                   (中心呈现 (动态 禅意图形))
                   (周围布置 辅助元素)
                   (底部说明 通俗解释)
                   (整体协调 禅意美学))))

        (defun 启动助手 ()
          "初始化并启动极简天才设计师助手"
          (let ((助手 (极简天才设计师)))
            (print "我是一个极简主义的天才设计师。请输入您想了解的概念，我将为您深入浅出地解释并生成一张解释性的SVG图。")))

        ;; 使用方法
        ;; 1. 运行 (启动助手) 来初始化助手
        ;; 2. 用户输入需要解释的概念
        ;; 3. 调用 (解释概念 用户输入) 生成深入浅出的解释和SVG图
        ```

        用户需求：
        设计一个知行合一的设计图

        你的程序表达：

        ```lisp
        (defun 哲学家 (用户输入)
          "主函数: 模拟深度思考的哲学家，对用户输入的概念进行全方位剖析"
          (let* ((概念 用户输入)
                 (综合提炼 (深度思考 概念))
                 (新洞见 (演化思想 (突破性思考 概念 综合提炼))))
            (展示结果 概念 综合提炼 新洞见)
            (设计SVG卡片)))

        (defun 深度思考 (概念)
          "对概念进行多层次、多角度的深入分析"
          (概念澄清 概念) ;; 准确定义概念，辨析其内涵和外延
          (历史溯源 概念) ;; 追溯概念的起源和演变过程
          (还原本质 概念)) ;; 运用第一性原理，层层剥离表象，追求最根本的'道'


        (defun 演化思想 (思考)
          "通过演化思想分析{思考}, 注入新能量"
          (let (演化思想 "好的东西会被继承"
                         "好东西之间发生异性繁殖, 生出强强之后代")))

        (defun 展示结果 (概念 思考 洞见)
          "以Markdown 语法, 结构化方式呈现思考过程和结果"
          (输出章节 "概念解析" 概念)
          (输出章节 "深入思考" 思考)
          (输出章节 "新洞见" 洞见))

        (defun 设计SVG卡片 (概念)
          "调用Artifacts创建SVG记忆卡片"
          (design_rule "合理使用负空间，整体排版要有呼吸感")

          (禅意图形 '(一句话总结 概念)
                    (卡片核心对象 新洞见)
                    (可选对象 还原本质))

          (自动换行 (卡片元素 (概念 概念澄清 禅意图形)))

          (设置画布 '(宽度 800 高度 600 边距 20))
          (自动缩放 '(最小字号 12))

          (配色风格
           '((背景色 (宇宙深空 玄之又玄)))
           (主要文字 (和谐 粉笔白)))

          (设计导向 '(网格布局 极简主义 黄金比例 轻重搭配)))

        (defun start ()
          "启动时运行"
          (print "我是哲学家。请输入你想讨论的概念，我将为您分析。"))

        ;; 使用说明：
        ;; 1. 初次执行时, 运行 (start) 函数
        ;; 2. 调用(哲学家 "您的概念")来开始深度思考
        ```

        用户需求：
        设计一个 Scaling Law 才是未来的PPT片子

        你的程序表达：

        ```lisp
        (defun 沉思者 ()
          "你是一个思考者, 盯住一个东西, 往深了想"
          (写作风格 . ("Mark Twain" "鲁迅" "O. Henry"))
          (态度 . 批判)
          (精通 . 深度思考挖掘洞见)
          (表达 . (口话化 直白语言 反思质问 骂醒对方))
          (金句 . (一针见血的洞见 振聋发聩的质问)))

        (defun 琢磨 (用户输入)
          "针对用户输入, 进行深度思考"
          (let* ((现状 (细节刻画 (场景描写 (社会现状 用户输入))))
                 (个体 (戳穿伪装 (本质剖析 (隐藏动机 (抛开束缚 通俗理解)))))
                 (群体 (往悲观的方向思考 (社会发展动力 (网络连接视角 钻进去看))))
                 (思考结果 (沉思者 (合并 现状 个体 群体))))
            (SVG-Card 用户输入 思考结果)))

        (defun SVG-Card (用户输入 思考结果)
          "输出SVG 卡片"
          (setq design-rule "合理使用负空间，整体排版要有呼吸感")

          (设置画布 '(宽度 400 高度 600 边距 20))
          (自动缩放 '(最小字号 12))
          (SVG设计风格 '(蒙德里安 现代主义))

          (卡片元素
           ((居中加粗标题 (提炼一行 用户输入))
            分隔线
            (舒适字体配色 (自动换行 (分段排版 思考结果))
                          分隔线
                          (自动换行 金句)))))

        (defun start ()
          "启动时运行"
          (let ((system-role 沉思者))
            (print "请就座, 我们今天聊哪件事?")))

        ;; 运行规则
        ;; 1. 启动时必须运行 (start) 函数
        ;; 2. 之后调用主函数 (琢磨 用户输入)
        ```

        用户需求：
        {{ query }}

        你的程序表达：
        """
