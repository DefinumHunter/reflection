"""Stimulus coverage and tags from both component golden models."""
from Engine.Coverage import Op, Tag, Cross
from .Protocol import MacNeighbor, Reset


def field(name):
    return lambda s: getattr(s.op, name) if isinstance(s.op, MacNeighbor) else None


def neighbor_case(s):
    op = s.op
    if not isinstance(op, MacNeighbor) or not op.vld:
        return None
    if not op.neighbor_vld:
        return "missing"
    return "wrong_id" if op.mismatch else "match"


def sidebands(s):
    op = s.op
    if not isinstance(op, MacNeighbor) or not op.vld:
        return None
    return f"{op.ring_final}{op.sub_post}"


def spacing(s):
    if not isinstance(s.op, MacNeighbor):
        return None
    return "no_gap" if s.gap == 0 else "gap"


def reset_position(s):
    if not isinstance(s.op, Reset):
        return None
    return "after_mac" if isinstance(s.prev, MacNeighbor) else "initial"


valid = Op("MAC input valid", [0, 1], of=field("vld"), at_least=5)
neighbor = Op("neighbor case", ["match", "missing", "wrong_id"],
              of=neighbor_case, at_least=5)
ring = Op("ring final", [0, 1], of=field("ring_final"), at_least=10)
sub = Op("post subtract", [0, 1], of=field("sub_post"), at_least=10)
side = Op("sideband combinations", ["00", "01", "10", "11"],
          of=sidebands, at_least=5)
ids = Op("transaction ID", list(range(1, 16)), of=field("id"), at_least=3)
gaps = Op("spacing", ["no_gap", "gap"], of=spacing, at_least=5)
resets = Op("reset placement", ["initial", "after_mac"], of=reset_position)
rounding = Tag("MAC rounding",
               ["round_down", "round_up", "round_tie_stay", "round_tie_up"],
               at_least=3)
mac_sat = Tag("MAC saturation", ["sat_none", "sat_pos", "sat_neg"], at_least=5)
post_op = Tag("post operation", ["post_add", "post_sub"], at_least=5)
post_sat = Tag("post saturation",
               ["post_sat_none", "post_sat_pos", "post_sat_neg"], at_least=5)

POINTS = [
    valid, neighbor, ring, sub, side, ids, gaps, resets,
    Cross(ring, sub), rounding, mac_sat, post_op, post_sat,
]
