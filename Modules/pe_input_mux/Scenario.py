"""Stimuli independent of golden arithmetic results."""
from Engine.Rules import bit, bits, corners, sequential
from .Protocol import Direct, Local, PreSum

MASK = 0xFFFFFFFF
CORNERS = [0, 1, 2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF,
           0x7FFFFFFE, 0x80000001, 0x10000, 0xFFFF0000]

RULES = {
    "a": corners(CORNERS, 0.4, bits(32)),
    "b": corners(CORNERS, 0.4, bits(32)),
    "c": corners(CORNERS, 0.4, bits(32)),
    "local": corners(CORNERS, 0.4, bits(32)),
    "sub_pre": bit(),
    "id": sequential(1, 15),
    "ring_final": bit(),
    "sub_post": bit(),
}

def sat_add_pos(ctx):
    return PreSum(a=0x7FFFFFFF, b=ctx.rng.randrange(1, 1 << 30), sub_pre=0)

def sat_add_neg(ctx):
    return PreSum(a=0x80000000, b=(-ctx.rng.randrange(1, 1 << 30)) & MASK, sub_pre=0)

def sat_sub_pos(ctx):
    return PreSum(a=0x7FFFFFFF, b=(-ctx.rng.randrange(1, 1 << 30)) & MASK, sub_pre=1)

def sat_sub_neg(ctx):
    return PreSum(a=0x80000000, b=ctx.rng.randrange(1, 1 << 30), sub_pre=1)

WEIGHTS = {
    Direct: 22, Local: 22, PreSum: 25,
    sat_add_pos: 7, sat_add_neg: 7,
    sat_sub_pos: 7, sat_sub_neg: 7,
    # Invalid single-beat inputs still exercise bubble propagation.
    lambda ctx: Direct(issue=0): 3,
}

DIRECTED = [
    Direct(a=0, b=0xFFFFFFFF, id=1, ring_final=0, sub_post=0),
    Local(a=0x80000000, local=0x7FFFFFFF, id=2, ring_final=0, sub_post=1),
    PreSum(a=1, b=2, c=3, sub_pre=0, id=3, ring_final=1, sub_post=0),
    PreSum(a=5, b=8, c=0xFFFFFFFF, sub_pre=1, id=4, ring_final=1, sub_post=1),
    PreSum(a=0x7FFFFFFF, b=1, c=0x10000, sub_pre=0, id=5),
    PreSum(a=0x80000000, b=0xFFFFFFFF, c=0x10000, sub_pre=0, id=6),
    PreSum(a=0x7FFFFFFF, b=0xFFFFFFFF, c=0x10000, sub_pre=1, id=7),
    PreSum(a=0x80000000, b=1, c=0x10000, sub_pre=1, id=8),
    Direct(a=0xDEADBEEF, b=0x12345678, issue=0, id=9),
    Direct(a=0x10000, b=0x20000, id=10),
]
