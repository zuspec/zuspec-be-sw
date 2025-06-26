import ctypes
import dataclasses as dc
from typing import ClassVar

@dc.dataclass
class Context(object):
    alloc : ctypes.c_void_p = None
    sched : ctypes.c_void_p = None
    _librt : ClassVar[ctypes.CDLL] = None

    def __post_init__(self):
        rt = self.librt()
        if self.alloc is None:
            zsp_alloc_malloc_create = rt.zsp_alloc_malloc_create
            zsp_alloc_malloc_create.restype = ctypes.c_void_p
            self.alloc = zsp_alloc_malloc_create()
        if self.sched is None:
            zsp_scheduler_create = rt.zsp_scheduler_create
            zsp_scheduler_create.restype = ctypes.c_void_p
            zsp_scheduler_create.argtypes = [ctypes.c_void_p]
            self.sched = zsp_scheduler_create(self.alloc)
        pass

    @classmethod
    def librt(cls):
        if cls._librt is None:
            from zsp_be_sw import lib_rt
            cls._librt = ctypes.cdll.LoadLibrary(lib_rt())
        return cls._librt

