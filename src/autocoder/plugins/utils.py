import json

def load_json_file(file_path: str) -> dict:
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json_file(file_path: str, data: dict):
    with open(file_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
