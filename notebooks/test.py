import json
file_path = "/Users/allwefantasy/projects/auto-coder/.auto-coder/auto-coder.web/chat-lists/chat_2025-04-12T01-37-20-855Z.json"
with open(file_path, "r",encoding="utf-8") as f:
    data = json.load(f)
    print(data)

