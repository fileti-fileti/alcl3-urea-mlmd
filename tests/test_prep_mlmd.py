"""Tests of scripts/prep_mlmd.py: run dir, provenance, refusals and the job's chain logic."""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import unittest
from pathlib import Path

from helpers import ROOT, TempRepo, run

import prep_mlmd as pm  # noqa: E402  (scripts/ is on sys.path via helpers)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def stub(path, body):
    path.write_text("#!/bin/bash\n" + body + "\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class TestPrepMLMD(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        self.addCleanup(self.t.__exit__, None, None, None)
        r = self.t.repo
        shutil.copytree(str(ROOT / "configs" / "machines"), str(r / "configs" / "machines"))
        (r / "inputs").mkdir()
        (r / "inputs" / "m.model").write_bytes(b"model-bytes")
        (r / "inputs" / "box.pdb").write_text("HETATM\n")
        self.cfg = {"model": {"path": "inputs/m.model", "sha256": sha(b"model-bytes")},
                    "dtype": "float64", "structure": {"path": "inputs/box.pdb", "box_A": 29.729979},
                    "seed": 1, "min_distance_A": 0.6, "check_every": 100, "ckpt_every": 2000,
                    "stages": []}
        (r / "configs" / "c.json").write_text(json.dumps(self.cfg))
        (r / "runs").mkdir()
        (r / ".gitkeep_runs").write_text("")
        run(["git", "add", "-A"], r)
        run(["git", "commit", "-q", "-m", "init", "--no-verify"], r)

    def prep(self, **kw):
        args = dict(machine="sdumont")
        args.update(kw)
        return pm.prepare(self.t.repo, self.t.repo / "configs" / "c.json", args.pop("name", "r1"), **args)

    def test_run_dir_and_provenance(self):
        d = self.prep()
        cfg = json.loads((d / "run.json").read_text())
        head = run(["git", "rev-parse", "HEAD"], self.t.repo).stdout.strip()
        self.assertEqual(cfg["provenance"]["commit"], head)
        self.assertEqual(cfg["model"]["path"], str(self.t.repo / "inputs" / "m.model"))
        self.assertTrue(Path(cfg["structure"]["path"]).is_absolute())
        job = (d / "job.sbatch").read_text()
        self.assertNotIn("--exclude", job)                  # prepare() default: none
        for s in ("#SBATCH -p sequana_gpu", "#SBATCH -t 1-00:00:00",
                  "module load python/3.10.16_sequana", "--budget-s 85800", "mace0316_env/bin/python",
                  "#SBATCH --gres=gpu:1", "#SBATCH -c 6"):
            self.assertIn(s, job)
        self.assertEqual(run(["bash", "-n", str(d / "job.sbatch")], d).returncode, 0)

    def test_refusals(self):
        self.prep()
        with self.assertRaises(pm.PrepError):
            self.prep()                                     # exists
        with self.assertRaises(pm.PrepError):
            self.prep(name="r2", partition="nope")
        with self.assertRaises(pm.PrepError):
            self.prep(name="r3", time="00:05:00")           # shorter than margin
        with self.assertRaises(pm.PrepError):
            self.prep(name="r4", env="/not/listed")
        (self.t.repo / "dirty.txt").write_text("x")
        with self.assertRaises(pm.PrepError):
            self.prep(name="r5")

    def test_run_name(self):
        self.assertTrue(self.prep(name="pilot-r10-T400-reag").is_dir())   # CLAUDE.md convention
        for bad in ("../x", "a/b", "-x", "a b"):
            with self.assertRaises(pm.PrepError):
                self.prep(name=bad)

    def test_wrong_model_sha(self):
        cfg = dict(self.cfg, model={"path": "inputs/m.model", "sha256": "0" * 64})
        (self.t.repo / "configs" / "c.json").write_text(json.dumps(cfg))
        run(["git", "commit", "-q", "-am", "bad sha", "--no-verify"], self.t.repo)
        with self.assertRaises(pm.PrepError):
            self.prep()

    def chain(self, rc, chain):
        d = self.prep(name="c{}{}".format(rc, chain), max_chain=30, exclude="sdumont8042")
        self.assertIn("#SBATCH --exclude=sdumont8042", (d / "job.sbatch").read_text())
        fake = self.t.ext / "bin{}{}".format(rc, chain)
        fake.mkdir()
        log = fake / "sbatch.log"
        stub(fake / "module", "exit 0")
        stub(fake / "nvidia-smi", "echo fake-gpu")
        stub(fake / "sbatch", 'echo "$@" >> {}'.format(log))
        stub(fake / "python", "exit {}".format(rc))
        job = (d / "job.sbatch").read_text()
        py = [w for w in job.split() if w.endswith("/bin/python")][0]
        (d / "job.sbatch").write_text(job.replace(py, str(fake / "python")))
        env = dict(os.environ, PATH="{}:{}".format(fake, os.environ["PATH"]), CHAIN=str(chain))
        p = subprocess.run(["bash", str(d / "job.sbatch")], cwd=str(d), env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return p.returncode, (log.read_text() if log.exists() else ""), d

    def test_chain_resubmits_on_budget(self):
        code, calls, d = self.chain(3, 0)
        self.assertEqual(code, 0)
        self.assertEqual(calls.strip(), "--export=CHAIN=1 {}/job.sbatch".format(d))

    def test_chain_stops_when_done_stopped_or_at_max(self):
        self.assertEqual(self.chain(0, 0)[:2], (0, ""))
        self.assertEqual(self.chain(4, 0)[:2], (4, ""))
        self.assertEqual(self.chain(3, 29)[:2], (1, ""))


if __name__ == "__main__":
    unittest.main()
