#!/usr/bin/env python3
"""Collect the facts /start-session and /end-session check, as Markdown. Read-only.

Usage:
  session_facts.py [--fetch]

Never fails: a section that cannot be computed says "unavailable: <reason>".
--fetch runs `git fetch origin` first (updates remote-tracking refs only, no files).
Reports: machine, git state and divergence from origin, status block and "last sync"
lines, newest journal entry, Slurm queue split into this project / other, ended project
jobs not yet in the ledger, purge rule, registered results whose checksums fail,
TODO(owner) count. Never prints a number it did not read from a command or a file.
Standard library only; runs on Python >= 3.6.
"""
import argparse
import getpass
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cost_ledger  # noqa: E402
import machine_config  # noqa: E402
import register_result  # noqa: E402

DEFAULT_REPO = Path(__file__).resolve().parent.parent
STATUS_RE = re.compile(r"<!-- BEGIN STATUS -->\n(.*?)<!-- END STATUS -->", re.S)
MARKER = "<!-- NEW ENTRIES BELOW -->"


def sh(cmd, cwd):
    try:
        p = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def section(title, body):
    print("## {}\n{}\n".format(title, body.rstrip() or "(none)"))


def machine_facts(repo):
    try:
        name = machine_config.detect(repo)
        return name, machine_config.load(name, repo), None
    except machine_config.ConfigError as e:
        return "unknown", None, str(e)


def git_facts(repo, fetch):
    out = []
    if fetch:
        rc, _, err = sh(["git", "fetch", "-q", "origin"], repo)
        out.append("- fetch origin: " + ("ok" if rc == 0 else "FAILED: " + err))
    rc, branch, _ = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    rc2, head, _ = sh(["git", "log", "-1", "--format=%h %cs %s"], repo)
    out.append("- branch: {}; HEAD: {}".format(branch if rc == 0 else "unknown",
                                                head if rc2 == 0 else "unknown"))
    rc, st, _ = sh(["git", "status", "--porcelain"], repo)
    lines = [l for l in st.splitlines() if l.strip()] if rc == 0 else None
    out.append("- uncommitted changes: {}".format(
        "unknown" if lines is None else ("none" if not lines else "{} path(s)".format(len(lines)))))
    for l in (lines or [])[:15]:
        out.append("    {}".format(l))
    rc, remotes, _ = sh(["git", "remote"], repo)
    remotes = remotes.split() if rc == 0 else []
    out.append("- remotes: {}".format(", ".join(remotes) or "none"))
    for r in remotes:
        rc, ab, _ = sh(["git", "rev-list", "--left-right", "--count",
                        "HEAD...{}/{}".format(r, branch)], repo)
        if rc == 0:
            ahead, behind = ab.split()
            state = "in sync" if ahead == behind == "0" else (
                "DIVERGED" if ahead != "0" and behind != "0" else
                "ahead {} (unpushed)".format(ahead) if ahead != "0" else "behind {}".format(behind))
            out.append("- vs {}/{}: {} (ahead {}, behind {})".format(r, branch, state, ahead, behind))
        else:
            out.append("- vs {}/{}: unavailable (no remote-tracking ref)".format(r, branch))
    return "\n".join(out)


def status_block(repo):
    try:
        text = (repo / "CLAUDE.md").read_text()
    except OSError as e:
        return "unavailable: {}".format(e)
    m = STATUS_RE.search(text)
    return m.group(1) if m else "unavailable: STATUS markers not found in CLAUDE.md"


def newest_journal(repo):
    try:
        text = (repo / "docs" / "journal.md").read_text()
    except OSError as e:
        return "unavailable: {}".format(e)
    if MARKER not in text:
        return "unavailable: marker line not found in docs/journal.md"
    body = text.split(MARKER, 1)[1]
    m = re.search(r"^## .*?(?=^## |\Z)", body, re.S | re.M)
    return m.group(0).strip() if m else "(no entries yet)"


def queue(repo):
    if not shutil.which("squeue"):
        return "unavailable: squeue not found on this machine"
    rc, out, err = sh(["squeue", "-h", "-u", getpass.getuser(), "-o", "%i|%j|%P|%T|%M|%Z"], repo)
    if rc != 0:
        return "unavailable: squeue failed: {}".format(err)
    prefixes = cost_ledger.default_workdirs(repo)
    mine, other = [], 0
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) == 6 and prefixes and cost_ledger.inside(parts[5], prefixes):
            mine.append("- {} {} {} {} elapsed {}".format(*parts[:5]))
        elif line.strip():
            other += 1
    if not prefixes:
        mine.append("(no runs/ in this repo: project jobs cannot be identified)")
    return "\n".join(mine + ["- jobs of this user outside the project: {}".format(other)])


def unledgered(repo, machine, cfg):
    if cfg is None:
        return "unavailable: machine unknown"
    if not shutil.which("sacct"):
        return "unavailable: sacct not found on this machine"
    since = None
    if not cost_ledger.read_ledger(cost_ledger.ledger_path(repo, machine)):
        m = re.search(r"Updated: (\d{4}-\d{2}-\d{2})", status_block(repo))
        if not m:
            return "unavailable: empty ledger and no 'Updated: YYYY-MM-DD' in the status block"
        since = m.group(1)                   # empty ledger: look back to the last status update
    try:
        _, since, new, skipped = cost_ledger.add(repo, machine, cfg["cost"]["unit"],
                                                 since=since, dry_run=True)
    except cost_ledger.LedgerError as e:
        return "unavailable: {}".format(e)
    rows = ["- {} {} {} exit {} end {} cost {} {}".format(
        r["job_id"], r["job_name"], r["state"], r["exit_code"], r["end"], r["cost"], r["cost_unit"])
        for r in new]
    return "\n".join(["- since {}: {} ended project job(s) not in the ledger; {} outside the project"
                      .format(since, len(new), skipped)] + rows)


def results_check(repo):
    out = []
    for prov in sorted((repo / "results").glob("*/PROVENANCE.json")):
        name = prov.parent.name
        try:
            n, problems = register_result.check(repo, name)
        except Exception as e:  # report, never crash
            problems, n = ["unreadable: {}".format(e)], 0
        out.append("- {}: {}".format(name, "OK ({} files)".format(n) if not problems
                                     else "FAIL " + "; ".join(problems)))
    return "\n".join(out) or "(no registered results)"


def todo_count(repo):
    n = 0
    for p in [repo / "CLAUDE.md"] + sorted((repo / "docs").rglob("*.md")):
        try:
            n += p.read_text().count("TODO(owner)")
        except OSError:
            pass
    return "- TODO(owner) occurrences in CLAUDE.md + docs/: {}".format(n)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=str(DEFAULT_REPO), help=argparse.SUPPRESS)
    ap.add_argument("--fetch", action="store_true", help="git fetch origin first")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    machine, cfg, err = machine_facts(repo)
    section("Machine", "- {} (hostname {}){}".format(
        machine, socket.gethostname(), "; " + err if err else ""))
    section("Git", git_facts(repo, a.fetch))
    section("Status block (CLAUDE.md)", status_block(repo))
    section("Newest journal entry", newest_journal(repo))
    section("Slurm queue", queue(repo))
    section("Ended jobs not in the ledger", unledgered(repo, machine, cfg))
    section("Storage purge", "- {}".format(cfg["storage"]["purge"]) if cfg else "unavailable")
    section("Registered results (checksums)", results_check(repo))
    section("Waiting on owner", todo_count(repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
