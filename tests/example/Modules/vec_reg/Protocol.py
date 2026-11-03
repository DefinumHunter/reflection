"""vec_reg transactions. Array elements are separate inputs: "a[0]", "a[1]", ..."""
from dataclasses import dataclass

IDLE = {"rst_n": 1, "a[0]": 0, "a[1]": 0, "a[2]": 0, "k": 0}


@dataclass
class Reset:
    length: int = 2
    no_overlap = True

    def cycles(self):
        return [{"rst_n": 0}] * self.length


@dataclass
class Lanes:
    a: list = None          # three values, one per lane
    k: int = None

    def cycles(self):
        return [{"a[0]": self.a[0], "a[1]": self.a[1], "a[2]": self.a[2], "k": self.k}]
