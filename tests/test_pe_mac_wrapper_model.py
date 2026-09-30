"""Two real modules through one net: pe_input_mux -> mac_q16 inside pe_mac_wrapper.

The directed tests encode the intent (what each sel mode must compute, and
that sel/id stay with their result). The Icarus test checks that the model
reproduces the RTL cycle for cycle; it cannot catch a wrong connection in the
wrapper, since the model takes its connections from that same RTL -- that is
what Modules/pe_mac_wrapper/Connections.json is for (checked on every build).
"""
import random

import pytest

import Project
from Components.MacNode import mac_q16_golden
from Components.MuxNode import LOAD_AB, LOAD_SUM, USE_LOCAL, USE_SUM
from tests import icarus

MODULE = "pe_mac_wrapper"

# sel = LOAD_SUM with zeros only touches sum1/sum2, never mux1/mux2/id
NOP = {"rst_n": 1, "local_data": 0, "sub": 0, "in_a": 0, "in_b": 0,
       "sel": LOAD_SUM, "in_id": 0, "issue_vld": 0, "mac_sel_in": 0}

Q = lambda x: int(x * 65536) & 0xFFFFFFFF          # Q16.16 constant


def model(stages=None):
    return Project.model(MODULE, params={"PIPELINE_STAGES": stages} if stages else None)


def mul(a, b):
    return mac_q16_golden({"in_a": a, "in_b": b})["out_res"]


def run(m, rows, tail=8):
    for _ in range(4):
        m.step({**NOP, "rst_n": 0})
    return [m.step({**NOP, **r}) for r in rows] + [m.step(NOP) for _ in range(tail)]


def results(outs):
    return [(o["out_res"], o["out_sel"], o["out_id"]) for o in outs if o["out_vld"] == 1]


def test_structure():
    nl = Project.netlist(MODULE)
    assert {(l.path, l.module) for l in nl.leaves} == {("dut.u_mux", "pe_input_mux"),
                                                       ("dut.u_mac", "mac_q16")}
    assert set(nl.outputs) == {"out_vld", "out_sel", "out_res", "out_id", "busy"}
    assert "issue_vld" in nl.inputs and "mac_sel_in" in nl.inputs


@pytest.mark.parametrize("stages", [4, 2])
def test_latency_is_one_plus_pipeline_from_issue(stages):
    m = model(stages)
    outs = run(m, [{"sel": LOAD_AB, "in_a": Q(3), "in_b": Q(2.5), "in_id": 7},
                   {"issue_vld": 1, "mac_sel_in": 1}])
    issue = 1
    hits = [c for c, o in enumerate(outs) if o["out_vld"] == 1]
    assert hits == [issue + 1 + stages]
    o = outs[hits[0]]
    assert (o["out_res"], o["out_sel"], o["out_id"]) == (Q(7.5), 1, 7)


def test_mode_a_times_b():
    m = model()
    outs = run(m, [{"sel": LOAD_AB, "in_a": Q(-1.5), "in_b": Q(4), "in_id": 1},
                   {"issue_vld": 1}])
    assert results(outs) == [(Q(-6), 0, 1)]


@pytest.mark.parametrize("sub", [0, 1])
def test_mode_c_times_sum(sub):
    a, b, c = Q(3), Q(1.25), Q(2)
    m = model()
    outs = run(m, [{"sel": LOAD_SUM, "in_a": a, "in_b": b},
                   {"sel": USE_SUM, "in_a": c, "sub": sub, "in_id": 5},
                   {"issue_vld": 1, "mac_sel_in": 1}])
    expected = Q(2 * (3 - 1.25)) if sub else Q(2 * (3 + 1.25))
    assert results(outs) == [(expected, 1, 5)]


def test_sum_saturates_before_mac():
    big = 0x7FFFFFFF
    m = model()
    outs = run(m, [{"sel": LOAD_SUM, "in_a": big, "in_b": big},
                   {"sel": USE_SUM, "in_a": Q(1), "in_id": 2},
                   {"issue_vld": 1}])
    assert results(outs) == [(mul(Q(1), big), 0, 2)]


def test_mode_a_times_local_data():
    m = model()
    outs = run(m, [{"sel": USE_LOCAL, "in_a": Q(0.5), "local_data": Q(10), "in_id": 3},
                   {"issue_vld": 1}])
    assert results(outs) == [(Q(5), 0, 3)]


def test_back_to_back_keeps_sel_and_id_with_their_result():
    rnd = random.Random(1)
    txs = [(rnd.getrandbits(32), rnd.getrandbits(32), i % 16, i % 2) for i in range(10)]
    rows = []
    for k in range(len(txs) + 1):
        r = {}
        if k < len(txs):                       # load transaction k
            a, b, tid, _ = txs[k]
            r.update(sel=LOAD_AB, in_a=a, in_b=b, in_id=tid)
        if k > 0:                              # issue transaction k-1
            r.update(issue_vld=1, mac_sel_in=txs[k - 1][3])
        rows.append(r)
    m = model()
    got = results(run(m, rows))
    assert got == [(mul(a, b), s, tid) for a, b, tid, s in txs]


def test_idle_between_load_and_issue_keeps_the_data():
    m = model()
    outs = run(m, [{"sel": LOAD_AB, "in_a": Q(2), "in_b": Q(3), "in_id": 4},
                   {}, {}, {},
                   {"issue_vld": 1}])
    assert results(outs) == [(Q(6), 0, 4)]


# --- model against the real RTL (Icarus) ------------------------------------

CORNERS = [0x00000000, 0x00010000, 0x00008000, 0x7FFFFFFF, 0x80000000,
           0xFFFFFFFF, 0x00000001, 0xFFFF0000, 0x40000000, 0x00020000]


def _stimulus(seed, n=500):
    rnd = random.Random(seed)
    word = lambda: rnd.choice(CORNERS) if rnd.random() < 0.2 else rnd.getrandbits(32)
    rows = [{**NOP, "sel": None, "issue_vld": None} for _ in range(3)]  # all X at power-up
    rows += [{**NOP, "rst_n": 0} for _ in range(2)]
    for c in range(n):
        rows.append({"rst_n": 0 if 300 <= c < 302 else 1,
                     "local_data": word(), "sub": rnd.getrandbits(1),
                     "in_a": word(), "in_b": word(), "sel": rnd.getrandbits(2),
                     "in_id": rnd.getrandbits(4), "issue_vld": int(rnd.random() < 0.6),
                     "mac_sel_in": rnd.getrandbits(1)})
    return rows


@pytest.mark.skipif(not icarus.available, reason="iverilog not installed")
@pytest.mark.parametrize("stages", [4, 2])
def test_model_matches_rtl(tmp_path, stages):
    params = {"PIPELINE_STAGES": stages}
    m = Project.model(MODULE, params=params)
    rows = _stimulus(seed=10 + stages)
    rtl = icarus.run(Project.sources(MODULE), Project.tb(MODULE), m.inputs, m.outputs,
                     rows, tmp_path, params=params)
    ours = [m.step(r) for r in rows]
    assert len(rtl) == len(ours) == len(rows)
    diffs = icarus.diff(ours, rtl)
    assert not diffs, f"{len(diffs)} mismatches, first: {diffs[:5]}"
    assert sum(o["out_vld"] == 1 for o in ours) > 250
