"""Single-cycle MAC/neighbor input beats; raw unsigned port bits."""
from dataclasses import dataclass

IDLE = {
    "rst_n": 1, "mac_res": 0, "mac_vld": 0, "mac_id": 0,
    "mac_ring_final": 0, "mac_sub_post": 0,
    "neighbor_res": 0, "neighbor_vld": 0, "neighbor_id": 0,
}

@dataclass
class Beat:
    mac: int = None
    neighbor: int = None
    vld: int = 1
    id: int = None
    ring_final: int = None
    sub_post: int = None
    neighbor_vld: int = 1
    # 0: matching ID, 1: mismatching ID. Generated explicitly rather than
    # using independent IDs, to guarantee both neighbor-check outcomes.
    mismatch: int = 0

    def cycles(self):
        neighbor_id = (self.id + (1 if self.mismatch else 0)) & 15
        return [{
            "mac_res": self.mac, "neighbor_res": self.neighbor,
            "mac_vld": self.vld, "mac_id": self.id,
            "mac_ring_final": self.ring_final, "mac_sub_post": self.sub_post,
            "neighbor_vld": self.neighbor_vld, "neighbor_id": neighbor_id,
        }]

@dataclass
class Reset:
    length: int = 3
    no_overlap = True

    def cycles(self):
        return [{"rst_n": 0}] * self.length
