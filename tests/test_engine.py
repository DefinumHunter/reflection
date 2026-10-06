"""The engine on small synthetic modules (tests/rtl/fixtures.sv), not project RTL."""
from pathlib import Path

import pytest

from Engine.Core import LeafSpec
from Engine.Model import CombLoopError, Model
from Engine.Netlist import NetlistError, load

FIX = Path(__file__).resolve().parent / "rtl" / "fixtures.sv"


class Inc8:
    def tick(self, i):
        return {"y": None if i["a"] is None else (i["a"] + 1) & 0xFF}


class Reg8:
    def __init__(self, q=None):
        self.q = q

    def start(self):
        return {"q": self.q}

    def tick(self, i):
        self.q = i["d"]
        return {"q": self.q}


INC = LeafSpec(module="inc8", golden=Inc8, comb={"y"})
REG = LeafSpec(module="reg8", golden=Reg8)
FIXTURES = {"inc8": INC, "reg8": REG}


def test_comb_chain_settles_in_one_cycle_regardless_of_order():
    m = Model.from_rtl([FIX], "tb_chain", FIXTURES)
    assert m.step({"x": 5})["y"] == 8
    assert m.peek("m1") == 6 and m.peek("m2") == 7


def test_comb_loop_is_reported():
    m = Model.from_rtl([FIX], "tb_loop", FIXTURES)
    with pytest.raises(CombLoopError, match="u1.*u2|u2.*u1"):
        m.step()


def test_loop_through_register_is_fine():
    m = Model.from_rtl([FIX], "tb_counter", FIXTURES, init={"u_reg": {"q": 0}})
    assert [m.step()["q"] for _ in range(5)] == [0, 1, 2, 3, 4]


def test_hierarchy_generate_and_assign_are_flattened():
    nl = load([FIX], "tb_hier", FIXTURES)
    assert sorted(l.path for l in nl.leaves) == sorted(
        f"g[{i}].p.i{j}" for i in range(3) for j in range(2))
    assert Model(nl, FIXTURES).step({"x": 10})["y"] == 16


def test_tb_parameter_override():
    nl = load([FIX], "tb_hier", FIXTURES, params={"N": 5})
    assert len(nl.leaves) == 10
    assert Model(nl, FIXTURES).step({"x": 0})["y"] == 10


def test_missing_component_for_behavioural_module_is_an_error():
    with pytest.raises(NetlistError, match="u_reg.*no component"):
        load([FIX], "tb_counter", {"inc8": INC})
