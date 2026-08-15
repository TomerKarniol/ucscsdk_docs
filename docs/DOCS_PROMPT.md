# Prompt: Full documentation for `ucscsdk`

> Paste everything below the line into Claude Code, from a fresh session, in the
> directory where `ucscsdk/` is cloned. Start in **plan mode** (`Shift+Tab`).

---

You are documenting **`ucscsdk`** — the Cisco UCS Central Python SDK
(https://github.com/CiscoUcs/ucscsdk, Apache-2.0, v0.9.0.10) — which today ships
almost no usable documentation. Your job is to produce a complete, verified
documentation set that serves **two audiences equally**: human engineers reading
prose, and AI coding agents that need machine-readable, unambiguous facts.

## Ground truth about this repo (verified — do not re-derive, but do re-confirm if a fact looks wrong)

- Package: `ucscsdk`, deps `pyparsing` + `six`, Python 2.6/2.7/3.x-era code.
- It talks to **UCS Central**, *not* UCS Manager (that is the separate `ucsmsdk`).
  Never conflate the two, and never copy `ucsmsdk` examples.
- **2,113 `.py` files total**, but they are not equal:
  - **19 hand-written core modules** in `ucscsdk/*.py` (~17.3k LOC). These you
    READ IN FULL:
    `ucschandle.py` (831), `ucscsession.py` (549), `ucscmo.py` (691),
    `ucsccoreutils.py` (692), `ucsccoremeta.py` (617), `ucsceventhandler.py` (676),
    `ucscgenutils.py` (582), `ucscdriver.py` (288), `ucscfilter.py` (240),
    `ucscfiltertype.py` (203), `ucsccore.py` (204), `ucscmethod.py` (175),
    `ucscbasetype.py` (145), `ucscexception.py` (119), `ucscxmlcodec.py` (93),
    `__init__.py` (51), `ucscmethodfactory.py` (1727, 122 functions),
    `ucscmeta.py` (3876, generated maps), `ucscconstants.py` (5590, generated).
  - **6 hand-written util modules** in `ucscsdk/utils/`. Also READ IN FULL:
    `ucscbackup.py` (56K), `converttopython.py` (43K), `ucscfirmware.py` (23K),
    `ucsctechsupport.py` (16K), `ucscdomain.py` (12K), `ccoimage.py` (9K).
  - **1,926 generated MO classes** in `ucscsdk/mometa/<pkg>/<ClassName>.py`
    across 95 packages (`aaa`, `compute`, `ls`, `lstorage`, `fabric`, `org`,
    `vnic`, `firmware`, `policy`, …).
  - **123 generated method-meta modules** in `ucscsdk/methodmeta/*Meta.py`.
  - `tests/` — 12 subdirs of real, working usage. This is your best source of
    **verified** examples (`tests/common/`, `tests/utils/`, `tests/sp/`,
    `tests/vlan/`, `tests/policy/`, `tests/generic_mo/`, `tests/convert_to_ucs/`).
  - `docs/ucscsdk_ug.rst` — a 932-line user guide. It is the ONLY real prose that
    exists. Mine it, correct it, supersede it; do not just reformat it.
- Architecture in one line: an XML API client. Python `ManagedObject`s are
  serialized to XML method calls, POSTed over HTTPS to UCS Central, responses
  parsed back into MOs. Everything hangs off the **MIT** (Management Information
  Tree): each MO has a **DN** (full path) and **RN** (name relative to parent,
  often templated from "naming properties", e.g. `ls-[name]`).
- Public surface you must cover exhaustively:
  - `UcscHandle(ip, username, password, port=443, proxy=None)` and its methods:
    `login`, `logout`, `get_auth_token`, `query_dn`, `query_dns`, `query_classid`,
    `query_classids`, `query_children`, `add_mo`, `set_mo`, `remove_mo`, `commit`,
    `commit_buffer_discard`, `wait_for_event`, `process_xml_elem`,
    `set_dump_xml`/`unset_dump_xml`, `set_mode_threading`/`unset_mode_threading`,
    `is_threading_enabled`, `get_firmware_version`, `is_local_download_supported`
    — including the `tag=` commit-buffer semantics and the `dme="central-mgr"` arg.
  - `UcscSession` properties: `ip`, `username`, `proxy`, `uri`, `ucs`, `cookie`,
    `session_id`, `version`, `refresh_period`, `priv`, `domains`, `channel`,
    `evt_channel`, `last_update_time`.
  - Filters: `ucscfilter.ParseFilter` (a pyparsing grammar behind `filter_str`),
    `generate_infilter`, `create_basic_filter`, and every class in
    `ucscfiltertype.py`: Eq, Ne, Gt, Ge, Lt, Le, Wcard, Anybit, Allbits, Bw,
    And, Or, Not.
  - Exceptions: `UcscException`, `UcscValidationException`, `UcscLoginError`,
    `UcscConnectionError`, `UcscOperationError`, `UcscWrapperException`, `UcscError`.
  - Events: `UcscEventHandle`, `MoChangeEvent`, `WatchBlock`, and how
    `wait_for_event` sits on top of them.
  - All 122 `ucscmethodfactory` functions and their `methodmeta` contracts.
  - Every **public** function in the 6 utils modules (leading-underscore = internal;
    document internals only in the internals section).

## Non-negotiable rules

1. **Zero invented API.** Every class name, DN pattern, property, constant, and
   function signature in the docs must exist in the source. If you cannot point at
   the file and line, it does not go in the docs.
2. **No live UCS Central is available.** Do not claim any example was executed
   against hardware. Examples are verified by *static* means (see Phase 5).
   Mark anything unverifiable as `> Not executed against live hardware.`
3. Prefer the metadata as the source of truth for generated code. Read a handful of
   `mometa` files to learn the *shape* (`MoMeta`, `MoPropertyMeta`, `<Class>Consts`,
   `__init__(parent_mo_or_dn, <naming props>, **kwargs)`), then **introspect
   programmatically** for the other 1,900. Do not hand-read 1,926 files.
4. Docs go under `docs/`. Never write to the repo root. Never modify SDK source.
5. Work phase by phase. After each phase, append what you learned to
   `docs/_work/NOTES.md` and the phase checklist in `docs/_work/PROGRESS.md`, then
   tell me to `/clear` before the next phase. Those two files are your memory —
   write them as if the next phase runs in a session that has never seen this one.

## Phases

### Phase 0 — Map, don't read
Inventory the repo mechanically (`find`, `wc -l`, `grep -n '^class \|^def '`).
Produce `docs/_work/INVENTORY.md`: every module, its LOC, its public symbols, and
a one-line "what it is". Write `docs/_work/PROGRESS.md` with a checkbox per
deliverable listed in Phase 6. Do not write prose docs yet.

### Phase 1 — Core architecture (read in full)
Read all 19 core modules end to end. Trace one request completely:
`handle.query_dn("org-root")` → `ucscmethodfactory` → `ucscxmlcodec` →
`ucscdriver` POST → response → `ucsccoreutils.extract_molist_from_method_response`
→ `ManagedObject`. Do the same for a write: `add_mo` → commit buffer → `commit` →
`ConfigConfMos`. Write `docs/internals/architecture.md` and
`docs/internals/request-lifecycle.md` with real file:line references.

### Phase 2 — The metadata system
Read `ucsccoremeta.py`, `ucscmeta.py`, `ucscmo.py`, `ucsccoreutils.py` together.
Explain `MoMeta`, `MoPropertyMeta` (access levels, masks, restrictions, min/max
version), `VersionMeta`, `MO_CLASS_ID`/`METHOD_CLASS_ID` maps, RN templating and
naming props, `load_class`/`load_mo` dynamic import, and `GenericMo`. Write
`docs/internals/metadata-system.md`. This is the chapter that lets an agent reason
about MOs it has never seen — make it precise.

### Phase 3 — Generate the reference
Write `docs/_tools/gen_reference.py` (stdlib only, runs offline, imports the SDK):
- For all 1,926 MOs: class id, python class, module path, parent classes, RN
  pattern, naming props, every property with xml name / type / access / versions,
  and its `<Class>Consts` values.
- For all 122 method-factory functions + 123 methodmeta modules: signature, XML
  method name, input/output properties, version.
Emit BOTH:
- Human: `docs/reference/mo/<package>.md` (95 files) + `docs/reference/methods.md`.
- Agent: `docs/agents/mo-index.json` and `docs/agents/api-index.json` — flat,
  greppable, stable-keyed JSON.
The script must be re-runnable and its output must be reproducible. Commit the
script, not just its output.

### Phase 4 — Human guides
Hand-write `docs/guides/` (one file each, numbered, each opening with a runnable
snippet and closing with "common errors"):
getting-started · information-model (MIT/DN/RN) · connecting-and-auth (incl.
`get_auth_token`, proxy, session refresh) · querying (all five query methods,
`hierarchy=`, `need_response=`) · filters (grammar + every filter type, with the
`filter_str` mini-language documented properly — it is undocumented today) ·
create-modify-delete (commit buffer, `tag=`, `modify_present`, discard) ·
transactions-and-threading · events-and-wait-for-event · error-handling ·
backup-export-import · domain-management · firmware · tech-support ·
xml-to-python (`converttopython`) · advanced (dump_xml, `dme=`, parallel tx).
Every example must be traceable to `tests/` or to source you read. Where
`docs/ucscsdk_ug.rst` is wrong or stale, say so explicitly in the new doc.

### Phase 5 — Verification (this is the gate, not optional)
Write `docs/_tools/verify_docs.py` (stdlib only, offline). It must:
- extract every ```python block from `docs/**/*.md`;
- `ast.parse` each one (syntax gate);
- resolve every `ucscsdk.…` import, class name, MO class id, property name,
  constant, and function signature referenced anywhere in the docs against the
  installed package via `importlib`/`inspect` — **fail loudly on anything that
  does not exist**;
- check every internal doc link resolves and every `file.py:NN` reference points
  at a line that still exists.
Run it. Fix every failure. Then run the repo's own tests (`python -m pytest tests
-q`, offline subset) and report the actual output — pass or fail, verbatim. Paste
the final `verify_docs.py` output into `docs/_work/VERIFICATION.md`.

### Phase 6 — Agent-facing layer
- `docs/llms.txt` — Anthropic/llms.txt-style index: one line per doc with a
  description precise enough to route on.
- `docs/agents/AGENTS.md` — a dense, no-prose operating manual for an AI writing
  ucscsdk code: the 10 canonical task recipes (connect, query one, query many with
  filter, create SP, modify, delete, transaction, watch event, backup, register
  domain), the DN patterns table, the top-50 MO classes by usefulness, and an
  explicit **"do not do this"** list (wrong: `ucsmsdk` APIs, guessed DNs, forgetting
  `commit()`, mutating after commit, ignoring `UcscException` error codes).
- A `CLAUDE.md` at the docs root pointing at all of the above.
- `docs/README.md` — the router: "human? start here / agent? read llms.txt".

## How to work

- Use **subagents** for Phase 0 and for any broad grep sweep, so file dumps never
  land in your main context. Do the reading in Phase 1–2 yourself.
- Run `/clear` between phases; `docs/_work/NOTES.md` + `PROGRESS.md` carry you over.
- If a phase reveals the ground-truth list above is wrong, fix the docs to match
  the source and note the discrepancy in `NOTES.md`.
- Stop and ask me only if something would make the docs actively wrong. Otherwise
  state your assumption in `NOTES.md` and keep going.
- Do not commit anything unless I ask.

Start with Phase 0 and show me `INVENTORY.md` + your plan before writing prose.
