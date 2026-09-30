"""The generator engine on a toy protocol (no RTL involved)."""
from dataclasses import dataclass
from collections import Counter

import pytest

from Engine.Generator import Directed, Generator, GeneratorError, Random
from Engine.Rules import between, bit, bits, const, corners, one_of, sequential

INPUTS = ["go", "x", "y", "tag"]
WIDTHS = {"go": 1, "x": 8, "y": 8, "tag": 4}
IDLE = dict(go=0, x=0, y=0, tag=0)


@dataclass
class Load:          # x in clock 0, go in clock 1
    x: int = None
    tag: int = None

    def cycles(self):
        return [dict(x=self.x, tag=self.tag), dict(go=1)]


@dataclass
class Both:          # x and y together, one clock
    x: int = None
    y: int = None

    def cycles(self):
        return [dict(x=self.x, y=self.y)]


@dataclass
class Hold:
    no_overlap = True

    def cycles(self):
        return [dict(go=0)] * 2


RULES = {"x": bits(8), "y": bits(8), "tag": sequential(1, 3)}


def gen(plan, rules=RULES, idle=IDLE, seed=1, widths=WIDTHS):
    return Generator(plan, rules, idle, INPUTS, widths, seed)


def test_same_seed_same_rows_different_seed_different_rows():
    plan = [Random({Load: 1, Both: 1}, count=50, gap=one_of([0, 1, 2]))]
    assert list(gen(plan, seed=7)) == list(gen(plan, seed=7))
    assert list(gen(plan, seed=7)) != list(gen(plan, seed=8))


def test_directed_keeps_pinned_fields_and_fills_the_rest():
    g = gen([Directed([Load(x=0x42)])])
    rows = list(g)
    assert rows == [dict(go=0, x=0x42, y=0, tag=1), dict(go=1, x=0, y=0, tag=0)]
    assert g.ctx.history == [Load(x=0x42, tag=1)]


def test_idle_fills_untouched_clocks_and_gaps():
    # the gap comes before every transaction, the first one included
    rows = list(gen([Directed([Load(x=1, tag=1), Load(x=2, tag=2)], gap=2)]))
    assert [r["go"] for r in rows] == [0, 0, 0, 1, 0, 0, 0, 1]
    assert [r["x"] for r in rows] == [0, 0, 1, 0, 0, 0, 2, 0]


def test_overlap_merges_clocks():
    g = gen([Directed([Load(x=1, tag=1), Load(x=2, tag=2)], gap=-1)])
    rows = list(g)
    assert rows == [dict(go=0, x=1, y=0, tag=1),
                    dict(go=1, x=2, y=0, tag=2),     # issue of #0 + load of #1
                    dict(go=1, x=0, y=0, tag=0)]
    assert g.trace[1] == ["#0 Load[1]", "#1 Load[0]"]


def test_overlap_conflict_is_an_error():
    with pytest.raises(GeneratorError, match=r"clock 0: #1 Both\[0\] drives x=2, but #0 Load\[0\]"):
        list(gen([Directed([Load(x=1, tag=1), Both(x=2, y=0)], gap=-2)]))


def test_same_value_in_overlap_is_fine():
    rows = list(gen([Directed([Both(x=5, y=1), Both(x=5, y=1)], gap=-1)]))
    assert rows == [dict(go=0, x=5, y=1, tag=0)]


def test_gap_before_already_sent_clocks_is_an_error():
    with pytest.raises(GeneratorError, match="before clocks already sent"):
        list(gen([Directed([Both(x=1, y=1), Load(x=1, tag=1), Both(x=1, y=1)], gap=-3)]))


def test_no_overlap_transactions_ignore_negative_gaps():
    rows = list(gen([Directed([Load(x=1, tag=1), Hold(), Load(x=2, tag=2)], gap=-1)]))
    assert len(rows) == 2 + 2 + 2


def test_missing_rule_is_reported():
    with pytest.raises(GeneratorError, match=r"Both.y is not set.*no rule for 'y'"):
        list(gen([Directed([Both(x=1)])], rules={"x": bits(8)}))


def test_rows_are_checked_against_the_tb():
    with pytest.raises(GeneratorError, match="does not fit in 8 bits"):
        list(gen([Directed([Both(x=0x100, y=0)])]))
    with pytest.raises(GeneratorError, match="negative: use raw bits, e.g. 0xff"):
        list(gen([Directed([Both(x=-1, y=0)])]))
    with pytest.raises(GeneratorError, match=r"nothing drives \['tag'\]: add them to IDLE"):
        list(gen([Directed([Both(x=1, y=1)])], idle=dict(go=0, x=0, y=0)))

    @dataclass
    class Stray:
        def cycles(self):
            return [dict(z=1)]
    with pytest.raises(GeneratorError, match=r"clock 0 \(#0 Stray\[0\]\).*\['z'\].*not TB inputs"):
        list(gen([Directed([Stray()])]))


def test_weights_are_respected():
    g = gen([Random({Load: 3, Both: 1}, count=2000, gap=5)])
    list(g)
    kinds = Counter(type(op).__name__ for op in g.ctx.history)
    assert 0.70 < kinds["Load"] / 2000 < 0.80


def test_rules():
    from Engine.Generator import Ctx
    ctx = Ctx(3)
    assert {between(2, 4)(ctx) for _ in range(200)} == {2, 3, 4}
    assert const(9)(ctx) == 9
    assert 0.25 < sum(bit(0.3)(ctx) for _ in range(2000)) / 2000 < 0.35
    hits = sum(corners([0xAA], p=0.2, otherwise=const(0))(ctx) == 0xAA for _ in range(2000))
    assert 0.15 < hits / 2000 < 0.25
    seq = sequential(1, 3)
    ctx.history, ctx.field = [], "tag"
    got = []
    for _ in range(5):
        v = seq(ctx)
        got.append(v)
        ctx.history.append(Load(x=0, tag=v))
    assert got == [1, 2, 3, 1, 2]


def test_generator_is_pull_based():
    g = iter(gen([Random({Load: 1}, count=10**9)]))
    first = [next(g) for _ in range(5)]          # would hang if it built everything
    assert len(first) == 5
