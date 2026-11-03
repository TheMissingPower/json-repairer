"""The frozen case set: well formed, the same ids as the contract, every broken text refused, every
ground truth strict, and the verifier's copies byte-for-byte the tools'."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contract import CaseId
from plugin.cases import CASES
from plugin.strict_json import problems, strict_loads

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("module", ["cases.py", "strict_json.py"])
def test_the_verifier_copies_are_the_tools(module: str) -> None:
    assert (ROOT / "verifier" / module).read_bytes() == (ROOT / "src" / "plugin" / module).read_bytes(), (
        f"verifier/{module} must be a byte-for-byte copy of src/plugin/{module}"
    )


def test_the_contract_lists_every_case() -> None:
    assert [case.value for case in CaseId] == list(CASES)


def test_there_are_single_combined_and_trap_cases() -> None:
    assert 25 <= len(CASES) <= 30
    assert sum(len(case["corruptions"]) == 1 for case in CASES.values()) >= 8
    assert sum(2 <= len(case["corruptions"]) <= 4 for case in CASES.values()) >= 10
    assert sum(case_id.startswith("trap-") for case_id in CASES) >= 5
    assert len({case["document"] for case in CASES.values()}) >= 10


def test_every_kind_of_corruption_is_used() -> None:
    used = {label.rsplit(" x", 1)[0] for case in CASES.values() for label in case["corruptions"]}
    assert used == {
        "trailing commas",
        "single-quoted keys",
        "unquoted keys",
        "single-quoted strings",
        "missing commas",
        "// comments",
        "/* */ comments",
        "Python literals True/False/None",
        "NaN/Infinity for null",
        "missing closers at the end",
    }


@pytest.mark.parametrize("case_id", list(CASES))
def test_each_broken_text_fails_json_loads(case_id: str) -> None:
    broken = CASES[case_id]["broken"]
    with pytest.raises(ValueError):
        json.loads(broken)
    assert problems(broken)


@pytest.mark.parametrize("case_id", list(CASES))
def test_each_ground_truth_is_strict_json(case_id: str) -> None:
    case = CASES[case_id]
    assert problems(case["truth"]) == []
    assert isinstance(strict_loads(case["truth"]), dict)
    assert case["note"].strip() and case["broken"] != case["truth"]


def test_the_ground_truth_holds_the_tricky_values() -> None:
    texts = " ".join(case["truth"] for case in CASES.values())
    for needle in ["'", '\\"', "//", "/*", '"true"', '"null"', '"True"', "1.0", "e+23", "-12", "{}", "[]", "\\\\"]:
        assert needle in texts, needle
    assert any(ord(char) > 127 for char in texts)
