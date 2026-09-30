def to_signed(raw: int, bits: int = 32) -> int:
    raw &= (1 << bits) - 1
    if raw & (1 << (bits - 1)):
        raw -= (1 << bits)
    return raw


def saturate(val: int, bits: int = 32) -> int:
    lo = -(1 << (bits - 1))
    hi = (1 << (bits - 1)) - 1
    if val < lo:
        return lo & ((1 << bits) - 1)
    if val > hi:
        return hi
    return val & ((1 << bits) - 1)


def q16(x: float, bits: int = 32) -> int:
    """Q16.16 constant as raw bits, e.g. q16(-1.5) -> 0xFFFE8000."""
    return int(round(x * 65536)) & ((1 << bits) - 1)
