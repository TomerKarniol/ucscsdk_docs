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

---

## Phase 2 — 2026-08-16

Wrote `internals/metadata-system.md`. 109 line refs machine-checked; every runnable snippet
executed under `/usr/bin/python3`.

### Metadata shapes (positional args — the generated files use positional form)

```
MoMeta(name, xml_attribute, rn, version, inp_out, mask,
       field_names, access, parents, children, verbs)
MoPropertyMeta(name, xml_attribute, field_type, version, access, mask,
               min_length, max_length, pattern, value_set, range_val)
MethodMeta(name, xml_attribute, version)
MethodPropertyMeta(name, xml_attribute, field_type, version, inp_out, is_complex_type)
```

**Naming trap**: `MoMeta.access` is the RBAC **privilege list** (`["admin","ls-config",…]`).
The read/write nature is `MoMeta.inp_out` (`InputOutput` / `OutputOnly`). `ClassIdMeta`
swaps them into sane names (`ucsccoreutils.py:518-519`).

Access levels (`ucsccoremeta.py:301`): NAMING 0, CREATE_ONLY 1, READ_ONLY 2, READ_WRITE 3,
INTERNAL 4.

### Measured statistics (recompute rather than trust if the package changes)

- 1,831 MOs, **24,998 properties** total.
- Access split: READ_ONLY 15,698 (62.8%) · READ_WRITE 4,882 (19.5%) · INTERNAL 3,086 ·
  NAMING 1,216 · CREATE_ONLY 116. **Only ~1 property in 5 is writable.**
- RN: 806 classes have a **static** RN (no `[prop]`); 1,025 are templated.
  Naming-prop counts: 0→806, 1→887, 2→92, 3→42, 4→2, 5→1, 6→1.
- `inp_out`: InputOutput 1,448 · OutputOnly 383. 103 classes have no declared parent.
- Field types: string 19,837 · uint 2,065 · ulong 2,005 · byte 367 · float 356 ·
  ushort 289 · int 76 · sbyte 1.
- `verbs` is dirty data: 738 `None` entries plus lowercase duplicates (`get` 64, `set` 27,
  `add` 14, `remove` 14) alongside `Get` 1,029 / `Set` 520 / `Add` 327 / `Remove` 306.

### More verified bugs (add to the Phase 1 list)

- **`MethodPropertyMeta.name` is infinitely recursive** (`ucsccoremeta.py:562-565`): the
  getter returns `self.name`, not `self.__name`. Accessing it raises `RecursionError`.
  Every other getter on that class is fine. Phase 3's generator must read
  `prop_meta` keys / `xml_attribute` and must never touch `.name` on a `MethodPropertyMeta`.
- **`validate_property_value` short-circuits** (`ucsccoremeta.py:363-377`): a satisfied
  `min_length` (or `max_length`, or `range_val`) returns `True` immediately, so `pattern`
  and `value_set` are never evaluated. Verified: a meta with `min_length=1` and
  `pattern=^[a-z]+$` accepts `"123!!"`. Client-side validation is weaker than the metadata
  suggests — say so in the guides, do not present it as a guarantee.
- `MoPropertyRestriction.range_roc` / `.value_set_roc` are always `None` (`:256-257`).
- **`UcscVersion` is unhashable** — `__eq__` without `__hash__` (`:233`). `{v}` → TypeError.
- `UcscVersion("garbage")` does **not** raise; all components stay `None` and it compares
  less than everything real. `UcscVersion(None)` returns a half-built object whose
  `.version` raises `AttributeError`.
- `UcscVersion` silently **rewrites** interim versions (`:146-154`): `2.0(1.5)` → mr `2`,
  patch `a`; a missing patch becomes `'z'`.
- `validate_property_value` calls `len(input_value)` → `TypeError` on int input.

### Facts for Phase 3 (the generator)

- Subpackage rule is exactly: leading lowercase run of the camelCase class id
  (`ucsccoreutils.py:144`). `LsServer` → `lsServer` → `ls` → `mometa/ls/LsServer.py`.
- `load_class` is case-sensitive; `word_u` only uppercases the first char, so `"lsserver"`
  → `"Lsserver"` → miss. Normalise via `find_class_id_in_mo_meta_ignore_case`.
- Generated MO module layout: `<Class>Consts` class, then `mo_meta = MoMeta(...)`, then
  `prop_meta = {...}`, then `prop_map = {xmlName: python_name}`, then
  `def __init__(self, parent_mo_or_dn, <naming props...>, **kwargs)`.
- `<Class>Consts` attribute convention is `<PROPERTY>_<VALUE>` upper-snake; values equal the
  property's `value_set`.
- `GenericMo` keeps the class id in **wire case** (`lsServer`); `ManagedObject.get_class_id()`
  returns Python case (`LsServer`). Do not mix them as dict keys.

---

## Phase 3 — 2026-08-16

Wrote `docs/_tools/gen_reference.py` (stdlib only, offline, deterministic). Run it with:

```
/usr/bin/python3 docs/_tools/gen_reference.py
```

Output (all generated — never hand-edit):
- `reference/mo/<package>.md` × 94 + `reference/mo/index.md`
- `reference/methods.md` — 122 sections, 122 summary rows
- `agents/mo-index.json` (537K, routing/summary — loadable whole)
- `agents/mo-details.jsonl` (25M, **one JSON object per line**, full record)
- `agents/api-index.json` (196K — handle surface, methods, basetypes, exceptions, filters)

Counts emitted: 1831 MOs / 94 packages / 122 methods / 24,998 props. Matches Phase 0 and
Phase 2 exactly.

### Determinism verified

Two consecutive runs give byte-identical output (md5 of md5s of every generated file).
Achieved by sorting every mapping and writing nothing timestamped.

### Two problems solved while building it — do not reintroduce

1. **Acronym runs break naive snake-casing.** `re.sub(r"(?<!^)(?=[A-Z])","_",cid).lower()`
   maps `AaaGetKVMLaunchUrlInternal` → `aaa_get_k_v_m_...`, but the real function is
   `aaa_get_kvm_launch_url_internal`. Five methods were affected: `AaaGetKVMLaunchUrlInternal`,
   `ConfigResolveClassDB`, `ConfigUCEstimateImpact`, `SyntheticFSObjInventory`,
   `SyntheticFSObjInventoryB`. Fix: match on the **underscore-free lowercase** form
   (`cid.lower()` vs `fn.replace("_","")`), exact for all 122.
2. **A single 29MB pretty-printed JSON is neither loadable nor greppable.** Split into a
   537K routing index plus JSONL. `grep '"class_id": "LsServer"' mo-details.jsonl` now
   returns the complete record on one line.

### Generator gotcha

`MethodPropertyMeta.name` raises `RecursionError` (see Phase 2). The generator uses the
`prop_meta` dict key as the python name and never touches `.name`. Keep it that way.

### Correctness cross-check (ran after generating)

- class-id set in JSONL == `MO_CLASS_META` keys, exactly (1831).
- 200 randomly sampled MOs: `rn`, `xml`, `access`/`inp_out`, `parents`, `module`, and the
  full property-name set all match the live classes; per-property `xml`/`type` match too.
- Documented module path == `ucscsdk.mometa.<pkg>.<Class>` for every sample, and 40 random
  documented imports actually import.
- method set == `METHOD_CLASS_ID` (122), every one has a resolved builder function.
- 23 public `UcscHandle` members indexed.

Sizes: `reference/` 21M, `agents/` 25.7M. Large but generated; the script is the artifact.

---

## Phase 4 — 2026-08-16

Wrote all 15 guides in `docs/guides/`, plus `docs/_work/UG-RST-AUDIT.md` (the deferred
`ucscsdk_ug.rst` audit, done in main context after two failed subagent attempts).

All 3,661 ```python blocks across `docs/**` now `ast.parse` cleanly.

### The old user guide is badly wrong — full list in UG-RST-AUDIT.md

Headlines, all verified against source:
- `delete_mo` (rst:324) and `commit_mo` (rst:327) **do not exist** — they are `remove_mo`
  and `commit`.
- `export_config` (rst:700) does not exist; the import raises `ImportError`.
- rst:371 and rst:388 show `query_dn`/`query_classid` taking varargs for multiple
  DNs/class ids. The real APIs are `query_dns(["a","b"])` / `query_classids(["a","b"])`.
- rst:406 claims all four query methods accept filters. **Only `query_classid` and
  `query_children` do.**
- Five code blocks are syntactically broken (unbalanced parens at 676/708, literal `\n` at
  736, dangling arg at 743, missing comma at 782).
- Two Python-2 `print` statements (528, 643).

### Utils signatures — verified, several differ from the old guide

Captured in the guides; the ones most likely to trip you up:
- `backup_domain_remote(handle, file_dir, file_name, domain_ip, protocol, hostname, ...)`
  vs `export_config_domain_remote(handle, file_dir, file_name, domain_ip, hostname,
  protocol, ...)` — **protocol/hostname are swapped**. Use kwargs.
- `schedule_*` use **`file_path`**, not `file_dir`; `max_bkup_files` defaults to the
  *string* `'2'`.
- `sync_firmware_update_from_cisco(..., sync_frequencey='daily', ...)` — the typo is the
  real parameter name.
- Tech support options are `ucsm`, `ucsm-mgmt`, `chassis`, `rack-server`,
  **`fabric-extender`** (not `fex`), `server-memory`. Required kwargs:
  `chassis_id` / `rack_server_id` / `fex_id` / **`server_id_list`** (not
  `server_memory_id`). Anything else → `UcscValidationException: Unrecognised option value`.
- `get_cco_firmware_image(..., mdf_id_list=(284308174,), ...)` default covers UCS Central
  only.

### More verified facts added this phase

- Filter test assertions from `tests/common/test_generate_filter.py` were run directly
  (bypassing `nose`) and **all four still pass** — they are quoted in guide 05 as verified
  examples. Precedence confirmed: `not` > `and` > `or`.
- `converttopython.convert_to_ucs_python(xml=True, request=...)` was executed; guide 14
  quotes its real output verbatim.
- **Naming properties are immutable after construction** — `sp.name = "x"` raises
  `ValueError: name is not a read-write property.` (access level NAMING is not READ_WRITE).
  The `UcscValidationException` in `make_rn` only fires if you force past the setter.
- `LsServer` has **52** children in its MoMeta (not 50 — recount if quoting).
- `commit(tag=...)` on a never-used tag raises **`KeyError`**; the default buffer returns
  `None` silently. Asymmetric.
- `BwFilter` serializes its bounds as `first_value=` / `second_value=` — **snake_case XML
  attributes**, unlike every other wire name. `AbstractFilter.to_xml` only special-cases
  `class_` → `class`.
- `print_mo_hierarchy` works (unlike `write_mo_tree`/`show_tree`) and prints the *metadata*
  hierarchy for a class id.

### Checker false positives to avoid in Phase 5

1. **Do not flag "broken links" inside code spans.** Property regex patterns like
   `` `^[A-Za-z]([A-Za-z0-9-]*[A-Za-z0-9])?$` `` in the generated reference tables look like
   markdown links to a naive regex. `verify_docs.py` must strip inline code spans and fenced
   blocks before link-checking, or it will report ~19 phantom failures.
2. Illustrative fragments (bare `def` signatures, dict-entry excerpts) were made
   syntactically valid rather than weakening the AST gate. Keep it that way.

---

## Phase 5 — 2026-08-16

Wrote `docs/_tools/verify_docs.py` (the gate) and `docs/_tools/nose_shim.py`.
Result captured in `docs/_work/VERIFICATION.md`.

**Final: `all 12877 checks passed`, exit 0.** Re-run after any doc edit:

```
/usr/bin/python3 docs/_tools/verify_docs.py
```

### The gate was self-tested — keep doing this

A first-run green is not evidence the checker works. A file with 8 planted defects was
added; all 8 checks fired (14 failures). It caught the subtle one: importing `LsServer`
from package `compute` instead of `ls` resolves as a dotted path but is a real doc error.
Self-test file deleted afterwards.

### Two false-positive classes — fixed by narrowing scope, NOT by allowlisting

1. **Inline code spans break link checking.** Generated reference tables embed property
   regexes; `[...](...)` inside a code span reads as a markdown link → ~19 phantom
   failures. `strip_code()` removes fenced blocks + inline spans before link checks.
2. **Unlabelled fences hold pasted terminal output.** `VERIFICATION.md` quotes the
   checker's own failure messages, which name deliberately-nonexistent symbols. The
   `symbols`/`classes`/`props`/`linerefs` checks now call `strip_output_blocks()`, which
   drops ```` ``` ```` fences but **keeps** ```` ```python ```` ones — so linerefs inside
   real examples stay verified.

Three placeholder strings in VERIFICATION.md prose (a dotted `ucscsdk.…` placeholder, `<Cls>.prop_meta`,
and a literal `lookup_by_dn` path) were **reworded**, not allowlisted. `SYMBOL_ALLOW` has
exactly one entry. Keep it that way — if the gate fires on prose, fix the prose.

Note the checker fires on its own document when you add prose citing a fake symbol. That
happened twice while writing VERIFICATION.md. Working as intended.

### The SDK test suite: honest result

- **As shipped**: `pytest tests -q` → `22 errors during collection`, all
  `ModuleNotFoundError: No module named 'nose'`. Only `tests/test_ucscsdk.py` (an empty
  stub) and `tests/convert_to_ucs` collect → `2 passed`. Effectively **one** real assertion.
- **With `docs/_tools/nose_shim.py`** (fake nose in `sys.modules`, nothing on disk touched):
  **34 passed, 3 failed** over the hardware-free modules.

The 3 failures are **real and diagnosed**: the assertions compare exact XML byte strings
with **alphabetically sorted attributes**. Python ≤3.7's `ET.tostring` sorted attributes;
3.8+ preserves insertion order. Attribute order is not significant in XML, so this is a
stale test fixture, not an SDK defect — but the suite cannot pass on any modern Python
without being rewritten.

Do **not** run the whole suite unshielded: modules importing `tests/connection/info.py`
call `custom_setup()` → real login to 192.168.1.1 → hangs until timeout. Restrict to the
hardware-free list (command is in VERIFICATION.md §3).

Two bugs in my own shim, found and fixed before trusting any number:
- nose exposes unittest asserts snake_cased (`assert_equal` → `assertEqual`). Looking up
  the snake name on `TestCase` gave 24 spurious `AttributeError` failures.
- Missing `with_setup` broke collection of 3 modules.
Lesson: a shim that produces failures is not evidence about the code under test until the
shim itself is verified.

---

## Phase 6 — 2026-08-16 — COMPLETE

Wrote `docs/llms.txt`, `docs/agents/AGENTS.md`, `docs/CLAUDE.md`, `docs/README.md`.

**Final gate: `all 12966 checks passed`, exit 0** across 123 markdown files.

### Top-50 list was hand-curated, not scored

A first attempt ranked classes by `n_writable * 2 + package bonus`. It surfaced
`ClitestTypeTest`, `SyntheticFile`, `HcReport` and `BiosVfPCISlotOptionROMEnable` — high
property counts, no operational relevance. Writable-property count is not usefulness.

The shipped list is 57 hand-picked classes covering service profiles, boot, org/domain
groups, network, vNICs, pools, compute, storage, identity, firmware and ops. **All 57 were
verified present in `mo-index.json` before publishing** (0 missing). If you extend it,
verify the same way — `verify_docs.py` does not check prose class-name mentions, only
imports.

### The gate fires on its own documents — twice more this phase

`VERIFICATION.md` and `NOTES.md` both contained a dotted `ucscsdk.…` placeholder in prose
describing the checker. Reworded, not allowlisted. Expect this whenever you write *about*
the checker: any dotted path in prose is treated as a claim.

### Project status: all six phases complete

| Phase | Deliverable | State |
|---|---|---|
| 0 | INVENTORY / PROGRESS / NOTES | done |
| 1 | internals/architecture.md, request-lifecycle.md | done |
| 2 | internals/metadata-system.md | done |
| 3 | gen_reference.py -> 94 pages + methods.md + 3 indexes | done |
| 4 | 15 guides + UG-RST-AUDIT.md | done |
| 5 | verify_docs.py + nose_shim.py + VERIFICATION.md | done, gate green |
| 6 | llms.txt, AGENTS.md, CLAUDE.md, README.md | done |

Invariants held throughout: nothing written outside `docs/`; SDK clone source unmodified
(`git diff --stat HEAD -- ucscsdk/ tests/ docs/` inside the clone is empty).

Deviation from the original plan, at the user's request: each phase was committed and
pushed to `origin/main` rather than left uncommitted, and commits carry only the user's
authorship (no co-author trailer).

### If you pick this up later

- Re-run both tools first; they are the source of truth:
  `/usr/bin/python3 docs/_tools/gen_reference.py && /usr/bin/python3 docs/_tools/verify_docs.py`
- The reference and agent indexes are **generated**. Never hand-edit `reference/**` or
  `agents/*.json*`.
- Known gaps, deliberate: the 122 XML methods have generated contracts but no prose beyond
  guide 15; `converttopython`'s interactive log-scraping mode is documented but could not be
  exercised (needs a GUI log); no example has ever touched real hardware.
