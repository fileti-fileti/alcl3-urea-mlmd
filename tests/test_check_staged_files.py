"""Pre-commit hook (scripts/check_staged_files.sh) through real `git commit` calls."""
import os
import unittest

from helpers import TempRepo, run


class HookTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        self.repo = self.t.repo
        run(["git", "add", "-A"], self.repo)
        run(["git", "commit", "-qm", "base"], self.repo)

    def tearDown(self):
        self.t.__exit__()

    def write(self, rel, data=b"a,b\n"):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def commit(self, *paths):
        run(["git", "add", "-f"] + list(paths), self.repo)
        return run(["git", "commit", "-qm", "t"], self.repo, check=False)

    def assertBlocked(self, *paths):
        p = self.commit(*paths)
        self.assertNotEqual(p.returncode, 0, "commit of {} was not blocked".format(paths))
        self.assertIn("BLOCKED", p.stderr)

    def test_gitignore_refuses_data_csv(self):
        self.write("data/x.csv")
        p = run(["git", "add", "data/x.csv"], self.repo, check=False)
        self.assertNotEqual(p.returncode, 0)

    def test_hook_blocks_forced_data_csv(self):
        self.write("data/x.csv")
        self.assertBlocked("data/x.csv")

    def test_hook_blocks_runs_and_logs(self):
        self.write("runs/a.txt")
        self.write("logs/b.txt")
        self.assertBlocked("runs/a.txt", "logs/b.txt")

    def test_symlink_data_ignored_and_blocked(self):
        os.symlink(str(self.t.ext), str(self.repo / "data"))
        p = run(["git", "status", "--porcelain", "--ignored"], self.repo)
        self.assertIn("!! data", p.stdout)
        self.assertBlocked("data")

    def test_blocked_extensions(self):
        for ext in ["pt", "npz", "tar", "wfn", "extxyz", "traj", "nc", "db", "sqlite", "PT"]:
            self.write("x/f." + ext, b"")
            self.assertBlocked("x/f." + ext)
            run(["git", "reset", "-q"], self.repo)
            os.remove(str(self.repo / "x" / ("f." + ext)))

    def test_missing_extension_list_blocks_everything(self):
        os.remove(str(self.repo / "scripts" / "blocked_extensions.txt"))
        self.write("x/a.txt")
        self.assertBlocked("x/a.txt")

    def test_large_file_blocked(self):
        self.write("x/big file.txt", b"a" * (1024 * 1024 + 1))
        self.assertBlocked("x/big file.txt")

    def test_small_xyz_and_text_pass(self):
        self.write("x/init.xyz", b"1\n\nH 0 0 0\n")
        self.write("configs/a.yaml", b"k: 1\n")
        p = self.commit("x/init.xyz", "configs/a.yaml")
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_deletion_of_tracked_file_passes(self):
        self.write("x/a.txt")
        self.assertEqual(self.commit("x/a.txt").returncode, 0)
        run(["git", "rm", "-q", "x/a.txt"], self.repo)
        p = run(["git", "commit", "-qm", "rm"], self.repo, check=False)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
