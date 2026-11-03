"""Read the RTL (TB + DUT sources) and flatten it into a netlist.

Structure comes from the RTL: pyslang elaborates it (parameters, generate,
.* connections), we walk the instance tree from the TB and collapse every
port-to-net and `assign a = b;` alias into one net.

An instance whose module has a component (LeafSpec) becomes a leaf: its
insides are not read, the golden models them. Any other instance is pure
structure and is walked into.

The TB is the entry point: its signals are the model's global inputs
(driven by nobody inside) and outputs (driven by a leaf).

Unpacked arrays (`logic [31:0] d [0:8]`) are split into one net per element,
named like the element: "d[3]". A leaf sees an array port as a list (see
Leaf.arrays); the TB, the stimulus and Connections.json see the elements.

Files without `timescale get DEFAULT_TIMESCALE, as simulators do, so the
RTL may leave it to the TB.
"""
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import pyslang
from pyslang import ast, syntax

SK = ast.SymbolKind
EK = ast.ExpressionKind


DEFAULT_TIMESCALE = "1ns/1ps"


class NetlistError(Exception):
    pass


def _elements(t, where):
    """Index values of an unpacked array type, left to right; None for a
    plain signal. Only one unpacked dimension is supported."""
    if not t.isUnpackedArray:
        return None
    if t.arrayElementType.isUnpackedArray:
        raise NetlistError(f"{where}: arrays with more than one unpacked dimension "
                           f"are not supported yet")
    r = t.fixedRange
    step = 1 if r.right >= r.left else -1
    return list(range(r.left, r.right + step, step))


@dataclass
class Leaf:
    path: str                 # instance path below the TB, e.g. "dut"
    module: str               # RTL module name, e.g. "mac_q16"
    params: Dict[str, object] # elaborated RTL parameters
    inputs: Dict[str, int]    # port -> net index; array ports as "d[0]", "d[1]", ...
    outputs: Dict[str, int]
    arrays: Dict[str, List[str]] = None   # array port -> its element names, in order


@dataclass
class Netlist:
    top: str
    nets: List[str]           # net index -> readable name
    inputs: Dict[str, int]    # TB signal -> net, driven from outside
    outputs: Dict[str, int]   # TB signal -> net, driven by a leaf
    leaves: List[Leaf]
    widths: Dict[str, int]    # TB signal -> bit width (array elements: "d[3]")


def load(files: Iterable[str], top: str, components: dict,
         clocks: Iterable[str] = ("clk",), params: Optional[dict] = None) -> Netlist:
    """params: override the TB's parameters, e.g. {"PIPELINE_STAGES": 6}."""
    comp = _compile(files, top, params or {})
    tops = {t.name: t for t in comp.getRoot().topInstances}
    if top not in tops:
        raise NetlistError(f"top '{top}' not found; uninstantiated modules: {sorted(tops)}")
    return _Builder(tops[top], components, set(clocks)).build()


def _compile(files, top, params) -> ast.Compilation:
    opts = ast.CompilationOptions()
    opts.topModules = {top}
    opts.paramOverrides = [f"{k}={v}" for k, v in params.items()]
    opts.defaultTimeScale = pyslang.TimeScale.fromString(DEFAULT_TIMESCALE)
    comp = ast.Compilation(pyslang.Bag([opts]))
    for f in files:
        comp.addSyntaxTree(syntax.SyntaxTree.fromFile(str(f)))
    errors = [d for d in comp.getAllDiagnostics() if d.isError()]
    if errors:
        text = pyslang.DiagnosticEngine.reportAll(comp.sourceManager, errors)
        raise NetlistError("RTL does not elaborate:\n" + text)
    return comp


class _Builder:
    def __init__(self, tb, components, clocks):
        self.tb = tb
        self.components = components
        self.clocks = clocks
        self.parent: Dict[str, str] = {}
        self.raw_leaves = []  # (path, module, params, {port: key}, {port: key})

    # --- union-find over signal keys -------------------------------------
    def _find(self, k: str) -> str:
        self.parent.setdefault(k, k)
        while self.parent[k] != k:
            self.parent[k] = self.parent[self.parent[k]]
            k = self.parent[k]
        return k

    def _union(self, a: str, b: str):
        self.parent[self._find(a)] = self._find(b)

    def _union_keys(self, a, b, where):
        """Join two _keys() results: a signal with a signal, an array with an
        array element by element (by position, as SystemVerilog assigns them)."""
        (ka, ia), (kb, ib) = a, b
        if (ia is None) != (ib is None) or (ia is not None and len(ka) != len(kb)):
            raise NetlistError(f"{where}: array and signal (or arrays of different "
                               f"sizes) connected together")
        for x, y in (zip(ka, kb) if ia is not None else [(ka, kb)]):
            self._union(x, y)

    # --- expressions -> signal keys ---------------------------------------
    def _key(self, e, where: str) -> str:
        """Key of a plain signal (or one element of an array)."""
        keys = self._keys(e, where)
        if keys[1] is not None:
            raise NetlistError(f"{where}: a whole array where one signal is expected")
        return keys[0]

    def _base(self, e, where: str) -> str:
        """Key of what an element select indexes into (array or vector)."""
        if e.kind == EK.NamedValue:
            return e.symbol.hierarchicalPath
        return self._key(e, where)

    def _keys(self, e, where: str):
        """(key, None) for a plain signal, ([element keys], [indices]) for a whole array."""
        if e.kind == EK.Assignment:          # output port connections
            return self._keys(e.left, where)
        if e.kind == EK.Conversion and e.isImplicit:
            return self._keys(e.operand, where)
        if e.kind == EK.NamedValue:
            base = e.symbol.hierarchicalPath
            idx = _elements(e.type, where)
            if idx is None:
                return base, None
            return [f"{base}[{i}]" for i in idx], idx
        if e.kind == EK.ElementSelect and e.selector.constant is not None:
            return f"{self._base(e.value, where)}[{int(e.selector.constant.value)}]", None
        raise NetlistError(
            f"{where}: connection '{str(e.syntax).strip() if e.syntax else e.kind}' "
            f"is not supported yet (only plain names and constant element selects)")

    # --- walking ------------------------------------------------------------
    def _rel(self, path: str) -> str:
        prefix = self.tb.name + "."
        return path[len(prefix):] if path.startswith(prefix) else path

    def _walk(self, scope, is_top: bool, module: str = None):
        for m in scope:
            k = m.kind
            if k == SK.Instance:
                self._instance(m)
            elif k == SK.ContinuousAssign:
                a = m.assignment
                where = f"assign in {self._rel(scope.hierarchicalPath) or self.tb.name}"
                self._union_keys(self._keys(a.left, where), self._keys(a.right, where), where)
            elif k == SK.GenerateBlock:
                if not m.isUninstantiated:
                    self._walk(m, is_top, module)
            elif k == SK.GenerateBlockArray:
                for entry in m.entries:
                    if not entry.isUninstantiated:
                        self._walk(entry, is_top, module)
            elif k == SK.ProceduralBlock and not is_top:
                if m.procedureKind in (ast.ProceduralBlockKind.Initial,
                                       ast.ProceduralBlockKind.Final):
                    continue
                raise NetlistError(
                    f"'{self._rel(scope.hierarchicalPath)}' has behavioural logic "
                    f"({m.procedureKind.name}) but its module has no component; "
                    f"add Components/{module}_node.py "
                    f"or move the logic into a leaf module")
            # the TB's initial/always blocks (dumpfile, clock) are ignored

    def _instance(self, inst):
        module = inst.definition.name
        path = inst.hierarchicalPath
        rel = self._rel(path)
        if module in self.components:
            params = {}
            for p in inst.body:
                if p.kind == SK.Parameter and not p.isLocalParam:
                    v = p.value.value
                    try:
                        params[p.name] = int(v)
                    except (TypeError, ValueError):
                        params[p.name] = str(v)
            ins, outs, arrays = {}, {}, {}
            for pc in inst.portConnections:
                name = pc.port.name
                if name in self.clocks:
                    continue
                where = f"{rel}.{name}"
                d = pc.port.direction
                if d not in (ast.ArgumentDirection.In, ast.ArgumentDirection.Out):
                    raise NetlistError(f"{where}: {d.name} ports are not supported")
                side = ins if d == ast.ArgumentDirection.In else outs
                idx = _elements(pc.port.type, where)
                if idx is None:
                    side[name] = (f"{path}.{name}<unconnected>" if pc.expression is None
                                  else self._key(pc.expression, where))
                    continue
                keys = ([f"{path}.{name}[{i}]<unconnected>" for i in idx]
                        if pc.expression is None else self._keys(pc.expression, where)[0])
                if len(keys) != len(idx):
                    raise NetlistError(f"{where}: array of {len(keys)} elements on a port "
                                       f"of {len(idx)}")
                arrays[name] = [f"{name}[{i}]" for i in idx]
                for elem, key in zip(arrays[name], keys):
                    side[elem] = key
            self.raw_leaves.append((rel, module, params, ins, outs, arrays))
            return
        # structural module: alias its ports to the outer nets, then walk in
        for pc in inst.portConnections:
            if pc.port.name in self.clocks or pc.expression is None:
                continue
            where = f"{rel}.{pc.port.name}"
            inner = pc.port.internalSymbol.hierarchicalPath
            idx = _elements(pc.port.type, where)
            inner_keys = (inner, None) if idx is None else ([f"{inner}[{i}]" for i in idx], idx)
            self._union_keys(inner_keys, self._keys(pc.expression, where), where)
        self._walk(inst.body, is_top=False, module=module)

    # --- result ---------------------------------------------------------------
    def build(self) -> Netlist:
        self._walk(self.tb.body, is_top=True)

        tb_signals, widths = [], {}
        for m in self.tb.body:
            if m.kind not in (SK.Variable, SK.Net) or m.name in self.clocks:
                continue
            idx = _elements(m.type, f"{self.tb.name}.{m.name}")
            if idx is None:
                tb_signals.append(m.name)
                widths[m.name] = m.type.bitWidth
            else:                                  # one TB signal per element
                for i in idx:
                    tb_signals.append(f"{m.name}[{i}]")
                    widths[f"{m.name}[{i}]"] = m.type.arrayElementType.bitWidth
        tb_key = {n: f"{self.tb.name}.{n}" for n in tb_signals}

        index: Dict[str, int] = {}
        names: List[str] = []

        def net(key: str) -> int:
            root = self._find(key)
            if root not in index:
                index[root] = len(names)
                names.append(self._rel(key))
            return index[root]

        for n in tb_signals:  # TB names win as readable net names
            net(tb_key[n])

        leaves, drivers = [], {}
        for rel, module, params, ins, outs, arrays in self.raw_leaves:
            leaf = Leaf(rel, module, params,
                        {p: net(k) for p, k in ins.items()},
                        {p: net(k) for p, k in outs.items()}, arrays)
            for port, n in leaf.outputs.items():
                if n in drivers:
                    raise NetlistError(
                        f"net '{names[n]}' has two drivers: {drivers[n]} and {rel}.{port}")
                drivers[n] = f"{rel}.{port}"
            bad = self.components[module].comb - set(leaf.outputs) - set(arrays)
            if bad:
                raise NetlistError(
                    f"component for '{module}' marks {sorted(bad)} as comb, "
                    f"but the RTL has no such outputs")
            leaves.append(leaf)

        inputs, outputs, seen = {}, {}, set()
        for n in tb_signals:
            i = net(tb_key[n])
            if i in seen:          # another name for a TB signal already listed
                continue
            seen.add(i)
            (outputs if i in drivers else inputs)[n] = i
        return Netlist(self.tb.name, names, inputs, outputs, leaves, widths)
