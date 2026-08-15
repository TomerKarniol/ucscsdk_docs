#!/usr/bin/env python3
"""Generate the ucscsdk reference from the installed package.

Stdlib only. Offline. Deterministic: every mapping is emitted in sorted order and
nothing timestamped is written, so two runs produce byte-identical output.

    /usr/bin/python3 docs/_tools/gen_reference.py

Must run under an interpreter that can import the SDK. /usr/bin/python3 (3.12) has
six + pyparsing; the uv python3 on PATH does not. This script only needs the metadata,
so it avoids importing ucschandle/ucscfilter and works under either -- but the method
reference needs ucscmethodfactory, which is import-clean.

Outputs (all paths relative to docs/):
    reference/mo/<package>.md   one per mometa package
    reference/mo/index.md       package index
    reference/methods.md        all 122 XML methods
    agents/mo-index.json        flat, greppable, stable-keyed
    agents/api-index.json       methods + handle surface
"""

import inspect
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(HERE)
REPO = os.path.dirname(DOCS)
SDK = os.path.join(REPO, "ucscsdk")

sys.path.insert(0, SDK)

from ucscsdk import ucsccoreutils as cu          # noqa: E402
from ucscsdk import ucscmethodfactory as mf      # noqa: E402
from ucscsdk.ucscmeta import (                   # noqa: E402
    MO_CLASS_META, METHOD_CLASS_ID, OTHER_TYPE_CLASS_ID,
)

ACCESS = {0: "NAMING", 1: "CREATE_ONLY", 2: "READ_ONLY", 3: "READ_WRITE", 4: "INTERNAL"}

# MethodPropertyMeta.name is an infinitely recursive getter (ucsccoremeta.py:562).
# Never touch .name on one of those -- the dict key is the python name anyway.


def package_of(class_id):
    """mometa subpackage for a class id: the leading lowercase run of the wire name.

    Mirrors ucsccoreutils.load_class (ucsccoreutils.py:144).
    """
    wire = class_id[0].lower() + class_id[1:]
    return re.match("([a-z])+", wire).group()


def naming_props(mo_meta):
    return re.findall(r"\[([^\]]*)\]", mo_meta.rn)


def consts_for(module, class_id):
    """The <Class>Consts sibling, as {attr: value}, or {}."""
    consts = getattr(module, class_id + "Consts", None)
    if consts is None:
        return {}
    return {
        k: v for k, v in vars(consts).items()
        if not k.startswith("_") and isinstance(v, str)
    }


def collect_mos():
    """Introspect all MO classes. Returns {class_id: record} and {class_id: consts}."""
    mos, consts = {}, {}
    for class_id in sorted(MO_CLASS_META):
        mm = MO_CLASS_META[class_id]
        cls = cu.load_class(class_id)
        if cls is None:                     # defensive; every id in the map resolves
            continue
        module = sys.modules[cls.__module__]

        props = {}
        for pname in sorted(cls.prop_meta):
            pm = cls.prop_meta[pname]
            r = pm.restriction
            props[pname] = {
                "xml": pm.xml_attribute,
                "type": pm.field_type,
                "access": ACCESS.get(pm.access, str(pm.access)),
                "version": str(pm.version),
                "mask": hex(pm.mask) if pm.mask else None,
                "min_length": r.min_length,
                "max_length": r.max_length,
                "pattern": r.pattern,
                "value_set": sorted(r.value_set) if r.value_set else [],
                "range": sorted(r.range_val) if r.range_val else [],
            }

        sig = inspect.signature(cls.__init__)
        params = [p for p in sig.parameters if p not in ("self", "kwargs")]

        mos[class_id] = {
            "class_id": class_id,
            "xml": mm.xml_attribute,
            "package": package_of(class_id),
            "module": cls.__module__,
            "rn": mm.rn,
            "naming_props": naming_props(mm),
            "init_args": params,
            "version": str(mm.version),
            "access": mm.inp_out,
            "privileges": sorted(x for x in (mm.access or []) if x),
            "parents": sorted(mm.parents or []),
            "children": sorted(mm.children or []),
            "verbs": sorted({v.capitalize() for v in (mm.verbs or []) if v}),
            "props": props,
        }
        consts[class_id] = consts_for(module, class_id)
    return mos, consts


def collect_methods():
    """Introspect all 122 method builders + their methodmeta contracts."""
    out = {}
    factory = {}
    for name, fn in vars(mf).items():
        if name.startswith("_") or not inspect.isfunction(fn):
            continue
        if fn.__module__ != mf.__name__:
            continue
        factory[name] = fn

    # class id <-> factory function: ConfigResolveDn <-> config_resolve_dn.
    # Naive snake-casing breaks on acronym runs -- AaaGetKVMLaunchUrlInternal is
    # aaa_get_kvm_launch_url_internal, not ..._k_v_m_.... Match on the underscore-free
    # lowercase form instead, which is exact for all 122.
    by_flat = {n.replace("_", ""): n for n in factory}

    def fn_for(cid):
        return by_flat.get(cid.lower())

    for class_id in sorted(METHOD_CLASS_ID):
        module = cu.load_module(class_id)
        mm = module.method_meta
        props = {}
        for pname in sorted(module.prop_meta):
            pm = module.prop_meta[pname]
            props[pname] = {
                "xml": pm.xml_attribute,
                "type": pm.field_type,
                "direction": pm.inp_out,
                "complex": bool(pm.is_complex_type),
                "version": str(pm.version),
            }
        fname = fn_for(class_id)
        fn = factory.get(fname) if fname else None
        out[class_id] = {
            "class_id": class_id,
            "xml": mm.xml_attribute,
            "version": str(mm.version),
            "function": fname if fn else None,
            "signature": (fname + str(inspect.signature(fn))) if fn else None,
            "module": "ucscsdk.methodmeta.%sMeta" % class_id,
            "props": props,
            "inputs": sorted(p for p, d in props.items()
                             if d["direction"] in ("Input", "InputOutput")),
            "outputs": sorted(p for p, d in props.items()
                              if d["direction"] in ("Output", "InputOutput")),
        }
    unmatched = sorted(set(factory) - {v["function"] for v in out.values()})
    return out, unmatched


def collect_handle():
    """Public UcscHandle surface, for the agent index."""
    try:
        from ucscsdk.ucschandle import UcscHandle
    except ImportError as exc:                 # six missing under a bare interpreter
        return {"_unavailable": str(exc)}
    out = {}
    for name, fn in sorted(vars(UcscHandle).items()):
        if name.startswith("_") and name != "__init__":
            continue
        if not callable(fn):
            continue
        doc = (inspect.getdoc(fn) or "").strip().split("\n")[0]
        out[name] = {
            "signature": name + str(inspect.signature(fn)).replace("self, ", "").replace("self", ""),
            "summary": doc,
        }
    return out


# ---------------------------------------------------------------- rendering

def md_escape(s):
    return s.replace("|", "\\|").replace("\n", " ") if isinstance(s, str) else s


def truncate(s, n=60):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def render_package(pkg, class_ids, mos, consts):
    L = []
    L.append("# `mometa/%s` — %d managed object%s\n" % (pkg, len(class_ids), "" if len(class_ids) == 1 else "s"))
    L.append("> Generated by `docs/_tools/gen_reference.py` from ucscsdk 0.9.0.10. "
             "Do not edit by hand.\n")
    L.append("Import pattern: `from ucscsdk.mometa.%s.<Class> import <Class>`\n" % pkg)
    L.append("| Class | Wire name | RN | Naming props | Access |")
    L.append("|---|---|---|---|---|")
    for cid in class_ids:
        m = mos[cid]
        L.append("| [`%s`](#%s) | `%s` | `%s` | %s | %s |" % (
            cid, cid.lower(), m["xml"], md_escape(m["rn"]),
            ", ".join("`%s`" % p for p in m["naming_props"]) or "—",
            m["access"]))
    L.append("")

    for cid in class_ids:
        m = mos[cid]
        L.append("\n---\n")
        L.append("## %s\n" % cid)
        L.append("```python")
        L.append("from ucscsdk.mometa.%s.%s import %s" % (pkg, cid, cid))
        args = ", ".join(m["init_args"])
        L.append("mo = %s(%s)" % (cid, args + (", **kwargs" if m["init_args"] else "**kwargs")))
        L.append("```\n")
        L.append("| | |")
        L.append("|---|---|")
        L.append("| Wire name | `%s` |" % m["xml"])
        L.append("| Module | `%s` |" % m["module"])
        L.append("| RN template | `%s` |" % md_escape(m["rn"]))
        L.append("| DN | parent DN + `/` + RN |")
        L.append("| Naming properties | %s |" % (", ".join("`%s`" % p for p in m["naming_props"]) or "none — RN is static"))
        L.append("| Since | %s |" % m["version"])
        L.append("| Access | `%s` |" % m["access"])
        L.append("| Verbs | %s |" % (", ".join("`%s`" % v for v in m["verbs"]) or "—"))
        L.append("| Privileges | %s |" % (", ".join("`%s`" % p for p in m["privileges"]) or "—"))
        L.append("| Parents | %s |" % (", ".join("`%s`" % p for p in m["parents"]) or "—"))
        nch = len(m["children"])
        if nch:
            shown = ", ".join("`%s`" % c for c in m["children"][:20])
            if nch > 20:
                shown += " … (%d total)" % nch
            L.append("| Children | %s |" % shown)
        else:
            L.append("| Children | — |")
        L.append("")

        writable = [p for p, d in m["props"].items() if d["access"] == "READ_WRITE"]
        L.append("**Configurable properties** (%d of %d): %s\n" % (
            len(writable), len(m["props"]),
            ", ".join("`%s`" % p for p in writable) or "none"))

        L.append("| Property | XML | Type | Access | Since | Restrictions |")
        L.append("|---|---|---|---|---|---|")
        for pname, d in m["props"].items():
            rest = []
            if d["min_length"] is not None:
                rest.append("min %s" % d["min_length"])
            if d["max_length"] is not None:
                rest.append("max %s" % d["max_length"])
            if d["pattern"]:
                rest.append("re `%s`" % md_escape(truncate(d["pattern"], 40)))
            if d["value_set"]:
                rest.append("one of %d" % len(d["value_set"]))
            if d["range"]:
                rest.append("range %s" % md_escape(", ".join(d["range"][:3])))
            L.append("| `%s` | `%s` | %s | %s | %s | %s |" % (
                pname, d["xml"], d["type"], d["access"], d["version"],
                "; ".join(rest) or "—"))
        L.append("")

        cs = consts.get(cid) or {}
        if cs:
            L.append("<details><summary><code>%sConsts</code> — %d values</summary>\n" % (cid, len(cs)))
            L.append("```python")
            L.append("from ucscsdk.mometa.%s.%s import %sConsts" % (pkg, cid, cid))
            for k in sorted(cs):
                L.append("%sConsts.%s = %r" % (cid, k, cs[k]))
            L.append("```")
            L.append("\n</details>\n")
    return "\n".join(L) + "\n"


def render_package_index(by_pkg, mos):
    L = ["# Managed object reference\n",
         "> Generated by `docs/_tools/gen_reference.py`. Do not edit by hand.\n",
         "%d managed objects across %d packages. The package is the leading lowercase run "
         "of the wire name (`lsServer` → `ls`).\n" % (len(mos), len(by_pkg)),
         "| Package | MOs | Notable classes |", "|---|---|---|"]
    for pkg in sorted(by_pkg):
        cids = by_pkg[pkg]
        notable = ", ".join("`%s`" % c for c in cids[:4])
        if len(cids) > 4:
            notable += ", …"
        L.append("| [`%s`](%s.md) | %d | %s |" % (pkg, pkg, len(cids), notable))
    return "\n".join(L) + "\n"


def render_methods(methods, unmatched):
    L = ["# XML method reference\n",
         "> Generated by `docs/_tools/gen_reference.py`. Do not edit by hand.\n",
         "%d methods. Each is built by a function in `ucscsdk.ucscmethodfactory` that "
         "returns an `xml.etree` Element; post it with `handle.process_xml_elem(elem)`.\n"
         % len(methods),
         "All builders serialize with `WriteXmlOption.DIRTY`, so only arguments you pass "
         "appear on the wire.\n",
         "```python",
         "from ucscsdk import ucscmethodfactory as mf",
         "elem = mf.config_resolve_dn(cookie=handle.cookie, dn='org-root')",
         "result = handle.process_xml_elem(elem)",
         "```\n",
         "| Method | XML | Builder | Since |", "|---|---|---|---|"]
    for cid in sorted(methods):
        m = methods[cid]
        L.append("| [`%s`](#%s) | `%s` | `%s` | %s |" % (
            cid, cid.lower(), m["xml"], m["function"] or "—", m["version"]))
    L.append("")
    if unmatched:
        L.append("\nFactory functions with no matching method class id: %s\n"
                 % ", ".join("`%s`" % f for f in unmatched))

    for cid in sorted(methods):
        m = methods[cid]
        L.append("\n---\n")
        L.append("## %s\n" % cid)
        if m["signature"]:
            L.append("```python")
            L.append("from ucscsdk.ucscmethodfactory import %s" % m["function"])
            L.append(m["signature"])
            L.append("```\n")
        L.append("| | |")
        L.append("|---|---|")
        L.append("| XML element | `<%s>` |" % m["xml"])
        L.append("| Meta module | `%s` |" % m["module"])
        L.append("| Since | %s |" % m["version"])
        L.append("")
        L.append("| Property | XML | Type | Direction | Complex |")
        L.append("|---|---|---|---|---|")
        for pname, d in m["props"].items():
            L.append("| `%s` | `%s` | %s | %s | %s |" % (
                pname, d["xml"], d["type"], d["direction"], "yes" if d["complex"] else "—"))
        L.append("")
    return "\n".join(L) + "\n"


def write(path, text):
    full = os.path.join(DOCS, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        fh.write(text)
    return full


def main():
    mos, consts = collect_mos()
    methods, unmatched = collect_methods()

    by_pkg = {}
    for cid, m in mos.items():
        by_pkg.setdefault(m["package"], []).append(cid)
    for pkg in by_pkg:
        by_pkg[pkg].sort()

    n = 0
    for pkg in sorted(by_pkg):
        write("reference/mo/%s.md" % pkg, render_package(pkg, by_pkg[pkg], mos, consts))
        n += 1
    write("reference/mo/index.md", render_package_index(by_pkg, mos))
    write("reference/methods.md", render_methods(methods, unmatched))

    # Agent indexes.
    #
    # mo-index.json is the ROUTING file: one compact entry per class, small enough to
    # load whole (~400KB). mo-details.jsonl carries the full record -- one JSON object
    # per LINE, so `grep '"class_id": "LsServer"' mo-details.jsonl` returns the entire
    # record in one hit. A single 29MB pretty-printed blob was neither loadable nor
    # greppable, which is why these are separate.
    write("agents/mo-index.json", json.dumps({
        "sdk_version": "0.9.0.10",
        "count": len(mos),
        "details": "mo-details.jsonl (one JSON object per line, key: class_id)",
        "packages": {p: sorted(c) for p, c in sorted(by_pkg.items())},
        "classes": {
            cid: {
                "package": m["package"],
                "xml": m["xml"],
                "rn": m["rn"],
                "naming_props": m["naming_props"],
                "access": m["access"],
                "parents": m["parents"],
                "n_props": len(m["props"]),
                "n_writable": sum(1 for d in m["props"].values()
                                  if d["access"] == "READ_WRITE"),
            }
            for cid, m in sorted(mos.items())
        },
    }, indent=1, sort_keys=True) + "\n")

    lines = []
    for cid, m in sorted(mos.items()):
        rec = dict(m)
        rec["consts"] = consts.get(cid) or {}
        lines.append(json.dumps(rec, sort_keys=True))
    write("agents/mo-details.jsonl", "\n".join(lines) + "\n")

    write("agents/api-index.json", json.dumps({
        "sdk_version": "0.9.0.10",
        "handle": collect_handle(),
        "methods": methods,
        "basetypes": {k: v for k, v in sorted(OTHER_TYPE_CLASS_ID.items())},
        "exceptions": [
            "UcscException", "UcscValidationException", "UcscLoginError",
            "UcscConnectionError", "UcscOperationError", "UcscWrapperException",
            "UcscError",
        ],
        "filter_types": [
            "AllbitsFilter", "AndFilter", "AnybitFilter", "BwFilter", "EqFilter",
            "GeFilter", "GtFilter", "LeFilter", "LtFilter", "NeFilter", "NotFilter",
            "OrFilter", "WcardFilter",
        ],
        "filter_str_types": {
            "eq": "EqFilter", "ne": "NeFilter", "ge": "GeFilter", "gt": "GtFilter",
            "le": "LeFilter", "lt": "LtFilter", "re": "WcardFilter",
        },
    }, indent=1, sort_keys=True) + "\n")

    print("mos            %d in %d packages" % (len(mos), len(by_pkg)))
    print("methods        %d (%d unmatched factory fns)" % (len(methods), len(unmatched)))
    print("props          %d" % sum(len(m["props"]) for m in mos.values()))
    print("wrote          %d package pages + index + methods.md + 2 json" % n)


if __name__ == "__main__":
    main()
