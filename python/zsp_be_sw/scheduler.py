import asyncio
import ctypes
import dataclasses as dc
from typing import ClassVar
from .api import Api
from .thread import Thread, zsp_thread_exit_f

class zsp_scheduler_t(ctypes.Structure):
    _fields_ = [
        ("alloc", ctypes.c_void_p),
        ("next", ctypes.c_void_p),
        ("tail", ctypes.c_void_p),
        ("active", ctypes.c_int32),
    ]

@dc.dataclass
class Scheduler(object):
    alloc : ctypes.c_void_p = None
    hndl : ctypes.c_void_p = None
    loop = None
    actors : list = dc.field(default_factory=list)
    _ev : asyncio.Event = dc.field(default_factory=asyncio.Event)
    _running : bool = False
    _default : ClassVar = None


    def __post_init__(self):
        api = Api.inst()

        if self.alloc is None:
            self.alloc = api._zsp_alloc_malloc_create()
        if self.hndl is None:
            self.hndl = api._zsp_scheduler_create(self.alloc)

    def add_actor(self, actor):
        print("--> add_actor", flush=True)
        self.actors.append(actor)
        print("<-- add_actor", flush=True)

    def init_loop(self, loop):
        self.loop = loop

    def _idle(self, loop):
        print("--> idle", flush=True)
        api = Api.inst()
        sched = ctypes.cast( self.hndl, ctypes.POINTER(zsp_scheduler_t))

        print("active: %d" % sched.contents.active, flush=True)
        while sched.contents.active > 0:
            if api._zsp_scheduler_run(self.hndl) == 0:
                break

        self._ev.set()
#        loop.stop()
        print("<-- idle", flush=True)

    async def run_actor(self, actor):
        print("--> run_actor", flush=True)
        loop = asyncio.get_event_loop()
        sched = ctypes.cast(self.hndl, ctypes.POINTER(zsp_scheduler_t))

        ev = asyncio.Event()
        def thread_end(*args):
            nonlocal ev
            print("--> thread_end", flush=True)
            ev.set()
            print("<-- thread_end", flush=True)
        end_f = zsp_thread_exit_f(thread_end)
        actor.thread.set_exit_f(end_f)

        loop.call_soon(self._idle, loop)

        print("--> await ev.wait()", flush=True)
        await ev.wait()
        print("<-- await ev.wait()", flush=True)

    async def run_a(self):
        print("--> run_a", flush=True)
        loop = asyncio.get_event_loop()
        for i in range(20):
            loop.call_soon(self._idle, loop)
            print("--> run_a.loop.run_forever", flush=True)
            await self._ev.wait()
            self._ev.clear()
            print("<-- run_a.loop.run_forever", flush=True)
#        await self._ev.wait()
        print("<-- run_a", flush=True)
        pass

    def run(self):
        sched = ctypes.cast(
            self.hndl,
            ctypes.POINTER(zsp_scheduler_t))

        print("--> scheduler.run", flush=True)
        loop = asyncio.get_event_loop()
        for i in range(20):
            print("--> scheduler.run_forever", flush=True)
            asyncio.run(self.run_a())
        print("<-- scheduler.run_forever", flush=True)

        print("active: %d" % sched.contents.active, flush=True)

#        loop.run

        # TODO: how do we know when we're done?
        # - Keep looping 
        # TODO: 
        print("<-- scheduler.run", flush=True)
        pass

    @classmethod
    def default(cls):
        if cls._default is None:
            cls._default = Scheduler()
        return cls._default

    pass