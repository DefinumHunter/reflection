"""Coverage across mux, MAC and output strapping in one PE."""
from Engine.Coverage import Cross, Op, Tag
from .Protocol import Direct, Local, PreSum, Reset, packed_gap


def mode(s):
    if isinstance(s.op, Direct):
        return "direct"
    if isinstance(s.op, Local):
        return "local"
    if isinstance(s.op, PreSum):
        return "pre_sum"
    return None


def valid(s):
    if isinstance(s.op, (Direct, Local)):
        return s.op.issue
    if isinstance(s.op, PreSum):
        return 1
    return None


def pre_sub(s):
    return s.op.sub_pre if isinstance(s.op, PreSum) else None


def neighbor(s):
    op = s.op
    if not isinstance(op, (Direct, Local, PreSum)):
        return None
    if isinstance(op, (Direct, Local)) and not op.issue:
        return None
    if not op.neighbor_vld:
        return "missing"
    return "wrong_id" if op.mismatch else "match"


def flags(s):
    op = s.op
    if not isinstance(op, (Direct, Local, PreSum)):
        return None
    if isinstance(op, (Direct, Local)) and not op.issue:
        return None
    return f"{op.ring_final}{op.sub_post}"


def ids(s):
    return s.op.id if isinstance(s.op, (Direct, Local, PreSum)) else None


def spacing(s):
    if not isinstance(s.op, (Direct, Local, PreSum)):
        return None
    if not isinstance(s.prev, (Direct, Local, PreSum)):
        return "gap"
    expected = (2 if isinstance(s.prev, PreSum) else 1) - len(s.prev.cycles())
    return "continuous" if s.gap == expected else "gap"


def reset_position(s):
    if not isinstance(s.op, Reset):
        return None
    return "after_op" if isinstance(s.prev, (Direct, Local, PreSum)) else "initial"


selection = Op("operand selection", ["direct", "local", "pre_sum"], of=mode, at_least=10)
issue = Op("issue valid", [0, 1], of=valid, at_least=5)
preop = Op("pre-sum operation", [0, 1], of=pre_sub, at_least=10)
neighbors = Op("neighbor case", ["match", "missing", "wrong_id"],
               of=neighbor, at_least=5)
side = Op("sideband combinations", ["00", "01", "10", "11"],
          of=flags, at_least=5)
id_point = Op("transaction id", list(range(1, 16)), of=ids, at_least=3)
gaps = Op("spacing", ["continuous", "gap"], of=spacing, at_least=10)
resets = Op("reset placement", ["initial", "after_op"], of=reset_position)
mux_arithmetic = Tag("mux pre-sum operation", ["sum_add", "sum_sub"], at_least=5)
mux_saturation = Tag("mux pre-sum saturation",
                     ["sum_sat_none", "sum_sat_pos", "sum_sat_neg"], at_least=5)
mac_rounding = Tag("MAC rounding",
                   ["round_down", "round_up", "round_tie_stay", "round_tie_up"],
                   at_least=3)
mac_saturation = Tag("MAC saturation", ["sat_none", "sat_pos", "sat_neg"], at_least=5)
post_operation = Tag("post operation", ["post_add", "post_sub"], at_least=5)
post_saturation = Tag("post saturation",
                      ["post_sat_none", "post_sat_pos", "post_sat_neg"], at_least=5)

POINTS = [
    selection, issue, preop, neighbors, side, id_point, gaps, resets,
    Cross(selection, issue),
    mux_arithmetic, mux_saturation, mac_rounding, mac_saturation,
    post_operation, post_saturation,
]
