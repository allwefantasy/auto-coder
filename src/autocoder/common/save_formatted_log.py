import os
import json
import uuid
from datetime import datetime

def save_formatted_log(project_root, json_text, suffix):
    """
    Save a JSON log as a formatted markdown file under project_root/.cache/logs.
    Filename: <YYYYmmdd_HHMMSS>_<uuid>_<suffix>.md
    Args:
        project_root (str): The root directory of the project.
        json_text (str): The JSON string to be formatted and saved.
        suffix (str): The suffix for the filename.
    """
    # Parse JSON
    try:
        data = json.loads(json_text)
    except Exception as e:
        raise ValueError(f"Invalid JSON provided: {e}")

    # Format as markdown with recursive depth
    def to_markdown(obj, level=1):
        lines = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                lines.append(f"{'#' * (level + 1)} {key}\n")
                lines.extend(to_markdown(value, level + 1))
        elif isinstance(obj, list):
            for idx, item in enumerate(obj, 1):
                lines.append(f"{'#' * (level + 1)} Item {idx}\n")
                lines.extend(to_markdown(item, level + 1))
        else:
            lines.append(str(obj) + "\n")
        return lines

    md_lines = ["# Log Entry\n"]
    md_lines.extend(to_markdown(data, 1))
    md_content = "\n".join(md_lines)

    # Prepare directory
    logs_dir = os.path.join(project_root, ".cache", "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Prepare filename
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())
    filename = f"{now}_{unique_id}_{suffix}.md"
    filepath = os.path.join(logs_dir, filename)

    # Save file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    return filepath
