"""Read the RTL (TB + DUT sources) and flatten it into a netlist.

Structure comes from the RTL: pyslang elaborates it (parameters, generate,
.* connections), we walk the instance tree from the TB and collapse every
port-to-net and `assign a = b;` alias into one net.

An instance whose module has a component (LeafSpec) becomes a leaf: its
insides are not read, the golden models them. Any other instance is pure
structure and is walked into.

The TB is the entry point: its signals are the model's global inputs
(driven by nobody inside) and outputs (driven by a leaf).
"""
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import pyslang
from pyslang import ast, syntax

SK = ast.SymbolKind
EK = ast.ExpressionKind


class NetlistError(Exception):
    pass


@dataclass
class Leaf:
    path: str                 # instance path below the TB, e.g. "dut"
    module: str               # RTL module name, e.g. "mac_q16"
    params: Dict[str, object] # elaborated RTL parameters
    inputs: Dict[str, int]    # port -> net index
    outputs: Dict[str, int]


@dataclass
class Netlist:
    top: str
    nets: List[str]           # net index -> readable name
    inputs: Dict[str, int]    # TB signal -> net, driven from outside
    outputs: Dict[str, int]   # TB signal -> net, driven by a leaf
    leaves: List[Leaf]
    widths: Dict[str, int]    # TB signal -> bit width


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

    # --- expressions -> signal keys ---------------------------------------
    def _key(self, e, where: str) -> str:
        if e.kind == EK.Assignment:          # output port connections
            return self._key(e.left, where)
        if e.kind == EK.Conversion and e.isImplicit:
            return self._key(e.operand, where)
        if e.kind == EK.NamedValue:
            return e.symbol.hierarchicalPath
        if e.kind == EK.ElementSelect and e.selector.constant is not None:
            return f"{self._key(e.value, where)}[{int(e.selector.constant.value)}]"
        raise NetlistError(
            f"{where}: connection '{str(e.syntax).strip() if e.syntax else e.kind}' "
            f"is not supported yet (only plain names and constant element selects)")

    # --- walking ------------------------------------------------------------
    def _rel(self, path: str) -> str:
        prefix = self.tb.name + "."
        return path[len(prefix):] if path.startswith(prefix) else path

    def _walk(self, scope, is_top: bool):
        for m in scope:
            k = m.kind
            if k == SK.Instance:
                self._instance(m)
            elif k == SK.ContinuousAssign:
                a = m.assignment
                where = f"assign in {self._rel(scope.hierarchicalPath) or self.tb.name}"
                self._union(self._key(a.left, where), self._key(a.right, where))
            elif k == SK.GenerateBlock:
                if not m.isUninstantiated:
                    self._walk(m, is_top)
            elif k == SK.GenerateBlockArray:
                for entry in m.entries:
                    if not entry.isUninstantiated:
                        self._walk(entry, is_top)
            elif k == SK.ProceduralBlock and not is_top:
                if m.procedureKind in (ast.ProceduralBlockKind.Initial,
                                       ast.ProceduralBlockKind.Final):
                    continue
                raise NetlistError(
                    f"'{self._rel(scope.hierarchicalPath)}' has behavioural logic "
                    f"({m.procedureKind.name}) but its module has no component; "
                    f"add a LeafSpec for it or move the logic into a leaf module")
            # the TB's initial/always blocks (dumpfile, clock) are ignored

    def _instance(self, inst):
        module = inst.definition.name
        path = inst.hierarchicalPath
        rel = self._rel(path)
        if module in self.components:
            params = {}
            for p in inst.body:
                if p.kind == SK.Parameter:
                    v = p.value.value
                    try:
                        params[p.name] = int(v)
                    except (TypeError, ValueError):
                        params[p.name] = str(v)
            ins, outs = {}, {}
            for pc in inst.portConnections:
                name = pc.port.name
                if name in self.clocks:
                    continue
                where = f"{rel}.{name}"
                key = (f"{path}.{name}<unconnected>" if pc.expression is None
                       else self._key(pc.expression, where))
                d = pc.port.direction
                if d == ast.ArgumentDirection.In:
                    ins[name] = key
                elif d == ast.ArgumentDirection.Out:
                    outs[name] = key
                else:
                    raise NetlistError(f"{where}: {d.name} ports are not supported")
            self.raw_leaves.append((rel, module, params, ins, outs))
            return
        # structural module: alias its ports to the outer nets, then walk in
        for pc in inst.portConnections:
            if pc.port.name in self.clocks or pc.expression is None:
                continue
            inner = pc.port.internalSymbol.hierarchicalPath
            self._union(inner, self._key(pc.expression, f"{rel}.{pc.port.name}"))
        self._walk(inst.body, is_top=False)

    # --- result ---------------------------------------------------------------
    def build(self) -> Netlist:
        self._walk(self.tb.body, is_top=True)

        tb_signals = [m.name for m in self.tb.body
                      if m.kind in (SK.Variable, SK.Net) and m.name not in self.clocks]
        tb_key = {n: f"{self.tb.name}.{n}" for n in tb_signals}
        widths = {m.name: m.type.bitWidth for m in self.tb.body
                  if m.kind in (SK.Variable, SK.Net) and m.name not in self.clocks}

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
        for rel, module, params, ins, outs in self.raw_leaves:
            leaf = Leaf(rel, module, params,
                        {p: net(k) for p, k in ins.items()},
                        {p: net(k) for p, k in outs.items()})
            for port, n in leaf.outputs.items():
                if n in drivers:
                    raise NetlistError(
                        f"net '{names[n]}' has two drivers: {drivers[n]} and {rel}.{port}")
                drivers[n] = f"{rel}.{port}"
            bad = self.components[module].comb - set(leaf.outputs)
            if bad:
                raise NetlistError(
                    f"component for '{module}' marks {sorted(bad)} as comb, "
                    f"but the RTL has no such outputs")
            leaves.append(leaf)

        inputs, outputs = {}, {}
        for n in tb_signals:
            i = net(tb_key[n])
            (outputs if i in drivers else inputs)[n] = i
        return Netlist(self.tb.name, names, inputs, outputs, leaves, widths)
