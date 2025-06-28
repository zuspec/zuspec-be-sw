import asyncio
import ctypes
import dataclasses as dc
import sys
from typing import Any, Callable, Dict
from .actor_type import zsp_actor_type_t
from .api import Api
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
    _task = None

    def __post_init__(self):
        self._dflt_func_m.update({
            "print": self._print
        })
        self.sched.add_actor(self)

    def start(self, args=None):
        print("--> start.task", flush=True)
        self._task = asyncio.Task(self.run(args))
#        loop = asyncio.get_event_loop()
        loop.call_soon(self._start)
        print("<-- start.task", flush=True)
        return self._task
    
    def _start(self):
        loop = asyncio.get_event_loop()
        pass
    
    def _print(self, api_h, msg):
        print("--> _print", flush=True)
        sys.stdout.write(msg.decode())
        print("<-- _print", flush=True)

    def _do_work(self):
        print("--> _do_work", flush=True)
        # This is a placeholder for actual work that the actor might do
        # In a real implementation, this would likely involve calling methods
        # on the actor's API or performing some computation.
        print("<-- _do_work", flush=True)

    async def run(self, args=None):
        print("--> run.task", flush=True)
#        loop = asyncio.get_event_loop()

#        self.sched.init_loop(loop)

        # TODO: Start actor (which initializes the thread)
        actor_type_h : zsp_actor_type_t = Api.inst()._zsp_actor_type(self.hndl)
        thread_h = actor_type_h.contents.run(
            self.hndl, 
            self.sched.hndl,
            None)

        self.thread = Thread(thread_h)

        # Set thread-exit callback
#        self.thread.set_exit_f(zsp_thread_exit_f(self._thread_end))

#        print("--> run.schedule", flush=True)
#        loop.call_soon(self._do_work, None)
#        print("<-- run.schedule", flush=True)

        # Wait for the actor to finish running
        print("-- run.task", flush=True)
        await self.sched.run_actor(self)
        print("<-- run.task", flush=True)

    async def trigger_thread_end(self):
        print("--> trigger_thread_end", flush=True)
        self._ev.set()
        print("<-- trigger_thread_end", flush=True)

    def _thread_end(self, thread_h):
        print("--> _thread_end", flush=True)
        self._ev.set()
        print("<-- _thread_end", flush=True)

    def _default_func(self, name, *args):
        print("Default: %s" % name)
        raise Exception("Unimplemented: %s"% name)

    def _default_task(self, name, *args):
        print("Default: %s")
        raise Exception("Unimplemented: %s"% name)

    def init_api(self, scope=None):
        for f in self.api._fields_:
            name = f[0]
            istask = getattr(f[1], "_istask_", False)

            impl = None

            # TODO: Search for an available implementation

            if impl is None and name in self._dflt_func_m.keys():
                impl = self._dflt_func_m[name]
            
            if impl is None:
                print("Default: %s" % f[0])
                if istask:
                    def task_tramp(api, *args):
                        self._default_task(name, *args)
                    impl = task_tramp
                else:
                    def func_tramp(api, *args):
                        self._default_func(name, *args)
                    impl = func_tramp
            print("Setting %s to %s" % (name, impl))
            setattr(self.api, name, f[1](impl))
        pass
    pass