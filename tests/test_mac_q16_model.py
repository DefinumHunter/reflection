"""mac_q16 alone: stateful golden, timing, reset/X, and a cycle-exact check
against the real RTL in Icarus (skipped if iverilog is not installed)."""
import random

import pytest

import Project
from Components.MacNode import mac_q16_golden
from tests import icarus

MODULE = "mac_q16"
IDLE = {"rst_n": 1, "in_vld": 0, "sel": 0, "in_a": 0, "in_b": 0, "in_id": 0}


def mac_model(stages=None, init=None):
    params = {"PIPELINE_STAGES": stages} if stages is not None else None
    return Project.model(MODULE, params=params, init=init)


def run_reset(m, cycles):
    for _ in range(cycles):
        m.step({**IDLE, "rst_n": 0})


def expected(a, b):
    return mac_q16_golden({"in_a": a, "in_b": b})["out_res"]


def test_tb_is_the_boundary():
    nl = Project.netlist(MODULE)
    assert set(nl.inputs) == {"rst_n", "in_vld", "sel", "in_a", "in_b", "in_id"}
    assert set(nl.outputs) == {"busy", "out_vld", "out_sel", "out_res", "out_id"}
    [leaf] = nl.leaves
    assert (leaf.path, leaf.module, leaf.params) == ("dut", "mac_q16", {"PIPELINE_STAGES": 4})


@pytest.mark.parametrize("stages", [4, 6, 1])
def test_latency_follows_rtl_parameter(stages):
    m = mac_model(stages)
    run_reset(m, stages)
    a, b = 0x00030000, 0x00028000          # 3.0 * 2.5
    seen = [m.step({**IDLE, "in_vld": 1, "sel": 1, "in_a": a, "in_b": b, "in_id": 9})]
    seen += [m.step(IDLE) for _ in range(stages + 1)]
    hits = [c for c, o in enumerate(seen) if o["out_vld"] == 1]
    assert hits == [stages]
    o = seen[stages]
    assert (o["out_res"], o["out_sel"], o["out_id"]) == (expected(a, b), 1, 9)
    assert o["out_res"] == 0x00078000


def test_busy_rises_in_the_same_cycle():
    m = mac_model()
    run_reset(m, 4)
    assert m.step(IDLE)["busy"] == 0
    assert m.step({**IDLE, "in_vld": 1})["busy"] == 1   # comb: no wait
    for _ in range(4):
        assert m.step(IDLE)["busy"] == 1                 # still in the pipe
    assert m.step(IDLE)["busy"] == 0


def test_long_reset_fills_data_pipe_with_zeros():
    m = mac_model()
    assert m.step(IDLE)["out_res"] is None               # power-up: X
    run_reset(m, 4)
    assert m.step(IDLE)["out_res"] == 0                  # zeros flowed in during reset


def test_short_reset_leaves_x_in_the_tail():
    m = mac_model()
    run_reset(m, 2)                                      # pipe: 0, 0, X, X
    outs = [m.step(IDLE) for _ in range(4)]
    assert [o["out_res"] for o in outs] == [None, None, 0, 0]
    assert all(o["out_vld"] == 0 for o in outs)          # vld pipe is reset


def test_rst_n_x_takes_else_branch_like_verilog():
    m = mac_model()
    for _ in range(4):
        m.step({**IDLE, "rst_n": None, "in_vld": 1})
    assert m.step(IDLE)["out_vld"] == 1


def test_manual_initial_pipeline():
    m = mac_model(init={"dut": {"pipe": [1, 2, 3, 4], "vld_pipe": [0, 0, 0, 1],
                                "sel_pipe": [0, 0, 0, 0], "id_pipe": [0, 0, 0, 0]}})
    assert [m.step(IDLE)["out_res"] for _ in range(4)] == [4, 3, 2, 1]


def test_init_with_wrong_length_is_rejected():
    with pytest.raises(ValueError):
        mac_model(init={"dut": {"pipe": [1, 2]}})


# --- model against the real RTL (Icarus) ------------------------------------

CORNERS = [0x00000000, 0x00010000, 0x00008000, 0x7FFFFFFF, 0x80000000,
           0xFFFFFFFF, 0x00000001, 0xFFFF0000, 0x40000000, 0x00020000]


def _stimulus(seed, n=400):
    rnd = random.Random(seed)
    word = lambda: rnd.choice(CORNERS) if rnd.random() < 0.15 else rnd.getrandbits(32)
    rows = [dict(IDLE) for _ in range(3)]                      # no reset yet: X state
    rows += [{**IDLE, "rst_n": 0} for _ in range(2)]           # short reset
    for c in range(n):
        rows.append({"rst_n": 0 if 200 <= c < 203 else 1,      # reset mid-stream,
                     "in_vld": int(rnd.random() < 0.8),        # data keeps flowing
                     "sel": rnd.getrandbits(1), "in_a": word(), "in_b": word(),
                     "in_id": rnd.getrandbits(4)})
    return rows


@pytest.mark.skipif(not icarus.available, reason="iverilog not installed")
@pytest.mark.parametrize("stages", [4, 3])
def test_model_matches_rtl(tmp_path, stages):
    params = {"PIPELINE_STAGES": stages}
    m = Project.model(MODULE, params=params)
    rows = _stimulus(seed=stages)
    rtl = icarus.run(Project.sources(MODULE), Project.tb(MODULE), m.inputs, m.outputs,
                     rows, tmp_path, params=params)
    model = [m.step(r) for r in rows]

    assert len(rtl) == len(model) == len(rows)
    diffs = icarus.diff(model, rtl)
    assert not diffs, f"{len(diffs)} mismatches, first: {diffs[:5]}"
    assert sum(o["out_vld"] == 1 for o in model) > 250   # the check actually saw data
