"""Coverage of a module's test on the model only: no simulator, no RTL check.

    python -m Engine.Cover pe_mac_wrapper             (the test's own seed)
    python -m Engine.Cover pe_mac_wrapper seed=7
    python -m Engine.Cover pe_mac_wrapper seeds=50    (seeds 1..50 merged)

Use it while tuning Scenario.py and Coverage.py: it answers "what would this
test exercise" in a fraction of a second. The real run is Engine.Run.
Exits with the number of points that still have holes.
"""
import sys

import Project
from Engine import Coverage


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    module, seed, seeds = argv[0], None, None
    for arg in argv[1:]:
        k, v = arg.split("=", 1)
        if k == "seed":
            seed = int(v)
        elif k == "seeds":
            seeds = int(v)
        else:
            print(f"unknown argument '{arg}'")
            return 2
    if seeds is None:
        data = Project.dry_run(module, seed)
    else:
        data = None
        for s in range(1, seeds + 1):
            one = Project.dry_run(module, s)
            data = one if data is None else Coverage.merge(data, one)
    print(Coverage.report(data))
    return len(Coverage.holes(data))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
