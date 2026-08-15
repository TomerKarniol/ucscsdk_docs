# 9. Error handling

> Exception behaviour below was verified offline against the installed package.

```python
from ucscsdk.ucscexception import UcscException, UcscValidationException

try:
    handle.add_mo(sp)
    handle.commit()
except UcscException as e:
    print("server rejected:", e.error_code, e.error_descr)
except UcscValidationException as e:
    print("client-side validation:", e.error_msg)
```

## The hierarchy

There are two unrelated roots. This matters — there is no single base class to catch.

```
Exception
├── UcscWrapperException          client-side / transport
│   ├── UcscLoginError
│   ├── UcscConnectionError
│   └── UcscOperationError
└── UcscError                     server-side / validation
    ├── UcscException
    └── UcscValidationException
```

To catch everything from the SDK you need both:

```python
from ucscsdk.ucscexception import UcscWrapperException, UcscError

try:
    ...
except (UcscWrapperException, UcscError) as e:
    ...
```

Plain `except UcscError` misses login and connection failures. `except Exception` also
catches the `ValueError`s and `urllib` errors described below.

## `UcscException` — the server said no

Raised whenever a response carries a non-zero error code.

```python
try:
    handle.commit()
except UcscException as e:
    e.error_code     # e.g. '103'
    e.error_descr    # human-readable reason
    str(e)           # '[ErrorCode]: 103[ErrorDescription]: ...'
```

Two things to know:

**`error_code` is a string off the wire**, even though the SDK's internal default is the
integer `0`. Compare as a string, or normalise:

```python
if str(e.error_code) == "103":
    ...
```

**`e.args` is empty.** `UcscException.__init__` never calls `super().__init__()`, so
`str(e)` and the two properties are the only way to get the message. Logging `e.args` gets
you `()`.

## `UcscValidationException` — the SDK said no

Raised before anything is sent, by client-side checks:

```python
try:
    handle.wait_for_event(sp, "bad_prop", "x", cb)
except UcscValidationException as e:
    e.error_msg
    str(e)        # '[ErrorMessage]: ...'
```

Sources: a naming property that is `None` when the RN is built, and the event handler's
argument checks (unknown class id, unknown property, missing success value).

Note the attribute is `error_msg`, not `error_descr`.

## `UcscLoginError`

Authentication and connection-parameter problems:

```python
UcscHandle("1.2.3.4", "admin", "pw", port=8443)
# UcscLoginError: Can not login to UcsCentral with port other than '443'
```

It accepts an `error_code` argument but **discards it** — `e.error_code` is an
`AttributeError`. Use `str(e)`.

Bad credentials do *not* raise this; they raise `UcscException` from the server's response.

## `UcscOperationError`

Raised by the utility modules when a multi-step operation fails. It formats its message at
construction:

```python
UcscOperationError("Getting Version", "Failed")
# str(e) == 'Getting Version failed, error: Failed'
```

The `operation` and `error` parts are not kept as attributes.

## `UcscConnectionError`

Defined and exported, but rarely raised — transport failures usually surface as raw
`urllib` exceptions instead. Do not rely on it as your network-error catch.

## Errors that are not SDK exceptions

A lot of everyday failures are plain builtins:

| What you did | What you get |
|---|---|
| assigned a read-only property | `ValueError: <p> is not a read-write property.` |
| assigned an invalid value | `ValueError: Invalid Value Exception - [Class]: ...` |
| omitted a naming property | `TypeError: __init__() missing 1 required positional argument` |
| empty DN to `query_dn` | `ValueError: Provide dn.` |
| no `in_mo`/`in_dn` to `query_children` | `ValueError: [Error]: GetChild: Provide in_mo or in_dn.` |
| unknown property in a filter | `KeyError: '<prop>'` |
| malformed filter | `pyparsing.ParseException` |
| committed an unused tag | `KeyError: '<tag>'` |
| network failure | `urllib.error.URLError`, `socket.timeout` |

So a realistic guard is broader than the SDK's own hierarchy:

```python
from ucscsdk.ucscexception import UcscWrapperException, UcscError

try:
    ...
except (UcscWrapperException, UcscError) as e:
    log.error("ucs: %s", e)
except (ValueError, KeyError, TypeError) as e:
    log.error("client-side: %s", e)
```

## Silent failures

Several conditions produce no exception at all. These cause more lost time than any
exception:

| Symptom | Cause |
|---|---|
| `commit()` did nothing | buffer empty — forgot to stage, or already committed |
| `query_dn` returned `None` | DN does not exist; misspelling looks identical |
| filter matched everything | omitted `type="eq"`; default is wildcard |
| property assignment ignored | used the wire name (`usrLbl`) instead of `usr_lbl` |
| `wait_for_event` returned instantly | the MO was `None` |
| `get_auth_token()` returned `None` | no blades or rack units in the domain |
| filter silently ignored | passed to a method with no `filter_str` |

Assert rather than assume:

```python
sp = handle.query_dn(dn)
if sp is None:
    raise RuntimeError("not found: %s" % dn)
```

## A failed commit discards your work

```python
try:
    handle.commit()
except UcscException:
    # the buffer is ALREADY EMPTY here
    ...
```

There is nothing to fix and resend — rebuild and re-stage. This is deliberate, and it also
means a retry loop around `commit()` alone will do nothing on the second pass.

```python
for attempt in range(3):
    try:
        stage_everything(handle)      # must re-stage each time
        handle.commit()
        break
    except UcscException as e:
        if attempt == 2:
            raise
```

## Debugging

```python
import logging, ucscsdk
ucscsdk.set_log_level(logging.DEBUG)

handle.set_dump_xml()
...
handle.unset_dump_xml()
```

The XML dump is usually decisive: it shows exactly which properties were marked dirty and
sent. Passwords are masked in `aaaLogin`; session cookies are not.

## Common errors

**`except UcscError` did not catch a login failure** — `UcscLoginError` descends from
`UcscWrapperException`, a separate root. Catch both.

**`e.args` is empty** — expected for `UcscException`. Use `str(e)`, `e.error_code`,
`e.error_descr`.

**`AttributeError: 'UcscLoginError' object has no attribute 'error_code'`** — the constructor
accepts it and drops it.

**`AttributeError: 'UcscValidationException' object has no attribute 'error_descr'`** — that
class uses `error_msg`.

**Comparing `e.error_code` to an int always fails** — it is a string from XML.

**Retrying `commit()` in a loop changes nothing** — the buffer was discarded on the first
failure. Re-stage inside the loop.

**`AttributeError: module 'ssl' has no attribute 'wrap_socket'`** — the TLSv1 fallback path
on Python 3.12+. The real failure was an SSL error; this masks it.

**`AttributeError: module 'inspect' has no attribute 'getargspec'`** — you called
`ucsccoreutils.load_mo` or `GenericMo.to_mo`, both broken on Python 3.11+. Use
`load_class` instead.
