# 2. The information model — MIT, DN, RN

> Every snippet in this guide runs offline with no server. They were executed against the
> installed package.

```python
from ucscsdk.mometa.ls.LsServer import LsServer

sp = LsServer("org-root", name="sp_demo")
sp.rn     # 'ls-sp_demo'
sp.dn     # 'org-root/ls-sp_demo'
```

## One tree

UCS Central keeps all state in a single tree: the **Management Information Tree** (MIT).
Every object in it is a **managed object** (MO), and every MO has exactly one place in the
tree.

```
topRoot
├── org-root                             OrgOrg
│   ├── ls-sp_demo                       LsServer
│   │   ├── ether-eth0                   VnicEther
│   │   └── boot-policy                  LsbootDef
│   └── org-Engineering                  OrgOrg
├── fabric
│   └── lan
│       └── net-100                      FabricVlan
└── domaingroup-root                     OrgDomainGroup
```

There is no "list of service profiles" endpoint. There is a tree, and you address parts of
it.

## RN — relative name

The **RN** identifies an object among its siblings. It is generated from a template stored
in the class's metadata:

```python
from ucscsdk.ucscmeta import MO_CLASS_META

MO_CLASS_META["LsServer"].rn      # 'ls-[name]'
MO_CLASS_META["FabricVlan"].rn    # 'net-[name]'
MO_CLASS_META["OrgOrg"].rn        # 'org-[name]'
MO_CLASS_META["LsbootDef"].rn     # 'boot-policy'
```

Anything in `[...]` is a **naming property**. `LsbootDef` has none — its RN is a fixed
string, so there can be only one per parent.

That is common. Of 1,831 classes:

| Naming properties | Classes |
|---|---|
| 0 — static RN | 806 |
| 1 | 887 |
| 2 | 92 |
| 3+ | 46 |

Some templates take several:

```python
MO_CLASS_META["LsVConAssign"].rn   # 'assign-[transport]-vnic-[vnic_name]'
```

## DN — distinguished name

The **DN** is the full path from the root: parent DN + `/` + RN. It is the primary key for
everything.

```python
sp = LsServer("org-root", name="sp_demo")
sp.dn                      # 'org-root/ls-sp_demo'

from ucscsdk.mometa.vnic.VnicEther import VnicEther
eth = VnicEther(sp, name="eth0")
eth.dn                     # 'org-root/ls-sp_demo/ether-eth0'
```

Pass the parent as an **MO** and the child is attached to it in memory as well as getting
the right DN. Pass a **string** and you only get the DN:

```python
eth2 = VnicEther("org-root/ls-sp_demo", name="eth1")
eth2.dn                    # 'org-root/ls-sp_demo/ether-eth1'
eth2.parent_mo             # None  — no in-memory link
```

Both are valid. Use the MO form when you are building a tree to commit in one shot; use the
string form when you already know the DN and do not have the parent object.

## Naming properties are required

They are positional arguments on the generated constructor:

```python
LsServer("org-root", name="sp_demo")     # fine
LsServer("org-root")                     # TypeError: missing 'name'
```

They are also **immutable after construction**. A naming property has access level
`NAMING`, which is not read-write, so reassignment is rejected:

```python
sp = LsServer("org-root", name="sp_demo")
sp.name = "other"
# ValueError: name is not a read-write property.
```

To "rename" an object you create a new one, or use the server-side rename method
`ucscmethodfactory.config_conf_rename`. Changing the attribute locally would desynchronise
the RN and DN from the name, which is exactly why the SDK forbids it.

If a naming property is `None` when the RN is built — which requires forcing past the
setter — RN generation fails:

```
UcscValidationException: [ErrorMessage]: Property "name" was None in make_rn
```

## Going backwards: DN to properties

```python
from ucscsdk import ucsccoreutils as cu

cu.get_naming_props("ls-sp_demo", "ls-[name]")
# {'name': 'sp_demo'}

cu.get_naming_props("assign-ethernet-vnic-eth0",
                    "assign-[transport]-vnic-[vnic_name]")
# {'transport': 'ethernet', 'vnic_name': 'eth0'}
```

Useful when a query hands you a DN and you need the parts.

## Where can this object live?

The metadata declares legal parents and children, so you never have to guess a DN:

```python
MO_CLASS_META["LsServer"].parents     # ['computeTemplate', 'orgOrg']
MO_CLASS_META["FabricVlan"].parents   # ['fabricEthEstcCloud', 'fabricLanCloud']
```

`LsServer` under `OrgOrg` — hence `org-root/ls-sp_demo`. Combine with the RN template and
the DN follows mechanically. This is the correct way to construct a DN; **guessing DN
strings is the most common source of silent failure**, because a wrong DN usually produces
an empty result rather than an error.

Children work the same way:

```python
len(MO_CLASS_META["LsServer"].children)   # 52
"vnicEther" in MO_CLASS_META["LsServer"].children   # True
```

Note children are listed in **wire case** (`vnicEther`), while class ids are Python case
(`VnicEther`). Normalise before comparing:

```python
cu.find_class_id_in_mo_meta_ignore_case("vnicEther")   # 'VnicEther'
```

## Well-known DNs

These are stable across installations and are the usual entry points:

| DN | Class | What |
|---|---|---|
| `org-root` | `OrgOrg` | root organisation |
| `org-root/org-<name>` | `OrgOrg` | sub-organisation |
| `org-root/ls-<name>` | `LsServer` | service profile |
| `org-root/ls-<name>/ether-<name>` | `VnicEther` | vNIC on a profile |
| `fabric/lan` | `FabricLanCloud` | LAN cloud |
| `fabric/lan/net-<name>` | `FabricVlan` | VLAN |
| `domaingroup-root` | `OrgDomainGroup` | root domain group |
| `sys` | `TopSystem` | system container |

Verify any of them the same way:

```python
from ucscsdk.mometa.top.TopSystem import TopSystem
TopSystem().dn        # 'sys'
```

## Object identity and status

An MO carries a `status` property that tells the server what to do with it on commit —
`created`, `modified`, `deleted`, or `created,modified`. You do not normally set it by
hand; `add_mo`/`set_mo`/`remove_mo` do it. See
[06 — create, modify, delete](06-create-modify-delete.md).

## Properties: Python names vs wire names

Every property has two names. Your code uses the Python one; the XML uses the other.

```python
from ucscsdk import ucsccoreutils as cu

pm = cu.get_mo_property_meta("LsServer", "usr_lbl")
pm.xml_attribute       # 'usrLbl'
```

The mapping lives on the class:

```python
LsServer.prop_map["usrLbl"]     # 'usr_lbl'
```

Roughly: `camelCase` on the wire, `snake_case` in Python. Never send the wire name from
your code — property assignment uses the Python name and will treat an unknown name as a
new, unvalidated property rather than raising.

## Common errors

**`ValueError: name is not a read-write property.`** — you tried to reassign a naming
property. They are fixed at construction; rename server-side with
`ucscmethodfactory.config_conf_rename` instead.

**`UcscValidationException: Property "name" was None in make_rn`** — a naming property was
`None` when the RN was built.

**`TypeError: __init__() missing 1 required positional argument`** — supply the naming
properties.

**A query returns `None` or `[]` for a DN you are sure exists** — the DN is wrong. Rebuild
it from `MO_CLASS_META[cid].rn` and `.parents` rather than typing it. Note that `query_dn`
returns `None` for a missing DN; it does not raise.

**`ValueError: parent mo or dn must be specified`** — the first argument was neither a
`ManagedObject` nor a `str`.

**A property you set silently does nothing** — you used the wire name (`usrLbl`) instead of
the Python name (`usr_lbl`). Unknown names are accepted and stored as extra properties, so
there is no error. Check against `prop_meta`:

```python
"usrLbl" in LsServer.prop_meta      # False  — wrong
"usr_lbl" in LsServer.prop_meta     # True   — right
```
