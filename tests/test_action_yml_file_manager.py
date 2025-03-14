import os
import tempfile
import shutil
import unittest
import yaml
from autocoder.common.action_yml_file_manager import ActionYmlFileManager


class TestActionYmlFileManager(unittest.TestCase):
    def setUp(self):
        # 创建临时测试目录
        self.test_dir = tempfile.mkdtemp()
        self.actions_dir = os.path.join(self.test_dir, "actions")
        os.makedirs(self.actions_dir, exist_ok=True)
        self.action_manager = ActionYmlFileManager(self.test_dir)
        
        # 创建一些测试 YAML 文件
        self.test_files = [
            {
                "name": "000000000001_test1.yml",
                "content": {
                    "query": "Test query 1",
                    "urls": ["/src/test1.py", "/src/test2.py"]
                }
            },
            {
                "name": "000000000002_test2.yml",
                "content": {
                    "query": "Test query 2",
                    "urls": ["/src/test3.py", "/src/test4.py"]
                }
            },
            {
                "name": "000000000003_test3.yml",
                "content": {
                    "query": "Test query 3",
                    "urls": ["/src/test5.py", "/src/test6.py"]
                }
            }
        ]
        
        # 写入测试文件
        for file_info in self.test_files:
            file_path = os.path.join(self.actions_dir, file_info["name"])
            with open(file_path, "w") as f:
                yaml.dump(file_info["content"], f)
    
    def tearDown(self):
        # 清理临时目录
        shutil.rmtree(self.test_dir)
    
    def test_get_action_files(self):
        # 测试获取所有 action 文件
        files = self.action_manager.get_action_files()
        self.assertEqual(len(files), 3)
        
        # 测试带前缀过滤
        files = self.action_manager.get_action_files(filter_prefix="00000000000")
        self.assertEqual(len(files), 3)
        
        files = self.action_manager.get_action_files(filter_prefix="000000000001")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "000000000001_test1.yml")
    
    def test_get_sequence_number(self):
        # 测试获取序号
        self.assertEqual(self.action_manager.get_sequence_number("000000000001_test1.yml"), 1)
        self.assertEqual(self.action_manager.get_sequence_number("000000000002_test2.yml"), 2)
        self.assertEqual(self.action_manager.get_sequence_number("invalid_name.yml"), 0)
    
    def test_get_latest_action_file(self):
        # 测试获取最新 action 文件
        latest = self.action_manager.get_latest_action_file()
        self.assertEqual(latest, "000000000003_test3.yml")
        
        # 测试带前缀过滤
        latest = self.action_manager.get_latest_action_file(filter_prefix="000000000002")
        self.assertEqual(latest, "000000000002_test2.yml")
    
    def test_get_next_sequence_number(self):
        # 测试获取下一个序号
        next_seq = self.action_manager.get_next_sequence_number()
        self.assertEqual(next_seq, 4)
    
    def test_load_and_save_yaml_content(self):
        # 测试加载 YAML 内容
        content = self.action_manager.load_yaml_content("000000000001_test1.yml")
        self.assertEqual(content["query"], "Test query 1")
        self.assertEqual(content["urls"], ["/src/test1.py", "/src/test2.py"])
        
        # 测试更新 YAML 内容
        content["new_field"] = "test value"
        result = self.action_manager.save_yaml_content("000000000001_test1.yml", content)
        self.assertTrue(result)
        
        # 验证更新后的内容
        updated_content = self.action_manager.load_yaml_content("000000000001_test1.yml")
        self.assertEqual(updated_content["new_field"], "test value")
    
    def test_update_yaml_field(self):
        # 测试更新特定字段
        result = self.action_manager.update_yaml_field(
            "000000000002_test2.yml", 
            "updated_field", 
            "updated value"
        )
        self.assertTrue(result)
        
        # 验证更新后的字段
        content = self.action_manager.load_yaml_content("000000000002_test2.yml")
        self.assertEqual(content["updated_field"], "updated value")
        
    def test_create_next_action_file(self):
        # 测试创建下一个 action 文件
        new_file = self.action_manager.create_next_action_file("test4")
        self.assertTrue(os.path.exists(new_file))
        
        # 验证文件名格式
        file_name = os.path.basename(new_file)
        self.assertTrue(file_name.startswith("000000000004_"))
        self.assertTrue(file_name.endswith("_test4.yml"))
        
        # 测试带内容创建
        content = "test_content: test_value\n"
        new_file2 = self.action_manager.create_next_action_file("test5", content=content)
        self.assertTrue(os.path.exists(new_file2))
        
        with open(new_file2, "r") as f:
            file_content = f.read()
        self.assertEqual(file_content, content)


if __name__ == "__main__":
    unittest.main() 