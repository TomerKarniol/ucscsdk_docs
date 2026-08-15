# 11. Domain management

> Every example needs a live server. Signatures verified by introspection.

```python
from ucscsdk.utils.ucscdomain import domain_register

domain_register(handle, domain_name_or_ip="192.168.1.100",
                username="admin", password="password")
```

## What a domain is

UCS Central manages UCS **domains** — each one a UCS Manager instance with its own fabric
interconnects, chassis and servers. Before you can push global policy at a domain, it has to
be registered.

Domains are organised into **domain groups**, arranged in a tree under `domaingroup-root`.
Policy applies at a group and flows down.

## Register

```python
domain_register(handle, domain_name_or_ip, username, password, timeout=120)
```

```python
domain_register(handle, domain_name_or_ip="192.168.1.100",
                username="admin", password="password")
```

The credentials are the **UCS Manager** admin credentials for that domain, not your UCS
Central ones. Registration is asynchronous; the helper waits up to `timeout` seconds.

Registration requires **UCS Central 1.5 or later**.

## Check before acting

```python
from ucscsdk.utils.ucscdomain import is_domain_registered

if not is_domain_registered(handle, "192.168.1.100"):
    domain_register(handle, domain_name_or_ip="192.168.1.100",
                    username="admin", password="password")
```

Cheaper and clearer than registering and catching the failure.

## Inspect

```python
from ucscsdk.utils.ucscdomain import get_domain, get_domain_operational_status

domain = get_domain(handle, domain_ip="192.168.1.100")
status = get_domain_operational_status(handle, domain_ip="192.168.1.100")
```

Both accept an optional `domain_name=` instead of matching on IP — useful where a domain
was registered by name.

`get_domain` returns the managed object, so you can read its properties directly.

## Unregister

```python
from ucscsdk.utils.ucscdomain import domain_unregister

domain_unregister(handle, domain_name_or_ip="192.168.1.100")
```

The domain keeps running; it stops being centrally managed. Global policies previously
pushed to it remain in place locally.

## Domain groups

```python
from ucscsdk.utils.ucscdomain import (domain_group_create, get_domain_group_dn,
                                      domain_assign_to_domaingroup)

domain_group_create(handle, name="production")
domain_group_create(handle, name="web", parent_dn="domaingroup-root/domaingroup-production")

domain_assign_to_domaingroup(handle, domain_ip="192.168.1.100",
                             domain_group="root/production")
```

Signatures:

```python
domain_group_create(handle, name, descr='', parent_dn='domaingroup-root')
domain_assign_to_domaingroup(handle, domain_ip, domain_group, domain_name=None)
get_domain_group_dn(handle, domain_group)
```

Note the **two different notations**, and they are not interchangeable:

- `parent_dn` takes a real DN: `domaingroup-root/domaingroup-production`.
- `domain_group` takes a slash path rooted at `root`: `root/production`.

`get_domain_group_dn` converts the second form into the first:

```python
get_domain_group_dn(handle, "root/production")
# 'domaingroup-root/domaingroup-production'
```

Use it whenever you need to hand a group to something that wants a DN.

## Working with domains directly

The helpers cover the common cases. For anything else, query the MOs — domain objects live
in the `extpol` and `domain` packages:

```python
domains = handle.query_classid("ExtpolRegistry")
for d in domains:
    print(d.dn, d.name, d.oper_state)
```

See [`reference/mo/extpol.md`](../reference/mo/extpol.md) and
[`reference/mo/domain.md`](../reference/mo/domain.md) for the full class lists.

## A registration workflow

```python
from ucscsdk.utils.ucscdomain import (is_domain_registered, domain_register,
                                      domain_group_create,
                                      domain_assign_to_domaingroup,
                                      get_domain_operational_status)
from ucscsdk.ucscexception import UcscException
import os

ip = "192.168.1.100"

if not is_domain_registered(handle, ip):
    domain_register(handle, domain_name_or_ip=ip,
                    username=os.environ["UCSM_USER"],
                    password=os.environ["UCSM_PASS"],
                    timeout=300)

try:
    domain_group_create(handle, name="production")
except UcscException as e:
    if "already exists" not in str(e).lower():
        raise

domain_assign_to_domaingroup(handle, domain_ip=ip, domain_group="root/production")
print(get_domain_operational_status(handle, domain_ip=ip))
```

## Common errors

**Registration fails on an older UCS Central** — `domain_register` and `domain_unregister`
need version 1.5+. Check with `handle.get_firmware_version()`.

**`UcscOperationError: ... failed, error: ...`** — registration was rejected or timed out.
Usual causes: wrong UCS Manager credentials, the domain is unreachable from UCS Central, or
it is already registered elsewhere.

**Timeout during registration** — the default is 120 seconds and registration can take
longer. Raise `timeout`.

**Domain group not found** — you mixed the notations. `domain_group` wants `root/production`;
`parent_dn` wants `domaingroup-root/domaingroup-production`. Convert with
`get_domain_group_dn`.

**Domain registered but nothing applies to it** — it is not in a domain group, or it is in a
group with no policies. Assign it with `domain_assign_to_domaingroup`.

**`get_domain` returns nothing** — the IP does not match how the domain was registered. Try
`domain_name=` instead.

**Credentials in source control** — `domain_register` needs UCS Manager admin credentials.
Read them from the environment.
