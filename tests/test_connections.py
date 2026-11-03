"""Hand-written connection list vs the RTL."""
import json

import pytest

import Project
from Engine.Connections import ConnectionMismatch, check, check_file
from Engine.Netlist import load

MODULE = "pe_mac_wrapper"


def spec():
    return json.loads(Project.connections_file(MODULE).read_text(encoding="utf-8"))


def wrapper_netlist(tmp_path, edit=None):
    """Netlist of the wrapper, optionally with its RTL edited (old, new)."""
    files = Project.sources(MODULE)
    if edit:
        files = [f for f in files if f.name != "pe_mac_wrapper.sv"]
        text = (Project.RTL_DIR / "pe_mac_wrapper.sv").read_text(encoding="utf-8")
        assert edit[0] in text
        broken = tmp_path / "pe_mac_wrapper.sv"
        broken.write_text(text.replace(*edit), encoding="utf-8")
        files.append(broken)
    return load(files, Project.tb(MODULE), Project.components(), Project.CLOCKS)


def test_project_list_matches_rtl():
    assert check(Project.netlist(MODULE, check_connections=False), spec()) == []


def test_build_checks_connections_automatically(tmp_path):
    nl = wrapper_netlist(tmp_path, (".sel    (mux_out_sel),", ".sel    (mac_sel_in),"))
    with pytest.raises(ConnectionMismatch):
        check_file(nl, Project.connections_file(MODULE))


def test_old_sel_bug_is_reported_exactly(tmp_path):
    nl = wrapper_netlist(tmp_path, (".sel    (mux_out_sel),", ".sel    (mac_sel_in),"))
    problems = check(nl, spec())
    assert "u_mux.out_sel -> u_mac.sel expected, but in the RTL u_mac.sel is driven by mac_sel_in" in problems
    assert "mac_sel_in -> u_mac.sel is in the RTL but not in the list" in problems


def test_swapped_data_is_reported(tmp_path):
    nl = wrapper_netlist(tmp_path, (".in_a   (mux_a_out),", ".in_a   (mux_b_out),"))
    problems = check(nl, spec())
    assert any("u_mux.a_out -> u_mac.in_a expected" in p for p in problems)
    assert any("u_mux.b_out -> u_mac.in_a is in the RTL" in p for p in problems)


def test_unconnected_input_is_reported(tmp_path):
    nl = wrapper_netlist(tmp_path, (".in_id  (mux_out_id),", ".in_id  (),"))
    assert "u_mac.in_id is not driven by anything" in check(nl, spec())


def test_forgotten_line_is_reported():
    s = spec()
    del s["connections"]["u_mux.out_id"]
    problems = check(Project.netlist(MODULE, check_connections=False), s)
    assert problems == ["u_mux.out_id -> u_mac.in_id is in the RTL but u_mux.out_id is not in the list"]


def test_typos_and_direction_mistakes_are_reported():
    s = spec()
    s["connections"]["u_mux.a_out"] = ["u_mac.in_aa"]
    s["connections"]["u_mac.sel"] = ["out_sel"]
    problems = check(Project.netlist(MODULE, check_connections=False), s)
    assert "u_mux.a_out -> u_mac.in_aa: u_mac.in_aa is not an input port or a TB output" in problems
    assert "u_mac.sel is an input, it cannot be a source" in problems
    assert "out_sel is listed under two sources: u_mac.out_sel and u_mac.sel" in problems
