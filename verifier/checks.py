"""Checks shared by the tool verifiers. Pure functions of their arguments."""

from .cases import CASES
from .strict_json import fingerprint


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def bundled(case_id):
    """The bundled case's broken text and ground truth, as the verifier's own copy of cases.py holds them."""
    entry = CASES[case_id.value]
    return entry["broken"], entry["truth"]


def answer_key_problem(case_id, pin):
    """Why ``pin`` is not the answer key of the bundled case ``case_id``, or None."""
    if pin is None:
        return "There is no answer key: pin_case's output is missing"
    if pin.case_id != case_id:
        return f"The answer key is for case {pin.case_id.value}, not {case_id.value}"
    broken, truth = bundled(case_id)
    if pin.broken_json != broken:
        return f"The answer key's broken text is not the bundled case {case_id.value}'s"
    if pin.truth_json != truth:
        return f"The answer key's original is not the bundled case {case_id.value}'s"
    if pin.sha256 != fingerprint(broken, truth):
        return "The answer key's sha256 is not the case's"
    return None
