"""What to feed mac_q16: value rules, directed corner cases."""
from Components.Fixed import q16
from Engine.Rules import bit, bits, corners
from .Protocol import Mac

CORNERS = [0x00000000, 0x00010000, 0x00008000, 0x7FFFFFFF, 0x80000000,
           0xFFFFFFFF, 0x00000001, 0xFFFF0000, 0x40000000, 0x00020000]

RULES = {
    "a":   corners(CORNERS, p=0.15, otherwise=bits(32)),
    "b":   corners(CORNERS, p=0.15, otherwise=bits(32)),
    "vld": bit(0.8),
    "sel": bit(0.5),
    "id":  bits(4),
}

WEIGHTS = {Mac: 1}

DIRECTED = [
    # banker's rounding: product ends exactly on .5 (guard=1, sticky=0)
    Mac(a=1, b=0x8000, vld=1),              # 0.5 ulp, lsb 0 -> stays 0
    Mac(a=3, b=0x8000, vld=1),              # 1.5 ulp, lsb 1 -> rounds up to 2
    Mac(a=5, b=0x8000, vld=1),              # 2.5 ulp, lsb 0 -> stays 2
    # saturation
    Mac(a=0x7FFFFFFF, b=0x7FFFFFFF, vld=1),  # max * max -> +max
    Mac(a=0x80000000, b=0x80000000, vld=1),  # min * min -> +max
    Mac(a=0x80000000, b=0x7FFFFFFF, vld=1),  # min * max -> min
    # ordinary values
    Mac(a=q16(3), b=q16(2.5), vld=1),
    Mac(a=q16(-1.5), b=q16(4), vld=1),
]
