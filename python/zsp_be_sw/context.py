import dataclasses as dc
from .scheduler import Scheduler

@dc.dataclass
class Context(object):
    sched : Scheduler = None

    def __post_init__(self):
        if self.sched is None:
            self.sched = Scheduler()


