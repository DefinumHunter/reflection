"""What to feed pe_mac_wrapper: value rules, weights, gaps, directed cases."""
from Components.Fixed import q16
from Engine.Rules import bit, bits, corners, one_of, sequential
from Modules.mac_q16.Scenario import sat_pair, small_pair, tie_pair
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


# --- value recipes -----------------------------------------------------------

def sum_pair(rng, sat, sub):
    """Operands for the mux sum a + b (sub = 0) or a - b (sub = 1), raw 32-bit.
    sat = "none": both small, no saturation; "pos"/"neg": the sum leaves the
    32-bit range upwards / downwards."""
    if sat == "none":
        return [(rng.getrandbits(30) - (1 << 29)) & 0xFFFFFFFF for _ in range(2)]
    a, b = (rng.randrange((1 << 30) + 1, 1 << 31) for _ in range(2))   # each > half of max
    if sat == "neg":
        a = -a
    if (sat == "neg") != bool(sub):       # a + b needs b on a's side, a - b the opposite
        b = -b
    return [a & 0xFFFFFFFF, b & 0xFFFFFFFF]


# --- classes of stimulus -----------------------------------------------------
# Operations whose operands are built for one behaviour; rules fill the rest.

def _sum(sat):
    def make(ctx):
        sub = ctx.rng.getrandbits(1)
        a, b = sum_pair(ctx.rng, sat, sub)
        c = small_pair(ctx.rng)[0]
        return MulSum(a=a, b=b, c=c, sub=sub)
    make.__name__ = f"sum_{sat}"
    return make


sum_none, sum_pos, sum_neg = _sum("none"), _sum("pos"), _sum("neg")


def mul_ordinary(ctx):
    a, b = small_pair(ctx.rng)
    return MulAB(a=a, b=b)


def mul_tie(ctx):
    a, b = tie_pair(ctx.rng, up=bool(ctx.rng.getrandbits(1)))
    return MulAB(a=a, b=b)


def mul_sat(ctx):
    a, b = sat_pair(ctx.rng, positive=bool(ctx.rng.getrandbits(1)))
    return MulAB(a=a, b=b)


def local_ordinary(ctx):
    a, local = small_pair(ctx.rng)
    return MulLocal(a=a, local=local)


# MulAB / MulSum / MulLocal = anything goes (random 32-bit and corner values)
WEIGHTS = {
    mul_ordinary: 16, mul_tie: 24, mul_sat: 6, MulAB: 6,
    sum_none: 15, sum_pos: 6, sum_neg: 6, MulSum: 6,
    local_ordinary: 16, MulLocal: 6,
}

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
