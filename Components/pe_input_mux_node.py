# Components/pe_input_nux.py
from Engine.Core import LeafSpec
from Engine.Fixed import to_signed, saturate

# sel modes
SEL_AB    = 0b00
SEL_SUM   = 0b01
SEL_SUM_C = 0b10
SEL_LOCAL = 0b11


def sum_sat(sum1, sum2, sub, tags: list = None):
    """sum1 ± sum2 with 33-bit intermediate, then saturate to signed 32.
    X in → X out. Optional coverage tags."""
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
    """pe_input_mux golden model.

    Two pipeline stages after the pre-sum registers.
    Result (data + valid + id + flags) appears exactly 2 cycles after
    the cycle that had issue_vld=1.
    """

    def __init__(self,
                 # pre-sum
                 sum1=None, sum2=None,
                 # stage 1
                 op1=None, op2=None, vld=None,
                 id_reg=None, ring_reg=None, subpost_reg=None,
                 # stage 2 (outputs)
                 a_out=None, b_out=None, out_vld=None,
                 out_id=None, out_ring_final=None, out_sub_post=None):
        self.tags = []

        # pre-sum registers
        self.sum1 = sum1
        self.sum2 = sum2

        # stage 1
        self.op1 = op1
        self.op2 = op2
        self.vld = vld
        self.id_reg = id_reg
        self.ring_reg = ring_reg
        self.subpost_reg = subpost_reg

        # stage 2
        self.out = {
            "a_out": a_out,
            "b_out": b_out,
            "out_vld": out_vld,
            "out_id": out_id,
            "out_ring_final": out_ring_final,
            "out_sub_post": out_sub_post,
        }

    def start(self):
        return dict(self.out)

    def tick(self, i: dict) -> dict:
        # ---------- stage 2 (reads stage 1) ----------
        o = {
            "a_out": self.op1,
            "b_out": self.op2,
            "out_vld": self.vld,
            "out_id": self.out["out_id"],
            "out_ring_final": self.out["out_ring_final"],
            "out_sub_post": self.out["out_sub_post"],
        }
        if self.vld == 1:
            o["out_id"] = self.id_reg
            o["out_ring_final"] = self.ring_reg
            o["out_sub_post"] = self.subpost_reg

        # ---------- id + flags (RTL writes them even under reset) ----------
        if i["issue_vld"] == 1:
            self.id_reg = i["in_id"]
            self.ring_reg = i["ring_final"]
            self.subpost_reg = i["sub_post"]

        # ---------- stage 1 + pre-sum ----------
        if i["rst_n"] == 0:
            self.sum1 = 0
            self.sum2 = 0
            self.op1 = 0
            self.op2 = 0
            self.vld = 0
            o["out_vld"] = 0
        else:
            sel = i["sel"]
            issue = i["issue_vld"]

            # pre-sum load
            if sel == SEL_SUM:
                self.sum1 = i["in_a"]
                self.sum2 = i["in_b"]

            # stage-1 operand registers
            if sel in (SEL_AB, SEL_SUM_C, SEL_LOCAL):
                self.op1 = i["in_a"]
                if sel == SEL_AB:
                    self.op2 = i["in_b"]
                elif sel == SEL_LOCAL:
                    self.op2 = i["local_data"]
                else:  # SEL_SUM_C
                    counted = self.tags if issue == 1 else None
                    self.op2 = sum_sat(self.sum1, self.sum2,
                                       i["sub_pre"], counted)

            # stage-1 valid
            self.vld = issue

        self.out = o
        return dict(o)


NODE = LeafSpec(
    module="pe_input_mux",
    golden=PeInputMux,
)