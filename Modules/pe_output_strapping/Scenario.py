"""Directed corners and reproducible random inputs; no expected outputs here."""
from Engine.Rules import bit, corners, bits, sequential
from .Protocol import Beat

MASK = 0xFFFFFFFF
CORNERS = [0, 1, 2, 0x10000, 0x7FFFFFFF, 0x7FFFFFFE,
           0x80000000, 0x80000001, 0xFFFFFFFF, 0xFFFF0000]

RULES = {
    "mac": corners(CORNERS, 0.4, bits(32)),
    "neighbor": corners(CORNERS, 0.4, bits(32)),
    "id": sequential(1, 15),
    "ring_final": bit(),
    "sub_post": bit(),
}

def valid_match(ctx):
    return Beat(vld=1, neighbor_vld=1, mismatch=0)

def missing_neighbor(ctx):
    return Beat(vld=1, neighbor_vld=0, mismatch=0)

def wrong_id(ctx):
    return Beat(vld=1, neighbor_vld=1, mismatch=1)

def invalid_mac(ctx):
    return Beat(vld=0, neighbor_vld=ctx.rng.getrandbits(1),
                mismatch=ctx.rng.getrandbits(1))

def sat_pos_add(ctx):
    return Beat(neighbor=0x7FFFFFFF, mac=ctx.rng.randrange(1, 1 << 30),
                sub_post=0)

def sat_neg_add(ctx):
    return Beat(neighbor=0x80000000,
                mac=(-ctx.rng.randrange(1, 1 << 30)) & MASK, sub_post=0)

def sat_pos_sub(ctx):
    return Beat(neighbor=0x7FFFFFFF,
                mac=(-ctx.rng.randrange(1, 1 << 30)) & MASK, sub_post=1)

def sat_neg_sub(ctx):
    return Beat(neighbor=0x80000000, mac=ctx.rng.randrange(1, 1 << 30),
                sub_post=1)

WEIGHTS = {
    valid_match: 36, missing_neighbor: 8, wrong_id: 8, invalid_mac: 8,
    sat_pos_add: 10, sat_neg_add: 10, sat_pos_sub: 10, sat_neg_sub: 10,
}

DIRECTED = [
    Beat(mac=0, neighbor=0, id=1, ring_final=0, sub_post=0),
    Beat(mac=1, neighbor=2, id=2, ring_final=1, sub_post=0),
    Beat(mac=1, neighbor=2, id=3, ring_final=0, sub_post=1),
    Beat(mac=0xFFFFFFFF, neighbor=0, id=4, ring_final=1, sub_post=1),
    Beat(mac=1, neighbor=0x7FFFFFFF, id=5, sub_post=0),
    Beat(mac=0xFFFFFFFF, neighbor=0x80000000, id=6, sub_post=0),
    Beat(mac=0xFFFFFFFF, neighbor=0x7FFFFFFF, id=7, sub_post=1),
    Beat(mac=1, neighbor=0x80000000, id=8, sub_post=1),
    Beat(mac=0x12345678, neighbor=0x76543210, id=9, mismatch=1),
    Beat(mac=0x10000, neighbor=0x20000, id=10, neighbor_vld=0),
    Beat(mac=0x30000, neighbor=0x40000, id=11, vld=0),
    Beat(mac=0x50000, neighbor=0x60000, id=12, ring_final=1, sub_post=0),
    Beat(mac=0x70000, neighbor=0x80000, id=13, ring_final=1, sub_post=1),
    Beat(mac=0x90000, neighbor=0xA0000, id=14, ring_final=0, sub_post=0),
    Beat(mac=0xB0000, neighbor=0xC0000, id=15, ring_final=0, sub_post=1),
]
