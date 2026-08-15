# Verification

Run date: 2026-08-16 (final, after Phase 6). Interpreter: `/usr/bin/python3` (CPython 3.12.3).
Package under test: `ucscsdk` 0.9.0.10 at `ucscsdk/ucscsdk/`, imported via `sys.path`.
No live UCS Central was available; nothing here was executed against hardware.

---

## 1. `verify_docs.py` — the gate

```
$ /usr/bin/python3 docs/_tools/verify_docs.py
verifying 123 markdown files under docs

syntax        3681 checked     0 failed  ok
imports       3562 checked     0 failed  ok
symbols       1988 checked     0 failed  ok
classes       3347 checked     0 failed  ok
props            7 checked     0 failed  ok
signatures     155 checked     0 failed  ok
links          175 checked     0 failed  ok
linerefs        51 checked     0 failed  ok

all 12966 checks passed
```

Exit status `0`.

(The `symbols` and `linerefs` totals are lower than an earlier run of the same checker
because unlabelled fenced blocks — pasted terminal output, including the deliberately
broken self-test output quoted below — are now excluded from prose scanning. See
[One deliberate design choice](#one-deliberate-design-choice).)

What each check does:

| Check | What must hold |
|---|---|
| `syntax` | every ```` ```python ```` block `ast.parse`s |
| `imports` | every `from ucscsdk… import X` / `import ucscsdk…` resolves via `importlib` |
| `symbols` | every dotted `ucscsdk.…` attribute path named in prose exists |
| `classes` | every MO class id imported is in `MO_CLASS_ID`, **and lives in the package the doc says**; every `mf.<fn>` exists on `ucscmethodfactory` |
| `props` | every `"prop" in <Cls>.prop_meta` and `get_mo_property_meta(…)` claim holds |
| `signatures` | every documented `func(a, b=c)` uses only real parameters, per `inspect.signature` |
| `links` | every relative markdown link resolves on disk |
| `linerefs` | every `file.py:NN` points at a line the file still has |

### The gate was itself tested

A green result on the first run is not evidence the checker works. A file with eight
planted defects was added and every check fired:

```
14 FAILURES

  [syntax] _selftest.md block 1: '(' was never closed
  [imports] _selftest.md block 2: from ucscsdk.mometa.ls.NoSuchClass import NoSuchClass -- ucscsdk.mometa.ls has no attribute 'NoSuchClass'
  [imports] _selftest.md block 3: from ucscsdk.mometa.compute.LsServer import LsServer -- ucscsdk.mometa.compute has no attribute 'LsServer'
  [symbols] _selftest.md: ucscsdk.ucschandle.UcscHandle.lookup_by_dn -- ucscsdk.ucschandle has no attribute 'lookup_by_dn'
  [classes] _selftest.md: NoSuchClass not in MO_CLASS_ID
  [classes] _selftest.md: LsServer is in package 'ls', doc says 'compute'
  [classes] _selftest.md: ucscmethodfactory has no config_resolve_nothing
  [props] _selftest.md: LsServer.prop_meta has no 'no_such_prop'
  [props] _selftest.md: get_mo_property_meta('LsServer', 'bogus_prop') is None
  [signatures] _selftest.md: backup_local(...): 'nonexistent_arg' is not a parameter -- real: (handle, file_dir, file_name, preserve_pooled_values=False, remove_from_ucsc=False, timeout=600)
  [links] _selftest.md: broken link -> ./does-not-exist.md
  [linerefs] _selftest.md: ucschandle.py:99999 -- file has 831 lines
```

The self-test file was then deleted. Notably it caught the *wrong-package* case — importing `LsServer` from the `compute`
package instead of `ls` — which resolves as a dotted path but is a real documentation
error.

### One deliberate design choice

Two classes of false positive had to be handled, and both were fixed by narrowing *where*
the checker looks — not by adding suppressions or an allowlist.

**Inline code spans, for links.** The generated MO reference embeds property regexes such
as `^[A-Za-z]([A-Za-z0-9-]*[A-Za-z0-9])?$` inside code spans. A naive link scan reads
`[...](...)` as a markdown link and reported ~19 phantom failures. Link checking now strips
fenced blocks and inline code spans first.

**Unlabelled fenced blocks, for prose scanning.** This file quotes the checker's own
failure messages, which name symbols that deliberately do not exist — a phantom
`lookup_by_dn` handle method, a `NoSuchClass` MO, an out-of-range line number.
Re-checking those as claims made the gate fail on its own evidence. The `symbols`,
`classes`, `props` and `linerefs` checks now skip unlabelled ```` ``` ```` fences, which is
where pasted terminal output lives, while still scanning prose **and** ```` ```python ````
blocks — so `# mometa/ls/LsServer.py:389`-style references inside real examples remain
verified.

Three remaining hits were placeholder text in this file's own prose
(`ucscsdk.a.b.C`, `Class.prop_meta`). Those were **reworded** rather than allowlisted, so
the checker keeps treating every dotted path in prose as a claim to verify.

Both fixes narrow scope precisely; planted defects outside those regions are still caught,
as shown above.

---

## 2. `gen_reference.py` — determinism

Two consecutive runs produce byte-identical output:

```
$ /usr/bin/python3 docs/_tools/gen_reference.py
mos            1831 in 94 packages
methods        122 (0 unmatched factory fns)
props          24998
wrote          94 package pages + index + methods.md + 2 json

$ find docs/reference docs/agents -type f | sort | xargs md5sum | md5sum
887d2db95a4a35808adf5950b762e8fd  -
$ /usr/bin/python3 docs/_tools/gen_reference.py >/dev/null
$ find docs/reference docs/agents -type f | sort | xargs md5sum | md5sum
887d2db95a4a35808adf5950b762e8fd  -
```

Generated data was also cross-checked against the live package: the class-id set in
`mo-details.jsonl` equals `MO_CLASS_META`'s keys exactly (1831), and for 200 randomly
sampled MOs the `rn`, `xml`, `access`, `parents`, `module` and full property-name set all
match, as do each property's `xml` and `type`. All 122 methods resolve to a builder
function.

---

## 3. The SDK's own test suite

### As shipped: it does not run

```
$ /usr/bin/python3 -m pytest tests -q
ERROR tests/common/test_generate_filter.py
ERROR tests/common/test_query_children.py
ERROR tests/common/test_request_xml.py
ERROR tests/common/test_special_rn.py
ERROR tests/common/test_ucsccoreutils.py
ERROR tests/common/test_ucscfromxml.py
ERROR tests/common/test_ucschandle.py
ERROR tests/common/test_ucscmo.py
ERROR tests/common/test_ucscpropval.py
ERROR tests/common/test_ucsctoxml.py
ERROR tests/common/test_ucscvalidatemethod.py
ERROR tests/common/test_ucscversion.py
ERROR tests/common/test_unknown_props.py
ERROR tests/coreutils/test_get_meta_info.py
ERROR tests/generic_mo/test_ucscgmo.py
ERROR tests/policy/test_policy.py
ERROR tests/sp/test_sp.py
ERROR tests/utils/test_backup.py
ERROR tests/utils/test_domain.py
ERROR tests/utils/test_eventhandler.py
ERROR tests/utils/test_firmware.py
ERROR tests/utils/test_techsupport.py
!!!!!!!!!!!!!!!!!!! Interrupted: 22 errors during collection !!!!!!!!!!!!!!!!!!!
22 errors in 0.20s
```

Every error is the same cause:

```
tests/utils/test_techsupport.py:15: in <module>
    from nose.plugins.attrib import attr
E   ModuleNotFoundError: No module named 'nose'
```

24 of 26 test modules import `nose`, which is dead upstream and cannot be installed on
Python 3.12 (it breaks on `collections.Callable`). This is a property of the SDK, not of
this environment. It was **reported, not repaired** — fixing it would mean modifying the
clone, which is out of scope for a documentation task.

The two modules that do collect:

```
$ /usr/bin/python3 -m pytest tests/test_ucscsdk.py tests/convert_to_ucs -q
..                                                                       [100%]
2 passed in 0.04s
```

One of those two is an empty stub (`test_000_something` has a `pass` body), so the shipped
suite yields exactly **one** meaningful assertion as-is.

### With `nose` shimmed: real signal

To get actual coverage, `docs/_tools/nose_shim.py` registers fake `nose` modules in
`sys.modules`. Nothing on disk is modified and the clone is untouched. Only the
hardware-free modules can run — anything importing `tests/connection/info.py` calls
`custom_setup()`, which tries to log in to `192.168.1.1` and blocks.

```
$ PYTHONPATH=docs/_tools /usr/bin/python3 -m pytest -q -p nose_shim \
    tests/common/test_generate_filter.py tests/common/test_special_rn.py \
    tests/common/test_ucscfromxml.py tests/common/test_ucschandle.py \
    tests/common/test_ucscmo.py tests/common/test_ucsctoxml.py \
    tests/common/test_ucscvalidatemethod.py tests/common/test_ucscversion.py \
    tests/common/test_unknown_props.py tests/convert_to_ucs tests/test_ucscsdk.py

FAILED tests/common/test_ucsctoxml.py::test_001_mo_to_xml - AssertionError: b...
FAILED tests/common/test_ucsctoxml.py::test_001_mo_heirarchy_to_xml - Asserti...
FAILED tests/common/test_unknown_props.py::test_001_knownmo_unknownprop - Ass...
3 failed, 34 passed, 9 subtests passed in 1.37s
```

**34 passed, 3 failed.**

The 3 failures are a genuine SDK/Python-version incompatibility, not shim noise. Example:

```
AssertionError: b'<lsServer name="ra11" agentPolicyName="" type="inst[49 chars]" />'
             != b'<lsServer agentPolicyName="" dn="ls-ra11" name="ra1[49 chars]" />'
```

The expected strings are **alphabetically sorted by attribute**. Python ≤ 3.7's
`ET.tostring` sorted attributes; 3.8+ preserves insertion order:

```
$ /usr/bin/python3 -c "import xml.etree.ElementTree as ET; e=ET.Element('x'); e.set('zeta','1'); e.set('alpha','2'); print(ET.tostring(e))"
b'<x zeta="1" alpha="2" />'
```

So the SDK's emitted XML is semantically identical and these three assertions are testing an
ordering guarantee the standard library stopped making. Attribute order is not significant
in XML, so this is a test-fixture problem rather than an SDK defect — but it does mean the
suite cannot pass on any modern Python without being rewritten.

Two shim bugs were found and fixed during this exercise before the numbers above were
trusted: the initial version mapped nose's snake_case asserts (`assert_equal`) directly onto
`unittest.TestCase` attribute names, producing 24 spurious `AttributeError` failures, and it
lacked `with_setup`, which broke collection of three modules.

---

## 4. Filter assertions, run directly

The filter examples quoted in [guides/05-filters.md](../guides/05-filters.md) are the SDK's
own test assertions, executed independently of the test runner:

```
PASS test_001_not_filter
PASS ls_filter
PASS org_filter
PASS test_003_mixed_filter
```

---

## 5. Summary

| Gate | Result |
|---|---|
| `verify_docs.py` | **pass** — 12,966 checks, 0 failures, exit 0 |
| `verify_docs.py` self-test | **pass** — all 8 checks fire on planted defects |
| `gen_reference.py` determinism | **pass** — byte-identical across runs |
| Generated data vs live package | **pass** — 1831/1831 class ids, 200-MO deep sample |
| SDK test suite, as shipped | **fails to run** — 22 collection errors, `nose` unavailable |
| SDK test suite, `nose` shimmed | **34 passed, 3 failed** — the 3 are XML attribute-ordering fixtures |

No example in the documentation claims to have been executed against live hardware.
Examples that require a server are marked as such; the rest were run offline against the
installed package.
