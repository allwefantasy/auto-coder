
import os
from autocoder.common.v2.agent.agentic_edit_tools.list_code_definition_names_tool_resolver import ListCodeDefinitionNamesToolResolver
from autocoder.common.v2.agent.agentic_edit_types import ListCodeDefinitionNamesTool
from autocoder.common import AutoCoderArgs

def main():
    # 目标路径，测试本身的resolver文件
    target_path = "src/autocoder/common/v2/agent/agentic_edit_tools/list_code_definition_names_tool_resolver.py"
    
    # 构造工具参数
    tool = ListCodeDefinitionNamesTool(
        path=target_path
    )

    # 初始化参数
    args = AutoCoderArgs(
        source_dir="."
    )

    # 创建resolver，agent传None即可
    resolver = ListCodeDefinitionNamesToolResolver(agent=None, tool=tool, args=args)

    # 执行工具
    result = resolver.resolve()

    # 打印结果
    print("Success:", result.success)
    print("Message:", result.message)
    print("Content:", result.content)

if __name__ == "__main__":
    main()
