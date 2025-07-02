import asyncio
import ctypes
import dataclasses as dc
import sys
from typing import Any, Callable, Dict
from .actor_type import zsp_actor_type_t
from .api import Api
from .closure import Closure, TaskClosure
from .context import Context
from .import_linker import ImportLinker
from .scheduler import Scheduler
from .thread import Thread, zsp_thread_exit_f
from .model_types import Signature

@dc.dataclass
class Actor(object):
    sched : Scheduler
    model : 'Model'
    api : ctypes.Structure
    hndl : ctypes.c_void_p
    thread : Thread = None
    _ev : asyncio.Event = dc.field(default_factory=asyncio.Event)
    _dflt_func_m : Dict[str, Callable] = dc.field(default_factory=dict)
    _task = None

    def __post_init__(self):
        self._dflt_func_m.update({
            "print": self._print,
            "message": self._message,
        })
        self.sched.add_actor(self)

    def _print(self, msg):
        sys.stdout.write(msg.decode())

    def _message(self, level, msg):
        sys.stdout.write(msg.decode())

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

        self.thread = Thread(thread_h, self.sched)

        # Wait for the actor to finish running
        if self.thread.alive:
            await self.sched.run_actor(self)

        # TODO: clean up?
        print("-- Thread is done")
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

    def init_api(self, linker : ImportLinker):
        i = 0
        for sig in self.model.signatures:
            name = sig.name
            print("name: %s, istask: %s" % (name, sig.istask), flush=True)

            impl = None

            # TODO: Search for an available implementation

            if impl is None and name in self._dflt_func_m.keys():
                if sig.istask:
                    impl = TaskClosure(
                        sig, 
                        self._dflt_func_m[name], 
                        self.sched)
                else:
                    impl = Closure(sig, self._dflt_func_m[name])
            
            if impl is None:
                impl = linker.get_closure(sig)

            if impl is None:
                raise Exception("No implementation found for %s" % name)

            setattr(self.api, name, sig.ftype(impl.func))
        pass
    pass