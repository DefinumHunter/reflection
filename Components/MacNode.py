# Components/MacNode.py
from Engine.Core import LeafSpec
from Components.Fixed import to_signed, saturate


def mac_q16_golden(inputs: dict, tags: list = None) -> dict:
    """The arithmetic only: Q16 multiply, banker's rounding, saturation.
    If `tags` is given, the branches taken are appended to it (for coverage)."""
    a = to_signed(inputs.get("in_a", 0))
    b = to_signed(inputs.get("in_b", 0))
    prod = a * b
    fraction       = prod & 0xFFFF
    res_calculated = prod >> 16
    guard  = (fraction & 0x8000) != 0
    sticky = (fraction & 0x7FFF) != 0
    lsb    = (res_calculated & 1)  != 0
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
    """Verilog || with X: any 1 -> 1, else any X -> X, else 0."""
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

    State mirrors the RTL registers: pipe, vld_pipe, sel_pipe, id_pipe; index 0 is
    the first stage, index -1 drives the outputs. Any of them can be given
    at construction to start from a known state.
    Math is done at the input side and the result travels down the pipe;
    RTL rounds at the output side, which is equivalent.
    """

    def __init__(self, PIPELINE_STAGES=4, pipe=None, vld_pipe=None, sel_pipe=None,
                 id_pipe=None):
        self.n = PIPELINE_STAGES
        self.tags = []                      # coverage tags, collected by the model
        self.pipe = _fill(pipe, self.n)
        self.id_pipe = _fill(id_pipe, self.n)
        self.vld_pipe = _fill(vld_pipe, self.n)
        self.sel_pipe = _fill(sel_pipe, self.n)

    def _registered(self):
        return {"out_res": self.pipe[-1],
                "out_vld": self.vld_pipe[-1],
                "out_sel": self.sel_pipe[-1],
                "out_id":  self.id_pipe[-1]}

    def start(self):
        return self._registered()

    def tick(self, i: dict) -> dict:
        # comb, from the state before the edge
        busy = _x_or(i["in_vld"], *self.vld_pipe)

        # clk edge. Data and id pipes have no reset: they move every cycle.
        a, b = i["in_a"], i["in_b"]
        counted = self.tags if i["in_vld"] == 1 else None    # only real multiplies count
        res = None if a is None or b is None else mac_q16_golden(i, counted)["out_res"]
        self.pipe = [res] + self.pipe[:-1]
        self.id_pipe = [i["in_id"]] + self.id_pipe[:-1]

        # vld/sel pipes: reset only if rst_n is exactly 0. With rst_n = X,
        # `if (!rst_n)` takes the else branch in Verilog, so do we.
        if i["rst_n"] == 0:
            self.vld_pipe = [0] * self.n
            self.sel_pipe = [0] * self.n
        else:
            self.vld_pipe = [i["in_vld"]] + self.vld_pipe[:-1]
            self.sel_pipe = [i["sel"]] + self.sel_pipe[:-1]

        return {**self._registered(), "busy": busy}


MacNode = LeafSpec(
    module="mac_q16",
    golden=MacQ16,
    comb={"busy"},
)
