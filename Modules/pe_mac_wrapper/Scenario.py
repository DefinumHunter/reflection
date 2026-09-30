"""What to feed pe_mac_wrapper: value rules, weights, gaps, directed cases."""
from Components.Fixed import q16
from Engine.Rules import bit, bits, corners, one_of, sequential
from .Protocol import MulAB, MulLocal, MulSum, Reset

CORNERS = [0x00000000, 0x00010000, 0x00008000, 0x7FFFFFFF, 0x80000000,
           0xFFFFFFFF, 0x00000001, 0xFFFF0000, 0x40000000, 0x00020000]
data = corners(CORNERS, p=0.2, otherwise=bits(32))

RULES = {
    "a": data, "b": data, "c": data, "local": data,
    "sub": bit(0.5),
    "id": sequential(1, 15),          # 1, 2, ..., 15, 1, ... (0 = no transaction)
    "mac_sel": bit(0.5),
}

WEIGHTS = {MulAB: 50, MulSum: 30, MulLocal: 20}

# -1: next operation loads in the clock this one issues (full rate)
GAP = one_of([-1, 0, 1, 2, 3], weights=[4, 3, 2, 1, 1])

MAX, MIN = 0x7FFFFFFF, 0x80000000
DIRECTED = [
    MulAB(a=q16(3), b=q16(2.5)),
    MulSum(a=q16(3), b=q16(1.25), c=q16(2), sub=0),
    MulSum(a=q16(3), b=q16(1.25), c=q16(2), sub=1),
    MulLocal(a=q16(0.5), local=q16(10)),
    MulSum(a=MAX, b=MAX, c=q16(1), sub=0),     # sum saturates to +max before the MAC
    MulSum(a=MIN, b=1, c=q16(1), sub=1),       # difference saturates to min
    MulAB(a=MIN, b=MIN),                       # product saturates
]

# the same operations back to back at full rate, sel/id must stay with each result
BACK_TO_BACK = [MulAB(), MulSum(), MulLocal(), MulAB(), MulSum(), MulAB()]
