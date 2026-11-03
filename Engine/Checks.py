"""Comparison rules for the scoreboard.

A rule is compare(expected, actual) -> [(signal, expected, actual), ...]
for one clock; an empty list means the clock matches. Modules pick one in
their Checks.py, or write their own (e.g. only compare data when valid is 1).
"""


def exact(expected, actual):
    """Every signal must match exactly, except where the model says X (None)."""
    return [(s, e, actual[s]) for s, e in expected.items()
            if e is not None and actual[s] != e]


def only(signals, rule=exact):
    """Apply `rule` to a subset of signals only."""
    signals = set(signals)
    def compare(expected, actual):
        return [m for m in rule(expected, actual) if m[0] in signals]
    return compare
