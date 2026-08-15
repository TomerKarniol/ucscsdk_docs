# Request lifecycle

> Two complete traces: one read, one write. Every file:line points at
> `ucscsdk/ucscsdk/`. All XML below was produced by running the SDK's encoder offline —
> the request documents are byte-exact. Response documents are hand-written minimal
> examples fed through the real parser.
>
> Not executed against live hardware.

---

## Read path

### `handle.query_dn("org-root")`

#### 1. `UcscHandle.query_dn` — `ucschandle.py:312`

```python
def query_dn(self, dn, hierarchy=False, need_response=False, dme="central-mgr"):
    ...
```

Guards on empty `dn` (`:342`, raises `ValueError`), then builds the method document:

```python
elem = config_resolve_dn(cookie=self.cookie,        # :345
                         dn=dn,
                         in_hierarchical=hierarchy)
```

#### 2. `ucscmethodfactory.config_resolve_dn` — `ucscmethodfactory.py:912`

```python
def config_resolve_dn(cookie, dn, in_hierarchical=YesOrNo.FALSE):
    method = ExternalMethod("ConfigResolveDn")
    method.cookie = cookie
    method.dn = dn
    method.in_hierarchical = (("false", "true")[in_hierarchical in ucscgenutils.AFFIRMATIVE_LIST])
    xml_request = method.to_xml(option=WriteXmlOption.DIRTY)
    return xml_request
```

Three things happen here, and they are the same in all 122 factory functions:

- `ExternalMethod("ConfigResolveDn")` loads `methodmeta/ConfigResolveDnMeta.py` through
  `ucsccoreutils.load_module` (`ucscmethod.py:51`) and pre-seeds every property in
  `prop_meta` to `None` (`ucscmethod.py:60`).
- Booleans are normalised to the strings `"false"`/`"true"` via
  `ucscgenutils.AFFIRMATIVE_LIST`. The wire never sees a Python bool.
- `to_xml(option=WriteXmlOption.DIRTY)` — **all 122 builders pass `DIRTY`**, so only
  properties that were actually set are emitted.

`ExternalMethod.to_xml` (`ucscmethod.py:99`) skips any property whose meta says
`inp_out == "Output"` (`:111`) and recurses into complex types (`:113`).

The result is an `xml.etree` Element, not a string:

```xml
<configResolveDn cookie="&lt;real-cookie&gt;" dn="org-root" inHierarchical="false" />
```

#### 3. `UcscSession.post_elem` — `ucscsession.py:226`

```python
self._tx_lock_acquire_conditional(elem)      # :244  global lock, skipped for aaaLogout
if self._is_stale_cookie(elem):              # :245
    elem.attrib['cookie'] = self.cookie      # :246  repair a rotated cookie in place
self.dump_xml_request(elem)                  # :248
xml_str = xc.to_xml_str(elem)                # :249
response_str = self.post_xml(xml_str, dme=dme)   # :251
self.dump_xml_response(response_str)         # :252
response = xc.from_xml_str(response_str, self)   # :255
if elem.tag == "aaaRefresh":                 # :260
    self._update_cookie(response)            # :261  inside the lock, on purpose
self._tx_lock_release_conditional(elem)      # :263
```

The stale-cookie repair at `:245` matters: an element built before an auto-refresh rotated
the cookie is patched just before it goes out, so a long-lived `elem` never fails
authentication.

`dump_xml_request` (`ucscsession.py:207`) masks `inPassword` on `aaaLogin` before logging
and restores it afterwards — enabling `set_dump_xml()` does not leak the password.

#### 4. `ucscxmlcodec.to_xml_str` — `ucscxmlcodec.py:26`

```python
return ET.tostring(elem)
```

On Python 3 this returns **`bytes`**, not `str`. Anything consuming it must decode.

#### 5. `UcscSession.post_xml` → `post` → driver — `ucscsession.py:188`, `:170`

```python
ucsm_uri = self.__uri + "/xmlIM/" + dme       # :202
```

This is the only place `dme=` is used. `"central-mgr"` is the default everywhere; the
argument exists so callers can address a different DME on the same host.

`UcscDriver.post` (`ucscdriver.py:233`) builds an opener from the handler list
(`:258`), and on any exception whose text contains `"ssl"` retries once against
`TLS1Handler` (`:261-267`). It follows one 301/302 redirect (`:268-278`) and caches the
redirect target in `__redirect_uri`, so later posts skip straight there (`:252`).
`read=True` decodes the body as UTF-8 (`:282`).

#### 6. `ucscxmlcodec.from_xml_str` — `ucscxmlcodec.py:66`

```python
root_elem = ET.fromstring(xml_str)
if root_elem.tag == "error":                 # :85
    raise ex.UcscException(root_elem.attrib['errorCode'],
                           root_elem.attrib['errorDescr'])
class_id = ucscgenutils.word_u(root_elem.tag)     # :90  configResolveDn → ConfigResolveDn
response = ucsccoreutils.get_ucsc_obj(class_id, root_elem)   # :91
response.from_xml(root_elem, handle)              # :92
```

A top-level `<error>` document raises immediately — before any handle-level error check
sees it:

```
>>> xc.from_xml_str('<error errorCode="103" errorDescr="nope"/>')
UcscException: [ErrorCode]: 103[ErrorDescription]: nope
```

#### 7. `ucsccoreutils.get_ucsc_obj` — `ucsccoreutils.py:35`

The dispatch that turns tags into objects:

| Test | Result | Line |
|---|---|---|
| `class_id in METHOD_CLASS_ID` | `ExternalMethod(class_id)` | `:54` |
| `class_id in MO_CLASS_ID` | the generated MO class, via `load_class` | `:56` |
| `class_id in OTHER_TYPE_CLASS_ID` | `ucscbasetype`/filter type | `:80` |
| otherwise | `GenericMo` | `:95` |

For an MO it introspects the generated `__init__` to discover the naming properties
(`:60`), passes them all as `None`, and sets `from_xml_response=True` so `__init__` skips
RN/DN computation (`ucscmo.py:81`) — the server already told us the DN.

The parent DN is recovered with `os.path.dirname(elem.attrib["dn"])` (`:70`).

#### 8. `from_xml` fills the graph — `ucscmethod.py:123`, `ucscmo.py:351`

`ExternalMethod.from_xml` maps XML attribute names to Python names through `prop_map`
(`:131`), skips `Input`-only properties (`:134`), and for complex `Output` children builds
the child object and recurses (`:155-161`). `outConfig` becomes `response.out_config`.

`ManagedObject.from_xml` (`ucscmo.py:351`) does the same for MOs, and critically: an
attribute **not** in `prop_map` is not discarded — it is recorded in `__xtra_props`
(`:365`) and set on the instance anyway (`:369`). Then `mark_clean()` (`:379`) zeroes the
dirty mask, so a freshly parsed MO is not considered modified.

Verified round-trip:

```python
resp = ('<configResolveDn dn="org-root" cookie="c" response="yes">'
        '<outConfig><orgOrg dn="org-root" name="root"/></outConfig>'
        '</configResolveDn>')
o = xc.from_xml_str(resp)
o.error_code                        # 0
o.out_config.child[0].get_class_id()  # 'OrgOrg'
o.out_config.child[0].dn              # 'org-root'
```

#### 9. Back in `query_dn` — `ucschandle.py:349`

```python
if response.error_code != 0:                  # :349
    raise UcscException(response.error_code, response.error_descr)
if need_response:  return response            # :352
if hierarchy:                                 # :355
    return ucsccoreutils.extract_molist_from_method_response(response, hierarchy)
mo = None
if len(response.out_config.child) > 0:        # :363
    mo = response.out_config.child[0]
return mo
```

`error_code` defaults to the integer `0` (`ucscmethod.py:63`) but arrives from XML as a
**string**. `"103" != 0` is true, so the check works — but never write
`response.error_code == 0` expecting an int on a real response.

Return shape depends on the flags:

| Flags | Returns |
|---|---|
| default | one `ManagedObject`, or `None` |
| `hierarchy=True` | flat `list` of MOs |
| `need_response=True` | the `ExternalMethod` (checked **before** `hierarchy`) |

#### 10. `extract_molist_from_method_response` — `ucsccoreutils.py:274`

Accepts either `out_config` or `out_configs` (`:296-299`). With `in_hierarchical=False` it
returns `resp_configs.child` directly. With `True` it walks the tree — **destructively**:

```python
while mo.child_count() > 0:          # :312
    for child in mo.child:
        mo.child_remove(child)       # :314  detaches from the parent
        child.mark_clean()
        child_mo_list.append(child)
        break
```

`hierarchy=True` therefore gives you a flat list *and dismantles the tree while building
it*. The returned MOs no longer have their children attached. If you need the tree intact,
use `need_response=True` and walk `out_config` yourself.

### The other four query methods

Same spine, different builder:

| Handle method | Builder | Returns |
|---|---|---|
| `query_dn` `:312` | `config_resolve_dn` | one MO |
| `query_dns` `:217` | `config_resolve_dns` | `{dn: mo}`, missing DNs stay `None` (`:244`) |
| `query_classid` `:367` | `config_resolve_class` | list of MOs |
| `query_classids` `:263` | `config_resolve_classes` | `{class_id: [mo]}` |
| `query_children` `:452` | `config_resolve_children` | list of MOs |

`query_classid` and `query_children` additionally resolve the class id case-insensitively
through `find_class_id_in_mo_meta_ignore_case` (`:424`, `:526`) and compile `filter_str`
via `generate_infilter` (`:432`, `:535`):

```xml
<configResolveClass classId="lsServer" cookie="c" inHierarchical="false">
  <inFilter><eq class="lsServer" property="name" value="web"/></inFilter>
</configResolveClass>
```

`query_classids` (`:308`) indexes its result dict by `out_mo.get_class_id()` — a class id
returned by the server that was not requested raises `KeyError`.

---

## Write path

### `handle.add_mo(sp)` then `handle.commit()`

#### 1. Build the MO

```python
from ucscsdk.mometa.ls.LsServer import LsServer

sp = LsServer("org-root", name="test_sp", usr_lbl="demo")
```

`ManagedObject.__init__` (`ucscmo.py:60`) resolves the parent (`:72-79`), computes RN then
DN (`:82-83`), and applies `**kwargs` through `__set_prop` (`:96`). Each assignment runs
`validate_property_value` (`ucscmo.py:180`) and ORs the property's `mask` into
`_dirty_mask` (`:188`). The dirty mask is what makes the property appear in the XML later.

Assignments are validated, not merely stored:

```
>>> sp.oper_state = "up"
ValueError: oper_state is not a read-write property.
>>> sp.usr_lbl = "x" * 99
ValueError: Invalid Value Exception - [LsServer]: Prop <usr_lbl>, Value<xxx…>
```

#### 2. `add_mo` — `ucschandle.py:585`

```python
tag = self._auto_set_tag_context(tag)                      # :605
if modify_present in ucscgenutils.AFFIRMATIVE_LIST:        # :607
    mo.status = "created,modified"
else:
    mo.status = "created"                                  # :610
self._update_commit_buf(mo, tag)                           # :612
```

No network call. `_update_commit_buf` (`:559`) stores `buf[mo.dn] = mo` — **keyed by DN**,
so staging the same DN twice keeps only the last object.

`_auto_set_tag_context` (`:569`) returns your explicit `tag` unchanged; otherwise, only if
threading mode is on, it returns `threading.currentThread().name`.

#### 3. `commit` — `ucschandle.py:666`

```python
mo_dict = self._get_commit_buf(tag)          # :690
if not mo_dict:                              # :691
    log.debug("Commit Buffer is Empty")
    return None                              # silent no-op
```

An empty buffer returns `None` quietly. Forgetting `add_mo` produces no error at all.

It then walks each staged MO's descendants and records the dirty ones in `refresh_dict`
(`:698-705`), and wraps every MO in a `<pair>` keyed by DN:

```python
pair = Pair()                    # :707
pair.key = mo_dn
pair.child_add(mo_dict[mo_dn])
config_map.child_add(pair)
elem = config_conf_mos(self.cookie, config_map, False)   # :712
```

#### 4. `config_conf_mos` — `ucscmethodfactory.py:389`

Same shape as every builder, `WriteXmlOption.DIRTY` again. `ManagedObject.to_xml`
(`ucscmo.py:307`) then emits only properties whose mask is set:

```python
if option == WriteXmlOption.DIRTY and not self.is_dirty():   # :312
    return                                                    # skipped entirely
...
if (option != WriteXmlOption.DIRTY or
        (mo_prop_meta.mask is not None and
         self._dirty_mask & mo_prop_meta.mask != 0)):          # :323
    xml_obj.set(mo_prop_meta.xml_attribute, value)
```

Unknown properties from `__xtra_props` are emitted too (`:339-343`), and `dn` is forced in
if absent (`:345`).

The real payload:

```xml
<configConfMos cookie="c" inHierarchical="false">
  <inConfigs>
    <pair key="org-root/ls-test_sp">
      <lsServer name="test_sp" status="created" usrLbl="demo" dn="org-root/ls-test_sp"/>
    </pair>
  </inConfigs>
</configConfMos>
```

Note `usr_lbl` → `usrLbl`: the Python name is translated through `MoPropertyMeta`, never
sent as-is.

#### 5. Post, then reconcile — `ucschandle.py:713`

```python
response = self.post_elem(elem, dme=dme)     # :713
if response.error_code != 0:                 # :714
    self.commit_buffer_discard(tag)          # :715  buffer is dropped before raising
    raise UcscException(response.error_code, response.error_descr)

for pair_ in response.out_configs.child:     # :718
    for out_mo in pair_.child:
        out_mo.sync_mo(mo_dict[out_mo.dn])   # :720  server values → your objects
```

**A failed commit discards your staged changes.** There is no retry-after-fix; you rebuild
the buffer.

`sync_mo` (`ucscmo.py:398`) copies the server's returned properties back onto the object you
handed in, so your local `sp` reflects server-assigned fields after a successful commit.

If any descendants were dirty, a second round-trip re-reads them with `config_resolve_dns`
(`:729-737`), because `ConfigConfMos` returns only the top-level objects.

Finally `commit_buffer_discard(tag)` (`:739`) clears the buffer on success too — a
committed buffer is always empty afterwards, success or failure.

#### 6. `commit_buffer_discard` — `ucschandle.py:741`

```python
tag = self._auto_set_tag_context(tag)
if tag is None:
    self.__commit_buf = {}                   # :758
if tag in self.__commit_buf_tagged:          # :760
    del self.__commit_buf_tagged[tag]
```

### Delete

`remove_mo` (`ucschandle.py:639`) sets `status = "deleted"` and detaches the MO from its
parent (`:661-662`) so a subsequent `to_xml` on the parent will not re-emit it. The commit
path is otherwise identical — deletion travels as a `status` attribute inside
`ConfigConfMos`, not as a separate method.

---

## Both paths, side by side

| | Read | Write |
|---|---|---|
| Entry | `query_dn` `ucschandle.py:312` | `add_mo` `:585` → `commit` `:666` |
| Builder | `config_resolve_dn` `:912` | `config_conf_mos` `:389` |
| Wire method | `<configResolveDn>` | `<configConfMos>` |
| Buffered? | no, immediate | yes, until `commit()` |
| Server errors | raise `UcscException` | raise `UcscException`, **buffer discarded** |
| Result | MO / list / dict | `None`; MOs mutated in place by `sync_mo` |

## Common errors

**`UcscException: [ErrorCode]: 103 …`** — the server rejected the request. Read
`e.error_code` and `e.error_descr`; both are properties on the exception
(`ucscexception.py:90-98`). Note `UcscException` never calls `super().__init__()`, so
`e.args` is empty — use `str(e)` or the two properties.

**Commit does nothing, no error** — the buffer was empty (`ucschandle.py:691`). Under
threading mode, check you are committing from the same thread that staged, since the tag
defaults to the thread name.

**Changes vanish after a failed commit** — by design (`ucschandle.py:715`).

**`AttributeError: 'LsServer' object has no attribute 'children'`** — you called
`mo.show_tree()`. That method is broken; the attribute is `child`.

**`TypeError: LsServer.__init__() missing 1 required positional argument: 'name'`** —
naming properties are positional and required.

**`ValueError: <prop> is not a read-write property.`** — the property's access level is
`READ_ONLY`. Check with
`ucsccoreutils.get_mo_property_meta("LsServer", "oper_state").access`.
