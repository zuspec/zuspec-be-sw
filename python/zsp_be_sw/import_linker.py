import dataclasses as dc
from .closure import Closure
from .model_types import Signature

@dc.dataclass
class ImportLinker(object):

    def get_closure(self, method : Signature) -> Closure:
        raise NotImplementedError("ImportLinker.get_closure() must be implemented by subclasses")