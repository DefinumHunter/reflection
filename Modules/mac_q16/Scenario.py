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


# --- value recipes -----------------------------------------------------------
# Pairs of operands (raw 32-bit) built to land in one class of behaviour.
# They return plain numbers, so any module whose inputs reach a MAC can use them.

def small_pair(rng):
    """Ordinary values: |a|, |b| < 2^23 (128.0 in Q16), the product never saturates."""
    return [(rng.getrandbits(24) - (1 << 23)) & 0xFFFFFFFF for _ in range(2)]


def tie_pair(rng, up):
    """Product ends exactly on half an LSB, so banker's rounding decides.
    b = 0.5; a is odd, so the dropped fraction is exactly 0.5; bit 1 of a is
    the LSB of the result: 1 -> rounds up, 0 -> stays."""
    a = (rng.getrandbits(30) << 2) | (0b11 if up else 0b01)
    pair = [a, 0x00008000]
    rng.shuffle(pair)
    return pair


def sat_pair(rng, positive):
    """Both magnitudes >= 2^24 (256.0): the product is past the 32-bit range.
    Same signs -> saturates to max, opposite signs -> to min."""
    a, b = (rng.randrange(1 << 24, 1 << 31) for _ in range(2))
    if rng.random() < 0.5:
        a, b = -a, -b
    if not positive:
        b = -b
    return [a & 0xFFFFFFFF, b & 0xFFFFFFFF]


def corner_pair(rng):
    """One operand from the corner values (0, 1.0, -1 LSB, max, min, ...), the
    other a corner too or an ordinary value."""
    pair = [rng.choice(CORNERS),
            rng.choice(CORNERS) if rng.random() < 0.3 else small_pair(rng)[0]]
    rng.shuffle(pair)
    return pair


# --- classes of stimulus -----------------------------------------------------
# Each returns a transaction with the fields it cares about; rules fill the rest.

def ordinary(ctx):
    a, b = small_pair(ctx.rng)
    return Mac(a=a, b=b)


def cornered(ctx):
    a, b = corner_pair(ctx.rng)
    return Mac(a=a, b=b)


def tie_up(ctx):
    a, b = tie_pair(ctx.rng, up=True)
    return Mac(a=a, b=b, vld=1)


def tie_stay(ctx):
    a, b = tie_pair(ctx.rng, up=False)
    return Mac(a=a, b=b, vld=1)


def sat_pos(ctx):
    a, b = sat_pair(ctx.rng, positive=True)
    return Mac(a=a, b=b, vld=1)


def sat_neg(ctx):
    a, b = sat_pair(ctx.rng, positive=False)
    return Mac(a=a, b=b, vld=1)


# Mac = anything goes (random 32-bit and corner values; mostly saturates)
WEIGHTS = {ordinary: 45, cornered: 25, Mac: 6, tie_up: 6, tie_stay: 6, sat_pos: 6, sat_neg: 6}

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
