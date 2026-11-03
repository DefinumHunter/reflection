from Engine.Core import LeafSpec


class VecReg:
    """vec_reg: y[i] <= a[i] + k + i (8 bit, reset to 0); s = y[0] + y[1] + y[2], comb."""

    def __init__(self, y=None):
        self.tags = []
        self.y = list(y) if y is not None else [None] * 3

    def start(self):
        return {"y": list(self.y)}

    def tick(self, i):
        # comb, from the state before the edge
        s = None if None in self.y else sum(self.y) & 0xFF
        if s is not None:
            self.tags.append("sum_wraps" if sum(self.y) > 0xFF else "sum_fits")
        # clk edge
        if i["rst_n"] == 0:
            self.y = [0, 0, 0]
        elif i["k"] is None or None in i["a"]:
            self.y = [None] * 3
        else:
            self.y = [(v + i["k"] + n) & 0xFF for n, v in enumerate(i["a"])]
        return {"y": list(self.y), "s": s}


NODE = LeafSpec(golden=VecReg, comb={"s"})
