"""Directed corners and randomized full-PE operations."""
from Engine.Rules import bit, bits, corners, sequential
from .Protocol import Direct, Local, PreSum

CORNERS = [
    0, 1, 2, 3, 0x8000, 0x10000, 0x20000,
    0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFF0000,
]

RULES = {
    "a": corners(CORNERS, 0.4, bits(32)),
    "b": corners(CORNERS, 0.4, bits(32)),
    "c": corners(CORNERS, 0.4, bits(32)),
    "local": corners(CORNERS, 0.4, bits(32)),
    "neighbor": corners(CORNERS, 0.4, bits(32)),
    "sub_pre": bit(),
    "id": sequential(1, 15),
    "ring_final": bit(),
    "sub_post": bit(),
}


def missing(ctx):
    return Direct(neighbor_vld=0)


def wrong_id(ctx):
    return Local(mismatch=1)


def invalid(ctx):
    return Direct(issue=0)


def pre_add_sat(ctx):
    return PreSum(a=0x7FFFFFFF, b=1, sub_pre=0)


def pre_sub_sat(ctx):
    return PreSum(a=0x80000000, b=1, sub_pre=1)


def post_add_sat(ctx):
    return Direct(a=0x10000, b=0x10000,
                  neighbor=0x7FFFFFFF, sub_post=0)


def post_sub_sat(ctx):
    return Direct(a=0x10000, b=0x10000,
                  neighbor=0x80000000, sub_post=1)


WEIGHTS = {
    Direct: 22,
    Local: 18,
    PreSum: 20,
    missing: 6,
    wrong_id: 6,
    invalid: 5,
    pre_add_sat: 6,
    pre_sub_sat: 5,
    post_add_sat: 6,
    post_sub_sat: 6,
}

DIRECTED = [
    Direct(a=0x10000, b=0x10000, neighbor=0, id=1,
           ring_final=0, sub_post=0),
    Local(a=0x20000, local=0x30000, neighbor=0x10000, id=2,
          ring_final=1, sub_post=0),
    PreSum(a=0x10000, b=0x20000, c=0x30000, sub_pre=0,
           neighbor=0x10000, id=3, ring_final=0, sub_post=1),
    PreSum(a=0x30000, b=0x10000, c=0x20000, sub_pre=1,
           neighbor=0x10000, id=4, ring_final=1, sub_post=1),
    PreSum(a=0x7FFFFFFF, b=1, c=0x10000, sub_pre=0,
           neighbor=0, id=5),
    PreSum(a=0x80000000, b=1, c=0x10000, sub_pre=1,
           neighbor=0, id=6),
    Direct(a=1, b=0x8000, neighbor=0, id=7),
    Direct(a=3, b=0x8000, neighbor=0, id=8),
    Direct(a=5, b=0x8000, neighbor=0, id=9),
    Direct(a=0x7FFFFFFF, b=0x7FFFFFFF, neighbor=0, id=10),
    Direct(a=0x80000000, b=0x7FFFFFFF, neighbor=0, id=11),
    Direct(a=0x10000, b=0x10000, neighbor=0x7FFFFFFF,
           id=12, sub_post=0),
    Direct(a=0x10000, b=0x10000, neighbor=0x80000000,
           id=13, sub_post=1),
    Local(a=0x10000, local=0x10000, neighbor=0x10000,
          id=14, mismatch=1),
    Direct(a=0x10000, b=0x10000, neighbor=0x10000,
           id=15, neighbor_vld=0),
    Direct(a=0xDEADBEEF, b=0x12345678, neighbor=0,
           id=1, issue=0),
]
