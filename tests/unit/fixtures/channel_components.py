"""
Channel component fixtures for ChannelPortLowerPass tests.

Must live in a file so inspect.getsource() works.
"""
import zuspec.dataclasses as zdc
from zuspec.dataclasses.tlm import Channel, GetIF, PutIF


@zdc.dataclass
class Producer(zdc.Component):
    out_ch: Channel[zdc.bit32] = zdc.output()


@zdc.dataclass
class Consumer(zdc.Component):
    in_ch: Channel[zdc.bit32] = zdc.input()
