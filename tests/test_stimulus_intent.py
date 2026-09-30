"""Protocols against intent: do the transactions really do what they claim?

Expected values here come from hand-worked numbers and from the operation's
meaning (c * (a + b), ...), not from the RTL. The model is used as the device
because it is already checked cycle-for-cycle against the RTL.
"""
import pytest

import Project
from Components.Fixed import q16, saturate, to_signed
from Components.MacNode import mac_q16_golden
from Engine.Generator import Directed, Generator, Random
from Modules.mac_q16 import Scenario as MacScenario
from Modules.mac_q16.Protocol import Mac, Reset as MacReset
from Modules.pe_mac_wrapper import Protocol as WP, Scenario as WS


def run(module, plan, seed=1, tail=12):
    m = Project.model(module)
    t = Project.test(module)
    g = Generator(plan, t.RULES, t.IDLE, list(m.netlist.inputs), m.netlist.widths, seed)
    outs = [m.step(r) for r in g]
    outs += [m.step(t.IDLE) for _ in range(tail)]
    return g, outs


def valid(outs, *sigs):
    return [tuple(o[s] for s in sigs) for o in outs if o["out_vld"] == 1]


# --- mac_q16 ----------------------------------------------------------------

def test_mac_directed_cases_give_hand_worked_results():
    _, outs = run("mac_q16", [Directed([MacReset(4)]), Directed(MacScenario.DIRECTED)])
    assert [r for (r,) in valid(outs, "out_res")] == [
        0,              # 0.5 ulp, lsb 0: stays
        2,              # 1.5 ulp, lsb 1: rounds up
        2,              # 2.5 ulp, lsb 0: stays
        0x7FFFFFFF,     # max * max
        0x7FFFFFFF,     # min * min
        0x80000000,     # min * max
        q16(7.5),
        q16(-6),
    ]


# --- pe_mac_wrapper -----------------------------------------------------------

def mul(a, b):
    return mac_q16_golden({"in_a": a, "in_b": b})["out_res"]


def meaning(op):
    """What the operation should produce, from its definition."""
    if isinstance(op, WP.MulAB):
        return mul(op.a, op.b)
    if isinstance(op, WP.MulSum):
        a, b = to_signed(op.a), to_signed(op.b)
        return mul(op.c, saturate(a - b if op.sub else a + b))
    if isinstance(op, WP.MulLocal):
        return mul(op.a, op.local)
    raise TypeError(op)


def check_in_order(g, outs):
    ops = [op for op in g.ctx.history if not isinstance(op, WP.Reset)]
    want = [(meaning(op), op.mac_sel, op.id) for op in ops]
    assert valid(outs, "out_res", "out_sel", "out_id") == want


def test_wrapper_directed_cases():
    g, outs = run("pe_mac_wrapper", [Directed([WP.Reset(4)]), Directed(WS.DIRECTED)])
    check_in_order(g, outs)
    got = [r for (r,) in valid(outs, "out_res")]
    assert got[:4] == [q16(7.5), q16(8.5), q16(3.5), q16(5)]


@pytest.mark.parametrize("gap", [-1, 0, 2])
def test_wrapper_back_to_back(gap):
    g, outs = run("pe_mac_wrapper", [Directed([WP.Reset(4)]), Directed(WS.BACK_TO_BACK, gap=gap)])
    check_in_order(g, outs)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_wrapper_random_stream_with_overlaps(seed):
    g, outs = run("pe_mac_wrapper",
                  [Directed([WP.Reset(4)]), Random(WS.WEIGHTS, count=300, gap=WS.GAP)], seed)
    check_in_order(g, outs)
    overlapped = sum(len(t) > 1 for t in g.trace)
    assert overlapped > 30             # the stream really ran at full rate in places


def test_full_rate_is_one_result_per_clock_for_two_clock_ops():
    ops = [WP.MulAB() for _ in range(10)]
    g, outs = run("pe_mac_wrapper", [Directed([WP.Reset(4)]), Directed(ops, gap=-1)])
    check_in_order(g, outs)
    hits = [c for c, o in enumerate(outs) if o["out_vld"] == 1]
    assert hits == list(range(hits[0], hits[0] + 10))   # ten results on ten consecutive clocks
