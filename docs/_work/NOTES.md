# NOTES — running memory across phases

**Read this file first in every new session.** It assumes you have never seen the previous
phase. Append, never rewrite. Newest phase at the bottom.

---

## Phase 0 — 2026-08-15

### Environment (verified, non-obvious, will bite you)

- Repo root: `/home/tomer/code/ucscsdk_docs`. The SDK clone is at `ucscsdk/` (untracked in
  git); the package itself is `ucscsdk/ucscsdk/`. So `ucscsdk/ucscsdk/ucschandle.py`.
- **Docs root is `/home/tomer/code/ucscsdk_docs/docs/`** — the OUTER repo, chosen by the
  user. Never write inside the clone. Never modify SDK source.
- **Use `/usr/bin/python3` (3.12.3) for everything.** It has `six`, `pyparsing`, and
  `pytest 9.0.2` in `/usr/lib/python3/dist-packages`.
  The `python3` first on `$PATH` is uv's CPython 3.13.12 and has **none** of them — under it
  `import ucscsdk.ucschandle` and `import ucscsdk.ucscfilter` both fail. Symptom is a bare
  `ModuleNotFoundError: No module named 'six'` / `'pyparsing'`. Nothing is broken; you used
  the wrong interpreter.
- The package is **not pip-installed**. Every script must do:
  `sys.path.insert(0, "/home/tomer/code/ucscsdk_docs/ucscsdk")`.
- Only two modules have third-party deps: `ucscdriver.py` needs `six`,
  `ucscfilter.py` needs `pyparsing`. Everything else — including all 1,831 `mometa`
  classes and `ucsccoreutils` — imports on bare stdlib. Useful if a tool needs to run
  under the uv interpreter: skip those two modules and it works.
- No network needed. No live UCS Central available — **no example may claim to have been
  executed against hardware.**
- `docs/DOCS_PROMPT.md` already exists in the outer repo; leave it alone.

### Corrections to the original brief (source wins; docs must match source)

| Brief claimed | Actual | How verified |
|---|---|---|
| 1,926 MO classes | **1,831** | `len(ucscmeta.MO_CLASS_ID)` == `len(MO_CLASS_META)` == filesystem count of non-`__init__` files under `mometa/` |
| 95 mometa packages | **94** | `ls -d ucscsdk/mometa/*/ \| grep -v __pycache__ \| wc -l` |
| 123 methodmeta modules | **122** `*Meta.py` | the 123rd file is `__init__.py`; matches `len(METHOD_CLASS_ID) == 122` |
| Filter classes named `Eq`, `Ne`, `Gt`, `Wcard`… | All carry a `Filter` suffix: `EqFilter`, `NeFilter`, `GtFilter`, `GeFilter`, `LtFilter`, `LeFilter`, `WcardFilter`, `AnybitFilter`, `AllbitsFilter`, `BwFilter`, `AndFilter`, `OrFilter`, `NotFilter` | `grep '^class ' ucscfiltertype.py` |
| `ucscfilter` exposes `ParseFilter`, `generate_infilter`, `create_basic_filter` | Also exposes **`handle_filter_max_component_limit(handle, l_filter)`** — undocumented, must be covered | `grep '^def ' ucscfilter.py` |

Confirmed as stated: 2,113 `.py` files; 19 core modules @ 17,349 LOC; 6 utils modules @
4,495 LOC; 122 `ucscmethodfactory` functions; `UcscHandle`/`UcscSession` public surface
exactly as listed; all seven exception classes present.

### Facts worth carrying forward

- `ucscmeta.MO_CLASS_ID` and `METHOD_CLASS_ID` are **frozensets of class-id strings**, not
  dicts. The dict is `MO_CLASS_META: {class_id -> MoMeta}`. `OTHER_TYPE_CLASS_ID` is a dict
  of 26 entries mapping `ucscbasetype`/filter types to their module name. Do not assume
  `.items()` works on the first two.
- `ucscconstants.py` (5,590 LOC) contains only **four** classes: `NamingId` (l.16),
  `YesOrNo` (l.1997), `NamingPropertyId` (l.2003), `Status` (l.5585).
- `ucscmeta.VersionMeta` holds **32** `UcscVersion` constants, `Version101a` upward.
- Package version is **0.9.0.10** (`ucscsdk.__version__`).
- `UcscHandle.wait_for_event` delegates to the module function
  `ucsceventhandler.wait(handle, mo, prop, value, cb, timeout_sec=None, poll_sec=None)`.
- `methodmeta/*Meta.py` shape is stable and machine-readable: `method_meta = MethodMeta(...)`,
  `prop_meta = {python_name: MethodPropertyMeta(...)}`, `prop_map = {xmlAttr: python_name}`.
  Phase 3 should parse these by import, not by regex.

### ⚠ The test suite does not run — `nose`, not `pytest`

This changes Phase 5. **24 of the 26 test modules `import nose`** (`from nose.tools import *`,
`from nose.plugins.skip import SkipTest`). `nose` is dead upstream, is not installed, and
cannot be installed on Python 3.12 (it breaks on `collections.Callable`). Measured:

```
$ /usr/bin/python3 -m pytest tests -q --collect-only
!!!!!!!!!!!!!!!!!!! Interrupted: 22 errors during collection !!!!!!!!!!!!!!!!!!!
2 tests collected, 22 errors in 0.26s
```

Only two modules are import-clean — `tests/test_ucscsdk.py` (a stub) and
`tests/convert_to_ucs/test_convert_to_from_xml.py`.

Consequences:
- `tests/` remains the **best source of verified usage intent** — read it, quote it, trace
  examples to it. It is *not* an executable oracle.
- Phase 5 must report this verbatim in `VERIFICATION.md`. Do not "fix" it by installing or
  vendoring `nose`, and do not silently skip the run — the honest output *is* the result.
  The real gate is `verify_docs.py`, which validates every documented symbol by
  `importlib`/`inspect` against the package. That works fine.
- Never write "verified by running the tests" in any doc.

### Live-hardware split in `tests/`

Everything importing `tests/connection/info.py` calls `custom_setup()`, which builds a real
`UcscHandle` from `tests/connection/connection.cfg` and calls `login()` — so it needs
hardware. `connection.cfg` ships placeholder values (`hostname=192.168.1.1`,
`username=admin`, `password=password`) plus sections for backup/firmware/techsupport/domain
paths. Treat all of it as fictional; never present those IPs or credentials as real.

Needs live UCS Central: `common/test_query_children.py`, `common/test_request_xml.py`,
`common/test_ucscpropval.py`, `coreutils/test_get_meta_info.py`,
`generic_mo/test_ucscgmo.py`, `policy/test_policy.py`, `sp/test_sp.py`,
`utils/test_{backup,domain,eventhandler,firmware,techsupport}.py`, `vlan/tests_vlan.py`.

Pure offline unit tests (no handle): `common/test_{generate_filter,special_rn,ucsccoreutils,
ucscfromxml,ucschandle,ucscmo,ucsctoxml,ucscvalidatemethod,ucscversion,unknown_props}.py`,
`convert_to_ucs/test_convert_to_from_xml.py`. These are the richest source of assertable,
hardware-free examples — especially `test_generate_filter.py` (the `filter_str` grammar) and
`test_special_rn.py` (RN templating edge cases).

### Assumptions made (not blocking, flagged per the brief)

- "1,926 MOs / 95 packages / 123 methodmeta" in the brief were stale or counted
  `__init__.py`. Docs use the measured numbers.
- `tests/connection/` requires live hardware and will be excluded from the Phase 5 offline
  test run; the exclusion will be stated explicitly rather than silently dropped.
- The suite's `nose` breakage is reported, not repaired. Fixing the SDK's tests is outside
  the documentation scope and would mean modifying the clone, which is forbidden.

### Deferred to Phase 4: the `ucscsdk_ug.rst` staleness audit

`ucscsdk/docs/ucscsdk_ug.rst` (932 lines) has **not** been audited yet. Phase 4 must read it
in full anyway — to mine it *and* to correct it — so auditing it earlier just means reading
it twice. When you get there, check each of its examples against:

- real `UcscHandle` signatures (in `INVENTORY.md` §1.1, taken from `inspect.signature`);
- `ucscmeta.MO_CLASS_ID` membership for every MO class name it mentions;
- actual function names in `ucscsdk/utils/*.py` (backup/firmware/techsupport/domain names
  are the likeliest to have drifted);
- property names against each MO's `prop_meta`.

Produce a flat `rst:LINE — claims X — wrong because Y — source says Z` list; the brief
requires the new docs to state explicitly where the old guide is wrong. Also expect Python 2
idioms, `nose`-era instructions, and stale install steps that should not be carried forward.

Process note: two attempts to delegate this to an `Explore` subagent returned nothing (the
agent went idle without reporting, twice). Do it in the main context — the file is small
enough and correctness here matters more than context economy.

### Deliverables written this phase

`docs/_work/INVENTORY.md`, `docs/_work/PROGRESS.md`, `docs/_work/NOTES.md`. No prose docs.

---

## Phase 1 — 2026-08-16

Read all 19 core modules. Wrote `internals/architecture.md` and
`internals/request-lifecycle.md`. All 86 `file.py:NN` refs machine-checked in-bounds and
spot-checked by content.

### Verified bugs in the SDK (documented, not fixed)

Confirmed by running code under `/usr/bin/python3` 3.12.3:

| Symbol | State | Cause |
|---|---|---|
| `ucsccoreutils.load_mo` (`:157`) | broken 3.11+ | `inspect.getargspec` removed |
| `GenericMo.to_mo` (`ucscmo.py:649`) | broken 3.11+ | same, via `__get_mo_obj` `:621` |
| `ManagedObject.show_tree` (`ucscmo.py:411`) | broken always | uses `self.children`; attr is `child` |
| `ucsccoreutils.write_mo_tree` (`:325`) | broken always | uses `mo.class_id`; accessor is `get_class_id()` |
| `extract_mo_tree_from_config_method_response` (`:401`) | broken always | calls `write_mo_tree` |
| `is_local_download_supported` (`ucschandle.py:811`) | broken 3.13+ | `distutils` removed |
| `TLS1Connection.connect` (`ucscdriver.py:112`) | broken 3.12+ | `ssl.wrap_socket` removed |

`get_ucsc_obj` branches on `sys.version_info` and uses `getfullargspec` — the same fix was
never applied to `load_mo`/`__get_mo_obj`. That is why response parsing works but those two
do not.

### Wrong docstrings in the SDK (do not copy into docs)

- `ucschandle.py:44` — `port=100` example. `__create_uri` (`ucscsession.py:117`) raises
  `UcscLoginError` for any port but 443, **at construction**.
- `ucschandle.py:332-337` — four calls to `handle.lookup_by_dn`, which exists nowhere in
  the source. A `ucsmsdk`-ism. The method is `query_dn`.
- `ucsccoreutils.py:447-448` — `print_mo_hierarchy` example shows `write_mo_tree`.
- `ucscfilter.py:172` — `generate_infilter` example has unbalanced quotes, will not parse.
- `ucscsession.py:342-347` — `file_upload` example says `source_dir`; the param is `file_dir`.
  `file_download`'s docstring says `dest_dir` for the same reason.

### Semantics worth not re-deriving

- **All 122 factory functions** call `to_xml(option=WriteXmlOption.DIRTY)`. Only set
  properties are serialized. `WriteXmlOption` = ALL 0 / ALL_CONFIG 1 / DIRTY 2.
- `to_xml_str` returns **bytes** on Python 3 (`ET.tostring`).
- `extract_molist_from_method_response(resp, True)` **destroys the tree** while flattening
  (`child_remove` at `:314`). For an intact tree use `need_response=True`.
- `commit()` on error **discards the buffer** (`ucschandle.py:715`) then raises. On success
  it also discards (`:739`). A committed buffer is always empty.
- `commit()` on an empty buffer returns `None` silently (`:691`) — forgetting `add_mo` is
  not an error.
- Commit buffer is keyed by **DN**; staging the same DN twice keeps only the last object.
- `tx_lock` (`ucscsession.py:25`) is **module-level** — serializes every request across all
  handles in the process. Threading mode separates commit *buffers*, not the wire.
- `error_code` is int `0` by default but a **string** off the wire. `!= 0` works; `== 0` on
  a real response does not.
- Filter default type is **`re` (WcardFilter)**, not `eq` (`ucscfilter.py:51`). Default flag
  `C`; `flag="I"` rewrites letters to `[Aa]` classes.
- The `filter_str` mini-language exposes only eq/ne/ge/gt/le/lt/re (`ucscfilter.py:24-31`).
  `BwFilter`, `AnybitFilter`, `AllbitsFilter` are reachable **only** via
  `create_basic_filter`, whose kwargs are snake_case (`first_value`, `second_value`).
- `load_class` is **case-sensitive** — `load_class('lsserver')` returns `None`. Resolve with
  `find_class_id_in_mo_meta_ignore_case` first.
- Unknown props survive round-trips via `__xtra_props` (`ucscmo.py:155`, `:339`).

### Security facts (verified, belong in the guides too)

- **TLS is not verified.** `ucscdriver.py:83` builds `SSLContext(PROTOCOL_SSLv23)` with no
  CA bundle; `verify_mode=CERT_NONE`, `check_hostname=False`. No SDK option changes this.
- **XML parsing**: external entities are blocked by stdlib ET (`ParseError: undefined
  entity`), but internal entity expansion *is* performed → billion-laughs-shaped DoS from a
  hostile server. Combined with the above, a MITM is that hostile server. Do not overstate
  this as XXE — file disclosure does not work; tested.
