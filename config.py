"""
config.py
Machine and tool configuration. Lives at repo root.

This is the only file you edit when:
  - switching simulators
  - moving to a new machine
  - updating tool paths or versions

Everything else in the project is machine-agnostic.

To switch simulator: change ACTIVE_SIM to one of the keys in SIMULATORS.
To override from CLI: python run.py --module mac_q16 --sim xcelium
"""

from dataclasses import dataclass, field
from pathlib import Path


# ── Simulator profile ─────────────────────────────────────────────

@dataclass
class SimConfig:
    name:        str          # cocotb_tools simulator name
    tool_path:   Path         # directory containing simulator executables
                              # empty = already on PATH
    module_load: str          # "module load ..." command on Linux HPC
                              # empty = no module loading needed
    wave_viewer: Path         # waveform viewer executable
    wave_format: str          # "vcd", "fsdb", "wlf"
    build_args:  list = field(default_factory=list)
    extra_env:   dict = field(default_factory=dict)


# ── Simulator profiles ────────────────────────────────────────────

SIMULATORS: dict[str, SimConfig] = {

    "icarus": SimConfig(
        name        = "icarus",
        tool_path   = Path(""),     # iverilog is on PATH
        module_load = "",
        wave_viewer = Path(r"C:\Users\INTEL\gtkwave-3.3.100-bin-win64\gtkwave64\bin\gtkwave.exe"),
        wave_format = "vcd",
        build_args  = [],
        extra_env   = {},
    ),

    "questa": SimConfig(
        name        = "questa",
        tool_path   = Path(r"C:\questasim64_2024.1\win64"),
        module_load = "",
        wave_viewer = Path(r"C:\questasim64_2024.1\win64\vsim.exe"),
        wave_format = "wlf",
        build_args  = ["-sv"],
        extra_env   = {},
    ),

    "xcelium": SimConfig(
        name        = "xcelium",
        tool_path   = Path(""),
        module_load = "cadence/XCELIUMMAIN/24.03.001",
        wave_viewer = Path("verdi"),
        wave_format = "fsdb",
        build_args  = ["-access", "+r", "-sv"],
        extra_env   = {"CDS_AUTO_64BIT": "all"},
    ),

    "vcs": SimConfig(
        name        = "vcs",
        tool_path   = Path(""),
        module_load = "synopsys/VCS/R-2020.12",
        wave_viewer = Path("verdi"),
        wave_format = "fsdb",
        build_args  = ["-full64", "-sverilog", "+acc"],
        extra_env   = {},
    ),
}

# ── Active selection ──────────────────────────────────────────────
# Change this one line to switch simulator.

ACTIVE_SIM: str = "icarus"
