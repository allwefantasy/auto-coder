import unittest
import byzerllm
from autocoder.common import AutoCoderArgs
from autocoder.agent.planner import Planner, get_tools
from autocoder.utils.tests import get_llm

class TestPlanner(unittest.TestCase):
    def setUp(self):
        args = AutoCoderArgs(
            project_type="py",
            source_dir="/Users/allwefantasy/projects/auto-coder",
            target_file="/Users/allwefantasy/projects/auto-coder/output.txt",
            model="deepseek_chat",
            human_as_model=False,
            emb_model="gpt_emb",
            ray_address="auto"
        )
        llm = get_llm(args)        
        self.planner = Planner(args, llm)

    def test_get_project_related_files(self):
        tools = get_tools(args=self.planner.args, llm=self.planner.llm)
        for tool in tools:
            if tool.metadata.name == "get_project_related_files":
                result = tool.fn("query")
                self.assertIsNotNone(result)
                self.assertTrue(isinstance(result, str))
                break

    def test_generate_auto_coder_yaml(self):
        tools = get_tools(args=self.planner.args, llm=self.planner.llm)
        for tool in tools:
            if tool.metadata.name == "generate_auto_coder_yaml":
                result = tool.fn("yaml_file_name", "yaml_str")
                self.assertIsNotNone(result)
                self.assertTrue(isinstance(result, str))
                break

    def test_get_auto_coder_knowledge(self):
        tools = get_tools(args=self.planner.args, llm=self.planner.llm)
        for tool in tools:
            if tool.metadata.name == "get_auto_coder_knowledge":
                result = tool.fn("query")
                self.assertIsNotNone(result)
                self.assertTrue(isinstance(result, str))
                break
