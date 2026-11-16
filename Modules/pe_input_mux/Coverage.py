"""Functional coverage of input selection, pre-sum arithmetic and sidebands."""
from Engine.Coverage import Op, Tag, Cross
from .Protocol import Direct, Local, PreSum, Reset

def mode(sample):
    op = sample.op
    if isinstance(op, Direct):
        return "direct"
    if isinstance(op, Local):
        return "local"
    if isinstance(op, PreSum):
        return "pre_sum"
    return None

def issue(sample):
    op = sample.op
    if isinstance(op, (Direct, Local)):
        return op.issue
    if isinstance(op, PreSum):
        return 1
    return None

def sub_pre(sample):
    return sample.op.sub_pre if isinstance(sample.op, PreSum) else None

def flags(sample):
    op = sample.op
    if not isinstance(op, (Direct, Local, PreSum)):
        return None
    if isinstance(op, (Direct, Local)) and not op.issue:
        return None
    return f"{op.ring_final}{op.sub_post}"

def ids(sample):
    op = sample.op
    return op.id if isinstance(op, (Direct, Local, PreSum)) else None

def spacing(sample):
    return ("continuous" if sample.gap == 0 else "gap") if isinstance(
        sample.op, (Direct, Local, PreSum)) else None

def reset_position(sample):
    if not isinstance(sample.op, Reset):
        return None
    return "after_op" if isinstance(sample.prev, (Direct, Local, PreSum)) else "initial"

selection = Op("operand selection", ["direct", "local", "pre_sum"], of=mode, at_least=10)
valid = Op("issue valid", [0, 1], of=issue, at_least=5)
preop = Op("pre-sum operation", [0, 1], of=sub_pre, at_least=10)
side = Op("sideband combinations", ["00", "01", "10", "11"], of=flags, at_least=5)
id_point = Op("transaction id", list(range(1, 16)), of=ids, at_least=3)
gaps = Op("spacing", ["continuous", "gap"], of=spacing, at_least=10)
resets = Op("reset placement", ["initial", "after_op"], of=reset_position)
arithmetic = Tag("pre-sum operation executed", ["sum_add", "sum_sub"], at_least=5)
saturation = Tag("pre-sum saturation", ["sum_sat_none", "sum_sat_pos", "sum_sat_neg"], at_least=5)

POINTS = [selection, valid, preop, side, id_point, gaps, resets,
          Cross(selection, valid), arithmetic, saturation]
