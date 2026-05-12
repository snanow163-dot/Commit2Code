from pathlib import Path
from Refacting_types import utils as utils

def get_changing_names(root, commit, item, github_project_path, count):
    folder = Path("refacting_source_code/Move_Method")
    SHA = commit.get("sha1", "")

    left_path = item.get("leftSideLocations", [{}])[0].get("filePath")
    right_path = item.get("rightSideLocations", [{}])[0].get("filePath")

    left_element = item.get("leftSideLocations", [{}])[0].get("codeElement", "")
    right_element = item.get("rightSideLocations", [{}])[0].get("codeElement", "")
    before_name = left_element.split(" ")[1].split("(")[0] if " " in left_element else None
    after_name = right_element.split(" ")[1].split("(")[0] if " " in right_element else None

    before_src = utils.cmd_live(["git", "show", SHA + "^:" + left_path], cwd=github_project_path)
    after_src = utils.cmd_live(["git", "show", SHA + ":" + right_path], cwd=github_project_path)

    if before_src.returncode != 0:
        print(f"[WARN] Move_Method: 前文件获取失败 {left_path} in {SHA}^: {before_src.stderr}")
        return
    if after_src.returncode != 0:
        print(f"[WARN] Move_Method: 后文件获取失败 {right_path} in {SHA}: {after_src.stderr}")
        return

    before_file_code = before_src.stdout
    after_file_code = after_src.stdout

    before_class = utils.find_class_containing_method(before_file_code, before_name) if before_name else None
    after_class = utils.find_class_containing_method(after_file_code, after_name) if after_name else None

    before_class_code = utils.extract_class_source(before_file_code, before_class) if before_class else None
    after_class_code = utils.extract_class_source(after_file_code, after_class) if after_class else None

    payload = {
        "SHA": SHA,
        "type": "Move Method",
        "left_path": left_path,
        "right_path": right_path,
        "before_name": before_name,
        "after_name": after_name,
        "before_class": {"name": before_class, "code": before_class_code},
        "after_class": {"name": after_class, "code": after_class_code},
        "before_function": utils.extract_function_source(before_file_code, before_name) if before_name else None,
        "after_function": utils.extract_function_source(after_file_code, after_name) if after_name else None,
    }

    out_file = f"{count}~{SHA}~{before_name or 'unknown'}~{after_name or 'unknown'}.json"
    utils.write_json(folder, out_file, payload)
