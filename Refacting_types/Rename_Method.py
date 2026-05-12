from Refacting_types import utils as utils
from pathlib import Path
import re

def get_changing_names(root, commit, item, github_project_path, count):
    folder = Path("refacting_source_code/Rename_Method")
    SHA = commit.get("sha1", "")

    file_path = item["leftSideLocations"][0].get("filePath")

    before_name = item["leftSideLocations"][0]["codeElement"].split(" ")[1].split("(")[0]
    after_name = item["rightSideLocations"][0]["codeElement"].split(" ")[1].split("(")[0]

    before_src = utils.cmd_live(["git", "show", SHA + "^:" + file_path], cwd=github_project_path)
    if before_src.returncode != 0:
        print(f"[WARN] Rename_Method.py: 前文件获取失败 {file_path} in {SHA}^: {before_src.stderr}")
        return

    after_src = utils.cmd_live(["git", "show", SHA + ":" + file_path], cwd=github_project_path)
    if after_src.returncode != 0:
        print(f"[WARN] Rename_Method.py: 后文件获取失败 {file_path} in {SHA}: {after_src.stderr}")
        return

    before_file_code = before_src.stdout
    after_file_code = after_src.stdout

    before_class = utils.find_class_containing_method(before_file_code, before_name)
    after_class = utils.find_class_containing_method(after_file_code, after_name)

    before_class_code = utils.extract_class_source(before_file_code, before_class) if before_class else None
    after_class_code = utils.extract_class_source(after_file_code, after_class) if after_class else None

    payload = {
        "SHA": SHA,
        "type": "Rename Method",
        "path": file_path,
        "before_name": before_name,
        "after_name": after_name,
        "before_class": {"name": before_class, "code": before_class_code},
        "after_class": {"name": after_class, "code": after_class_code},
        "before_function": utils.extract_function_source(before_file_code, before_name),
        "after_function": utils.extract_function_source(after_file_code, after_name),
    }

    out_file = f"{count}~{SHA}~{before_name}~{after_name}.json"
    utils.write_json(folder, out_file, payload)

