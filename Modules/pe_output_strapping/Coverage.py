"""Input protocol and arithmetic coverage for the CHECK_NEIGHBOR=1 run.

CHECK_NEIGHBOR=0 is an additional parameter run: mismatch stimuli are then
intentionally accepted; the scoreboard still checks that behavior.
"""
from Engine.Coverage import Op, Tag, Cross
from .Protocol import Beat, Reset

def valid(s):
    return s.op.vld if isinstance(s.op, Beat) else None

def neighbor_case(s):
    op = s.op
    if not isinstance(op, Beat) or not op.vld:
        return None
    if not op.neighbor_vld:
        return "missing"
    return "wrong_id" if op.mismatch else "match"

def routing(s):
    op = s.op
    return op.ring_final if isinstance(op, Beat) and op.vld else None

def operation(s):
    op = s.op
    return op.sub_post if isinstance(op, Beat) and op.vld else None

def sidebands(s):
    op = s.op
    return f"{op.ring_final}{op.sub_post}" if isinstance(op, Beat) and op.vld else None

def ids(s):
    return s.op.id if isinstance(s.op, Beat) and s.op.vld else None

def spacing(s):
    return ("continuous" if s.gap == 0 else "gap") if isinstance(s.op, Beat) else None

def reset_position(s):
    if not isinstance(s.op, Reset):
        return None
    return "after_beat" if isinstance(s.prev, Beat) else "initial"

vld = Op("mac valid", [0, 1], of=valid, at_least=10)
neighbor = Op("neighbor check cases", ["match", "missing", "wrong_id"],
              of=neighbor_case, at_least=5)
route = Op("ring final", [0, 1], of=routing, at_least=10)
sub = Op("post subtract", [0, 1], of=operation, at_least=10)
flags = Op("sideband combinations", ["00", "01", "10", "11"], of=sidebands, at_least=5)
ident = Op("transaction id", list(range(1, 16)), of=ids, at_least=3)
gaps = Op("spacing", ["continuous", "gap"], of=spacing, at_least=10)
resets = Op("reset placement", ["initial", "after_beat"], of=reset_position)
arithmetic = Tag("post operation", ["post_add", "post_sub"], at_least=5)
saturation = Tag("post saturation", ["post_sat_none", "post_sat_pos", "post_sat_neg"],
                 at_least=5)

POINTS = [vld, neighbor, route, sub, flags, ident, gaps, resets,
          Cross(route, sub), arithmetic, saturation]
