# CLAUDE.md — working in this documentation repo

Instructions for an AI assistant editing or using these docs.

## What this repo is

Documentation for **`ucscsdk` 0.9.0.10**, the Cisco **UCS Central** Python SDK.
The SDK itself is a clone at `../ucscsdk/` (untracked). **Never modify it.** These docs
describe it; they do not patch it.

`ucscsdk` is not `ucsmsdk`. UCS Central, not UCS Manager. Do not copy examples between them.

## Before you write ucscsdk code

Read [`agents/AGENTS.md`](agents/AGENTS.md). It has the ten canonical recipes, the DN
pattern table, and a do-not-do list that covers the mistakes that actually occur —
forgetting `commit()`, guessing DNs, using the default wildcard filter when you meant
equality, and calling the eight SDK functions that are broken on modern Python.

To look up a class you do not know:

```bash
grep '"class_id": "LsServer"' docs/agents/mo-details.jsonl
```

One line back, complete: every property with restrictions, plus every `<Class>Consts` value.
For a routing-level answer, `agents/mo-index.json` is small enough to load whole.

## Before you edit these docs

**Use `/usr/bin/python3` for everything.** It has `six` and `pyparsing`. The `python3` first
on `$PATH` may be a uv interpreter with neither, under which `import ucscsdk.ucschandle`
fails outright. That is a wrong-interpreter symptom, not a broken SDK.

The SDK is not pip-installed. Scripts do `sys.path.insert(0, "<repo>/ucscsdk")`.

## After you edit these docs

Run the gate. It is not optional:

```bash
/usr/bin/python3 docs/_tools/verify_docs.py    # must exit 0
```

It resolves every code block, import, dotted symbol, MO class id, property reference,
function signature, internal link and `file.py:NN` reference against the installed package.
If it fires, **fix the doc** — do not add an allowlist entry. `SYMBOL_ALLOW` has exactly one
entry and should stay that way.

Two things it deliberately skips, both to avoid false positives, both documented in the
script: inline code spans when checking links (property regexes look like markdown links),
and unlabelled ``` fences when scanning prose (they hold pasted terminal output, including
the checker's own failure messages). Labelled ```python blocks are always scanned.

## Do not hand-edit generated files

`reference/**` and `agents/*.json*` come from
[`_tools/gen_reference.py`](_tools/gen_reference.py). Edit the script and regenerate:

```bash
/usr/bin/python3 docs/_tools/gen_reference.py
```

It is deterministic — two runs are byte-identical. If a rerun produces a diff you did not
intend, that is a bug in your change.

## Ground rules for content

1. **Zero invented API.** If you cannot point at the file and line, it does not go in.
   The verifier enforces this mechanically for symbols; for behaviour, run it.
2. **No live UCS Central is available.** Never claim an example was executed against
   hardware. Mark server-dependent snippets; run everything else offline and say so.
3. **Prefer measurement to assertion.** Counts, distributions and behaviours in these docs
   were produced by introspecting or executing the package. If you add a number, compute it.
4. **Record defects, do not fix them.** Several SDK functions are broken. They are
   documented in `README.md`, `internals/architecture.md` and `AGENTS.md`. Patching the
   clone is out of scope.

## Where things are

| Need | File |
|---|---|
| Routing for any consumer | [`llms.txt`](llms.txt) |
| Human entry point | [`README.md`](README.md) |
| Agent operating manual | [`agents/AGENTS.md`](agents/AGENTS.md) |
| How the client works | [`internals/architecture.md`](internals/architecture.md) |
| One request, end to end | [`internals/request-lifecycle.md`](internals/request-lifecycle.md) |
| Reasoning about unseen classes | [`internals/metadata-system.md`](internals/metadata-system.md) |
| Accumulated verified findings | [`_work/NOTES.md`](_work/NOTES.md) |
| Proof the docs are correct | [`_work/VERIFICATION.md`](_work/VERIFICATION.md) |
| Where the old guide is wrong | [`_work/UG-RST-AUDIT.md`](_work/UG-RST-AUDIT.md) |

`_work/NOTES.md` is the accumulated memory across all phases of this project. Read it before
making non-trivial changes — it records what was verified, what was measured, and which
plausible-looking assumptions turned out to be false.

## Facts most likely to trip you up

- `MO_CLASS_ID` and `METHOD_CLASS_ID` are **frozensets**, not dicts. `MO_CLASS_META` is the
  dict.
- `load_class` is **case-sensitive**; normalise with
  `find_class_id_in_mo_meta_ignore_case` first.
- `to_xml_str` returns **bytes**.
- The default `filter_str` type is **`re`** (wildcard), not `eq`.
- Only `query_classid` and `query_children` accept `filter_str`.
- A failed `commit()` **discards the buffer**.
- `MethodPropertyMeta.name` raises `RecursionError` — never touch it; use the dict key.
- The SDK's test suite does not run (`nose`). `_tools/nose_shim.py` makes the offline subset
  executable: 34 pass, 3 fail on stale XML-attribute-ordering fixtures.
