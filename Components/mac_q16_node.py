# Components/mac_q16_node.py
from Engine.Core import LeafSpec
from Engine.Fixed import to_signed, saturate


def mac_q16_golden(inputs: dict, tags: list = None) -> dict:
    """Q16.16 multiply → banker's round (half to even) → saturate.
    If `tags` is given, the branches taken are appended to it (for coverage)."""
    a = to_signed(inputs["in_a"])
    b = to_signed(inputs["in_b"])
    prod = a * b
    fraction       = prod & 0xFFFF
    res_calculated = prod >> 16
    guard  = (fraction & 0x8000) != 0
    sticky = (fraction & 0x7FFF) != 0
    lsb    = (res_calculated & 1) != 0
    if guard and (sticky or lsb):
        res_calculated += 1
    if tags is not None:
        tags.append("round_down" if not guard else
                    "round_up" if sticky else
                    "round_tie_up" if lsb else "round_tie_stay")
        tags.append("sat_pos" if res_calculated > 0x7FFFFFFF else
                    "sat_neg" if res_calculated < -0x80000000 else "sat_none")
    return {"out_res": saturate(res_calculated)}


def _x_or(*bits):
    """Verilog || with X: any 1 → 1, else any X → X, else 0."""
    if any(b == 1 for b in bits):
        return 1
    if any(b is None for b in bits):
        return None
    return 0


def _fill(init, n):
    """Pipeline of n stages. Default: None (X, as at power-up)."""
    if init is None:
        return [None] * n
    init = list(init)
    if len(init) != n:
        raise ValueError(f"initial pipeline has {len(init)} stages, PIPELINE_STAGES={n}")
    return init


class MacQ16:
    """mac_q16 behaviour, one object per RTL instance.

    State mirrors the RTL registers:
      pipe        – 64-bit product (or the already-rounded result; equivalent)
      vld_pipe    – valid
      id_pipe, ring_pipe, subpost_pipe – sideband

    Multiplication is done at the input side; rounding + saturation at the
    output side. Only vld_pipe is reset.
    """

    def __init__(self, PIPELINE_STAGES=4,
                 pipe=None, vld_pipe=None,
                 id_pipe=None, ring_pipe=None, subpost_pipe=None):
        self.n = PIPELINE_STAGES
        self.tags = []

        self.pipe        = _fill(pipe, self.n)
        self.vld_pipe    = _fill(vld_pipe, self.n)
        self.id_pipe     = _fill(id_pipe, self.n)
        self.ring_pipe   = _fill(ring_pipe, self.n)
        self.subpost_pipe = _fill(subpost_pipe, self.n)

    def _registered(self):
        return {
            "out_res":        self.pipe[-1],
            "out_vld":        self.vld_pipe[-1],
            "out_id":         self.id_pipe[-1],
            "out_ring_final": self.ring_pipe[-1],
            "out_sub_post":   self.subpost_pipe[-1],
        }

    def start(self):
        return self._registered()

    def tick(self, i: dict) -> dict:
        # combinatorial busy from the state *before* the edge
        busy = _x_or(i["in_vld"], *self.vld_pipe)

        # ----- clock edge -----
        a, b = i["in_a"], i["in_b"]
        counted = self.tags if i["in_vld"] == 1 and i["rst_n"] == 1 else None
        res = (None if a is None or b is None
               else mac_q16_golden({"in_a": a, "in_b": b}, counted)["out_res"])

        # data + sideband always shift (no reset)
        self.pipe         = [res] + self.pipe[:-1]
        self.id_pipe      = [i["in_id"]] + self.id_pipe[:-1]
        self.ring_pipe    = [i["in_ring_final"]] + self.ring_pipe[:-1]
        self.subpost_pipe = [i["in_sub_post"]] + self.subpost_pipe[:-1]

        # valid pipe: reset only when rst_n is exactly 0
        if i["rst_n"] == 0:
            self.vld_pipe = [0] * self.n
        else:
            self.vld_pipe = [i["in_vld"]] + self.vld_pipe[:-1]

        return {**self._registered(), "busy": busy}


MacNode = LeafSpec(
    module="mac_q16",
    golden=MacQ16,
    comb={"busy"},
)