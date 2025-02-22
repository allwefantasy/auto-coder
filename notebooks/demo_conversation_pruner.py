import byzerllm
from autocoder.common.conversation_pruner import ConversationPruner
import json
from loguru import logger

# 初始化 LLM
llm = byzerllm.ByzerLLM.from_default_model("deepseek_chat")

# 创建 ConversationPruner 实例
pruner = ConversationPruner(llm, safe_zone_tokens=50*1024, group_size=4)

# 生成一个长的对话历史
conversations = [
    {"role": "user", "content": "请帮我写一个Python函数来计算斐波那契数列"},
    {"role": "assistant", "content": "好的，这是一个计算斐波那契数列的Python函数:\n\n```python\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)\n```"},
    {"role": "user", "content": "这个函数的时间复杂度是多少？"},
    {"role": "assistant", "content": "这个递归实现的时间复杂度是O(2^n)，因为每次调用都会产生两个新的调用。"},
    {"role": "user", "content": "有没有更高效的实现方式？"},
    {"role": "assistant", "content": "是的，我们可以使用动态规划来优化，时间复杂度可以降到O(n)。这里是一个优化版本:\n\n```python\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    \n    prev, curr = 0, 1\n    for _ in range(n-1):\n        prev, curr = curr, prev + curr\n    return curr\n```"},
    {"role": "user", "content": "很好！这个版本的空间复杂度是多少？"},
    {"role": "assistant", "content": "这个优化版本的空间复杂度是O(1)，因为我们只使用了常数级别的额外空间。"},
    {"role": "user", "content": "能否再优化一下，使用矩阵快速幂的方法？"},
    {"role": "assistant", "content": "当然可以！使用矩阵快速幂可以将时间复杂度进一步优化到O(log n)。这里是一个实现:\n\n```python\nimport numpy as np\n\ndef matrix_power(matrix, power):\n    result = np.identity(len(matrix), dtype=object)\n    while power > 0:\n        if power % 2 == 1:\n            result = np.dot(result, matrix)\n        matrix = np.dot(matrix, matrix)\n        power = power // 2\n    return result\n\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    matrix = np.array([[1, 1], [1, 0]], dtype=object)\n    result_matrix = matrix_power(matrix, n-1)\n    return result_matrix[0][0]\n```"},
    {"role": "user", "content": "这个方法的时间复杂度是多少？"},
    {"role": "assistant", "content": "使用矩阵快速幂方法的时间复杂度是O(log n)，这是目前已知的最优时间复杂度。"}
]

# 打印原始对话长度
logger.info(f"原始对话长度: {len(conversations)}")

# 测试不同的修剪策略
strategies = ["summarize", "truncate", "hybrid"]
for strategy in strategies:
    pruned_conversations = pruner.prune_conversations(conversations, strategy_name=strategy)
    logger.info(f"使用策略 '{strategy}' 修剪后的对话长度: {len(pruned_conversations)}")
    logger.info(f"修剪后的对话内容:\n{json.dumps(pruned_conversations, indent=2, ensure_ascii=False)}")