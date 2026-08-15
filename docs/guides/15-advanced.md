# 15. Advanced

> Snippets are marked where they need a server. XML shown was generated offline.

```python
from ucscsdk import ucscmethodfactory as mf

elem = mf.config_find_dns_by_class_id(cookie=handle.cookie,
                                      class_id="lsServer", in_filter=None)
dns = handle.process_xml_elem(elem)
```

## Calling XML methods directly

`UcscHandle` wraps a handful of the 122 XML methods. For the rest, build the element with
`ucscmethodfactory` and post it with `process_xml_elem`:

```python
process_xml_elem(elem, dme="central-mgr")
```

It posts, raises `UcscException` on a non-zero error code, and unwraps the result:

| Response contains | You get |
|---|---|
| `out_config` | `response.out_config.child` |
| `out_configs` | flat list of MOs (unwrapping `Pair` elements) |
| `out_dns` | `response.out_dns.child` |
| none of these | the `ExternalMethod` itself |

Every builder takes `cookie` first and returns an `xml.etree` Element. Useful ones with no
handle wrapper:

```python
mf.config_conf_rename(cookie, dn, in_new_name, in_hierarchical='false')
mf.ls_clone(cookie, dn, in_server_name, in_target_org, in_hierarchical='false')
mf.ls_instantiate_template(...)
mf.config_find_dependencies(...)
mf.config_resolve_children_sorted(...)
mf.fault_ack_faults(...)
```

The full list with signatures and input/output contracts is in
[`reference/methods.md`](../reference/methods.md).

### Inspecting before sending

```python
from ucscsdk import ucscxmlcodec as xc

elem = mf.config_resolve_dn(cookie="c", dn="org-root", in_hierarchical=False)
print(xc.to_xml_str(elem).decode())
# <configResolveDn cookie="c" dn="org-root" inHierarchical="false" />
```

> Runs offline. `to_xml_str` returns **bytes** — decode before printing.

Note booleans become the strings `"false"`/`"true"`; the wire never sees a Python bool.

## Hand-built filters

The `filter_str` language covers seven of the thirteen filter types. For the rest, build the
object and pass it as `in_filter`:

```python
from ucscsdk.ucscfilter import create_basic_filter
from ucscsdk.ucscbasetype import FilterFilter

bw = create_basic_filter("BwFilter", class_="lsServer", property="name",
                         first_value="a", second_value="m")
in_filter = FilterFilter()
in_filter.child_add(bw)

elem = mf.config_resolve_class(cookie=handle.cookie, class_id="lsServer",
                               in_filter=in_filter, in_hierarchical=False)
mos = handle.process_xml_elem(elem)
```

Composite filters nest:

```python
from ucscsdk.ucscfiltertype import AndFilter

and_f = AndFilter()
and_f.child_add(create_basic_filter("EqFilter", class_="lsServer",
                                    property="usrLbl", value="prod"))
and_f.child_add(bw)
```

Building filters by hand means **you** supply the wire property name (`usrLbl`), because
the name translation only happens in the `filter_str` path.

One quirk to be aware of. `AbstractFilter.to_xml` emits each attribute under its Python
name, special-casing only `class_` → `class`. So `BwFilter` serializes as:

```xml
<bw class="lsServer" first_value="a" property="name" second_value="m" />
```

The attributes are `first_value`/`second_value`, not camelCase like every other wire name in
this SDK. That is what the SDK sends; if the server rejects it, this is why. The seven
filter types reachable from `filter_str` are unaffected — they only use `class`, `property`
and `value`.

## `dme=`

Every query, `commit` and `process_xml_elem` accepts `dme="central-mgr"`. It is the last
path segment of the endpoint:

```
https://<host>:443/xmlIM/<dme>
```

`central-mgr` is the default and is right for essentially everything. The argument exists so
a caller can address a different DME on the same host. Change it only if you know the DME
name you need; an unknown one produces a transport-level error, not a friendly message.

## Dumping XML

```python
handle.set_dump_xml()
handle.query_dn("org-root")
handle.unset_dump_xml()
```

> Needs a live server.

Requests and responses go to the `ucscentral` logger at DEBUG:

```python
import logging, ucscsdk
ucscsdk.set_log_level(logging.DEBUG)
```

The `aaaLogin` password is masked and restored; **session cookies are not masked**. Scrub
dumps before sharing them.

## Parallel transactions

Covered in [07](07-transactions-and-threading.md); the short version:

```python
handle.add_mo(mo1, tag="net")
handle.add_mo(mo2, tag="compute")
handle.commit(tag="net")
handle.commit(tag="compute")
```

Tagged buffers are independent. Requests still serialize on a process-global lock, so this
is isolation, not parallelism.

## Working with unknown classes

If UCS Central returns a class this SDK version has never heard of, you get a `GenericMo`
rather than an exception:

```python
from ucscsdk.ucscmo import generic_mo_from_xml

g = generic_mo_from_xml('<someNewThing dn="org-root/x" foo="bar"/>')
g.properties        # {'dn': 'org-root/x', 'foo': 'bar', 'rn': 'x'}
g.get_class_id()    # 'someNewThing'  — wire case
```

> Runs offline.

The same applies to unknown *properties* on a known class: they are stored and re-emitted on
write, so a read-modify-write cycle does not silently drop fields a newer server understands.

`GenericMo.to_mo()` converts back to a typed MO — but it is **broken on Python 3.11+**
(`inspect.getargspec` was removed). Use `ucsccoreutils.load_class` and construct the object
yourself.

## Metadata-driven code

You can write code that works against classes you have never seen:

```python
from ucscsdk import ucsccoreutils as cu
from ucscsdk.ucscmeta import MO_CLASS_META

cid = cu.find_class_id_in_mo_meta_ignore_case("lsserver")   # 'LsServer'
meta = MO_CLASS_META[cid]
meta.rn                                    # 'ls-[name]'
cu.get_meta_info(cid).config_props         # writable property names
```

> Runs offline.

For the full picture see [internals/metadata-system.md](../internals/metadata-system.md), and
for machine-readable form `agents/mo-index.json` plus `agents/mo-details.jsonl`.

## Uploading and downloading files

`UcscSession` exposes the transfer primitives the utils modules use:

```python
handle.file_download(url_suffix, file_dir, file_name, progress=Progress())
handle.file_upload(url_suffix, file_dir, file_name, progress=Progress())
```

The parameter is `file_dir`, despite the docstrings saying `dest_dir` and `source_dir`.
Pass your own `Progress` subclass to control reporting.

Prefer the `utils` wrappers ([10](10-backup-export-import.md), [12](12-firmware.md),
[13](13-tech-support.md)) — they handle the create-poll-download sequence for you.

## Things that do not work

Verified broken on modern Python. Do not build on them:

| Symbol | Status |
|---|---|
| `ucsccoreutils.load_mo` | `AttributeError` on 3.11+ — use `load_class` |
| `GenericMo.to_mo` | `AttributeError` on 3.11+ |
| `ManagedObject.show_tree` | always fails — uses `self.children`, attribute is `child` |
| `ucsccoreutils.write_mo_tree` | always fails — uses `mo.class_id`, accessor is `get_class_id()` |
| `extract_mo_tree_from_config_method_response` | always fails — calls the above |
| `UcscHandle.is_local_download_supported` | `ModuleNotFoundError` on 3.13+ (`distutils`) |
| `MethodPropertyMeta.name` | `RecursionError` — the getter returns itself |
| `TLS1Connection.connect` | `AttributeError` on 3.12+ (`ssl.wrap_socket`) |

To walk a tree yourself, recurse over `mo.child`:

```python
def walk(mo, depth=0):
    print("  " * depth + "%s (%s)" % (mo.dn, mo.get_class_id()))
    for ch in mo.child:
        walk(ch, depth + 1)
```

`print_mo_hierarchy` does work, and prints the *metadata* hierarchy for a class id rather
than a live object:

```python
cu.print_mo_hierarchy("LsServer", depth=1)
```

> Runs offline.

## Security notes

Two facts worth designing around:

- **TLS certificates are not verified** — no CA bundle, `check_hostname=False`,
  `verify_mode=CERT_NONE`, with no option to change it. An active man-in-the-middle is not
  detected.
- **Response XML is parsed with the stdlib parser.** External entities are blocked, so
  classic XXE file disclosure does not apply, but internal entity expansion is performed —
  a hostile server can send a small document that costs a great deal of memory.

Together: on an untrusted network, neither the transport nor the parser is protecting you.
Use UCS Central over a trusted management network.

## Common errors

**`AttributeError: module 'inspect' has no attribute 'getargspec'`** — `load_mo` or
`to_mo`. See the table above.

**`TypeError: a bytes-like object is required`** — `to_xml_str` returns bytes; decode it.

**`UcscException` from `process_xml_elem`** — non-zero error code in the response. Read
`error_code` and `error_descr`.

**`process_xml_elem` returned an `ExternalMethod` instead of MOs** — the response had none
of `out_config`, `out_configs`, `out_dns`. Inspect the object directly.

**Hand-built filter matches nothing** — you used the Python property name. Direct filter
construction needs the wire name (`usrLbl`, not `usr_lbl`).

**`KeyError` from `create_basic_filter`** — wrong kwargs for that filter type. `BwFilter`
needs `first_value` and `second_value`, in snake_case.

**Changing `dme=` broke everything** — `central-mgr` is almost always correct.
