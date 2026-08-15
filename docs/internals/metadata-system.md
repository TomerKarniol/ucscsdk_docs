# The metadata system

> This is the chapter that lets you reason about an MO you have never seen. Every number
> below was computed by introspecting the installed package, not estimated. File:line
> references point at `ucscsdk/ucscsdk/`.

## Why it exists

1,831 of the SDK's classes are generated. None of them contain behaviour — they contain
**data describing themselves**, and a handful of hand-written modules interpret that data.
`ManagedObject` does not know what an `LsServer` is; it reads `LsServer.mo_meta` and
`LsServer.prop_meta` at runtime and behaves accordingly.

Consequence: if you can read the metadata, you can predict exactly what any of the 1,831
classes will do — its DN shape, which properties you may set, what values they accept, and
which UCS Central version introduced them. You never have to guess.

## The five metadata classes

All in `ucsccoremeta.py`.

| Class | Line | Describes |
|---|---|---|
| `MoMeta` | `:469` | one managed-object class |
| `MoPropertyMeta` | `:295` | one property of a managed object |
| `MoPropertyRestriction` | `:243` | the value constraints of one property |
| `MethodMeta` | `:593` | one XML method |
| `MethodPropertyMeta` | `:547` | one property of an XML method |
| `UcscVersion` | `:31` | a parsed, comparable UCS Central version |

## `MoMeta`

Eleven positional arguments (`ucsccoremeta.py:477`):

```python
MoMeta(name, xml_attribute, rn, version, inp_out, mask,
       field_names, access, parents, children, verbs)
```

Real instance, `mometa/ls/LsServer.py:223`:

```python
mo_meta = MoMeta(
    "LsServer",                       # name          python class name
    "lsServer",                       # xml_attribute wire tag
    "ls-[name]",                      # rn            template
    VersionMeta.Version101a,          # version       first release containing it
    "InputOutput",                    # inp_out       writable, vs "OutputOnly"
    0x3fffffff,                       # mask          dirty bit for the whole object
    [],                               # field_names
    ["admin", "ls-compute", "ls-config", "ls-server"],   # access — PRIVILEGES
    ['computeTemplate', 'orgOrg'],    # parents       legal parent class ids
    ['cimcvmediaMountConfigDef'],   # children      legal child class ids (52 total)
    ["Add", "Get", "Remove", "Set"],  # verbs         permitted operations
)
```

**The naming is a trap.** `MoMeta.access` is the list of *RBAC privilege strings*, not an
access level. The read/write nature of the class is `MoMeta.inp_out`. `ucsccoreutils`
renames them when it builds `ClassIdMeta` (`:518-519`) — `access` ← `inp_out`,
`access_privilege` ← `access` — which is the sane mapping, but the raw `MoMeta` attribute
names are the confusing ones.

Measured across all 1,831 classes:

| Field | Distribution |
|---|---|
| `inp_out` | `InputOutput` 1,448 · `OutputOnly` 383 |
| `parents` | 103 classes have **no** declared parent |
| `verbs` | `Get` 1,029 · `Set` 520 · `Add` 327 · `Remove` 306 |

`verbs` is dirty data: 738 entries are `None`, and lowercase duplicates exist
(`get` 64, `set` 27, `add` 14, `remove` 14). Compare case-insensitively and tolerate `None`
if you rely on it at all.

## RN templating and naming properties

`MoMeta.rn` is a template. Anything in `[...]` names a property whose value is substituted.

```
LsServer          "ls-[name]"                → ls-test_sp
OrgOrg            "org-[name]"               → org-root
FabricVlan        "net-[name]"               → net-100
```

Across the 1,831 classes:

| Naming properties in RN | Classes |
|---|---|
| 0 (static RN, e.g. `"boot-policy"`) | 806 |
| 1 | 887 |
| 2 | 92 |
| 3 | 42 |
| 4 | 2 |
| 5 | 1 |
| 6 | 1 |

So **44% of MOs have a fixed RN** and take no naming argument at all — their DN is decided
entirely by where you attach them.

Substitution happens in `ManagedObject.make_rn` (`ucscmo.py:278`):

```python
for prop in re.findall(r"""\[([^\]]*)\]""", rn_pattern):
    if prop in self.prop_meta:
        if getattr(self, prop):
            rn_pattern = re.sub(r"""\[%s\]""" % prop, '%s' % getattr(self, prop), rn_pattern)
        else:
            raise UcscValidationException('Property "%s" was None in make_rn' % prop)
```

The inverse — recovering property values from a DN you were handed — is
`ucsccoreutils.get_naming_props` (`:476`), which turns `[prop]` into a named regex group:

```python
get_naming_props("ls-test_sp", "ls-[name]")   # {'name': 'test_sp'}
```

Naming properties are **required positional arguments** on the generated `__init__`:

```python
def __init__(self, parent_mo_or_dn, name, **kwargs):   # mometa/ls/LsServer.py:389
    ...
```

One documented exception: `StorageLocalDiskPartition` has an RN that changed across UCS
Central releases, and `ManagedObject.rn_is_special_case`/`rn_get_special_case`
(`ucscmo.py:259`, `:268`) hard-code the fallback to `"partition"`. It is the only class
with this treatment.

## `MoPropertyMeta`

Eleven positional arguments (`ucsccoremeta.py:307`):

```python
MoPropertyMeta(name, xml_attribute, field_type, version, access, mask,
               min_length, max_length, pattern, value_set, range_val)
```

The last five are folded into a `MoPropertyRestriction` (`:316`).

Four real properties from `LsServer`:

```python
prop_meta = {
"name":       MoPropertyMeta("name", "name", "string", VersionMeta.Version101a,
                             MoPropertyMeta.NAMING, 0x10000,
                             None, None, r"""[\-\.:_a-zA-Z0-9]{2,32}""", [], []),
"usr_lbl":    MoPropertyMeta("usr_lbl", "usrLbl", "string", VersionMeta.Version101a,
                             MoPropertyMeta.READ_WRITE, 0x4000000,
                             None, None, r"""[ !#$%&...]{0,32}""", [], []),
"oper_state": MoPropertyMeta("oper_state", "operState", "string", VersionMeta.Version111a,
                             MoPropertyMeta.READ_ONLY, None,
                             None, None, None, ["ok", "config", "..."], []),
"dn":         MoPropertyMeta("dn", "dn", "string", VersionMeta.Version101a,
                             MoPropertyMeta.READ_ONLY, 0x20, 0, 256, None, [], []),
}
```

Note `usr_lbl` → `usrLbl`. **The Python name and the wire name differ for most properties.**
`prop_map` (`mometa/ls/LsServer.py:307`) maps wire → Python; `prop_meta` is keyed by Python
name.

### Access levels

Constants at `ucsccoremeta.py:301-305`:

| Level | Value | Meaning |
|---|---|---|
| `NAMING` | 0 | part of the RN; set once via the constructor |
| `CREATE_ONLY` | 1 | settable only while the property is still `None` |
| `READ_ONLY` | 2 | server-owned; assignment raises |
| `READ_WRITE` | 3 | freely settable |
| `INTERNAL` | 4 | SDK/server bookkeeping |

Measured over all 24,998 properties in the package:

| Access | Count | Share |
|---|---|---|
| `READ_ONLY` | 15,698 | 62.8% |
| `READ_WRITE` | 4,882 | 19.5% |
| `INTERNAL` | 3,086 | 12.3% |
| `NAMING` | 1,216 | 4.9% |
| `CREATE_ONLY` | 116 | 0.5% |

**Only about one property in five is writable.** When looking for what you can configure on
a class, filter to `READ_WRITE` — that is exactly what `ClassIdMeta.config_props` does
(`ucsccoreutils.py:538-540`).

Enforcement is in `ManagedObject.__set_prop` (`ucscmo.py:173-179`):

```python
if prop_meta.access != MoPropertyMeta.READ_WRITE:
    if getattr(self, name) is not None or prop_meta.access != MoPropertyMeta.CREATE_ONLY:
        raise ValueError("%s is not a read-write property." % name)
```

`CREATE_ONLY` gets exactly one write while the value is still `None`.

Field types across the package: `string` 19,837 · `uint` 2,065 · `ulong` 2,005 ·
`byte` 367 · `float` 356 · `ushort` 289 · `int` 76 · `sbyte` 1. Note that **values still
travel as strings** — the type is descriptive, and `validate_property_value` calls
`len(input_value)`, so passing a real `int` where a restriction exists raises `TypeError`.

### The dirty mask

Every property carries a `mask` — a single bit. Setting the property ORs that bit into the
object's `_dirty_mask` (`ucscmo.py:188`). At serialization time only masked properties are
emitted (`ucscmo.py:323`), which is how a `set_mo` sends just the fields you touched
instead of the whole object. `MoMeta.mask` (`0x3fffffff` for `LsServer`) is the
whole-object mask used by `mark_dirty` (`ucscmo.py:246`).

Properties with `mask=None` — like `oper_state` above — can never be marked dirty, which is
consistent with being `READ_ONLY`.

### Value restrictions

`MoPropertyRestriction` (`:243`) holds `min_length`, `max_length`, `pattern`, `value_set`,
`range_val`. Two of its seven properties, `range_roc` and `value_set_roc`, are always
`None` (`:256-257`) — nothing ever assigns them.

`validate_property_value` (`:355`) is where these are enforced, and **it short-circuits**:

```python
if self.__restriction.min_length:
    if len(input_value) >= self.__restriction.min_length:
        return True          # ← returns before pattern/value_set are ever checked
```

Verified:

```python
p = MoPropertyMeta("n", "n", "string", "V", 3, 0x1, 1, None, r"^[a-z]+$", None, None)
p.validate_property_value("123!!")    # True — pattern never evaluated
```

So a property declaring both `min_length` and a `pattern` is validated **only** by
`min_length`. The same early return applies to `max_length` and `range_val`. Client-side
validation is therefore weaker than the metadata implies; the server remains the real
authority. Do not treat a passing `validate_property_value` as proof the server will accept
a value.

Also: `validate_property_value(None)` returns `False` (`:359`), but `__set_prop` only
validates truthy values (`ucscmo.py:180`), so assigning `None` is always permitted.

## `<Class>Consts`

Every generated module defines a sibling constants class — `LsServerConsts`
(`mometa/ls/LsServer.py:8`) — holding the legal values of enumerated properties as
`UPPER_SNAKE` attributes:

```python
from ucscsdk.mometa.ls.LsServer import LsServer, LsServerConsts

LsServerConsts.ASSIGN_STATE_ASSIGNED    # 'assigned'
LsServerConsts.CONFIG_STATE_APPLIED     # 'applied'
```

The naming convention is `<PROPERTY>_<VALUE>` with non-alphanumerics folded to `_`. These
are the same strings as the property's `value_set`. Prefer the constant over the literal —
it is the difference between a typo failing at import and failing on the server.

## `UcscVersion` and `VersionMeta`

`VersionMeta` (`ucscmeta.py:19`) holds **32** `UcscVersion` constants, `Version101a`
through the latest. Every `MoMeta` and `MoPropertyMeta` carries one as its `version`,
meaning *the first release in which this exists*. That is how you tell whether a property is
safe to use against a given UCS Central.

`UcscVersion` (`ucsccoremeta.py:31`) parses strings like `"2.0(1a)"` with **nine** regex
patterns tried in order (`:52-130`), covering release, spin (`3.0(1S10)`), engineering
(`4.2(0.175a)`) and interim builds. It implements the full comparison set (`:221-237`):

```python
UcscVersion("2.0(1a)") > UcscVersion("1.5(1a)")    # True
```

Four sharp edges, all verified:

1. **Unparseable strings do not raise.** `UcscVersion("not-a-version")` constructs fine with
   every component `None`. It then compares as *less than* everything real. A typo silently
   becomes "very old" rather than an error.
2. **`UcscVersion(None)` returns a half-built object.** `__init__` bails at `:41` before
   setting `__version`, so `.version` raises `AttributeError`.
3. **It is unhashable.** `__eq__` is defined without `__hash__` (`:233`), so Python 3 sets
   `__hash__ = None`. `{version}` and `dict[version]` raise `TypeError`.
4. **Interim versions are silently bumped.** `_set_versions` (`:146-154`) rewrites the parsed
   value: `2.0(1.5)` becomes mr `2`, patch `a`. A missing patch becomes `'z'` on the theory
   that a spin build is later than any patch. Comparisons are against the rewritten value,
   not what you passed.

## The global registry — `ucscmeta.py`

Four module-level names (`ucscmeta.py`), all generated:

| Name | Type | Size | Contents |
|---|---|---|---|
| `MO_CLASS_ID` | `frozenset` | 1,831 | every MO class id, e.g. `"LsServer"` |
| `METHOD_CLASS_ID` | `frozenset` | 122 | every method class id, e.g. `"ConfigResolveDn"` |
| `MO_CLASS_META` | `dict` | 1,831 | `class_id -> MoMeta` |
| `OTHER_TYPE_CLASS_ID` | `dict` | 26 | `class_id -> module name` for basetypes and filters |

The first two are **sets, not dicts** — `MO_CLASS_ID.items()` is an `AttributeError`. Use
`MO_CLASS_META` when you want the metadata.

Membership in `MO_CLASS_ID` is the single authoritative answer to "is this a real class?".
Check there before believing any class name.

## Dynamic loading

`ucsccoreutils.load_class` (`:130`) turns a class id into a class with no import statement:

```python
class_id = ucscgenutils.word_u(class_id)              # lsServer → LsServer
mod_class_id = ucscgenutils.word_l(class_id)          # LsServer → lsServer
class_id_sub_pkg = re.match("([a-z])+", mod_class_id).group()   # → "ls"
mo_pkg = "ucscsdk.mometa.ls.LsServer"
```

The subpackage is the **leading lowercase run** of the camelCase id. That is the whole rule,
and it is why the 94 `mometa` packages are named as they are.

```python
from ucscsdk import ucsccoreutils as cu
cu.load_class("LsServer")     # <class 'ucscsdk.mometa.ls.LsServer.LsServer'>
cu.load_class("lsserver")     # None  ← case matters
```

`word_u` only uppercases the first letter, so `"lsserver"` becomes `"Lsserver"`, which is
not in `MO_CLASS_ID`. **Always normalise first:**

```python
cid = cu.find_class_id_in_mo_meta_ignore_case("lsserver")   # 'LsServer'
cls = cu.load_class(cid)
```

That case-insensitive lookup is a linear scan over 1,831 strings (`:202-204`) — fine
occasionally, worth caching in a loop.

`load_module` (`:101`) is the sibling for method metas and basetypes.
`ucsccoreutils.load_mo` (`:157`) looks like a third entry point but is **broken on Python
3.11+** — it calls `inspect.getargspec`, which no longer exists. Use `load_class` plus your
own construction.

## `GenericMo` — the forward-compatibility escape hatch

When the server sends a class id the SDK has never heard of, `get_ucsc_obj`
(`ucsccoreutils.py:95`) does not raise — it builds a `GenericMo` (`ucscmo.py:459`), which
stores every XML attribute in a plain dict exposed as `.properties` (`:553`) and recurses
into children.

```python
from ucscsdk.ucscmo import generic_mo_from_xml

g = generic_mo_from_xml('<lsServer dn="org-root/ls-t" name="t"/>')
g.properties            # {'dn': 'org-root/ls-t', 'name': 't', 'rn': 'ls-t'}
g.get_class_id()        # 'lsServer'
```

Note `rn` in `properties` even though the XML never carried it — `GenericMo.from_xml`
derives the missing half of the dn/rn pair (`ucscmo.py:594-596`) and records it. The class
id is kept in **wire case** (`lsServer`), unlike `ManagedObject.get_class_id()`, which
returns the Python case (`LsServer`).

This is how an older SDK keeps working against a newer UCS Central. The same instinct
applies at the property level: unknown attributes on a *known* class are kept in
`__xtra_props` (`ucscmo.py:155`) and re-serialized (`:339-343`), so a read-modify-write
cycle does not silently drop fields the SDK does not model.

`GenericMo.to_mo()` (`:649`) converts back to a real `ManagedObject` when the class *is*
known — but it is **broken on Python 3.11+**, again via `inspect.getargspec` (`:621`).

## Reading metadata at runtime

The friendly front door is `ucsccoreutils.get_meta_info` (`:652`), which returns a
`ClassIdMeta` (`:503`):

```python
from ucscsdk import ucsccoreutils as cu

meta = cu.get_meta_info(class_id="lsserver")   # case-insensitive here
meta.rn                # 'ls-[name]'
meta.parents           # ['computeTemplate', 'orgOrg']
meta.config_props      # only the READ_WRITE property names
meta.props["usr_lbl"]  # the MoPropertyMeta
print(meta)            # tree + every property, formatted
```

For one property directly:

```python
pm = cu.get_mo_property_meta("LsServer", "usr_lbl")
pm.xml_attribute       # 'usrLbl'
pm.access              # 3  (READ_WRITE)
pm.restriction.pattern # the regex
```

`get_mo_property_meta` accepts either the Python name or the XML name (`:244-247`), and
`"mo_meta"` as a special key returns the class's `MoMeta` (`:239`).

To search when you only know a fragment:

```python
cu.search_class_id("ls")      # exact match if any; otherwise logs related ids at INFO
```

Note it *logs* suggestions rather than returning them (`:643`), so enable
`ucscsdk.set_log_level(logging.INFO)` to see them.

## Common errors

**`AttributeError: 'frozenset' object has no attribute 'items'`** — you used `MO_CLASS_ID`
where you wanted `MO_CLASS_META`.

**`load_class` returns `None`** — wrong case. Normalise with
`find_class_id_in_mo_meta_ignore_case` first.

**`ValueError: <prop> is not a read-write property.`** — the property is `READ_ONLY`,
`INTERNAL`, or a `CREATE_ONLY` that already has a value. Check
`get_mo_property_meta(cid, prop).access` against the table above.

**`UcscValidationException: Property "name" was None in make_rn`** — a naming property was
cleared after construction. RN cannot be rebuilt.

**`TypeError: object of type 'int' has no len()`** — you assigned an `int` to a property
that has a length or pattern restriction. Pass strings.

**`TypeError: unhashable type: 'UcscVersion'`** — expected; use `str(version)` as the key.

**A value passes `validate_property_value` and the server still rejects it** — expected. The
short-circuit above means only the first satisfied restriction is checked, and the server
enforces rules the metadata does not model at all.

## See also

- [architecture.md](architecture.md) — how these pieces fit into the client as a whole.
- [request-lifecycle.md](request-lifecycle.md) — where `prop_meta` and the dirty mask are
  consumed during serialization.
