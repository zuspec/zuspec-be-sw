import asyncio
import ctypes
import dataclasses as dc
from .api import Api

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
    sched : ctypes.c_void_p = None
    loop = None

    def __post_init__(self):
        api = Api.inst()

        if self.alloc is None:
            self.alloc = api._zsp_alloc_malloc_create()
        if self.sched is None:
            self.sched = api._zsp_scheduler_create(self.alloc)

    def init_loop(self, loop):
        self.loop = loop

    async def _idle(self, loop):
        print("--> idle", flush=True)
        loop.stop()
        print("<-- idle", flush=True)

    async def run_a(self):
        pass

    def run(self):
        sched = ctypes.cast(
            self.sched,
            ctypes.POINTER(zsp_scheduler_t))

        print("--> scheduler.run", flush=True)
        loop = asyncio.get_event_loop()
        loop.call_later(0.0, self._idle(loop))
        loop.run_until_complete(self.run_a())

        print("active: %d" % sched.contents.active)

        loop.run

        # TODO: how do we know when we're done?
        # - Keep looping 
        # TODO: 
        print("<-- scheduler.run", flush=True)
        pass

    pass