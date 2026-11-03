"""Write the Reflection TB for an RTL module from its ports.

    python -m Engine.MakeTb w_normalize            writes hardware/tb/tb_w_normalize.sv
    python -m Engine.MakeTb w_normalize --print    only prints it
    python -m Engine.MakeTb --all                  every module in hardware/rtl without a TB

A Reflection TB has no logic: one signal per port, named like the port, and
the module instantiated as `dut` with .*. Parameters become TB parameters, so
they can be overridden from the command line. Output arrays are declared as
`wire`: Icarus does not pass an unpacked array output port to a `logic`.

Widths are written as numbers for the parameters' default values. If a port
width depends on a parameter, overriding it needs the TB edited by hand; the
TB says so in a comment.
"""
import re
import sys

import pyslang
from pyslang import ast, syntax

import Project
from Engine.Netlist import DEFAULT_TIMESCALE, NetlistError


def _compile(module):
    opts = ast.CompilationOptions()
    opts.topModules = {module}
    opts.defaultTimeScale = pyslang.TimeScale.fromString(DEFAULT_TIMESCALE)
    comp = ast.Compilation(pyslang.Bag([opts]))
    for f in Project.rtl_sources():
        comp.addSyntaxTree(syntax.SyntaxTree.fromFile(str(f)))
    errors = [d for d in comp.getAllDiagnostics() if d.isError()]
    if errors:
        raise NetlistError("RTL does not elaborate:\n"
                           + pyslang.DiagnosticEngine.reportAll(comp.sourceManager, errors))
    tops = {t.name: t for t in comp.getRoot().topInstances}
    if module not in tops:
        raise NetlistError(f"module '{module}' not found in {Project.RTL_DIR}")
    return tops[module]


def _decl(t):
    """'logic signed [31:0]' and the unpacked part ' [0:8]' of a port type."""
    unpacked = ""
    if t.isUnpackedArray:
        r = t.fixedRange
        unpacked = f" [{r.left}:{r.right}]"
        t = t.arrayElementType
    w = t.bitWidth
    packed = "logic" + (" signed" if t.isSigned else "") + (f" [{w - 1}:0]" if w > 1 else "")
    return packed, unpacked


def tb_text(module: str) -> str:
    inst = _compile(module)
    params = [p for p in inst.body if p.kind == ast.SymbolKind.Parameter and not p.isLocalParam]
    ports = [p for p in inst.body.portList]
    rows = []
    for p in ports:
        packed, unpacked = _decl(p.type)
        out = p.direction == ast.ArgumentDirection.Out
        if out and unpacked:
            packed = packed.replace("logic", "wire ", 1)
        rows.append((packed, p.name + unpacked + ";",
                     "out" if out else "in" if p.direction == ast.ArgumentDirection.In
                     else p.direction.name))

    header = str(inst.definition.syntax.header.ports) if inst.definition.syntax else ""
    param_widths = any(re.search(rf"\b{q.name}\b", header) for q in params)

    width = max(len(r[0]) for r in rows)
    lines = ["`timescale 1ns / 1ps", "",
             "// Reflection TB, made by Engine/MakeTb.py from the ports of " + module + ".",
             "// No logic here: the bench drives and samples these signals."]
    if param_widths:
        lines.append("// Port widths depend on parameters: they are for the default values.")
    lines += ["", f"module tb_{module};"]
    for p in params:
        try:
            value = int(p.value.value)
            lines.append(f"    parameter int {p.name} = {value};")
        except (TypeError, ValueError):
            lines.append(f"    parameter {p.name} = {p.value};")
    if params:
        lines.append("")
    for packed, name, _ in rows:
        lines.append(f"    {packed:<{width}} {name}")
    lines.append("")
    if params:
        binds = ", ".join(f".{p.name}({p.name})" for p in params)
        lines.append(f"    {module} #({binds}) dut (.*);")
    else:
        lines.append(f"    {module} dut (.*);")
    lines += ["", "    initial begin", '        $dumpfile("waves.vcd");',
              f"        $dumpvars(0, tb_{module});", "    end", "endmodule", ""]
    return "\n".join(lines)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--all":
        made = 0
        for m in Project.rtl_modules():
            path = Project.TB_DIR / f"tb_{m}.sv"
            if path.exists():
                continue
            Project.TB_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(tb_text(m), encoding="utf-8")
            print(f"wrote {path.relative_to(Project.ROOT)}")
            made += 1
        print(f"{made} TB written")
        return 0
    module = argv[0]
    text = tb_text(module)
    if "--print" in argv:
        print(text)
        return 0
    path = Project.TB_DIR / f"tb_{module}.sv"
    if path.exists():
        print(f"{path.relative_to(Project.ROOT)} exists; delete it first or use --print")
        return 1
    Project.TB_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path.relative_to(Project.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
