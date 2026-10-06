"""Stimulus generator: transactions in, one row per clock out.

Three things meet here, each written somewhere else:
    Protocol   (per module)  transactions and how each one looks in cycles
    Scenario   (per module)  value rules, weights, directed cases
    Test       (per module)  the plan: which segments, how many, seed

A transaction is a dataclass whose fields are the values it carries, plus
    cycles() -> [ {TB input: value}, ... ]     one dict per clock, only the
                                               inputs this transaction drives
Fields left as None are filled from the rules, so a directed case can pin
some fields and leave the rest random: MulSum(a=0x7FFFFFFF, b=0x7FFFFFFF).

The plan is a list of segments:
    Directed([op, op, ...], gap=0)         these transactions, in this order
    Random({OpA: 50, OpB: 30}, count, gap) `count` transactions, kind by weight

A key in the Random weights is a transaction class, or a function f(ctx) that
returns a transaction with some fields already set -- a "class" of stimulus,
e.g. a pair of operands built to saturate. The rules fill what it leaves None.

gap = clocks between the end of one transaction and the start of the next;
an int or a rule. gap = -1 starts the next transaction in the last clock of
the previous one (they overlap), -2 in the one before, and so on. Overlapping
clocks are merged; if two transactions drive the same input in the same clock
with different values, that is an error, not a silent override.

A transaction with `no_overlap = True` (e.g. a reset) never overlaps its
neighbours: negative gaps next to it count as 0.

Every clock not driven by any transaction gets the module's IDLE row. Every
emitted row is checked against the TB: all inputs present, no unknown names,
values are raw bits that fit the port width.
"""
import dataclasses
import random


class GeneratorError(Exception):
    pass


@dataclasses.dataclass
class Directed:
    ops: list
    gap: object = 0


@dataclasses.dataclass
class Random:
    weights: dict
    count: int
    gap: object = 0


class Ctx:
    """What a rule can see."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.history = []
        self.field = None     # name of the field being filled right now


def _value(rule_or_int, ctx):
    return rule_or_int(ctx) if callable(rule_or_int) else rule_or_int


class Generator:
    def __init__(self, plan, rules, idle, inputs, widths, seed):
        self.plan, self.rules, self.idle = plan, rules, dict(idle)
        self.inputs, self.widths, self.seed = list(inputs), widths, seed
        self.ctx = Ctx(seed)
        self.trace = []   # per emitted row: ["#12 MulSum[1]", ...]
        self.sent = []    # per transaction: (transaction, gap before it), for coverage

    # --- transactions ------------------------------------------------------

    def fill(self, op):
        """Copy of op with every None field taken from the rules."""
        if not dataclasses.is_dataclass(op):
            raise GeneratorError(f"{op!r} is not a dataclass transaction")
        values = {}
        for f in dataclasses.fields(op):
            if getattr(op, f.name) is None:
                if f.name not in self.rules:
                    raise GeneratorError(f"{type(op).__name__}.{f.name} is not set and "
                                         f"the scenario has no rule for '{f.name}'")
                self.ctx.field = f.name
                values[f.name] = self.rules[f.name](self.ctx)
        return dataclasses.replace(op, **values)

    def _ops(self):
        """(filled transaction, gap before it), in plan order."""
        for seg in self.plan:
            if isinstance(seg, Directed):
                for op in seg.ops:
                    yield self.fill(op), _value(seg.gap, self.ctx)
            elif isinstance(seg, Random):
                kinds, weights = list(seg.weights), list(seg.weights.values())
                for _ in range(seg.count):
                    kind = self.ctx.rng.choices(kinds, weights=weights)[0]
                    op = kind() if isinstance(kind, type) else kind(self.ctx)
                    yield self.fill(op), _value(seg.gap, self.ctx)
            else:
                raise GeneratorError(f"unknown plan segment {seg!r}")

    # --- clocks ------------------------------------------------------------

    def _row(self, slot):
        row = {**self.idle, **slot}
        extra = set(row) - set(self.inputs)
        missing = set(self.inputs) - set(row)
        if extra:
            raise GeneratorError(f"drives {sorted(extra)}, which are not TB inputs; "
                                 f"inputs: {self.inputs}")
        if missing:
            raise GeneratorError(f"nothing drives {sorted(missing)}: add them to IDLE")
        for name, v in row.items():
            w = self.widths[name]
            if not isinstance(v, int) or isinstance(v, bool):
                raise GeneratorError(f"{name} = {v!r} is not an int")
            if v < 0:
                raise GeneratorError(f"{name} = {v} is negative: use raw bits, "
                                     f"e.g. {v & ((1 << w) - 1):#x} for {w} bits")
            if v >> w:
                raise GeneratorError(f"{name} = {v:#x} does not fit in {w} bits")
        return row

    def __iter__(self):
        slots, owners = {}, {}          # clock -> {input: value}, clock -> [labels]
        emitted = 0                     # clocks below this are already out
        end = 0                         # clock after the last placed transaction
        prev = None

        def flush(upto):
            nonlocal emitted
            while emitted < upto:
                try:
                    row = self._row(slots.pop(emitted, {}))
                except GeneratorError as e:
                    where = ", ".join(owners.get(emitted, [])) or "idle"
                    raise GeneratorError(f"clock {emitted} ({where}): {e}") from None
                self.trace.append(owners.pop(emitted, []))
                emitted += 1
                yield row

        for n, (op, gap) in enumerate(self._ops()):
            name = type(op).__name__
            if prev is None or getattr(op, "no_overlap", False) \
                    or getattr(prev, "no_overlap", False):
                gap = max(0, gap)                     # nothing / not allowed to overlap
            start = end + gap
            if start < emitted:
                raise GeneratorError(f"#{n} {name}: gap {gap} starts it at clock {start}, "
                                     f"before clocks already sent (up to {emitted - 1})")
            yield from flush(start)
            cycles = op.cycles()
            for k, drive in enumerate(cycles):
                clock = start + k
                slot = slots.setdefault(clock, {})
                label = f"#{n} {name}[{k}]"
                for sig, v in drive.items():
                    if sig in slot and slot[sig] != v:
                        raise GeneratorError(
                            f"clock {clock}: {label} drives {sig}={v}, but "
                            f"{', '.join(owners[clock])} already drives {sig}={slot[sig]}")
                    slot[sig] = v
                owners.setdefault(clock, []).append(label)
            self.ctx.history.append(op)
            self.sent.append((op, gap))
            end = max(end, start + len(cycles))
            prev = op
        yield from flush(end)
