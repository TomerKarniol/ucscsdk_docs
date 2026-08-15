"""In-memory `nose` shim so the SDK's offline unit tests can be executed.

The SDK's test suite imports `nose`, which is dead upstream and uninstallable on
Python 3.12 (it breaks on collections.Callable). Without this, 24 of 26 test modules
fail at collection and the suite yields no signal at all.

This registers fake `nose` modules in sys.modules. Nothing on disk is modified and
the SDK clone is not touched. Load it as a pytest plugin:

    PYTHONPATH=docs/_tools /usr/bin/python3 -m pytest -p nose_shim <offline modules>

Only the hardware-free modules can run; anything importing tests/connection/info.py
calls custom_setup() and blocks trying to reach 192.168.1.1.
"""
import sys, types, unittest

class _TC(unittest.TestCase):
    def runTest(self): pass
_tc = _TC()
_tc.maxDiff = None

def _camel(snake):
    # nose exposes unittest asserts as snake_case: assert_equal -> assertEqual
    head, _, tail = snake.partition('_')
    parts = tail.split('_')
    return head + ''.join(p.title() for p in parts)

def _mk(name):
    target = getattr(_tc, _camel(name))
    def f(*a, **k): return target(*a, **k)
    return f

tools = types.ModuleType("nose.tools")
for n in ["assert_equal","assert_not_equal","assert_true","assert_false","assert_raises",
          "assert_in","assert_not_in","assert_is_none","assert_is_not_none",
          "assert_almost_equal","assert_list_equal","assert_dict_equal"]:
    setattr(tools, n, _mk(n))
tools.ok_ = _mk("assertTrue"); tools.eq_ = _mk("assertEqual")
def raises(*exc):
    def deco(fn):
        def wrapper(*a, **k):
            try: fn(*a, **k)
            except exc: return
            raise AssertionError("%s not raised" % (exc,))
        wrapper.__name__ = fn.__name__
        return wrapper
    return deco
tools.raises = raises
def with_setup(setup=None, teardown=None):
    def deco(fn):
        fn.setup = setup; fn.teardown = teardown
        return fn
    return deco
tools.with_setup = with_setup
def istest(fn): return fn
def nottest(fn): return fn
tools.istest = istest; tools.nottest = nottest
tools.timed = lambda *a, **k: (lambda fn: fn)
tools.set_trace = lambda *a, **k: None

nose = types.ModuleType("nose"); nose.tools = tools
plugins = types.ModuleType("nose.plugins")
skip = types.ModuleType("nose.plugins.skip")
class SkipTest(Exception): pass
skip.SkipTest = SkipTest
attrib = types.ModuleType("nose.plugins.attrib")
def attr(*a, **k):
    def deco(fn): return fn
    return deco
attrib.attr = attr
plugins.skip = skip; plugins.attrib = attrib; nose.plugins = plugins
for name, mod in [("nose",nose),("nose.tools",tools),("nose.plugins",plugins),
                  ("nose.plugins.skip",skip),("nose.plugins.attrib",attrib)]:
    sys.modules[name] = mod
