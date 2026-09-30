"""pe_mac_wrapper transactions and how each one looks in clocks.

Every operation loads the mux in one or two clocks and issues on the next
clock; the MAC result comes out 1 + PIPELINE_STAGES clocks after the issue.
id 0 is reserved for "no transaction", real operations use 1..15.
"""
from dataclasses import dataclass

from Components.MuxNode import LOAD_AB, LOAD_SUM, USE_LOCAL, USE_SUM

# A clock nobody drives: nothing issued, id 0. sel=LOAD_SUM is the only mode
# that leaves mux1/mux2 alone (it rewrites sum1/sum2, which every sum
# operation loads for itself right before using).
IDLE = dict(rst_n=1, local_data=0, sub=0, in_a=0, in_b=0,
            sel=LOAD_SUM, in_id=0, issue_vld=0, mac_sel_in=0)


@dataclass
class Reset:
    length: int = 5
    no_overlap = True          # a load under reset would be lost

    def cycles(self):
        return [dict(rst_n=0)] * self.length


@dataclass
class MulAB:
    """a * b"""
    a: int = None
    b: int = None
    id: int = None
    mac_sel: int = None

    def cycles(self):
        return [dict(sel=LOAD_AB, in_a=self.a, in_b=self.b, in_id=self.id),
                dict(issue_vld=1, mac_sel_in=self.mac_sel)]


@dataclass
class MulSum:
    """c * (a + b), or c * (a - b) when sub = 1; the sum saturates first."""
    a: int = None
    b: int = None
    c: int = None
    sub: int = None
    id: int = None
    mac_sel: int = None

    def cycles(self):
        return [dict(sel=LOAD_SUM, in_a=self.a, in_b=self.b),
                dict(sel=USE_SUM, in_a=self.c, sub=self.sub, in_id=self.id),
                dict(issue_vld=1, mac_sel_in=self.mac_sel)]


@dataclass
class MulLocal:
    """a * local"""
    a: int = None
    local: int = None
    id: int = None
    mac_sel: int = None

    def cycles(self):
        return [dict(sel=USE_LOCAL, in_a=self.a, local_data=self.local, in_id=self.id),
                dict(issue_vld=1, mac_sel_in=self.mac_sel)]
