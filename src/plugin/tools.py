from __future__ import annotations

from pathlib import Path

from contract import RULES, CaseInput, CaseOutput, CheckInput, CheckOutput, PinOutput
from plugin.cases import CASES
from plugin.strict_json import check, fingerprint


def pin_case(given: CaseInput, workspace: Path) -> PinOutput:
    """The answer key: the bundled case's broken text, the original it was made from, and their fingerprint."""
    case = CASES[given.case_id.value]
    return PinOutput(
        case_id=given.case_id,
        broken_json=case["broken"],
        truth_json=case["truth"],
        sha256=fingerprint(case["broken"], case["truth"]),
    )


def get_case(given: CaseInput, workspace: Path) -> CaseOutput:
    return CaseOutput(case_id=given.case_id, broken_json=CASES[given.case_id.value]["broken"], rules=RULES)


def check_json(given: CheckInput, workspace: Path) -> CheckOutput:
    valid, error, line, column = check(given.text)
    return CheckOutput(valid=valid, error=error, line=line, column=column)
