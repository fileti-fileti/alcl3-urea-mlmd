"""Tests of src/bond_width.py on a synthetic trajectory with a known bond-length spread.

Need numpy: run with the MLMD venv (skipped otherwise), as tests/test_mlmd.py.
"""
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE = importlib.util.find_spec("numpy") is not None


@unittest.skipUnless(HAVE, "needs numpy (MLMD venv)")
class TestBondWidth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "src"))
        import bond_width
        cls.m = bond_width

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp))

    def test_known_spread_per_block_and_minimum_image(self):
        import numpy as np
        rng = np.random.default_rng(0)
        L, nf = 10.0, 200
        g = np.arange(3) * L / 3
        n_pos = np.array([[x + 0.2, y + 1.5, z + 1.5] for x in g for y in g for z in g])  # N 3.33 A apart
        nb = len(n_pos)                                 # x = 0.2: those H sit across the x boundary
        u = np.tile([-1.0, 0.0, 0.0], (nb, 1))
        lines = []
        for f in range(nf):
            sigma = 0.01 if f < nf // 2 else 0.02
            r = 1.0 + rng.normal(0, sigma, nb)
            h_pos = (n_pos + r[:, None] * u) % L
            lines += [str(2 * nb + 1), "i = {}".format(f)]
            lines += ["N {:.8f} {:.8f} {:.8f}".format(*p) for p in n_pos]
            lines += ["H {:.8f} {:.8f} {:.8f}".format(*p) for p in h_pos]
            lines.append("Cl 5.0 5.0 5.0")
        p = self.tmp / "t.xyz"
        p.write_text("\n".join(lines) + "\n")
        sym, X = self.m.read_xyz(str(p))
        out = self.m.widths(sym, X, L, "N", "H", 1.2, 2)
        self.assertEqual(out["bonds"], nb)
        self.assertEqual(out["frames"], nf)
        s1, s2 = (b["std_A"] for b in out["blocks"])
        self.assertAlmostEqual(s1, 0.01, delta=0.001)
        self.assertAlmostEqual(s2, 0.02, delta=0.002)
        self.assertAlmostEqual(out["blocks"][0]["mean_A"], 1.0, delta=0.001)

    def test_bad_file(self):
        p = self.tmp / "bad.xyz"
        p.write_text("3\nc\nN 0 0 0\nH 1 0 0\n")
        with self.assertRaises(ValueError):
            self.m.read_xyz(str(p))


if __name__ == "__main__":
    unittest.main()
