"""The repair-json task's verdict: 6 constraints, in order, every one of which must hold.

The ground truth is the verifier's own copy of the bundled case (cases.py), never the agent's word:
the answer key, pin_case's pinned output, must agree with it before anything else is judged. Each
constraint is {id, constraint, ok, expected, actual, message}: ok is True (holds), False (fails) or
None (not checked, because a check it needs failed).
"""

from .checks import answer_key_problem, bundled, result
from .strict_json import DUPLICATE_KEY, NON_FINITE, SYNTAX, first_difference, problems, strict_loads

CONSTRAINTS = (
    ("answer-key", "The answer key is the bundled case"),
    ("contract-shape", "repaired_json is a non-empty string"),
    ("strict-json", "The repair parses as JSON"),
    ("no-nonfinite", "The repair has no NaN or Infinity"),
    ("no-duplicate-keys", "No object in the repair names a key twice"),
    ("matches-original", "The repair holds exactly the original data, with the same types"),
)


def verify_task(arguments, output, reference, workspace):
    found = {}

    def record(key, ok, message="", expected=None, actual=None):
        found[key] = {"ok": ok, "expected": expected, "actual": actual, "message": message}

    def skip(message):
        for key, _ in CONSTRAINTS:
            if key not in found:
                record(key, None, message)

    problem = answer_key_problem(arguments.case_id, reference)
    if problem:
        record("answer-key", False, problem)
        skip("Not checked: answer-key did not hold.")
        return _verdict(found, None)
    record("answer-key", True)
    _, truth_text = bundled(arguments.case_id)
    truth = strict_loads(truth_text)

    text = output.repaired_json
    if not isinstance(text, str):
        record("contract-shape", False, "repaired_json is not a string")
    elif not text.strip():
        record("contract-shape", False, "repaired_json is empty")
    else:
        record("contract-shape", True)
    if not found["contract-shape"]["ok"]:
        skip("Not checked: contract-shape did not hold.")
        return _verdict(found, None)

    found_problems = problems(text)
    syntax = [entry for entry in found_problems if entry[0] == SYNTAX]
    if syntax:
        _, message, line, column = syntax[0]
        record(
            "strict-json", False, f"{message} at line {line}, column {column}", actual={"line": line, "column": column}
        )
        skip("Not checked: strict-json did not hold.")
        return _verdict(found, None)
    record("strict-json", True)
    for key, kind in (("no-nonfinite", NON_FINITE), ("no-duplicate-keys", DUPLICATE_KEY)):
        messages = [message for entry_kind, message, _, _ in found_problems if entry_kind == kind]
        record(key, not messages, "; ".join(messages))
    if found_problems:
        skip("Not checked: the repair is not strict JSON.")
        return _verdict(found, None)

    difference = first_difference(truth, strict_loads(text))
    if difference is None:
        record("matches-original", True)
    else:
        path, message = difference
        record("matches-original", False, f"{path}: {message}")
    return _verdict(found, difference)


def _verdict(found, difference):
    constraints = [{"id": key, "constraint": text, **found[key]} for key, text in CONSTRAINTS]
    failed = [entry for entry in constraints if entry["ok"] is False]
    details = {"constraints": constraints, "first_difference": difference[0] if difference else None}
    if not failed:
        return result(True, "All 6 checks hold: the repair is strict JSON with exactly the original data.", **details)
    first = failed[0]
    more = f" (+{len(failed) - 1} more)" if len(failed) > 1 else ""
    return result(False, f"{first['id']}: {first['message']}{more}", **details)
