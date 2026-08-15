#!/usr/bin/env python3
"""Verify every factual claim in docs/ against the installed ucscsdk.

Stdlib only. Offline. Exits non-zero on any failure.

    /usr/bin/python3 docs/_tools/verify_docs.py

Checks, in order:
  1. syntax     -- every ```python block ast.parse()s
  2. imports    -- every `from ucscsdk... import X` / `import ucscsdk...` resolves
  3. symbols    -- every dotted ucscsdk.* attribute path referenced in prose exists
  4. classes    -- every MO class id named in docs is in MO_CLASS_ID
  5. props      -- every <Cls>.prop_meta / get_mo_property_meta reference is real
  6. signatures -- every documented `func(a, b=c)` matches inspect.signature
  7. links      -- every relative markdown link resolves on disk
  8. linerefs   -- every `file.py:NN` points at a line that exists

Note on link checking: the generated reference embeds property regexes such as
`^[A-Za-z]([A-Za-z0-9-]*[A-Za-z0-9])?$` inside code spans. A naive scan reads
`[...](...)` as a markdown link and reports ~19 phantom failures, so inline code spans
and fenced blocks are stripped before links are checked.
"""

import ast
import glob
import importlib
import inspect
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(HERE)
REPO = os.path.dirname(DOCS)
SDK = os.path.join(REPO, "ucscsdk")
SRC = os.path.join(SDK, "ucscsdk")

sys.path.insert(0, SDK)

failures = []
counts = {}


def fail(check, where, msg):
    failures.append((check, where, msg))


def bump(check, n=1):
    counts[check] = counts.get(check, 0) + n


def docs_files():
    return sorted(glob.glob(os.path.join(DOCS, "**", "*.md"), recursive=True))


def rel(path):
    return os.path.relpath(path, REPO)


def code_blocks(text, lang="python"):
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


def strip_code(text):
    """Remove fenced blocks and inline code spans -- see module docstring."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def strip_output_blocks(text):
    """Remove UNLABELLED fenced blocks, keeping ```python ones.

    Unlabelled fences hold pasted terminal output. VERIFICATION.md quotes this
    checker's own failure messages -- which name symbols that deliberately do not
    exist -- and those must not be re-checked as claims. Labelled ```python blocks
    are kept, so `# mometa/ls/LsServer.py:389`-style references inside real code
    examples are still verified.
    """
    return re.sub(r"```[ \t]*\n.*?```", "", text, flags=re.S)


# ---------------------------------------------------------------- 1. syntax

def check_syntax(files):
    for f in files:
        for i, block in enumerate(code_blocks(open(f).read()), 1):
            bump("syntax")
            try:
                ast.parse(block)
            except SyntaxError as e:
                fail("syntax", "%s block %d" % (rel(f), i), str(e))


# ------------------------------------------------------- 2. imports & symbols

def resolve(dotted):
    """Resolve 'ucscsdk.a.b.C' to an object, trying module then attribute."""
    parts = dotted.split(".")
    for split in range(len(parts), 0, -1):
        mod_name = ".".join(parts[:split])
        try:
            obj = importlib.import_module(mod_name)
        except Exception:
            continue
        for attr in parts[split:]:
            if not hasattr(obj, attr):
                raise AttributeError("%s has no attribute %r" % (mod_name, attr))
            obj = getattr(obj, attr)
        return obj
    raise ImportError("cannot import %s" % dotted)


def check_imports(files):
    for f in files:
        for i, block in enumerate(code_blocks(open(f).read()), 1):
            try:
                tree = ast.parse(block)
            except SyntaxError:
                continue                      # already reported by check_syntax
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if not (node.module or "").startswith("ucscsdk"):
                        continue
                    for alias in node.names:
                        bump("imports")
                        try:
                            resolve(node.module + "." + alias.name)
                        except Exception as e:
                            fail("imports", "%s block %d" % (rel(f), i),
                                 "from %s import %s -- %s" % (node.module, alias.name, e))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if not alias.name.startswith("ucscsdk"):
                            continue
                        bump("imports")
                        try:
                            importlib.import_module(alias.name)
                        except Exception as e:
                            fail("imports", "%s block %d" % (rel(f), i),
                                 "import %s -- %s" % (alias.name, e))


SYMBOL_RE = re.compile(r"\bucscsdk(?:\.[A-Za-z_][A-Za-z0-9_]*)+")

# Attribute paths that are legitimately absent from the package: prose about
# things that do NOT exist, and module paths used as illustrative placeholders.
SYMBOL_ALLOW = {
    "ucscsdk.mometa.ls.LsServer.LsServerConsts",   # resolved via class module
}


def check_symbols(files):
    for f in files:
        text = strip_output_blocks(open(f).read())
        for m in set(SYMBOL_RE.findall(text)):
            dotted = m.rstrip(".")
            if dotted in SYMBOL_ALLOW:
                continue
            bump("symbols")
            try:
                resolve(dotted)
            except Exception as e:
                fail("symbols", rel(f), "%s -- %s" % (dotted, e))


# ------------------------------------------------------------- 4. MO classes

def check_classes(files):
    from ucscsdk.ucscmeta import MO_CLASS_ID, METHOD_CLASS_ID

    # Class ids appear as `LsServer` in code spans; only check ones we assert exist
    pat = re.compile(r"from ucscsdk\.mometa\.([a-z]+)\.([A-Za-z0-9]+) import ([A-Za-z0-9, ]+)")
    for f in files:
        text = strip_output_blocks(open(f).read())
        for pkg, mod, names in pat.findall(text):
            bump("classes")
            if mod not in MO_CLASS_ID:
                fail("classes", rel(f), "%s not in MO_CLASS_ID" % mod)
                continue
            expected_pkg = re.match("([a-z])+", mod[0].lower() + mod[1:]).group()
            if pkg != expected_pkg:
                fail("classes", rel(f),
                     "%s is in package %r, doc says %r" % (mod, expected_pkg, pkg))
            for name in [n.strip() for n in names.split(",") if n.strip()]:
                if name not in (mod, mod + "Consts"):
                    fail("classes", rel(f), "%s imports unexpected name %s" % (mod, name))

    # method factory functions referenced as ucscmethodfactory.<fn> or mf.<fn>
    import ucscsdk.ucscmethodfactory as mf
    for f in files:
        for fn in set(re.findall(r"\bmf\.([a-z_][a-z0-9_]*)\s*\(",
                                 strip_output_blocks(open(f).read()))):
            bump("classes")
            if not hasattr(mf, fn):
                fail("classes", rel(f), "ucscmethodfactory has no %s" % fn)


# ---------------------------------------------------------------- 5. props

# `Class.prop_meta` membership assertions written as "prop" in Class.prop_meta
PROP_IN_META = re.compile(r'"([a-z_][a-z0-9_]*)"\s+in\s+([A-Z][A-Za-z0-9]*)\.prop_meta')
PROP_NOT_IN = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"\s+in\s+([A-Z][A-Za-z0-9]*)\.prop_meta\s*#\s*False')


def check_props(files):
    from ucscsdk import ucsccoreutils as cu

    for f in files:
        text = strip_output_blocks(open(f).read())
        negatives = {(p, c) for p, c in PROP_NOT_IN.findall(text)}
        for prop, cls in PROP_IN_META.findall(text):
            if (prop, cls) in negatives:
                continue
            bump("props")
            klass = cu.load_class(cls)
            if klass is None:
                fail("props", rel(f), "unknown class %s" % cls)
            elif prop not in klass.prop_meta:
                fail("props", rel(f), "%s.prop_meta has no %r" % (cls, prop))

        # get_mo_property_meta("Class", "prop")
        for cls, prop in re.findall(
                r'get_mo_property_meta\(\s*"([A-Za-z0-9]+)"\s*,\s*"([a-z_][a-z0-9_]*)"', text):
            bump("props")
            if prop == "mo_meta":
                continue
            if cu.get_mo_property_meta(cls, prop) is None:
                fail("props", rel(f), "get_mo_property_meta(%r, %r) is None" % (cls, prop))


# ------------------------------------------------------------ 6. signatures

SIG_RE = re.compile(r"^([a-z_][a-z0-9_]*)\((.*)\)\s*$", re.M)

# module search order for a bare function name documented as `foo(a, b=1)`
SIG_MODULES = [
    "ucscsdk.ucscmethodfactory",
    "ucscsdk.utils.ucscbackup",
    "ucscsdk.utils.ucscfirmware",
    "ucscsdk.utils.ucsctechsupport",
    "ucscsdk.utils.ucscdomain",
    "ucscsdk.utils.ccoimage",
    "ucscsdk.utils.converttopython",
    "ucscsdk.ucsccoreutils",
    "ucscsdk.ucscfilter",
    "ucscsdk.ucscgenutils",
]


def normalise(sig):
    """inspect.signature text -> comparable form (drop annotations/defaults repr noise)."""
    return re.sub(r"\s+", "", sig)


def check_signatures(files):
    from ucscsdk.ucschandle import UcscHandle

    mods = {}
    for name in SIG_MODULES:
        try:
            mods[name] = importlib.import_module(name)
        except Exception as e:
            fail("signatures", name, "module import failed: %s" % e)

    handle_members = {n: v for n, v in vars(UcscHandle).items() if callable(v)}

    for f in files:
        for block in code_blocks(open(f).read()):
            for m in SIG_RE.finditer(block):
                fname, args = m.group(1), m.group(2)
                if "=" not in args and "," not in args and not args:
                    continue                        # bare foo() -- nothing to check
                target = None
                if fname in handle_members:
                    target = handle_members[fname]
                else:
                    for mod in mods.values():
                        if hasattr(mod, fname):
                            cand = getattr(mod, fname)
                            if inspect.isfunction(cand):
                                target = cand
                                break
                if target is None:
                    continue                        # not a documented SDK function
                bump("signatures")
                try:
                    real = str(inspect.signature(target))
                except (ValueError, TypeError):
                    continue
                real_params = [p for p in inspect.signature(target).parameters
                               if p not in ("self",)]
                doc_params = []
                try:
                    call = ast.parse(fname + "(" + args + ")", mode="eval").body
                except SyntaxError:
                    continue
                for a in call.args:
                    doc_params.append(getattr(a, "id", None))
                for kw in call.keywords:
                    doc_params.append(kw.arg)
                for p in doc_params:
                    if p is None or p == "handle":
                        continue
                    if p not in real_params:
                        fail("signatures", rel(f),
                             "%s(...): %r is not a parameter -- real: %s"
                             % (fname, p, real))


# --------------------------------------------------------------- 7. links

LINK_RE = re.compile(r"\[[^\]]*\]\((?!https?:|mailto:)([^)#]+)(?:#[^)]*)?\)")


def check_links(files):
    for f in files:
        for target in LINK_RE.findall(strip_code(open(f).read())):
            bump("links")
            resolved = os.path.normpath(os.path.join(os.path.dirname(f), target))
            if not os.path.exists(resolved):
                fail("links", rel(f), "broken link -> %s" % target)


# ------------------------------------------------------------ 8. line refs

LINEREF_RE = re.compile(r"\b((?:mometa/[a-z]+/)?[A-Za-z_][A-Za-z0-9_]*\.py):(\d+)")


def check_linerefs(files):
    cache = {}

    def nlines(path):
        if path not in cache:
            try:
                with open(path) as fh:
                    cache[path] = sum(1 for _ in fh)
            except OSError:
                cache[path] = None
        return cache[path]

    for f in files:
        text = strip_output_blocks(open(f).read())
        for name, lineno in LINEREF_RE.findall(text):
            candidates = [os.path.join(SRC, name),
                          os.path.join(SRC, "utils", os.path.basename(name)),
                          os.path.join(DOCS, "_tools", os.path.basename(name))]
            path = next((c for c in candidates if os.path.exists(c)), None)
            if path is None:
                continue                     # not a source ref (e.g. generated.py)
            bump("linerefs")
            n = nlines(path)
            if n is None or int(lineno) > n:
                fail("linerefs", rel(f),
                     "%s:%s -- file has %s lines" % (name, lineno, n))


# ------------------------------------------------------------------- main

def main():
    files = docs_files()
    print("verifying %d markdown files under %s\n" % (len(files), rel(DOCS)))

    for fn in (check_syntax, check_imports, check_symbols, check_classes,
               check_props, check_signatures, check_links, check_linerefs):
        fn(files)

    order = ["syntax", "imports", "symbols", "classes", "props",
             "signatures", "links", "linerefs"]
    by_check = {}
    for check, where, msg in failures:
        by_check.setdefault(check, []).append((where, msg))

    for check in order:
        n = counts.get(check, 0)
        bad = len(by_check.get(check, []))
        status = "FAIL" if bad else "ok"
        print("%-11s %6d checked  %4d failed  %s" % (check, n, bad, status))

    if failures:
        print("\n%d FAILURES\n" % len(failures))
        for check in order:
            for where, msg in by_check.get(check, []):
                print("  [%s] %s: %s" % (check, where, msg))
        return 1

    print("\nall %d checks passed" % sum(counts.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
