# 5. Filters

> The `filter_str` mini-language is undocumented upstream. This chapter documents it from
> the grammar in `ucscfilter.py`. Every XML result shown here was generated offline and
> matches the SDK's own test assertions.

```python
sps = handle.query_classid("LsServer",
                           filter_str='(usr_lbl, "prod", type="eq")')
```

Filters are accepted by **`query_classid`** and **`query_children`** only. `query_dn`,
`query_dns` and `query_classids` have no `filter_str` parameter.

## Seeing what a filter compiles to

You can develop filters with no server at all:

```python
from ucscsdk.ucscfilter import generate_infilter
from ucscsdk.ucscxmlcodec import to_xml_str

f = generate_infilter("LsServer", '(usr_lbl, "prod", type="eq")', True)
print(to_xml_str(f.to_xml()).decode())
# <filter><eq class="lsServer" property="usrLbl" value="prod" /></filter>
```

> Runs offline. Do this whenever a filter behaves unexpectedly.

Note `usr_lbl` became `usrLbl` — the Python name is translated to the wire name for you,
provided the third argument (`is_meta_class_id`) is `True`.

## Grammar

```
filter      := expression
expression  := term | 'not' expression | expression 'and' expression
                    | expression 'or' expression | '(' expression ')'
term        := '(' prop ',' value [',' 'type' '=' '"' TYPE '"']
                                  [',' 'flag' '=' '"' FLAG '"'] ')'
prop        := [A-Za-z0-9_]+          python property name
value       := '...' | "..." | bare-word-without-commas
TYPE        := re | eq | ne | gt | ge | lt | le
FLAG        := C | I
```

Precedence, tightest first: `not` → `and` → `or`.

## The default type is `re`, not `eq`

This is the single biggest gotcha.

```python
'(name, "test")'                  # → <wcard ...>   wildcard/regex match
'(name, "test", type="eq")'       # → <eq ...>      exact match
```

Verified:

```python
generate_infilter("LsServer", '(name, "test")', True)
# <filter><wcard class="lsServer" property="name" value="test" /></filter>
```

If you meant equality, **say `type="eq"`**. A bare `(name, "test")` matches anything
containing `test`.

## Filter types

| `type=` | XML | Meaning |
|---|---|---|
| `re` | `<wcard>` | wildcard / regex match — **the default** |
| `eq` | `<eq>` | equal |
| `ne` | `<ne>` | not equal |
| `gt` | `<gt>` | greater than |
| `ge` | `<ge>` | greater than or equal |
| `lt` | `<lt>` | less than |
| `le` | `<le>` | less than or equal |

Those seven are all the mini-language offers. The SDK has three more filter classes —
`BwFilter` (between), `AnybitFilter`, `AllbitsFilter` — which **cannot** be expressed in
`filter_str`. Build them directly; see [Beyond the mini-language](#beyond-the-mini-language).

## Case-insensitive matching

`flag="I"` rewrites each letter in the value into a two-character class:

```python
generate_infilter("LsServer", '(name, "test", type="eq", flag="I")', True)
# <filter><eq class="lsServer" property="name" value="[Tt][Ee][Ss][Tt]" /></filter>
```

The default is `flag="C"` (case-sensitive). Because the rewrite produces a regex-ish value,
`flag="I"` is most meaningful with `type="re"`; combined with `type="eq"` the server is
being asked to match that literal bracket expression.

## Combining conditions

```python
'(usr_lbl, "prod", type="eq") and (oper_state, "ok", type="eq")'
'(name, "web", type="eq") or (name, "app", type="eq")'
'not (dn, "org-root/ls-C1_B1", type="eq")'
```

Verified — this is assertion `test_001_not_filter` from the SDK's own test suite:

```python
generate_infilter("LsServer", 'not (dn,"org-root/ls-C1_B1", type="eq")', True)
# <filter><not><eq class="lsServer" property="dn" value="org-root/ls-C1_B1" /></not></filter>
```

Precedence in action — `and` binds tighter than `or`, so this parses as
`not( A or (B and not C) )`:

```python
filter_str = ('not((type, "instance", type="eq") or '
              '(usr_lbl, "lsserver", type="eq") and '
              'not(descr, "description", type="re"))')
```

compiles to

```xml
<filter>
  <not>
    <or>
      <eq class="lsServer" property="type" value="instance"/>
      <and>
        <eq class="lsServer" property="usrLbl" value="lsserver"/>
        <not><wcard class="lsServer" property="descr" value="description"/></not>
      </and>
    </or>
  </not>
</filter>
```

Parenthesise when you mean something else.

## Quoting

Values may be single-quoted, double-quoted, or bare:

```python
'(name, "web-01", type="eq")'
"(name, 'web-01', type='eq')"
'(name, web-01, type="eq")'      # bare — no commas allowed
```

Use quotes. A bare value stops at the first comma, which silently truncates anything
containing one.

Since the filter itself is a Python string containing quotes, pick the outer quote to avoid
escaping, or use a triple-quoted string for multi-line filters:

```python
filter_str = '''(name, "demo", type="eq") or
                ((name, "demo_1") and (name, "[0-9]_1"))'''
```

## Property names

Use the **Python** property name (`usr_lbl`), not the wire name (`usrLbl`). The translation
happens for you. An unknown name is not a friendly error:

```python
generate_infilter("LsServer", '(bogus_prop, "x", type="eq")', True)
# KeyError: 'bogus_prop'
```

Check first:

```python
from ucscsdk.mometa.ls.LsServer import LsServer
"usr_lbl" in LsServer.prop_meta      # True
```

## `is_meta_class_id`

The third argument to `generate_infilter`. `True` means "this class is in the SDK's
metadata, so translate property names". `False` skips translation and passes your property
name through untouched — which you want only for a class the SDK does not know.

The handle decides this for you: it looks the class id up and passes `True` if found. You
only care when calling `generate_infilter` yourself.

## Beyond the mini-language

For the three filter types with no grammar syntax, build the object directly:

```python
from ucscsdk.ucscfilter import create_basic_filter
from ucscsdk.ucscbasetype import FilterFilter

bw = create_basic_filter("BwFilter", class_="lsServer", property="name",
                         first_value="a", second_value="m")
in_filter = FilterFilter()
in_filter.child_add(bw)
```

> Runs offline.

Note the kwargs are **snake_case** (`first_value`, `second_value`) even though the XML
attributes are not. All 13 filter classes live in `ucscsdk.ucscfiltertype`:

`AllbitsFilter`, `AndFilter`, `AnybitFilter`, `BwFilter`, `EqFilter`, `GeFilter`,
`GtFilter`, `LeFilter`, `LtFilter`, `NeFilter`, `NotFilter`, `OrFilter`, `WcardFilter`.

They all end in `Filter`. Elsewhere you may see them referred to as `Eq`, `Wcard` and so
on — those names do not exist.

To use a hand-built filter, pass the element to a method factory function yourself; see
[15 — advanced](15-advanced.md).

## Very large filters

UCS Central limits how many components one filter may contain. `handle_filter_max_component_limit`
regroups an over-wide `And`/`Or` into nested groups of at most 10:

```python
from ucscsdk.ucscfilter import handle_filter_max_component_limit
smaller = handle_filter_max_component_limit(handle, big_or_filter)
```

It recurses until every level is within the limit. The `handle` argument is required but
unused. It only restructures `AndFilter`/`OrFilter`; anything else is returned unchanged.
You will rarely call this — it matters when generating filters from a long list of DNs.

## Common errors

**Filter matches too much** — you omitted `type="eq"` and got the default wildcard.

**`KeyError: 'some_prop'`** — the property name is not in the class's `prop_meta`. Check
spelling and use the Python name.

**`pyparsing.ParseException: Expected ...`** — malformed filter. Common causes: an
unsupported `type=` (only the seven above), a missing comma, unbalanced parentheses,
unbalanced quotes.

**Filter silently ignored** — passed to a method that has no `filter_str`
(`query_dn`, `query_dns`, `query_classids`), or to `query_children` without `class_id`.

**Value truncated at a comma** — an unquoted bare value. Quote it.

**`ImportError: No module named 'pyparsing'`** — `ucscfilter` is the only module needing it.
`pip install pyparsing`.

**A filter that works alone fails when combined** — precedence. `and` binds tighter than
`or`; add parentheses.
