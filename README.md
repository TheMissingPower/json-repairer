# JSON Repairer

A `nanoagent.plugin/v0001` plugin. Its task, `repair-json`, gives an agent a
corrupted JSON text and asks for it back as strict JSON (RFC 8259) holding
exactly the data its author meant. The corruptions are the ones people and
programs really make: trailing commas, single quotes, unquoted keys, missing
commas, comments, Python's `True`/`False`/`None`, `NaN`, and a document cut off
before its last closers. A pure-code verifier, with no LLM, parses the repair
strictly and compares it with the original using strict types. The 28 cases are
bundled with the plugin, so the environment needs no network.

## Tools

| Tool | Does | Code |
|---|---|---|
| `pin_case` | The answer key. Pins the bundled case's broken text, the original document it was made from, and their sha256. Runs out of the agent's sight | `src/plugin/tools.py` |
| `get_case` | A case's broken text and the repair rules in words. Never the original | `src/plugin/tools.py` |
| `check_json` | Whether a text is strict JSON. If it isn't, gives the first problem with its line and column. It never repairs anything and never compares with the original | `src/plugin/tools.py`, `src/plugin/strict_json.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `repair-json` | Repairs a corrupted JSON text into strict JSON holding exactly the original data | `agent`, with `get_case` and `check_json`; reference `pin_case` |

## The task

Before the agent starts, NanoAgent runs `pin_case` with the task input
(`{"case_id": ...}`), out of the agent's sight, and pins its output. The agent
then has `get_case`, `check_json` and `submit`:

1. Call `get_case` once.
2. Write the repair by hand, and use `check_json` as often as needed.
3. Call `submit` with `{repaired_json}`.

**The rules** (stated in the task instructions and in `contract.RULES`):
- Fix syntax only. Never add, remove, rename or reorder keys or array items.
- Never change a value. `1` stays `1`, `1.0` stays `1.0`, and the string `"true"` stays a string.
- Write strict JSON: double-quoted keys and strings, with no comments, trailing commas, single quotes, `NaN` or `Infinity`.
- `True`, `False` and `None` become `true`, `false` and `null`.
- `NaN` and `Infinity` stand where the value was `null`, so write `null`.
- Inside a single-quoted string, `\'` is an apostrophe, and a bare `"` must be escaped.
- A document cut short at the very end needs only its missing closers.
- Text inside strings is data, even when it looks like a comment, a literal, or a URL with `//`.
- Whitespace and formatting don't matter.

## The cases

The 28 cases come from 13 hand-written, synthetic documents: an app config, a
product catalog, an API response, editor settings, feature flags, French UI
strings, an order, a CI pipeline, GeoJSON, sensor readings, edge shapes,
literal traps and user preferences. No real people's data is used. The
documents hold tricky but valid content on purpose:
- apostrophes, escaped `\"` and backslashes
- commas, braces, `//`, `/* */`, `"true"`, `"True"` and `"None"` inside strings
- accented letters and emoji
- `{}` and `[]`, and arrays of objects
- `1` beside `1.0`, booleans beside the strings `"true"`/`"false"`, and `null` beside `"null"`
- negative numbers, exponents, and a 20-digit integer

| Kind | Cases |
|---|---|
| One corruption | `trailing-comma-objects`, `trailing-comma-arrays`, `single-quoted-strings`, `single-quoted-keys`, `unquoted-keys`, `missing-commas`, `missing-closers`, `line-comments`, `block-comments`, `python-literals`, `nan-for-null` (with one trailing comma, since Python's `json.loads` accepts `NaN`) |
| Two to four at once | `combo-quotes-and-commas`, `combo-javascript-object`, `combo-python-repr`, `combo-comment-and-closer`, `combo-four-kinds`, `combo-unicode`, `combo-edge-shapes`, `combo-nan-and-python`, `combo-settings`, `combo-prefs` |
| Traps | `trap-apostrophe-single-quotes`, `trap-true-in-string`, `trap-python-words-quoted`, `trap-url-double-slash`, `trap-comment-text-in-string`, `trap-string-true-vs-bool`, `trap-backslash-single-quotes` |

`src/plugin/tools_dev/generate_cases.py` made the cases once, from seed 480,
and froze them in `src/plugin/cases.py`. It never edits text. Instead, it
writes each document out token by token, and each corruption is a separate,
deterministic function that marks sites in the document tree:
- a comma after this container's last item
- no comma before this item
- these quotes on this key or string
- this comment before this item
- `True` for this `true`
- `NaN` for this `null`
- drop the last k closers

Each mark becomes exactly one change, so every case has one repair, and
dropping the marks gives back the original exactly. The generator refuses
combinations that would lose information, such as a trailing comma just before
a dropped closer. It also asserts that every broken text fails both
`json.loads` and the strict parser. The verifier never regenerates anything.

## Ground truth and verification

The ground truth is the verifier's own copy of the case: `verifier/cases.py`
and `verifier/strict_json.py` are byte-for-byte copies of the tools' modules,
and a test enforces it, since the verifier sandbox may not import `src/`.
`verifier/task.py` judges the repair against 6 constraints, in order. Each
entry of the verdict's `details.constraints` is
`{id, constraint, ok, expected, actual, message}`. `ok` is `true` or `false`,
or `null` when the constraint was not checked because an earlier one failed.

| # | id | What it checks | Example failure message |
|---|---|---|---|
| 1 | `answer-key` | The pinned answer key is this case: broken text, original and sha256 | The answer key is for case single-quoted-strings, not missing-commas |
| 2 | `contract-shape` | `repaired_json` is a non-empty string | repaired_json is empty |
| 3 | `strict-json` | It parses as JSON | Expecting ',' delimiter at line 13, column 22 |
| 4 | `no-nonfinite` | No `NaN`, `Infinity` or `-Infinity` (Python's `json` accepts them; `parse_constant` catches them) | NaN is not JSON: strict JSON has no NaN or Infinity |
| 5 | `no-duplicate-keys` | No object names a key twice (`object_pairs_hook` catches it) | the key "status" appears 2 times in one object |
| 6 | `matches-original` | A deep comparison with strict types: a boolean is never an integer, and an integer is never a float. Key order is ignored; array order is not | $.data.users[0].active: expected boolean true, got integer 1 |

How it is scored:
- **Score 1.0** when all 6 checks hold; otherwise 0.0. There is no partial credit: a repair that changes any value is wrong.
- **The message** names the first failing constraint, with the JSON path of the first difference, e.g. `$.items[2].price`.
- **`details.first_difference`** holds that path on its own.

NanoAgent's contract layer already refuses a missing `repaired_json` or a
non-string one before the verifier runs. `contract-shape` checks again, in case
one gets through. Every tool call is checked too:
- `verify_output` holds `get_case` to the bundled broken text and the rules.
- It holds `check_json` to its own strict check of the same text.
- It holds `pin_case` to the case and its sha256.

## Limitations

- **The cases are public.** They ship in this repository, so a model trained on it could recall the originals.
- **28 fixed cases.** They cover each corruption alone and in combination, but not every way JSON gets broken.
- **Numbers are judged by value, not spelling.** `1e3` and `1000.0` are the same float. The broken texts write numbers as Python prints them, so `1e-3` appears as `0.001`.
- **Only corruptions with one repair.** Damage that loses information (a value cut off mid-way, a string missing its closing quote) is left out on purpose, since no verifier could know the intended value.
- **Only the final answer is judged.** The verifier doesn't look at how the agent got its repair.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions (no network), tools, task
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes; the rules
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # needed environment variable names (none here)
├── src/plugin/      # the MCP server (__main__.py), the tools (tools.py), strict JSON and the strict-type
│                    #   comparison (strict_json.py), the frozen cases (cases.py), and
│                    #   tools_dev/generate_cases.py (the documents and corruptions that made them)
├── tests/           # offline tests: the verifier, the tools and a whole scripted run, the case set,
│                    #   the generator, and the verifier sandbox rules
├── ui/              # how the page draws a repair: renderers.js and renderers.css
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier: one module per tool, the task's 6 constraints in task.py
```

## Develop and run

Install [uv](https://docs.astral.sh/uv/), then, from this folder:

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv lock --check
```

Everything is offline and deterministic: no network, no clock and no randomness
at run time. The tools write nothing to `NANOAGENT_WORKSPACE`. No model runs in
the tests: `tests/test_tools.py` scripts a whole run through the real tools and
the real verifier.

To regenerate the cases (only after changing the generator), run it as a module,
from this folder, so `contract.py` can be imported:

```bash
uv run python -m plugin.tools_dev.generate_cases   # rewrites src/plugin/cases.py and verifier/cases.py
```

`nanoagent plugin inspect .` checks every plugin rule locally. To publish, push
the plugin to a public GitHub repository and submit it on RUSH Lab.
