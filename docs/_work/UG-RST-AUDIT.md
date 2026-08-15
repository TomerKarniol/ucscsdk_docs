# Audit of `ucscsdk/docs/ucscsdk_ug.rst`

The 932-line user guide shipped with the SDK is the only pre-existing prose. It is mined and
superseded by `docs/guides/`. Every defect below was verified against the source; each is
corrected explicitly in the guide named in the last column.

`rst:NN` is the line number in `ucscsdk/docs/ucscsdk_ug.rst`.

## API names that do not exist

| rst | Claims | Reality | Corrected in |
|---|---|---|---|
| 324 | "Delete an object - `delete_mo`" | The method is **`remove_mo`**. `delete_mo` is not defined anywhere. | [06](../guides/06-create-modify-delete.md) |
| 327 | "`commit_mo` commits the changes" | The method is **`commit`**. `commit_mo` does not exist. | [06](../guides/06-create-modify-delete.md) |
| 700 | `from ucscsdk.utils.ucscbackup import ... export_config` | No `export_config`. Only `export_config_local`, `export_config_remote`, `export_config_domain_remote`. The import raises `ImportError`. | [10](../guides/10-backup-export-import.md) |

## Wrong call signatures

| rst | Claims | Reality | Corrected in |
|---|---|---|---|
| 371 | `handle.query_dn("org-root/ls-sp_demo", "org-root")` for multiple DNs | That is `query_dns` and it takes a **list**: `query_dns(["a", "b"])`. As written the second string binds to `hierarchy`. | [04](../guides/04-querying.md) |
| 388 | `handle.query_classid("orgOrg", "fabricVlan")` for multiple class ids | That is `query_classids(["orgOrg", "fabricVlan"])`. As written `"fabricVlan"` binds to `filter_str` and fails to parse. | [04](../guides/04-querying.md) |
| 406 | Filters may be passed to `query_dn`, `query_dns`, `query_classid`, `query_classids` | Only **`query_classid`** and **`query_children`** have a `filter_str` parameter. The other three do not accept one. `query_children` is not mentioned at all. | [04](../guides/04-querying.md), [05](../guides/05-filters.md) |

## Broken code blocks

| rst | Problem |
|---|---|
| 676, 708 | `password='password'))` — unbalanced parenthesis; the block is not valid Python. |
| 699-700 | Imports `export_config` (does not exist) while using `export_config_domain_remote` (never imported). |
| 736-737 | Literal `\n` inside the code block: `file_dir = "/home/user/backup"\n`. |
| 742-743 | Dangling `file_dir=file_dir` on its own line after `merge=True)` — leftover from an edit. |
| 782 | `get_domain_tech_support(handle, domain_ip = '192.168.1.1'` — missing comma before the next argument. |

## Python 2 only

| rst | Code |
|---|---|
| 528 | `print class_meta` |
| 643 | `print mo_change_event.mo` |

The SDK itself is Python 3 compatible; only these examples are not. Do not carry them
forward.

## Stale or misleading, though not strictly wrong

- **rst:311-313, 353-354, 390-400, 472-473, 491-492, 684-685, 716-717, 751-752, 801-802,
  831-832** — every "API Reference" link points at `ciscoucs.github.io/ucscsdk_docs/…`.
  These are external and unverifiable from here; several use inconsistent casing
  (`Ucschandle` vs `UcscHandle`) that suggests they were hand-edited. The new docs link
  internally instead.
- **rst:425** — correctly states that `re` is the default filter type. Worth noting because
  it is the single most surprising behaviour and everything else about filters is
  undocumented; the new [05](../guides/05-filters.md) documents the whole grammar.
- **rst:443** — describes the example filter as checking
  `(name == "demo") or (name == *demo_1* and name == [0-9]_1)`. Mixing `==` with wildcard
  notation obscures that the second and third terms are wildcard matches, not equality.
- **rst:249-290** — install/uninstall instructions are fine but predate wheels and modern
  packaging guidance.
- **rst:563-617** — the sample `get_meta_info` output is truncated mid-list
  (`properties` shows 2 of many). Useful as shape, not as data.
- **rst:829** — "Domain register and unregister are available only from UCS Central version
  1.5 onwards" is a real constraint and is carried into
  [11](../guides/11-domain-management.md).

## Correct and worth keeping

These parts of the guide hold up and were carried forward:

- The MIT / DN / RN conceptual framing (rst:70-197).
- `add_mo` does not send until `commit()` (rst:350-351, 469-470, 488-489).
- The transaction model and `tag=` for parallel transactions (rst:494-515, 888-909).
- Threading mode using thread names as tags automatically (rst:911-932).
- Backup vs export-config distinction, and that domain backup is remote-only
  (rst:682, 714).
- Domain import only from backups held on UCS Central (rst:754).
- Domain tech support cannot be downloaded via UCS Central (rst:804).
- `wait_for_event` argument list and the advice to set a timeout (rst:625-638).

## Not covered by the old guide at all

The following had no prose anywhere and are new in `docs/guides/`:

- The `filter_str` grammar itself — precedence, quoting, `flag="I"`, and the fact that
  three filter types are unreachable from it.
- `query_children`, `hierarchy=`, `need_response=`.
- `modify_present=`, `commit_buffer_discard`, buffer-keyed-by-DN semantics.
- That a failed `commit()` discards the buffer.
- The exception hierarchy having two unrelated roots.
- `get_auth_token`, proxy support, session refresh mechanics.
- TLS certificates not being verified.
- Every Python-3.11+/3.12+/3.13+ breakage.
- `converttopython`, beyond its existence.
