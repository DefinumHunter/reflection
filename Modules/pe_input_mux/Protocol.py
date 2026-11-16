"""Clock-accurate input operations for pe_input_mux."""
from dataclasses import dataclass

IDLE = {
    "rst_n": 1, "in_a": 0, "in_b": 0, "local_data": 0,
    "sel": 0, "sub_pre": 0, "issue_vld": 0,
    "ring_final": 0, "sub_post": 0, "in_id": 0,
}

@dataclass
class Direct:
    a: int = None
    b: int = None
    id: int = None
    ring_final: int = None
    sub_post: int = None
    issue: int = 1

    def cycles(self):
        return [{"sel": 0, "in_a": self.a, "in_b": self.b,
                 "issue_vld": self.issue, "in_id": self.id,
                 "ring_final": self.ring_final, "sub_post": self.sub_post}]

@dataclass
class Local:
    a: int = None
    local: int = None
    id: int = None
    ring_final: int = None
    sub_post: int = None
    issue: int = 1

    def cycles(self):
        return [{"sel": 3, "in_a": self.a, "local_data": self.local,
                 "issue_vld": self.issue, "in_id": self.id,
                 "ring_final": self.ring_final, "sub_post": self.sub_post}]

@dataclass
class PreSum:
    a: int = None
    b: int = None
    c: int = None
    sub_pre: int = None
    id: int = None
    ring_final: int = None
    sub_post: int = None

    def cycles(self):
        return [
            {"sel": 1, "in_a": self.a, "in_b": self.b,
             "sub_pre": self.sub_pre, "issue_vld": 0},
            {"sel": 2, "in_a": self.c, "sub_pre": self.sub_pre,
             "issue_vld": 1, "in_id": self.id,
             "ring_final": self.ring_final, "sub_post": self.sub_post},
        ]

@dataclass
class Reset:
    length: int = 3
    no_overlap = True

    def cycles(self):
        return [{"rst_n": 0}] * self.length
