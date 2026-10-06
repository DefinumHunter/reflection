"""
Engine/RTLParams.py
Reads parameter declarations from SystemVerilog files.
No regex — plain line-by-line parsing.
Returns a dict of all parameters found in the file.
"""

from pathlib import Path


def read_rtl_params(rtl_file: Path) -> dict[str, int]:
    """
    Reads all 'parameter' declarations from a SystemVerilog file.
    Handles:
        parameter int PIPELINE_STAGES = 4;
        parameter PIPELINE_STAGES = 4;
        parameter int PIPELINE_STAGES = 4  // comment
    Returns { "PIPELINE_STAGES": 4, ... }
    Skips non-integer parameters silently.
    """
    params = {}

    for line in rtl_file.read_text().splitlines():
        # strip inline comments
        line = line.split("//")[0].strip()

        if "parameter" not in line or "=" not in line:
            continue

        # take everything after the keyword "parameter"
        after = line.split("parameter", 1)[-1].strip()

        # replace "=" with space for uniform splitting
        after = after.replace("=", " ")

        # split into tokens, remove empty strings
        parts = [p for p in after.split() if p]

        # need at least name and value
        if len(parts) < 2:
            continue

        # last token is the value (may have trailing ; or ,)
        value_str = parts[-1].rstrip(";,").strip()

        # second-to-last token is the name
        # (handles both "int NAME value" and "NAME value")
        name = parts[-2].rstrip(";,").strip()

        # skip if name looks like a type keyword
        if name in ("int", "logic", "bit", "byte", "shortint",
                    "longint", "integer", "time"):
            if len(parts) >= 3:
                name = parts[-3].rstrip(";,").strip()
            else:
                continue

        try:
            params[name] = int(value_str)
        except ValueError:
            pass  # skip string or expression parameters

    return params
