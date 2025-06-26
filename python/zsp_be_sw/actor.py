import asyncio
import ctypes
import dataclasses as dc
import sys
from typing import Any, Callable, Dict
from .context import Context
from .scheduler import Scheduler
from .thread import Thread, zsp_thread_exit_f


@dc.dataclass
class Actor(object):
    sched : Scheduler
    api : ctypes.Structure
    hndl : ctypes.c_void_p
    thread : Thread = None
    _ev : asyncio.Event = dc.field(default_factory=asyncio.Event)
    _dflt_func_m : Dict[str, Callable] = dc.field(default_factory=dict)

    def __post_init__(self):
        self._dflt_func_m.update({
            "print": self._print
        })

    def start(self, args=None) -> asyncio.Task:
        return asyncio.Task(self.run(args))
    
    def _print(self, msg):
        sys.stdout.write(msg)

    async def run(self, args=None):
        print("--> run", flush=True)
        loop = asyncio.get_event_loop()

        self.sched.init_loop(loop)

        # TODO: Start actor (which initializes the thread)

        # Set thread-exit callback
        self.thread.set_exit_f(zsp_thread_exit_f(self._thread_end))

        # Wait for the actor to finish running
        await self._ev.wait()
        print("<-- run", flush=True)

    def _thread_end(self, thread_h):
        self._ev.set()

    def _default_func(self, name, *args):
        print("Default: %s")
        raise Exception("Unimplemented")

    def _default_task(self, name, *args):
        print("Default: %s")
        raise Exception("Unimplemented")

    def init_api(self, scope=None):
        for f in self.api._fields_:
            name = f[0]
            istask = getattr(f[1], "_istask_", False)

            impl = None

            # TODO: Search for an available implementation

            if impl is None and f[1] in self._dflt_func_m.keys():
                impl = self._dflt_func_m[f[1]]
            
            if impl is None:
                if istask:
                    def task_tramp(*args):
                        self._default_task(name, *args)
                    impl = task_tramp
                else:
                    def func_tramp(*args):
                        self._default_func(name, *args)
                    impl = func_tramp
            setattr(self.api, name, f[1](impl))
        pass
    pass