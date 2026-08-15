# 10. Backup, export and import

> Every example needs a live server. All signatures below were verified by introspection.

```python
from ucscsdk.utils.ucscbackup import backup_local

backup_local(handle, file_dir="/home/user/backup",
             file_name="full-state_backup.tgz")
```

## Two kinds of backup

| Kind | Contents | Functions |
|---|---|---|
| **full-state** | complete binary snapshot, for disaster recovery | `backup_*` |
| **config-all** | logical configuration, importable and mergeable | `export_config_*` |

Full-state restores UCS Central to exactly where it was. Config export is what you use to
move configuration between systems.

## Backing up UCS Central

```python
from ucscsdk.utils.ucscbackup import backup_local, backup_remote

backup_local(handle, file_dir="/home/user/backup",
             file_name="full-state.tgz")

backup_remote(handle, file_dir="/backups", file_name="full-state.tgz",
              hostname="192.168.1.50", protocol="scp",
              username="admin", password="password")
```

Signatures:

```python
backup_local(handle, file_dir, file_name,
             preserve_pooled_values=False, remove_from_ucsc=False, timeout=600)

backup_remote(handle, file_dir, file_name, hostname, protocol='scp',
              username=None, password='', preserve_pooled_values=False,
              remove_from_ucsc=False, timeout=600)
```

`backup_local` downloads through your handle to your machine; `backup_remote` tells UCS
Central to push the file to another host, so `file_dir` is a path **on that remote host**.

`remove_from_ucsc=True` deletes the backup object from UCS Central afterwards — worth using
so repeated runs do not accumulate.

`preserve_pooled_values=True` keeps assigned pool identities (MACs, WWNs, UUIDs) in the
backup.

## Backing up a UCS domain

```python
from ucscsdk.utils.ucscbackup import backup_domain_remote

backup_domain_remote(handle, file_dir="/backups", file_name="domain.tgz",
                     domain_ip="10.10.10.1", protocol="scp",
                     hostname="192.168.1.50",
                     username="admin", password="password")
```

**Domain backups can only go to a remote host.** There is no `backup_domain_local`.

## Exporting configuration

```python
from ucscsdk.utils.ucscbackup import (export_config_local, export_config_remote,
                                      export_config_domain_remote)

export_config_local(handle, file_dir="/home/user/backup",
                    file_name="config-all.tgz")
```

There is **no** function called `export_config`. The old user guide imports one; that import
fails. The three real names are above.

Watch the argument order if you pass positionally — it differs between the two domain
functions:

```python
backup_domain_remote(handle, file_dir, file_name, domain_ip, protocol, hostname, ...)
export_config_domain_remote(handle, file_dir, file_name, domain_ip, hostname, protocol, ...)
```

`protocol` and `hostname` are swapped. Use keyword arguments and the problem disappears.

## Importing configuration

```python
from ucscsdk.utils.ucscbackup import (import_config_ucscentral,
                                      import_config_local,
                                      import_config_remote,
                                      import_config_domain)

import_config_local(handle, file_dir="/home/user/backup",
                    file_name="config-all.tgz", merge=True)
```

| Function | Source of the file |
|---|---|
| `import_config_ucscentral(handle, file_name, merge=True, timeout=120)` | already on UCS Central |
| `import_config_local(handle, file_dir, file_name, merge=True, timeout=120)` | your machine |
| `import_config_remote(handle, file_dir, file_name, hostname, merge=True, protocol='scp', username=None, password='', timeout=120)` | a remote host |
| `import_config_domain(handle, to_domain_ip, from_domain_ip, config_file, merge=True, ...)` | a domain backup held on UCS Central |

**`merge=True` merges into the existing configuration; `merge=False` replaces it.** The
default is merge. Be deliberate — a replace is destructive and there is no confirmation
prompt.

Domain import only works from backups already on UCS Central:

```python
import_config_domain(handle, to_domain_ip="10.10.10.100",
                     from_domain_ip="192.168.1.1",
                     config_file="all-cfg.1.tgz")
```

Source and target may be the same domain (restore) or different (clone).

## Scheduled backups

```python
from ucscsdk.utils.ucscbackup import (schedule_backup, schedule_export_config,
                                      schedule_backup_domain,
                                      schedule_export_config_domain,
                                      remove_schedule_backup,
                                      remove_schedule_export_config,
                                      remove_schedule_backup_domain,
                                      remove_schedule_export_config_domain)

schedule_backup(handle, remote_enabled=True, protocol="scp",
                hostname="192.168.1.50", file_path="/backups",
                username="admin", password="password",
                max_bkup_files="5")
```

Full signature:

```python
schedule_backup(handle, descr='Database Backup Policy',
                sched_name='global-default', max_bkup_files='2',
                remote_enabled=False, protocol=None, hostname=None,
                file_path=None, username=None, password='')
```

Note `file_path`, not `file_dir` — the scheduling functions use a different parameter name
from the one-shot ones. `max_bkup_files` defaults to the **string** `'2'`; pass a string.

Each `schedule_*` has a matching `remove_schedule_*`:
`remove_schedule_backup(handle)`, `remove_schedule_export_config(handle)`,
`remove_schedule_backup_domain(handle, domain_group='root')`,
`remove_schedule_export_config_domain(handle, domain_group='root')`.

These configure a recurring policy on UCS Central; they do not run a backup now.

## Timeouts

Backups default to `timeout=600` seconds, imports to `120`. Large systems exceed both.
Raise the timeout rather than retrying a half-finished operation:

```python
backup_local(handle, file_dir="/backups", file_name="full.tgz", timeout=3600)
```

The helpers poll UCS Central until the operation reports completion, then download.

## Credentials

Do not hard-code passwords. Read them from the environment or a secret store:

```python
import os
backup_remote(handle, file_dir="/backups", file_name="full.tgz",
              hostname="192.168.1.50", protocol="scp",
              username=os.environ["BACKUP_USER"],
              password=os.environ["BACKUP_PASS"])
```

Remote credentials are sent to UCS Central, which uses them to reach the file server. They
travel over the SDK's unverified TLS connection — see
[03 — connecting and auth](03-connecting-and-auth.md).

## Common errors

**`ImportError: cannot import name 'export_config'`** — no such function. Use
`export_config_local`, `export_config_remote` or `export_config_domain_remote`.

**`UcscOperationError: <operation> failed, error: ...`** — the operation was rejected or
timed out. The message carries the reason.

**Timeout on a large system** — raise `timeout`.

**Backup file not where expected** — for `*_remote`, `file_dir` is on the **remote host**,
not your machine. Only `*_local` writes locally.

**Domain backup fails with no local option** — correct; domain backups are remote-only.

**Import replaced everything** — `merge=False`. The default is `True`; check what you
passed.

**`UcscException` about an existing backup object** — a previous run left one behind. Use
`remove_from_ucsc=True`, or delete it before retrying.

**Repeated runs get slower or fail** — accumulated backup objects on UCS Central. Same fix.
