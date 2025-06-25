# Conversation Pruners

This directory contains conversation pruning utilities for managing token usage in long conversations.

## Available Pruners

### 1. ConversationPruner (`conversation_pruner.py`)

The original conversation pruner that handles general conversation history management using strategies like:
- **Summarize**: Groups early conversations and generates summaries
- **Truncate**: Removes early conversation groups
- **Hybrid**: Tries summarization first, then truncation if needed

### 2. AgenticConversationPruner (`agentic_conversation_pruner.py`)

A specialized pruner designed for agentic conversations that contain tool execution results. This pruner specifically targets:
- Tool result messages (role='user', content contains `<tool_result>`)
- Replaces tool output content with placeholder messages
- Preserves conversation flow while reducing token usage

## Usage

### Basic Usage of AgenticConversationPruner

```python
from autocoder.common.pruner.agentic_conversation_pruner import AgenticConversationPruner
from autocoder.common import AutoCoderArgs

# Initialize the pruner
args = AutoCoderArgs(conversation_prune_safe_zone_tokens=50000)  # 50K token threshold
llm = get_your_llm_instance()
pruner = AgenticConversationPruner(args=args, llm=llm)

# Example conversation with tool results
conversations = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Please read the file config.json"},
    {"role": "assistant", "content": "I'll read the file for you.\n\n<read_file>\n<path>config.json</path>\n</read_file>"},
    {
        "role": "user", 
        "content": "<tool_result tool_name='ReadFileTool' success='true'><message>File read successfully</message><content>{'database': {'host': 'localhost', 'port': 5432, 'name': 'myapp'}, 'api': {'key': 'abc123', 'endpoint': 'https://api.example.com'}}</content></tool_result>"
    },
    {"role": "assistant", "content": "I can see your configuration file. The database is set to localhost:5432..."}
]

# Prune the conversations
pruned_conversations = pruner.prune_conversations(conversations)

# Get cleanup statistics
stats = pruner.get_cleanup_statistics(conversations, pruned_conversations)
print(f"Tokens saved: {stats['tokens_saved']}")
print(f"Tool results cleaned: {stats['tool_results_cleaned']}")
```

### Integration with AgenticEdit

The `AgenticConversationPruner` is automatically integrated into the `AgenticEdit` class:

```python
# In AgenticEdit.analyze() method
if current_tokens > safe_zone_tokens:
    logger.info(f"Conversation too long ({current_tokens} tokens), applying agentic pruning")
    conversations = self.agentic_pruner.prune_conversations(conversations)
    # Continue with pruned conversations...
```

## How AgenticConversationPruner Works

### 1. Tool Result Detection

The pruner identifies tool result messages by checking:
- Message role is 'user'
- Content contains `<tool_result` and `tool_name=`

### 2. Progressive Cleanup

Starting from the first tool result:
1. Check if current token count exceeds safe zone
2. If yes, replace the tool result content with a placeholder
3. Continue to next tool result until within safe zone

### 3. Content Replacement

Original tool result:
```xml
<tool_result tool_name='ReadFileTool' success='true'>
<message>File read successfully</message>
<content>Very long file content that takes many tokens...</content>
</tool_result>
```

After cleanup:
```xml
<tool_result tool_name='ReadFileTool' success='true'>
<message>Content cleared to save tokens</message>
<content>This message has been cleared. If you still want to get this information, you can call the tool again to retrieve it.</content>
</tool_result>
```

## Benefits

### For Regular ConversationPruner:
- Handles general conversation history
- Supports multiple strategies (summarize, truncate, hybrid)
- Good for managing overall conversation length

### For AgenticConversationPruner:
- **Surgical precision**: Only removes tool output content, not conversation logic
- **Maintains context**: Keeps tool call history and assistant responses
- **Preserves workflow**: User can re-run tools to get current information
- **Efficient**: Targets the largest content blocks (tool outputs) first

## Configuration

### Available Settings

```python
# Set the token threshold for pruning
args.conversation_prune_safe_zone_tokens = 50000  # Default: 50K tokens

# The agentic pruner will automatically activate when conversations exceed this limit
```

## Testing

Run the test file to see the pruner in action:

```bash
cd src/autocoder/common/pruner
python test_agentic_conversation_pruner.py
```

This will demonstrate:
- Tool result detection and cleaning
- Token usage statistics
- Before/after conversation comparison

## When to Use Which Pruner

### Use AgenticConversationPruner when:
- Working with agentic workflows that generate tool outputs
- Tool results contain large amounts of data (file contents, API responses, etc.)
- You want to preserve conversation logic while reducing token usage
- Recent tool outputs are more important than old ones

### Use ConversationPruner when:
- Working with general chat conversations
- Need conversation summarization
- Want to remove entire conversation segments
- Working with non-agentic workflows 