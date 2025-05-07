
import os
import shutil
from loguru import logger
import sys

# Ensure the package root is in PYTHONPATH
project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

from autocoder.common import AutoCoderArgs
from autocoder.common.v2.agent.agentic_edit_types import WriteToFileTool
from autocoder.common.v2.agent.agentic_edit_tools.write_to_file_tool_resolver import WriteToFileToolResolver
from autocoder.common.file_monitor.monitor import get_file_monitor, FileMonitor
from autocoder.common.rulefiles.autocoderrules_utils import get_rules, reset_rules_manager
from autocoder.auto_coder_runner import load_tokenizer
from unittest.mock import MagicMock

def setup_demo_environment(base_dir_name="demo_write_to_file_env"):
    """Sets up a clean directory for the demo."""
    base_dir = os.path.abspath(base_dir_name)
    if os.path.exists(base_dir):
        logger.info(f"Cleaning up existing demo directory: {base_dir}")
        shutil.rmtree(base_dir)
    os.makedirs(base_dir, exist_ok=True)
    logger.info(f"Created demo directory: {base_dir}")
    
    # Create a dummy .autocoderignore
    with open(os.path.join(base_dir, ".autocoderignore"), "w") as f:
        f.write("# Dummy ignore file for demo\n")
    return base_dir

def main():
    logger.info("--- 开始演示 WriteToFileToolResolver ---")

    # 1. 准备演示环境
    demo_root = setup_demo_environment()

    # 2. 初始化配置参数
    # Note: According to demo_or_test_initialization_order.md, FileMonitor and Rules should be initialized first.
    # AutoCoderArgs will use demo_root as source_dir.
    
    args = AutoCoderArgs(
        source_dir=demo_root,
        enable_auto_fix_lint=False, # Start with linting disabled for simplicity
    )
    logger.info(f"使用配置: source_dir='{args.source_dir}', enable_auto_fix_lint={args.enable_auto_fix_lint}")

    # Initialize FileMonitor and Rules (as per demo_or_test_initialization_order.md)
    # Resetting instances for a clean state if this demo is run multiple times or after tests
    FileMonitor.reset_instance()
    reset_rules_manager()

    monitor = get_file_monitor(args.source_dir)
    if not monitor.is_running():
        monitor.start()
    logger.info(f"文件监控已在运行: {monitor.root_dir}")

    rules = get_rules(args.source_dir)
    logger.info(f"已加载规则: {len(rules)} 条从 {args.source_dir}")
    
    # Load tokenizer
    try:
        load_tokenizer()
        logger.info("Tokenizer 加载完成")
    except Exception as e:
        logger.error(f"Tokenizer 加载失败: {e}. Demo may not fully work.")
        # return # Or proceed with caution

    # Mock an agent instance (no shadow manager for basic demo)
    mock_agent = MagicMock()
    mock_agent.shadow_manager = None
    mock_agent.shadow_linter = None
    mock_agent.args = args
    mock_agent.record_file_change = MagicMock() # To track calls

    # --- 场景 1: 创建一个新文件 ---
    logger.info("\n--- 场景 1: 创建一个新文件 ---")
    file_path1 = "my_new_file.txt"
    content1 = "Hello, AutoCoder! This is a new file."
    tool1 = WriteToFileTool(path=file_path1, content=content1)
    resolver1 = WriteToFileToolResolver(agent=mock_agent, tool=tool1, args=args)

    logger.info(f"执行写入: path='{file_path1}', content='{content1[:30]}...'")
    result1 = resolver1.resolve()

    if result1.success:
        logger.success(f"成功: {result1.message}")
        full_path1 = os.path.join(demo_root, file_path1)
        if os.path.exists(full_path1):
            with open(full_path1, "r") as f:
                logger.info(f"文件 '{full_path1}' 内容: '{f.read()}'")
            mock_agent.record_file_change.assert_called_with(file_path1, "added", content=content1, diffs=None)
        else:
            logger.error(f"错误: 文件 '{full_path1}' 未找到!")
    else:
        logger.error(f"失败: {result1.message}")
    mock_agent.record_file_change.reset_mock()


    # --- 场景 2: 覆盖一个已存在的文件 ---
    logger.info("\n--- 场景 2: 覆盖一个已存在的文件 ---")
    file_path2 = "my_new_file.txt" # Same file as above
    content2 = "This content overwrites the previous one."
    
    # Ensure the file exists from a previous step or create it
    abs_path2 = os.path.join(demo_root, file_path2)
    if not os.path.exists(abs_path2):
        with open(abs_path2, "w") as f: f.write("Initial dummy content for overwrite test.")

    tool2 = WriteToFileTool(path=file_path2, content=content2)
    resolver2 = WriteToFileToolResolver(agent=mock_agent, tool=tool2, args=args)
    
    logger.info(f"执行写入: path='{file_path2}', content='{content2[:30]}...'")
    result2 = resolver2.resolve()

    if result2.success:
        logger.success(f"成功: {result2.message}")
        full_path2 = os.path.join(demo_root, file_path2)
        if os.path.exists(full_path2):
            with open(full_path2, "r") as f:
                logger.info(f"文件 '{full_path2}' 新内容: '{f.read()}'")
            mock_agent.record_file_change.assert_called_with(file_path2, "modified", content=content2, diffs=None)

        else:
            logger.error(f"错误: 文件 '{full_path2}' 未找到!")
    else:
        logger.error(f"失败: {result2.message}")
    mock_agent.record_file_change.reset_mock()

    # --- 场景 3: 在尚不存在的目录中创建文件 ---
    logger.info("\n--- 场景 3: 在尚不存在的目录中创建文件 ---")
    file_path3 = "new_folder/another_folder/deep_file.md"
    content3 = "# Markdown File\n\nThis file is created in a new directory structure."
    tool3 = WriteToFileTool(path=file_path3, content=content3)
    resolver3 = WriteToFileToolResolver(agent=mock_agent, tool=tool3, args=args)

    logger.info(f"执行写入: path='{file_path3}', content='{content3[:30]}...'")
    result3 = resolver3.resolve()

    if result3.success:
        logger.success(f"成功: {result3.message}")
        full_path3 = os.path.join(demo_root, file_path3)
        if os.path.exists(full_path3):
            with open(full_path3, "r") as f:
                logger.info(f"文件 '{full_path3}' 内容:\n{f.read()}")
            mock_agent.record_file_change.assert_called_with(file_path3, "added", content=content3, diffs=None)
        else:
            logger.error(f"错误: 文件 '{full_path3}' 未找到!")
    else:
        logger.error(f"失败: {result3.message}")
    mock_agent.record_file_change.reset_mock()

    # --- 场景 4: 尝试写入项目根目录之外 (应失败) ---
    logger.info("\n--- 场景 4: 尝试写入项目根目录之外 ---")
    # Create a path that aims to go outside demo_root
    # On POSIX, if path is absolute, os.path.join(source_dir, path) returns path.
    # The resolver's security check is on the absolute path.
    
    # Find a directory outside demo_root
    parent_of_demo_root = os.path.dirname(demo_root)
    outside_path_attempt = os.path.join(parent_of_demo_root, "attempt_outside.txt")
    
    # To make the tool use this absolute path, we need to provide it directly.
    # The tool's 'path' parameter is typically relative to args.source_dir.
    # If we provide an absolute path here, the resolver should still check it.
    if os.name == 'posix':
        file_path4 = outside_path_attempt
    else: # For Windows, os.path.join might behave differently with absolute paths.
          # A relative path like "../sibling_dir/file.txt" is more reliable for testing this.
          # However, the resolver joins it with source_dir first, so it might become valid.
          # The most robust way to test the security check is to ensure the *final* absolute path
          # is outside the *final* absolute source_dir.
        file_path4 = os.path.abspath(os.path.join(demo_root, "..", "attempt_outside.txt"))


    content4 = "This should not be written."
    tool4 = WriteToFileTool(path=file_path4, content=content4)
    resolver4 = WriteToFileToolResolver(agent=mock_agent, tool=tool4, args=args)

    logger.info(f"执行写入: path='{file_path4}', content='{content4[:30]}...'")
    result4 = resolver4.resolve()

    if not result4.success and ("访问被拒绝" in result4.message or "Access denied" in result4.message) :
        logger.success(f"成功 (按预期失败): {result4.message}")
        if os.path.exists(outside_path_attempt):
             logger.error(f"严重错误: 文件 '{outside_path_attempt}' 被意外创建!")
        else:
             logger.info(f"文件 '{outside_path_attempt}' 未被创建 (正确).")
    else:
        logger.error(f"失败 (未按预期失败): {result4.message}, Success: {result4.success}")
        if os.path.exists(outside_path_attempt):
             logger.warning(f"文件 '{outside_path_attempt}' 被意外创建!")

    # --- 场景 5: 使用 Linting (需要 ShadowManager 和 Linter) ---
    logger.info("\n--- 场景 5: 使用 Linting (需要 ShadowManager 和 Linter) ---")
    args.enable_auto_fix_lint = True # Enable linting for this scenario
    
    from autocoder.shadows.shadow_manager import ShadowManager
    from autocoder.linters.shadow_linter import ShadowLinter
    
    # Ensure the shadow base directory exists within the demo_root for isolation
    shadow_base_dir = os.path.join(demo_root, ".auto-coder", "shadows") # Consistent with test
    os.makedirs(shadow_base_dir, exist_ok=True)
    
    shadow_manager = ShadowManager(source_dir=args.source_dir, event_file_id="demo_event")
    shadow_linter = ShadowLinter(shadow_manager=shadow_manager, verbose=True) # Enable verbose for demo
    
    mock_agent_with_shadow = MagicMock()
    mock_agent_with_shadow.shadow_manager = shadow_manager
    mock_agent_with_shadow.shadow_linter = shadow_linter
    mock_agent_with_shadow.args = args
    mock_agent_with_shadow.record_file_change = MagicMock()

    file_path5 = "python_code.py"
    content5_good = "def my_func():\n    print('Hello from Python')\n"
    content5_bad = "def my_func()\n    print 'bad syntax'\n" # Intentional syntax error

    tool5_good = WriteToFileTool(path=file_path5, content=content5_good)
    resolver5_good = WriteToFileToolResolver(agent=mock_agent_with_shadow, tool=tool5_good, args=args)
    
    logger.info(f"执行写入 (良好 Python 代码): path='{file_path5}'")
    result5_good = resolver5_good.resolve()
    logger.info(f"结果 (良好代码): Success: {result5_good.success}, Message: {result5_good.message}")
    if "代码质量检查通过" not in result5_good.message and "Linting passed" not in result5_good.message:
        logger.warning("Linting message for good code might be missing or unexpected.")
    
    # Clean shadows before next linting test to ensure isolation
    shadow_manager.clean_shadows()

    tool5_bad = WriteToFileTool(path=file_path5, content=content5_bad)
    resolver5_bad = WriteToFileToolResolver(agent=mock_agent_with_shadow, tool=tool5_bad, args=args)

    logger.info(f"执行写入 (错误 Python 代码): path='{file_path5}'")
    result5_bad = resolver5_bad.resolve()
    logger.info(f"结果 (错误代码): Success: {result5_bad.success}, Message: {result5_bad.message}")
    if "代码质量检查发现" not in result5_bad.message and "Linting found" not in result5_bad.message:
        logger.warning("Linting message for bad code might be missing or unexpected.")
    
    # Final cleanup of shadow directory for this agent
    shadow_manager.clean_shadows()


    logger.info("\n--- 清理演示环境 ---")
    # shutil.rmtree(demo_root) # Comment out if you want to inspect files
    logger.info(f"演示环境位于: {demo_root} (手动清理如果需要)")

    logger.info("--- 演示 WriteToFileToolResolver 结束 ---")

if __name__ == "__main__":
    # Configure Loguru for better output
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    main()
