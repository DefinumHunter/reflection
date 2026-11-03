"""Engine/MakeTb.py on the worked example."""
from Engine.MakeTb import tb_text
from Engine.Netlist import load
import Project


def test_made_tb_matches_the_ports_and_loads(tmp_path):
    text = tb_text("vec_reg")
    assert "module tb_vec_reg;" in text and "vec_reg dut (.*);" in text
    assert "logic [7:0] a [0:2];" in text.replace("  ", " ").replace("  ", " ")
    assert "wire  [7:0] y [0:2];" in text           # output array -> wire
    tb = tmp_path / "tb_vec_reg.sv"
    tb.write_text(text)
    nl = load(Project.rtl_sources() + [tb], "tb_vec_reg", Project.components())
    assert list(nl.inputs) == ["rst_n", "a[0]", "a[1]", "a[2]", "k"]


def test_made_tb_forwards_parameters():
    text = tb_text("mac_q16")
    assert "parameter int PIPELINE_STAGES = 4;" in text
    assert "mac_q16 #(.PIPELINE_STAGES(PIPELINE_STAGES)) dut (.*);" in text
