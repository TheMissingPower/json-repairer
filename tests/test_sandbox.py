"""The verifier keeps to the rules of NanoAgent's verifier sandbox (nanoagent.plugin.v0001.verifier)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

VERIFIER = Path(__file__).resolve().parent.parent / "verifier"
ALLOWED_IMPORTS = {
    "__future__", "collections", "dataclasses", "decimal", "difflib", "enum", "fractions", "functools", "hashlib",
    "itertools", "json", "math", "operator", "pathlib", "re", "statistics", "string", "textwrap", "typing",
    "unicodedata", "contract",
}  # fmt: skip
FORBIDDEN_NAMES = {
    "__import__", "breakpoint", "compile", "delattr", "eval", "exec", "getattr", "globals", "input", "locals", "open",
    "setattr", "vars",
}  # fmt: skip
FORBIDDEN_ATTRIBUTES = {
    "builtins", "chmod", "hardlink_to", "mkdir", "os", "rename", "rmdir", "shutil", "socket", "subprocess",
    "symlink_to", "sys", "touch", "unlink",
}  # fmt: skip


@pytest.mark.parametrize("path", sorted(VERIFIER.iterdir()), ids=lambda path: path.name)
def test_the_verifier_keeps_to_the_sandbox(path: Path) -> None:
    assert path.suffix == ".py" or path.name == "__pycache__", "verifier/ holds only .py files"
    if path.suffix != ".py":
        return
    problems = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            problems += [alias.name for alias in node.names if alias.name.split(".")[0] not in ALLOWED_IMPORTS]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                problems.append(node.module)
            problems += [a.name for a in node.names if a.name.startswith("_") or a.name in FORBIDDEN_ATTRIBUTES]
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            problems.append(node.id)
        elif isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in FORBIDDEN_ATTRIBUTES):
            problems.append("." + node.attr)
    assert problems == []
