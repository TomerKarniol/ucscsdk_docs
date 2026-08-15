# 14. XML to Python — `converttopython`

> The example below was executed offline. This tool needs no server.

```python
from ucscsdk.utils.converttopython import convert_to_ucs_python

xml_str = '''<configConfMo dn="" cookie="SECURED" inHierarchical="false">
  <inConfig>
    <fabricUdldLinkPolicy adminState="enabled" descr="for testing"
      dn="domaingroup-root/udld-link-pol-test_udldlink"
      name="test_udldlink" status="created"/>
  </inConfig>
</configConfMo>'''

convert_to_ucs_python(xml=True, request=xml_str)
```

Real output:

```
### Please review the generated cmdlets before deployment.

##### Start-Of-PythonScript #####

from ucscsdk.mometa.fabric.FabricUdldLinkPolicy import FabricUdldLinkPolicy

mo = FabricUdldLinkPolicy(parent_mo_or_dn="domaingroup-root", admin_state="enabled", descr="for testing", name="test_udldlink")
handle.add_mo(mo)

handle.commit()
##### End-Of-PythonScript #####
### End of Convert-To-Python ###
```

## Why this exists

You do something in the UCS Central GUI, capture the XML it sent, and this turns it into
the equivalent SDK code. It is the fastest way to learn which class and properties
correspond to a screen you already know how to use.

It also answers "what is the Python name for this XML attribute?" — note `adminState`
became `admin_state` above, and the `dn` was split into a `parent_mo_or_dn` plus the naming
property `name`.

## Signature

```python
convert_to_ucs_python(xml=False, request=None, dump_to_file=False,
                      dump_file_path=None, dump_xml=False)
```

| Argument | Meaning |
|---|---|
| `xml` | `True` to convert the string in `request` |
| `request` | the XML string |
| `dump_to_file` | write the generated script to a file |
| `dump_file_path` | where to write it |
| `dump_xml` | also print the XML that was parsed |

Two modes:

**Explicit XML** — pass `xml=True` and a `request` string, as above.

**Log-scraping** — call it with no arguments and it reads a UCS Central GUI log, extracting
XML requests and converting each one:

```python
convert_to_ucs_python()
convert_to_ucs_python(dump_xml=True)
```

The interactive mode looks for the Java/GUI log on your machine, so it only works where the
GUI has been run.

Writing to a file:

```python
convert_to_ucs_python(xml=True, request=xml_str,
                      dump_to_file=True,
                      dump_file_path="/home/user/generated.py")
```

## What it handles

The converter recognises the common request shapes and emits idiomatic code for each:

| XML method | Generated |
|---|---|
| `configConfMo` / `configConfMos` | MO construction + `add_mo` + `commit` |
| `configResolveDn` / `configResolveClass` | `query_dn` / `query_classid`, including filters |
| `configConfRename` | rename |
| `lsClone`, `lsInstantiate*` | clone / instantiate-from-template |
| `lsTemplatise` | templatise |
| `statsClearInterval` | clear interval |

Nested `<inConfig>` trees become nested MO construction with the parent passed to each
child.

## Review before you run

The banner is not decoration. The generated code:

- has **no `handle`** — it assumes one exists in scope;
- contains **no error handling**;
- reproduces whatever the GUI sent, including properties you may not want to set;
- may include a `status` the GUI computed for its own situation.

Treat it as a first draft. Typical edits are removing properties you do not care about,
replacing hard-coded names with variables, and adding `modify_present=True` to make it
idempotent.

## Capturing the XML

Two ways to get input:

**From the SDK itself.** Dump traffic from a working script and reuse the XML:

```python
handle.set_dump_xml()
```

Requests and responses go to the `ucscentral` logger at DEBUG.

**From the GUI log.** The interactive mode reads it for you; otherwise find the log and
copy the request out.

Remember the captured XML contains a **session cookie**. Do not paste it into a bug report
or commit it — replace it, as the example above does with `cookie="SECURED"`.

## A round trip

Because the generated code is normal SDK code, you can verify it produces the same XML you
started with:

```python
from ucscsdk.mometa.fabric.FabricUdldLinkPolicy import FabricUdldLinkPolicy
from ucscsdk import ucscxmlcodec as xc

mo = FabricUdldLinkPolicy(parent_mo_or_dn="domaingroup-root",
                          admin_state="enabled", descr="for testing",
                          name="test_udldlink")
mo.status = "created"
print(xc.to_xml_str(mo.to_xml()).decode())
```

> Runs offline.

That is the check the SDK's own `tests/convert_to_ucs/` directory performs.

## Common errors

**`xml.etree.ElementTree.ParseError`** — the XML is malformed, usually truncated on copy or
missing a wrapping element.

**Nothing is generated** — the request method is not one of the recognised shapes. Only the
methods listed above are handled; anything else produces no output.

**Interactive mode finds no log** — it looks for the GUI log locally. Use `xml=True` with an
explicit string instead.

**Generated code raises `NameError: name 'handle' is not defined`** — expected; supply your
own handle.

**Generated code fails with "already exists"** — the captured request was a create. Add
`modify_present=True` to `add_mo`.

**`SyntaxWarning: invalid escape sequence`** on import — a known artefact of this module's
source. Harmless.
