"""session_facts.py: never fails; reads status block, journal and git state."""
import io
import contextlib
import unittest

import session_facts as sf
from helpers import TempRepo, run, ROOT
import shutil


class FactsTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        self.repo = self.t.repo
        shutil.copy(str(ROOT / "CLAUDE.md"), str(self.repo))
        (self.repo / "docs").mkdir()
        # Own fixture: a project's real journal has entries, the test needs an empty one.
        (self.repo / "docs" / "journal.md").write_text("# Journal\n\n<!-- NEW ENTRIES BELOW -->\n")
        shutil.copytree(str(ROOT / "configs"), str(self.repo / "configs"))
        run(["git", "add", "-A"], self.repo)
        run(["git", "commit", "-qm", "base"], self.repo)

    def tearDown(self):
        self.t.__exit__()

    def facts(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = sf.main(["--repo", str(self.repo)] + list(args))
        return rc, buf.getvalue()

    def test_runs_and_has_all_sections(self):
        rc, out = self.facts()
        self.assertEqual(rc, 0)
        for h in ["Machine", "Git", "Status block", "Newest journal entry", "Slurm queue",
                  "Ended jobs not in the ledger", "Storage purge", "Registered results",
                  "Waiting on owner"]:
            self.assertIn("## " + h, out)
        self.assertIn("Last sync", out)
        self.assertIn("(no entries yet)", out)

    def test_newest_journal_entry(self):
        j = self.repo / "docs" / "journal.md"
        j.write_text(j.read_text() + "\n## 2026-01-02 — neumann — B\n- x\n\n## 2026-01-01 — neumann — A\n")
        self.assertTrue(sf.newest_journal(self.repo).startswith("## 2026-01-02 — neumann — B"))

    def test_missing_files_do_not_crash(self):
        (self.repo / "CLAUDE.md").unlink()
        (self.repo / "docs" / "journal.md").unlink()
        rc, out = self.facts()
        self.assertEqual(rc, 0)
        self.assertIn("unavailable", out)

    def test_empty_ledger_uses_status_date(self):
        import os
        os.symlink(str(self.t.ext), str(self.repo / "runs"))
        cfg = {"cost": {"unit": "core-hours"}}
        out = sf.unledgered(self.repo, "neumann", cfg)
        if "sacct not found" not in out:
            self.assertIn("since 2026-", out)

    def test_dirty_tree_reported(self):
        (self.repo / "new.txt").write_text("x\n")
        self.assertIn("1 path(s)", sf.git_facts(self.repo, fetch=False))


if __name__ == "__main__":
    unittest.main()
