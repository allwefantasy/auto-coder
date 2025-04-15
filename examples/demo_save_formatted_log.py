import os
import json
from autocoder.common.save_formatted_log import save_formatted_log

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 示例1：普通dict
    data_dict = {
        "event": "run_model",
        "status": "success",
        "detail": {
            "model": "gpt-4",
            "duration": 3.5
        },
        "tags": ["test", "log"]
    }
    json_text1 = json.dumps(data_dict, ensure_ascii=False)
    path1 = save_formatted_log(project_root, json_text1, "dict-demo")
    print(f"Dict demo log saved to: {path1}")

    # 示例2：list[dict]
    data_list = [
        {"step": 1, "desc": "load data", "ok": True},
        {"step": 2, "desc": "train", "ok": False, "error": {"msg": "OOM", "code": 123}},
        {"step": 3, "desc": "eval", "ok": True, "scores": [0.8, 0.9]}
    ]
    json_text2 = json.dumps(data_list, ensure_ascii=False)
    path2 = save_formatted_log(project_root, json_text2, "list-demo")
    print(f"List[dict] demo log saved to: {path2}")
