"""Functional coverage: stimuli plus arithmetic branches from the golden."""
from Engine.Coverage import Cross, Op, Tag
from .Protocol import Mac, Reset


def field(name):
    return lambda sample: getattr(sample.op, name) if isinstance(sample.op, Mac) else None


def sideband(sample):
    op = sample.op
    if not isinstance(op, Mac) or op.vld != 1:
        return None
    return f"{op.ring_final}{op.sub_post}"


def gap_class(sample):
    if not isinstance(sample.op, Mac):
        return None
    return "back_to_back" if sample.gap == 0 else "with_gap"


def reset_position(sample):
    if not isinstance(sample.op, Reset):
        return None
    return "after_mac" if isinstance(sample.prev, Mac) else "initial"


valid = Op("input valid", [0, 1], of=field("vld"), at_least=10)
ring = Op("ring final", [0, 1], of=field("ring_final"), at_least=10)
sub = Op("sub post", [0, 1], of=field("sub_post"), at_least=10)
ids = Op("transaction id", list(range(1, 16)), of=field("id"), at_least=3)
side = Op("valid sideband combinations", ["00", "01", "10", "11"], of=sideband, at_least=5)
gaps = Op("spacing", ["back_to_back", "with_gap"], of=gap_class, at_least=10)
resets = Op("reset placement", ["initial", "after_mac"], of=reset_position)

rounding = Tag(
    "rounding",
    ["round_down", "round_up", "round_tie_stay", "round_tie_up"],
    at_least=5,
)
saturation = Tag(
    "saturation",
    ["sat_none", "sat_pos", "sat_neg"],
    at_least=5,
)

POINTS = [
    valid, ring, sub, ids, side, gaps, resets,
    Cross(ring, sub),
    rounding, saturation,
]
