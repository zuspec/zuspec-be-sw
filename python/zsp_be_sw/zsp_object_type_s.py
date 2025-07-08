import ctypes

class zsp_object_type_s(ctypes.Structure):
    _fields_ = [
        ("super", ctypes.c_void_p),
        ("name", ctypes.c_char_p),
    ]