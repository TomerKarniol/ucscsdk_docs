# 7. Transactions and threading

> Examples need a live server unless marked otherwise.

```python
handle.add_mo(mo1, tag="net")
handle.add_mo(mo2, tag="compute")
handle.commit(tag="net")        # sends mo1 only
handle.commit(tag="compute")    # sends mo2 only
```

## The default transaction

Everything staged since the last `commit()` is one transaction. One request, atomic on the
server:

```python
handle.add_mo(LsServer("org-root", name="sp1"))
handle.add_mo(LsServer("org-root", name="sp2"))
handle.commit()          # both, or neither
```

There is no explicit "begin". The buffer opens when you stage the first object and closes
when you commit or discard.

## Independent transactions with `tag=`

One handle has one default buffer plus a dictionary of tagged buffers. `tag=` is accepted
by `add_mo`, `set_mo`, `remove_mo`, `commit` and `commit_buffer_discard`:

```python
handle.add_mo(mo1, tag="trans_1")
handle.add_mo(mo2, tag="trans_2")
handle.add_mo(mo3, tag="trans_1")
handle.remove_mo(mo4, tag="trans_2")

handle.commit(tag="trans_2")     # mo2 and mo4
handle.add_mo(mo5, tag="trans_1")
handle.commit(tag="trans_1")     # mo1, mo3, mo5
```

Tagged buffers are completely independent — a failure in one does not disturb another.

The tagged buffer is created on first use. Committing a tag that was never staged raises
`KeyError`, unlike the default buffer which quietly returns `None`:

```python
handle.commit(tag="never_used")     # KeyError: 'never_used'
```

Guard it if the tag is computed.

## Threading mode

```python
handle.set_mode_threading()
```

Each thread now gets its own buffer automatically, keyed by thread name, without passing
`tag=` anywhere:

```python
import threading

def worker(name):
    sp = LsServer("org-root", name=name)
    handle.add_mo(sp)      # goes to this thread's own buffer
    handle.commit()        # commits only this thread's work

for n in ["sp1", "sp2", "sp3"]:
    threading.Thread(target=worker, args=(n,), name=n).start()
```

Without threading mode every thread would share the default buffer, and one thread's
`commit()` would send another thread's half-built objects.

Turn it off with `handle.unset_mode_threading()`; check with
`handle.is_threading_enabled()`.

An explicit `tag=` always wins over the automatic thread tag.

### Threads must commit their own work

The tag is the *current* thread's name. Staging in one thread and committing from another
means the committing thread looks in its own buffer, finds it empty, and returns `None`
silently.

### Thread names must be distinct

The buffer key is `threading.currentThread().name`. Two threads with the same name share a
buffer. Python's defaults (`Thread-1`, `Thread-2`) are unique; if you name threads
yourself, keep them unique.

## Threading does not make requests parallel

This is the important limitation.

`ucscsession` holds a **module-level** lock that `post_elem` acquires around every request
except `aaaLogout`. It is global to the process — shared by every handle, every thread.

So:

- Threads stage work **concurrently**.
- Requests go out **one at a time**, in whatever order threads reach the lock.

Threading mode buys transaction isolation, not throughput. Ten threads against UCS Central
are not ten times faster; they serialize at the lock. If you are trying to speed up bulk
work, batch more objects into fewer commits instead — one `commit()` with fifty staged
objects is one request.

Separate `UcscHandle` instances do not help either; the lock is module-level, not
per-handle. Separate *processes* would, at the cost of separate sessions.

## Failure semantics

A failed commit **discards that buffer** and raises:

```python
try:
    handle.commit(tag="trans_1")
except UcscException as e:
    # trans_1's buffer is already empty — nothing to retry
    print(e.error_code, e.error_descr)
```

Rebuild and re-stage; there is nothing left to fix and resend. Other tags are untouched.

## Practical batching

```python
BATCH = 50
staged = 0
for name in names:
    handle.add_mo(LsServer("org-root", name=name), modify_present=True)
    staged += 1
    if staged % BATCH == 0:
        handle.commit()
if staged % BATCH:
    handle.commit()
```

One request per 50 objects instead of one per object. Batch size is a trade-off: bigger
batches are faster but lose more work on failure, and very large filters or payloads can hit
server limits.

## Common errors

**`KeyError: '<tag>'`** — committing a tag nothing was staged under. Note the default
buffer returns `None` in the same situation; tagged buffers raise.

**`commit()` silently does nothing under threading mode** — you staged in one thread and
committed in another, or the thread was renamed in between.

**Two threads clobber each other's buffers** — duplicate thread names, or threading mode
was never enabled.

**Adding threads did not speed anything up** — expected. The global transaction lock
serializes requests. Batch instead.

**A failed commit lost work in an unrelated tag** — it should not; buffers are separate. If
you see this, check you are not passing the same tag from both places, or relying on the
automatic thread tag while also passing explicit tags.

**Deadlock or hang on commit** — a long-running request holds the global lock; every other
thread waits. Set a timeout at the transport layer or reduce batch size.
