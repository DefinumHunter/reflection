# Components/pe_output_strapping_node.py
from Engine.Core import LeafSpec
from Engine.Fixed import to_signed, saturate


def post_sum(neighbor_res, mac_res, sub_post, tags: list = None):
    """neighbor +- mac, saturated to signed 32. X in -> X out. Optional coverage tags."""
    if neighbor_res is None or mac_res is None or sub_post is None:
        return None
    n, m = to_signed(neighbor_res), to_signed(mac_res)
    raw = n - m if sub_post else n + m
    if tags is not None:
        tags.append("post_sub" if sub_post else "post_add")
        tags.append("post_sat_pos" if raw > 0x7FFFFFFF else
                    "post_sat_neg" if raw < -0x80000000 else "post_sat_none")
    return saturate(raw)


def _and(a, b):
    """Verilog && with X: any 0 -> 0, else any X -> X, else 1."""
    if a == 0 or b == 0:
        return 0
    if a is None or b is None:
        return None
    return 1


def _not(a):
    return None if a is None else 1 - a


class PeOutputStrapping:
    """pe_output_strapping golden model. See docs/pe_output_strapping.md.

    stage 1: mac, neighbor, id, ring, sub (every clock); valid (mac_vld and the
             neighbor check); error (sticky, set when the check fails).
    stage 2: out = sat(neighbor +- mac), out_id (every clock);
             out_valid_ring / out_valid_final from stage-1 valid and ring.
    Result: 2 clocks after mac_vld. Reset clears only the valids and error.
    """

    def __init__(self, CHECK_NEIGHBOR=1):
        self.check = CHECK_NEIGHBOR
        self.tags = []
        # power-up: everything X
        self.mac = self.neighbor = self.id = self.ring = self.sub = None
        self.valid = None
        self.error = None
        self.out = {"out": None, "out_id": None,
                    "out_valid_ring": None, "out_valid_final": None}

    def start(self):
        return {**self.out, "error": self.error}

    def _match(self, i):
        """The neighbor check of this clock: 1, 0 or None (X)."""
        if not self.check:
            return 1
        if i["neighbor_vld"] == 0:
            return 0
        if None in (i["neighbor_vld"], i["neighbor_id"], i["mac_id"]):
            return None
        return int(i["neighbor_id"] == i["mac_id"])

    def tick(self, i: dict) -> dict:
        # comb, from the state before the edge
        idle = _and(_and(_not(self.valid), _not(self.out["out_valid_ring"])),
                    _not(self.out["out_valid_final"]))

        # ---- edge: stage 2 from the old stage 1 ----
        counted = self.tags if self.valid == 1 and i["rst_n"] == 1 else None
        o = {"out": post_sum(self.neighbor, self.mac, self.sub, counted),
             "out_id": self.id}
        if i["rst_n"] == 0:
            o["out_valid_ring"] = o["out_valid_final"] = 0
        else:
            o["out_valid_ring"] = _and(self.ring, self.valid)
            o["out_valid_final"] = _and(_not(self.ring), self.valid)

        # ---- edge: stage 1 from the inputs ----
        match = self._match(i)
        if i["rst_n"] == 0:
            self.valid, self.error = 0, 0
        else:
            self.valid = _and(i["mac_vld"], match)
            failed = _and(i["mac_vld"], _not(match))
            if failed == 1:
                self.error = 1
            elif failed is None and self.error != 1:
                self.error = None
        self.mac, self.neighbor = i["mac_res"], i["neighbor_res"]
        self.id, self.ring, self.sub = i["mac_id"], i["mac_ring_final"], i["mac_sub_post"]

        self.out = o
        return {**o, "error": self.error, "idle": idle}


NODE = LeafSpec(golden=PeOutputStrapping, comb={"idle"})