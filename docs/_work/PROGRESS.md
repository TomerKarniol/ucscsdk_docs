# PROGRESS — `ucscsdk` documentation set

One checkbox per deliverable. Tick only when the file exists **and** the phase's own
verification passed. Read `NOTES.md` first — it carries the environment facts and every
correction found so far.

## Phase 0 — Map
- [x] `docs/_work/INVENTORY.md`
- [x] `docs/_work/PROGRESS.md`
- [x] `docs/_work/NOTES.md`

## Phase 1 — Core architecture
- [x] Read all 19 core modules end to end
- [x] `docs/internals/architecture.md`
- [x] `docs/internals/request-lifecycle.md` (read trace + write trace, `file.py:NN` refs)

## Phase 2 — Metadata system
- [x] `docs/internals/metadata-system.md`

## Phase 3 — Generated reference
- [x] `docs/_tools/gen_reference.py` (stdlib only, offline, deterministic)
- [x] `docs/reference/mo/<package>.md` × 94 (+ index.md)
- [x] `docs/reference/methods.md`
- [x] `docs/agents/mo-index.json` (+ `mo-details.jsonl`)
- [x] `docs/agents/api-index.json`
- [x] Re-run produces byte-identical output

## Phase 4 — Human guides (`docs/guides/`)
- [x] `01-getting-started.md`
- [x] `02-information-model.md` (MIT / DN / RN)
- [x] `03-connecting-and-auth.md` (`get_auth_token`, proxy, session refresh)
- [x] `04-querying.md` (all five query methods, `hierarchy=`, `need_response=`)
- [x] `05-filters.md` (`filter_str` grammar + all 13 `*Filter` classes)
- [x] `06-create-modify-delete.md` (commit buffer, `tag=`, `modify_present`, discard)
- [x] `07-transactions-and-threading.md`
- [x] `08-events-and-wait-for-event.md`
- [x] `09-error-handling.md`
- [x] `10-backup-export-import.md`
- [x] `11-domain-management.md`
- [x] `12-firmware.md`
- [x] `13-tech-support.md`
- [x] `14-xml-to-python.md` (`converttopython`)
- [x] `15-advanced.md` (`dump_xml`, `dme=`, parallel tx)

## Phase 5 — Verification (gate)
- [x] `docs/_tools/verify_docs.py` (stdlib only, offline)
- [x] `verify_docs.py` exits 0 — every doc symbol resolves
- [x] All internal doc links resolve
- [x] All `file.py:NN` references point at live lines
- [x] Repo test suite run, output captured verbatim
- [x] `docs/_work/VERIFICATION.md`

## Phase 6 — Agent layer
- [x] `docs/llms.txt`
- [x] `docs/agents/AGENTS.md` (10 recipes, DN table, top-50 MOs, do-not-do list)
- [x] `docs/CLAUDE.md`
- [x] `docs/README.md`

## Invariants (check every phase)
- [x] Nothing written outside `docs/`
- [x] SDK source under `ucscsdk/` never modified (`git status` shows it untracked, unchanged)
- [x] ~~No commits made~~ — user asked for a commit+push per phase
- [x] Every unexecutable example carries `> Not executed against live hardware.`
