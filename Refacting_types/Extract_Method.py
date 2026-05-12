from Refacting_types import utils as utils
import os
import sys
import re
from pathlib import Path




def get_source_code(root, commit, item, github_project_path, count):
    folder = Path("refacting_source_code/Extract_Method")
    SHA = commit.get("sha1", "")

    description = item.get("description", "")
    pattern = re.compile(
        r'Extract Method\s+(?:public|protected|private)\s+'
        r'([A-Za-z_]\w*)\s*\([^)]*\)\s*(?::\s*[^ ]+)?\s+'
        r'extracted from\s+(?:public|protected|private)\s+'
        r'([A-Za-z_]\w*)\s*\([^)]*\)\s*(?::\s*[^ ]+)?\s+'
        r'in class'
    )
    m = pattern.search(description)
    if not m:
        raise ValueError(f"无法解析 Extract Method 描述: {description}")

    extracted_name = m.group(1)
    source_name = m.group(2)

    before_path = item["leftSideLocations"][0].get("filePath")
    after_path = item["rightSideLocations"][0].get("filePath")

    before_src = utils.cmd_live(["git", "show", SHA + "^:" + before_path], cwd=github_project_path)
    if before_src.returncode != 0:
        print(f"[WARN] Extract_Method: 前文件获取失败 {before_path} in {SHA}^: {before_src.stderr}")
        return

    after_src = utils.cmd_live(["git", "show", SHA + ":" + after_path], cwd=github_project_path)
    if after_src.returncode != 0:
        print(f"[WARN] Extract_Method: 后文件获取失败 {after_path} in {SHA}: {after_src.stderr}")
        return

    before_code = before_src.stdout
    after_code = after_src.stdout

    before_class_name = utils.find_class_containing_method(before_code, source_name)
    after_source_class = utils.find_class_containing_method(after_code, source_name)
    after_extracted_class = utils.find_class_containing_method(after_code, extracted_name)

    before_class_code = utils.extract_class_source(before_code, before_class_name) if before_class_name else None
    after_source_class_code = utils.extract_class_source(after_code, after_source_class) if after_source_class else None
    after_extracted_class_code = (
        utils.extract_class_source(after_code, after_extracted_class)
        if after_extracted_class and after_extracted_class != after_source_class
        else None
    )

    output_payload = {
        "SHA": SHA,
        "type": "Extract Method",
        "before_path": before_path,
        "after_path": after_path,
        "source_method": source_name,
        "extracted_method": extracted_name,
        "before_class": {
            "name": before_class_name,
            "code": before_class_code,
        },
        "after_classes": [],
        "before_function": utils.extract_function_source(before_code, source_name),
        "after_source_function": utils.extract_function_source(after_code, source_name),
        "after_extracted_function": utils.extract_function_source(after_code, extracted_name),
    }

    if after_source_class:
        output_payload["after_classes"].append({"name": after_source_class, "code": after_source_class_code})
    if after_extracted_class and after_extracted_class != after_source_class:
        output_payload["after_classes"].append({"name": after_extracted_class, "code": after_extracted_class_code})

    out_file = f"{count}~{SHA}.json"
    utils.write_json(folder, out_file, output_payload)





