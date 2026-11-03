"""Write src/plugin/cases.py and its verifier copy: the bundled cases, each a broken text and its ground truth.

Each ground truth is a hand-written, synthetic JSON document below. The broken text is that document
written out token by token with corruptions at sites drawn from a fixed seed: each corruption is one
function that marks sites, and the writer turns every mark into exactly one change. Writing from the
tree, never editing text, means each case has one repair, and dropping the marks gives back the
document. Run once; the verifier only ever reads the frozen cases.py.

    uv run python -m plugin.tools_dev.generate_cases
"""

import json
import random
from pathlib import Path

from plugin.strict_json import first_difference, strict_loads

SEED = 480
ROOT = Path(__file__).resolve().parents[3]
TARGETS = (ROOT / "src" / "plugin" / "cases.py", ROOT / "verifier" / "cases.py")
INDENT = "  "
BARE_KEY_START = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_$"
BARE_KEY_REST = BARE_KEY_START + "0123456789"
LITERAL_WORDS = {"true", "false", "null"}
COMMENTS = (
    "TODO: review before release",
    "temporary override",
    "copied from staging",
    "see the changelog",
    "keep in sync with the docs",
    "added by hand",
)
ESCAPES = {"\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}

# --- the ground truth: synthetic documents, valid strict JSON ---------------------------------------

DOCUMENTS = {
    "app-config": r"""
{"name": "orbit-notes", "version": "2.4.1", "debug": false, "port": 8080, "timeout_seconds": 30.0,
 "retry": {"attempts": 3, "backoff": 1.5, "max_delay": 60},
 "features": ["sync", "offline", "dark-mode"],
 "database": {"host": "db.internal.example", "replicas": [], "options": {}},
 "homepage": "https://orbit-notes.example.com/docs//latest",
 "log_format": "[{time}] {level}: {message}",
 "proxy": null}
""",
    "product-catalog": r"""
{"store": "Lumen Hardware", "currency": "USD",
 "products": [
  {"sku": "LH-1001", "name": "Builder's Hammer", "price": 24.99, "in_stock": true,
   "tags": ["tools", "steel"], "discount": null},
  {"sku": "LH-1002", "name": "12\" Ruler, metric & imperial", "price": 7.5, "in_stock": false,
   "tags": [], "discount": 0.1},
  {"sku": "LH-1003", "name": "Cordless Drill {Pro}", "price": 129, "in_stock": true,
   "tags": ["power", "true"], "discount": null}],
 "total_products": 3}
""",
    "api-response": r"""
{"status": "ok", "code": 200,
 "data": {"users": [
   {"id": 101, "handle": "comet_rider", "active": true, "score": -12, "last_login": null},
   {"id": 102, "handle": "quiet.otter", "active": false, "score": 3.75e2, "last_login": "2026-10-30T14:22:05Z"}],
  "page": 1, "per_page": 2, "has_more": "false"},
 "errors": [], "request_id": "req_7f3a9c"}
""",
    "editor-settings": r"""
{"editor": {
  "theme": {"name": "Solar Dusk", "colors": {"background": "#1e1e2e", "foreground": "#cdd6f4"}},
  "font": {"family": "Fira Code", "size": 14, "line_height": 1.0},
  "keybindings": [{"key": "ctrl+/", "command": "toggle comment // line"},
                  {"key": "ctrl+shift+p", "command": "open palette"}]},
 "telemetry": {"enabled": false, "endpoint": null},
 "version": 3,
 "recent_files": ["C:\\projects\\notes.md", "/home/dev/todo.txt"]}
""",
    "feature-flags": r"""
{"flags": {"new_checkout": true, "beta_banner": "true", "legacy_api": false, "rollout_percent": 25,
           "experiment_ratio": 0.25, "kill_switch": null, "owner_note": "null means unset"},
 "updated_by": "release-bot", "environments": ["staging", "production"]}
""",
    "i18n-strings": r"""
{"locale": "fr-FR",
 "messages": {"greeting": "Bonjour, ça va ?", "farewell": "À bientôt !", "season": "l'été est arrivé",
              "quote": "Il a dit : \"Salut\"", "menu": "Café ☕ et crêpes 🥞"},
 "plural_rules": {"one": "{n} élément", "other": "{n} éléments"},
 "rtl": false}
""",
    "order": r"""
{"order_id": "ORD-2026-0042",
 "customer": {"name": "Avery Quill", "email": "avery.quill@example.com"},
 "items": [{"sku": "BK-17", "title": "Tea for Two: A Guide", "qty": 2, "unit_price": 12.0},
           {"sku": "MG-03", "title": "Mug, blue (12 oz)", "qty": 1, "unit_price": 9.95}],
 "shipping": {"method": "standard", "cost": 0,
              "address": {"line1": "1 Example Way", "line2": null, "city": "Springfield", "postal_code": "00000"}},
 "paid": true,
 "notes": "Leave at the door; don't ring."}
""",
    "ci-pipeline": r"""
{"pipeline": "build-and-test", "on": ["push", "pull_request"],
 "jobs": [{"name": "lint", "steps": ["checkout", "ruff check ."], "allow_failure": false},
          {"name": "test", "matrix": {"python": ["3.12", "3.13"], "os": ["ubuntu", "windows"]},
           "steps": ["checkout", "pytest -q"], "timeout_minutes": 20}],
 "env": {"PYTHONHASHSEED": "0", "CI": "true"},
 "artifacts": null}
""",
    "geo-features": r"""
{"type": "FeatureCollection",
 "features": [
  {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-95.4018, 29.7174]},
   "properties": {"name": "Campus Lake", "elevation_m": -3, "visited": true}},
  {"type": "Feature",
   "geometry": {"type": "LineString", "coordinates": [[-95.4, 29.71], [-95.39, 29.72], [-95.38, 29.725]]},
   "properties": {"name": "Loop Trail", "elevation_m": 12.5, "visited": false}}],
 "bbox": [-95.41, 29.7, -95.37, 29.73]}
""",
    "sensor-readings": r"""
{"device": "thermo-7", "unit": "celsius",
 "readings": [{"t": 0, "value": 21.5, "ok": true}, {"t": 60, "value": -4.25, "ok": true},
              {"t": 120, "value": null, "ok": false}, {"t": 180, "value": 1e-3, "ok": true},
              {"t": 240, "value": null, "ok": false}],
 "calibration": {"offset": 0.0, "scale": 1, "reference": 6.02e23},
 "alerts": []}
""",
    "edge-shapes": r"""
{"empty_object": {}, "empty_array": [], "nested_empty": [[], [{}], {"a": []}],
 "zero": 0, "big": 12345678901234567890, "small_float": -2.5E-4,
 "empty_string": "", "padded": "  spaced  ", "braces": "{not: [an object]}",
 "comma_list": "a, b, c", "null_string": "null", "none_text": "None of the above",
 "odd key!": "keys need not be identifiers", "tail": [1, [2, [3]]]}
""",
    "literal-traps": r"""
{"title": "True Detective notes",
 "answers": [true, false, null],
 "labels": {"yes": "True", "no": "False", "maybe": "None"},
 "quote": "He said 'True' twice",
 "link": "https://example.org/a//b?q=True",
 "flags": [false, true, null],
 "comment": "/* not a comment */ and // neither"}
""",
    "user-prefs": r"""
{"profile": {"display_name": "Jordan Example", "handle": "jx_42",
             "bio": "Likes \"quotes\", commas, and {braces}."},
 "notifications": {"email": true, "sms": false, "digest": "weekly"},
 "privacy": {"show_email": false, "blocked": []},
 "limits": {"daily_minutes": 90, "weekly_hours": 10.5}}
""",
}


# --- sites: where each corruption can go, in document order ------------------------------------------


def walk(value, path=()):
    """Every (path, value) in the document, depth first, the root first."""
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, path + (index,))


def items(container):
    return list(container.items()) if isinstance(container, dict) else list(enumerate(container))


def closing_chain(doc):
    """The containers whose closers end the document, outermost first: dropping k of them drops the last k."""
    chain, path, value = [], (), doc
    while isinstance(value, (dict, list)) and value:
        chain.append(path)
        key, value = items(value)[-1]
        path = path + (key,)
    if isinstance(value, (dict, list)):
        chain.append(path)
    return chain


def is_bare_key(key):
    return bool(key) and key[0] in BARE_KEY_START and all(c in BARE_KEY_REST for c in key) and key not in LITERAL_WORDS


def new_marks():
    return {
        "trailing_comma": set(),
        "single_key": set(),
        "bare_key": set(),
        "single_value": set(),
        "no_comma": set(),
        "line_comment": {},
        "block_comment": {},
        "python_literal": set(),
        "non_finite": {},
        "closers": [],
    }


def pick(rng, sites, count, what):
    sites = list(sites)
    if len(sites) < count:
        raise ValueError(f"only {len(sites)} site(s) for {what}, not {count}")
    return rng.sample(sites, count)


def anywhere(value):
    return True


# --- the corruptions: each marks `count` sites whose value passes `only` -----------------------------


def trailing_commas(doc, rng, marks, count, only=anywhere):
    """A comma after the last item of an object or array."""
    sites = [p for p, v in walk(doc) if isinstance(v, (dict, list)) and v and only(v) and p not in marks["closers"]]
    marks["trailing_comma"].update(pick(rng, sites, count, "trailing commas"))


def single_quoted_keys(doc, rng, marks, count, only=anywhere):
    """'key' for "key"."""
    sites = [p for p, _ in walk(doc) if p and isinstance(p[-1], str) and only(p[-1]) and p not in marks["bare_key"]]
    marks["single_key"].update(pick(rng, sites, count, "single-quoted keys"))


def unquoted_keys(doc, rng, marks, count, only=anywhere):
    """key for "key", only for keys a JavaScript identifier could be."""
    sites = [p for p, _ in walk(doc) if p and isinstance(p[-1], str) and is_bare_key(p[-1]) and only(p[-1])]
    sites = [p for p in sites if p not in marks["single_key"]]
    marks["bare_key"].update(pick(rng, sites, count, "unquoted keys"))


def single_quoted_strings(doc, rng, marks, count, only=anywhere):
    """'text' for "text": a ' inside becomes \\' and a " inside is left bare."""
    sites = [p for p, v in walk(doc) if isinstance(v, str) and only(v)]
    marks["single_value"].update(pick(rng, sites, count, "single-quoted strings"))


def missing_commas(doc, rng, marks, count, only=anywhere):
    """No comma between two items of an object or array."""
    sites = [(p, i) for p, i, item in item_sites(doc) if i and only(item)]
    marks["no_comma"].update(pick(rng, sites, count, "missing commas"))


def item_sites(doc):
    """(container path, index, item) for every item of every object and array."""
    return [(p, i, item) for p, v in walk(doc) if isinstance(v, (dict, list)) for i, (_, item) in enumerate(items(v))]


def comment_sites(doc, marks, only):
    taken = set(marks["line_comment"]) | set(marks["block_comment"])
    return [(p, i) for p, i, item in item_sites(doc) if only(item) and (p, i) not in taken]


def line_comments(doc, rng, marks, count, only=anywhere):
    """A // comment on its own line before an item."""
    for site in pick(rng, comment_sites(doc, marks, only), count, "line comments"):
        marks["line_comment"][site] = rng.choice(COMMENTS)


def block_comments(doc, rng, marks, count, only=anywhere):
    """A /* */ comment just before an item."""
    for site in pick(rng, comment_sites(doc, marks, only), count, "block comments"):
        marks["block_comment"][site] = rng.choice(COMMENTS)


def python_literals(doc, rng, marks, count, only=anywhere):
    """True, False and None for true, false and null."""
    sites = [p for p, v in walk(doc) if (v is None or isinstance(v, bool)) and only(v) and p not in marks["non_finite"]]
    marks["python_literal"].update(pick(rng, sites, count, "Python literals"))


def non_finite(doc, rng, marks, count, only=anywhere):
    """NaN or Infinity where the original value is null: the task says these become null."""
    sites = [p for p, v in walk(doc) if v is None and p not in marks["python_literal"]]
    for site in pick(rng, sites, count, "NaN or Infinity"):
        marks["non_finite"][site] = rng.choice(("NaN", "Infinity"))


def missing_closers(doc, rng, marks, count, only=anywhere):
    """The last `count` closing braces or brackets of the document dropped."""
    chain = closing_chain(doc)
    if len(chain) < count:
        raise ValueError(f"the document ends with only {len(chain)} closer(s), not {count}")
    dropped = chain[len(chain) - count :]
    if set(dropped) & marks["trailing_comma"]:
        raise ValueError("a dropped closer would follow a trailing comma, which has no single repair")
    marks["closers"] = dropped


LABELS = {
    trailing_commas: "trailing commas",
    single_quoted_keys: "single-quoted keys",
    unquoted_keys: "unquoted keys",
    single_quoted_strings: "single-quoted strings",
    missing_commas: "missing commas",
    line_comments: "// comments",
    block_comments: "/* */ comments",
    python_literals: "Python literals True/False/None",
    non_finite: "NaN/Infinity for null",
    missing_closers: "missing closers at the end",
}


# --- the writer: the document, token by token, with every mark applied --------------------------------


def string(text, quote='"'):
    out = []
    for char in text:
        if char in ESCAPES:
            out.append(ESCAPES[char])
        elif char == quote:
            out.append("\\" + quote)
        elif ord(char) < 0x20:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    return quote + "".join(out) + quote


def scalar(value, path, marks):
    if isinstance(value, str):
        return string(value, "'" if path in marks["single_value"] else '"')
    if path in marks["non_finite"]:
        return marks["non_finite"][path]
    if path in marks["python_literal"]:
        return {True: "True", False: "False", None: "None"}[value]
    return json.dumps(value)


def key_text(path, marks):
    key = path[-1]
    if path in marks["bare_key"]:
        return key
    return string(key, "'" if path in marks["single_key"] else '"')


def write(value, marks, path=(), depth=0):
    if not isinstance(value, (dict, list)):
        return scalar(value, path, marks)
    opener, closer = ("{", "}") if isinstance(value, dict) else ("[", "]")
    if not value:
        return opener + closer
    inner, outer = INDENT * (depth + 1), INDENT * depth
    lines = []
    entries = items(value)
    for index, (key, item) in enumerate(entries):
        child = path + (key,)
        if (path, index) in marks["line_comment"]:
            lines.append(f"{inner}// {marks['line_comment'][(path, index)]}")
        text = write(item, marks, child, depth + 1)
        if isinstance(value, dict):
            text = f"{key_text(child, marks)}: {text}"
        if (path, index) in marks["block_comment"]:
            text = f"/* {marks['block_comment'][(path, index)]} */ {text}"
        last = index == len(entries) - 1
        comma = (path in marks["trailing_comma"]) if last else ((path, index + 1) not in marks["no_comma"])
        lines.append(inner + text + ("," if comma else ""))
    return opener + "\n" + "\n".join(lines) + "\n" + outer + closer


def corrupt(doc, corruptions, rng):
    marks = new_marks()
    for function, count, only in corruptions:
        function(doc, rng, marks, count, only)
    text = write(doc, marks)
    for _ in marks["closers"]:
        assert text[-1] in "]}", text[-20:]
        text = text[:-1].rstrip()
    return text


# --- the cases ---------------------------------------------------------------------------------------


def c(function, count=1, only=anywhere):
    return function, count, only


CASES = [
    # One kind of corruption.
    ("trailing-comma-objects", "app-config", "Trailing commas after the last member of objects.",
     [c(trailing_commas, 2, lambda v: isinstance(v, dict))]),
    ("trailing-comma-arrays", "product-catalog", "Trailing commas after the last item of arrays.",
     [c(trailing_commas, 2, lambda v: isinstance(v, list))]),
    ("single-quoted-strings", "order", "Some string values are in single quotes.",
     [c(single_quoted_strings, 3)]),
    ("single-quoted-keys", "feature-flags", "Some keys are in single quotes.",
     [c(single_quoted_keys, 3)]),
    ("unquoted-keys", "editor-settings", "Some keys have no quotes at all, JavaScript style.",
     [c(unquoted_keys, 4)]),
    ("missing-commas", "api-response", "Two commas between items are missing.",
     [c(missing_commas, 2)]),
    ("missing-closers", "geo-features", "The document stops before its last two closers.",
     [c(missing_closers, 2)]),
    ("line-comments", "ci-pipeline", "Two // comments on lines of their own.",
     [c(line_comments, 2)]),
    ("block-comments", "sensor-readings", "Two /* */ comments before items.",
     [c(block_comments, 2)]),
    ("python-literals", "feature-flags", "Python's True, False and None in place of true, false and null.",
     [c(python_literals, 3)]),
    ("nan-for-null", "sensor-readings", "NaN or Infinity where a reading is null, and a trailing comma.",
     [c(non_finite, 2), c(trailing_commas, 1)]),
    # Two to four kinds at once.
    ("combo-quotes-and-commas", "product-catalog", "Single-quoted strings and a trailing comma.",
     [c(single_quoted_strings, 2), c(trailing_commas, 1)]),
    ("combo-javascript-object", "app-config", "Unquoted keys, a // comment and a trailing comma, as in JavaScript.",
     [c(unquoted_keys, 3), c(line_comments, 1), c(trailing_commas, 1)]),
    ("combo-python-repr", "api-response", "Single quotes on keys and strings and Python literals, as Python prints.",
     [c(single_quoted_keys, 3), c(single_quoted_strings, 2), c(python_literals, 2)]),
    ("combo-comment-and-closer", "geo-features", "A /* */ comment and a missing final brace.",
     [c(block_comments, 1), c(missing_closers, 1)]),
    ("combo-four-kinds", "order", "Unquoted keys, a missing comma, a Python literal and a missing final brace.",
     [c(unquoted_keys, 2), c(missing_commas, 1), c(python_literals, 1), c(missing_closers, 1)]),
    ("combo-unicode", "i18n-strings", "Single-quoted accented and emoji strings and a trailing comma.",
     [c(single_quoted_strings, 2, lambda v: any(ord(ch) > 127 for ch in v)), c(trailing_commas, 1)]),
    ("combo-edge-shapes", "edge-shapes", "Trailing commas and a missing comma around empty and nested containers.",
     [c(trailing_commas, 2), c(missing_commas, 1)]),
    ("combo-nan-and-python", "sensor-readings", "NaN or Infinity for null, Python literals and a // comment.",
     [c(non_finite, 1), c(python_literals, 2), c(line_comments, 1)]),
    ("combo-settings", "editor-settings", "Single-quoted strings, a /* */ comment and missing final closers.",
     [c(single_quoted_strings, 2), c(block_comments, 1), c(missing_closers, 2)]),
    ("combo-prefs", "user-prefs", "Unquoted keys, a single-quoted string and a trailing comma.",
     [c(unquoted_keys, 2), c(single_quoted_strings, 1), c(trailing_commas, 1)]),
    # Traps: text that looks like a corruption but is data.
    ("trap-apostrophe-single-quotes", "i18n-strings",
     "Single-quoted strings that hold an apostrophe (escaped \\') or a double quote (left bare).",
     [c(single_quoted_strings, 2, lambda v: "'" in v or '"' in v)]),
    ("trap-true-in-string", "literal-traps", "Python literals, while the strings \"True\", \"False\" and \"None\" stay.",
     [c(python_literals, 4)]),
    ("trap-python-words-quoted", "literal-traps", "Python literals beside single-quoted strings 'True' and 'None'.",
     [c(python_literals, 3), c(single_quoted_strings, 2, lambda v: v in ("True", "None"))]),
    ("trap-url-double-slash", "app-config", "// comments in a document whose URL holds // too.",
     [c(line_comments, 2), c(trailing_commas, 1)]),
    ("trap-comment-text-in-string", "literal-traps", "Real comments beside a string that holds /* */ and //.",
     [c(block_comments, 1), c(line_comments, 1)]),
    ("trap-string-true-vs-bool", "feature-flags", "Python literals beside the string \"true\", which stays a string.",
     [c(python_literals, 2), c(unquoted_keys, 2)]),
    ("trap-backslash-single-quotes", "editor-settings", "A single-quoted Windows path, its backslashes escaped.",
     [c(single_quoted_strings, 1, lambda v: "\\" in v), c(trailing_commas, 1)]),
]  # fmt: skip


def build():
    documents = {name: strict_loads(text) for name, text in DOCUMENTS.items()}
    for name, doc in documents.items():
        rewritten = strict_loads(write(doc, new_marks()))
        assert first_difference(doc, rewritten) is None, f"{name}: the writer changes the document"
    cases = {}
    for case_id, name, note, corruptions in CASES:
        doc = documents[name]
        broken = corrupt(doc, corruptions, random.Random(f"{SEED}:{case_id}"))
        try:
            json.loads(broken)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{case_id}: json.loads accepts the broken text")
        try:
            strict_loads(broken)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{case_id}: strict_loads accepts the broken text")
        labels = tuple(f"{LABELS[function]} x{count}" for function, count, _ in corruptions)
        truth = json.dumps(doc, ensure_ascii=False)
        cases[case_id] = {"note": note, "document": name, "corruptions": labels, "broken": broken, "truth": truth}
    return cases


def source(cases):
    out = [
        '"""The bundled cases: each a broken text and the ground truth it was made from, as strict JSON text.',
        "",
        "Generated by tools_dev/generate_cases.py and frozen here: do not edit by hand. verifier/cases.py is a",
        "byte-for-byte copy, and contract.CaseId lists the same ids; tests enforce both.",
        '"""',
        "",
        "CASES = {",
    ]
    for case_id, case in cases.items():
        out.append(f"    {case_id!r}: {{")
        out.append(f"        'note': {case['note']!r},")
        out.append(f"        'document': {case['document']!r},")
        out.append(f"        'corruptions': {case['corruptions']!r},")
        out.append("        'broken': (")
        lines = case["broken"].split("\n")
        for index, line in enumerate(lines):
            piece = line + "\n" if index < len(lines) - 1 else line
            out.append(f"            {piece!r}")
        out.append("        ),")
        out.append(f"        'truth': {case['truth']!r},")
        out.append("    },")
    out.append("}")
    return "\n".join(out) + "\n"


def main():
    text = source(build())
    for target in TARGETS:
        target.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
