# 4. Querying

> All examples need a live server unless marked otherwise. Return shapes and signatures
> below were verified by introspection against the installed package.

```python
sp = handle.query_dn("org-root/ls-sp_demo")
if sp is not None:
    print(sp.name, sp.oper_state)
```

## The five methods

| Method | Ask | Returns |
|---|---|---|
| `query_dn(dn, ...)` | one object by DN | one MO, or `None` |
| `query_dns(dns, ...)` | several objects by DN | `{dn: mo-or-None}` |
| `query_classid(class_id, ...)` | all objects of a type | `list` of MOs |
| `query_classids(class_ids, ...)` | all objects of several types | `{class_id: [mo]}` |
| `query_children(in_mo=/in_dn=, ...)` | children of an object | `list` of MOs |

Exact signatures:

```python
query_dn(dn, hierarchy=False, need_response=False, dme='central-mgr')
query_dns(dns=[], dme='central-mgr')
query_classid(class_id=None, filter_str=None, hierarchy=False,
              need_response=False, dme='central-mgr')
query_classids(class_ids=[], dme='central-mgr')
query_children(in_mo=None, in_dn=None, class_id=None, filter_str=None,
               hierarchy=False, dme='central-mgr')
```

Note what is **not** there: `query_dn`, `query_dns` and `query_classids` take no
`filter_str`. Only `query_classid` and `query_children` filter. The old user guide claims
all four accept filters; it is wrong.

## `query_dn` — one object

```python
sp = handle.query_dn("org-root/ls-sp_demo")
```

Returns `None` when the DN does not exist. **It does not raise.** A typo in a DN looks
exactly like an object that is not there, which is why you should build DNs from metadata
rather than typing them — see [02](02-information-model.md).

```python
if sp is None:
    raise SystemExit("no such service profile")
```

## `query_dns` — several DNs at once

```python
result = handle.query_dns(["org-root/ls-sp1", "org-root/ls-sp2", "org-root"])
result["org-root/ls-sp1"]     # MO or None
```

One round trip instead of three. Every DN you asked for is a key; DNs that did not resolve
map to `None`. Pass a **list** — the first argument is the whole collection, not a
varargs.

```python
handle.query_dns("org-root/ls-sp1", "org-root")   # WRONG
```

That passes the second DN as `dme` and iterates the first string character by character.
The old user guide shows exactly this mistake, written as `query_dn`.

## `query_classid` — everything of a type

```python
profiles = handle.query_classid("LsServer")
for sp in profiles:
    print(sp.dn)
```

Class ids are matched case-insensitively, so `"LsServer"`, `"lsServer"` and `"lsserver"`
all work here. (That tolerance is specific to the query methods — `load_class` is strict.)

Unfiltered, this returns every object of that type in the whole MIT. On a large
installation that is a lot; filter it:

```python
profiles = handle.query_classid("LsServer",
                                filter_str='(usr_lbl, "prod", type="eq")')
```

See [05 — filters](05-filters.md).

## `query_classids` — several types at once

```python
result = handle.query_classids(["OrgOrg", "FabricVlan"])
result["OrgOrg"]      # [MO, ...]
result["FabricVlan"]  # [MO, ...]
```

Again a **list**. And again the old guide gets this wrong, showing
`handle.query_classid("orgOrg", "fabricVlan")` — which would pass `"fabricVlan"` as
`filter_str` and fail to parse.

One sharp edge: results are bucketed by the class id the *server* returns. If it returns a
type you did not ask for, this raises `KeyError`. That is rare but it is why you should not
wrap this in a bare `except`.

## `query_children` — walk down

```python
vnics = handle.query_children(in_dn="org-root/ls-sp_demo", class_id="VnicEther")
```

Either `in_mo` or `in_dn` is required; supplying neither raises `ValueError`. With an MO,
its `dn` is used.

```python
sp = handle.query_dn("org-root/ls-sp_demo")
children = handle.query_children(in_mo=sp)          # every direct child
vnics    = handle.query_children(in_mo=sp, class_id="VnicEther")
```

`filter_str` only applies when `class_id` is also given — the filter needs a class to
resolve property names against. Passing `filter_str` alone is silently ignored.

## `hierarchy=True`

Available on `query_dn`, `query_classid`, `query_children`. It asks the server for the
whole subtree.

```python
everything = handle.query_dn("org-root/ls-sp_demo", hierarchy=True)
len(everything)      # a flat list, not one object
```

Two consequences that surprise people:

1. **The return type changes.** `query_dn` normally returns one MO; with `hierarchy=True`
   it returns a `list`.
2. **The tree is flattened destructively.** While building the list the SDK detaches each
   child from its parent. The objects you get back no longer have their children attached.

If you want the tree structure intact, ask for the response object instead and walk it
yourself:

```python
resp = handle.query_dn("org-root/ls-sp_demo", hierarchy=True, need_response=True)
root = resp.out_config.child[0]
for child in root.child:
    print(child.dn)
```

## `need_response=True`

Returns the raw `ExternalMethod` response instead of parsed MOs.

```python
resp = handle.query_dn("org-root", need_response=True)
resp.error_code          # 0
resp.out_config.child    # list of MOs
```

`need_response` is checked **before** `hierarchy`, so with both set you get the response
object and `hierarchy` only affects what the server sent.

Use it when you need the envelope — error codes, or the tree shape as above.

## Reading properties

```python
sp = handle.query_dn("org-root/ls-sp_demo")
sp.name, sp.dn, sp.oper_state, sp.usr_lbl
print(sp)              # formatted dump of every property
```

Properties use Python names (`usr_lbl`), not wire names (`usrLbl`). To discover them
without a server:

```python
from ucscsdk.mometa.ls.LsServer import LsServer
sorted(LsServer.prop_meta)           # all 79 property names
```

> Runs offline.

A property the SDK does not know about — because the server is newer — is still readable;
it is stored as an extra property and kept on round trips.

## Choosing a method

- Know the exact DN → `query_dn`. Cheapest and most precise.
- Know several DNs → `query_dns`. One round trip.
- Want all of a type → `query_classid` **with a filter**.
- Exploring an object's contents → `query_children`.
- Need a whole subtree in one call → `hierarchy=True`, and mind the flattening.

## `dme=`

Every query takes `dme="central-mgr"`. It selects the endpoint path segment —
`https://host/xmlIM/<dme>`. The default is correct for essentially all use; the argument
exists to address a different DME on the same host. See [15 — advanced](15-advanced.md).

## Common errors

**`query_dn` returns `None`** — the DN does not exist, or is misspelled. Not an error
condition; check for it explicitly.

**`ValueError: Provide dn.`** — empty DN string.

**`ValueError: Provide Comma Separated string of Dns`** — `query_dns` got an empty list.
Despite the message, it wants a list.

**`ValueError: Provide Parameter class_id`** — `query_classid` called with no class id.

**`ValueError: [Error]: GetChild: Provide in_mo or in_dn.`** — `query_children` needs one
of them.

**`KeyError` from `query_classids`** — the server returned a class you did not request.

**`UcscException: [ErrorCode]: ...`** — the server rejected the query. Read `error_code`
and `error_descr`; see [09 — error handling](09-error-handling.md).

**A filter is ignored** — you passed `filter_str` to `query_dn`, `query_dns` or
`query_classids`, which do not accept one; or to `query_children` without `class_id`.

**`hierarchy=True` gave me a list where I expected an object** — that is the documented
behaviour of `query_dn`.
