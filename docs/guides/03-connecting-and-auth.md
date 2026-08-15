# 3. Connecting and authentication

> Snippets that reach a server are marked. Everything else was run offline.

```python
from ucscsdk.ucschandle import UcscHandle

handle = UcscHandle("192.168.1.1", "admin", "password")
handle.login()
try:
    print(handle.version, handle.session_id)
finally:
    handle.logout()
```

> Needs a live server.

## Constructing the handle

```python
UcscHandle(ip, username, password, port=443, proxy=None)
```

Nothing connects yet — the constructor only builds a URI and a driver. One thing *is*
validated immediately:

```python
UcscHandle("1.2.3.4", "admin", "pw", port=8443)
# UcscLoginError: Can not login to UcsCentral with port other than '443'
```

**Only port 443 works.** The check is in the constructor, so this raises before you call
`login()`. The SDK's own docstring shows `port=100` as an example; that example is wrong.

## Logging in

```python
handle.login(auto_refresh=False, force=False)
```

Returns `True` on success, raises `UcscException` on rejection.

| Argument | Effect |
|---|---|
| `auto_refresh=True` | starts a background timer that renews the session before it expires |
| `force=True` | logs out and reconnects even if the existing cookie is still valid |

Without `force`, `login()` first probes the existing session by resolving `sys`. If that
works, it returns `True` without re-authenticating — so calling `login()` twice is cheap
and safe.

## Session state

After a successful login the handle exposes read-only properties:

```python
handle.cookie            # session cookie, sent with every request
handle.session_id
handle.version           # UcscVersion, e.g. 2.0(1a)
handle.refresh_period    # seconds until the session expires
handle.priv              # privilege list
handle.domains
handle.channel
handle.evt_channel       # event channel, used by the event handler
handle.last_update_time
handle.ip
handle.username
handle.uri               # 'https://192.168.1.1:443'
handle.proxy
handle.ucs
```

All are properties without setters — assigning to them raises `AttributeError`.

**`handle.ucs` is not the system name.** It is set to the IP you passed in and never
updated. `_login` does try to overwrite it with the real `TopSystem.name`, but writes to a
differently-named attribute, so the assignment is lost. If you want the system name, ask
for it:

```python
handle.query_dn("sys").name
```

> Needs a live server.

`handle.version` is a `UcscVersion`, not a string — comparable, but not hashable:

```python
from ucscsdk.ucsccoremeta import UcscVersion
handle.version > UcscVersion("1.5(1a)")     # True/False
str(handle.version)                          # '2.0(1a)'
```

## Session refresh

UCS Central sessions expire after `refresh_period` seconds. Two options.

**Automatic** — a daemon `threading.Timer` renews at `refresh_period - 60` seconds
(minimum 60):

```python
handle.login(auto_refresh=True)
```

The timer is a daemon thread, so it will not keep your process alive, and `logout()`
cancels it.

**Manual** — do nothing, and re-login when a call fails with an authentication error.
Fine for short scripts.

There is no public "refresh now" method; the internal one is `handle._refresh()`.

## Proxy

```python
handle = UcscHandle("192.168.1.1", "admin", "password",
                    proxy="http://proxy.example.com:8080")
```

The string is passed straight to `urllib`'s `ProxyHandler` for both `http` and `https`.

## TLS is not verified

The SDK builds its SSL context with no CA bundle, `check_hostname=False`, and
`verify_mode=CERT_NONE`. **The server certificate is not validated and the hostname is not
checked.** Traffic is encrypted but not authenticated, so an active man-in-the-middle is
not detected.

There is no option to enable verification — it would require patching `ucscdriver.py`.
Treat UCS Central connections as trusted-network-only, and do not rely on TLS here as an
authentication boundary.

Related: if the initial handshake raises anything mentioning SSL, the driver retries once
with a TLSv1-only connection. On Python 3.12+ that retry path itself fails with
`AttributeError: module 'ssl' has no attribute 'wrap_socket'`, because `ssl.wrap_socket`
was removed. The primary path is unaffected.

## Auth token

`get_auth_token()` returns a one-shot token, typically for launching KVM:

```python
token = handle.get_auth_token()
```

> Needs a live server.

It works by finding a server to scope the token to: it queries `ComputeBlade`, falls back
to `ComputeRackUnit`, then requests a token for the first result. **If the domain has no
blades and no rack units, it returns `None`** rather than raising — check the result.

## Logging out

```python
handle.logout()
```

Returns `True`. Safe to call when never logged in (returns `True` immediately). It cancels
the refresh timer and clears session state. A server response of error code `555` is
treated as success — the session was already gone.

`logout` deliberately bypasses the global transaction lock, so it will not block behind an
in-flight request.

## Multiple handles

Each `UcscHandle` has its own session. But the transaction lock is **module-level**, shared
across every handle in the process, so requests from different handles still serialize.
Separate handles give you separate sessions and separate commit buffers, not concurrency.
See [07 — transactions and threading](07-transactions-and-threading.md).

## Seeing the traffic

```python
handle.set_dump_xml()
handle.query_dn("org-root")
handle.unset_dump_xml()
```

> Needs a live server.

Requests and responses go to the `ucscentral` logger at DEBUG, so enable logging too:

```python
import logging, ucscsdk
ucscsdk.set_log_level(logging.DEBUG)
```

The password in the `aaaLogin` request is masked before logging and restored afterwards, so
dumping does not leak credentials. Nothing else is redacted — session cookies **are**
logged.

## Common errors

**`UcscLoginError: Can not login to UcsCentral with port other than '443'`** — raised by the
constructor. Drop the `port` argument.

**`UcscException: [ErrorCode]: 551 [ErrorDescription]: Authentication failed`** — bad
credentials. `e.error_code` and `e.error_descr` carry the detail.

**`urllib.error.URLError` / socket timeout on `login()`** — network or firewall, not auth.
The SDK does not wrap these; you get the `urllib` exception.

**`AttributeError: module 'ssl' has no attribute 'wrap_socket'`** — the TLSv1 fallback fired
on Python 3.12+. The original failure was an SSL error; this exception masks it. Check the
server's TLS configuration.

**Session dies mid-script** — you did not pass `auto_refresh=True` and exceeded
`refresh_period`. Either enable it or re-login.

**`handle.ucs` returns an IP, not a name** — expected; see above. Query `sys` instead.

**`TypeError: unhashable type: 'UcscVersion'`** — `handle.version` cannot be a dict key.
Use `str(handle.version)`.
