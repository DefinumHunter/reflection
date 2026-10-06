"""What counts as "tested" for mac_q16.

    stimulus  what was sent: vld, sel, corner values, reset in the stream
    behaviour what the multiplier did, reported by the golden as tags:
              which rounding branch, which saturation branch
"""
from Engine.Coverage import Cross, Op, Tag
from .Protocol import Mac, Reset
from .Scenario import CORNERS


def _mac(field):
    return lambda s: getattr(s.op, field) if isinstance(s.op, Mac) else None


def _corner(field):
    def of(s):
        v = getattr(s.op, field, None)
        return f"{v:#010x}" if isinstance(s.op, Mac) and v in CORNERS else None
    return of


def _reset(s):
    if not isinstance(s.op, Reset):
        return None
    return "mid stream" if isinstance(s.prev, Mac) else "at start"


vld = Op("vld", [0, 1], of=_mac("vld"))
sel = Op("sel", [0, 1], of=_mac("sel"))
a_corner = Op("a corner", [f"{c:#010x}" for c in CORNERS], of=_corner("a"))
b_corner = Op("b corner", [f"{c:#010x}" for c in CORNERS], of=_corner("b"))
reset = Op("reset", ["at start", "mid stream"], of=_reset)

# tags from Components/MacNode.py, only for multiplies with in_vld = 1
rounding = Tag("rounding", ["round_down", "round_up", "round_tie_stay", "round_tie_up"],
               at_least=20)
saturation = Tag("saturation", ["sat_none", "sat_pos", "sat_neg"], at_least=20)

POINTS = [vld, sel, Cross(vld, sel), a_corner, b_corner, reset, rounding, saturation]
