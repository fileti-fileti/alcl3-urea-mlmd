"""Tests of src/lammps_bench.py: LAMMPS output parsers, the rule, and the data files.

Need numpy and ase: run with the MLMD venv (skipped otherwise), as tests/test_mlmd.py.
"""
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE = all(importlib.util.find_spec(m) for m in ("numpy", "ase"))
BOXES = Path("/scratch/acmes/eudes.fileti3/projects/alcl3-urea-mlmd-store/data/boxes/mlmd-boxes-r1.0-v2")

LOG = """LAMMPS (10 Sep 2025)
Per MPI rank memory allocation (min/avg/max) = 3.1 | 3.1 | 3.1 Mbytes
   Step         PotEng
         0  -312744.1234567890
Loop time of 1.2 on 6 procs for 0 steps with 1512 atoms
"""
PERF = """Performance: 0.264 ns/day, 90.7 hours/ns, 6.130 timesteps/s, 9.268 katom-step/s
...
Performance: 0.300 ns/day, 80.0 hours/ns, 6.944 timesteps/s, 10.5 katom-step/s
"""
DUMP = """ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id fx fy fz
1 0.1000000000 -0.2000000000 0.3000000000
2 -0.1000000000 0.2000000000 -0.3000000000
"""


@unittest.skipUnless(HAVE, "needs numpy and ase (MLMD venv)")
class TestLammpsBench(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "src"))
        import lammps_bench
        cls.m = lammps_bench

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp))

    def test_parsers(self):
        self.assertAlmostEqual(self.m.parse_pe(LOG), -312744.1234567890)
        self.assertAlmostEqual(self.m.parse_performance(PERF), 6.944)
        f = self.m.parse_forces(DUMP, 2)
        self.assertEqual(f.shape, (2, 3))
        self.assertAlmostEqual(f[1, 2], -0.3)
        with self.assertRaises(ValueError):
            self.m.parse_performance("no perf here")
        with self.assertRaises(ValueError):
            self.m.parse_forces(DUMP.replace("\n1 0.1", "\n3 0.1"), 2)
        self.assertTrue(self.m.gpu_used("12345, /path/bin/lmp, 2100 MiB\n"))
        self.assertFalse(self.m.gpu_used(""))

    def test_verdict(self):
        fast = {"f64": 12.3, "f32": 17.9}
        self.assertEqual(self.m.verdict(True, fast, True, True), "yes")
        self.assertEqual(self.m.verdict(True, {"f64": 12.3, "f32": 17.8}, True, True), "no")
        self.assertEqual(self.m.verdict(True, {"f64": 3.0, "f32": 4.0}, True, True), "no")
        self.assertEqual(self.m.verdict(False, fast, True, True), "inconclusive")
        self.assertEqual(self.m.verdict(True, fast, False, True), "inconclusive")
        self.assertEqual(self.m.verdict(True, fast, True, False), "inconclusive")

    @unittest.skipUnless(BOXES.is_dir(), "start boxes not present")
    def test_data_files_round_trip(self):
        import numpy as np
        from ase.data import atomic_numbers
        from ase.io.lammpsdata import read_lammps_data
        import mlmd
        self.m.write_inputs(self.tmp, BOXES, 29.729979)
        for box in self.m.BOXES:
            a0 = mlmd.read_pdb(BOXES / "r1.0_{}.pdb".format(box), 29.729979)
            a = read_lammps_data(str(self.tmp / "{}.data".format(box)), atom_style="atomic", units="metal",
                                 Z_of_type={i + 1: atomic_numbers[s] for i, s in enumerate(self.m.SPECORDER)})
            self.assertEqual(a.get_chemical_symbols(), a0.get_chemical_symbols())
            self.assertTrue(np.allclose(a.positions, a0.positions, atol=1e-8))
            self.assertTrue(np.allclose(a.cell.lengths(), [29.729979] * 3, atol=1e-9))
            text = (self.tmp / "sp_{}_f64.in".format(box)).read_text()
            self.assertIn("pair_coeff * * run2r10m0_f64.model-lammps.pt Al Cl O N C H", text)
        self.assertIn("run 500", (self.tmp / "bench_f32.in").read_text())


if __name__ == "__main__":
    unittest.main()
