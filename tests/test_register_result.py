"""register_result.py: register, refuse, --update, --check (guide step 4 check)."""
import json
import os
import unittest

import register_result as rr
from helpers import TempRepo


class RegisterTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        self.repo, self.run_dir = self.t.repo, self.t.ext
        (self.run_dir / "out").mkdir()
        (self.run_dir / "out" / "energy.csv").write_text("step,E\n0,-1.5\n")
        (self.run_dir / "summary.txt").write_text("ok\n")

    def tearDown(self):
        self.t.__exit__()

    def cli(self, *args):
        return rr.main(["--repo", str(self.repo)] + list(args))

    def test_toy_run_register_then_check_passes(self):
        self.assertEqual(self.cli("toy", str(self.run_dir), "out/*.csv", "*.txt"), 0)
        dest = self.repo / "results" / "toy"
        self.assertEqual((dest / "out" / "energy.csv").read_text(), "step,E\n0,-1.5\n")
        prov = json.loads((dest / "PROVENANCE.json").read_text())
        self.assertEqual(sorted(e["path"] for e in prov["files"]), ["out/energy.csv", "summary.txt"])
        self.assertEqual(prov["files"][0]["sha256"], rr.sha256(self.run_dir / "out" / "energy.csv"))
        self.assertEqual(self.cli("--check", "toy"), 0)

    def test_check_fails_after_editing_copy(self):
        self.cli("toy", str(self.run_dir), "out/*.csv")
        with open(str(self.repo / "results" / "toy" / "out" / "energy.csv"), "a") as f:
            f.write("1,-1.6\n")
        self.assertEqual(self.cli("--check", "toy"), 1)

    def test_check_fails_on_missing_and_unlisted(self):
        self.cli("toy", str(self.run_dir), "out/*.csv", "*.txt")
        dest = self.repo / "results" / "toy"
        os.remove(str(dest / "summary.txt"))
        (dest / "extra.txt").write_text("x\n")
        n, problems = rr.check(self.repo, "toy")
        self.assertIn("missing: summary.txt", problems)
        self.assertIn("unlisted: extra.txt", problems)

    def test_existing_needs_update(self):
        self.cli("toy", str(self.run_dir), "*.txt")
        self.assertEqual(self.cli("toy", str(self.run_dir), "*.txt"), 1)
        (self.run_dir / "summary.txt").write_text("changed\n")
        self.assertEqual(self.cli("--update", "toy", str(self.run_dir), "*.txt"), 0)
        self.assertEqual((self.repo / "results" / "toy" / "summary.txt").read_text(), "changed\n")
        self.assertEqual(self.cli("--check", "toy"), 0)

    def test_refuses_binary(self):
        (self.run_dir / "w.bin").write_bytes(b"\x00\x01\x02")
        with self.assertRaises(rr.RegisterError):
            rr.register(self.repo, "toy", self.run_dir, ["w.bin"])
        self.assertFalse((self.repo / "results" / "toy").exists())

    def test_refuses_blocked_extension_even_if_small_text(self):
        (self.run_dir / "set.extxyz").write_text("1\n\nH 0 0 0\n")
        with self.assertRaises(rr.RegisterError) as e:
            rr.register(self.repo, "toy", self.run_dir, ["set.extxyz"])
        self.assertIn(".extxyz", str(e.exception))

    def test_refuses_without_extension_list(self):
        os.remove(str(self.repo / "scripts" / "blocked_extensions.txt"))
        with self.assertRaises(rr.RegisterError):
            rr.register(self.repo, "toy", self.run_dir, ["*.txt"])

    def test_refuses_large(self):
        (self.run_dir / "big.txt").write_text("a" * (rr.MAX_BYTES + 1))
        with self.assertRaises(rr.RegisterError):
            rr.register(self.repo, "toy", self.run_dir, ["big.txt"])

    def test_refuses_ignored_destination(self):
        (self.run_dir / "__pycache__").mkdir()
        (self.run_dir / "__pycache__" / "x.txt").write_text("x\n")
        with self.assertRaises(rr.RegisterError):
            rr.register(self.repo, "toy", self.run_dir, ["__pycache__/x.txt"])

    def test_refuses_no_match_and_bad_name(self):
        with self.assertRaises(rr.RegisterError):
            rr.register(self.repo, "toy", self.run_dir, ["*.nothing"])
        with self.assertRaises(rr.RegisterError):
            rr.register(self.repo, "Bad Name", self.run_dir, ["*.txt"])

    def test_legacy_name_and_utf8_text(self):
        (self.run_dir / "notes.txt").write_text("Δ energia ✓\n", encoding="utf-8")
        self.assertEqual(self.cli("legacy-old-2025", str(self.run_dir), "notes.txt"), 0)
        self.assertEqual(self.cli("--check", "legacy-old-2025"), 0)


if __name__ == "__main__":
    unittest.main()
