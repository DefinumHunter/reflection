"""mac_q16 transactions. The module streams: one transaction is one clock."""
from dataclasses import dataclass

# What every clock looks like when no transaction drives it.
IDLE = dict(rst_n=1, in_vld=0, sel=0, in_a=0, in_b=0, in_id=0)


@dataclass
class Reset:
    length: int = 5
    no_overlap = True          # a load under reset would be lost

    def cycles(self):
        return [dict(rst_n=0)] * self.length


@dataclass
class Mac:
    """One multiply. vld = 0 still pushes the data down the pipe, like the RTL."""
    a: int = None
    b: int = None
    vld: int = None
    sel: int = None
    id: int = None

    def cycles(self):
        return [dict(in_a=self.a, in_b=self.b, in_vld=self.vld, sel=self.sel, in_id=self.id)]
