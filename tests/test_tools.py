from __future__ import annotations

import json
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import RULES, CaseInput, CaseOutput, CheckInput, CheckOutput, PinOutput, RepairOutput, Tool
from plugin import check_json, get_case, pin_case
from plugin.__main__ import IMPLEMENTATIONS
from plugin.cases import CASES


def case_input(case_id: str) -> CaseInput:
    return build_output({"case_id": case_id}, CaseInput)


def checked(text: str, tmp_path: Path) -> CheckOutput:
    given = build_output({"text": text}, CheckInput)
    made = build_output(plain_output(check_json(given, tmp_path)), CheckOutput)
    assert verifier.verify_input("check_json", given)["valid"] is True
    assert verifier.verify_output("check_json", given, made, str(tmp_path))["valid"] is True
    return made


def test_get_case_gives_the_broken_text_and_rules(tmp_path: Path) -> None:
    made = build_output(plain_output(get_case(case_input("missing-commas"), tmp_path)), CaseOutput)
    assert made.broken_json == CASES["missing-commas"]["broken"] and made.rules == RULES
    assert verifier.verify_output("get_case", case_input("missing-commas"), made, str(tmp_path))["valid"] is True


def test_get_case_never_shows_the_ground_truth(tmp_path: Path) -> None:
    made = plain_output(get_case(case_input("missing-commas"), tmp_path))
    assert set(made) == {"case_id", "broken_json", "rules"}
    assert CASES["missing-commas"]["truth"] not in json.dumps(made, ensure_ascii=False)


def test_a_changed_case_is_refused(tmp_path: Path) -> None:
    made = plain_output(get_case(case_input("missing-commas"), tmp_path))
    changed = build_output({**made, "broken_json": CASES["missing-commas"]["truth"]}, CaseOutput)
    assert verifier.verify_output("get_case", case_input("missing-commas"), changed, str(tmp_path))["valid"] is False


def test_check_json_accepts_strict_json(tmp_path: Path) -> None:
    made = checked(CASES["combo-unicode"]["truth"], tmp_path)
    assert (made.valid, made.error, made.line, made.column) == (True, None, None, None)


def test_check_json_gives_the_line_and_column_of_a_syntax_error(tmp_path: Path) -> None:
    made = checked('{\n  "a": 1,\n  "b": 2,\n}', tmp_path)
    assert made.valid is False and (made.line, made.column) == (4, 1)
    assert "property name" in made.error


@pytest.mark.parametrize(
    ("text", "says"),
    [('{"a": NaN}', "NaN"), ("[Infinity]", "Infinity"), ('{"a": 1, "a": 1}', "appears 2 times"), ("", "Expecting")],
)
def test_check_json_refuses_what_pythons_json_lets_through(tmp_path: Path, text: str, says: str) -> None:
    made = checked(text, tmp_path)
    assert made.valid is False and says in made.error


def test_check_json_never_repairs(tmp_path: Path) -> None:
    made = plain_output(check_json(build_output({"text": "{'a': 1}"}, CheckInput), tmp_path))
    assert set(made) == {"valid", "error", "line", "column"}


def test_a_wrong_check_is_refused(tmp_path: Path) -> None:
    given = build_output({"text": "[1, 2,]"}, CheckInput)
    lie = build_output({"valid": True, "error": None, "line": None, "column": None}, CheckOutput)
    assert verifier.verify_output("check_json", given, lie, str(tmp_path))["valid"] is False


def test_pin_case_is_the_bundled_case(tmp_path: Path) -> None:
    made = build_output(plain_output(pin_case(case_input("combo-four-kinds"), tmp_path)), PinOutput)
    assert made.truth_json == CASES["combo-four-kinds"]["truth"] and len(made.sha256) == 64
    assert verifier.verify_output("pin_case", case_input("combo-four-kinds"), made, str(tmp_path))["valid"] is True
    tampered = build_output({**plain_output(made), "sha256": "0" * 64}, PinOutput)
    assert verifier.verify_output("pin_case", case_input("combo-four-kinds"), tampered, str(tmp_path))["valid"] is False


def test_a_whole_run_as_nanoagent_drives_it(tmp_path: Path) -> None:
    """The reference first, then get_case, check_json on the broken text and on the repair, then submit."""
    arguments = case_input("trap-python-words-quoted")
    key = build_output(plain_output(pin_case(arguments, tmp_path)), PinOutput)
    broken = build_output(plain_output(get_case(arguments, tmp_path)), CaseOutput).broken_json
    assert checked(broken, tmp_path).valid is False
    # Quotes first, so the strings "True" and "None" are never taken for literals; then the bare literals.
    # Anchored on ": ", since "He said 'True' twice" holds 'True' too.
    repair = broken.replace(": 'True'", ': "True"').replace(": 'None'", ': "None"')
    repair = repair.replace("None\n", "null\n").replace("False,", "false,")
    assert checked(repair, tmp_path).valid is True
    output = build_output({"repaired_json": repair}, RepairOutput)
    verdict = verifier.verify_task("repair-json", arguments, output, key, str(tmp_path))
    assert verdict["valid"] is True, verdict["message"]


def test_a_blind_find_and_replace_falls_into_the_trap(tmp_path: Path) -> None:
    arguments = case_input("trap-true-in-string")
    key = build_output(plain_output(pin_case(arguments, tmp_path)), PinOutput)
    broken = CASES["trap-true-in-string"]["broken"]
    blind = broken.replace("True", "true").replace("False", "false").replace("None", "null")
    output = build_output({"repaired_json": blind}, RepairOutput)
    verdict = verifier.verify_task("repair-json", arguments, output, key, str(tmp_path))
    assert verdict["valid"] is False and verdict["message"].startswith("matches-original: $.title")


def test_the_server_implements_every_tool() -> None:
    assert set(IMPLEMENTATIONS) == set(Tool)


def test_tools_write_nothing(tmp_path: Path) -> None:
    pin_case(case_input("combo-unicode"), tmp_path)
    get_case(case_input("combo-unicode"), tmp_path)
    check_json(build_output({"text": "{}"}, CheckInput), tmp_path)
    assert list(tmp_path.iterdir()) == []
