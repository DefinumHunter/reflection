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


# --- unpacked arrays ----------------------------------------------------------

ARR = [Path(__file__).resolve().parent / "rtl" / f for f in ("arrays.sv", "arrays_tb.sv")]


class Vadd3:
    def tick(self, i):
        assert isinstance(i["a"], list) and len(i["a"]) == 3     # array port = list
        return {"y": [(v + i["k"] + n) & 0xFF for n, v in enumerate(i["a"])]}


class Sum3:
    def tick(self, i):
        return {"s": sum(i["v"]) & 0xFF}


ARRAYS = {"vadd3": LeafSpec(module="vadd3", golden=Vadd3, comb={"y"}),
          "sum3": LeafSpec(module="sum3", golden=Sum3, comb={"s"}),
          "inc8": INC}


def test_array_ports_become_one_tb_signal_per_element():
    nl = load(ARR, "tb_arrays", ARRAYS)       # also: default timescale for arrays.sv
    assert list(nl.inputs) == ["a[0]", "a[1]", "a[2]", "k"]
    assert list(nl.outputs) == ["y[0]", "y[1]", "y[2]", "s"]
    assert all(nl.widths[n] == 8 for n in [*nl.inputs, *nl.outputs])
    u1 = next(l for l in nl.leaves if l.path == "dut.u1")
    assert u1.arrays == {"a": ["a[0]", "a[1]", "a[2]"], "y": ["y[0]", "y[1]", "y[2]"]}


def test_goldens_see_arrays_as_lists_and_arrays_connect_by_position():
    m = Model.from_rtl(ARR, "tb_arrays", ARRAYS)
    out = m.step({"a[0]": 10, "a[1]": 20, "a[2]": 30, "k": 1})
    y = [10 + 1 + 0 + 1 + 0, 20 + 1 + 1 + 1 + 1, 30 + 1 + 2 + 1 + 2]   # through u1, then u2
    assert [out[f"y[{n}]"] for n in range(3)] == y
    assert out["s"] == sum(y)


def test_array_elements_in_connection_check():
    from Engine.Connections import actual
    got = actual(load(ARR, "tb_arrays", ARRAYS), "dut")
    assert got["a[1]"] == {"u1.a[1]"}
    assert got["u1.y[0]"] == {"u2.a[0]"}
    assert got["u2.y[2]"] == {"u3.v[2]", "y[2]"}


def test_golden_returning_wrong_array_size_is_reported():
    class Short:
        def tick(self, i):
            return {"y": [0, 0]}
    comps = {**ARRAYS, "vadd3": LeafSpec(module="vadd3", golden=Short, comb={"y"})}
    with pytest.raises(ValueError, match="'y' is an array of 3"):
        Model.from_rtl(ARR, "tb_arrays", comps).step({"a[0]": 0, "a[1]": 0, "a[2]": 0, "k": 0})


def test_one_element_of_a_tb_array_on_a_plain_port():
    m = Model.from_rtl([FIX] + ARR, "tb_pick", ARRAYS)
    assert m.step({"arr[0]": 0, "arr[1]": 41, "arr[2]": 0})["o"] == 42


# --- finding components by file name -------------------------------------------

def _package(tmp_path, name, files):
    import sys
    pkg = tmp_path / name
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for fname, text in files.items():
        (pkg / fname).write_text(text)
    sys.path.insert(0, str(tmp_path))
    return name


SPEC = "from Engine.Core import LeafSpec\nclass G:\n    pass\n"


def test_components_are_found_by_file_name(tmp_path):
    from Engine.Core import find_leaves
    name = _package(tmp_path, "comps_ok", {
        "inc8_node.py": SPEC + "NODE = LeafSpec(golden=G, comb={'y'})\n",
        "helpers.py": "raise RuntimeError('helpers are not imported by the search')\n"})
    found = find_leaves(name)
    assert list(found) == ["inc8"] and found["inc8"].module == "inc8"


def test_component_file_without_node_is_reported(tmp_path):
    from Engine.Core import find_leaves
    name = _package(tmp_path, "comps_nonode", {"inc8_node.py": SPEC + "SPEC = LeafSpec(golden=G)\n"})
    with pytest.raises(ValueError, match="inc8_node.py: needs NODE"):
        find_leaves(name)


def test_component_module_must_match_file_name(tmp_path):
    from Engine.Core import find_leaves
    name = _package(tmp_path, "comps_mismatch",
                    {"inc8_node.py": SPEC + "NODE = LeafSpec(golden=G, module='reg8')\n"})
    with pytest.raises(ValueError, match="file name says 'inc8'"):
        find_leaves(name)


def test_missing_component_error_names_the_file():
    with pytest.raises(NetlistError, match="Components/reg8_node.py"):
        load([FIX], "tb_counter", {"inc8": INC})
