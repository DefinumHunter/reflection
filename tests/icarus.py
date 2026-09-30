"""Run a TB in Icarus with a per-cycle stimulus table and read back its outputs.

Test-only helper for checking the Python model against the real RTL; it is
not the cocotb/UVM bench. It generates a small harness that instantiates the
user's TB unchanged and drives/samples its signals hierarchically:
cycle c: inputs applied just after the clk edge, outputs sampled just before
the next edge -- the same moment Model.step() describes.
None in the stimulus is driven as X; X/Z read back become None.
"""
import re
import shutil
import subprocess
from pathlib import Path

available = shutil.which("iverilog") is not None and shutil.which("vvp") is not None


def _hex(v):
    return "x" if v is None else f"{v:x}"


def _parse(tok):
    return None if re.search("[xXzZ]", tok) else int(tok, 16)


def run(files, tb, inputs, outputs, rows, workdir, clock="clk", params=None):
    """params: override the TB's parameters (via defparam)."""
    workdir = Path(workdir)
    defparams = "\n".join(f"    defparam t.{k} = {v};" for k, v in (params or {}).items())
    regs = "\n".join(f"    reg [63:0] v_{s};" for s in inputs)
    scan = " ".join(["%h"] * len(inputs))
    scan_args = ", ".join(f"v_{s}" for s in inputs)
    drive = "\n".join(f"                t.{s} = v_{s};" for s in inputs)
    show = " ".join(["%h"] * len(outputs))
    show_args = ", ".join(f"t.{s}" for s in outputs)
    harness = f"""`timescale 1ns/1ps
module rfl_harness;
    {tb} t();
{defparams}
{regs}
    integer fin, fout, r;
    initial t.{clock} = 0;
    always #5 t.{clock} = ~t.{clock};
    initial begin
        fin  = $fopen("vec.txt", "r");
        fout = $fopen("out.txt", "w");
        #6;
        while (!$feof(fin)) begin
            r = $fscanf(fin, "{scan}\\n", {scan_args});
            if (r == {len(inputs)}) begin
{drive}
                #8;
                $fdisplay(fout, "{show}", {show_args});
                #2;
            end
        end
        $fclose(fout);
        $finish;
    end
endmodule
"""
    (workdir / "rfl_harness.sv").write_text(harness, encoding="utf-8")
    (workdir / "vec.txt").write_text(
        "".join(" ".join(_hex(r[s]) for s in inputs) + "\n" for r in rows), encoding="utf-8")
    subprocess.run(["iverilog", "-g2012", "-s", "rfl_harness", "-o", "sim",
                    *map(str, files), "rfl_harness.sv"],
                   cwd=workdir, check=True, capture_output=True, text=True)
    subprocess.run(["vvp", "-n", "sim"], cwd=workdir, check=True, capture_output=True)
    lines = (workdir / "out.txt").read_text(encoding="utf-8").splitlines()
    return [dict(zip(outputs, map(_parse, l.split()))) for l in lines]


def diff(model, rtl):
    """[(cycle, signal, model, rtl)] where they differ."""
    return [(c, s, model[c][s], rtl[c][s])
            for c in range(len(rtl)) for s in rtl[c] if model[c][s] != rtl[c][s]]
