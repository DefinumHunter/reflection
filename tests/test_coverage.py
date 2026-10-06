"""The coverage engine on toy data, tags through the model, class functions in
the generator, and the two project modules' coverage on the model."""
from dataclasses import dataclass
from pathlib import Path

import pytest

import Project
from Components.MacNode import mac_q16_golden
from Components.MuxNode import sum_sat
from Engine import Coverage as C
from Engine.Core import LeafSpec
from Engine.Coverage import Coverage, Cross, Op, Tag
from Engine.Generator import Directed, Generator, Random
from Engine.Model import Model
from Engine.Rules import bits
from Modules.mac_q16.Scenario import corner_pair, sat_pair, small_pair, tie_pair
from Modules.pe_mac_wrapper.Scenario import sum_pair

FIX = Path(__file__).resolve().parent / "rtl" / "fixtures.sv"


@dataclass
class A:
    x: int = None

    def cycles(self):
        return [dict(x=self.x)]


@dataclass
class B:
    x: int = None

    def cycles(self):
        return [dict(x=self.x)]


def points():
    kind = Op("kind", ["A", "B"], of=lambda s: type(s.op).__name__)
    gap = Op("gap", ["none", "pause"], of=lambda s: None if s.prev is None
             else "none" if s.gap == 0 else "pause")
    size = Tag("size", ["small", "big"])
    sign = Tag("sign", ["pos", "neg"])
    return kind, gap, size, sign


# --- counting ----------------------------------------------------------------

def test_op_points_count_transactions_and_report_holes():
    kind, gap, _, _ = points()
    cov = Coverage([kind, gap, Cross(kind, gap)])
    cov.sample_ops([(A(1), 0), (A(2), 0), (A(3), 3)])
    d = cov.data()
    assert d["points"]["kind"]["hits"] == {"A": 3}
    assert d["points"]["gap"]["hits"] == {"none": 1, "pause": 1}      # the first has no prev
    assert d["points"]["kind x gap"]["hits"] == {"A x none": 1, "A x pause": 1}
    assert C.totals(d) == (5, 8)
    assert C.holes(d) == {"kind": ["B"], "kind x gap": ["B x none", "B x pause"]}


def test_tag_points_count_per_instance_and_cross_within_one_golden():
    _, _, size, sign = points()
    cov = Coverage([size, sign, Cross(size, sign)])
    cov.sample_tags([("u1", ["small", "pos"]), ("u2", ["big"])])
    cov.sample_tags([("u1", ["small", "neg"])])
    d = cov.data()
    assert d["points"]["size"]["hits"] == {"small": 2, "big": 1}
    assert d["points"]["size"]["by_instance"] == {"u1": {"small": 2}, "u2": {"big": 1}}
    # u2's "big" came without a sign, and never together with u1's tags
    assert d["points"]["size x sign"]["hits"] == {"small x pos": 1, "small x neg": 1}
    assert "u2: missing small" in C.report(d)


def test_at_least_needs_more_than_one_hit():
    cov = Coverage([Tag("size", ["small", "big"], at_least=3)])
    for _ in range(3):
        cov.sample_tags([("u", ["small"])])
    cov.sample_tags([("u", ["big"])])
    d = cov.data()
    assert C.holes(d) == {"size": ["big"]}
    assert "MISSING (need 3 each): big" in C.report(d)


def test_values_outside_bins_and_unknown_tags_are_reported_not_lost():
    kind, _, size, _ = points()
    only_a = Op("kind", ["A"], of=kind.of)
    cov = Coverage([only_a, size])
    cov.sample_ops([(A(1), 0), (B(1), 0)])
    cov.sample_tags([("u", ["small", "smal"])])           # typo in a golden
    text = C.report(cov.data())
    assert "values outside the bins: B (1)" in text
    assert "tags no point asks for: smal (1)" in text


def test_points_are_reusable_each_coverage_has_its_own_counters():
    kind, *_ = points()
    c1, c2 = Coverage([kind]), Coverage([kind])
    c1.sample_ops([(A(1), 0)])
    assert c1.data()["points"]["kind"]["hits"] == {"A": 1}
    assert c2.data()["points"]["kind"]["hits"] == {}
    assert kind.hits == {}


def test_merge_adds_runs_and_closes_holes(tmp_path):
    kind, gap, size, _ = points()
    runs = []
    for ops, tags in ([(A(1), 0)], [("u1", ["small"])]), ([(B(1), 0)], [("u2", ["big"])]):
        cov = Coverage([kind, size])
        cov.sample_ops(ops)
        cov.sample_tags(tags)
        runs.append(cov.data())
    assert C.holes(runs[0]) and C.holes(runs[1])
    merged = C.merge(*runs)
    assert C.holes(merged) == {}
    assert merged["points"]["size"]["by_instance"] == {"u1": {"small": 1}, "u2": {"big": 1}}
    C.save(merged, tmp_path / "c.json")
    assert C.load(tmp_path / "c.json") == merged
    with pytest.raises(ValueError):
        C.merge(runs[0], Coverage([kind]).data())


def test_mistakes_in_the_point_list_are_errors():
    kind, gap, size, _ = points()
    with pytest.raises(ValueError, match="never sampled together"):
        Cross(kind, size)
    with pytest.raises(ValueError, match="must also be in the list"):
        Coverage([kind, Cross(kind, gap)])
    with pytest.raises(ValueError, match="duplicate"):
        Coverage([kind, kind])


# --- tags through the model ----------------------------------------------------

class Inc8Tagged:
    def __init__(self):
        self.tags = []

    def tick(self, i):
        if i["a"] is None:
            return {"y": None}
        self.tags.append("odd" if i["a"] & 1 else "even")
        return {"y": (i["a"] + 1) & 0xFF}


def test_model_collects_tags_with_the_instance_path_every_cycle():
    spec = LeafSpec(module="inc8", input_specs={}, output_specs={}, golden=Inc8Tagged, comb={"y"})
    m = Model.from_rtl([FIX], "tb_chain", {"inc8": spec})
    m.step({"x": 4})                                   # u1 sees 4, u2 sees 5, u3 sees 6
    assert sorted(m.tags) == [("u1", ["even"]), ("u2", ["odd"]), ("u3", ["even"])]
    m.step({"x": 5})
    assert sorted(m.tags) == [("u1", ["odd"]), ("u2", ["even"]), ("u3", ["odd"])]   # not accumulated


# --- class functions in the generator -------------------------------------------

def test_weights_accept_class_functions_and_gaps_are_recorded():
    def big(ctx):
        return A(x=200 + ctx.rng.randrange(50))
    g = Generator([Directed([A(1)]), Random({big: 1, B: 1}, count=40, gap=2)],
                  {"x": bits(4)}, {"x": 0}, ["x"], {"x": 8}, seed=3)
    rows = list(g)
    assert len(g.sent) == 41 and g.sent[0] == (A(1), 0)
    assert all(gap == 2 for _, gap in g.sent[1:])
    kinds = {type(op).__name__ for op, _ in g.sent[1:]}
    assert kinds == {"A", "B"}
    assert all(op.x >= 200 for op, _ in g.sent[1:] if isinstance(op, A))    # from the class
    assert all(op.x < 16 for op, _ in g.sent[1:] if isinstance(op, B))      # from the rule
    assert len(rows) == 1 + 40 * 3


# --- recipes really produce their class (checked with the goldens' own tags) -----

def mac_tags(a, b):
    tags = []
    mac_q16_golden({"in_a": a, "in_b": b}, tags)
    return tags


@pytest.mark.parametrize("seed", range(5))
def test_mac_recipes(seed):
    import random
    rng = random.Random(seed)
    for _ in range(200):
        assert mac_tags(*small_pair(rng))[1] == "sat_none"
        assert mac_tags(*tie_pair(rng, up=True)) == ["round_tie_up", "sat_none"]
        assert mac_tags(*tie_pair(rng, up=False)) == ["round_tie_stay", "sat_none"]
        assert mac_tags(*sat_pair(rng, positive=True))[1] == "sat_pos"
        assert mac_tags(*sat_pair(rng, positive=False))[1] == "sat_neg"
        assert all(0 <= v <= 0xFFFFFFFF for v in corner_pair(rng))


@pytest.mark.parametrize("sub", [0, 1])
@pytest.mark.parametrize("sat", ["none", "pos", "neg"])
def test_sum_recipes(sat, sub):
    import random
    rng = random.Random(sat + str(sub))
    for _ in range(200):
        a, b = sum_pair(rng, sat, sub)
        tags = []
        sum_sat(a, b, sub, tags)
        assert tags == ["sum_sub" if sub else "sum_add", f"sum_sat_{sat}"]


def test_tags_do_not_change_results():
    import random
    rng = random.Random(0)
    for _ in range(500):
        i = {"in_a": rng.getrandbits(32), "in_b": rng.getrandbits(32)}
        assert mac_q16_golden(i, []) == mac_q16_golden(i)


# --- the project modules ----------------------------------------------------------

@pytest.mark.parametrize("module", sorted(Project.MODULES))
@pytest.mark.parametrize("seed", [None, 2, 3])
def test_module_tests_close_their_coverage(module, seed):
    data = Project.dry_run(module, seed)
    assert C.holes(data) == {}, "\n" + C.report(data)
    assert data["unlisted_tags"] == {}


def test_coverage_shows_what_the_old_random_stimulus_was_missing():
    """Fully random 32-bit operands: nearly every multiply saturates and exact
    ties never happen by chance. This is why Scenario.py has classes."""
    from Modules.mac_q16 import Coverage as MC, Test as T
    from Modules.mac_q16.Protocol import Mac, Reset
    m = Project.model("mac_q16")
    g = Generator([Directed([Reset(5)]), Random({Mac: 1}, count=500)],
                  {**T.RULES, "a": bits(32), "b": bits(32)}, T.IDLE,
                  list(m.netlist.inputs), m.netlist.widths, seed=1)
    cov = Coverage(MC.POINTS)
    for row in g:
        m.step(row)
        cov.sample_tags(m.tags)
    sat = cov.data()["points"]["saturation"]["hits"]
    rnd = cov.data()["points"]["rounding"]["hits"]
    assert sat.get("sat_none", 0) < 0.05 * sum(sat.values())
    assert rnd.get("round_tie_up", 0) == 0 and rnd.get("round_tie_stay", 0) == 0
    assert "rounding" in C.holes(cov.data())
