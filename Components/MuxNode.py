# Components/MuxNode.py
from Engine.Generators import SignalSpec
from Engine.Core import LeafSpec
from Components.Fixed import to_signed, saturate

MUX_INPUT_SPEC = {
    "local_data": SignalSpec(kind="data", width=32, signed=True),
    "sub":        SignalSpec(kind="bit",  width=1,  signed=False, prob_one=0.5),
    "in_a":       SignalSpec(kind="data", width=32, signed=True),
    "in_b":       SignalSpec(kind="data", width=32, signed=True),
    "sel":        SignalSpec(kind="data", width=2,  signed=False),
    "in_id":      SignalSpec(kind="data", width=4,  signed=False),
    "issue_vld":  SignalSpec(kind="bit",  width=1,  signed=False, prob_one=0.5),
    "issue_sel":  SignalSpec(kind="bit",  width=1,  signed=False, prob_one=0.5),
}
MUX_OUTPUT_SPEC = {
    "a_out":   SignalSpec(kind="data", width=32, signed=True),
    "b_out":   SignalSpec(kind="data", width=32, signed=True),
    "out_id":  SignalSpec(kind="data", width=4,  signed=False),
    "out_vld": SignalSpec(kind="bit",  width=1,  signed=False),
    "out_sel": SignalSpec(kind="bit",  width=1,  signed=False),
}

# sel modes
LOAD_AB   = 0b00   # mux1 <- in_a, mux2 <- in_b
LOAD_SUM  = 0b01   # sum1 <- in_a, sum2 <- in_b, mux1/mux2 hold
USE_SUM   = 0b10   # mux1 <- in_a, mux2 <- sat(sum1 +/- sum2), sub decides
USE_LOCAL = 0b11   # mux1 <- in_a, mux2 <- local_data


def sum_sat(sum1, sum2, sub, tags: list = None):
    """sum1 +/- sum2 (32-bit signed), saturated. X in -> X out.
    If `tags` is given, the branches taken are appended to it (for coverage)."""
    if sum1 is None or sum2 is None or sub is None:
        return None
    a, b = to_signed(sum1), to_signed(sum2)
    raw = a - b if sub else a + b
    if tags is not None:
        tags.append("sum_sub" if sub else "sum_add")
        tags.append("sum_sat_pos" if raw > 0x7FFFFFFF else
                    "sum_sat_neg" if raw < -0x80000000 else "sum_sat_none")
    return saturate(raw)


class PeInputMux:
    """pe_input_mux behaviour, one object per RTL instance.

    Two register stages:
      holding regs (sum1, sum2, mux1, mux2, id): written by sel, keep their
          value otherwise; reset to 0 (id has no reset).
      output regs (a_out, b_out, out_id, out_vld, out_sel): a_out/b_out copy
          mux1/mux2 every cycle, out_id only on issue_vld; only out_vld and
          out_sel are reset, the others hold during reset.
    So a transaction is issued one cycle after its data was loaded, and comes
    out one cycle after issue_vld.
    sel = X or an unknown value writes nothing (Verilog case with X matches no
    branch); rst_n = X takes the non-reset branch, as `if (!rst_n)` does.
    """

    def __init__(self, sum1=None, sum2=None, mux1=None, mux2=None, id=None,
                 a_out=None, b_out=None, out_id=None, out_vld=None, out_sel=None):
        self.tags = []                      # coverage tags, collected by the model
        self.sum1, self.sum2, self.mux1, self.mux2, self.id = sum1, sum2, mux1, mux2, id
        self.out = {"a_out": a_out, "b_out": b_out, "out_id": out_id,
                    "out_vld": out_vld, "out_sel": out_sel}

    def start(self):
        return dict(self.out)

    def tick(self, i: dict) -> dict:
        # everything below reads the state before the edge
        o = dict(self.out)
        if i["rst_n"] == 0:
            o["out_vld"], o["out_sel"] = 0, 0
            self.sum1 = self.sum2 = self.mux1 = self.mux2 = 0
        else:
            o["out_vld"], o["out_sel"] = i["issue_vld"], i["issue_sel"]
            o["a_out"], o["b_out"] = self.mux1, self.mux2
            if i["issue_vld"] == 1:
                o["out_id"] = self.id

            sel = i["sel"]
            counted = self.tags if sel == USE_SUM else None      # only when the sum is used
            summed = sum_sat(self.sum1, self.sum2, i["sub"], counted)
            if sel == LOAD_SUM:
                self.sum1, self.sum2 = i["in_a"], i["in_b"]
            elif sel in (LOAD_AB, USE_SUM, USE_LOCAL):
                self.mux1, self.id = i["in_a"], i["in_id"]
                self.mux2 = {LOAD_AB: i["in_b"], USE_SUM: summed,
                             USE_LOCAL: i["local_data"]}[sel]
        self.out = o
        return dict(o)


MuxNode = LeafSpec(
    module="pe_input_mux",
    input_specs=MUX_INPUT_SPEC,
    output_specs=MUX_OUTPUT_SPEC,
    golden=PeInputMux,
)
