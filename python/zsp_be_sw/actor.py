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
from .zsp_object_type_s import zsp_object_type_s

@dc.dataclass
class Actor(object):
    sched : Scheduler
    comp_t : ctypes.c_void_p
    action_t : ctypes.c_void_p
    api : ctypes.Structure
    hndl : ctypes.c_void_p = None
    thread : Thread = None
    _ev : asyncio.Event = dc.field(default_factory=asyncio.Event)

    def __post_init__(self):
        self.sched.add_actor(self)

    # def _do_work(self):
    #     print("--> _do_work", flush=True)
    #     # This is a placeholder for actual work that the actor might do
    #     # In a real implementation, this would likely involve calling methods
    #     # on the actor's API or performing some computation.
    #     print("<-- _do_work", flush=True)

    async def run(self, args=None):
        from .api import Api
        comp_t = ctypes.cast(self.comp_t, ctypes.POINTER(zsp_object_type_s))
        action_t = ctypes.cast(self.action_t, ctypes.POINTER(zsp_object_type_s))
        print("--> run.task", flush=True)

        print("comp: %s action: %s" % (
            comp_t.contents.name.decode(),
            action_t.contents.name.decode()), flush=True)

        api : Api = Api.inst()

        thread_h = api._zsp_actor_create(
            self.sched.hndl,
            ctypes.byref(self.api),
            self.comp_t,
            self.action_t
        )

        # TODO: Start actor (which initializes the thread)
#        actor_type_h : zsp_actor_type_t = Api.inst()._zsp_actor_type(self.hndl)
#        thread_h = actor_type_h.contents.run(
#            self.hndl, 
#            self.sched.hndl,
#            None)

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

   
    pass