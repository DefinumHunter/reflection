"""
Components/MacNode.py
Stimulus data and golden model for mac_q16.
No driver, no monitor, no class — pure data and math.

MAC_INPUT_SPEC    — input signal specs for the generic driver
MAC_OUTPUT_SPEC   — output signal specs for the generic monitor
MAC_BASIC_CORNERS — directed corner-case cycles
MAC_PLACEMENTS    — placement instructions
mac_q16_golden()  — reference model for mac_q16
"""

from Engine.Generators import SignalSpec, Placement
from Components.Fixed import to_signed, saturate

# ── Signal specs ──────────────────────────────────────────────────

_CORNER_POOL = [
    0x00000000, 0x00010000, 0x00008000,
    0x7FFFFFFF, 0x80000000, 0xFFFFFFFF,
    0x00000001, 0xFFFF0000, 0x40000000,
    0x00020000,
]

MAC_INPUT_SPEC = {
    "in_a":   SignalSpec(kind="data", width=32, signed=True,
                         corner_pool=_CORNER_POOL, corner_probability=0.15),
    "in_b":   SignalSpec(kind="data", width=32, signed=True,
                         corner_pool=_CORNER_POOL, corner_probability=0.15),
    "in_vld": SignalSpec(kind="bit",  width=1,  signed=False, prob_one=0.80),
}

MAC_OUTPUT_SPEC = {
    "out_res": SignalSpec(kind="data", width=32, signed=True),
    "out_vld": SignalSpec(kind="bit",  width=1,  signed=False),
}

# ── Corner cases ──────────────────────────────────────────────────

MAC_BASIC_CORNERS = [
    {"in_a": 0x00000000, "in_b": 0x00000000, "in_vld": 1},
    {"in_a": 0x00010000, "in_b": 0x00010000, "in_vld": 1},
    {"in_a": 0x00020000, "in_b": 0x00018000, "in_vld": 1},
    {"in_a": 0x7FFFFFFF, "in_b": 0x00000002, "in_vld": 1},
    {"in_a": 0x80000000, "in_b": 0x00000002, "in_vld": 1},
    {"in_a": 0x7FFFFFFF, "in_b": 0x7FFFFFFF, "in_vld": 1},
    {"in_a": 0x80000000, "in_b": 0x80000000, "in_vld": 1},
    {"in_a": 0x80000000, "in_b": 0x7FFFFFFF, "in_vld": 1},
    {"in_a": 0xFFFF0000, "in_b": 0x00010000, "in_vld": 1},
    {"in_a": 0xFFFF0000, "in_b": 0xFFFF0000, "in_vld": 1},
    {"in_a": 0x00000001, "in_b": 0x00000001, "in_vld": 1},
    {"in_a": 0x00008000, "in_b": 0x00020000, "in_vld": 1},
    {"in_a": 0x7FFFFFFF, "in_b": 0x00000000, "in_vld": 1},
    {"in_a": 0x80000000, "in_b": 0x00000000, "in_vld": 1},
    {"in_a": 0xFFFFFFFF, "in_b": 0x00010000, "in_vld": 1},
    {"in_a": 0x00018000, "in_b": 0x00010000, "in_vld": 1},
    {"in_a": 0x00014000, "in_b": 0x00013334, "in_vld": 1},
    {"in_a": 0x00014000, "in_b": 0x00020000, "in_vld": 1},
]

MAC_VALID_DROP_RACE = [
    {"in_vld": 0},
    {"in_a": 0x7FFFFFFF, "in_b": 0x00000002, "in_vld": 1},
    {"in_vld": 0},
    {"in_a": 0x80000000, "in_b": 0x00000002, "in_vld": 1},
]

MAC_PLACEMENTS = [
    Placement(cycle=0,    sequence=MAC_BASIC_CORNERS),
    Placement(cycle=None, sequence=MAC_VALID_DROP_RACE),
]

# ── Golden model ──────────────────────────────────────────────────

def mac_q16_golden(a_raw: int, b_raw: int) -> dict:
    """
    Q16.16 signed multiply with Banker's rounding and saturation.
    Matches mac_q16 RTL exactly.
    Returns { "out_res": int } as unsigned 32-bit.
    """
    a    = to_signed(a_raw)
    b    = to_signed(b_raw)
    prod = a * b

    fraction       = prod & 0xFFFF
    res_calculated = prod >> 16

    guard  = (fraction & 0x8000) != 0
    sticky = (fraction & 0x7FFF) != 0
    lsb    = (res_calculated & 1)  != 0

    if guard and (sticky or lsb):
        res_calculated += 1

    return {"out_res": saturate(res_calculated)}


def mac_q16_golden_cycle(inp: dict) -> dict:
    """
    Full-cycle golden model — accepts input cycle dict, returns output dict.
    Used by ChainReference. Handles in_vld=0 by returning zeros.
    """
    if not inp.get("in_vld", 0):
        return {"out_vld": 0, "out_res": 0}
    result = mac_q16_golden(inp.get("in_a", 0), inp.get("in_b", 0))
    return {"out_vld": 1, **result}
