from __future__ import annotations
import os, fnmatch, asyncio
from watchfiles import Change
from autocoder.common.ignorefiles.ignore_file_utils import should_ignore
from autocoder.common.file_monitor.monitor import get_file_monitor
import logging
import functools

logger = logging.getLogger(__name__)

class DirectoryCache:
    _instance: "DirectoryCache|None" = None

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.files_set: set[str] = set()
        self.lock = asyncio.Lock()
        self._main_loop = asyncio.get_event_loop()  # 保存主事件循环引用
        logger.info(f"Initializing DirectoryCache for root: {self.root}")

    # ---------- 单例获取 ----------
    @classmethod
    def get_instance(cls, root: str | None = None) -> "DirectoryCache":
        if cls._instance is None:
            if root is None:
                raise ValueError("root is required when initializing DirectoryCache for the first time")
            logger.info("Creating new DirectoryCache instance.")
            cls._instance = cls(root)
            cls._instance._build()      # 同步首扫
            cls._instance._register_monitor()
        elif root is not None and os.path.abspath(root) != cls._instance.root:
             # 如果请求的 root 与已存在的实例 root 不同，可以选择抛出错误或重新初始化
             logger.warning(f"Requested root {os.path.abspath(root)} differs from existing instance root {cls._instance.root}. Re-initializing cache.")
             cls._instance = cls(root)
             cls._instance._build()
             cls._instance._register_monitor()

        return cls._instance

    # ---------- 构建 ----------
    def _build(self) -> None:
        logger.info(f"Building initial file cache for {self.root}...")
        count = 0
        for r, ds, fs in os.walk(self.root, followlinks=True):
            # 过滤掉需要忽略的目录
            ds[:] = [d for d in ds if not should_ignore(os.path.join(r, d))]
            for f in fs:
                fp = os.path.join(r, f)
                abs_fp = os.path.abspath(fp)
                if not should_ignore(abs_fp):
                    self.files_set.add(abs_fp)
                    count += 1
        logger.info(f"Initial cache build complete. Found {count} files.")


    # ---------- 监控回调 ----------
    def _register_monitor(self) -> None:
        try:
            logger.info(f"Registering file monitor for {self.root}")
            mon = get_file_monitor(self.root)
            # 使用 functools.partial 包装异步回调
            async_callback_wrapper = functools.partial(self._on_change_wrapper)
            mon.register("**/*", async_callback_wrapper) # 监听所有文件变化
            if not mon.is_running():
                logger.info("Starting file monitor...")
                mon.start()
            logger.info("File monitor registered and running.")
        except Exception as e:
            logger.error(f"Failed to register or start file monitor: {e}", exc_info=True)

    # Wrapper to run the async callback in the event loop
    def _on_change_wrapper(self, change: Change, path: str):
        try:
            # 使用run_coroutine_threadsafe在主事件循环中运行协程
            # 注意：主事件循环必须在其他地方运行，如主线程中
            asyncio.run_coroutine_threadsafe(self._on_change(change, path), self._main_loop)
        except Exception as e:
            logger.error(f"Error executing _on_change_wrapper: {e}", exc_info=True)
            # 如果run_coroutine_threadsafe失败，可以考虑一个同步的备用处理方法
            try:
                # 同步备份处理
                ap = os.path.abspath(path)
                if should_ignore(ap):
                    return
                
                if change is Change.added:
                    self.files_set.add(ap)
                elif change is Change.deleted:
                    self.files_set.discard(ap)
                # Change.modified不需要更新集合
            except Exception as backup_error:
                logger.error(f"Backup handler also failed: {backup_error}", exc_info=True)


    async def _on_change(self, change: Change, path: str) -> None:
        ap = os.path.abspath(path)
        # Check ignore status again, as gitignore might change
        if should_ignore(ap):
            # If a previously tracked file becomes ignored, remove it
            async with self.lock:
                if ap in self.files_set:
                    logger.debug(f"File became ignored, removing from cache: {ap}")
                    self.files_set.discard(ap)
            return

        async with self.lock:
            if change is Change.added:
                logger.debug(f"File added, adding to cache: {ap}")
                self.files_set.add(ap)
            elif change is Change.deleted:
                logger.debug(f"File deleted, removing from cache: {ap}")
                self.files_set.discard(ap)
            elif change is Change.modified:
                 # Modification doesn't change existence, but we might want to log or handle metadata updates if needed
                 logger.debug(f"File modified: {ap} (ignored in cache set)")
                 pass # No change needed for the set itself

    # ---------- 查询 ----------
    async def query(self, patterns: list[str]) -> list[str]:
        logger.debug(f"Querying cache with patterns: {patterns}")
        async with self.lock:
            # Make a copy to avoid issues if the set is modified during iteration (though lock prevents this here)
            current_files = list(self.files_set)

        if not patterns or patterns == [""] or patterns == ["*"]:
             logger.debug(f"Returning all {len(current_files)} cached files.")
             return current_files

        out: set[str] = set()

        for p in patterns:
            pattern_abs = os.path.abspath(os.path.join(self.root, p)) if not os.path.isabs(p) else p
            is_glob = "*" in p or "?" in p or "[" in p # More robust glob check

            try:
                if is_glob:
                    # fnmatch expects relative paths for matching within a root usually,
                    # but here we match against absolute paths in files_set.
                    # We need a pattern that works with absolute paths.
                    # If pattern 'p' is like '*.py', we need to match '/path/to/root/**/*.py'
                    # Let's adjust the pattern logic or filtering logic.

                    # Option 1: Match relative paths within the root
                    # Convert absolute paths in files_set to relative for matching
                    # relative_files = [os.path.relpath(f, self.root) for f in current_files]
                    # matched_relative = fnmatch.filter(relative_files, p)
                    # out.update(os.path.join(self.root, rel_f) for rel_f in matched_relative)

                    # Option 2: Match absolute paths directly (might need careful pattern construction)
                    # If p is relative, make it absolute based on root for matching
                    # Example: p = "src/*.py" -> effective_pattern = "/path/to/root/src/*.py"
                    # This requires fnmatch to handle absolute paths correctly or custom logic.

                    # Option 3: Simplified wildcard matching on absolute paths
                    # Treat '*' as a general wildcard anywhere in the path.
                    # fnmatch.filter might work if the pattern is constructed like `*pattern*`
                    # Let's stick to the user's original logic first, assuming it worked for their case
                    # The original `*{p}*` suggests substring matching with wildcards? Let's refine.

                    # Refined Glob Matching:
                    # If p contains wildcards, assume it's a glob pattern relative to root.
                    # Convert files_set paths to relative for matching.
                    for f_abs in current_files:
                        f_rel = os.path.relpath(f_abs, self.root)
                        if fnmatch.fnmatch(f_rel, p) or fnmatch.fnmatch(os.path.basename(f_abs), p):
                             out.add(f_abs)

                else:
                    # Exact or substring matching for non-glob patterns
                    # Match against filename or full path segment
                    p_lower = p.lower()
                    for f_abs in current_files:
                        if p_lower in os.path.basename(f_abs).lower() or p_lower in f_abs.lower():
                             out.add(f_abs)

            except Exception as e:
                logger.error(f"Error during pattern matching for '{p}': {e}", exc_info=True)


        result = sorted(list(out)) # Sort for consistent output
        logger.debug(f"Query returned {len(result)} files.")
        return result

# Helper function (optional, could be integrated into get_instance)
def initialize_cache(root_path: str):
    """Initializes the DirectoryCache singleton."""
    try:
        DirectoryCache.get_instance(root_path)
        logger.info("DirectoryCache initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize DirectoryCache: {e}", exc_info=True)

