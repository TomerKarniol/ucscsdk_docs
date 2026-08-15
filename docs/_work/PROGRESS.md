# PROGRESS — `ucscsdk` documentation set

One checkbox per deliverable. Tick only when the file exists **and** the phase's own
verification passed. Read `NOTES.md` first — it carries the environment facts and every
correction found so far.

## Phase 0 — Map
- [x] `docs/_work/INVENTORY.md`
- [x] `docs/_work/PROGRESS.md`
- [x] `docs/_work/NOTES.md`

## Phase 1 — Core architecture
- [ ] Read all 19 core modules end to end
- [ ] `docs/internals/architecture.md`
- [ ] `docs/internals/request-lifecycle.md` (read trace + write trace, `file.py:NN` refs)

## Phase 2 — Metadata system
- [ ] `docs/internals/metadata-system.md`

## Phase 3 — Generated reference
- [ ] `docs/_tools/gen_reference.py` (stdlib only, offline, deterministic)
- [ ] `docs/reference/mo/<package>.md` × 94
- [ ] `docs/reference/methods.md`
- [ ] `docs/agents/mo-index.json`
- [ ] `docs/agents/api-index.json`
- [ ] Re-run produces byte-identical output

## Phase 4 — Human guides (`docs/guides/`)
- [ ] `01-getting-started.md`
- [ ] `02-information-model.md` (MIT / DN / RN)
- [ ] `03-connecting-and-auth.md` (`get_auth_token`, proxy, session refresh)
- [ ] `04-querying.md` (all five query methods, `hierarchy=`, `need_response=`)
- [ ] `05-filters.md` (`filter_str` grammar + all 13 `*Filter` classes)
- [ ] `06-create-modify-delete.md` (commit buffer, `tag=`, `modify_present`, discard)
- [ ] `07-transactions-and-threading.md`
- [ ] `08-events-and-wait-for-event.md`
- [ ] `09-error-handling.md`
- [ ] `10-backup-export-import.md`
- [ ] `11-domain-management.md`
- [ ] `12-firmware.md`
- [ ] `13-tech-support.md`
- [ ] `14-xml-to-python.md` (`converttopython`)
- [ ] `15-advanced.md` (`dump_xml`, `dme=`, parallel tx)

## Phase 5 — Verification (gate)
- [ ] `docs/_tools/verify_docs.py` (stdlib only, offline)
- [ ] `verify_docs.py` exits 0 — every doc symbol resolves
- [ ] All internal doc links resolve
- [ ] All `file.py:NN` references point at live lines
- [ ] Repo test suite run, output captured verbatim
- [ ] `docs/_work/VERIFICATION.md`

## Phase 6 — Agent layer
- [ ] `docs/llms.txt`
- [ ] `docs/agents/AGENTS.md` (10 recipes, DN table, top-50 MOs, do-not-do list)
- [ ] `docs/CLAUDE.md`
- [ ] `docs/README.md`

## Invariants (check every phase)
- [ ] Nothing written outside `docs/`
- [ ] SDK source under `ucscsdk/` never modified (`git status` shows it untracked, unchanged)
- [ ] No commits made
- [ ] Every unexecutable example carries `> Not executed against live hardware.`
