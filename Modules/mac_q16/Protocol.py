"""Transactions for the current mac_q16 interface (one operation per cycle)."""
from dataclasses import dataclass

# Every TB input except clk. An idle cycle never launches a valid product.
IDLE = {
    "rst_n": 1,
    "in_vld": 0,
    "in_a": 0,
    "in_b": 0,
    "in_id": 0,
    "in_ring_final": 0,
    "in_sub_post": 0,
}


@dataclass
class Mac:
    """One pipeline input beat; invalid beats also exercise bubble propagation."""
    a: int = None
    b: int = None
    vld: int = None
    id: int = None
    ring_final: int = None
    sub_post: int = None

    def cycles(self):
        return [{
            "in_vld": self.vld,
            "in_a": self.a,
            "in_b": self.b,
            "in_id": self.id,
            "in_ring_final": self.ring_final,
            "in_sub_post": self.sub_post,
        }]


@dataclass
class Reset:
    """Synchronous active-low reset; only valid pipeline is reset in RTL."""
    length: int = 4
    no_overlap = True

    def cycles(self):
        return [{"rst_n": 0}] * self.length
