# 1. Getting started

> Not executed against live hardware. Snippets that need a server are marked; everything
> else in this guide was run offline against the installed package.

## Install

```
pip install ucscsdk
```

Dependencies are `pyparsing` and `six`. The package is `ucscsdk` — Cisco's SDK for **UCS
Central**. If you want UCS *Manager*, you want `ucsmsdk`; the two are not interchangeable.

Check what you have:

```python
import ucscsdk
print(ucscsdk.__version__)          # '0.9.0.10'
```

## Connect, query, disconnect

```python
from ucscsdk.ucschandle import UcscHandle

handle = UcscHandle("192.168.1.1", "admin", "password")
handle.login()

org = handle.query_dn("org-root")
print(org.dn, org.name)

handle.logout()
```

> Needs a live server.

`login()` returns `True` on success and raises otherwise. `port` defaults to `443` and
**must stay 443** — any other value raises `UcscLoginError` when you construct the handle,
not when you log in.

## Create something

```python
from ucscsdk.mometa.ls.LsServer import LsServer

sp = LsServer("org-root", name="sp_demo")
sp.descr = "created from python"

handle.add_mo(sp)
handle.commit()
```

> Needs a live server.

Two things to internalise immediately:

1. **`add_mo` does not talk to the server.** It stages the object. Nothing happens until
   `commit()`. This is the single most common mistake.
2. **The first positional argument is the parent**, given as a DN string or another MO.
   After that come the *naming properties* — for `LsServer` that is `name`, and it is
   required.

You can build and inspect an MO with no server at all:

```python
from ucscsdk.mometa.ls.LsServer import LsServer

sp = LsServer("org-root", name="sp_demo")
sp.rn          # 'ls-sp_demo'
sp.dn          # 'org-root/ls-sp_demo'
```

That much is pure client-side computation, and it is how you check a DN before you go
near a server.

## Finding the class you need

There are 1,831 managed-object classes. Three ways in, cheapest first:

```python
from ucscsdk import ucsccoreutils as cu

cu.find_class_id_in_mo_meta_ignore_case("lsserver")   # 'LsServer'
```

```python
meta = cu.get_meta_info(class_id="lsserver")
meta.rn              # 'ls-[name]'
meta.parents         # ['computeTemplate', 'orgOrg']
meta.config_props    # the 25 writable property names
```

Or read the generated reference: [`reference/mo/index.md`](../reference/mo/index.md) lists
all 94 packages, and each package page documents every class in it.

The package name is the leading lowercase run of the wire name — `lsServer` lives in `ls`,
`fabricVlan` in `fabric`, `computeBlade` in `compute`:

```python
from ucscsdk.mometa.ls.LsServer import LsServer
from ucscsdk.mometa.fabric.FabricVlan import FabricVlan
from ucscsdk.mometa.compute.ComputeBlade import ComputeBlade
```

## Turning on logging

```python
import logging
import ucscsdk

ucscsdk.set_log_level(logging.DEBUG)
```

To see the actual XML on the wire:

```python
handle.set_dump_xml()
...
handle.unset_dump_xml()
```

Passwords are masked in the `aaaLogin` dump, so this is safe to leave on while debugging.
Everything else is logged verbatim.

## What to read next

| You want to | Read |
|---|---|
| Understand DNs, RNs, the tree | [02 — information model](02-information-model.md) |
| Auth, tokens, proxies, refresh | [03 — connecting and auth](03-connecting-and-auth.md) |
| Query things | [04 — querying](04-querying.md) |
| Filter query results | [05 — filters](05-filters.md) |
| Create, modify, delete | [06 — create, modify, delete](06-create-modify-delete.md) |
| Know why it broke | [09 — error handling](09-error-handling.md) |

## Common errors

**`UcscLoginError: Can not login to UcsCentral with port other than '443'`** — you passed
another port to `UcscHandle(...)`. Raised at construction. Only 443 is supported.

**`TypeError: LsServer.__init__() missing 1 required positional argument: 'name'`** — naming
properties are required positional arguments, not optional keywords.

**`handle.commit()` returns `None` and nothing changed** — the commit buffer was empty. You
either forgot `add_mo`/`set_mo`, or already committed (a commit always empties the buffer).

**`AttributeError: 'UcscHandle' object has no attribute 'lookup_by_dn'`** — that method does
not exist. It is `query_dn`. The name appears in the SDK's own docstring, which is wrong; it
is a `ucsmsdk` habit.

**`ModuleNotFoundError: No module named 'six'` / `'pyparsing'`** — dependencies missing.
`pip install six pyparsing`, or install the SDK properly.

**`ImportError: cannot import name 'LsServer'`** — check the package. It is
`ucscsdk.mometa.ls.LsServer`, and the module name matches the class name exactly, including
case.
