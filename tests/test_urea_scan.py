"""Tests of src/urea_scan.py on a synthetic box with one urea of each kind and a known proton
transfer between two frames.

Need numpy: run with the MLMD venv (skipped otherwise), as tests/test_mlmd.py.
"""
import csv
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE = importlib.util.find_spec("numpy") is not None
L = 20.0


def urea(c):
    """C, O, N1, N2 of a planar urea with C at c, and the four N-H sites."""
    import numpy as np
    c = np.asarray(c, float)
    o, n1, n2 = c + [0, 0, 1.26], c + [1.15, 0, -0.67], c + [-1.15, 0, -0.67]
    h = [n1 + [0.87, 0, 0.5], n1 + [0, 0, -1.0], n2 + [-0.87, 0, 0.5], n2 + [0, 0, -1.0]]
    return [("C", c), ("O", o), ("N", n1), ("N", n2)], h, o


def box(frame):
    """Five ureas, two Al, one Cl. A: free, across the x boundary. B: O-bound to Al. C: bound
    to Al through N and O. D, E: free. Frame 0: all ureas normal. Frame 1: one H of C moved to
    the O of D (ureate + uronium), one H of E moved to its own O (tautomer)."""
    atoms = []
    centres = {"A": (0.5, 10, 10), "B": (6, 4, 4), "C": (14, 4, 4), "D": (6, 14, 14),
               "E": (14, 14, 14)}
    parts = {k: urea(v) for k, v in centres.items()}
    o_d, o_e = parts["D"][2], parts["E"][2]
    for k in "ABCDE":
        heavy, h, _ = parts[k]
        if frame == 1 and k == "C":
            h[1] = o_d + [0, 0, 0.98]
        if frame == 1 and k == "E":
            h[3] = o_e + [0, 0, 0.98]
        atoms += heavy + [("H", p) for p in h]
    atoms += [("Al", parts["B"][2] + [0, 0, 1.85]), ("Al", parts["C"][0][0][1] + [1.6, 0, 0.9]),
              ("Cl", [10.0, 10.0, 2.0])]
    return atoms


def write_xyz(path, frames, truncate=False):
    import numpy as np
    lines = []
    for atoms in frames:
        lines += [str(len(atoms)), "comment"]
        lines += ["{} {:.6f} {:.6f} {:.6f}".format(e, *(np.asarray(p, float) % L))
                  for e, p in atoms]
    if truncate:
        lines = lines[:-3]
    Path(path).write_text("\n".join(lines) + "\n")


@unittest.skipUnless(HAVE, "needs numpy (MLMD venv)")
class TestUreaScan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "src"))
        import urea_scan
        cls.m = urea_scan

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp))

    def counts(self, frame):
        import numpy as np
        atoms = box(frame)
        X = np.array([p for _, p in atoms]) % L
        return self.m.scan_frame([e for e, _ in atoms], X, L)

    def test_binding_classes_and_minimum_image(self):
        c = self.counts(0)
        self.assertEqual((c["free"], c["al_O"], c["al_N"], c["al_NO"]), (3, 1, 0, 1))
        self.assertEqual(c["normal"], 5)          # A keeps its 4 H across the x boundary
        self.assertEqual((c["tautomer"], c["ureate"], c["uronium"], c["h_on_O"]), (0, 0, 0, 0))
        self.assertEqual((c["orphan_NO"], c["unbonded_H"]), (0, 0))

    def test_transfer_classes(self):
        c = self.counts(1)
        self.assertEqual((c["normal"], c["tautomer"], c["ureate"], c["uronium"]), (2, 1, 1, 1))
        self.assertEqual(c["h_on_O"], 2)
        self.assertEqual((c["free"], c["al_O"], c["al_N"], c["al_NO"]), (3, 1, 0, 1))

    def test_orphan_and_unbonded(self):
        import numpy as np
        atoms = box(0) + [("N", np.array([10.0, 2.0, 10.0])), ("H", np.array([10.0, 10.0, 6.0]))]
        X = np.array([p for _, p in atoms]) % L
        c = self.m.scan_frame([e for e, _ in atoms], X, L)
        self.assertEqual((c["orphan_NO"], c["unbonded_H"]), (1, 1))

    def test_files_summary_and_truncated_frame(self):
        p = self.tmp / "t.xyz"
        write_xyz(p, [box(0), box(1), box(1)], truncate=True)
        out_csv, out_json = self.tmp / "f.csv", self.tmp / "s.json"
        self.m.main([str(p), "--box", str(L), "--blocks", "2", "--csv", str(out_csv),
                     "-o", str(out_json)])
        s = json.loads(out_json.read_text())
        self.assertTrue(s["partial_last_frame"])
        self.assertEqual((s["ureas"], s["frames"], s["frames_with_transfer"]), (5, 2, 1))
        self.assertEqual(s["first_transfer_frame"], 1)
        self.assertEqual((s["max"]["ureate"], s["max"]["uronium"]), (1, 1))
        rows = list(csv.DictReader(out_csv.open()))
        self.assertEqual([r["frame"] for r in rows], ["0", "1"])
        self.assertEqual(rows[1]["tautomer"], "1")

    def test_bad_files(self):
        p = self.tmp / "order.xyz"
        a, b = box(0), box(0)
        b[0], b[1] = b[1], b[0]
        write_xyz(p, [a, b])
        with self.assertRaises(ValueError):
            self.m.main([str(p), "--box", str(L)])
        q = self.tmp / "nourea.xyz"
        q.write_text("2\nc\nAl 0 0 0\nCl 2 0 0\n")
        with self.assertRaises(ValueError):
            self.m.main([str(q), "--box", str(L)])


if __name__ == "__main__":
    unittest.main()
