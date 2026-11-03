"""Check the connections parsed from the RTL against a hand-written list.

The model takes its connections from the RTL, so it repeats any wiring
mistake there. This check is the independent opinion: you write down what
should be connected, and every difference is reported.

File format (JSON):
    {
      "scope": "dut",                         optional: prefix for instance names
      "connections": {
        "u_mux.out_sel": ["u_mac.sel"],       source -> every place it goes
        "rst_n":         ["u_mux.rst_n", "u_mac.rst_n"],
        "u_mac.out_res": ["out_res"]
      }
    }
A source is a leaf output port ("inst.port") or a TB input ("name").
A destination is a leaf input port or a TB output. Names without a dot are
TB signals and are not prefixed with the scope. Clocks are not listed.

Strict: an RTL connection missing from the file is an error too, otherwise a
forgotten line would silently mean an unchecked connection. Outputs going
nowhere (e.g. `.busy()`) may be left out or listed with [].
"""
import json
from pathlib import Path

from Engine.Netlist import Netlist


class ConnectionMismatch(Exception):
    pass


def actual(netlist: Netlist, scope: str = "") -> dict:
    """{source: set(destinations)} as parsed from the RTL, plus undriven inputs
    under the key None."""
    prefix = scope + "." if scope else ""

    def ep(path, port):
        path = path[len(prefix):] if prefix and path.startswith(prefix) else path
        return f"{path}.{port}"

    driver, readers = {}, {}
    for name, net in netlist.inputs.items():
        driver[net] = name
    for leaf in netlist.leaves:
        for port, net in leaf.outputs.items():
            driver[net] = ep(leaf.path, port)
        for port, net in leaf.inputs.items():
            readers.setdefault(net, set()).add(ep(leaf.path, port))
    for name, net in netlist.outputs.items():
        readers.setdefault(net, set()).add(name)

    result = {src: set() for src in driver.values()}
    for net, dsts in readers.items():
        result.setdefault(driver.get(net), set()).update(dsts)
    return result


def check(netlist: Netlist, spec: dict) -> list:
    """Every difference between the RTL and the spec, as readable lines."""
    got = actual(netlist, spec.get("scope", ""))
    want = {src: list(dsts) for src, dsts in spec["connections"].items()}
    problems = []

    undriven = got.pop(None, set())
    for dst in sorted(undriven):
        problems.append(f"{dst} is not driven by anything")

    got_driver = {d: s for s, dsts in got.items() for d in dsts}
    known = set(got) | set(got_driver) | undriven

    seen = {}
    for src, dsts in want.items():
        for d in dsts:
            if d in seen:
                problems.append(f"{d} is listed under two sources: {seen[d]} and {src}")
            seen[d] = src

    for src, dsts in want.items():
        if src not in got:
            problems.append(f"{src} is an input, it cannot be a source" if src in known
                            else f"{src} is not an output port or a TB input")
            continue
        for d in sorted(set(dsts) - got[src]):
            if d not in known:
                problems.append(f"{src} -> {d}: {d} is not an input port or a TB output")
            else:
                problems.append(f"{src} -> {d} expected, but in the RTL {d} is driven by "
                                f"{got_driver.get(d, 'nothing')}")
        for d in sorted(got[src] - set(dsts)):
            problems.append(f"{src} -> {d} is in the RTL but not in the list")

    for src in sorted(set(got) - set(want)):
        if got[src]:
            problems.append(f"{src} -> {', '.join(sorted(got[src]))} "
                            f"is in the RTL but {src} is not in the list")
    return problems


def check_file(netlist: Netlist, path) -> None:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    problems = check(netlist, spec)
    if problems:
        raise ConnectionMismatch(
            f"{Path(path).name}: {len(problems)} difference(s) with the RTL:\n  "
            + "\n  ".join(problems))
