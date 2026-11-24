"""Tests of src/rdf_compare.py on synthetic RDF tables (needs numpy: MLMD venv)."""
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE = importlib.util.find_spec("numpy") is not None


@unittest.skipUnless(HAVE, "needs numpy (MLMD venv)")
class TestRdfCompare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "src"))
        import numpy as np
        import rdf_compare
        cls.np, cls.rc = np, rdf_compare

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp))

    def table(self, name, peak=2.1, height=8.0, se=0.05, flat=False):
        np = self.np
        r = np.arange(0.01, 9.7, 0.02)
        if flat:
            g = np.where(r > 3.0, 0.3, 0.0)
        else:
            g = height * np.exp(-((r - peak) / 0.08) ** 2) + np.where(r > 3.5, 1.0, 0.0)
        shell = 4 * np.pi * 0.01 * r ** 2 * 0.02
        cn = np.cumsum(g * shell)
        s = np.full_like(r, se) * (g > 0)
        cols = ["r_center_A", "r_upper_A", "g_Al-Cl", "se_Al-Cl", "cn_Al-Cl", "g_Al-Al", "se_Al-Al", "cn_Al-Al"]
        gf = np.where(r > 3.0, 0.3, 0.0)
        data = np.column_stack([r, r + 0.01, g, s, cn, gf, 0 * r, np.cumsum(gf * shell)])
        p = self.tmp / name
        np.savetxt(str(p), data, delimiter=",", header=",".join(cols), comments="", fmt="%.6f")
        return str(p)

    def test_identical_tables_pass(self):
        ok, out = self.rc.compare(self.table("a.csv"), self.table("b.csv"))
        self.assertTrue(ok)
        self.assertEqual(out["Al-Cl"]["status"], "pass")
        self.assertAlmostEqual(out["Al-Cl"]["r_peak_ref_A"], 2.10, delta=0.0101)   # bin centre next to 2.10
        self.assertEqual(out["Al-Al"]["status"], "no peak")

    def test_shifted_peak_fails(self):
        ok, out = self.rc.compare(self.table("a.csv", peak=2.2), self.table("b.csv"))
        self.assertFalse(ok)
        self.assertGreater(abs(out["Al-Cl"]["dr_peak_A"]), 0.04)

    def test_height_change_judged_in_sigma(self):
        ok, out = self.rc.compare(self.table("a.csv", height=8.1), self.table("b.csv"))
        self.assertTrue(ok)                       # 0.1 / (0.05 * sqrt 2) = 1.4 sigma
        ok, out = self.rc.compare(self.table("a.csv", height=9.0), self.table("b.csv"))
        self.assertFalse(ok)                      # 14 sigma

    def test_cn_error_is_sum_of_shell_weighted_se(self):
        np = self.np
        g = np.array([0.0, 1.0, 2.0])
        cn = np.array([0.0, 0.5, 1.5])
        e = self.rc.cn_error(g, np.array([0.0, 0.1, 0.1]), cn)
        self.assertTrue(np.allclose(e, [0.0, 0.05, 0.10]))


if __name__ == "__main__":
    unittest.main()
