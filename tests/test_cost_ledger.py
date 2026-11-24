"""cost_ledger.py: parse sacct, attribute by WorkDir (ADR-0010), ended jobs only, dedupe,
units, sum across machines."""
import os
import unittest

import cost_ledger as cl
from helpers import TempRepo

# Synthetic `sacct -X -n -P` output in FIELDS order; job IDs and paths are made up.
# {RUNS} is replaced by the resolved runs/ store of the temp repo.
SACCT = """\
101|toy|batch|COMPLETED|0:0|2026-01-01T10:00:00|2026-01-01T10:01:00|60|1|n09|{RUNS}/toy
102|fail|batch|FAILED|1:0|2026-01-01T11:00:00|2026-01-01T13:00:00|7200|128|n10|{RUNS}/a/b
103|cancel|batch|CANCELLED by 1004|0:0|2026-01-01T12:00:00|2026-01-01T12:30:00|1800|64|n11|{RUNS}
104|run|EPYC_9734|RUNNING|0:0|2026-01-01T12:00:00|Unknown|999|448|n12|{RUNS}/run
105|wait|batch|PENDING|0:0|Unknown|Unknown|0|0|None assigned|{RUNS}/wait
106|tout|batch|TIMEOUT|0:0|2026-01-02T00:00:00|2026-01-03T00:00:00|86400|96|n11|{RUNS}/t
201|other|batch|COMPLETED|0:0|2026-01-01T10:00:00|2026-01-01T11:00:00|3600|128|n09|/home/u/other-project/run
202|prefix|batch|COMPLETED|0:0|2026-01-01T10:00:00|2026-01-01T11:00:00|3600|128|n09|{RUNS}-other/x
"""


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        self.repo = self.t.repo
        store = self.t.ext / "store" / "runs"
        store.mkdir(parents=True)
        os.symlink(str(store), str(self.repo / "runs"))     # runs/ -> large storage
        self.sacct = SACCT.replace("{RUNS}", os.path.realpath(str(store)))

    def tearDown(self):
        self.t.__exit__()

    def add(self, machine="neumann", unit="core-hours", text=None, since="2026-01-01", **kw):
        return cl.add(self.repo, machine, unit, since, text or self.sacct, **kw)

    def test_adds_only_ended_project_jobs_with_core_hours(self):
        path, _, new, skipped = self.add()
        self.assertEqual([r["job_id"] for r in new], ["101", "102", "103", "106"])
        self.assertEqual(skipped, 2)                       # 201 other project, 202 prefix trap
        cost = {r["job_id"]: r["cost"] for r in cl.read_ledger(path)}
        self.assertEqual(cost["101"], "0.0167")     # 60 s x 1 CPU
        self.assertEqual(cost["102"], "256.0000")   # 2 h x 128 CPUs (failed counts)
        self.assertEqual(cost["106"], "2304.0000")  # 24 h x 96 CPUs

    def test_workdir_through_symlink_path_counts(self):
        text = self.sacct.replace(os.path.realpath(str(self.t.ext / "store" / "runs")),
                                  str(self.repo / "runs"))
        _, _, new, _ = self.add(text=text)
        self.assertEqual(len(new), 4)

    def test_no_runs_and_no_workdir_is_an_error(self):
        os.remove(str(self.repo / "runs"))
        with self.assertRaises(cl.LedgerError):
            self.add()

    def test_explicit_workdir(self):
        os.remove(str(self.repo / "runs"))
        _, _, new, _ = self.add(workdirs=["/home/u/other-project"])
        self.assertEqual([r["job_id"] for r in new], ["201"])

    def test_explicit_jobs_ignore_workdir(self):
        _, _, new, _ = self.add(jobs=["201", "104"], since=None)
        self.assertEqual([r["job_id"] for r in new], ["201"])   # 104 still running

    def test_bad_job_id(self):
        with self.assertRaises(cl.LedgerError):
            self.add(jobs=["12;rm"], since=None)

    def test_dedupe_on_second_add(self):
        self.add()
        _, _, new, _ = self.add()
        self.assertEqual(new, [])
        self.assertEqual(len(cl.read_ledger(cl.ledger_path(self.repo, "neumann"))), 4)

    def test_running_job_added_after_it_ends(self):
        self.add()
        ended = self.sacct.replace("104|run|EPYC_9734|RUNNING|0:0|2026-01-01T12:00:00|Unknown|999",
                                   "104|run|EPYC_9734|COMPLETED|0:0|2026-01-01T12:00:00|2026-01-01T13:00:00|3600")
        _, since, new, _ = self.add(text=ended, since=None)
        self.assertEqual(since, "2026-01-03")           # latest recorded end
        self.assertEqual([r["job_id"] for r in new], ["104"])
        self.assertEqual(new[0]["cost"], "448.0000")

    def test_empty_ledger_requires_since(self):
        with self.assertRaises(cl.LedgerError):
            self.add(since=None)

    def test_unknown_unit_gives_unknown_cost(self):
        _, _, new, _ = self.add(machine="sdumont", unit="TODO-unit")
        self.assertTrue(all(r["cost"] == "unknown" for r in new))

    def test_dry_run_writes_nothing(self):
        path, _, new, _ = self.add(dry_run=True)
        self.assertEqual(len(new), 4)
        self.assertFalse(path.exists())

    def test_bad_sacct_line(self):
        with self.assertRaises(cl.LedgerError):
            self.add(text="101|toy|batch\n")

    def test_sum_per_unit_across_machines(self):
        self.add()
        line = "900|m|sequana_cpu_dev|COMPLETED|0:0|2026-01-01T10:00:00|2026-01-01T11:00:00|3600|48|x|{}/m\n"
        self.add(machine="sdumont", unit="TODO-unit",
                 text=line.format(os.path.realpath(str(self.repo / "runs"))))
        picked, totals = cl.sum_jobs(self.repo, ["101", "102", "sdumont:900"])
        self.assertEqual(len(picked), 3)
        self.assertAlmostEqual(totals["core-hours"]["cost"], 256.0167, places=4)
        self.assertEqual(totals["TODO-unit"]["unknown"], 1)

    def test_sum_missing_and_ambiguous(self):
        self.add()
        self.add(machine="sdumont")                     # same IDs on both
        with self.assertRaises(cl.LedgerError) as e:
            cl.sum_jobs(self.repo, ["101", "999"])
        self.assertIn("999", str(e.exception))
        self.assertIn("ambiguous", str(e.exception))
        picked, _ = cl.sum_jobs(self.repo, ["neumann:101"])
        self.assertEqual(picked[0]["machine"], "neumann")

    def test_ledger_merge_has_no_conflict(self):
        # ADR-0009: each machine appends only to its own file.
        self.add(machine="neumann")
        self.add(machine="sdumont")
        files = sorted(p.name for p in (self.repo / "results").glob("cost_ledger_*.csv"))
        self.assertEqual(files, ["cost_ledger_neumann.csv", "cost_ledger_sdumont.csv"])


if __name__ == "__main__":
    unittest.main()
