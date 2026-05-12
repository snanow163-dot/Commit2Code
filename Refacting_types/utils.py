import os
import subprocess
from typing import List, Optional
from pathlib import Path
import shutil
import sys
import tempfile
import json

def write_txt(folder,file_name,content):
    folder.mkdir(parents=True, exist_ok=True)

    outfile = folder / file_name

    with outfile.open("a", encoding="utf-8") as f:
        f.write((content or "") +"\n")


def read_json(path: str | Path):
    path = Path(path)
    with path.open("r") as f:
        return json.load(f)
    return None


def write_json_kv(folder_path, file_name, key, value):
    
    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)
    outfile = folder / file_name

    # 1) 读原 JSON（不存在/损坏 -> 空 dict）
    data = {}
    if outfile.exists():
        try:
            with outfile.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    if not isinstance(data, dict):
        raise ValueError(f"目标 JSON 顶层不是对象(dict)，无法按 key 写入：{outfile}")

    # 2) 写入 key（支持 a.b.c 嵌套）
    parts = key.split(".") if key else []
    if not parts:
        raise ValueError("key 不能为空")

    cur = data
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value

    # 3) 原子写回（先写临时文件，再替换）
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=outfile.stem + "_", suffix=".tmp", dir=str(folder))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, outfile)  # 原子替换
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise



def cmd_live(cmd: List[str], cwd: Optional[str] = None):
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"  #运行 git fetch/pull/clone凭据认证跳过，防止批处理卡死。返回错误状态码。

    p = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,                       # 可有可无，这里不捕获输出所以不关键
        stdin=subprocess.DEVNULL,      # 不允许交互输入，避免卡住
        # stdout=subprocess.DEVNULL,     # 不把标准输出打印到终端
        stdout=subprocess.PIPE,
        # stderr=subprocess.DEVNULL,     # 不把错误输出打印到终端
        stderr=subprocess.PIPE
    )
    # return p.returncode
    return p

def ensure_empty_dir(dir_path: str | Path) -> Path:
    p = Path(dir_path)

    if p.exists():
        # if not p.is_dir():
        #     raise NotADirectoryError(f"{p} exists but is not a directory")
        # 删除目录内所有内容（文件/子目录），保留目录本身
        for child in p.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        p.mkdir(parents=True, exist_ok=True)

    return p


def safe_dir_name(project: str) -> str:
    return (project or "").strip().replace("/", "__").replace(" ", "_")


def write_json(folder_path, file_name, data):
    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)
    outfile = folder / file_name
    with outfile.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_class_containing_method(code: str, method_name: str) -> str | None:
    try:
        import javalang
    except ImportError:
        return None

    try:
        tree = javalang.parse.parse(code)
    except Exception:
        try:
            tree = javalang.parse.parse("class __DummyWrapper__ {\n" + code + "\n}")
        except Exception:
            return None

    def recurse(types):
        for typ in types:
            if isinstance(typ, (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration, javalang.tree.EnumDeclaration)):
                for m in getattr(typ, "methods", []):
                    if getattr(m, "name", None) == method_name:
                        return typ.name
                nested = getattr(typ, "types", []) or []
                found = recurse(nested)
                if found:
                    return found
        return None

    return recurse(tree.types)


def extract_class_source(code: str, class_name: str) -> str | None:
    import re

    if not class_name:
        return None

    patterns = [
        rf"(?m)^(?P<indent>\s*)(?:public|protected|private|abstract|final|static|strictfp|\s)*class\s+{re.escape(class_name)}\b[^{{]*\{{",
        rf"(?m)^(?P<indent>\s*)(?:public|protected|private|abstract|final|static|strictfp|\s)*interface\s+{re.escape(class_name)}\b[^{{]*\{{",
        rf"(?m)^(?P<indent>\s*)(?:public|protected|private|abstract|final|static|strictfp|\s)*enum\s+{re.escape(class_name)}\b[^{{]*\{{",
    ]

    for pattern in patterns:
        match = re.search(pattern, code)
        if not match:
            continue

        start = match.start()
        brace_index = code.find("{", match.end() - 1)
        if brace_index < 0:
            continue

        depth = 0
        i = brace_index
        while i < len(code):
            if code[i] == '{':
                depth += 1
            elif code[i] == '}':
                depth -= 1
                if depth == 0:
                    return code[start:i + 1]
            i += 1

    return None


def extract_function_source(code: str, func_name: str) -> str | None:
    # 仅支持 Java 源码提取，不再兼容 Python
    try:
        import javalang
    except ImportError:
        raise RuntimeError("javalang dependency is required for Java source parsing")

    target_code = code
    parsed_ok = False

    # 先尝试把输入当成完整 Java 文件
    try:
        tokens = list(javalang.tokenizer.tokenize(target_code))
        tree = javalang.parse.parse(target_code)
        parsed_ok = True
    except Exception:
        parsed_ok = False

    # 如果不是完整 compilation unit，就包装成一个 dummy class
    if not parsed_ok:
        try:
            target_code = "class __DummyWrapper__ {\n" + code + "\n}"
            tokens = list(javalang.tokenizer.tokenize(target_code))
            tree = javalang.parse.parse(target_code)
            parsed_ok = True
        except Exception:
            parsed_ok = False

    if not parsed_ok:
        # Java 解析失败，尝试后继正则兜底
        return _extract_function_source_regex(code, func_name)

    target_node = None
    for _, node in tree:
        if isinstance(node, (javalang.tree.MethodDeclaration, javalang.tree.ConstructorDeclaration)):
            if getattr(node, "name", None) == func_name:
                target_node = node
                break

    if target_node is None or getattr(target_node, "position", None) is None:
        # 解析成功但找不到方法，尝试正则兜底
        return _extract_function_source_regex(code, func_name)

    start_line = target_node.position.line
    start_col = target_node.position.column

    # 找到方法起始 token
    start_token_index = None
    for i, tok in enumerate(tokens):
        tok_line, tok_col = tok.position
        if (tok_line, tok_col) >= (start_line, start_col):
            start_token_index = i
            break

    if start_token_index is None:
        return _extract_function_source_regex(code, func_name)

    end_token_index = None
    first_block_index = None

    for i in range(start_token_index, len(tokens)):
        v = tokens[i].value
        if v == ";":
            end_token_index = i
            break
        if v == "{":
            first_block_index = i
            break

    if end_token_index is None and first_block_index is not None:
        depth = 0
        for i in range(first_block_index, len(tokens)):
            v = tokens[i].value
            if v == "{":
                depth += 1
            elif v == "}":
                depth -= 1
                if depth == 0:
                    end_token_index = i
                    break

    if end_token_index is None:
        return _extract_function_source_regex(code, func_name)

    # line/col -> offset
    lines = target_code.splitlines(True)

    if start_line < 1 or start_line > len(lines):
        return _extract_function_source_regex(code, func_name)
    start_offset = sum(len(lines[i]) for i in range(start_line - 1)) + (start_col - 1)

    end_tok = tokens[end_token_index]
    end_line, end_col = end_tok.position
    if end_line < 1 or end_line > len(lines):
        return _extract_function_source_regex(code, func_name)
    end_offset = sum(len(lines[i]) for i in range(end_line - 1)) + (end_col - 1) + len(end_tok.value)

    return target_code[start_offset:end_offset]


def _extract_function_source_regex(code: str, func_name: str) -> str | None:
    # 简单正则匹配方法声明并定位括号，作为 javalang 解析失败时备选
    import re

    pattern = re.compile(
        rf"(?m)^(?P<indent>\s*)(?:public|protected|private|static|final|synchronized|abstract|native|strictfp|\s)*" +
        rf"[\w\<\>\[\] ,\?&]+\s+{re.escape(func_name)}\s*\([^\)]*\)\s*(?:throws[\w\.,\s]*)?\s*\{{"
    )

    match = pattern.search(code)
    if not match:
        return None

    start = match.start()
    brace_index = code.find('{', match.end() - 1)
    if brace_index < 0:
        return None

    depth = 0
    i = brace_index
    while i < len(code):
        if code[i] == '{':
            depth += 1
        elif code[i] == '}':
            depth -= 1
            if depth == 0:
                return code[start:i + 1]
        i += 1

    return None


if __name__ == "__main__":
    rc = cmd_live(["pwd"], cwd="../")
    if rc.returncode != 0:
        print("测试未通过")
        sys.exit(rc.returncode)
    print("测试通过")
    print("1", rc.stdout)
    print("2", rc.stdout.strip())