import ctypes
import dataclasses as dc
from .zsp_object_type_s import zsp_object_type_s

@dc.dataclass
class CompT(object):
    name : str
    hndl : ctypes.c_void_p

    @staticmethod
    def mk(hndl):
        comp_t = ctypes.cast(hndl, ctypes.POINTER(zsp_object_type_s))
        return CompT(comp_t.contents.name.decode(), hndl)
