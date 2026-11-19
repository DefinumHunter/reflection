"""Mixed-direction interface modport and conflicting-driver regression."""
import unittest
from pathlib import Path
from types import SimpleNamespace

from Engine.Netlist import NetlistError, load


FIXTURE = Path(__file__).resolve().parent / "interface_fixture"


class InterfaceHandshakeNetlistTest(unittest.TestCase):
    def _load(self, top):
        return load(
            [FIXTURE / "handshake.sv"],
            top,
            {"handshake_stage": SimpleNamespace(comb=set())},
        )

    def test_mixed_direction_modports_and_chained_handshake(self):
        nl = self._load("handshake_top")
        leaves = {leaf.path: leaf for leaf in nl.leaves}
        self.assertEqual(set(leaves), {"stage0", "stage1"})
        for leaf in leaves.values():
            self.assertEqual(set(leaf.inputs), {
                "upstream.data", "upstream.valid", "downstream.ready"
            })
            self.assertEqual(set(leaf.outputs), {
                "upstream.ready", "downstream.data", "downstream.valid"
            })

        a, b = leaves["stage0"], leaves["stage1"]
        for field in ("data", "valid"):
            self.assertEqual(a.outputs[f"downstream.{field}"],
                             b.inputs[f"upstream.{field}"])
        # Backpressure flows in the opposite direction.
        self.assertEqual(b.outputs["upstream.ready"],
                         a.inputs["downstream.ready"])
        self.assertNotEqual(a.outputs["downstream.data"],
                            a.outputs["downstream.valid"])
        self.assertEqual(nl.widths["middle.data"], 16)
        self.assertEqual(nl.widths["middle.ready"], 1)

    def test_multiple_drivers_on_same_interface_are_rejected(self):
        with self.assertRaises(NetlistError):
            self._load("handshake_bad_top")


if __name__ == "__main__":
    unittest.main()
