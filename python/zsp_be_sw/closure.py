import asyncio
import ctypes
import dataclasses as dc
from typing import Any, Callable, Dict
from .api import Api
from .scheduler import Scheduler
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
    sched : ctypes.c_void_p = None
    thread : ctypes.c_void_p = None
    api : Any = None
    args : Any = None

    async def body(self):
        print("body")
        try:
            ret = await self.impl(*self.args)

            if ret is None:
                ret = 0

            # Sets the return value
            api = Api.inst()
            api._zsp_thread_return(self.thread, ret)
            api._zsp_thread_schedule(self.sched, self.thread)
        except Exception as e:
            print("Exception in TaskClosure.body: %s" % e, flush=True)
        pass

    def func(self, thread, idx, args):
        api = Api.inst()
        print("TaskClosure.func: thread=%s, idx=%s, args=%s" % (thread, idx, args), flush=True)

        # Save this so we can complete the task call later
        self.thread = thread
        self.sched = api._zsp_thread_scheduler(thread)

        # TODO:
        self.args = []

        try:
            # First argument is always the API class. Ignore
            for i,pt in enumerate(self.sig.ptypes):
                val = api._zsp_thread_va_arg(args, ctypes.sizeof(pt))
                if i:
                    if pt == ctypes.c_char_p:
                        # TODO: convert to string
                        pass
                    self.args.append(val)
        except Exception as e:
            print("Exception in TaskClosure.func: %s" % e, flush=True)

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
