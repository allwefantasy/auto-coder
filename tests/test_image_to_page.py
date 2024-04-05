import unittest
import byzerllm
import os
import base64
import json
from autocoder.common.image_to_page import ImageToPage
from autocoder.common import AutoCoderArgs

class TestImageToPage(unittest.TestCase):
    def setUp(self):
        byzerllm.connect_cluster()
        self.model = "qianwen_chat"
        # self.model = "sparkdesk_chat"
        self.llm = byzerllm.ByzerLLM()  
        self.llm.setup_default_model_name(self.model)
        self.llm.setup_template(self.model,"auto")

        vl_model = byzerllm.ByzerLLM()  
        # yi_vl_chat
        # qianwen_vl_chat
        vl_model.setup_default_model_name("qianwen_vl_chat")
        vl_model.setup_template("qianwen_vl_chat","auto")

        self.llm.setup_sub_client("vl_model",vl_model)

        self.image_to_page = ImageToPage(self.llm,args=AutoCoderArgs(source_dir="",anti_quota_limit=4))    

    def test_run_then_iterate(self):
        self.image_to_page.run_then_iterate(
            origin_image="/Users/allwefantasy/projects/auto-coder/screenshots/www_elmo_chat.png",
            html_path="/Users/allwefantasy/projects/auto-coder/screenshots/www_elmo_chat.html",            
        )

if __name__ == "__main__":
    unittest.main()