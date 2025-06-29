import ctypes
import dataclasses as dc
from typing import ClassVar

@dc.dataclass
class Api(object):
    _inst : ClassVar = None
    _librt : ctypes.CDLL = None
    _zsp_alloc_malloc_create = None
    _zsp_scheduler_create = None
    _zsp_scheduler_run = None
    _zsp_actor_start = None
    _zsp_actor_type = None
    _zsp_thread_alloc_frame = None
    _zsp_thread_return = None
    _zsp_thread_schedule = None
    _zsp_thread_scheduler = None
    _zsp_thread_va_arg = None

    def __post_init__(self):
        from zsp_be_sw import lib_rt
        from .actor_type import zsp_actor_type_t

        self._librt = ctypes.cdll.LoadLibrary(lib_rt())
        rt = self._librt

        self._zsp_alloc_malloc_create = rt.zsp_alloc_malloc_create
        self._zsp_alloc_malloc_create.restype = ctypes.c_void_p

        self._zsp_scheduler_create = rt.zsp_scheduler_create
        self._zsp_scheduler_create.argtypes = [ctypes.c_void_p]
        self._zsp_scheduler_create.restype = ctypes.c_void_p

        self._zsp_scheduler_run = rt.zsp_scheduler_run
        self._zsp_scheduler_run.restype = ctypes.c_int32
        self._zsp_scheduler_run.argtypes = [ctypes.c_void_p]

        self._zsp_actor_type = rt.zsp_actor_type
        self._zsp_actor_type.restype = ctypes.POINTER(zsp_actor_type_t)

        self._zsp_thread_alloc_frame = rt.zsp_thread_alloc_frame
        self._zsp_thread_alloc_frame.restype = ctypes.c_void_p
        self._zsp_thread_alloc_frame.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]

        self._zsp_thread_return = rt.zsp_thread_return
        self._zsp_thread_return.restype = ctypes.c_void_p
        self._zsp_thread_return.argtypes = [ctypes.c_void_p, ctypes.c_uint64]

        self._zsp_thread_schedule = rt.zsp_thread_schedule
        self._zsp_thread_schedule.restype = None
        self._zsp_thread_schedule.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        self._zsp_thread_scheduler = rt.zsp_thread_scheduler
        self._zsp_thread_scheduler.restype = ctypes.c_void_p
        self._zsp_thread_scheduler.argtypes = [ctypes.c_void_p]

        self._zsp_thread_va_arg = rt.zsp_thread_va_arg
        self._zsp_thread_va_arg.restype = ctypes.c_uint64
        self._zsp_thread_va_arg.argtypes = [ctypes.c_void_p, ctypes.c_size_t]

    @classmethod
    def inst(cls):
        if cls._inst is None:
            cls._inst = Api()
        return cls._inst



    @classmethod
    def inst(cls):
        if cls._inst is None:
            cls._inst = Api()
        return cls._inst

