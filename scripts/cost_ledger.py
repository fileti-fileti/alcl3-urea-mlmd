#!/usr/bin/env python3
"""Cost ledger: one CSV per machine, results/cost_ledger_<machine>.csv (ADR-0009, ADR-0010).

Usage:
  cost_ledger.py add [--machine M] [--unit U] [--since YYYY-MM-DD] [--workdir DIR ...]
                     [--jobs ID[,ID...]] [--sacct-file F] [--dry-run]
  cost_ledger.py sum --jobs ID[,ID...]      (ID or machine:ID; reads every ledger)

`add` appends one row per ended job (completed, failed, cancelled, timeout, ...) from
Slurm accounting (`sacct -X -P`) that is not already in the machine's ledger.
Attribution (ADR-0010): only jobs whose WorkDir is inside this repo's runs/ (the link and
the directory it resolves to) or inside a --workdir given explicitly; or the job IDs given
with --jobs. Never "all jobs of the user": other projects share the account.
With an empty ledger --since is required (unless --jobs); otherwise it defaults to the
latest recorded end date. --sacct-file reads saved `sacct -X -n -P -o <FIELDS>` output.

--machine defaults to the machine detected from the hostname (configs/machines/*.yaml)
and --unit to that machine's cost.unit.

Cost estimate: unit "core-hours" = ElapsedRaw x AllocCPUS / 3600; unit "UA" (SDumont,
ADR-0017) = ElapsedRaw x (AllocCPUS + 100 x GPUs) / 3600, GPUs from AllocTRES gres/gpu.
Any other unit is written as "unknown" (ADR-0005). `sum` reports totals per unit and
never adds different units together.
Standard library only; runs on Python >= 3.6.
"""
import argparse
import csv
import datetime
import getpass
import io
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import machine_config  # noqa: E402  (same directory; works under python -I too)

DEFAULT_REPO = Path(__file__).resolve().parent.parent
FIELDS = ["JobID", "JobName", "Partition", "State", "ExitCode",
          "Start", "End", "ElapsedRaw", "AllocCPUS", "NodeList", "WorkDir", "AllocTRES"]
UA_PER_GPU_HOUR = 100   # LNCC: 1 UA per CPU core-hour, 100 per GPU-hour (ADR-0017)
COLUMNS = ["machine", "job_id", "job_name", "partition", "state", "exit_code",
           "start", "end", "elapsed_s", "alloc_cpus", "nodelist", "workdir",
           "cost", "cost_unit", "recorded_at"]
NOT_ENDED = {"PENDING", "RUNNING", "REQUEUED", "RESIZING", "SUSPENDED"}
MACHINE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
JOBID_RE = re.compile(r"^[0-9]+([_+][0-9]+)?$")


class LedgerError(Exception):
    pass


def ledger_path(repo, machine):
    return repo / "results" / "cost_ledger_{}.csv".format(machine)


def read_ledger(path):
    if not path.exists():
        return []
    with open(str(path), newline="") as f:
        r = csv.DictReader(f)
        if r.fieldnames != COLUMNS:
            raise LedgerError("{}: unexpected header {}".format(path, r.fieldnames))
        return list(r)


def parse_sacct(text):
    """Parse `sacct -X -n -P -o FIELDS` output into dicts; skip blank lines."""
    jobs = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) != len(FIELDS):
            raise LedgerError("sacct line {}: expected {} fields, got {}: {!r}".format(
                n, len(FIELDS), len(parts), line))
        jobs.append(dict(zip(FIELDS, parts)))
    return jobs


def is_ended(job):
    state = job["State"].split()[0] if job["State"] else ""
    return state not in NOT_ENDED and job["End"] not in ("", "Unknown", "None")


def alloc_gpus(tres):
    """GPUs in AllocTRES ('cpu=6,gres/gpu=1,...'); typed gres/gpu:<type> ignored (no double count)."""
    for item in tres.split(","):
        key, _, val = item.partition("=")
        if key == "gres/gpu":
            return int(val)
    return 0


def estimate(job, unit):
    try:
        elapsed, cpus = int(job["ElapsedRaw"]), int(job["AllocCPUS"])
        if unit == "core-hours":
            return "{:.4f}".format(elapsed * cpus / 3600.0)
        if unit == "UA":
            if elapsed > 0 and not job["AllocTRES"]:
                return "unknown"          # ran, but no allocation recorded
            gpus = alloc_gpus(job["AllocTRES"])
            return "{:.4f}".format(elapsed * (cpus + UA_PER_GPU_HOUR * gpus) / 3600.0)
    except ValueError:
        return "unknown"
    return "unknown"


def default_workdirs(repo):
    """repo/runs as written and as resolved; empty if the repo has no runs/ link or dir."""
    runs = repo / "runs"
    if not runs.exists():
        return []
    return sorted({os.path.normpath(str(runs)), os.path.realpath(str(runs))})


def inside(path, prefixes):
    p = os.path.normpath(path)
    return any(p == d or p.startswith(d.rstrip("/") + "/") for d in prefixes)


def run_sacct(since=None, jobs=None):
    cmd = ["sacct", "-X", "-n", "-P", "-u", getpass.getuser(), "-o", ",".join(FIELDS)]
    cmd += ["-j", ",".join(jobs)] if jobs else ["-S", since]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    if p.returncode != 0:
        raise LedgerError("sacct failed: {}".format(p.stderr.strip()))
    return p.stdout


def add(repo, machine, unit, since=None, sacct_text=None, dry_run=False,
        workdirs=None, jobs=None):
    if not MACHINE_RE.match(machine):
        raise LedgerError("bad machine name {!r}".format(machine))
    if jobs:
        bad = [j for j in jobs if not JOBID_RE.match(j)]
        if bad:
            raise LedgerError("bad job id(s): {}".format(", ".join(bad)))
        prefixes = None
    else:
        prefixes = [os.path.normpath(os.path.expanduser(d)) for d in (workdirs or [])]
        prefixes = prefixes or default_workdirs(repo)
        if not prefixes:
            raise LedgerError("no runs/ in {} and no --workdir: give --workdir or --jobs".format(repo))
    path = ledger_path(repo, machine)
    rows = read_ledger(path)
    if since is None and not jobs:
        ends = [r["end"] for r in rows if r["end"]]
        if not ends:
            raise LedgerError("empty ledger: give --since YYYY-MM-DD (or --jobs)")
        since = max(ends)[:10]
    if sacct_text is None:
        sacct_text = run_sacct(since, jobs)
    known = {r["job_id"] for r in rows}
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    new, skipped = [], 0
    for j in parse_sacct(sacct_text):
        if jobs and j["JobID"] not in jobs:
            continue
        if not is_ended(j) or j["JobID"] in known:
            continue
        if prefixes is not None and not inside(j["WorkDir"], prefixes):
            skipped += 1
            continue
        known.add(j["JobID"])
        new.append({
            "machine": machine, "job_id": j["JobID"], "job_name": j["JobName"],
            "partition": j["Partition"], "state": j["State"], "exit_code": j["ExitCode"],
            "start": j["Start"], "end": j["End"], "elapsed_s": j["ElapsedRaw"],
            "alloc_cpus": j["AllocCPUS"], "nodelist": j["NodeList"], "workdir": j["WorkDir"],
            "cost": estimate(j, unit), "cost_unit": unit, "recorded_at": now,
        })
    if new and not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not path.exists()
        with open(str(path), "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
            if fresh:
                w.writeheader()
            w.writerows(new)
    return path, since, new, skipped


def all_rows(repo):
    rows = []
    for path in sorted((repo / "results").glob("cost_ledger_*.csv")):
        rows.extend(read_ledger(path))
    return rows


def sum_jobs(repo, job_specs):
    rows = all_rows(repo)
    picked, missing, ambiguous = [], [], []
    for spec in job_specs:
        machine, _, jid = spec.rpartition(":")
        hits = [r for r in rows if r["job_id"] == jid and (not machine or r["machine"] == machine)]
        if not hits:
            missing.append(spec)
        elif len(hits) > 1:
            ambiguous.append("{} ({})".format(spec, ", ".join(r["machine"] for r in hits)))
        else:
            picked.append(hits[0])
    if missing or ambiguous:
        msg = []
        if missing:
            msg.append("not in any ledger: " + ", ".join(missing))
        if ambiguous:
            msg.append("ambiguous, use machine:ID: " + "; ".join(ambiguous))
        raise LedgerError("; ".join(msg))
    totals = {}
    for r in picked:
        t = totals.setdefault(r["cost_unit"], {"cost": 0.0, "unknown": 0, "jobs": 0})
        t["jobs"] += 1
        if r["cost"] == "unknown":
            t["unknown"] += 1
        else:
            t["cost"] += float(r["cost"])
    return picked, totals


def split_ids(text):
    return [s.strip() for s in text.split(",") if s.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=str(DEFAULT_REPO), help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd")
    a_add = sub.add_parser("add", help="append ended jobs of this project from sacct")
    a_add.add_argument("--machine", help="default: detected from hostname")
    a_add.add_argument("--unit", help="default: cost.unit of the machine config")
    a_add.add_argument("--since", help="YYYY-MM-DD (required for an empty ledger)")
    a_add.add_argument("--workdir", action="append", help="count jobs submitted under DIR")
    a_add.add_argument("--jobs", help="ID[,ID...]: add exactly these jobs")
    a_add.add_argument("--sacct-file", help="saved sacct -X -n -P output")
    a_add.add_argument("--dry-run", action="store_true")
    a_sum = sub.add_parser("sum", help="total cost of a set of jobs")
    a_sum.add_argument("--jobs", required=True, help="ID[,ID...] or machine:ID")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    try:
        if a.cmd == "add":
            text = None
            if a.sacct_file:
                with io.open(a.sacct_file) as f:
                    text = f.read()
            jobs = split_ids(a.jobs) if a.jobs else None
            machine = a.machine or machine_config.detect(repo)
            unit = a.unit or machine_config.load(machine, repo)["cost"]["unit"]
            path, since, new, skipped = add(repo, machine, unit, a.since, text,
                                            a.dry_run, a.workdir, jobs)
            verb = "would add" if a.dry_run else "added"
            for r in new:
                print("{} {} {} {} {}".format(r["job_id"], r["state"], r["elapsed_s"],
                                              r["cost"], r["cost_unit"]))
            print("{} {} row(s) to {} (since {}); {} ended job(s) outside the project skipped".format(
                verb, len(new), path.relative_to(repo), since or "-", skipped))
            return 0
        if a.cmd == "sum":
            picked, totals = sum_jobs(repo, split_ids(a.jobs))
            for r in picked:
                print("{}:{} {} {} {}".format(r["machine"], r["job_id"], r["state"],
                                              r["cost"], r["cost_unit"]))
            for unit, t in sorted(totals.items()):
                extra = " ({} job(s) with unknown cost)".format(t["unknown"]) if t["unknown"] else ""
                print("TOTAL {:.4f} {} over {} job(s){}".format(t["cost"], unit, t["jobs"], extra))
            return 0
        ap.print_help()
        return 2
    except (LedgerError, machine_config.ConfigError) as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
