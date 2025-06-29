import ctypes
import dataclasses as dc
from typing import Any
from .model_types import zsp_actor_type_t
from .api import Api
from .scheduler import Scheduler
from .thread import zsp_task_func

class zsp_actor_type_t(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("size", ctypes.c_size_t),
        ("init", ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)),
        ("run", ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)),
        ("dtor", ctypes.CFUNCTYPE(None, ctypes.c_void_p)),
    ]

@dc.dataclass
class ActorType(object):
    model : 'Model'
    info : zsp_actor_type_t

    def mk(self, sched : Scheduler, scope=None):
        from .actor import Actor
        hndl = (ctypes.c_ubyte * self.info.contents.size)()
        zsp_api = Api.inst()
        imp_api = self.model.api_t()
        self.info.contents.init(
            ctypes.byref(hndl),
            ctypes.byref(imp_api))
        actor = Actor(
            sched=sched,
            model=self.model,
            api=imp_api,
            hndl=hndl)

        actor.init_api(scope)

        return actor


    @property
    def name(self):
        return self.info.contents.name.decode()
    pass