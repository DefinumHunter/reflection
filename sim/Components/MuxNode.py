"""
Components/MuxNode.py
Stimulus data and golden model for pe_input_mux.
No driver, no monitor, no class — pure data and math.

MUX_INPUT_SPEC    — input signal specs for the generic driver
MUX_OUTPUT_SPEC   — output signal specs for the generic monitor
MUX_BASIC_CORNERS — directed corner-case cycles
MUX_PLACEMENTS    — placement instructions
pe_input_mux_golden() — reference model for pe_input_mux
"""

from Engine.Generators import SignalSpec, Placement
from Components.Fixed import to_signed, saturate

# ── Signal specs ──────────────────────────────────────────────────

_CORNER_POOL = [
    0x00000000, 0x00010000, 0x7FFFFFFF,
    0x80000000, 0xFFFF0000, 0x00008000,
    0x00020000, 0xFFFE0000,
]

MUX_INPUT_SPEC = {
    "x":      SignalSpec(kind="data", width=32, signed=True,
                         corner_pool=_CORNER_POOL, corner_probability=0.15),
    "y":      SignalSpec(kind="data", width=32, signed=True,
                         corner_pool=_CORNER_POOL, corner_probability=0.15),
    "b":      SignalSpec(kind="data", width=32, signed=True,
                         corner_pool=_CORNER_POOL, corner_probability=0.15),
    "sel":    SignalSpec(kind="bit",  width=1,  signed=False, prob_one=0.5),
    "sub":    SignalSpec(kind="bit",  width=1,  signed=False, prob_one=0.5),
    "in_vld": SignalSpec(kind="bit",  width=1,  signed=False, prob_one=0.80),
}

MUX_OUTPUT_SPEC = {
    "a_out":   SignalSpec(kind="data", width=32, signed=True),
    "b_out":   SignalSpec(kind="data", width=32, signed=True),
    "out_vld": SignalSpec(kind="bit",  width=1,  signed=False),
}

# ── Corner cases ──────────────────────────────────────────────────

MUX_BASIC_CORNERS = [
    {"x": 0x00000000, "y": 0x00000000, "b": 0x00000000, "sel": 0, "sub": 0, "in_vld": 1},
    {"x": 0x00010000, "y": 0x00010000, "b": 0x00020000, "sel": 0, "sub": 0, "in_vld": 1},
    {"x": 0x00010000, "y": 0x00010000, "b": 0x00020000, "sel": 1, "sub": 0, "in_vld": 1},
    {"x": 0x00010000, "y": 0x00010000, "b": 0x00020000, "sel": 1, "sub": 1, "in_vld": 1},
    {"x": 0x7FFFFFFF, "y": 0x00000001, "b": 0x00000000, "sel": 1, "sub": 0, "in_vld": 1},
    {"x": 0x80000000, "y": 0xFFFFFFFF, "b": 0x00000000, "sel": 1, "sub": 1, "in_vld": 1},
    {"x": 0x7FFFFFFF, "y": 0x7FFFFFFF, "b": 0x00000000, "sel": 1, "sub": 0, "in_vld": 1},
    {"x": 0x80000000, "y": 0x80000000, "b": 0x00000000, "sel": 1, "sub": 1, "in_vld": 1},
    {"x": 0xFFFF0000, "y": 0x00010000, "b": 0x00000000, "sel": 1, "sub": 0, "in_vld": 1},
    {"x": 0xFFFF0000, "y": 0x00010000, "b": 0x00000000, "sel": 1, "sub": 1, "in_vld": 1},
    {"x": 0x7FFFFFFF, "y": 0x00000000, "b": 0x7FFFFFFF, "sel": 0, "sub": 0, "in_vld": 1},
    {"x": 0x80000000, "y": 0x00000000, "b": 0x80000000, "sel": 0, "sub": 0, "in_vld": 1},
]

MUX_PLACEMENTS = [
    Placement(cycle=0, sequence=MUX_BASIC_CORNERS),
]

# ── Golden model ──────────────────────────────────────────────────

def pe_input_mux_golden(
    x_raw: int, y_raw: int, b_raw: int,
    sel: int, sub: int
) -> dict:
    """
    sel=0 : a_out = x (direct passthrough)
    sel=1 : a_out = saturate(x - y) if sub else saturate(x + y)
    b_out is always b.
    Matches pe_input_mux RTL exactly.
    Returns { "a_out": int, "b_out": int } as unsigned 32-bit.
    """
    x = to_signed(x_raw)
    y = to_signed(y_raw)
    b = to_signed(b_raw)

    if sel == 0:
        a = x & 0xFFFFFFFF
    else:
        raw = (x - y) if sub else (x + y)
        a   = saturate(raw)

    return {
        "a_out": a & 0xFFFFFFFF,
        "b_out": b & 0xFFFFFFFF,
    }


def pe_input_mux_golden_cycle(inp: dict) -> dict:
    """
    Full-cycle golden model — accepts input cycle dict, returns output dict.
    Used by ChainReference. Handles in_vld=0 by returning zeros.
    """
    if not inp.get("in_vld", 0):
        return {"out_vld": 0, "a_out": 0, "b_out": 0}
    result = pe_input_mux_golden(
        inp.get("x", 0), inp.get("y", 0), inp.get("b", 0),
        inp.get("sel", 0), inp.get("sub", 0)
    )
    return {"out_vld": 1, **result}
