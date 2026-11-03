"""Cycle model: one step() = one clk.

Every net carries a value and a "settled" flag, reset each cycle.

At the start of a cycle these nets are settled right away:
  - nets driven by waiting outputs (their value was decided at the last clk),
  - TB inputs (from the stimulus),
  - nets nobody drives (None, i.e. X).
Then a leaf fires once all of its input nets are settled: its golden ticks
once, its comb outputs settle their nets immediately (which may let more
leaves fire), its waiting outputs are held until the next cycle.

The cycle is done when every leaf has fired. If leaves remain but nothing
can fire, the design has a combinational loop, and step() reports it.

Evaluation order comes only from dependencies, never from declaration order.
"""
from typing import Dict, Iterable, Optional

from Engine.Netlist import Netlist, load


class CombLoopError(Exception):
    pass


def _port(name: str) -> str:
    """Port an element net belongs to: "d[3]" -> "d"."""
    return name.split("[", 1)[0]


class _Inst:
    """One golden. The model works with element nets ("d[3]"); the golden sees
    array ports as lists ({"d": [v0, v1, ...]}) and returns them as lists."""

    def __init__(self, leaf, spec, init: dict):
        self.leaf = leaf
        self.arrays = leaf.arrays or {}
        self.golden = spec.golden(**leaf.params, **init)
        self.comb = {p: n for p, n in leaf.outputs.items() if _port(p) in spec.comb}
        self.wait = {p: n for p, n in leaf.outputs.items() if _port(p) not in spec.comb}
        self.in_nets = set(leaf.inputs.values())
        self.out_ports = {_port(p) for p in leaf.outputs}
        start = self.golden.start() if hasattr(self.golden, "start") else {}
        self.pending = {p: v for p, v in self._flat(start or {}, partial=True).items()
                        if p in self.wait}
        for p in self.wait:
            self.pending.setdefault(p, None)

    def _flat(self, out: dict, partial=False) -> dict:
        """Golden's {port: value or list} -> {element net name: value}."""
        flat = {}
        for port, v in out.items():
            elems = self.arrays.get(port)
            if elems is None:
                flat[port] = v
                continue
            if v is None:
                v = [None] * len(elems)
            if not isinstance(v, (list, tuple)) or len(v) != len(elems):
                raise ValueError(f"golden of '{self.leaf.path}' ({self.leaf.module}): "
                                 f"'{port}' is an array of {len(elems)}, "
                                 f"got {v!r:.60}")
            flat.update(zip(elems, v))
        return flat

    def fire(self, values: list) -> dict:
        ins = {}
        for p, n in self.leaf.inputs.items():
            if _port(p) not in self.arrays:
                ins[p] = values[n]
        for port, elems in self.arrays.items():
            if elems[0] in self.leaf.inputs:
                ins[port] = [values[self.leaf.inputs[e]] for e in elems]
        out = self.golden.tick(ins)
        missing = self.out_ports - set(out)
        extra = set(out) - self.out_ports
        if missing or extra:
            raise KeyError(f"golden of '{self.leaf.path}' ({self.leaf.module}): "
                           f"missing outputs {sorted(missing)}, unknown outputs {sorted(extra)}")
        return self._flat(out)

    def take_tags(self) -> list:
        """Coverage tags the golden collected during this tick (and forget them)."""
        tags = getattr(self.golden, "tags", None)
        if not tags:
            return []
        taken = list(tags)
        tags.clear()
        return taken


class Model:
    def __init__(self, netlist: Netlist, components: dict,
                 init: Optional[Dict[str, dict]] = None):
        """init: per-instance golden state override, e.g. {"dut": {"pipe": [...]}}."""
        init = init or {}
        self.netlist = netlist
        self.insts = [_Inst(l, components[l.module], init.get(l.path, {}))
                      for l in netlist.leaves]
        unknown = set(init) - {l.path for l in netlist.leaves}
        if unknown:
            raise KeyError(f"init for unknown instances {sorted(unknown)}")

        n = len(netlist.nets)
        self.values: list = [None] * n
        self.held = {name: None for name in netlist.inputs}  # TB inputs hold their value
        driven = {net for i in self.insts for net in i.leaf.outputs.values()}
        self.floating = [x for x in range(n) if x not in driven
                         and x not in netlist.inputs.values()]
        self.readers = {x: [] for x in range(n)}
        for i in self.insts:
            for net in i.in_nets:
                self.readers[net].append(i)
        self.cycle = 0
        self.tags = []

    @classmethod
    def from_rtl(cls, files: Iterable[str], top: str, components: dict,
                 clocks: Iterable[str] = ("clk",), init=None, params=None) -> "Model":
        return cls(load(files, top, components, clocks, params), components, init)

    @property
    def inputs(self):
        return list(self.netlist.inputs)

    @property
    def outputs(self):
        return list(self.netlist.outputs)

    def peek(self, name: str):
        """Value of any net this cycle, by its readable name."""
        return self.values[self.netlist.nets.index(name)]

    def step(self, stimulus: Optional[dict] = None) -> dict:
        """Simulate one clk. Inputs not given keep their previous value.

        Returns the TB outputs as they are during this cycle, i.e. what a
        monitor sampling just before the clk edge would see. Values that the
        golden computes at this clk show up in the next call.
        """
        for name, v in (stimulus or {}).items():
            if name not in self.held:
                raise KeyError(f"'{name}' is not a TB input; inputs: {self.inputs}")
            self.held[name] = v

        values, settled = self.values, [False] * len(self.values)
        self.tags = []        # [(instance path, [tag, ...])] reported in this cycle

        def settle(net, v):
            values[net] = v
            settled[net] = True

        for i in self.insts:
            for p, net in i.wait.items():
                settle(net, i.pending[p])
        for name, net in self.netlist.inputs.items():
            settle(net, self.held[name])
        for net in self.floating:
            settle(net, None)

        waiting_on = {id(i): sum(not settled[x] for x in i.in_nets) for i in self.insts}
        ready = [i for i in self.insts if waiting_on[id(i)] == 0]
        fired = 0
        while ready:
            i = ready.pop()
            out = i.fire(values)
            fired += 1
            tags = i.take_tags()
            if tags:
                self.tags.append((i.leaf.path, tags))
            for p in i.wait:
                i.pending[p] = out[p]
            for p, net in i.comb.items():
                settle(net, out[p])
                for r in self.readers[net]:
                    waiting_on[id(r)] -= 1
                    if waiting_on[id(r)] == 0:
                        ready.append(r)

        if fired != len(self.insts):
            stuck = [i for i in self.insts if waiting_on[id(i)] > 0]
            detail = "; ".join(
                f"{i.leaf.path} waits on "
                + ", ".join(self.netlist.nets[x] for x in sorted(i.in_nets) if not settled[x])
                for i in stuck)
            raise CombLoopError(f"cycle {self.cycle}: combinational loop: {detail}")

        self.cycle += 1
        return {name: values[net] for name, net in self.netlist.outputs.items()}
