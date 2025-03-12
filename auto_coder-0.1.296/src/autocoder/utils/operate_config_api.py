from autocoder.utils import get_last_yaml_file
import os
import uuid
import byzerllm
from autocoder.common import AutoCoderArgs
from typing import List, Optional
import yaml
from autocoder.auto_coder import AutoCoderArgs, load_include_files, Template
from autocoder.common import git_utils
import hashlib

# 该文件要给 chat,rag, web 等上层交互层使用


def convert_yaml_to_config(yaml_file: str):

    args = AutoCoderArgs()
    with open(yaml_file, "r",encoding="utf-8") as f:
        config = yaml.safe_load(f)
        config = load_include_files(config, yaml_file)
        for key, value in config.items():
            if key != "file":  # 排除 --file 参数本身
                # key: ENV {{VARIABLE_NAME}}
                if isinstance(value, str) and value.startswith("ENV"):
                    template = Template(value.removeprefix("ENV").strip())
                    value = template.render(os.environ)
                setattr(args, key, value)
    return args


def convert_yaml_config_to_str(yaml_config):
    yaml_content = yaml.safe_dump(
        yaml_config,
        allow_unicode=True,
        default_flow_style=False,
        default_style=None,
    )
    return yaml_content


def get_llm_friendly_package_docs(memory,
                                  package_name: Optional[str] = None, return_paths: bool = False
                                  ) -> List[str]:
    lib_dir = os.path.join(".auto-coder", "libs")
    llm_friendly_packages_dir = os.path.join(lib_dir, "llm_friendly_packages")
    docs = []

    if not os.path.exists(llm_friendly_packages_dir):
        print("llm_friendly_packages directory not found.")
        return docs

    libs = list(memory.get("libs", {}).keys())

    for domain in os.listdir(llm_friendly_packages_dir):
        domain_path = os.path.join(llm_friendly_packages_dir, domain)
        if os.path.isdir(domain_path):
            for username in os.listdir(domain_path):
                username_path = os.path.join(domain_path, username)
                if os.path.isdir(username_path):
                    for lib_name in os.listdir(username_path):
                        lib_path = os.path.join(username_path, lib_name)
                        if (
                            os.path.isdir(lib_path)
                            and (
                                package_name is None
                                or lib_name == package_name
                                or package_name == os.path.join(username, lib_name)
                            )
                            and lib_name in libs
                        ):
                            for root, _, files in os.walk(lib_path):
                                for file in files:
                                    if file.endswith(".md"):
                                        file_path = os.path.join(root, file)
                                        if return_paths:
                                            docs.append(file_path)
                                        else:
                                            with open(file_path, "r",encoding="utf-8") as f:
                                                docs.append(f.read())

    return docs


def convert_config_value(key, value):
    field_info = AutoCoderArgs.model_fields.get(key)
    if field_info:
        if value.lower() in ["true", "false"]:
            return value.lower() == "true"
        elif "int" in str(field_info.annotation):
            return int(value)
        elif "float" in str(field_info.annotation):
            return float(value)
        else:
            return value
    else:
        print(f"Invalid configuration key: {key}")
        return None


def get_llm(memory, model:Optional[str]=None):
    latest_yaml_file = get_last_yaml_file("actions")

    conf = memory.get("conf", {})
    current_files = memory["current_files"]["files"]
    execute_file = None

    if latest_yaml_file:
        try:
            execute_file = os.path.join("actions", latest_yaml_file)
            yaml_config = {
                "include_file": ["./base/base.yml"],
                "auto_merge": conf.get("auto_merge", "editblock"),
                "human_as_model": conf.get("human_as_model", "false") == "true",
                "skip_build_index": conf.get("skip_build_index", "true") == "true",
                "skip_confirm": conf.get("skip_confirm", "true") == "true",
                "silence": conf.get("silence", "true") == "true",
                "include_project_structure": conf.get("include_project_structure", "true")
                == "true",
            }
            for key, value in conf.items():
                converted_value = convert_config_value(key, value)
                if converted_value is not None:
                    yaml_config[key] = converted_value

            yaml_config["urls"] = current_files + get_llm_friendly_package_docs(
                memory=memory,
                return_paths=True
            )

            # 临时保存yaml文件，然后读取yaml文件，转换为args
            temp_yaml = os.path.join("actions", f"{uuid.uuid4()}.yml")
            try:
                with open(temp_yaml, "w",encoding="utf-8") as f:
                    f.write(convert_yaml_config_to_str(
                        yaml_config=yaml_config))
                args = convert_yaml_to_config(temp_yaml)
            finally:
                if os.path.exists(temp_yaml):
                    os.remove(temp_yaml)

            llm = byzerllm.ByzerLLM.from_default_model(model or
                                                       args.code_model or args.model)
            return llm
        except Exception as e:
            print(f"Failed to commit: {e}")
            if execute_file:
                os.remove(execute_file)
            return None
