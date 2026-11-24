"""Shared test helpers: a throwaway git repo with this repo's .gitignore and scripts."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def run(cmd, cwd, check=True):
    p = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    if check and p.returncode != 0:
        raise AssertionError("{} -> {}\n{}{}".format(cmd, p.returncode, p.stdout, p.stderr))
    return p


class TempRepo(object):
    """Context manager: temp dir with `repo/` (git, .gitignore, scripts, hooks) and `ext/`."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.repo = base / "repo"
        self.ext = base / "ext"
        self.ext.mkdir()
        self.repo.mkdir()
        run(["git", "init", "-q"], self.repo)
        run(["git", "config", "user.name", "test"], self.repo)
        run(["git", "config", "user.email", "test@example.invalid"], self.repo)
        run(["git", "config", "core.hooksPath", ".githooks"], self.repo)
        shutil.copy(str(ROOT / ".gitignore"), str(self.repo / ".gitignore"))
        shutil.copytree(str(ROOT / "scripts"), str(self.repo / "scripts"))
        shutil.copytree(str(ROOT / ".githooks"), str(self.repo / ".githooks"))
        (self.repo / "results").mkdir()
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()
