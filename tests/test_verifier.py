"""The repair-json verdict on correct, incorrect, missing, malformed and boundary repairs.

The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import CaseInput, PinOutput, RepairOutput
from plugin import pin_case
from plugin.cases import CASES


def reference(case_id: str, tmp_path: Path) -> PinOutput:
    return build_output(plain_output(pin_case(build_output({"case_id": case_id}, CaseInput), tmp_path)), PinOutput)


def judge(tmp_path: Path, case_id: str, text, *, pin="pinned", output=None):
    arguments = build_output({"case_id": case_id}, CaseInput)
    output = output or build_output({"repaired_json": text}, RepairOutput)
    key = reference(case_id, tmp_path) if pin == "pinned" else pin
    first = verifier.verify_task("repair-json", arguments, output, key, str(tmp_path))
    assert verifier.verify_task("repair-json", arguments, output, key, str(tmp_path)) == first, "deterministic"
    return first


def truth(case_id: str):
    return json.loads(CASES[case_id]["truth"])


def checks(verdict) -> dict:
    return {entry["id"]: entry["ok"] for entry in verdict["details"]["constraints"]}


def failed(verdict) -> list[str]:
    return [key for key, ok in checks(verdict).items() if ok is False]


# --- correct ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", list(CASES))
def test_every_ground_truth_passes(tmp_path: Path, case_id: str) -> None:
    verdict = judge(tmp_path, case_id, CASES[case_id]["truth"])
    assert verdict["valid"] is True and verdict["score"] == 1.0, verdict["message"]
    assert all(ok is True for ok in checks(verdict).values())
    assert verdict["message"] == "All 6 checks hold: the repair is strict JSON with exactly the original data."


def test_whitespace_and_key_order_do_not_matter(tmp_path: Path) -> None:
    def reorder(value):
        if isinstance(value, dict):
            return {key: reorder(value[key]) for key in reversed(list(value))}
        if isinstance(value, list):
            return [reorder(item) for item in value]
        return value

    text = json.dumps(reorder(truth("missing-commas")), indent=7, ensure_ascii=True)
    assert text != CASES["missing-commas"]["truth"]
    assert judge(tmp_path, "missing-commas", "\n\t " + text + "\r\n ")["valid"] is True


def test_escaped_unicode_is_the_same_text(tmp_path: Path) -> None:
    text = json.dumps(truth("combo-unicode"), ensure_ascii=True)
    assert "\\u00e7" in text and judge(tmp_path, "combo-unicode", text)["valid"] is True


# --- not JSON --------------------------------------------------------------------------------------


def test_the_broken_text_itself_fails(tmp_path: Path) -> None:
    verdict = judge(tmp_path, "missing-commas", CASES["missing-commas"]["broken"])
    assert failed(verdict) == ["strict-json"] and verdict["score"] == 0.0
    assert "line" in verdict["message"] and checks(verdict)["matches-original"] is None


def test_a_repair_still_invalid_fails(tmp_path: Path) -> None:
    text = CASES["trailing-comma-objects"]["truth"][:-1] + ",}"
    verdict = judge(tmp_path, "trailing-comma-objects", text)
    assert failed(verdict) == ["strict-json"]
    assert verdict["details"]["constraints"][2]["actual"]["line"] == 1


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_nan_or_infinity_left_in_fails(tmp_path: Path, token: str) -> None:
    text = CASES["nan-for-null"]["truth"].replace("null", token, 1)
    verdict = judge(tmp_path, "nan-for-null", text)
    assert failed(verdict) == ["no-nonfinite"] and token in verdict["message"]
    assert checks(verdict)["strict-json"] is True and checks(verdict)["matches-original"] is None


def test_duplicate_keys_fail(tmp_path: Path) -> None:
    text = '{"status": "ok", ' + CASES["missing-commas"]["truth"][1:]
    verdict = judge(tmp_path, "missing-commas", text)
    assert failed(verdict) == ["no-duplicate-keys"] and '"status"' in verdict["message"]


def test_a_python_literal_left_in_fails(tmp_path: Path) -> None:
    text = CASES["python-literals"]["truth"].replace("true", "True", 1)
    assert failed(judge(tmp_path, "python-literals", text)) == ["strict-json"]


# --- JSON, but not the original data -----------------------------------------------------------------


def mismatch(tmp_path: Path, case_id: str, value) -> dict:
    verdict = judge(tmp_path, case_id, json.dumps(value, ensure_ascii=False))
    assert failed(verdict) == ["matches-original"] and verdict["score"] == 0.0
    return verdict


def test_a_value_deleted_to_make_it_parse_fails(tmp_path: Path) -> None:
    value = truth("missing-commas")
    del value["data"]["users"][1]["score"]
    verdict = mismatch(tmp_path, "missing-commas", value)
    assert verdict["message"] == 'matches-original: $.data.users[1].score: the key "score" is missing'
    assert verdict["details"]["first_difference"] == "$.data.users[1].score"


def test_an_array_item_deleted_fails(tmp_path: Path) -> None:
    value = truth("trailing-comma-arrays")
    value["products"][0]["tags"].pop()
    assert (
        "$.products[0].tags: expected 2 items, got 1" in mismatch(tmp_path, "trailing-comma-arrays", value)["message"]
    )


def test_an_extra_key_fails(tmp_path: Path) -> None:
    value = truth("single-quoted-keys")
    value["flags"]["dark_mode"] = False
    assert "$.flags.dark_mode: the key" in mismatch(tmp_path, "single-quoted-keys", value)["message"]


def test_reordered_array_items_fail(tmp_path: Path) -> None:
    value = truth("missing-commas")
    value["data"]["users"].reverse()
    verdict = mismatch(tmp_path, "missing-commas", value)
    assert "$.data.users[0].id: expected integer 101, got integer 102" in verdict["message"]


def test_true_written_as_1_fails(tmp_path: Path) -> None:
    value = truth("missing-commas")
    value["data"]["users"][0]["active"] = 1
    verdict = mismatch(tmp_path, "missing-commas", value)
    assert "$.data.users[0].active: expected boolean true, got integer 1" in verdict["message"]


def test_float_written_as_int_fails(tmp_path: Path) -> None:
    value = truth("trailing-comma-objects")
    value["timeout_seconds"] = 30
    verdict = mismatch(tmp_path, "trailing-comma-objects", value)
    assert "$.timeout_seconds: expected float 30.0, got integer 30" in verdict["message"]


def test_int_written_as_float_fails(tmp_path: Path) -> None:
    value = truth("trailing-comma-objects")
    value["port"] = 8080.0
    assert "expected integer 8080, got float 8080.0" in mismatch(tmp_path, "trailing-comma-objects", value)["message"]


def test_null_written_as_the_string_null_fails(tmp_path: Path) -> None:
    value = truth("missing-commas")
    value["data"]["users"][0]["last_login"] = "null"
    verdict = mismatch(tmp_path, "missing-commas", value)
    assert '$.data.users[0].last_login: expected null null, got string "null"' in verdict["message"]


def test_the_string_true_written_as_a_boolean_fails(tmp_path: Path) -> None:
    value = truth("trap-string-true-vs-bool")
    value["flags"]["beta_banner"] = True
    assert "expected string" in mismatch(tmp_path, "trap-string-true-vs-bool", value)["message"]


def test_true_inside_a_string_changed_to_lowercase_fails(tmp_path: Path) -> None:
    value = truth("trap-true-in-string")
    value["labels"]["yes"] = "true"
    verdict = mismatch(tmp_path, "trap-true-in-string", value)
    assert '$.labels.yes: expected string "True", got string "true"' in verdict["message"]


def test_a_comment_like_url_cut_short_fails(tmp_path: Path) -> None:
    value = truth("trap-url-double-slash")
    value["homepage"] = "https:"
    assert "$.homepage" in mismatch(tmp_path, "trap-url-double-slash", value)["message"]


def test_a_big_integer_written_as_a_float_fails(tmp_path: Path) -> None:
    value = truth("combo-edge-shapes")
    value["big"] = float(value["big"])
    assert "$.big: expected integer" in mismatch(tmp_path, "combo-edge-shapes", value)["message"]


def test_an_odd_key_is_bracketed_in_the_path(tmp_path: Path) -> None:
    value = truth("combo-edge-shapes")
    value["odd key!"] = "changed"
    assert '$["odd key!"]' in mismatch(tmp_path, "combo-edge-shapes", value)["message"]


def test_a_different_root_type_fails(tmp_path: Path) -> None:
    assert "$: expected object" in mismatch(tmp_path, "missing-closers", [truth("missing-closers")])["message"]


# --- missing and malformed output -------------------------------------------------------------------


@pytest.mark.parametrize("text", ["", "   \n\t"])
def test_an_empty_repair_fails(tmp_path: Path, text: str) -> None:
    verdict = judge(tmp_path, "missing-commas", text)
    assert failed(verdict) == ["contract-shape"] and "empty" in verdict["message"]
    assert checks(verdict)["strict-json"] is None


def test_a_non_string_repair_fails(tmp_path: Path) -> None:
    # The contract refuses it first; the verifier refuses it too, should one reach it.
    with pytest.raises(ValueError, match="is not a str"):
        build_output({"repaired_json": {"status": "ok"}}, RepairOutput)
    with pytest.raises(ValueError, match="is not a str"):
        build_output({"repaired_json": 5}, RepairOutput)
    verdict = judge(tmp_path, "missing-commas", None, output=RepairOutput(repaired_json=truth("missing-commas")))
    assert failed(verdict) == ["contract-shape"] and "not a string" in verdict["message"]


def test_a_missing_field_is_refused_by_the_contract() -> None:
    with pytest.raises(ValueError, match="missing field"):
        build_output({}, RepairOutput)
    with pytest.raises(ValueError, match="does not declare"):
        build_output({"repaired": "{}"}, RepairOutput)


# --- the answer key ----------------------------------------------------------------------------------


def test_no_answer_key_fails(tmp_path: Path) -> None:
    verdict = judge(tmp_path, "missing-commas", CASES["missing-commas"]["truth"], pin=None)
    assert failed(verdict) == ["answer-key"] and checks(verdict)["matches-original"] is None


def test_another_cases_answer_key_fails(tmp_path: Path) -> None:
    other = reference("single-quoted-strings", tmp_path)
    verdict = judge(tmp_path, "missing-commas", CASES["missing-commas"]["truth"], pin=other)
    assert failed(verdict) == ["answer-key"] and "single-quoted-strings" in verdict["message"]


def test_a_tampered_answer_key_fails(tmp_path: Path) -> None:
    pin = plain_output(reference("missing-commas", tmp_path))
    pin["truth_json"] = pin["truth_json"].replace("101", "999")
    verdict = judge(tmp_path, "missing-commas", CASES["missing-commas"]["truth"], pin=build_output(pin, PinOutput))
    assert failed(verdict) == ["answer-key"] and "original" in verdict["message"]
