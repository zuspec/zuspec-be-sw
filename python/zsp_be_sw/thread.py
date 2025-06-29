
import ctypes
import dataclasses as dc
from .api import Api

zsp_task_func = ctypes.CFUNCTYPE(
    ctypes.c_void_p, 
    ctypes.c_void_p, 
    ctypes.c_int,
    ctypes.c_void_p)

class zsp_thread_prev_next_t(ctypes.Structure):
    _fields_ = [
        ("prev", ctypes.c_void_p),
        ("next", ctypes.c_void_p)
    ]

zsp_thread_exit_f = ctypes.CFUNCTYPE(None, ctypes.c_void_p)

class zsp_thread_t(ctypes.Structure):
    _fields_ = [
        ("group", zsp_thread_prev_next_t),
        ("exit_f", zsp_thread_exit_f),
        ("leaf", ctypes.c_void_p)
    ]

@dc.dataclass
class Thread(object):
    hndl : ctypes.POINTER
    sched : 'Scheduler'

    def set_exit_f(self, func : ctypes.CFUNCTYPE):
        hndl = ctypes.cast(self.hndl, ctypes.POINTER(zsp_thread_t))
        hndl.contents.exit_f = func

    @property
    def alive(self):
        hndl = ctypes.cast(self.hndl, ctypes.POINTER(zsp_thread_t))
        return hndl.contents.leaf is not None
    
    def thread_return(self, ret):
        api = Api.inst()
        print("--> zsp_thread_return", flush=True)
        api._zsp_thread_return(self.hndl, ret)
        print("<-- zsp_thread_return", flush=True)
        print("--> zsp_thread_schedule", flush=True)
        api._zsp_thread_schedule(self.sched.hndl, self.hndl)
        print("<-- zsp_thread_schedule", flush=True)

    def alloc_frame(self, sz) -> ctypes.c_void_p:
        api = Api.inst()
#        return api.