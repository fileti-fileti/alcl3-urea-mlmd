#!/usr/bin/env python3
"""Register small text result files as verbatim evidence under results/<name>/.

Usage:
  register_result.py <name> <run_dir> '<glob>' ['<glob>' ...] [--update]
  register_result.py --check <name>

Copies each matching file (path kept relative to <run_dir>) byte for byte into
results/<name>/ and writes results/<name>/PROVENANCE.json with source path, sha256,
size and dates. Refuses binary files, files over 1 MiB, extensions listed in
scripts/blocked_extensions.txt and destinations that git ignores. An existing registration is replaced only with --update. --check recomputes
the checksums and reports changed, missing and unlisted files (exit 1 on any).

Legacy results (ADR-0008) use a name starting with "legacy-".
Standard library only; runs on Python >= 3.6.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import machine_config  # noqa: E402  (same directory; works under python -I too)

MAX_BYTES = 1024 * 1024
PROVENANCE = "PROVENANCE.json"
EXT_FILE = "scripts/blocked_extensions.txt"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
DEFAULT_REPO = Path(__file__).resolve().parent.parent


class RegisterError(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def is_text(path):
    with open(str(path), "rb") as f:
        head = f.read(8192)
    if b"\0" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as e:
        # A multi-byte character cut at the 8 KiB boundary is still text.
        return e.start >= len(head) - 3
    return True


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo)] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    return p.returncode, p.stdout.strip()


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def blocked_extensions(repo):
    """Extensions the pre-commit hook blocks (shared list; a missing file is an error)."""
    path = repo / EXT_FILE
    if not path.is_file():
        raise RegisterError("{} missing; refusing to register".format(path))
    exts = set()
    with open(str(path)) as f:
        for line in f:
            exts.update(w.lower() for w in line.split("#", 1)[0].split())
    return exts


def collect(run_dir, patterns):
    files = {}
    for pat in patterns:
        matches = [p for p in sorted(run_dir.glob(pat)) if p.is_file()]
        if not matches:
            raise RegisterError("no file matches {!r} in {}".format(pat, run_dir))
        for p in matches:
            files[p.relative_to(run_dir).as_posix()] = p
    return files


def register(repo, name, run_dir, patterns, update=False):
    if not NAME_RE.match(name):
        raise RegisterError("bad name {!r}: use [a-z0-9][a-z0-9._-]*".format(name))
    run_dir = Path(run_dir).resolve()
    if not run_dir.is_dir():
        raise RegisterError("run_dir not found: {}".format(run_dir))
    dest = repo / "results" / name
    if dest.exists() and not update:
        raise RegisterError("{} exists; use --update to replace it".format(dest))

    files = collect(run_dir, patterns)
    blocked = blocked_extensions(repo)
    problems = []
    for rel, src in files.items():
        size = src.stat().st_size
        ext = src.name.rsplit(".", 1)[1].lower() if "." in src.name else ""
        if ext in blocked:
            problems.append("{}: extension .{} is blocked by the pre-commit hook".format(rel, ext))
        elif size > MAX_BYTES:
            problems.append("{}: {} B > {} B".format(rel, size, MAX_BYTES))
        elif not is_text(src):
            problems.append("{}: binary".format(rel))
        rc, _ = git(repo, "check-ignore", "-q", "--no-index",
                    (Path("results") / name / rel).as_posix())
        if rc == 0:
            problems.append("{}: destination is ignored by git".format(rel))
    if problems:
        raise RegisterError("refused:\n  " + "\n  ".join(problems))

    tmp = repo / "results" / ".{}.tmp".format(name)
    if tmp.exists():
        shutil.rmtree(str(tmp))
    entries = []
    for rel in sorted(files):
        src = files[rel]
        out = tmp / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(src), str(out))
        digest = sha256(src)
        if sha256(out) != digest:
            shutil.rmtree(str(tmp))
            raise RegisterError("{}: copy differs from source (changed while copying?)".format(rel))
        st = src.stat()
        entries.append({
            "path": rel,
            "source": str(src),
            "sha256": digest,
            "bytes": st.st_size,
            "source_mtime": datetime.datetime.fromtimestamp(
                st.st_mtime, datetime.timezone.utc).replace(microsecond=0).isoformat(),
        })
    rc, head = git(repo, "rev-parse", "HEAD")
    try:
        machine = machine_config.detect(repo)
    except machine_config.ConfigError:
        machine = "unknown"
    prov = {
        "name": name,
        "registered_at": now_utc(),
        "machine": machine,
        "hostname": socket.gethostname(),
        "repo_commit": head if rc == 0 else "unknown",
        "source_dir": str(run_dir),
        "patterns": list(patterns),
        "files": entries,
    }
    with open(str(tmp / PROVENANCE), "w") as f:
        json.dump(prov, f, indent=2, sort_keys=False)
        f.write("\n")
    if dest.exists():
        shutil.rmtree(str(dest))
    os.rename(str(tmp), str(dest))
    return dest, entries


def check(repo, name):
    dest = repo / "results" / name
    prov_path = dest / PROVENANCE
    if not prov_path.is_file():
        raise RegisterError("no {} in {}".format(PROVENANCE, dest))
    with open(str(prov_path)) as f:
        prov = json.load(f)
    listed = {e["path"]: e for e in prov["files"]}
    problems = []
    for rel, e in sorted(listed.items()):
        p = dest / rel
        if not p.is_file():
            problems.append("missing: {}".format(rel))
        elif sha256(p) != e["sha256"]:
            problems.append("changed: {}".format(rel))
    present = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()}
    for rel in sorted(present - set(listed) - {PROVENANCE}):
        problems.append("unlisted: {}".format(rel))
    return len(listed), problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", metavar="NAME", help="verify a registration")
    ap.add_argument("--update", action="store_true", help="replace an existing registration")
    ap.add_argument("--repo", default=str(DEFAULT_REPO), help=argparse.SUPPRESS)
    ap.add_argument("args", nargs="*", metavar="name run_dir glob")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    try:
        if a.check:
            if a.args:
                ap.error("--check takes only a name")
            n, problems = check(repo, a.check)
            if problems:
                print("FAIL {}: {}".format(a.check, "; ".join(problems)), file=sys.stderr)
                return 1
            print("OK {}: {} file(s) match PROVENANCE.json".format(a.check, n))
            return 0
        if len(a.args) < 3:
            ap.error("need: name run_dir glob [glob ...]")
        dest, entries = register(repo, a.args[0], a.args[1], a.args[2:], a.update)
        for e in entries:
            print("{}  {:>8} B  {}".format(e["sha256"][:12], e["bytes"], e["path"]))
        print("registered {} file(s) in {}".format(len(entries), dest.relative_to(repo)))
        return 0
    except RegisterError as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
