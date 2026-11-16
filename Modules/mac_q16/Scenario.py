"""Directed and seeded-random stimuli for Q16.16 multiplication.

All operand values are raw unsigned 32-bit port patterns. No expected result
is calculated here: arithmetic checking belongs to the existing golden model.
"""
from Engine.Rules import bit, bits, corners, sequential
from .Protocol import Mac

MASK = 0xFFFFFFFF
CORNERS = [
    0, 1, 2, 3, 5, 0x7FFF, 0x8000, 0xFFFF,
    0x10000, 0x20000, 0x40000000, 0x7FFFFFFF,
    0x80000000, 0x80000001, 0xFFFF0000, 0xFFFFFFFF,
]

RULES = {
    "a": corners(CORNERS, p=0.30, otherwise=bits(32)),
    "b": corners(CORNERS, p=0.30, otherwise=bits(32)),
    "vld": bit(0.80),
    "id": sequential(1, 15),
    "ring_final": bit(0.5),
    "sub_post": bit(0.5),
}


def small_pair(rng):
    """Signed magnitudes below 2^23: no output saturation is possible."""
    return [(rng.randrange(-(1 << 23), 1 << 23) & MASK) for _ in range(2)]


def tie_pair(rng, up):
    """Exactly half an output LSB, with even/odd retained LSB."""
    a = (rng.getrandbits(28) << 2) | (3 if up else 1)
    if rng.getrandbits(1):
        a = -a
    pair = [a & MASK, 0x8000]
    rng.shuffle(pair)
    return pair


def sat_pair(rng, positive):
    """Force saturation using large-magnitude signed inputs."""
    a = rng.randrange(1 << 24, 1 << 31)
    b = rng.randrange(1 << 24, 1 << 31)
    if rng.getrandbits(1):
        a, b = -a, -b
    if not positive:
        b = -b
    pair = [a & MASK, b & MASK]
    rng.shuffle(pair)
    return pair


def ordinary(ctx):
    a, b = small_pair(ctx.rng)
    return Mac(a=a, b=b, vld=1)


def tie_up(ctx):
    a, b = tie_pair(ctx.rng, True)
    return Mac(a=a, b=b, vld=1)


def tie_stay(ctx):
    a, b = tie_pair(ctx.rng, False)
    return Mac(a=a, b=b, vld=1)


def sat_pos(ctx):
    a, b = sat_pair(ctx.rng, True)
    return Mac(a=a, b=b, vld=1)


def sat_neg(ctx):
    a, b = sat_pair(ctx.rng, False)
    return Mac(a=a, b=b, vld=1)


def bubble(ctx):
    """An invalid beat with nontrivial data and sidebands."""
    return Mac(vld=0)


WEIGHTS = {
    ordinary: 30,
    Mac: 20,
    tie_up: 12,
    tie_stay: 12,
    sat_pos: 10,
    sat_neg: 10,
    bubble: 6,
}

# Explicitly cover arithmetic corners, signs, all sideband combinations,
# consecutive valid beats, invalid bubbles and a reset after live traffic.
DIRECTED = [
    Mac(a=0, b=0x7FFFFFFF, vld=1, id=1, ring_final=0, sub_post=0),
    Mac(a=0x10000, b=0x10000, vld=1, id=2, ring_final=0, sub_post=1),
    Mac(a=0xFFFF0000, b=0x10000, vld=1, id=3, ring_final=1, sub_post=0),
    Mac(a=0x10000, b=0xFFFF0000, vld=1, id=4, ring_final=1, sub_post=1),
    Mac(a=1, b=0x8000, vld=1, id=5),
    Mac(a=3, b=0x8000, vld=1, id=6),
    Mac(a=5, b=0x8000, vld=1, id=7),
    Mac(a=0xFFFFFFFF, b=0x8000, vld=1, id=8),
    Mac(a=0xFFFFFFFD, b=0x8000, vld=1, id=9),
    Mac(a=0x7FFFFFFF, b=0x7FFFFFFF, vld=1, id=10),
    Mac(a=0x80000000, b=0x80000000, vld=1, id=11),
    Mac(a=0x80000000, b=0x7FFFFFFF, vld=1, id=12),
    Mac(a=0x80000000, b=0x10000, vld=1, id=13),
    Mac(a=0x7FFFFFFF, b=0x10000, vld=1, id=14),
    Mac(a=0xDEADBEEF, b=0x12345678, vld=0, id=15, ring_final=1, sub_post=1),
    Mac(a=0x20000, b=0x30000, vld=1, id=1),
]
