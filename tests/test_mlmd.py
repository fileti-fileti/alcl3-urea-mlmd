"""Tests of src/mlmd.py with a small Lennard-Jones argon box (no GPU, no MACE).

Need numpy and ase: run with the MLMD venv, e.g.
  module load python/3.10.16_sequana; unset PYTHONPATH
  <venv>/bin/python -I -m unittest discover -s tests
Skipped under a python without them.
"""
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE = all(importlib.util.find_spec(m) for m in ("numpy", "ase"))
BOXES = Path("/scratch/acmes/eudes.fileti3/projects/alcl3-urea-mlmd-store/data/boxes/mlmd-boxes-r1.0-v2")


def pdb_line(i, el, x, y, z):
    return "{:<6}{:5d} {:<4} {:3} A{:4d}    {:8.3f}{:8.3f}{:8.3f}{:6.2f}{:6.2f}          {:>2}\n".format(
        "HETATM", i, el, "URE", 1, x, y, z, 1.0, 0.0, el)


class FakeClock:
    def __init__(self, step=1000.0):
        self.t, self.dt = 0.0, step

    def __call__(self):
        self.t += self.dt
        return self.t


@unittest.skipUnless(HAVE, "needs numpy and ase (MLMD venv)")
class TestMLMD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "src"))
        import mlmd
        cls.m = mlmd

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp))

    def lj(self):
        from ase.calculators.lj import LennardJones
        return LennardJones(sigma=3.4, epsilon=0.0104, rc=8.0, smooth=True)

    def structure(self):
        import numpy as np
        from ase.build import bulk
        from ase.io import write
        a = bulk("Ar", "fcc", a=5.4, cubic=True).repeat(2)
        a.positions += np.random.default_rng(0).normal(0, 0.05, a.positions.shape)
        p = self.tmp / "init.xyz"
        write(str(p), a, format="xyz")
        return p, float(a.cell.lengths()[0])

    def config(self, stages=None, **kw):
        p, L = self.structure()
        cfg = {"name": "t", "dtype": "float64", "structure": {"path": str(p), "box_A": L},
               "seed": 7, "min_distance_A": 0.6, "check_every": 10, "ckpt_every": 20,
               "stages": stages or [
                   {"name": "min", "kind": "minimise", "fmax_eV_A": 0.05, "max_steps": 50},
                   {"name": "ramp", "kind": "nvt", "dt_fs": 2.0, "ps": 0.1, "T_start_K": 20,
                    "T_K": 60, "taut_fs": 50, "thermo_every": 10, "dump_every": 0},
                   {"name": "npt", "kind": "npt_berendsen", "dt_fs": 2.0, "ps": 0.12, "T_K": 60,
                    "taut_fs": 100, "P_bar": 1.0, "taup_fs": 500,
                    "compressibility_per_bar": 4.5e-5, "mean_volume_last_ps": 0.06,
                    "thermo_every": 10, "dump_every": 0},
                   {"name": "prod", "kind": "nvt", "dt_fs": 2.0, "ps": 0.2, "T_K": 60,
                    "taut_fs": 100, "thermo_every": 10, "dump_every": 10}]}
        cfg.update(kw)
        return cfg

    def rundir(self, name, cfg):
        d = self.tmp / name
        d.mkdir()
        (d / "run.json").write_text(json.dumps(cfg))
        return d

    def run_(self, d, **kw):
        return self.m.run(d, calc_factory=self.lj, out=io.StringIO(), **kw)

    def frames(self, path):
        steps, lines = [], path.read_text().splitlines()
        i = 0
        while i < len(lines):
            n = int(lines[i])
            steps.append(int(lines[i + 1].split(",")[0].split("=")[1]))
            i += n + 2
        return steps

    def test_pdb_reader_elements_cell_wrap(self):
        p = self.tmp / "b.pdb"
        p.write_text("CRYST1   10.000   10.000   10.000  90.00  90.00  90.00 P 1           1\n"
                     + pdb_line(1, "AL", -0.5, 5.0, 9.9) + pdb_line(2, "CL", 10.2, 1.0, 1.0)
                     + pdb_line(3, "H", 1.0, 1.0, 1.0) + "END\n")
        a = self.m.read_pdb(p, 9.999)
        self.assertEqual(a.get_chemical_symbols(), ["Al", "Cl", "H"])
        self.assertAlmostEqual(a.cell.lengths()[0], 9.999)
        self.assertTrue(a.pbc.all())
        self.assertTrue(((a.positions >= 0) & (a.positions < 9.999)).all())
        self.assertAlmostEqual(a.positions[0, 0], 9.499, places=6)

    @unittest.skipUnless(BOXES.is_dir(), "start boxes not present")
    def test_real_boxes(self):
        from collections import Counter
        for f in ("r1.0_reagentes.pdb", "r1.0_ionico.pdb"):
            a = self.m.read_pdb(BOXES / f, 29.729979)
            self.assertEqual(Counter(a.get_chemical_symbols()),
                             {"H": 504, "Cl": 378, "N": 252, "Al": 126, "C": 126, "O": 126})
            self.assertEqual(len(a), 1512)

    def test_full_run_then_done(self):
        d = self.rundir("a", self.config())
        self.assertEqual(self.run_(d), 0)
        for n in ("min", "ramp", "npt", "prod"):
            self.assertTrue((d / "{}.done".format(n)).exists())
        self.assertEqual(self.frames(d / "prod.xyz"), list(range(0, 101, 10)))
        rows = (d / "prod.thermo.csv").read_text().splitlines()
        self.assertEqual(rows[0].split(","), self.m.THERMO_COLS)
        self.assertEqual([int(r.split(",")[0]) for r in rows[1:]], list(range(0, 101, 10)))
        self.assertEqual(self.run_(d), 0)           # already done: no-op

    def test_restart_every_chunk_equals_uninterrupted(self):
        import numpy as np
        from ase.io import read
        a = self.rundir("a", self.config())
        b = self.rundir("b", json.loads((a / "run.json").read_text()))
        self.assertEqual(self.run_(a), 0)
        codes = []
        for _ in range(100):
            codes.append(self.run_(b, budget_s=1.0, clock=FakeClock()))
            if codes[-1] != 3:
                break
        self.assertEqual(codes[-1], 0)
        self.assertGreater(codes.count(3), 10)
        fa, fb = read(str(a / "prod.final.traj")), read(str(b / "prod.final.traj"))
        self.assertTrue(np.allclose(fa.positions, fb.positions, atol=1e-8))
        self.assertTrue(np.allclose(fa.get_momenta(), fb.get_momenta(), atol=1e-8))
        self.assertTrue(np.allclose(fa.cell, fb.cell))
        self.assertEqual(self.frames(b / "prod.xyz"), list(range(0, 101, 10)))
        steps = [int(r.split(",")[0]) for r in (b / "npt.thermo.csv").read_text().splitlines()[1:]]
        self.assertEqual(steps, list(range(0, 61, 10)))

    def test_extend_after_done_equals_planned(self):
        # Extension (docs/experiments/pilot-r10-T400.md): a stage added after DONE continues
        # from the last final.traj with its velocities and RNG state, as if planned.
        import numpy as np
        from ase.io import read
        cfg = self.config()
        prod2 = dict(cfg["stages"][-1], name="prod2")
        planned = self.rundir("a", dict(cfg, stages=cfg["stages"] + [prod2]))
        ext = self.rundir("b", cfg)
        self.assertEqual(self.run_(planned), 0)
        self.assertEqual(self.run_(ext), 0)
        c = json.loads((ext / "run.json").read_text())
        c["stages"].append(prod2)
        (ext / "run.json").write_text(json.dumps(c))
        (ext / "DONE").unlink()
        self.assertEqual(self.run_(ext), 0)
        fa, fb = read(str(planned / "prod2.final.traj")), read(str(ext / "prod2.final.traj"))
        self.assertTrue(np.allclose(fa.positions, fb.positions, atol=1e-8))
        self.assertTrue(np.allclose(fa.get_momenta(), fb.get_momenta(), atol=1e-8))
        self.assertEqual(self.frames(ext / "prod2.xyz"), list(range(0, 101, 10)))
        p_last = read(str(ext / "prod.xyz"), index=-1).positions
        p_first = read(str(ext / "prod2.xyz"), index=0).positions
        self.assertTrue(np.allclose(p_last, p_first, atol=1e-7))   # junction frame repeated

    OU = {"name": "ou", "kind": "massive_ou", "dt_fs": 2.0, "ps": 2.0, "T_K": 60, "taut_fs": 50,
          "thermo_every": 10, "dump_every": 0}
    NVE = {"name": "nve", "kind": "nve", "dt_fs": 2.0, "ps": 0.4, "thermo_every": 10, "dump_every": 0}

    def thermo(self, path):
        import numpy as np
        return np.genfromtxt(str(path), delimiter=",", names=True)

    def test_massive_ou_temperature_and_bookkeeping(self):
        import numpy as np
        d = self.rundir("a", self.config(stages=[self.OU]))
        self.assertEqual(self.run_(d), 0)
        t = self.thermo(d / "ou.thermo.csv")
        self.assertLess(abs(t["T_K"][20:].mean() - 60.0), 6.0)
        self.assertTrue(np.isfinite(t["conserved_eV"]).all())
        self.assertLess(np.ptp(t["conserved_eV"]), 0.05 * t["ekin_eV"].mean())

    def test_nve_conserves_energy_and_needs_velocities(self):
        import numpy as np
        d = self.rundir("a", self.config(stages=[dict(self.OU, ps=0.2), self.NVE]))
        self.assertEqual(self.run_(d), 0)
        t = self.thermo(d / "nve.thermo.csv")
        self.assertLess(np.ptp(t["etot_eV"]), 0.01 * t["ekin_eV"].mean())
        self.assertTrue(np.allclose(t["conserved_eV"], t["etot_eV"]))
        with self.assertRaises(self.m.ConfigError):
            self.run_(self.rundir("b", self.config(stages=[self.NVE])))

    def test_restart_new_kinds_equals_uninterrupted(self):
        import numpy as np
        from ase.io import read
        cfg = self.config(stages=[dict(self.OU, ps=0.2, dump_every=10), dict(self.NVE, ps=0.2, dump_every=10)])
        a, b = self.rundir("a", cfg), self.rundir("b", cfg)
        self.assertEqual(self.run_(a), 0)
        codes = []
        for _ in range(100):
            codes.append(self.run_(b, budget_s=1.0, clock=FakeClock()))
            if codes[-1] != 3:
                break
        self.assertEqual(codes[-1], 0)
        self.assertGreater(codes.count(3), 5)
        fa, fb = read(str(a / "nve.final.traj")), read(str(b / "nve.final.traj"))
        self.assertTrue(np.allclose(fa.positions, fb.positions, atol=1e-8))
        self.assertTrue(np.allclose(fa.get_momenta(), fb.get_momenta(), atol=1e-8))
        ca, cb = self.thermo(a / "ou.thermo.csv"), self.thermo(b / "ou.thermo.csv")
        self.assertTrue(np.allclose(ca["conserved_eV"], cb["conserved_eV"], atol=1e-8))

    def test_npt_box_scaled_to_mean_volume(self):
        from ase.io import read
        d = self.rundir("a", self.config())
        self.assertEqual(self.run_(d), 0)
        rows = [r.split(",") for r in (d / "npt.thermo.csv").read_text().splitlines()[1:]]
        it, iv = self.m.THERMO_COLS.index("time_ps"), self.m.THERMO_COLS.index("volume_A3")
        vols = [float(r[iv]) for r in rows if float(r[it]) >= 0.12 - 0.06 - 1e-9]
        self.assertEqual(len(vols), 4)
        v = read(str(d / "npt.final.traj")).get_volume()
        self.assertAlmostEqual(v / (sum(vols) / len(vols)), 1.0, places=9)
        self.assertAlmostEqual(json.loads((d / "npt.volume.json").read_text())["mean_volume_A3"], v, places=6)

    def test_ramp_target_temperature(self):
        d = self.rundir("a", self.config())
        self.assertEqual(self.run_(d), 0)
        rows = [r.split(",") for r in (d / "ramp.thermo.csv").read_text().splitlines()[1:]]
        tt = [float(r[self.m.THERMO_COLS.index("T_target_K")]) for r in rows]
        self.assertAlmostEqual(tt[0], 20.0)
        self.assertAlmostEqual(tt[-1], 60.0)

    def test_stop_on_close_atoms(self):
        from ase import Atoms
        from ase.io import write
        p = self.tmp / "close.xyz"
        write(str(p), Atoms("Ar2", positions=[[1, 1, 1], [1.5, 1, 1]]), format="xyz")
        cfg = self.config(stages=[{"name": "md", "kind": "nvt", "dt_fs": 1.0, "ps": 0.02,
                                   "T_K": 50, "taut_fs": 50, "thermo_every": 10, "dump_every": 0}])
        cfg["structure"] = {"path": str(p), "box_A": 12.0}
        d = self.rundir("c", cfg)
        self.assertEqual(self.run_(d), 4)
        self.assertIn("0.500", (d / "STOPPED").read_text())
        self.assertEqual(self.run_(d), 4)

    def test_config_errors(self):
        bad = self.config()
        bad["stages"][1]["thermo_every"] = 15
        with self.assertRaises(self.m.ConfigError):
            self.m.run(self.rundir("x1", bad), calc_factory=self.lj, out=io.StringIO())
        bad = self.config()
        bad["stages"][3]["kind"] = "nve"
        with self.assertRaises(self.m.ConfigError):
            self.m.run(self.rundir("x2", bad), calc_factory=self.lj, out=io.StringIO())
        bad = self.config()
        bad["stages"][2]["extra"] = 1
        with self.assertRaises(self.m.ConfigError):
            self.m.run(self.rundir("x3", bad), calc_factory=self.lj, out=io.StringIO())

    def test_model_sha_checked_before_import(self):
        f = self.tmp / "fake.model"
        f.write_bytes(b"not a model")
        cfg = self.config(model={"path": str(f), "sha256": "0" * 64})
        with self.assertRaises(self.m.ConfigError):
            self.m.make_calculator(cfg, "cpu")


if __name__ == "__main__":
    unittest.main()
