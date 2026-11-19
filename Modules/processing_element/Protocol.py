"""Clock-accurate full-PE stimulus: mux -> MAC -> strapping.

The neighbor belongs to the MAC result, not to the next input operation.
The mux adds two clocks to the MAC's PIPELINE_STAGES clocks.
The final issue beat is at offset 0 (Direct/Local) or 1 (PreSum).
"""
from dataclasses import dataclass

PIPELINE_STAGES = 4
NEIGHBOR_DELAY = 2 + PIPELINE_STAGES

IDLE = {
    "rst_n": 1,
    "in_a": 0,
    "in_b": 0,
    "local_data": 0,
    "sel": 0,
    "sub_pre": 0,
    "issue_vld": 0,
    "ring_final": 0,
    "sub_post": 0,
    "in_id": 0,
    "neighbor_res": 0,
    "neighbor_vld": 0,
    "neighbor_id": 0,
}


@dataclass
class Direct:
    a: int = None
    b: int = None
    neighbor: int = None
    id: int = None
    ring_final: int = None
    sub_post: int = None
    issue: int = 1
    neighbor_vld: int = 1
    mismatch: int = 0

    def cycles(self):
        rows = [{} for _ in range(NEIGHBOR_DELAY + 1)]
        rows[0] = {
            "sel": 0, "in_a": self.a, "in_b": self.b,
            "issue_vld": self.issue, "in_id": self.id,
            "ring_final": self.ring_final, "sub_post": self.sub_post,
        }
        rows[NEIGHBOR_DELAY] = _neighbor(self)
        return rows


@dataclass
class Local:
    a: int = None
    local: int = None
    neighbor: int = None
    id: int = None
    ring_final: int = None
    sub_post: int = None
    issue: int = 1
    neighbor_vld: int = 1
    mismatch: int = 0

    def cycles(self):
        rows = [{} for _ in range(NEIGHBOR_DELAY + 1)]
        rows[0] = {
            "sel": 3, "in_a": self.a, "local_data": self.local,
            "issue_vld": self.issue, "in_id": self.id,
            "ring_final": self.ring_final, "sub_post": self.sub_post,
        }
        rows[NEIGHBOR_DELAY] = _neighbor(self)
        return rows


@dataclass
class PreSum:
    a: int = None
    b: int = None
    c: int = None
    sub_pre: int = None
    neighbor: int = None
    id: int = None
    ring_final: int = None
    sub_post: int = None
    neighbor_vld: int = 1
    mismatch: int = 0

    def cycles(self):
        rows = [{} for _ in range(NEIGHBOR_DELAY + 2)]
        rows[0] = {
            "sel": 1, "in_a": self.a, "in_b": self.b,
            "sub_pre": self.sub_pre, "issue_vld": 0,
        }
        rows[1] = {
            "sel": 2, "in_a": self.c, "sub_pre": self.sub_pre,
            "issue_vld": 1, "in_id": self.id,
            "ring_final": self.ring_final, "sub_post": self.sub_post,
        }
        rows[NEIGHBOR_DELAY + 1] = _neighbor(self)
        return rows


@dataclass
class Reset:
    length: int = 4
    no_overlap = True

    def cycles(self):
        return [{"rst_n": 0}] * self.length


def _neighbor(op):
    return {
        "neighbor_res": op.neighbor,
        "neighbor_vld": op.neighbor_vld,
        "neighbor_id": (op.id + op.mismatch) & 15,
    }


def packed_gap(ctx):
    """Start after the previous operation's input beat(s), not its neighbor.

    Generator calls gap rules before placing the next transaction. A prior
    Direct/Local occupies one input clock; PreSum occupies two.
    """
    if not ctx.history:
        return 0
    previous = ctx.history[-1]
    if isinstance(previous, (Direct, Local, PreSum)):
        return (2 if isinstance(previous, PreSum) else 1) - len(previous.cycles())
    return 0


def spaced_gap(ctx):
    return packed_gap(ctx) + ctx.rng.choice([0, 1, 2, 4])
