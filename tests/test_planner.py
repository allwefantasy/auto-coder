import unittest
import byzerllm
from autocoder.common import AutoCoderArgs
from autocoder.agent.planner import Planner, get_tools

class TestPlanner(unittest.TestCase):
    def setUp(self):
        args = AutoCoderArgs(
            project_type="py",
            source_dir="/Users/allwefantasy/projects/auto-coder",
            model="deepseek_chat",
            human_as_model=False,
        )
        llm = byzerllm.ByzerLLM.from_default_model(model=args.model)
        self.planner = Planner(args, llm)

    def test_get_project_related_files(self):
        tools = get_tools(args=self.planner.args, llm=self.planner.llm)
        for tool in tools:
            if tool.name == "get_project_related_files":
                result = tool.run("query")
                self.assertIsNotNone(result)
                self.assertTrue(isinstance(result, str))
                break

    def test_generate_auto_coder_yaml(self):
        tools = get_tools(args=self.planner.args, llm=self.planner.llm)
        for tool in tools:
            if tool.name == "generate_auto_coder_yaml":
                result = tool.run("yaml_file_name", "yaml_str")
                self.assertIsNotNone(result)
                self.assertTrue(isinstance(result, str))
                break

    def test_get_auto_coder_knowledge(self):
        tools = get_tools(args=self.planner.args, llm=self.planner.llm)
        for tool in tools:
            if tool.name == "get_auto_coder_knowledge":
                result = tool.run("query")
                self.assertIsNotNone(result)
                self.assertTrue(isinstance(result, str))
                break

if __name__ == "__main__":
    unittest.main()