import asyncio
import ctypes
import os
import pytest
import subprocess

from zsp_be_sw.closure import Closure
from zsp_be_sw.model import Model
from zsp_be_sw.model_types import Signature
from zsp_be_sw.scheduler import Scheduler

tests_unit_dir = os.path.dirname(os.path.abspath(__file__))
model_ext_api_dir = os.path.join(tests_unit_dir, "data/model_ext_api")
proj_dir = os.path.abspath(os.path.join(tests_unit_dir, "../.."))
incdir = os.path.join(proj_dir, "src/include")
libdir = os.path.join(proj_dir, "build/lib")

def test_smoke_1(tmpdir):

    # First, compile the shared library
    cmd = [
        'gcc', '-g', '-shared', '-fPIC', '-o', os.path.join(tmpdir, "model.so"),
        os.path.join(model_ext_api_dir, "smoke_1.c"),
        "-I%s" % incdir,
        "-L%s" % libdir, "-lzsp-be-sw-rt",
        "-Wl,-rpath,%s" % libdir
    ]

    print("cmd: %s" % " ".join(cmd))

    ret = subprocess.run(cmd)

    assert ret.returncode == 0

    model = Model.load(os.path.join(tmpdir, "model.so"))
    assert model is not None

    assert "smoke_1" in model.actor_types

    def add(a, b):
        return a + b
    
    async def doit(a, b):
        pass

#    sched = Scheduler()
    actor = model.mk_actor("smoke_1")

    asyncio.run(actor.run())

#    asyncio.run(run())


#    rt_lib = ctypes.cdll.LoadLibrary(os.path.join(libdir, "libzsp-be-sw-rt.so"))
#    assert rt_lib is not None


    # def dflt(*args, **kwargs):
    #     print("dflt: args=%s, kwargs=%s" % (args, kwargs))

    # api = api_t()
    # api.print = type(api.print)(dflt)
    # api.add = type(api.add)(dflt)


#    print("actors: %s" % actors[0])
#    print("actors: %s" % actors[0].contents.name.decode())
#    print("actors: %s" % actors[0].contents.size)
#    print("actors: %s" % actors[0].contents.init)

#    actor_h = (ctypes.c_ubyte * actors[0].contents.size)()
#    actors[0].contents.init(ctypes.byref(actor_h), ctypes.byref(api))
#    print("actors: %s" % actors[0].name.decode())

def test_scope_linker_1():
    from zsp_be_sw.import_linker_scope import ImportLinkerScope

    _val = 0

    def my_method():
        nonlocal _val
        _val += 1

    linker = ImportLinkerScope()
    method : Closure = linker.get_closure(Signature.from_name_sig("my_method", "V"))
    assert method is not None

    assert _val == 0
    method.impl()
    assert _val == 1

def test_scope_linker_2():
    from zsp_be_sw.import_linker_scope import ImportLinkerScope

    class MyClass(object):
        def __init__(self):
            self._val = 0
            linker = ImportLinkerScope()
            method : Closure = linker.get_closure(Signature.from_name_sig("my_method", "V"))
            assert method is not None

            assert self._val == 0
            method.impl()
            assert self._val == 1

        def my_method(self):
            self._val += 1

    c = MyClass()


