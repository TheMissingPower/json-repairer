"""The generator: deterministic, its writer faithful, and its frozen output exactly what it writes."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from plugin.strict_json import first_difference, strict_loads
from plugin.tools_dev import generate_cases as generator

ROOT = Path(__file__).resolve().parents[1]


def test_the_frozen_cases_are_what_the_generator_writes() -> None:
    text = generator.source(generator.build())
    assert (ROOT / "src" / "plugin" / "cases.py").read_text(encoding="utf-8") == text
    assert generator.source(generator.build()) == text, "deterministic"


@pytest.mark.parametrize("name", list(generator.DOCUMENTS))
def test_the_writer_without_marks_is_the_document(name: str) -> None:
    doc = strict_loads(generator.DOCUMENTS[name])
    assert first_difference(doc, strict_loads(generator.write(doc, generator.new_marks()))) is None


def test_single_quotes_escape_apostrophes_and_leave_double_quotes_bare() -> None:
    assert generator.string('l\'été "x"', "'") == "'l\\'été \"x\"'"
    assert generator.string("a\\b\n", '"') == '"a\\\\b\\n"'


def test_unquoted_keys_are_only_identifiers() -> None:
    assert generator.is_bare_key("rollout_percent") and generator.is_bare_key("$id")
    assert not generator.is_bare_key("odd key!") and not generator.is_bare_key("1st")
    assert not generator.is_bare_key("null") and not generator.is_bare_key("")


def test_a_closer_after_a_trailing_comma_is_refused() -> None:
    doc = {"a": [1, 2]}
    marks = generator.new_marks()
    marks["trailing_comma"].add(("a",))
    with pytest.raises(ValueError, match="no single repair"):
        generator.missing_closers(doc, random.Random(0), marks, 2)
