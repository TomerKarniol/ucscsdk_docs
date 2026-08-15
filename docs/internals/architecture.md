# Architecture

> Every file:line reference points at `ucscsdk/ucscsdk/` in the SDK clone, package
> version 0.9.0.10. All XML in this document was generated offline by running the SDK's
> own encoder; none of it came from a live server.

## One sentence

`ucscsdk` is an XML-over-HTTPS client for **Cisco UCS Central**: Python `ManagedObject`s are
serialized into XML *method* documents, POSTed to `https://<host>:443/xmlIM/<dme>`, and the
XML response is parsed back into `ManagedObject`s.

It is **not** a UCS Manager SDK. That is the separate `ucsmsdk` package. The two have
similar shapes and incompatible class sets — see [Do not conflate with ucsmsdk](#do-not-conflate-with-ucsmsdk).

## The layer cake

```
                      your code
                          │
  ┌───────────────────────▼────────────────────────┐
  │ UcscHandle              ucschandle.py:29       │  public API: query_*, add_mo,
  │   query_dn/query_classid/add_mo/commit/…       │  set_mo, remove_mo, commit
  └───────────────────────┬────────────────────────┘
                          │  builds an ExternalMethod, gets back MOs
  ┌───────────────────────▼────────────────────────┐
  │ ucscmethodfactory.py    122 builder functions  │  config_resolve_dn(...) →
  │   config_resolve_dn:912  config_conf_mos:389   │  xml.etree Element
  └───────────────────────┬────────────────────────┘
                          │  Element
  ┌───────────────────────▼────────────────────────┐
  │ UcscSession.post_elem   ucscsession.py:226     │  tx lock, stale-cookie fixup,
  │   post_xml:188  post:170                       │  dump_xml, encode, decode
  └───────────────────────┬────────────────────────┘
                          │  xml string
  ┌───────────────────────▼────────────────────────┐
  │ ucscxmlcodec.py         to_xml_str:26          │  Element ⇄ str ⇄ objects
  │                         from_xml_str:66        │
  └───────────────────────┬────────────────────────┘
                          │  bytes
  ┌───────────────────────▼────────────────────────┐
  │ UcscDriver.post         ucscdriver.py:233      │  urllib opener, TLS, proxy,
  │                                                │  redirect, retry-on-SSL
  └───────────────────────┬────────────────────────┘
                          │  HTTPS
                    UCS Central
```

Parsing back up the stack is driven by metadata:

```
  response xml str
      │  ucscxmlcodec.from_xml_str:66
      ▼
  ucsccoreutils.get_ucsc_obj:35 ──► ExternalMethod   (class_id in METHOD_CLASS_ID)
                               ├──► ManagedObject    (class_id in MO_CLASS_ID)
                               ├──► ucscbasetype.*   (class_id in OTHER_TYPE_CLASS_ID)
                               └──► GenericMo        (anything else — forward compat)
      │
      ▼  <obj>.from_xml(elem, handle)   ucscmethod.py:123 / ucscmo.py:351
  object graph
      │
      ▼  ucsccoreutils.extract_molist_from_method_response:274
  list[ManagedObject]
```

## The five modules that matter

| Module | Role |
|---|---|
| `ucschandle.py` (831) | The only class most users touch. Owns the **commit buffer**. |
| `ucscsession.py` (549) | Cookie, login/refresh/logout, the global transaction lock, `post_elem`. |
| `ucscmo.py` (691) | `ManagedObject` — metadata-driven attribute access, RN/DN, dirty tracking. |
| `ucsccoreutils.py` (692) | Metadata lookups + response→MO conversion. The wire/object bridge. |
| `ucscmethodfactory.py` (1727) | 122 generated builders, one per XML method. |

Everything else is supporting cast: `ucsccore.py` (base classes), `ucscmethod.py`
(`ExternalMethod` envelope), `ucscbasetype.py` (XML wrapper types), `ucscxmlcodec.py`
(93 lines, three functions), `ucscdriver.py` (transport), `ucscfilter*.py` (query filters),
`ucsceventhandler.py` (event channel), `ucscexception.py` (7 exception classes),
`ucscgenutils.py` (name mangling, file transfer, crypto).

The three big generated modules — `ucscmeta.py` (3,876), `ucscconstants.py` (5,590),
`ucscmethodfactory.py` (1,727) — are data, not logic. See
[metadata-system.md](metadata-system.md).

## The MIT: DN and RN

Everything on UCS Central hangs off one tree, the **Management Information Tree**. Each
object has:

- **RN** (relative name) — its name within its parent. Generated from a template in the
  class's `MoMeta`: `LsServer.mo_meta.rn == "ls-[name]"`, so a service profile named
  `test_sp` has RN `ls-test_sp`. Templating happens in `ManagedObject.make_rn`
  (`ucscmo.py:278`).
- **DN** (distinguished name) — the full path: parent DN + `/` + RN. Built in
  `ManagedObject._dn_set` (`ucscmo.py:114`).

```python
from ucscsdk.mometa.ls.LsServer import LsServer

sp = LsServer("org-root", name="test_sp")
sp.rn   # 'ls-test_sp'
sp.dn   # 'org-root/ls-test_sp'
```

The properties named inside `[...]` in the RN template are the **naming properties**, and
they are required positional arguments on the generated `__init__`. Omitting one is a
`TypeError`, not a runtime surprise:

```
>>> LsServer("org-root")
TypeError: LsServer.__init__() missing 1 required positional argument: 'name'
```

If a naming property is set to `None` later, `make_rn` raises
`UcscValidationException` (`ucscmo.py:295`).

## The commit buffer

Writes do not go to the server when you call them. `add_mo`/`set_mo`/`remove_mo` only set
`mo.status` and drop the MO into a dict keyed by DN; `commit()` is what talks to the server.

| Call | Sets `mo.status` to | Source |
|---|---|---|
| `add_mo(mo)` | `"created"` | `ucschandle.py:610` |
| `add_mo(mo, modify_present=True)` | `"created,modified"` | `ucschandle.py:608` |
| `set_mo(mo)` | `"modified"` | `ucschandle.py:636` |
| `remove_mo(mo)` | `"deleted"` (and detaches from parent) | `ucschandle.py:660` |

There are **two** buffers (`ucschandle.py:49`):

- `__commit_buf` — the default, one per handle.
- `__commit_buf_tagged` — a dict of `tag -> {dn: mo}`, so independent transactions can be
  built in parallel on one handle.

`tag=` selects between them (`_get_commit_buf`, `ucschandle.py:554`). When threading mode
is on, `_auto_set_tag_context` (`ucschandle.py:569`) silently substitutes the current
thread's name as the tag, giving each thread its own buffer.

Full write trace in [request-lifecycle.md](request-lifecycle.md#write-path).

## Threading: what is and is not parallel

`set_mode_threading()` gives each thread a **separate commit buffer**. It does *not* give
you parallel requests.

`ucscsession.py:25` defines a **module-level** lock:

```python
tx_lock = threading.Lock()
```

`post_elem` acquires it around every request except `aaaLogout`
(`_tx_lock_acquire_conditional`, `ucscsession.py:272`). It is global to the process, so it
serializes traffic across *every* handle in your program, not just one. Threading mode buys
you independent transaction *staging*; the wire is still one-at-a-time.

## Forward compatibility

The SDK is designed to keep working against a UCS Central newer than itself:

- Unknown **class ids** become `GenericMo` instead of raising (`ucsccoreutils.py:84-98`).
- Unknown **properties** on a known class are stored in `__xtra_props` and still serialized
  back out (`ucscmo.py:148-157`, `ucscmo.py:329-343`), so a round-trip does not silently
  drop fields the server understands and the SDK does not.

## Security: TLS is not verified

`UcscDriver` builds its SSL context at `ucscdriver.py:83`:

```python
ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
ssl_context.options |= ssl.OP_NO_SSLv2
ssl_context.options |= ssl.OP_NO_SSLv3
...
self.sock = ssl_context.wrap_socket(sock)
```

No CA bundle is loaded, `check_hostname` is left at its default `False`, and `verify_mode`
stays `CERT_NONE`. **The server's certificate is not validated and the hostname is not
checked.** Traffic is encrypted but not authenticated — it is exposed to an active
man-in-the-middle. There is no SDK option to turn verification on; changing it means
patching `ucscdriver.py`. Treat UCS Central connections as trusted-network-only.

### Response parsing uses the stdlib XML parser

`ucscxmlcodec.from_xml_str` (`ucscxmlcodec.py:84`) calls
`xml.etree.cElementTree.fromstring` on whatever the server returned. Measured on CPython
3.12:

- **External entities are blocked.** `<!ENTITY e SYSTEM "file:///etc/passwd">` fails with
  `ParseError: undefined entity`. Classic XXE file disclosure does not apply.
- **Internal entity expansion is performed.** A response declaring nested internal entities
  is expanded, so a hostile document can cost far more memory than its byte size — a
  billion-laughs-shaped denial of service against the client process.

That requires a malicious or impersonated UCS Central. Since certificates are not verified
(above), an active man-in-the-middle can be that server. The two findings compound: without
TLS verification, "trust the server's XML" is trust in whoever is on the path. On an
untrusted network, neither the transport nor the parser is defending you.

Related: `port` must be 443. `UcscSession.__create_uri` (`ucscsession.py:117`) raises
`UcscLoginError` for anything else, **at construction time**:

```
>>> UcscHandle("1.2.3.4", "admin", "pw", port=100)
UcscLoginError: Can not login to UcsCentral with port other than '443'
```

The `port=100` example in `UcscHandle`'s own docstring (`ucschandle.py:44`) is therefore
wrong — it cannot work.

## Python version reality

The SDK is 2.6/2.7/3.x-era code. On modern Python some of it is dead. Verified under
CPython 3.12.3:

| Symbol | State | Cause |
|---|---|---|
| `ucsccoreutils.load_mo` (`ucsccoreutils.py:157`) | **broken, 3.11+** | `inspect.getargspec`, removed in 3.11 |
| `GenericMo.to_mo` (`ucscmo.py:649`) | **broken, 3.11+** | same, via `__get_mo_obj` (`ucscmo.py:621`) |
| `ManagedObject.show_tree` (`ucscmo.py:411`) | **broken, always** | uses `self.children`; the attribute is `child` |
| `ucsccoreutils.write_mo_tree` (`ucsccoreutils.py:325`) | **broken, always** | uses `mo.class_id`; the accessor is `get_class_id()` |
| `extract_mo_tree_from_config_method_response` (`ucsccoreutils.py:401`) | **broken, always** | calls `write_mo_tree` |
| `UcscHandle.is_local_download_supported` (`ucschandle.py:811`) | **broken, 3.13+** | `distutils`, removed in 3.13 |
| `TLS1Connection.connect` (`ucscdriver.py:112`) | **broken, 3.12+** | `ssl.wrap_socket`, removed in 3.12 |

`TLS1Connection` is only the fallback path taken after an SSL error
(`ucscdriver.py:261-267`), so the primary connection still works; the *retry* is what dies.

`get_ucsc_obj` branches on `sys.version_info` and uses `getfullargspec`
(`ucsccoreutils.py:58-63`), which is why parsing responses works while `load_mo` does not —
the same fix was never applied to the second call site.

Two more that work but warn: `threading.Timer.setDaemon` (`ucscsession.py:371`) and
`log.warn` (`ucscexception.py:32`) are deprecated aliases.

## Do not conflate with ucsmsdk

`ucsmsdk` is the UCS **Manager** SDK. Its examples do not transfer. Concretely:

- There is no `handle.lookup_by_dn`. It appears four times in this SDK's own docstring for
  `query_dn` (`ucschandle.py:332-337`) and **nowhere in the source** — a `ucsmsdk`-ism that
  leaked into a comment. The method is `query_dn`.
- `dme="central-mgr"` is a UCS Central concept; it selects the endpoint path segment in
  `post_xml` (`ucscsession.py:202`).
- Class sets differ. Check membership against `ucscmeta.MO_CLASS_ID` before believing any
  class name you did not read out of this package.

## Known incorrect docstrings in the source

Carried here so you do not trust them:

| Location | Problem |
|---|---|
| `ucschandle.py:44` | `port=100` example raises `UcscLoginError` |
| `ucschandle.py:332-337` | calls `handle.lookup_by_dn`, which does not exist |
| `ucsccoreutils.py:447-448` | `print_mo_hierarchy` example shows `write_mo_tree` on a response |
| `ucscfilter.py:172` | `generate_infilter` example has unbalanced quotes and will not parse |
| `ucscsession.py:342-347` | `file_upload` example names `source_dir`; the parameter is `file_dir` |

## Where to go next

- [request-lifecycle.md](request-lifecycle.md) — both paths traced end to end with real XML.
- [metadata-system.md](metadata-system.md) — how `MoMeta`/`MoPropertyMeta` drive all of it.
