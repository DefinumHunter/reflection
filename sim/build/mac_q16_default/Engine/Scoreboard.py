"""
Engine/Scoreboard.py
Pure Python. No cocotb. No RTL.
"""

import csv
from pathlib import Path


def load(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [{k: int(v, 0) for k, v in row.items()} for row in reader]


def save(path: Path, stream: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not stream:
        return
    # collect all keys across all rows to handle mixed fieldnames
    all_keys = list(dict.fromkeys(k for row in stream for k in row))
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys,
                                extrasaction="ignore",
                                restval=0)
        writer.writeheader()
        writer.writerows(stream)


def compare(
    expected: list[dict],
    actual:   list[dict],
    signals:  list[str],
    name:     str = "module",
) -> bool:
    print(f"\n{'='*50}")
    print(f"SCOREBOARD: {name}")
    print(f"{'='*50}")

    if len(expected) != len(actual):
        print(f"❌ LENGTH MISMATCH — expected {len(expected)} rows, got {len(actual)}")
        return False

    passed = 0
    failed = 0

    for i, (exp, act) in enumerate(zip(expected, actual)):
        cycle_failed = False
        for sig in signals:
            e = exp.get(sig, 0)
            a = act.get(sig, 0)
            if e != a:
                if not cycle_failed:
                    print(f"\n❌ MISMATCH at cycle {i}:")
                    cycle_failed = True
                print(f"   {sig}: expected=0x{e:08x}  got=0x{a:08x}")
        if cycle_failed:
            failed += 1
        else:
            passed += 1

    print(f"\n{'='*50}")
    print(f"  total    : {len(expected)}")
    print(f"  PASSED   : {passed}")
    print(f"  FAILED   : {failed}")
    print(f"{'='*50}")

    if failed == 0:
        print("✅  ALL PASSED")
        return True
    else:
        print(f"❌  {failed} MISMATCHES")
        return False