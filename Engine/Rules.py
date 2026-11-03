"""Value rules: where a transaction field gets its value when a test does not
set it.

A rule is any callable rule(ctx) -> int. ctx gives:
    ctx.rng      random.Random seeded for this run (use it, never `random`)
    ctx.history  transactions generated so far, oldest first
    ctx.field    name of the field being filled
Values are raw bits (unsigned). Signed meaning is the golden's business.

    RULES = {
        "a":  corners(CORNERS, p=0.15, otherwise=bits(32)),
        "id": sequential(1, 15),
        "sub": bit(0.5),
    }
"""


def bits(n):
    """Any n-bit value."""
    return lambda ctx: ctx.rng.getrandbits(n)


def const(value):
    return lambda ctx: value


def bit(p_one=0.5):
    """1 with probability p_one."""
    return lambda ctx: int(ctx.rng.random() < p_one)


def between(lo, hi):
    """Integer in [lo, hi], both included."""
    return lambda ctx: ctx.rng.randint(lo, hi)


def one_of(values, weights=None):
    """One of the values, optionally weighted."""
    values = list(values)
    return lambda ctx: ctx.rng.choices(values, weights=weights)[0]


def corners(pool, p, otherwise):
    """A value from the corner pool with probability p, else from `otherwise`."""
    pool = list(pool)
    return lambda ctx: ctx.rng.choice(pool) if ctx.rng.random() < p else otherwise(ctx)


def sequential(lo, hi):
    """lo, lo+1, ..., hi, lo, ... for the field this rule is attached to.
    Uses the history: continues after the last value that field got."""
    def rule(ctx):
        for op in reversed(ctx.history):
            last = getattr(op, ctx.field, None)
            if last is not None:
                return lo if last >= hi else last + 1
        return lo
    return rule
