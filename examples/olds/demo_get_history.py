
import sys
import os

# Adjust sys.path to allow imports if running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autocoder.common import AutoCoderArgs
from autocoder.common.v2.agent.agentic_edit_conversation import AgenticConversation

def main():
    # Initialize args with current directory as source_dir
    args = AutoCoderArgs(source_dir=".")

    # Create conversation instance
    convo = AgenticConversation(args)

    # Add some consecutive same-role messages to test merging
    # Consecutive user messages
    for i in range(3):
        convo.add_user_message(f"Consecutive USER message #{i+1}")

    # Consecutive assistant messages
    for i in range(2):
        convo.add_assistant_message(f"Consecutive ASSISTANT reply #{i+1}")

    # Interleaved user-assistant pairs
    for i in range(5):
        convo.add_user_message(f"Normal USER message #{i+1}")
        convo.add_assistant_message(f"Normal ASSISTANT reply #{i+1}")

    # More consecutive user messages
    for i in range(4):
        convo.add_user_message(f"Another USER message #{i+1}")

    # More consecutive assistant messages
    for i in range(3):
        convo.add_assistant_message(f"Another ASSISTANT reply #{i+1}")

    # Add some tool messages (should be ignored by get_history)
    convo.add_assistant_tool_call_message(tool_calls=[{"name": "search", "args": {"query": "test"}}], content="Calling search tool")
    convo.add_tool_result_message(tool_call_id="12345", content="Tool result content")

    # Retrieve the last 20 user-assistant pairs
    history = convo.get_history()

    print(f"Retrieved {len(history)} messages (should be 40, 20 pairs):")
    for msg in history:
        print(f"{msg['role'].upper()}: {msg.get('content')}")

if __name__ == "__main__":
    main()
