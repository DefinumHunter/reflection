"""The full UVM bench (pyuvm + cocotb + Icarus) on each module, plus
deliberately broken RTL that it must catch. Slower than the rest (~1-2 s per
run); skipped if cocotb/pyuvm or Icarus are missing."""
import importlib.util

import pytest

import Project
from tests import icarus

pytestmark = pytest.mark.skipif(
    not icarus.available or importlib.util.find_spec("pyuvm") is None,
    reason="needs iverilog, cocotb and pyuvm")


def run(module, tmp_path, **kw):
    from Engine.Run import run as run_uvm
    return run_uvm(module, build_dir=tmp_path / "sim", **kw)


def broken(module, tmp_path, fname, old, new):
    files = []
    for f in Project.sources(module):
        if f.name == fname:
            text = f.read_text(encoding="utf-8")
            assert old in text, old
            (tmp_path / fname).write_text(text.replace(old, new), encoding="utf-8")
            f = tmp_path / fname
        files.append(f)
    return files


@pytest.mark.parametrize("module,params", [
    ("mac_q16", None), ("mac_q16", {"PIPELINE_STAGES": 7}),
    ("pe_mac_wrapper", None), ("pe_mac_wrapper", {"PIPELINE_STAGES": 2}),
])
def test_bench_passes_on_correct_rtl(tmp_path, module, params):
    assert run(module, tmp_path, params=params) == 0


def test_bench_catches_rounding_bug(tmp_path):
    files = broken("mac_q16", tmp_path, "mac_q16.sv",
                   "assign round  = guard & (sticky | lsb);",
                   "assign round  = guard & sticky;")
    assert run("mac_q16", tmp_path, sources=files) == 1


def test_bench_catches_out_id_from_wrong_register(tmp_path):
    # out_id taken from the live input instead of the id latched at load time
    files = broken("pe_mac_wrapper", tmp_path, "pe_input_mux.sv",
                   "                out_id <= local_id_mux;",
                   "                out_id <= in_id;")
    assert run("pe_mac_wrapper", tmp_path, sources=files) == 1


def test_capture_every_clock_is_invisible_under_legal_traffic(tmp_path):
    # Capturing out_id every clock instead of on issue_vld cannot be seen when
    # the mux is driven by the protocol: the latched id only changes on a load,
    # and every load is issued on the next clock. Documented here on purpose.
    files = broken("pe_mac_wrapper", tmp_path, "pe_input_mux.sv",
                   "            if (issue_vld) begin\n                out_id <= local_id_mux;\n            end",
                   "            out_id <= local_id_mux;")
    assert run("pe_mac_wrapper", tmp_path, sources=files) == 0


def test_bench_stops_on_wiring_bug_before_simulating(tmp_path):
    files = broken("pe_mac_wrapper", tmp_path, "pe_mac_wrapper.sv",
                   ".sel    (mux_out_sel),", ".sel    (mac_sel_in),")
    assert run("pe_mac_wrapper", tmp_path, sources=files) == 1


# --- coverage through the bench ---------------------------------------------------

@pytest.mark.parametrize("module", ["mac_q16", "pe_mac_wrapper"])
def test_bench_coverage_equals_model_only_coverage(tmp_path, module):
    """The tags counted in the simulation come from the model fed by the input
    monitor, i.e. from what the DUT really saw. They must be the same as in a
    model-only run of the same test."""
    from Engine import Coverage
    assert run(module, tmp_path) == 0
    bench = Coverage.load(tmp_path / "sim" / "coverage.json")
    assert bench == Project.dry_run(module)
    assert Coverage.holes(bench) == {}


def test_regression_over_seeds_merges_coverage(tmp_path):
    from Engine import Coverage
    from Engine.Run import regress
    failed, merged = regress("mac_q16", 3, build_dir=tmp_path / "sim")
    assert failed == []
    one = Project.dry_run("mac_q16", 1)
    assert merged["points"]["vld"]["hits"]["1"] > 2 * one["points"]["vld"]["hits"]["1"]
    assert Coverage.load(tmp_path / "sim" / "coverage_merged.json") == merged


def test_coverage_is_saved_even_when_the_scoreboard_fails(tmp_path):
    files = broken("mac_q16", tmp_path, "mac_q16.sv",
                   "assign round  = guard & (sticky | lsb);",
                   "assign round  = guard & sticky;")
    assert run("mac_q16", tmp_path, sources=files) == 1
    assert (tmp_path / "sim" / "coverage.json").exists()
