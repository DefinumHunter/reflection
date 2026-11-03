"""What counts as "tested" for pe_mac_wrapper.

    stimulus  which operations, in which order, how tightly packed, which ids
    behaviour tags from the goldens: what the sum in the mux did, and what the
              MAC behind it did (the MAC points are reused from mac_q16)
"""
from Engine.Coverage import Cross, Op, Tag
from Modules.mac_q16.Coverage import rounding, saturation
from .Protocol import MulAB, MulLocal, MulSum

KINDS = ["MulAB", "MulSum", "MulLocal"]


def _kind(op):
    return type(op).__name__ if isinstance(op, (MulAB, MulSum, MulLocal)) else None


def _gap(s):
    if not (_kind(s.op) and _kind(s.prev)):
        return None
    return "overlap" if s.gap < 0 else "none" if s.gap == 0 else "pause"


def _field(name):
    return lambda s: getattr(s.op, name, None) if _kind(s.op) else None


kind = Op("kind", KINDS, of=lambda s: _kind(s.op))
after = Op("after", KINDS, of=lambda s: _kind(s.prev) if _kind(s.op) else None)
gap = Op("gap", ["overlap", "none", "pause"], of=_gap)
ident = Op("id", range(1, 16), of=_field("id"))
mac_sel = Op("mac_sel", [0, 1], of=_field("mac_sel"))

# tags from Components/MuxNode.py, when a sum is actually used (sel = USE_SUM)
sum_op = Tag("sum op", ["sum_add", "sum_sub"])
sum_sat = Tag("sum saturation", ["sum_sat_none", "sum_sat_pos", "sum_sat_neg"], at_least=10)

POINTS = [
    kind, Cross(after, kind), after, gap, Cross(kind, gap), ident, mac_sel,
    sum_op, sum_sat, Cross(sum_op, sum_sat),
    rounding, saturation,
]
