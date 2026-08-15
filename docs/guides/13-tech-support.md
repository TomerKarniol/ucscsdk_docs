# 13. Tech support bundles

> Every example needs a live server. Signatures verified by introspection.

```python
from ucscsdk.utils.ucsctechsupport import get_tech_support

get_tech_support(handle, file_dir="/home/user/ts",
                 file_name="techsupport.tar")
```

## UCS Central tech support

```python
get_tech_support(handle, file_dir=None, file_name=None,
                 remove_from_ucsc=False, download=True, timeout=1200)
```

Creates the bundle on UCS Central, waits for it, and downloads it.

```python
get_tech_support(handle, file_dir="/home/user/ts",
                 file_name="ucsc-techsupport.tar",
                 remove_from_ucsc=True, timeout=1800)
```

`remove_from_ucsc=True` deletes the bundle from UCS Central after download — worth using,
since these are large and accumulate.

`download=False` creates the bundle without transferring it, for when you only want it to
exist server-side.

Collection is slow. The default `timeout=1200` (20 minutes) is not always enough on a busy
system.

## UCS domain tech support

```python
get_domain_tech_support(handle, domain_ip, domain_name=None,
                        option='ucsm', timeout=1200, **kwargs)
```

`option` selects what to collect, and **each option requires its own `kwargs`**:

| `option` | Required | Optional |
|---|---|---|
| `ucsm` | — | — |
| `ucsm-mgmt` | — | — |
| `chassis` | `chassis_id` | `cimc_id`, `iom_id`, `adapter_id`, `cartridge_id`, `cartridge_cimc_id` |
| `rack-server` | `rack_server_id` | `rack_adapter_id` |
| `fabric-extender` | `fex_id` | — |
| `server-memory` | `server_id_list` | — |

Two names catch people out: the fabric-extender option is **`fabric-extender`**, not `fex`
(though its argument is `fex_id`), and server-memory takes **`server_id_list`**, not
`server_memory_id`. Anything else raises:

```
UcscValidationException: Unrecognised option value: <option>
```

```python
get_domain_tech_support(handle, domain_ip="192.168.1.1",
                        option="ucsm-mgmt", timeout=1800)

get_domain_tech_support(handle, domain_ip="192.168.1.1",
                        option="chassis",
                        file_dir="/home/user/ts",
                        file_name="chassis-ts.tar",
                        chassis_id=1, cimc_id=1, adapter_id=1)

get_domain_tech_support(handle, domain_ip="192.168.1.1",
                        option="rack-server",
                        timeout=1800,
                        rack_server_id=1, rack_adapter_id="all")
```

Because the extra arguments arrive through `**kwargs`, **a misspelled one is silently
ignored** rather than raising — you get a bundle for the wrong scope, or a validation error
from the server. Check the spelling against the table.

Pass the component arguments **last**, after the named parameters.

### Downloading domain bundles

Domain tech support bundles are collected onto UCS Central but **cannot be downloaded
through it**. Retrieve them from the domain's UCS Manager directly. Setting `file_dir` and
`file_name` on a domain call does not change that.

## Lower-level pieces

For custom flows the individual steps are exposed:

```python
from ucscsdk.utils.ucsctechsupport import (poll_wait_for_tech_support,
                                           download_tech_support)

poll_wait_for_tech_support(handle, ts_mo, timeout)
download_tech_support(handle, name, file_dir, file_name)
```

`poll_wait_for_tech_support` blocks until the bundle is ready or the timeout expires.
`download_tech_support` fetches an existing one by name. You would only reach for these to
build something the wrappers do not cover.

## A realistic collection script

```python
import os
from ucscsdk.utils.ucsctechsupport import get_tech_support
from ucscsdk.ucscexception import UcscOperationError

out = "/var/tmp/ucsc-ts"
os.makedirs(out, exist_ok=True)

try:
    get_tech_support(handle,
                     file_dir=out,
                     file_name="ucsc-techsupport.tar",
                     remove_from_ucsc=True,
                     timeout=3600)
except UcscOperationError as e:
    raise SystemExit("tech support failed: %s" % e)
```

An hour-long timeout and `remove_from_ucsc=True` are the settings that avoid the two usual
failure modes.

## Disk space

Bundles are large — hundreds of megabytes is normal. They are written to `file_dir` on your
machine, and are also held on UCS Central until removed. Running out of space on either side
fails the operation partway.

## Common errors

**Timeout** — the default is 1200 seconds. Collection on a busy system takes longer; raise
`timeout`.

**`UcscOperationError: ... failed, error: ...`** — collection was rejected or failed. The
message carries the reason.

**Domain bundle never appears locally** — expected. Domain tech support cannot be downloaded
through UCS Central; get it from that domain's UCS Manager.

**Wrong scope collected** — a misspelled `**kwargs` name was ignored silently. Check against
the option table.

**Missing required component argument** — `option="chassis"` without `chassis_id`, and so
on. The validation happens inside the helper and surfaces as an operation error.

**`UcscValidationException: Unrecognised option value: fex`** — the option is
`fabric-extender`. Only the six names in the table are accepted.

**Disk full mid-download** — check space in `file_dir` before starting.

**UCS Central runs out of space over time** — old bundles accumulate. Use
`remove_from_ucsc=True`.
