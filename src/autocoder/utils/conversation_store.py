import os
import json
from autocoder.common import AutoCoderArgs


def store_code_model_conversation(
    args: AutoCoderArgs, instruction: str, conversations: any, model: str
):
    persit_dir = os.path.join(
        args.source_dir, ".auto-coder", "human_as_model_conversation"
    )
    os.makedirs(persit_dir, exist_ok=True)

    if args.human_as_model:
        model = "human"

    with open(os.path.join(persit_dir, "data.jsonl"), "a") as f:
        content = {
            "instruction": instruction,
            "conversations": conversations,
            "model": model,
            "yaml_file": args.file,
        }
        f.write(json.dumps(content, ensure_ascii=False) + "\n")


def load_code_model_conversation_from_store(args: AutoCoderArgs):
    persit_dir = os.path.join(
        args.source_dir, ".auto-coder", "human_as_model_conversation"
    )
    conversation_file = os.path.join(persit_dir, "data.jsonl")

    if not os.path.exists(conversation_file):
        return []

    conversations = []
    with open(conversation_file, "r",encoding="utf-8") as f:
        for line in f:
            conversations.append(json.loads(line))

    return conversations
