"""Structural interface regression: run with python -m unittest tests.test_interface_netlist.

This tests elaboration and net identities only; no simulator or golden ticks.
"""
import unittest
from pathlib import Path
from types import SimpleNamespace

from Engine.Netlist import load


FIXTURE = Path(__file__).resolve().parent / "interface_fixture"


class InterfaceNetlistTest(unittest.TestCase):
    def test_five_instances_and_interface_connections(self):
        # Netlist only needs the component's comb set, not its golden class.
        components = {"interface_test_pe": SimpleNamespace(comb=set())}
        nl = load(
            [FIXTURE / "interfaces.sv", FIXTURE / "pe.sv", FIXTURE / "top.sv"],
            "interface_test_top",
            components,
        )

        leaves = {leaf.path: leaf for leaf in nl.leaves}
        self.assertEqual(set(leaves), {f"pe{i}" for i in range(5)})
        self.assertEqual({leaf.module for leaf in leaves.values()},
                         {"interface_test_pe"})

        for leaf in leaves.values():
            self.assertEqual(set(leaf.inputs),
                             {"upstream.data", "upstream.valid"})
            self.assertEqual(set(leaf.outputs),
                             {"downstream.data", "downstream.valid"})
            self.assertNotEqual(leaf.inputs["upstream.data"],
                                leaf.inputs["upstream.valid"])

        # A chained connection must use the exact same net index.
        for field in ("data", "valid"):
            self.assertEqual(leaves["pe0"].outputs[f"downstream.{field}"],
                             leaves["pe1"].inputs[f"upstream.{field}"])
            # Two consumers of the same interface share their input net.
            self.assertEqual(leaves["pe3"].inputs[f"upstream.{field}"],
                             leaves["pe4"].inputs[f"upstream.{field}"])
            # Independent interfaces must not be accidentally merged.
            self.assertNotEqual(leaves["pe0"].inputs[f"upstream.{field}"],
                                leaves["pe2"].inputs[f"upstream.{field}"])
            self.assertNotEqual(leaves["pe3"].outputs[f"downstream.{field}"],
                                leaves["pe4"].outputs[f"downstream.{field}"])

        self.assertIn("in0.data", nl.inputs)
        self.assertIn("in1.data", nl.inputs)
        self.assertIn("out1.data", nl.outputs)
        self.assertIn("out4.valid", nl.outputs)
        self.assertEqual(nl.widths["in0.data"], 32)
        self.assertEqual(nl.widths["out4.valid"], 1)


if __name__ == "__main__":
    unittest.main()
