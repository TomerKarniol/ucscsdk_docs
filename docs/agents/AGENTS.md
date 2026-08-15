# AGENTS.md — operating manual for writing `ucscsdk` code

Dense reference for an AI agent. No narrative. Everything here is verified against
`ucscsdk` 0.9.0.10; see [`../_work/VERIFICATION.md`](../_work/VERIFICATION.md).

**Package is `ucscsdk` — Cisco UCS *Central*. Not `ucsmsdk` (UCS *Manager*). Their APIs and
class sets differ. Never mix them.**

Machine-readable companions:
- `mo-index.json` — 1,831 classes: package, rn, naming props, parents, counts. Load whole.
- `mo-details.jsonl` — one JSON object **per line**. `grep '"class_id": "LsServer"'` returns
  the full record including every property and every `<Class>Consts` value.
- `api-index.json` — handle surface, 122 methods with I/O contracts, basetypes, exceptions,
  filter types.

---

## 0. Non-negotiables

1. `add_mo` / `set_mo` / `remove_mo` **do not** contact the server. Nothing happens without
   `handle.commit()`.
2. A **failed `commit()` discards the buffer**. Re-stage before retrying.
3. `commit()` on an empty buffer returns `None` **silently**.
4. `query_dn` returns `None` for a missing DN. It does **not** raise.
5. Default filter type is **`re` (wildcard)**, not `eq`.
6. Never invent a DN. Derive it from `mo_meta.rn` + `mo_meta.parents`.
7. Property names in your code are **snake_case** (`usr_lbl`), not wire case (`usrLbl`).
8. Only **port 443**. Anything else raises at construction.

---

## 1. Ten canonical recipes

### 1.1 Connect

```python
from ucscsdk.ucschandle import UcscHandle

handle = UcscHandle("192.168.1.1", "admin", "password")
handle.login()
try:
    ...
finally:
    handle.logout()
```

`login(auto_refresh=True)` for anything running longer than `handle.refresh_period`.

### 1.2 Query one object

```python
sp = handle.query_dn("org-root/ls-sp_demo")
if sp is None:
    raise RuntimeError("not found")
```

### 1.3 Query many, with a filter

```python
sps = handle.query_classid("LsServer",
                           filter_str='(usr_lbl, "prod", type="eq")')
```

Never omit `type="eq"` when you mean equality. Multiple DNs / class ids take **lists**:

```python
handle.query_dns(["org-root/ls-a", "org-root/ls-b"])   # {dn: mo-or-None}
handle.query_classids(["OrgOrg", "FabricVlan"])        # {class_id: [mo]}
handle.query_children(in_dn="org-root/ls-sp_demo", class_id="VnicEther")
```

### 1.4 Create a service profile

```python
from ucscsdk.mometa.ls.LsServer import LsServer

sp = LsServer("org-root", name="sp_demo")
sp.descr = "created by automation"
handle.add_mo(sp, modify_present=True)
handle.commit()
```

`modify_present=True` makes it idempotent (`status="created,modified"`).

### 1.5 Modify

```python
sp = handle.query_dn("org-root/ls-sp_demo")
if sp is None:
    raise RuntimeError("not found")
sp.descr = "updated"
handle.set_mo(sp)
handle.commit()
```

Only `READ_WRITE` properties are assignable — about 19.5% of them.

### 1.6 Delete

```python
sp = handle.query_dn("org-root/ls-sp_demo")
if sp is not None:
    handle.remove_mo(sp)
    handle.commit()
```

Or without querying:

```python
handle.remove_mo(LsServer("org-root", name="sp_demo"))
handle.commit()
```

### 1.7 Transaction

```python
handle.add_mo(LsServer("org-root", name="sp1"), modify_present=True)
handle.add_mo(LsServer("org-root", name="sp2"), modify_present=True)
handle.commit()          # atomic: both, or neither
```

Independent transactions on one handle:

```python
handle.add_mo(mo1, tag="net")
handle.add_mo(mo2, tag="compute")
handle.commit(tag="net")
handle.commit(tag="compute")
```

### 1.8 Wait for an event

```python
def done(mce):
    print(mce.mo.dn, mce.mo.oper_state)

sp = handle.query_dn("org-root/ls-sp_demo")
if sp is None:
    raise RuntimeError("not found")
handle.wait_for_event(sp, "assoc_state", ["associated", "failed"], done,
                      timeout=1800)
```

Always set `timeout`. Always watch a **terminal** state list, not one transient value.
A `None` mo makes this return immediately with the callback never firing.

### 1.9 Backup

```python
from ucscsdk.utils.ucscbackup import backup_local, export_config_local

backup_local(handle, file_dir="/backups", file_name="full-state.tgz",
             remove_from_ucsc=True, timeout=3600)

export_config_local(handle, file_dir="/backups", file_name="config-all.tgz")
```

`backup_*` = full-state binary. `export_config_*` = importable logical config.
Domain backups are **remote-only**. There is no `export_config`.

### 1.10 Register a domain

```python
import os
from ucscsdk.utils.ucscdomain import is_domain_registered, domain_register

if not is_domain_registered(handle, "192.168.1.100"):
    domain_register(handle, domain_name_or_ip="192.168.1.100",
                    username=os.environ["UCSM_USER"],
                    password=os.environ["UCSM_PASS"],
                    timeout=300)
```

Credentials are the **UCS Manager** admin's. Needs UCS Central ≥ 1.5.

---

## 2. DN patterns

Verified from `mo_meta.rn` + `mo_meta.parents`.

| DN | Class |
|---|---|
| `sys` | `TopSystem` |
| `org-root` | `OrgOrg` |
| `org-root/org-<name>` | `OrgOrg` |
| `org-root/ls-<name>` | `LsServer` |
| `org-root/ls-<name>/ether-<name>` | `VnicEther` |
| `org-root/ls-<name>/fc-<name>` | `VnicFc` |
| `org-root/ls-<name>/iscsi-<name>` | `VnicIScsi` |
| `org-root/ls-<name>/conn-def` | `VnicConnDef` |
| `org-root/ls-<name>/boot-policy` | `LsbootDef` |
| `org-root/ls-<name>/power` | `LsPower` |
| `org-root/ls-<name>/pn-req` | `LsRequirement` |
| `org-root/lan-conn-templ-<name>` | `VnicLanConnTempl` |
| `org-root/san-conn-templ-<name>` | `VnicSanConnTempl` |
| `org-root/mac-pool-<name>` | `MacpoolPool` |
| `org-root/mac-pool-<name>/block-<from>-<to>` | `MacpoolBlock` |
| `org-root/ip-pool-<name>` | `IppoolPool` |
| `org-root/uuid-pool-<name>` | `UuidpoolPool` |
| `org-root/wwn-pool-<name>` | `FcpoolInitiators` |
| `org-root/iqn-pool-<name>` | `IqnpoolPool` |
| `org-root/compute-pool-<name>` | `ComputePool` |
| `org-root/blade-qualifier-<name>` | `ComputeQual` |
| `org-root/profile-<name>` | `LstorageProfile` |
| `org-root/fw-host-pack-<name>` | `FirmwareComputeHostPack` |
| `org-root/db-backup-policy-<name>` | `MgmtBackupPolicy` |
| `org-root/cfg-exp-policy-<name>` | `MgmtCfgExportPolicy` |
| `org-root/fault-policy` | `FaultPolicy` |
| `fabric/lan` | `FabricLanCloud` |
| `fabric/lan/net-<name>` | `FabricVlan` |
| `fabric/lan/net-group-<name>` | `FabricNetGroup` |
| `fabric/san` | `FabricSanCloud` |
| `domaingroup-root` | `OrgDomainGroup` |
| `domaingroup-root/domaingroup-<name>` | `OrgDomainGroup` |

**RN templating.** `[x]` is a naming property, required positionally in `__init__`:

```python
MO_CLASS_META["LsServer"].rn      # 'ls-[name]'
MO_CLASS_META["MacpoolBlock"].rn  # 'block-[r_from]-[to]'
```

806 of 1,831 classes have a **static** RN (no `[...]`) and take no naming argument.

Resolve an unknown DN properly:

```python
from ucscsdk.ucscmeta import MO_CLASS_META
from ucscsdk import ucsccoreutils as cu

cid = cu.find_class_id_in_mo_meta_ignore_case("fabricvlan")   # 'FabricVlan'
MO_CLASS_META[cid].rn                                          # 'net-[name]'
MO_CLASS_META[cid].parents                                     # legal parents
cu.get_meta_info(cid).config_props                             # writable props
```

---

## 3. Top 50 classes

Format: `Class` · package · rn · writable-property count.

**Service profiles & boot**
`LsServer` ls `ls-[name]` 25 · `LsServerExtension` ls `extension` 3 ·
`LsRequirement` ls `pn-req` 4 · `LsBinding` ls `pn` 3 · `LsPower` ls `power` 2 ·
`LsmaintAck` lsmaint `ack` 4 · `LsbootDef` lsboot `boot-policy` 6 ·
`LsbootStorage` lsboot `storage` 2 · `LsbootVirtualMedia` lsboot `[access]-vm` 4

**Org & domain groups**
`OrgOrg` org `org-[name]` 2 · `OrgDomainGroup` org `domaingroup-[name]` 2

**Network**
`FabricVlan` fabric `net-[name]` 8 · `FabricVsan` fabric `net-[name]` 6 ·
`FabricLanCloud` fabric `lan` 4 · `FabricSanCloud` fabric `san` 2 ·
`FabricNetGroup` fabric `net-group-[name]` 4 · `FabricPooledVlan` fabric `net-[name]` 1

**vNICs / vHBAs**
`VnicEther` vnic `ether-[name]` 16 · `VnicFc` vnic `fc-[name]` 17 ·
`VnicIScsi` vnic `iscsi-[name]` 19 · `VnicConnDef` vnic `conn-def` 3 ·
`VnicEtherIf` vnic `if-[name]` 2 · `VnicFcIf` vnic `if-default` 2 ·
`VnicLanConnTempl` vnic `lan-conn-templ-[name]` 14 ·
`VnicSanConnTempl` vnic `san-conn-templ-[name]` 11

**Pools**
`MacpoolPool` macpool `mac-pool-[name]` 2 · `MacpoolBlock` macpool `block-[r_from]-[to]` 2 ·
`IppoolPool` ippool `ip-pool-[name]` 2 · `IppoolBlock` ippool `block-[r_from]-[to]` 3 ·
`UuidpoolPool` uuidpool `uuid-pool-[name]` 3 ·
`UuidpoolBlock` uuidpool `block-from-[r_from]-to-[to]` 2 ·
`FcpoolInitiators` fcpool `wwn-pool-[name]` 2 · `FcpoolBlock` fcpool `block-[r_from]-[to]` 2 ·
`IqnpoolPool` iqnpool `iqn-pool-[name]` 3

**Compute**
`ComputeBlade` compute `blade-[slot_id]` 6 · `ComputeRackUnit` compute `rack-unit-[id]` 6 ·
`ComputePool` compute `compute-pool-[name]` 2 ·
`ComputePooledSlot` compute `system-[system_id]-blade-[chassis_id]-[slot_id]` 1 ·
`ComputePooledRackUnit` compute `system-[system_id]-rack-[id]` 1 ·
`ComputeQual` compute `blade-qualifier-[name]` 2 · `ComputePhysicalQual` compute `physical` 2

**Storage**
`LstorageProfile` lstorage `profile-[name]` 2 ·
`LstorageDasScsiLun` lstorage `das-scsi-lun-[name]` 10

**Identity & access**
`AaaUser` aaa `user-[name]` 13 · `AaaRole` aaa `role-[name]` 3 ·
`AaaLdapProvider` aaa `provider-[name]` 14 · `AaaOrg` aaa `org-[name]` 2

**Domains, firmware, ops**
`ExtpolRegistry` extpol `reg` 1 · `ExtpolProvider` extpol `prov-[type]` 1 ·
`FirmwareComputeHostPack` firmware `fw-host-pack-[name]` 10 ·
`FirmwareInfraPack` firmware `fw-infra-pack-[name]` 9 ·
`MgmtBackupPolicy` mgmt `db-backup-policy-[name]` 11 ·
`MgmtCfgExportPolicy` mgmt `cfg-exp-policy-[name]` 11 ·
`TopSystem` top `sys` 5 · `FaultInst` fault `fault-[code]` 4 ·
`FaultPolicy` fault `fault-policy` 12 · `PolicyControlEp` policy `control-ep-policy` 6

For anything else: `grep '"class_id": "X"' mo-details.jsonl`.

---

## 4. Filters

Only `query_classid` and `query_children` accept `filter_str`.

```
term := '(' prop ',' value [',' type="TYPE"] [',' flag="FLAG"] ')'
TYPE := re(default) | eq | ne | gt | ge | lt | le
FLAG := C(default) | I
```

Precedence: `not` > `and` > `or`.

```python
'(name, "web", type="eq")'
'(usr_lbl, "prod", type="eq") and (oper_state, "ok", type="eq")'
'not (dn, "org-root/ls-C1_B1", type="eq")'
```

Compile offline to check:

```python
from ucscsdk.ucscfilter import generate_infilter
from ucscsdk.ucscxmlcodec import to_xml_str

f = generate_infilter("LsServer", '(name, "web", type="eq")', True)
to_xml_str(f.to_xml())
```

`BwFilter`, `AnybitFilter`, `AllbitsFilter` are **not** expressible in `filter_str`; build
them with `create_basic_filter` (kwargs are snake_case: `first_value`, `second_value`).

---

## 5. Errors

Two unrelated roots — catching one misses the other:

```python
from ucscsdk.ucscexception import UcscWrapperException, UcscError

try:
    ...
except (UcscWrapperException, UcscError) as e:
    ...
```

`UcscWrapperException` → `UcscLoginError`, `UcscConnectionError`, `UcscOperationError`.
`UcscError` → `UcscException` (`.error_code`, `.error_descr`), `UcscValidationException`
(`.error_msg`).

`UcscException.error_code` is a **string** off the wire. `e.args` is empty — use `str(e)`.

Also expect plain builtins: `ValueError` (read-only property, invalid value, empty dn),
`TypeError` (missing naming property), `KeyError` (unknown filter property, unused commit
tag), `pyparsing.ParseException` (malformed filter).

---

## 6. Do not do this

**Wrong SDK**
- ✗ Using `ucsmsdk` APIs, class names or examples. Different product.
- ✗ `handle.lookup_by_dn(...)` — does not exist (it appears in the SDK's own docstring;
  that docstring is wrong). Use `query_dn`.
- ✗ `handle.delete_mo(...)` — does not exist. Use `remove_mo`.
- ✗ `handle.commit_mo(...)` — does not exist. Use `commit`.
- ✗ `from ucscsdk.utils.ucscbackup import export_config` — does not exist.

**Guessed DNs**
- ✗ Inventing a DN string. Derive from `MO_CLASS_META[cid].rn` and `.parents`.
- ✗ Assuming a wrong DN errors. It returns `None` / `[]`.

**Commit mistakes**
- ✗ Forgetting `commit()`. Silent no-op.
- ✗ Retrying `commit()` in a loop without re-staging — the buffer was discarded on failure.
- ✗ Staging the same DN twice expecting both to apply. Buffer is keyed by DN; last wins.
- ✗ Mutating an MO after `commit()` and expecting the server to see it. Stage again.
- ✗ Assuming a `None` return from `commit()` means success — it also means empty buffer.

**Filters**
- ✗ `'(name, "web")'` when you mean equality — that is a wildcard match.
- ✗ Passing `filter_str` to `query_dn`, `query_dns` or `query_classids` — no such parameter.
- ✗ `filter_str` on `query_children` without `class_id` — silently ignored.
- ✗ Wire property names in `filter_str` — use snake_case; translation is automatic.
- ✗ Unquoted values containing commas — truncated at the comma.

**Properties**
- ✗ Assigning wire names (`mo.usrLbl = "x"`). Silently stored as an unknown extra property,
  no error, and it is sent to the server.
- ✗ Assigning read-only properties — `ValueError`.
- ✗ Reassigning a naming property — `ValueError`; they are fixed at construction.
- ✗ Trusting client-side validation. It short-circuits: a satisfied `min_length` skips the
  `pattern` check entirely. The server is the authority.

**Errors**
- ✗ `except UcscError` alone — misses login/connection failures.
- ✗ Comparing `e.error_code` to an int — it is a string.
- ✗ Reading `e.args` on `UcscException` — always empty.

**Broken APIs — do not call**
- ✗ `ucsccoreutils.load_mo` — `AttributeError` on Python 3.11+.
- ✗ `GenericMo.to_mo` — same.
- ✗ `ManagedObject.show_tree` — always fails (`self.children` does not exist).
- ✗ `ucsccoreutils.write_mo_tree` / `extract_mo_tree_from_config_method_response` — always
  fail (`mo.class_id` does not exist).
- ✗ `handle.is_local_download_supported()` — `ModuleNotFoundError` on 3.13+ (`distutils`);
  its logic is also inverted relative to its name.
- ✗ `MethodPropertyMeta.name` — `RecursionError`.

Walk a tree manually instead:

```python
def walk(mo, depth=0):
    print("  " * depth + mo.dn)
    for ch in mo.child:
        walk(ch, depth + 1)
```

**Threading / concurrency**
- ✗ Expecting threads to speed up requests. A process-global lock serializes every request
  across every handle. Batch into fewer commits instead.
- ✗ Staging in one thread and committing in another under threading mode — the tag is the
  current thread's name.
- ✗ Duplicate thread names under threading mode — they share a buffer.

**Security**
- ✗ Assuming TLS is verified. It is not: no CA bundle, `check_hostname=False`,
  `verify_mode=CERT_NONE`, with no option to change it. Trusted networks only.
- ✗ Sharing `set_dump_xml()` output unscrubbed — session cookies are logged (the login
  password is masked).
- ✗ Hard-coding credentials. Read from the environment.

**Misc**
- ✗ Any port but 443 — `UcscLoginError` at construction.
- ✗ Treating `handle.ucs` as the system name — it is the IP you passed. Query `sys`.
- ✗ Using `UcscVersion` as a dict key — unhashable.
- ✗ Expecting `hierarchy=True` on `query_dn` to return one object — it returns a flat list
  and detaches children from parents while building it.
- ✗ `to_xml_str(...)` returns **bytes**; decode before printing.

---

## 7. Version gating

Every `MoMeta` and `MoPropertyMeta` carries the release that introduced it:

```python
from ucscsdk.ucscmeta import MO_CLASS_META
from ucscsdk.ucsccoremeta import UcscVersion
from ucscsdk import ucsccoreutils as cu

str(MO_CLASS_META["LsServer"].version)                     # '1.0(1a)'
str(cu.get_mo_property_meta("LsServer", "oper_state").version)   # '1.1(1a)'
UcscVersion("2.0(1a)") > UcscVersion("1.5(1a)")            # True
```

Check before using a newer property against an older server.
`UcscVersion("garbage")` does **not** raise — it constructs with all components `None` and
compares as older than everything.
