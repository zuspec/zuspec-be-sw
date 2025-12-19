import pytest
import zuspec.dataclasses as zdc

def test_smoke(tmpdir):

    @zdc.dataclass
    class MyC(zdc.Component):

        async def run(self, amt : zdc.uint32_t):
            for _ in 

