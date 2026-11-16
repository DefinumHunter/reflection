"""Directed arithmetic, neighbor-ID, routing and error cases."""
from Engine.Rules import bit, bits, corners, sequential
from .Protocol import MacNeighbor

MASK = 0xFFFFFFFF
CORNERS = [
    0, 1, 2, 3, 0x8000, 0x10000, 0x20000,
    0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFF0000,
]

RULES = {
    "a": corners(CORNERS, 0.40, bits(32)),
    "b": corners(CORNERS, 0.40, bits(32)),
    "neighbor": corners(CORNERS, 0.40, bits(32)),
    "id": sequential(1, 15),
    "ring_final": bit(),
    "sub_post": bit(),
}

def matching(ctx):
    return MacNeighbor()

def missing(ctx):
    return MacNeighbor(neighbor_vld=0)

def wrong_id(ctx):
    return MacNeighbor(mismatch=1)

def invalid(ctx):
    return MacNeighbor(vld=0)

def positive_overflow(ctx):
    return MacNeighbor(a=0x10000, b=0x10000,
                       neighbor=0x7FFFFFFF, sub_post=0)

def negative_overflow(ctx):
    return MacNeighbor(a=0x10000, b=0x10000,
                       neighbor=0x80000000, sub_post=1)

def negative_product(ctx):
    return MacNeighbor(a=0xFFFF0000, b=0x10000)

WEIGHTS = {
    matching: 35,
    missing: 8,
    wrong_id: 8,
    invalid: 8,
    positive_overflow: 12,
    negative_overflow: 12,
    negative_product: 17,
}

DIRECTED = [
    MacNeighbor(a=0x10000, b=0x10000, neighbor=0, id=1,
                ring_final=0, sub_post=0),
    MacNeighbor(a=0x20000, b=0x30000, neighbor=0x10000, id=2,
                ring_final=1, sub_post=0),
    MacNeighbor(a=0x10000, b=0x10000, neighbor=0x30000, id=3,
                ring_final=0, sub_post=1),
    MacNeighbor(a=0xFFFF0000, b=0x10000, neighbor=0x20000, id=4,
                ring_final=1, sub_post=1),
    MacNeighbor(a=0x10000, b=0x10000, neighbor=0x7FFFFFFF, id=5,
                ring_final=1, sub_post=0),
    MacNeighbor(a=0x10000, b=0x10000, neighbor=0x80000000, id=6,
                ring_final=0, sub_post=1),
    MacNeighbor(a=0x7FFFFFFF, b=0x7FFFFFFF, neighbor=0, id=7),
    MacNeighbor(a=0x80000000, b=0x7FFFFFFF, neighbor=0, id=8),
    MacNeighbor(a=1, b=0x8000, neighbor=0, id=9),
    MacNeighbor(a=3, b=0x8000, neighbor=0, id=10),
    MacNeighbor(a=5, b=0x8000, neighbor=0, id=11),
    MacNeighbor(a=0x10000, b=0x10000, neighbor=0x10000, id=12,
                mismatch=1),
    MacNeighbor(a=0x10000, b=0x10000, neighbor=0x10000, id=13,
                neighbor_vld=0),
    MacNeighbor(a=0x10000, b=0x10000, neighbor=0x10000, id=14,
                vld=0),
    MacNeighbor(a=0x10000, b=0x10000, neighbor=0x10000, id=15),
]
