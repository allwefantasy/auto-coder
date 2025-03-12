from typing import List, Dict, Any, Tuple, Optional
import os
import yaml
from loguru import logger
import byzerllm
import pydantic
import git
from rich.console import Console
from rich.panel import Panel
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText
from rich.console import Console


class NextQuery(pydantic.BaseModel):
    """下一个开发任务的描述和相关信息"""
    query: str = pydantic.Field(description="任务需求描述")
    urls: List[str] = pydantic.Field(description="预测可能需要修改的文件路径列表")
    priority: int = pydantic.Field(description="任务优先级，1-5，5为最高优先级")
    reason: str = pydantic.Field(description="为什么需要这个任务，以及为什么需要修改这些文件")
    dependency_queries: List[str] = pydantic.Field(description="依赖的历史任务列表", default_factory=list)


def load_yaml_config(yaml_file: str) -> Dict:
    """加载YAML配置文件"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading yaml file {yaml_file}: {str(e)}")
        return {}


class AutoGuessQuery:
    def __init__(self, llm: byzerllm.ByzerLLM,
                 project_dir: str,
                 skip_diff: bool = False,
                 file_size_limit: int = 100):
        """
        初始化 AutoGuessQuery

        Args:
            llm: ByzerLLM 实例，用于生成下一步任务预测
            project_dir: 项目根目录
            skip_diff: 是否跳过获取 diff 信息
            file_size_limit: 最多分析多少历史任务
        """
        self.project_dir = project_dir
        self.actions_dir = os.path.join(project_dir, "actions")
        self.llm = llm
        self.file_size_limit = file_size_limit
        self.skip_diff = skip_diff

    @byzerllm.prompt()
    def guess_next_query(self, querie_with_urls: List[Tuple[str, List[str], str]], task_limit_size: int = 5) -> str:
        """
        根据历史开发任务，预测接下来可能的多个开发任务，按照可能性从高到低排序。

        输入数据格式：
        querie_with_urls 包含多个历史任务信息，每个任务由以下部分组成：
        1. query: 任务需求描述
        2. urls: 修改的文件路径列表
        3. diff: Git diff信息，展示具体的代码修改

        示例数据：
        <queries>
        {% for query,urls,diff in querie_with_urls %}
        ## {{ query }}        

        修改的文件:
        {% for url in urls %}
        - {{ url }}
        {% endfor %}
        {% if diff %}

        代码变更:
        ```diff
        {{ diff }}
        ```
        {% endif %}        
        {% endfor %}
        </queries>

        分析要求：
        1. 分析历史任务的模式和规律
           - 功能演进路径：项目功能是如何逐步完善的
           - 代码变更模式：相似功能通常涉及哪些文件
           - 依赖关系：新功能和已有功能的关联
           
        2. 预测可能的任务时考虑：
           - 完整性：现有功能是否有待完善的地方
           - 扩展性：是否需要支持新的场景
           - 健壮性：是否需要增加容错和异常处理
           - 性能：是否有性能优化空间
           - 交互性：是否需要改善用户体验
           - 可维护性：是否需要重构或优化代码结构

        返回格式说明：
        返回一个JSON数组，数组中每个元素是一个NextQuery对象，按照可能性从高到低排序。每个对象包含：
        1. query: 任务的具体描述
        2. urls: 预计需要修改的文件列表
        3. priority: 优先级(1-5)
        4. reason: 为什么建议这个任务
        5. dependency_queries: 相关的历史任务列表

        示例返回：
        [
            {
                "query": "添加任务预测的单元测试",
                "urls": ["tests/test_auto_guess_query.py"],
                "priority": 5,
                "reason": "确保任务预测功能的正确性和稳定性对项目质量至关重要",
                "dependency_queries": ["实现任务预测功能"]
            },
            {
                "query": "优化向量搜索性能",
                "urls": ["src/autocoder/utils/search.py"],
                "priority": 4,
                "reason": "当前搜索速度较慢，需要添加向量索引提升性能",
                "dependency_queries": ["实现向量搜索基础功能"]
            }
        ]

        注意：
        1. 每个预测的任务都应该具体且可执行，而不是抽象的目标
        2. 文件路径预测应该基于已有文件的实际路径
        3. reason应该详细解释为什么这个任务重要，以及为什么需要修改这些文件
        4. priority的指定需要考虑任务的紧迫性和重要性
        3. 建议返回最多{{ task_limit_size }}个不同优先级的任务，覆盖不同的改进方向
        """
        pass

    def parse_history_tasks(self) -> List[Dict]:
        """
        解析历史任务信息

        Returns:
            List[Dict]: 每个字典包含一个历史任务的信息
        """
        # 获取所有YAML文件
        action_files = [
            f for f in os.listdir(self.actions_dir)
            if f[:3].isdigit() and "_" in f and f.endswith('.yml')
        ]

        # 按序号排序
        def get_seq(name):
            return int(name.split("_")[0])

        # 获取最新的action文件列表
        action_files = sorted(action_files, key=get_seq)
        action_files.reverse()

        action_files = action_files[:self.file_size_limit]

        querie_with_urls_and_diffs = []
        repo = git.Repo(self.project_dir)

        # 收集所有query、urls和对应的commit diff
        for yaml_file in action_files:
            yaml_path = os.path.join(self.actions_dir, yaml_file)
            config = load_yaml_config(yaml_path)

            if not config:
                continue

            query = config.get('query', '')
            urls = config.get('urls', [])

            if query and urls:
                commit_diff = ""
                if not self.skip_diff:
                    # 计算文件的MD5用于匹配commit
                    import hashlib
                    file_md5 = hashlib.md5(open(yaml_path, 'rb').read()).hexdigest()
                    response_id = f"auto_coder_{yaml_file}_{file_md5}"
                    # 查找对应的commit                   
                    try:
                        for commit in repo.iter_commits():
                            if response_id in commit.message:
                                if commit.parents:
                                    parent = commit.parents[0]
                                    commit_diff = repo.git.diff(
                                        parent.hexsha, commit.hexsha)
                                else:
                                    commit_diff = repo.git.show(commit.hexsha)
                                break
                    except git.exc.GitCommandError as e:
                        logger.error(f"Git命令执行错误: {str(e)}")
                    except Exception as e:
                        logger.error(f"获取commit diff时出错: {str(e)}")

                querie_with_urls_and_diffs.append((query, urls, commit_diff))

        return querie_with_urls_and_diffs

    def predict_next_tasks(self, task_limit_size: int = 5, is_human_as_model: bool = False) -> Optional[List[NextQuery]]:
        """
        预测接下来可能的开发任务列表，按照可能性从高到低排序

        Args:
            task_limit_size: 返回的任务数量限制，默认5个
            is_human_as_model: 是否人工模式，如果为True则输出prompt供人工编写结果

        Returns:
            List[NextQuery]: 预测的任务列表，如果预测失败则返回None
        """
        history_tasks = self.parse_history_tasks()
        
        if not history_tasks:
            logger.warning("No history tasks found")
            return None

        try:
            if is_human_as_model:                          
                console = Console()
                
                # 生成prompt
                prompt_content = self.guess_next_query.prompt(
                    querie_with_urls=history_tasks,
                    task_limit_size=task_limit_size
                )
                
                try:
                    import pyperclip
                    pyperclip.copy(prompt_content)
                    console.print(
                        Panel(
                            "The prompt has been copied to clipboard. Please paste it into the LLM and input the response below.",
                            title="Instructions",
                            border_style="blue",
                            expand=False,
                        )
                    )
                except Exception:
                    logger.warning("Clipboard not supported")
                    console.print(
                        Panel(
                            "The prompt could not be copied to clipboard. Please manually copy the following content:",
                            title="Instructions",
                            border_style="blue",
                            expand=False,
                        )
                    )
                    console.print(prompt_content)
                
                lines = []
                while True:
                    line = prompt(FormattedText([("#00FF00", "> ")]), multiline=False)
                    line_lower = line.strip().lower()
                    if line_lower in ["eof", "/eof"]:
                        break
                    elif line_lower in ["/clear"]:
                        lines = []
                        print("\033[2J\033[H")  # Clear terminal screen
                        continue
                    elif line_lower in ["/break"]:
                        raise Exception("User requested to break the operation.")
                    lines.append(line)
                
                result = "\n".join(lines)
                
                # 从输入中抽取JSON字符串并解析
                from byzerllm.utils.client import code_utils
                import json
                
                try:
                    json_str = code_utils.extract_code(result)[0][1]
                    task_list = json.loads(json_str)
                    return [NextQuery(**task) for task in task_list]
                except Exception as e:
                    logger.error(f"Error parsing input: {str(e)}")
                    return None
            else:
                result = self.guess_next_query.with_llm(self.llm).with_return_type(NextQuery).run(
                    querie_with_urls=history_tasks,
                    task_limit_size=task_limit_size
                )
                return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error predicting next task: {str(e)}")
            return None