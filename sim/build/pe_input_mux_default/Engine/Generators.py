"""
Components/Generators.py
Generic stimulus engine. No cocotb, no RTL, no module-specific knowledge.

SignalSpec  — describes one signal: width, signed, random rules.
VectorConfig — per-test knobs: counts, seed, gap behavior.
Placement   — a block of hand-written cycles to splice into the stream.

generate_stream() is the single function that produces the complete
cycle-by-cycle stimulus list. Both Precompute and CocotbEntry call it
with the same arguments to get the identical stream.
"""

import random
from dataclasses import dataclass, field


# ── Per-signal spec ───────────────────────────────────────────────

@dataclass
class SignalSpec:
    """
    Describes one signal's width, signedness, and random generation rules.

    kind="data" : random integer within [0, width_mask], optionally
                  drawn from corner_pool with corner_probability chance.
    kind="bit"  : random 0/1 with prob_one chance of being 1.

    width       : bit width of the signal (default 32)
    signed      : whether the driver should sign-extend (default True)
    """
    kind:               str   = "data"
    width:              int   = 32
    signed:             bool  = True
    corner_pool:        list  = field(default_factory=list)
    corner_probability: float = 0.15
    prob_one:           float = 1.0   # only used when kind="bit"

    @property
    def width_mask(self) -> int:
        return (1 << self.width) - 1

    @property
    def sign_threshold(self) -> int:
        return 1 << (self.width - 1)


# ── Common signal specs ───────────────────────────────────────────
# Reusable constants — import these in NodeDef files instead of
# repeating the same SignalSpec everywhere.

DATA32 = SignalSpec(kind="data", width=32, signed=True)
BIT    = SignalSpec(kind="bit",  width=1,  signed=False)
VLD    = SignalSpec(kind="bit",  width=1,  signed=False, prob_one=0.80)


# ── Vector / stream config ────────────────────────────────────────

@dataclass
class VectorConfig:
    """Per-test knobs. Lives in Spec.py, not in module data."""
    random_count:      int   = 200
    seed:              int   = 42
    first_idle_cycles: int   = 0
    drain_cycles:      int   = 6


# ── Placement ─────────────────────────────────────────────────────

@dataclass
class Placement:
    """
    A block of hand-written cycles to splice into the stream.
    cycle=None  → random non-overlapping position (reproducible via seed).
    cycle=N     → pinned at position N.
    sequence    → list of cycle dicts; signals not mentioned are filled
                  randomly per signal_spec.
    """
    sequence: list
    cycle:    int = None


# ── Single-cycle fill ─────────────────────────────────────────────

def _fill_cycle(signal_spec: dict, rng: random.Random,
                explicit: dict = None) -> dict:
    explicit = explicit or {}
    cycle = {}

    for name, spec in signal_spec.items():
        if name in explicit:
            cycle[name] = explicit[name]
            continue

        if spec.kind == "bit":
            cycle[name] = 1 if rng.random() < spec.prob_one else 0
        else:
            if spec.corner_pool and rng.random() < spec.corner_probability:
                cycle[name] = rng.choice(spec.corner_pool)
            else:
                cycle[name] = rng.randint(0, spec.width_mask)

    return cycle


# ── Stream assembly ───────────────────────────────────────────────

def generate_stream(
    signal_spec: dict,
    cfg:         VectorConfig,
    placements:  list = None,
) -> list:
    """
    Builds the complete cycle-by-cycle stimulus stream.

    1. Random baseline of cfg.random_count cycles.
    2. Splice in placements — pinned at fixed positions or randomly placed.
    3. Prepend cfg.first_idle_cycles all-zero cycles.
    4. Append cfg.drain_cycles all-zero cycles.

    Returns a list of dicts — one per cycle, signal name → value.
    Length is derived, never hardcoded elsewhere.
    """
    rng = random.Random(cfg.seed)
    placements = placements or []

    # 1. Random baseline
    baseline = [_fill_cycle(signal_spec, rng) for _ in range(cfg.random_count)]

    # 2. Resolve placements
    reserved = []

    def _overlaps(pos, length):
        for r_start, r_len in reserved:
            if pos < r_start + r_len and r_start < pos + length:
                return True
        return False

    resolved = []
    pinned     = [p for p in placements if p.cycle is not None]
    random_ones = [p for p in placements if p.cycle is None]

    for p in pinned:
        reserved.append((p.cycle, len(p.sequence)))
        resolved.append((p.cycle, p.sequence))

    for p in random_ones:
        length = len(p.sequence)
        for _ in range(1000):
            pos = rng.randint(0, len(baseline))
            if not _overlaps(pos, length):
                reserved.append((pos, length))
                resolved.append((pos, p.sequence))
                break
        else:
            raise RuntimeError(
                f"Could not place corner sequence of length {length} "
                f"without overlap after 1000 attempts."
            )

    # 3. Splice
    resolved.sort(key=lambda item: item[0])
    stream = []
    cursor = 0
    for pos, sequence in resolved:
        stream.extend(baseline[cursor:pos])
        for explicit_cycle in sequence:
            stream.append(_fill_cycle(signal_spec, rng, explicit_cycle))
        cursor = pos
    stream.extend(baseline[cursor:])

    # 4. Leading idles + trailing drain
    def _idle():
        return {name: 0 for name in signal_spec}

    return (
        [_idle() for _ in range(cfg.first_idle_cycles)]
        + stream
        + [_idle() for _ in range(cfg.drain_cycles)]
    )
