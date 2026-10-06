"""
Components/Fixed.py
Shared fixed-point math primitives.

Used by golden model functions in MacNode.py, MuxNode.py, and any
future module that operates on Q16.16 signed fixed-point values.
No cocotb, no RTL, no timing.
"""


def to_signed(v: int, width: int = 32) -> int:
    """Convert raw unsigned integer to Python signed int."""
    v &= (1 << width) - 1
    if v >= (1 << (width - 1)):
        v -= (1 << width)
    return v


def saturate(v: int, width: int = 32) -> int:
    """
    Saturate a signed Python int to fit in `width` bits.
    Returns raw unsigned representation.
    """
    max_val =  (1 << (width - 1)) - 1
    min_val = -(1 << (width - 1))
    if v > max_val:
        return max_val & ((1 << width) - 1)
    if v < min_val:
        return min_val & ((1 << width) - 1)
    return v & ((1 << width) - 1)
