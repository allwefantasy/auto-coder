from autocoder.rag.cache.base_cache import BaseCacheManager
from typing import Dict, List, Any, Optional, Union
import os
import threading
from loguru import logger
from watchfiles import watch, Change
from autocoder.rag.variable_holder import VariableHolder
from autocoder.common import SourceCode
from autocoder.rag.utils import process_file_in_multi_process, process_file_local
from watchfiles import Change, DefaultFilter, awatch, watch
from byzerllm import SimpleByzerLLM, ByzerLLM
from autocoder.common import AutoCoderArgs


class AutoCoderRAGDocListener(BaseCacheManager):
    """
    基于文件系统实时监控的代码缓存管理器。

    此类实现了对代码库的实时监控，当文件发生变化时（新增、修改、删除）自动更新缓存。
    与其他缓存管理器不同，它使用 watchfiles 库进行文件变更监控，无需定期扫描文件系统。

    类属性:
        cache: 缓存字典，存储处理后的文件内容
        ignore_dirs: 需要忽略的目录列表
        ignore_entity_patterns: 需要忽略的文件模式列表
    """
    cache: Dict[str, Dict] = {}
    ignore_dirs = [
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".venv",
        ".cache",
        ".idea",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".hypothesis",
    ]
    ignore_entity_patterns = [
        r"\.py[cod]$",
        r"\.___jb_...___$",
        r"\.sw.$",
        "~$",
        r"^\.\#",
        r"^\.DS_Store$",
        r"^flycheck_",
        r"^test.*$",
    ]

    def __init__(self, path: str, ignore_spec, required_exts: List, args: Optional[AutoCoderArgs] = None, llm: Optional[Union[ByzerLLM, SimpleByzerLLM, str]] = None) -> None:
        """
        初始化文件监控缓存管理器。

        参数:
            path: 需要监控的代码库根目录
            ignore_spec: 指定哪些文件/目录应被忽略的规则
            required_exts: 需要处理的文件扩展名列表

        缓存结构 (self.cache):
            self.cache 是一个字典，其结构比其他缓存管理器更简单:
            {
                "file_path1": {                  # 键为文件的绝对路径
                    "file_path": str,            # 文件的绝对路径
                    "content": List[Dict],       # 文件内容的结构化表示，每个元素是 SourceCode 对象的序列化
                },
                "file_path2": { ... },
                ...
            }

            与其他缓存管理器的主要区别:
            1. 不需要存储 MD5 哈希或修改时间，因为文件变更通过监控系统直接获取
            2. 没有本地持久化机制，所有缓存在内存中维护
            3. 缓存更新基于事件驱动，而非定期扫描

        文件监控机制:
            - 使用 watchfiles 库监控文件系统变更
            - 支持三种事件类型: 添加(added)、修改(modified)、删除(deleted)
            - 使用单独线程进行监控，不阻塞主线程
            - 监控遵循配置的忽略规则和所需扩展名过滤
            - 初始化时会先加载所有符合条件的文件

        源代码处理:
            使用 process_file_local 函数处理单个文件:
            - 参数: file_path (文件路径)
            - 返回值: List[SourceCode]
            - 文件处理后，直接更新内存中的缓存
        """
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.args = args
        self.llm = llm
        self.stop_event = threading.Event()

        # connect list
        self.ignore_entity_patterns.extend(self._load_ignore_file())
        self.file_filter = DefaultFilter(
            ignore_dirs=self.ignore_dirs,
            ignore_paths=[],
            ignore_entity_patterns=self.ignore_entity_patterns,
        )
        self.load_first()
        # 创建一个新线程来执行open_watch
        self.watch_thread = threading.Thread(target=self.open_watch)
        # 将线程设置为守护线程,这样主程序退出时,这个线程也会自动退出
        self.watch_thread.daemon = True
        # 启动线程
        self.watch_thread.start()

    def stop(self):
        """
        停止文件监控线程。

        设置停止事件并等待监控线程结束，用于在对象销毁前优雅地关闭监控。
        """
        self.stop_event.set()
        self.watch_thread.join()

    def __del__(self):
        """
        析构函数，确保在对象被销毁时停止监控线程。
        """
        self.stop()

    def load_first(self):
        """
        初始化时加载所有符合条件的文件。

        获取所有符合过滤条件的文件，并将它们添加到缓存中。
        这确保了缓存在开始监控前已经包含所有现有文件。
        """
        files_to_process = self.get_all_files()
        if not files_to_process:
            return
        for item in files_to_process:
            self.update_cache(item)

    def update_cache(self, file_path):
        """
        处理单个文件并更新缓存。

        参数:
            file_path: 文件的绝对路径

        处理流程:
            1. 使用 process_file_local 函数解析文件内容
            2. 将解析结果序列化并存储在缓存中
            3. 日志记录更新的文件及当前缓存状态
        """
        source_code = process_file_local(
            file_path, llm=self.llm, product_mode=self.product_mode)
        self.cache[file_path] = {
            "file_path": file_path,
            "content": [c.model_dump() for c in source_code],
        }
        logger.info(f"update cache: {file_path}")
        logger.info(f"current cache: {self.cache.keys()}")

    def remove_cache(self, file_path):
        """
        从缓存中移除指定文件。

        参数:
            file_path: 要移除的文件的绝对路径
        """
        del self.cache[file_path]
        logger.info(f"remove cache: {file_path}")
        logger.info(f"current cache: {self.cache.keys()}")

    def open_watch(self):
        """
        启动文件系统监控线程。

        此方法会持续监控文件系统变更，直到 stop_event 被设置。
        当检测到文件变更时，会根据变更类型执行相应的操作:
        - 添加/修改文件: 调用 update_cache 更新缓存
        - 删除文件: 调用 remove_cache 从缓存中移除
        """
        logger.info(f"start monitor: {self.path}...")
        for changes in watch(
            self.path, watch_filter=self.file_filter, stop_event=self.stop_event
        ):
            for change in changes:
                (action, path) = change
                if action == Change.added or action == Change.modified:
                    self.update_cache(path)
                elif action == Change.deleted:
                    self.remove_cache(path)

    def get_cache(self, options: Optional[Dict[str, Any]] = None):
        """
        获取当前缓存。

        参数:
            options: 可选的参数，指定获取缓存时的选项

        返回:
            当前内存中的缓存字典
        """
        return self.cache

    def _load_ignore_file(self):
        """
        加载忽略文件规则。

        首先尝试加载 .serveignore 文件，如果不存在，则尝试加载 .gitignore 文件。

        返回:
            包含忽略规则的字符串列表
        """
        serveignore_path = os.path.join(self.path, ".serveignore")
        gitignore_path = os.path.join(self.path, ".gitignore")

        if os.path.exists(serveignore_path):
            with open(serveignore_path, "r", encoding="utf-8") as ignore_file:
                patterns = ignore_file.readlines()
                return [pattern.strip() for pattern in patterns]
        elif os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as ignore_file:
                patterns = ignore_file.readlines()
                return [pattern.strip() for pattern in patterns]
        return []

    def get_all_files(self) -> List[str]:
        """
        获取所有符合条件的文件路径。

        遍历指定目录，应用忽略规则和扩展名过滤，
        返回所有符合条件的文件的绝对路径。

        返回:
            符合条件的文件路径列表
        """
        all_files = []
        for root, dirs, files in os.walk(self.path, followlinks=True):
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            if self.ignore_spec:
                relative_root = os.path.relpath(root, self.path)
                dirs[:] = [
                    d
                    for d in dirs
                    if not self.ignore_spec.match_file(os.path.join(relative_root, d))
                ]
                files = [
                    f
                    for f in files
                    if not self.ignore_spec.match_file(os.path.join(relative_root, f))
                ]

            for file in files:
                if self.required_exts and not any(
                    file.endswith(ext) for ext in self.required_exts
                ):
                    continue

                file_path = os.path.join(root, file)
                absolute_path = os.path.abspath(file_path)
                all_files.append(absolute_path)

        return all_files
