import dataclasses as dc
from typing import Any
from .model_types import zsp_actor_type_t
from .actor import Actor
from .context import Context

@dc.dataclass
class ActorType(object):
    api_t : Any
    info : zsp_actor_type_t

    def mk(self, ctxt : Context=None):
        pass

    @property
    def name(self):
        return self.info.contents.name.decode()
    pass