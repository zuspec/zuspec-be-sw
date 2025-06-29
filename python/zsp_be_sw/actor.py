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
from .model_types import Signature

@dc.dataclass
class Closure(object):
    sig : Signature
    impl : Callable

    def func(self, api, *args):
        # TODO: convert arguments (eg ctypes.c_char_p) if needed
        ret = self.impl(*args)

        # TODO: convert return (eg ctypes.c_char_p) if needed

        return ret
    
@dc.dataclass
class TaskClosure(Closure):
    sched : Scheduler
    thread : ctypes.c_void_p = None
    api : Any = None
    args : Any = None

    async def body(self):
        print("body")
#        ret = await self.impl(self.api, *self.args)
        ret = 1

        # Sets the return value
        api = Api.inst()
        print("--> zsp_thread_return", flush=True)
        api._zsp_thread_return(self.thread, ret)
        print("<-- zsp_thread_return", flush=True)
        print("--> zsp_thread_schedule", flush=True)
        api._zsp_thread_schedule(self.sched.hndl, self.thread)
        print("<-- zsp_thread_schedule", flush=True)
        pass

    def func(self, thread, idx, args):
        api = Api.inst()
        print("TaskClosure.func: thread=%s, idx=%s, args=%s" % (thread, idx, args), flush=True)

        # Save this so we can complete the task call later
        self.thread = thread
        # Create a frame for the call
        ret = api._zsp_thread_alloc_frame(thread, 0, None)
        # Extract built-in arguments
        # - API
        # Use signature to extract user arguments
        # Use the event look to start the body
        loop = asyncio.get_event_loop()
        loop.create_task(self.body())

#        self.api = api
#        self.args = tuple(*args)
        return ret

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
            "print": self._print
        })
        self.sched.add_actor(self)

    def _print(self, msg):
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

    def init_api(self, scope=None):
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
                if sig.istask:
                    impl = TaskClosure(
                        sig, 
                        self._default_task,
                        self.sched)
                else:
                    impl = Closure(self._default_func, name)

            setattr(self.api, name, sig.ftype(impl.func))
        pass
    pass