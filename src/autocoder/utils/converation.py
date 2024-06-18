import os
import json
from autocoder.common import AutoCoderArgs


def store_code_model_result(
    args: AutoCoderArgs, instruction: str, result: str, model: str
):
    persit_dir = os.path.join(
        args.source_dir, ".auto-coder", "human_as_model_conversation"
    )
    os.makedirs(persit_dir, exist_ok=True)
    with open(os.path.join(persit_dir, "data.jsonl"), "a") as f:
        conversation = {"instruction": instruction, "response": result, "model": model}
        f.write(json.dumps(conversation, ensure_ascii=False) + "\n")
