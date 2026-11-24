"""machine_config.py: strict YAML subset, schema (unknown keys rejected), detection."""
import shutil
import unittest

import machine_config as mc
from helpers import ROOT, TempRepo


class ParserTest(unittest.TestCase):
    def test_nested_mapping_lists_comments_quotes(self):
        text = ("a: 1   # c\nb:\n  c: \"x # not a comment\"\n  d:\n    - 'q'\n    - \"n[0-9]\"\n"
                "# full-line comment\ne: /p/a#b\n")
        self.assertEqual(mc.parse_yaml(text), {"a": "1", "b": {"c": "x # not a comment",
                                                               "d": ["q", "n[0-9]"]}, "e": "/p/a#b"})

    def test_rejects_unsupported(self):
        bad = ["a: [1, 2]\n", "a: {b: 1}\n", "a: &x 1\n", "a: |\n  t\n", "a:\n\t- x\n",
               "a: 1\na: 2\n", "a:\n", "a:\n  - b: 1\n", "---\na: 1\n", "a: 1\n  b: 2\n",
               "a: 'open\n", "- x\n- y\nb: 1\n"]
        for text in bad:
            with self.assertRaises(mc.ConfigError, msg=repr(text)):
                mc.parse_yaml(text)


class RepoConfigsTest(unittest.TestCase):
    def test_shipped_configs_validate(self):
        cfgs = mc.load_all(ROOT)
        self.assertEqual(sorted(cfgs), ["neumann", "sdumont"])

    def test_detect(self):
        self.assertEqual(mc.detect(ROOT, "headnode.cluster.neumann.unifesp.br"), "neumann")
        self.assertEqual(mc.detect(ROOT, "n09"), "neumann")
        self.assertEqual(mc.detect(ROOT, "sdumont17"), "sdumont")
        with self.assertRaises(mc.ConfigError):
            mc.detect(ROOT, "some-laptop.local")


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.t = TempRepo().__enter__()
        self.dir = self.t.repo / "configs" / "machines"
        self.dir.mkdir(parents=True)
        shutil.copy(str(ROOT / "configs" / "machines" / "neumann.yaml"), str(self.dir))
        self.text = (self.dir / "neumann.yaml").read_text()

    def tearDown(self):
        self.t.__exit__()

    def write(self, text):
        (self.dir / "neumann.yaml").write_text(text)

    def assertInvalid(self, text, fragment):
        self.write(text)
        with self.assertRaises(mc.ConfigError) as e:
            mc.load("neumann", self.t.repo)
        self.assertIn(fragment, str(e.exception))

    def test_copy_is_valid(self):
        self.assertEqual(mc.load("neumann", self.t.repo)["cost"]["unit"], "core-hours")

    def test_unknown_top_level_key(self):
        self.assertInvalid(self.text + "gpus: 4\n", "gpus: unknown key")

    def test_unknown_nested_key(self):
        self.assertInvalid(self.text.replace("  source: sacct\n", "  source: sacct\n  rate: 1\n"),
                           "cost.rate: unknown key")

    def test_missing_key(self):
        self.assertInvalid(self.text.replace("toy_job_partition: batch\n", ""),
                           "toy_job_partition: missing key")

    def test_wrong_type(self):
        self.assertInvalid(self.text.replace("scheduler: slurm", "scheduler:\n  - slurm"),
                           "scheduler: expected a string")

    def test_value_not_allowed(self):
        self.assertInvalid(self.text.replace("scheduler: slurm", "scheduler: pbs"), "not in")

    def test_name_must_match_file(self):
        self.assertInvalid(self.text.replace("name: neumann", "name: other"), "does not match")

    def test_toy_partition_must_exist(self):
        self.assertInvalid(self.text.replace("toy_job_partition: batch", "toy_job_partition: gpu"),
                           "not in partitions")


if __name__ == "__main__":
    unittest.main()
