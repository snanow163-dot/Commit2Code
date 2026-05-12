import json
import argparse
import shutil
import subprocess
from pathlib import Path
import logging
import Refacting_types as RT
import Refacting_types.utils as utils
import Config.configloader as Config

import sys

def read_json(path: str | Path):
    path = Path(path)
    with path.open("r") as f:
        return json.load(f)
    return None


def get_messages_of_refacting(root,github_project_path):
    fault_types = []
    count = 0
    type_count_dir = {}
    fault_count = 0
    created_dirs = set()

    def ensure_type_dir(t):
        if t not in created_dirs:
            utils.ensure_empty_dir("./refacting_source_code/" + utils.safe_dir_name(t))
            print("[DBG]:find_codes.py:已创建 {} 类型重构建源码存放目录:".format(t),"./refacting_source_code/" + utils.safe_dir_name(t))
            created_dirs.add(t)

    for commit in root:
        if commit["refactorings"] is not None:
            for item in commit["refactorings"]:
                item_type = item["type"]
                type_count_dir[item_type] = type_count_dir.get(item_type, 0) + 1

                match item_type: 

                    case "Extract Method":
                        ensure_type_dir(item_type)
                        RT.Extract_Method.get_source_code(root, commit, item, github_project_path, count + 1)
                        count += 1

                    case "Rename Method":
                        ensure_type_dir(item_type)
                        RT.Rename_Method.get_changing_names(root, commit, item, github_project_path, count + 1)
                        count += 1

                    case "Move Method":
                        ensure_type_dir(item_type)
                        RT.Move_Method.get_changing_names(root, commit, item, github_project_path, count + 1)
                        count += 1

                    case _:
                        if item_type not in fault_types:
                            fault_types.append(item_type)
                        fault_count += 1


    print("尚未定义源码获取方式的重构：",end=" ")
    for type in fault_types:
        print(type,end=",  ")

    print("\n\n源码提取{}次".format(count))
    for type_ in type_count_dir:
        if type_ not in fault_types:
            print(type_ + "提取{}次".format(type_count_dir[type_]))
    print("未定义提取{}次".format(fault_count))


def main() -> None:
    parser = argparse.ArgumentParser(description="从 RefactoringMiner 报告中提取 Java 变更函数/方法代码片段")
    parser.add_argument("--report", dest="report", help="RefactoringMiner JSON 报告路径")
    parser.add_argument("--project", dest="project", help="本地 Git 项目路径")
    parser.add_argument("--out", dest="out", default="./refacting_source_code", help="输出目录，默认 ./refacting_source_code")
    args = parser.parse_args()

    config_loader = Config.ConfigLoader()

    refactoringminer_report_path = args.report or config_loader.get("refactoringminer_report.path")
    github_project_path = args.project or config_loader.get("github_project.path")

    if not refactoringminer_report_path or not github_project_path:
        logging.error("请通过 --report 和 --project 指定路径，或在 Config/config.yaml 中配置 refactoringminer_report.path / github_project.path")
        return

    print(f"RefactoringMiner检测报告路径: {refactoringminer_report_path}")
    print(f"项目路径: {github_project_path}")

    out_dir = utils.ensure_empty_dir(args.out)
    print("已创建重构源码存放目录:", out_dir.resolve())

    manifest = read_json(refactoringminer_report_path)
    if not manifest or "commits" not in manifest:
        logging.error("报告文件内容无效，缺少 commits 节点")
        return

    commits = manifest["commits"]
    get_messages_of_refacting(commits, github_project_path)


if __name__ == "__main__":
    main()