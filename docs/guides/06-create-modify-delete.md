# 6. Create, modify, delete

> Examples need a live server unless marked otherwise. All XML shown was generated offline
> by the SDK's own encoder.

```python
from ucscsdk.mometa.ls.LsServer import LsServer

sp = LsServer("org-root", name="sp_demo")
sp.descr = "created from python"

handle.add_mo(sp)
handle.commit()
```

## Nothing happens until `commit()`

`add_mo`, `set_mo` and `remove_mo` do not touch the network. They set `mo.status` and put
the object into a **commit buffer** keyed by DN. `commit()` sends the whole buffer as one
`ConfigConfMos` request.

| Call | Sets `status` to |
|---|---|
| `add_mo(mo)` | `created` |
| `add_mo(mo, modify_present=True)` | `created,modified` |
| `set_mo(mo)` | `modified` |
| `remove_mo(mo)` | `deleted` |

Forgetting `commit()` is the most common bug with this SDK, and it is silent — no error, no
change.

## Create

```python
from ucscsdk.mometa.ls.LsServer import LsServer

sp = LsServer("org-root", name="sp_demo")
sp.descr = "web tier"
sp.usr_lbl = "prod"

handle.add_mo(sp)
handle.commit()
```

The wire payload, generated offline:

```xml
<configConfMos cookie="..." inHierarchical="false">
  <inConfigs>
    <pair key="org-root/ls-sp_demo">
      <lsServer name="sp_demo" status="created" usrLbl="prod" dn="org-root/ls-sp_demo"/>
    </pair>
  </inConfigs>
</configConfMos>
```

Only properties you actually set appear. That is the dirty-mask mechanism: assigning a
property marks it, and serialization emits marked properties only.

### `modify_present` — upsert

By default, creating something that already exists is an error from the server. With
`modify_present=True` the status becomes `created,modified`, which tells UCS Central to
create it or update it in place:

```python
handle.add_mo(sp, modify_present=True)
handle.commit()
```

Use this for idempotent scripts. Note it accepts the SDK's affirmative values, so `True`,
`"true"` and `"yes"` all work.

### Creating a subtree

Build children against the parent MO and commit the parent once:

```python
from ucscsdk.mometa.ls.LsServer import LsServer
from ucscsdk.mometa.vnic.VnicEther import VnicEther

sp = LsServer("org-root", name="sp_demo")
VnicEther(sp, name="eth0")
VnicEther(sp, name="eth1")

handle.add_mo(sp)
handle.commit()
```

Passing the parent MO attaches the child in memory, and the children are serialized inside
the parent's element. You do not call `add_mo` on each child.

## Modify

```python
sp = handle.query_dn("org-root/ls-sp_demo")
sp.descr = "updated"
handle.set_mo(sp)
handle.commit()
```

Query, mutate, stage, commit. A freshly parsed MO has a clean dirty mask, so only the
properties you change after the query are sent.

Only writable properties can be assigned. Roughly one property in five is `READ_WRITE`:

```python
sp.oper_state = "ok"
# ValueError: oper_state is not a read-write property.
```

To see what you may change:

```python
from ucscsdk import ucsccoreutils as cu
cu.get_meta_info("LsServer").config_props     # 25 names
```

> Runs offline.

Values are validated client-side against the metadata's pattern, length or value set:

```python
sp.usr_lbl = "x" * 99
# ValueError: Invalid Value Exception - [LsServer]: Prop <usr_lbl>, Value<xxx…>
```

That validation is **weaker than it looks**. If a property declares both a length limit and
a pattern, only the length is checked — the validator returns as soon as the first
restriction passes. Passing client-side validation is not a promise the server will accept
the value.

### Setting many properties at once

```python
sp.set_prop_multiple(descr="updated", usr_lbl="prod")
```

Unknown names are set forcibly with a logged warning rather than raising — convenient for
properties a newer server understands, dangerous for typos.

## Delete

```python
sp = handle.query_dn("org-root/ls-sp_demo")
handle.remove_mo(sp)
handle.commit()
```

Deletion travels as `status="deleted"` inside the same `ConfigConfMos`, not as a separate
method. `remove_mo` also detaches the object from its in-memory parent so a later
serialization of that parent does not resurrect it.

You do not need to query first if you can construct the DN:

```python
handle.remove_mo(LsServer("org-root", name="sp_demo"))
handle.commit()
```

Deleting a parent deletes its children server-side.

There is no `delete_mo`. The old user guide names one; it does not exist.

## What `commit()` does

1. Empty buffer → logs a debug line and returns `None`. **No error.**
2. Wraps each staged MO in a `<pair key="<dn>">` inside a `ConfigConfMos`.
3. Posts it.
4. On error: **discards the buffer**, then raises `UcscException`.
5. On success: copies server-returned values back onto your objects, re-reads any dirty
   descendants, and clears the buffer.

Point 4 matters. A failed commit loses your staged changes — there is no fix-and-retry.
Rebuild the buffer.

Point 5 means your local object is refreshed in place:

```python
sp = LsServer("org-root", name="sp_demo")
handle.add_mo(sp)
handle.commit()
sp.oper_state        # populated by the server's response
```

## The buffer is keyed by DN

Staging the same DN twice keeps only the last object:

```python
handle.add_mo(sp_v1)
handle.add_mo(sp_v2)     # same dn — replaces sp_v1 entirely
handle.commit()          # only sp_v2 is sent
```

Mutate one object rather than staging two.

## Discarding

```python
handle.add_mo(sp)
handle.commit_buffer_discard()    # never sent
```

Useful when validation fails halfway through building a batch.

## Transactions

Everything staged before a `commit()` goes in one request, so it succeeds or fails
together:

```python
handle.add_mo(LsServer("org-root", name="sp1"))
handle.add_mo(LsServer("org-root", name="sp2"))
handle.commit()          # both, or neither
```

For several independent transactions on one handle, use `tag=`. See
[07 — transactions and threading](07-transactions-and-threading.md).

## Common errors

**Nothing happened, no error** — you forgot `commit()`, or the buffer was already empty
because a previous `commit()` cleared it.

**`ValueError: <prop> is not a read-write property.`** — the property is read-only,
internal, or a create-only that already has a value.

**`ValueError: Invalid Value Exception - [Class]: Prop <p>, Value<v>`** — failed the
metadata restriction. Inspect it:

```python
cu.get_mo_property_meta("LsServer", "usr_lbl").restriction.pattern
```

**`UcscException` on commit, and my staged changes are gone** — expected. The buffer is
discarded before the exception is raised.

**`UcscException: ... already exists`** — use `add_mo(mo, modify_present=True)`.

**`TypeError: __init__() missing 1 required positional argument`** — naming properties are
positional and required.

**Server rejects a value that passed client validation** — expected; the client-side
validator short-circuits and the server enforces more rules.

**Only some of my changes were sent** — you staged two objects with the same DN, or you set
properties before the object was in a state where assignment marked them dirty. Check with
`handle.set_dump_xml()`.

**`AttributeError: 'UcscHandle' object has no attribute 'delete_mo'`** — it is `remove_mo`.

**`AttributeError: 'UcscHandle' object has no attribute 'commit_mo'`** — it is `commit`.
