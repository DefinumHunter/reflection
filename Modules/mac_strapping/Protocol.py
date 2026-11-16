"""MAC input and neighbor response separated by MAC pipeline latency.

A transaction spans PIPELINE_STAGES+1 clocks. Neighbor data is driven
at the cycle where the MAC's registered output is sampled by strapping.
The default test targets PIPELINE_STAGES=4.
"""
from dataclasses import dataclass

PIPELINE_STAGES = 4

IDLE = {
    "rst_n": 1,
    "in_vld": 0,
    "in_a": 0,
    "in_b": 0,
    "in_id": 0,
    "in_ring_final": 0,
    "in_sub_post": 0,
    "neighbor_res": 0,
    "neighbor_vld": 0,
    "neighbor_id": 0,
}


@dataclass
class MacNeighbor:
    a: int = None
    b: int = None
    neighbor: int = None
    id: int = None
    ring_final: int = None
    sub_post: int = None
    vld: int = 1
    neighbor_vld: int = 1
    mismatch: int = 0

    def cycles(self):
        rows = [{} for _ in range(PIPELINE_STAGES + 1)]
        rows[0] = {
            "in_vld": self.vld,
            "in_a": self.a,
            "in_b": self.b,
            "in_id": self.id,
            "in_ring_final": self.ring_final,
            "in_sub_post": self.sub_post,
        }
        rows[PIPELINE_STAGES] = {
            "neighbor_res": self.neighbor,
            "neighbor_vld": self.neighbor_vld,
            "neighbor_id": (self.id + self.mismatch) & 15,
        }
        return rows


@dataclass
class Reset:
    length: int = 4
    no_overlap = True

    def cycles(self):
        return [{"rst_n": 0}] * self.length
