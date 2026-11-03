"""The engine's own tests run on the worked example in tests/example/
(mac_q16, pe_input_mux, pe_mac_wrapper), not on the project's modules, so
they keep passing whatever is in hardware/ and Modules/."""
import os
from pathlib import Path

os.environ["REFLECTION_ROOT"] = str(Path(__file__).resolve().parent / "example")

import Project  # noqa: E402  (after REFLECTION_ROOT, so it picks the example)
