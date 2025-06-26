
import ctypes

type_m = {
    'c': ctypes.c_int8,
    'C': ctypes.c_uint8,
    's': ctypes.c_int16,
    'S': ctypes.c_uint16,
    'i': ctypes.c_int,
    'I': ctypes.c_uint,
    'u': ctypes.c_long,
    'U': ctypes.c_ulong,
    'V': None,
    'h': ctypes.c_void_p
}

def mk_signature(sig):
    fname = None
    ftype = None
    rtype = None
    ptypes = [ctypes.c_void_p]
    istask = False

    i = 0
    while i < len(sig):
        if sig[i].isnumeric():
            # Have a name
            len_s = ""
            while sig[i].isnumeric():
                len_s += sig[i]
                i += 1
            name = sig[i:i+int(len_s)]
            i += int(len_s)
            if fname is None:
                fname = name
                if i < len(sig) and sig[i] == 'T':
                    istask = True
                    i += 1
            else:
                # TODO: handle struct type
                pass
        elif sig[i] in type_m.keys():
            t = type_m[sig[i]]
            if rtype is None:
                rtype = t
            else:
                ptypes.append(t)
            i += 1
        else:
            raise Exception("Internal error: invalid character in signature: %s" % sig[i])

    ftype = ctypes.CFUNCTYPE(rtype, *ptypes)
    setattr(ftype, "_istask_", istask)

    return (fname, istask, ftype)

class zsp_actor_type_t(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("size", ctypes.c_uint32),
        ("init", ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)),
        # TODO: dtor
    ]
