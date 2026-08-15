# 8. Events and `wait_for_event`

> Every example needs a live server. Event delivery cannot be exercised offline.

```python
def on_done(mce):
    print("reached:", mce.mo.dn)

sp = handle.query_dn("org-root/ls-sp_demo")
handle.wait_for_event(sp, "oper_state", "ok", on_done, timeout=600)
```

## What this is for

Configuration on UCS Central is asynchronous. `commit()` returns as soon as the server
accepts the change, not when the change has taken effect. Associating a service profile,
applying firmware or registering a domain all take minutes. `wait_for_event` blocks until a
property reaches the value you want.

## `wait_for_event`

```python
wait_for_event(mo, prop, value, cb, timeout=None, poll_sec=None)
```

| Argument | Meaning |
|---|---|
| `mo` | the managed object to watch |
| `prop` | Python property name, e.g. `"oper_state"` |
| `value` | success value, or a **list** of acceptable values |
| `cb` | callback invoked once when the condition is met |
| `timeout` | seconds before giving up. **Set this.** |
| `poll_sec` | if given, poll instead of subscribing to the event channel |

It **blocks the calling thread** until the condition is met or the timeout expires,
sleeping in one-second steps.

A list of values is useful when a terminal state can be success *or* failure:

```python
handle.wait_for_event(sp, "assoc_state", ["associated", "failed"], on_done,
                      timeout=1800)
```

Waiting only for `"associated"` means a failed association hangs until timeout.

## The callback

Called with one argument, a `MoChangeEvent`:

```python
def on_done(mce):
    mce.event_id       # event id
    mce.mo             # the managed object, with current values
    mce.change_list    # properties that changed
```

Keep it short. It runs on the SDK's dequeue thread, so exceptions there do not propagate to
your main thread, and slow work blocks event processing.

## Event channel vs polling

**Event channel (default).** The SDK subscribes to UCS Central's event stream and reacts
when the server pushes a change. Low latency, no repeated queries — but it needs the event
channel to be reachable.

**Polling.** Passing `poll_sec` re-queries the object on an interval instead:

```python
handle.wait_for_event(sp, "oper_state", "ok", on_done,
                      timeout=600, poll_sec=30)
```

Use polling when the event channel is blocked by a firewall, or when you are watching
something that does not generate events reliably. Cost is a query every `poll_sec` seconds
and up to `poll_sec` of extra latency.

Internally these are different filters: in poll mode the event filter rejects everything and
a poll loop does the work instead.

## Validation happens up front

Before waiting, the SDK checks the class and property exist:

```python
handle.wait_for_event(sp, "no_such_prop", "x", cb)
# UcscValidationException: Unknown Property no_such_prop provided.
```

and requires a success value:

```python
# UcscValidationException: success_value parameter is not provided.
```

An unknown class id raises `UcscValidationException: Unknown ClassId ... provided.`

A `None` MO is not an error — `wait` returns immediately and the callback never fires. So
this hangs forever on a typo'd DN:

```python
sp = handle.query_dn("org-root/ls-typo")     # None
handle.wait_for_event(sp, "oper_state", "ok", cb)   # returns at once, cb never called
```

Check for `None` first.

## Always set a timeout

With `timeout=None` and a condition that never becomes true, `wait_for_event` blocks
forever — there is no default ceiling. Pick something matched to the operation: service
profile association can legitimately take 20+ minutes.

## The lower-level API

`wait_for_event` is a convenience wrapper. For more than one watcher, or watching a whole
class, use `UcscEventHandle` directly:

```python
from ucscsdk.ucsceventhandler import UcscEventHandle

ueh = UcscEventHandle(handle)

wb = ueh.add(class_id="LsServer", call_back=lambda mce: print(mce.mo.dn))
# ... other work happens while events arrive ...
ueh.remove(wb)
```

`add()` signature:

```python
add(class_id=None, managed_object=None, prop=None, success_value=[],
    poll_sec=None, timeout_sec=None, call_back=None, context=None)
```

Rules:

- Give `class_id` **or** `managed_object`, never both — that raises
  `UcscValidationException`.
- Neither means watch **everything**.
- With `managed_object` plus `prop`, `success_value` is required.

Other methods: `remove(watch_block)`, `clean()` to drop all watchers, `get()` to list them.

Unlike `wait_for_event`, `add()` does not block. Your program keeps running and callbacks
fire on the dequeue thread.

The reader and dispatcher threads start with the first watch block and are daemon threads,
so they will not keep your process alive.

## A realistic pattern

```python
from ucscsdk.ucscexception import UcscException
from ucscsdk.mometa.ls.LsServer import LsServer

sp = LsServer("org-root", name="sp_demo")
sp.descr = "provisioned"
handle.add_mo(sp, modify_present=True)
handle.commit()

sp = handle.query_dn("org-root/ls-sp_demo")
if sp is None:
    raise RuntimeError("service profile missing after commit")

state = {}
def done(mce):
    state["oper_state"] = mce.mo.oper_state

handle.wait_for_event(sp, "assoc_state", ["associated", "failed"], done,
                      timeout=1800)

if state.get("oper_state") != "ok":
    raise RuntimeError("did not come up: %r" % state)
```

Commit, re-query to get a server-backed object, wait for a terminal state, then check
which terminal state you got.

## Common errors

**Hangs forever** — no `timeout`, and the condition never becomes true. Or the MO was
`None`, in which case the call returned immediately and your callback simply never ran.

**`UcscValidationException: Unknown Property <p> provided.`** — wrong property name. Use the
Python name (`oper_state`, not `operState`).

**`UcscValidationException: success_value parameter is not provided.`** — watching a
property requires a success value.

**`UcscValidationException: Specify either class_id or managedObject, not both`** — pick
one.

**Callback never fires although the value did change** — the event channel is unreachable;
retry with `poll_sec`. Or the value passed through your target between polls; watch a
terminal state, not a transient one.

**Exception inside the callback disappears** — it runs on the dequeue thread. Wrap the body
in try/except and record the result somewhere your main thread reads.

**Process exits before events arrive** — the event threads are daemons. `wait_for_event`
blocks, so this only bites with the `UcscEventHandle` API; keep the main thread alive.
