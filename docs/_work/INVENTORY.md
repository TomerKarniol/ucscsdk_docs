# `ucscsdk` — Mechanical Inventory (Phase 0)

Package version **0.9.0.10**. Cisco UCS **Central** Python SDK (Apache-2.0).
Source of truth: `/home/tomer/code/ucscsdk_docs/ucscsdk/ucscsdk/` (untracked clone; read-only).

All counts below were produced mechanically (`find`, `wc -l`, `grep`, `ast`, runtime
introspection) on the working tree, not copied from the brief.

## 0. Totals

| Thing | Count |
|---|---|
| `.py` files in clone (incl. `tests/`, `setup.py`) | 2,113 |
| Hand-written core modules (`ucscsdk/*.py`) | 19 (17,349 LOC) |
| Hand-written util modules (`ucscsdk/utils/*.py`) | 6 (4,495 LOC, + empty `__init__.py`) |
| Generated MO classes (`ucscsdk/mometa/<pkg>/<Class>.py`) | **1,831** |
| MO packages (`ucscsdk/mometa/*/`) | **94** |
| Generated method-meta modules (`ucscsdk/methodmeta/*Meta.py`) | **122** (+ `__init__.py`) |
| Method-factory functions (`ucscmethodfactory.py`) | **122** |
| Test files (`tests/**/test_*.py`, `tests_*.py`) | 25 across 9 subdirs |

Runtime cross-check (`/usr/bin/python3`):
`len(ucscmeta.MO_CLASS_ID) == 1831`, `len(ucscmeta.MO_CLASS_META) == 1831`,
`len(ucscmeta.METHOD_CLASS_ID) == 122`, `len(ucscmeta.OTHER_TYPE_CLASS_ID) == 26`.
Filesystem MO-file count sums to exactly 1831. The maps and the tree agree.

## 1. Core modules — `ucscsdk/*.py`

Ordered by role, not by size. LOC from `wc -l`.

### 1.1 Entry points

**`__init__.py`** — 51 LOC — *Package init: logging setup + version.*
Public: `set_log_level(level=logging.DEBUG)`, `__version__ = "0.9.0.10"`, module-level
`log`, `console`, `formatter`.

**`ucschandle.py`** — 831 LOC — *`UcscHandle`, the entire public API surface. Everything a
user calls lives here.*
Public: `class UcscHandle(UcscSession)` with
`__init__(ip, username, password, port=443, proxy=None)`,
`login(auto_refresh=False, force=False)`, `logout()`,
`get_auth_token()`, `process_xml_elem(elem, dme='central-mgr')`,
`query_dn(dn, hierarchy=False, need_response=False, dme='central-mgr')`,
`query_dns(dns=[], dme='central-mgr')`,
`query_classid(class_id=None, filter_str=None, hierarchy=False, need_response=False, dme='central-mgr')`,
`query_classids(class_ids=[], dme='central-mgr')`,
`query_children(in_mo=None, in_dn=None, class_id=None, filter_str=None, hierarchy=False, dme='central-mgr')`,
`add_mo(mo, modify_present=False, tag=None)`, `set_mo(mo, tag=None)`, `remove_mo(mo, tag=None)`,
`commit(tag=None, dme='central-mgr')`, `commit_buffer_discard(tag=None)`,
`wait_for_event(mo, prop, value, cb, timeout=None, poll_sec=None)`,
`set_dump_xml()`, `unset_dump_xml()`, `set_mode_threading()`, `unset_mode_threading()`,
`is_threading_enabled()`, `get_firmware_version()`, `is_local_download_supported()`.
Internal: `_get_commit_buf(tag)`, `_update_commit_buf(mo, tag)`, `_auto_set_tag_context(tag)`.

**`ucscsession.py`** — 549 LOC — *Session/cookie/auth state and the transport-facing
`post_*` layer that `UcscHandle` inherits.*
Public: `class UcscSession` — properties `ip`, `username`, `proxy`, `uri`, `ucs`, `cookie`,
`session_id`, `version`, `refresh_period`, `priv`, `domains`, `channel`, `evt_channel`,
`last_update_time`; methods `post(uri, data=None, read=True)`,
`post_xml(xml_str, read=True, dme='central-mgr')`, `post_elem(elem, dme='central-mgr')`,
`dump_xml_request(elem)`, `dump_xml_response(resp)`,
`file_download(url_suffix, file_dir, file_name, ...)`, `file_upload(...)`.
Internal: `_login`, `_logout`, `_refresh`, `_update_cookie`, `_is_stale_cookie`,
`_set_dump_xml`, `_unset_dump_xml`, `_tx_lock_acquire_conditional`,
`_tx_lock_release_conditional`, `__create_uri`, `__clear`, `__update`,
`__start_refresh_timer`, `__stop_refresh_timer`, `__validate_connection`.

### 1.2 Object model

**`ucsccore.py`** — 204 LOC — *Root base classes for everything serializable.*
Public: `class UcscBase` (child list, dirty-mask, `to_xml`/`clone`/`elem_create`,
`attr_set`/`attr_get`, `child_add`/`child_remove`/`child_count`, `mark_clean`, `is_dirty`,
`write_object`), `class AbstractFilter(UcscBase)`, `class BaseObject(UcscBase)`.

**`ucscmo.py`** — 691 LOC — *`ManagedObject` (the metadata-driven MO) and `GenericMo`
(the schema-less escape hatch).*
Public: `class ManagedObject(UcscBase)` — `__init__(class_id, parent_mo_or_dn=None, **kwargs)`,
props `parent_mo`, methods `check_prop_match(**kwargs)`, `set_prop_multiple(**kwargs)`,
`mark_dirty()`, `is_dirty()`, `make_rn()`, `rn_is_special_case()`, `rn_get_special_case()`,
`to_xml()`, `from_xml()`, `sync_mo(mo)`, `show_tree(level=0)`,
`show_hierarchy(level=0, depth=None, show_level=[])`;
`class GenericMo(UcscBase)` — `properties`, `to_xml`, `from_xml`, `to_mo()`;
module functions `generic_mo_from_xml(xml_str)`, `generic_mo_from_xml_elem(elem)`.
Internal: `_GenericProp`, `__set_prop`, `__get_prop`, `_rn_set`, `_dn_set`.

**`ucscbasetype.py`** — 145 LOC — *Generated XML wrapper types used inside method payloads.*
Public: `Method`, `MethodSet`, `ClassId`, `ClassIdSet`, `ConfigConfig`, `ConfigMap`,
`ConfigSet`, `Dn`, `DnSet`, `FilterFilter`, `Id`, `IdSet`, `Pair` — all `BaseObject`
subclasses taking `**kwargs`.

**`ucscmethod.py`** — 175 LOC — *`ExternalMethod`: the request/response envelope object.*
Public: `class ExternalMethod(UcscBase)` — `__init__(method_id)`, `child_add(mo)`,
`set_attr(key, value)`, `get_error_response(error_code, error_descr)`, `to_xml()`, `from_xml()`.

### 1.3 Metadata

**`ucsccoremeta.py`** — 617 LOC — *The metadata vocabulary. Read this before anything else
in Phase 2.*
Public: `class WriteXmlOption` (Dirty/All/AllConfig constants),
`class UcscVersion` (parses `"2.0(1a)"`; `major/minor/mr/patch/spin/build/version`,
full rich comparison), `class MoPropertyRestriction`
(`min_length`, `max_length`, `pattern`, `range_val`, `value_set`, `range_roc`, `value_set_roc`),
`class MoPropertyMeta` (`name`, `xml_attribute`, `field_type`, `version`, `access`, `mask`,
`restriction`, `validate_property_value(input_value)`),
`class MoMeta` (`name`, `xml_attribute`, `rn`, `version`, `inp_out`, `mask`, `field_names`,
`access`, `children`, `parents`, `verbs`),
`class MethodPropertyMeta`, `class MethodMeta`.

**`ucscmeta.py`** — 3,876 LOC — *Generated. The global registry.*
Public: `class VersionMeta` (**32** `UcscVersion` constants, `Version101a` … latest),
`MO_CLASS_ID` (frozenset, 1831 class ids), `METHOD_CLASS_ID` (frozenset, 122),
`MO_CLASS_META` (dict `class_id -> MoMeta`, 1831),
`OTHER_TYPE_CLASS_ID` (dict `class_id -> module_name`, 26 — maps `ucscbasetype`/filter types).

**`ucscconstants.py`** — 5,590 LOC — *Generated. Four constant namespaces only.*
Public: `class NamingId` (l.16 — UPPER_SNAKE → `"camelCaseClassId"`, ~1,950 entries),
`class YesOrNo` (l.1997), `class NamingPropertyId` (l.2003), `class Status` (l.5585).

**`ucsccoreutils.py`** — 692 LOC — *Metadata lookup + response→MO conversion. The bridge
between the XML wire and the object model.*
Public: `get_ucsc_obj(class_id, elem, mo_obj=None)`, `load_module(module_name)`,
`load_class(class_id)`, `load_mo(elem)`, `is_valid_class_id(class_id)`,
`find_class_id_in_mo_meta_ignore_case(class_id)`,
`find_class_id_in_method_meta_ignore_case(class_id)`,
`get_mo_property_meta(class_id, key)`, `write_object(mo_or_list)`,
`extract_molist_from_method_response(method_response, ...)`,
`write_mo_tree(mo, level=0, depth=None, show_level=[], ...)`,
`extract_mo_tree_from_config_method_response(method_response, ...)`,
`print_mo_hierarchy(class_id, level=0, depth=None, show_level=[])`,
`get_naming_props(rn_str, rn_pattern)`, `class ClassIdMeta`, `search_class_id(class_id)`,
`get_meta_info(class_id, include_prop=True, ...)`.
Internal: `_show_tree`.

### 1.4 Transport & codec

**`ucscdriver.py`** — 288 LOC — *HTTP(S) transport. The only module needing `six`.*
Public: `class UcscDriver` — `__init__(proxy=None)`, `update_handlers(tls_proto=None)`,
`add_header(header_prop, header_value)`, `remove_header(header_prop)`, `redirect_uri`,
`get(uri)`, `post(uri, data=None, dump_xml=False, read=True, timeout=None)`.
Support: `SmartRedirectHandler`, `TLSHandler`/`TLSConnection`, `TLS1Handler`/`TLS1Connection`.

**`ucscxmlcodec.py`** — 93 LOC — *XML ⇄ object. Three functions, the whole codec.*
Public: `to_xml_str(elem)`, `extract_root_elem(xml_str)`, `from_xml_str(xml_str, handle=None)`.

### 1.5 Filters

**`ucscfilter.py`** — 240 LOC — *The `filter_str` mini-language. The only module needing
`pyparsing`.*
Public: `class ParseFilter(object)` — `__init__(class_id, is_meta_classid)`,
`parse_filter_obj(toks)`, `and_operator(toks)`, `or_operator(toks)`, `not_operator(toks)`,
`parse_filter_str(filter_str)`;
`generate_infilter(class_id, filter_str, is_meta_class_id)`,
`handle_filter_max_component_limit(handle, l_filter)` **(undocumented in the brief)**,
`create_basic_filter(filter_name, **kwargs)`.

**`ucscfiltertype.py`** — 203 LOC — *Generated. 13 filter classes, all `AbstractFilter`
subclasses with `create(**kwargs)`.*
Public (note the `…Filter` suffix — the brief omitted it):
`AllbitsFilter`, `AndFilter`, `AnybitFilter`, `BwFilter`, `EqFilter`, `GeFilter`,
`GtFilter`, `LeFilter`, `LtFilter`, `NeFilter`, `NotFilter`, `OrFilter`, `WcardFilter`.

### 1.6 Events

**`ucsceventhandler.py`** — 676 LOC — *Event channel: enqueue thread, dequeue thread,
watch blocks.*
Public: `class MoChangeEvent(event_id=None, mo=None, change_list=None)`,
`class WatchBlock(params, fmce, capacity, callback)` — `dequeue(miliseconds_timeout)`,
`enqueue(cmce)`, `queue_size()`;
`class UcscEventHandle(handle)` — `watch_block_add(params, ...)`,
`watch_block_remove(watch_block)`, `add(...)`, `remove(watch_block)`, `clean()`, `get()`;
module function `wait(handle, mo, prop, value, cb, timeout_sec=None, poll_sec=None)`
(this is what `UcscHandle.wait_for_event` delegates to);
`dequeue_default_callback(mce)`.

### 1.7 Errors

**`ucscexception.py`** — 119 LOC — *Two roots: `UcscWrapperException` (client-side) and
`UcscError` (server/validation).*
Public: `UcscWarning(warn_str)`;
`class UcscWrapperException(Exception)` → `UcscLoginError(message, error_code=None)`,
`UcscConnectionError(message)`, `UcscOperationError(operation, error)`;
`class UcscError(Exception)` → `UcscException(error_code, error_descr)` (props `error_code`,
`error_descr`), `UcscValidationException(error_msg)` (prop `error_msg`).

### 1.8 Misc utilities

**`ucscgenutils.py`** — 582 LOC — *Name mangling, file transfer, crypto, java/md5 helpers.*
Public: `is_python_reserved(word)`, `to_safe_prop(word)`, `from_safe_prop(word)`,
`to_python_propname(word)`, `convert_to_python_var_name(name)`, `word_l(word)`, `word_u(word)`,
`make_dn(rn_array)`, `class FileReadStream`, `class Progress(interval=1)`,
`download_file(driver, file_url, file_dir, file_name, progress=Progress())`,
`random_string(length)`, `encode_multipart_data(file_dir, file_name, progress=Progress())`,
`upload_file(driver, uri, file_dir, file_name, progress=Progress())`,
`check_registry_key(java_key)`, `is_binary_in_path(path, binary)`, `get_binary_path(binary)`,
`get_java_installation_path()`, `check_output(*popenargs, **kwargs)`, `get_java_version()`,
`get_md5_sum(filename)`, `get_sha_hash(input_string)`, `expand_key(key, clen)`,
`encrypt_password(password, key)`, `decrypt_password(cipher, key)`, `iteritems(d)`.

**`ucscmethodfactory.py`** — 1,727 LOC — *Generated. 122 `ExternalMethod` builders, one per
XML method. Naming: `config_resolve_dn` → `ConfigResolveDn` → `<configResolveDn/>`.*
Grouped by prefix: `aaa_*` (14), `cliview_*` (1), `compute_*` (3), `config_*` (49),
`equipment_*` (5), `event_*` (3), `fabric_*` (3), `fault_*` (5), `firmware_*` (2), `fsm_*` (1),
`ident_*` (3), `logging_*` (1), `ls_*` (5), `lstorage_*` (1), `method_vessel` (1), `org_*` (7),
`policy_*` (1), `pool_*` (1), `snmp_*` (1), `stats_*` (5), `synthetic_*` (3).
Hot ones for docs: `config_resolve_dn`, `config_resolve_dns`, `config_resolve_class`,
`config_resolve_classes`, `config_resolve_children`, `config_conf_mo`, `config_conf_mos`,
`config_conf_mo_group`, `config_conf_filtered`, `config_delete_mo`, `config_scope`,
`aaa_login`, `aaa_logout`, `aaa_refresh`, `aaa_get_auth_token_client`,
`event_subscribe`, `config_mo_change_event`.

## 2. Generated MO tree — `ucscsdk/mometa/`

94 packages, 1,831 classes. Each file defines one `class <Pkg><Name>(ManagedObject)` with a
module-level `<Class>Consts` class and a `MoMeta`/`MoPropertyMeta` block.
`__init__(parent_mo_or_dn, <naming props…>, **kwargs)`.

MO count per package (descending):

```
fabric 183   equipment 112   adaptor 108   bios 105   compute 105   storage  98
policy  74   vnic   74   gl     70   config 67   aaa    55   firmware 53
mgmt    50   comm   39   lsboot 32   lstorage 32   sysdebug 30   hc     24
license 22   ls     21   stats  21   domain 19   extpol 19   smartlicense 18
memory  17   ether  15   ident  15   callhome 14   org    14   fault  12
dupe    11   nfs    11   diag   10   fd     10   power  10   identpool 9
initiator 9  processor 9   testing 9   trig    9   fcpool  8   ippool  8
tag      8   iqnpool 7   event   7   pki     7   proc    7   smartcallhome 7
top      7   cimcvmedia 6   feature 6   macpool 6   network 6   observe 6
sw       6   uuidpool 6   change  5   consumer 5   extmgmt 5   inventory 5
os       5   query   5   qosclass 5   synthetic 5   sysfile 5   version 5
fc       5   cert    4   controller 4   queryresult 4   clitest 3   gmeta  3
ip       3   cpmaint 2   dcx     2   epqos   2   extvmm  2   flowctrl 2
graphics 2   gui     2   lsmaint 2   message 2   port    2   ses     2
capability 1 dpsec   1   fsm     1   inband  1   iscsi   1   net     1
nwctrl   1   security 1   sol     1   vm      1
```

Docs-relevant packages: `org`, `ls` (service profiles), `compute`, `fabric`, `vnic`,
`lstorage`, `aaa`, `firmware`, `policy`, `domain`, `extpol` (domain registration), `mgmt`.

## 3. Generated method-meta — `ucscsdk/methodmeta/`

122 `<Method>Meta.py` files. Each defines:
- `method_meta = MethodMeta("ConfigResolveDn", "configResolveDn", "Version142b")`
- `prop_meta = {python_name: MethodPropertyMeta(Name, xmlAttr, field_type, version, "Input"|"Output"|"InputOutput", is_complex)}`
- `prop_map = {xmlAttr: python_name}`

One `Meta.py` per `METHOD_CLASS_ID` entry — 122 = 122, exact.

## 4. `tests/` — verified-usage source

9 subdirs, 26 test modules. `tests/connection/` holds the live-connection fixture
(`connection.cfg`, `info.py`) — everything importing it needs hardware.

**The suite is not runnable**: 24 of 26 modules `import nose`, which is uninstallable on
Python 3.12. `pytest tests -q --collect-only` → `2 tests collected, 22 errors`. Read these
files as verified usage intent, never as an executable oracle. Full split in `NOTES.md`.

```
tests/common/         13 files  offline unit tests: filters, xml round-trip, MO, versions,
                                special RNs, prop validation, unknown props, query_children
tests/connection/      2 files  live-handle fixture (connection.cfg + info.py)
tests/convert_to_ucs/  1 file   converttopython round-trip
tests/coreutils/       1 file   get_meta_info
tests/generic_mo/      1 file   GenericMo
tests/policy/          1 file   policy CRUD
tests/sp/              1 file   service-profile CRUD
tests/utils/           5 files  backup, domain, eventhandler, firmware, techsupport
tests/vlan/            1 file   vlan CRUD
```

## 5. Existing prose

`ucscsdk/docs/ucscsdk_ug.rst` — 932 lines, the only prose in the repo. Sections: Overview ·
Management Information Model (Managed Objects / References / Properties / Methods) ·
Installation · Uninstallation · Getting Started (Connecting · Base APIs · Creating ·
Querying · Querying With Filters · Modifying · Deleting · Transaction) · Retrieving Meta
Information · Watch UCS Central Events · Backup And Import · Technical Support ·
Domain Management. To be mined, corrected, and superseded — not reformatted.
