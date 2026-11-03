"""Strict JSON (RFC 8259), shared by the tools and the verifier: verifier/strict_json.py is a byte-for-byte copy.

Python's json module accepts NaN, Infinity and -Infinity, and keeps the last of repeated keys; here both
are problems. Values compare with strict types, since in Python True == 1 and 1 == 1.0.
"""

import hashlib
import json
import re

SYNTAX = "syntax"
NON_FINITE = "non-finite"
DUPLICATE_KEY = "duplicate-key"
# Keys a path can name with a dot, e.g. $.items; any other key is bracketed, e.g. $["odd key"].
PLAIN_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SHOWN = 60


def problems(text):
    """Why ``text`` is not strict JSON, in the order found: [] when it is.

    Each problem is (kind, message, line, column); line and column are 1-based, or None when the
    parser gives no position. A syntax error stops the parse, so it is the only problem reported.
    """
    try:
        # Syntax alone: NaN, Infinity and repeated keys all pass here.
        json.loads(text, object_pairs_hook=list)
    except json.JSONDecodeError as error:
        return [(SYNTAX, error.msg, error.lineno, error.colno)]
    found = []

    def constant(name):
        found.append((NON_FINITE, f"{name} is not JSON: strict JSON has no NaN or Infinity", None, None))

    def pairs(items):
        keys = [key for key, _ in items]
        for key in dict.fromkeys(key for key in keys if keys.count(key) > 1):
            message = f"the key {quoted(key)} appears {keys.count(key)} times in one object"
            found.append((DUPLICATE_KEY, message, None, None))
        return dict(items)

    json.loads(text, parse_constant=constant, object_pairs_hook=pairs)
    return found


def strict_loads(text):
    """The value of strict JSON ``text``; a ValueError names its first problem."""
    found = problems(text)
    if found:
        kind, message, line, column = found[0]
        where = f" (line {line}, column {column})" if line is not None else ""
        raise ValueError(f"{kind}: {message}{where}")
    return json.loads(text)


def check(text):
    """check_json's answer for ``text``: (valid, error, line, column) of its first problem."""
    found = problems(text)
    if not found:
        return True, None, None, None
    _, message, line, column = found[0]
    return False, message, line, column


def fingerprint(broken, truth):
    """sha256 of a case's broken text and its ground truth."""
    canonical = json.dumps({"broken": broken, "truth": truth}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def kind_of(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def first_difference(expected, actual, path="$"):
    """Where ``actual`` first differs from ``expected``, as (path, message), or None when they are equal.

    Types are strict: a boolean is never an integer and an integer is never a float. Object keys
    may come in any order; array items may not.
    """
    if kind_of(expected) != kind_of(actual):
        return path, f"expected {described(expected)}, got {described(actual)}"
    if isinstance(expected, dict):
        for key in expected:
            if key not in actual:
                return member(path, key), f"the key {quoted(key)} is missing"
        for key in actual:
            if key not in expected:
                return member(path, key), f"the key {quoted(key)} is not in the original"
        for key in expected:
            found = first_difference(expected[key], actual[key], member(path, key))
            if found:
                return found
        return None
    if isinstance(expected, list):
        for index, (want, got) in enumerate(zip(expected, actual)):
            found = first_difference(want, got, f"{path}[{index}]")
            if found:
                return found
        if len(expected) != len(actual):
            return path, f"expected {len(expected)} items, got {len(actual)}"
        return None
    if expected != actual:
        return path, f"expected {described(expected)}, got {described(actual)}"
    return None


def member(path, key):
    return f"{path}.{key}" if PLAIN_KEY.fullmatch(key) else f"{path}[{quoted(key)}]"


def quoted(text):
    return json.dumps(text, ensure_ascii=False)


def described(value):
    shown = json.dumps(value, ensure_ascii=False)
    if len(shown) > SHOWN:
        shown = shown[: SHOWN - 3] + "..."
    return f"{kind_of(value)} {shown}"
