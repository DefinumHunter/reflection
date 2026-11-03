"""Functional coverage: counts what a run actually exercised.

Coverage only observes. It gets two kinds of samples:

    transactions  what the generator sent: the transaction, the gap before it,
                  the previous transaction
    tags          what the golden models reported while running, e.g.
                  "sat_pos" from the branch that saturated. Each tag comes
                  with the path of the RTL instance whose golden emitted it.

A module lists its points in Modules/<module>/Coverage.py:

    kind = Op("kind", ["MulAB", "MulSum"], of=lambda s: type(s.op).__name__)
    gap  = Op("gap", ["overlap", "none", "pause"], of=lambda s: ...)
    sat  = Tag("saturation", ["sat_none", "sat_pos", "sat_neg"])
    POINTS = [kind, gap, sat, Cross(kind, gap)]

Op    one bin per value of `of(s)`; s has .op, .gap, .prev (None for the first).
      `of` returning None means "this transaction is not about this point".
Tag   one bin per tag name; counts over all instances, and per instance too.
Cross every pair of bins of two points of the same kind, hit together: two Op
      points on the same transaction, or two Tag points from the same golden
      in the same clock.

Every point takes at_least=N: a bin counts as covered after N hits (default 1).
One lucky hit is not much evidence; use it for the bins that matter.

Nothing here fails a test: the result is counts and a report with the holes.
"""
import copy
import dataclasses
import json
from collections import Counter
from pathlib import Path


@dataclasses.dataclass
class Sample:
    op: object
    gap: int
    prev: object


class _Point:
    def __init__(self, name, bins, at_least=1):
        self.name, self.at_least = name, at_least
        self.bins = [str(b) for b in bins]
        if len(set(self.bins)) != len(self.bins):
            raise ValueError(f"coverage point '{name}' has duplicate bins")
        self.hits = Counter()
        self.other = Counter()        # values seen that are not bins

    def _count(self, value):
        key = str(value)
        (self.hits if key in self.bins else self.other)[key] += 1
        return key if key in self.bins else None


class Op(_Point):
    kind = "op"

    def __init__(self, name, bins, of, at_least=1):
        super().__init__(name, bins, at_least)
        self.of = of

    def sample(self, s):
        value = self.of(s)
        return [] if value is None else [b for b in [self._count(value)] if b]


class Tag(_Point):
    kind = "tag"

    def __init__(self, name, bins, at_least=1):
        super().__init__(name, bins, at_least)
        self.by_instance = {}         # path -> Counter(bin)

    def sample(self, path, tags):
        mine = [t for t in tags if t in self.bins]
        for t in mine:
            self.hits[t] += 1
            self.by_instance.setdefault(path, Counter())[t] += 1
        return mine


class Cross:
    def __init__(self, a, b, ignore=(), at_least=1):
        if a.kind != b.kind:
            raise ValueError(f"cannot cross {a.name} ({a.kind}) with {b.name} ({b.kind}): "
                             f"they are never sampled together")
        self.a, self.b, self.kind, self.at_least = a, b, a.kind, at_least
        self.name = f"{a.name} x {b.name}"
        skip = {f"{x} x {y}" for x, y in ignore}
        self.bins = [f"{x} x {y}" for x in a.bins for y in b.bins if f"{x} x {y}" not in skip]
        self.hits = Counter()
        self.other = Counter()

    def count(self, hits_a, hits_b):
        for x in hits_a:
            for y in hits_b:
                key = f"{x} x {y}"
                if key in self.bins:
                    self.hits[key] += 1


class Coverage:
    def __init__(self, points):
        self.points = copy.deepcopy(list(points))    # own counters: points are reusable
        names = [p.name for p in self.points]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate coverage point names: {names}")
        self.simple = [p for p in self.points if not isinstance(p, Cross)]
        self.crosses = [p for p in self.points if isinstance(p, Cross)]
        for c in self.crosses:
            for p in (c.a, c.b):
                if p not in self.simple:
                    raise ValueError(f"'{c.name}': '{p.name}' must also be in the list of points")
        self.unlisted_tags = Counter()    # tags no Tag point asks for (typo or forgotten)

    def _sample(self, kind, *args):
        hits = {id(p): p.sample(*args) for p in self.simple if p.kind == kind}
        for c in self.crosses:
            if c.kind == kind:
                c.count(hits[id(c.a)], hits[id(c.b)])

    def sample_ops(self, sent):
        """sent: [(transaction, gap before it), ...] in the order they were sent."""
        prev = None
        for op, gap in sent:
            self._sample("op", Sample(op, gap, prev))
            prev = op

    def sample_tags(self, tags):
        """tags: [(instance path, [tag, ...]), ...] for one clock (Model.tags)."""
        listed = {b for p in self.simple if p.kind == "tag" for b in p.bins}
        for path, names in tags:
            self._sample("tag", path, names)
            for t in names:
                if t not in listed:
                    self.unlisted_tags[t] += 1

    def data(self) -> dict:
        """Plain dict: can be saved as JSON, merged with other runs, reported."""
        points = {}
        for p in self.points:
            d = {"bins": p.bins, "at_least": p.at_least,
                 "hits": dict(p.hits), "other": dict(p.other)}
            if isinstance(p, Tag):
                d["by_instance"] = {k: dict(v) for k, v in sorted(p.by_instance.items())}
            points[p.name] = d
        return {"points": points, "unlisted_tags": dict(self.unlisted_tags)}


# --- working with the plain data ---------------------------------------------

def merge(a: dict, b: dict) -> dict:
    """Sum of two runs of the same coverage points."""
    def add(x, y):
        return dict(Counter(x) + Counter(y))

    if list(a["points"]) != list(b["points"]):
        raise ValueError("cannot merge coverage of different points")
    points = {}
    for name, pa in a["points"].items():
        pb = b["points"][name]
        if pa["bins"] != pb["bins"] or pa["at_least"] != pb["at_least"]:
            raise ValueError(f"cannot merge '{name}': bins differ")
        d = {"bins": pa["bins"], "at_least": pa["at_least"],
             "hits": add(pa["hits"], pb["hits"]),
             "other": add(pa["other"], pb["other"])}
        if "by_instance" in pa:
            paths = sorted(set(pa["by_instance"]) | set(pb["by_instance"]))
            d["by_instance"] = {k: add(pa["by_instance"].get(k, {}), pb["by_instance"].get(k, {}))
                                for k in paths}
        points[name] = d
    return {"points": points, "unlisted_tags": add(a["unlisted_tags"], b["unlisted_tags"])}


def _missing(p, hits=None):
    hits = p["hits"] if hits is None else hits
    return [b for b in p["bins"] if hits.get(b, 0) < p["at_least"]]


def totals(data: dict):
    """(bins covered, bins in total)."""
    total = sum(len(p["bins"]) for p in data["points"].values())
    return total - sum(len(_missing(p)) for p in data["points"].values()), total


def holes(data: dict) -> dict:
    """{point: [bins never hit]} for points that have any."""
    return {name: _missing(p) for name, p in data["points"].items() if _missing(p)}


def report(data: dict, counts=True) -> str:
    covered, total = totals(data)
    pct = 100.0 * covered / total if total else 100.0
    lines = [f"coverage: {pct:.1f}% ({covered}/{total} bins)"]
    width = max((len(n) for n in data["points"]), default=0)
    for name, p in data["points"].items():
        missing = _missing(p)
        line = f"  {name:<{width}}  {len(p['bins']) - len(missing):>3}/{len(p['bins']):<3}"
        if counts:
            line += "  " + " ".join(f"{b}={p['hits'].get(b, 0)}" for b in p["bins"])
        lines.append(line)
        if missing:
            need = f" (need {p['at_least']} each)" if p["at_least"] > 1 else ""
            lines.append(f"  {'':<{width}}  MISSING{need}: {', '.join(missing)}")
        if p["other"]:
            seen = ", ".join(f"{k} ({v})" for k, v in sorted(p["other"].items())[:8])
            lines.append(f"  {'':<{width}}  values outside the bins: {seen}")
        inst = p.get("by_instance", {})
        if len(inst) > 1:
            for path, h in inst.items():
                gone = _missing(p, h)
                if gone:
                    lines.append(f"  {'':<{width}}  {path}: missing {', '.join(gone)}")
    if data["unlisted_tags"]:
        tags = ", ".join(f"{k} ({v})" for k, v in sorted(data["unlisted_tags"].items()))
        lines.append(f"  tags no point asks for: {tags}")
    return "\n".join(lines)


def save(data: dict, path):
    Path(path).write_text(json.dumps(data, indent=1), encoding="utf-8")


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
