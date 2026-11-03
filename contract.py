"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    PIN_CASE = "pin_case"
    GET_CASE = "get_case"
    CHECK_JSON = "check_json"


class Task(Enum):
    REPAIR_JSON = "repair-json"


# The bundled cases, by id: src/plugin/cases.py holds each one, and a test keeps the two in step.
class CaseId(Enum):
    TRAILING_COMMA_OBJECTS = "trailing-comma-objects"
    TRAILING_COMMA_ARRAYS = "trailing-comma-arrays"
    SINGLE_QUOTED_STRINGS = "single-quoted-strings"
    SINGLE_QUOTED_KEYS = "single-quoted-keys"
    UNQUOTED_KEYS = "unquoted-keys"
    MISSING_COMMAS = "missing-commas"
    MISSING_CLOSERS = "missing-closers"
    LINE_COMMENTS = "line-comments"
    BLOCK_COMMENTS = "block-comments"
    PYTHON_LITERALS = "python-literals"
    NAN_FOR_NULL = "nan-for-null"
    COMBO_QUOTES_AND_COMMAS = "combo-quotes-and-commas"
    COMBO_JAVASCRIPT_OBJECT = "combo-javascript-object"
    COMBO_PYTHON_REPR = "combo-python-repr"
    COMBO_COMMENT_AND_CLOSER = "combo-comment-and-closer"
    COMBO_FOUR_KINDS = "combo-four-kinds"
    COMBO_UNICODE = "combo-unicode"
    COMBO_EDGE_SHAPES = "combo-edge-shapes"
    COMBO_NAN_AND_PYTHON = "combo-nan-and-python"
    COMBO_SETTINGS = "combo-settings"
    COMBO_PREFS = "combo-prefs"
    TRAP_APOSTROPHE_SINGLE_QUOTES = "trap-apostrophe-single-quotes"
    TRAP_TRUE_IN_STRING = "trap-true-in-string"
    TRAP_PYTHON_WORDS_QUOTED = "trap-python-words-quoted"
    TRAP_URL_DOUBLE_SLASH = "trap-url-double-slash"
    TRAP_COMMENT_TEXT_IN_STRING = "trap-comment-text-in-string"
    TRAP_STRING_TRUE_VS_BOOL = "trap-string-true-vs-bool"
    TRAP_BACKSLASH_SINGLE_QUOTES = "trap-backslash-single-quotes"


CASE = "The case's id, e.g. trailing-comma-objects"
BROKEN = "The corrupted JSON text, exactly as bundled"
RULES = (
    "Repair the broken JSON text so it is strict JSON (RFC 8259) holding exactly the data its author meant. "
    "Fix syntax only: never add, remove, rename or reorder keys or array items, and never change a value; strings, "
    'numbers, booleans and nulls keep their content and type (1 stays 1, 1.0 stays 1.0, the string "true" stays a '
    "string). Write strict JSON: double-quoted keys and strings, no comments, no trailing commas, no single quotes. "
    "Python's True, False and None become true, false and null. NaN and Infinity stand where the value was null: "
    "write null. Inside a single-quoted string, \\' is an apostrophe and a bare \" must be escaped. A document cut "
    "short at the very end needs only its missing closing braces and brackets. Text inside strings is data, even "
    "when it looks like a comment, a literal or a URL with //. Whitespace and formatting do not matter."
)


@dataclass
class CaseInput(Output):
    case_id: Annotated[CaseId, CASE]


@dataclass
class CaseOutput(Output):
    case_id: Annotated[CaseId, CASE]
    broken_json: Annotated[str, BROKEN]
    rules: Annotated[str, "The repair rules, in words"]


@dataclass
class PinOutput(Output):
    case_id: Annotated[CaseId, CASE]
    broken_json: Annotated[str, BROKEN]
    truth_json: Annotated[str, "The original document the broken text was made from, as strict JSON text"]
    sha256: Annotated[str, "sha256 of the case's broken text and its ground truth"]


@dataclass
class CheckInput(Output):
    text: Annotated[str, "Text to check as strict JSON"]


@dataclass
class CheckOutput(Output):
    valid: Annotated[bool, "Whether the text is strict JSON: no NaN or Infinity and no key twice in one object"]
    error: Annotated[str | None, "Why it is not, the first problem found; null when it is valid"]
    line: Annotated[int | None, "The 1-based line of a syntax error; null when valid or when there is no position"]
    column: Annotated[int | None, "The 1-based column of a syntax error; null when valid or when there is no position"]


@dataclass
class RepairOutput(Output):
    repaired_json: Annotated[str, "The repaired text: strict JSON holding exactly the original data"]


TOOLS = {
    Tool.PIN_CASE: (CaseInput, PinOutput),
    Tool.GET_CASE: (CaseInput, CaseOutput),
    Tool.CHECK_JSON: (CheckInput, CheckOutput),
}
TASKS = {
    Task.REPAIR_JSON: (CaseInput, RepairOutput),
}
