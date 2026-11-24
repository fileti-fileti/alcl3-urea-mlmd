#!/usr/bin/env python3
"""Prepare an MLMD run dir under runs/: run.json (config + provenance) and a self-resubmitting
Slurm job (ADR-0015, ADR-0016; scheme approved by the owner 2026-11-24).

Usage:
  prep_mlmd.py <config.json> --name <run> [--partition sequana_gpu] [--time 1-00:00:00]
               [--cpus 6] [--mem 32G] [--max-chain 30] [--exclude sdumont8042]
               [--env <venv>] [--margin-s 600] [--repo <repo>]

The config holds what src/mlmd.py reads (model, structure, stages, ...). Relative paths in it
(model.path, structure.path) are taken from the repo root and written as absolute paths.
The job loads the machine's Python module, runs `src/mlmd.py run <run_dir>` with a time budget
of the wall time minus --margin-s, and on exit code 3 (budget reached, checkpoint written)
submits itself again with CHAIN+1, up to --max-chain jobs; any other code ends the chain.
Refuses: an existing run dir, a dirty work tree, a model without sha256, a partition or env
not listed in configs/machines/<machine>.yaml.
Standard library only; Python >= 3.6.
"""
import argparse
import datetime
import hashlib
import json
import re
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import machine_config as mc  # noqa: E402

DEFAULT_REPO = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")   # runs/<exp>-r<NN>-T<T>-<start> (CLAUDE.md)
TIME_RE = re.compile(r"^(?:(\d+)-)?(\d{1,2}):(\d{2}):(\d{2})$")

JOB = """#!/bin/bash -l
# MLMD run {name}: written by scripts/prep_mlmd.py at commit {commit}. Submit from this dir:
#   cd {run_dir} && sbatch job.sbatch
#SBATCH -J {name}
#SBATCH -p {partition}
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH -c {cpus}
#SBATCH --mem={mem}
#SBATCH -t {time}
#SBATCH --requeue
#SBATCH --export=NONE
{exclude}#SBATCH -o slurm-%x-%j.out
set -uo pipefail
CHAIN=${{CHAIN:-0}}
cd {run_dir} || exit 5
echo "job=${{SLURM_JOB_ID:-local}} chain=$CHAIN node=$(hostname) start=$(date -Is)"
module purge
module load {module} || exit 5
unset PYTHONPATH
export OMP_NUM_THREADS={cpus}
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
{python} -I {repo}/src/mlmd.py run {run_dir} --budget-s {budget}
rc=$?
echo "mlmd rc=$rc end=$(date -Is)"
case $rc in
  0) echo "all stages done"; exit 0 ;;
  3) if (( CHAIN + 1 >= {max_chain} )); then echo "max chain ({max_chain}) reached: not resubmitting"; exit 1; fi
     sbatch --export=CHAIN=$((CHAIN + 1)) {run_dir}/job.sbatch || exit 6
     exit 0 ;;
  *) echo "no resubmission (rc=$rc)"; exit "$rc" ;;
esac
"""


class PrepError(Exception):
    pass


def git(repo, *args):
    p = subprocess.run(["git"] + list(args), cwd=str(repo), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    if p.returncode != 0:
        raise PrepError("git {}: {}".format(" ".join(args), p.stderr.strip()))
    return p.stdout


def parse_time(text):
    m = TIME_RE.match(text)
    if not m:
        raise PrepError("--time {!r}: expected [D-]HH:MM:SS".format(text))
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def sha256(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare(repo, config, name, partition="sequana_gpu", time="1-00:00:00", cpus=6, mem="32G",
            max_chain=30, exclude="", env=None, margin_s=600, machine=None, now=None):
    repo = Path(repo).absolute()
    if not NAME_RE.match(name):
        raise PrepError("--name {!r}: use [A-Za-z0-9._-]".format(name))
    machine = machine or mc.detect(repo)
    if not machine:
        raise PrepError("machine not detected (configs/machines/)")
    mcfg = mc.load(machine, repo)
    if partition not in mcfg["partitions"]:
        raise PrepError("partition {!r} not in {}.yaml".format(partition, machine))
    envs = mcfg["python"]["envs"]
    env = env or next((e for e in envs if e.endswith("mace0316_env")), None)
    if env not in envs:
        raise PrepError("env {!r} not in {}.yaml python.envs".format(env, machine))
    module = mcfg["python"]["module"]
    if module == mc.UNKNOWN:
        raise PrepError("python.module unknown in {}.yaml".format(machine))
    secs = parse_time(time)
    if secs <= margin_s + 60:
        raise PrepError("--time must exceed --margin-s by more than 60 s")
    if max_chain < 1:
        raise PrepError("--max-chain must be >= 1")
    if git(repo, "status", "--porcelain").strip():
        raise PrepError("work tree not clean: commit first (runs record their commit)")
    commit = git(repo, "rev-parse", "HEAD").strip()
    run_dir = repo / "runs" / name
    if run_dir.exists():
        raise PrepError("{} exists".format(run_dir))
    cfg_path = Path(config)
    cfg = json.loads(cfg_path.read_text())
    for key in ("model", "structure"):
        p = Path(cfg[key]["path"])
        cfg[key]["path"] = str(p if p.is_absolute() else repo / p)
        if not Path(cfg[key]["path"]).is_file():
            raise PrepError("{}.path not found: {}".format(key, cfg[key]["path"]))
    if not cfg["model"].get("sha256"):
        raise PrepError("model.sha256 missing")
    if sha256(cfg["model"]["path"]) != cfg["model"]["sha256"]:
        raise PrepError("model sha256 does not match the file")
    cfg["provenance"] = {
        "commit": commit, "config": str(cfg_path), "config_sha256": sha256(cfg_path),
        "structure_sha256": sha256(cfg["structure"]["path"]), "machine": machine,
        "host": socket.gethostname(),
        "created": (now or datetime.datetime.now()).isoformat(timespec="seconds"),
        "slurm": {"partition": partition, "time": time, "cpus": cpus, "mem": mem,
                  "max_chain": max_chain, "exclude": exclude, "margin_s": margin_s},
        "env": env, "module": module}
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps(cfg, indent=1) + "\n")
    job = JOB.format(name=name, commit=commit[:12], run_dir=run_dir, partition=partition,
                     cpus=cpus, mem=mem, time=time, module=module, repo=repo,
                     python=Path(env) / "bin" / "python", budget=secs - margin_s,
                     max_chain=max_chain,
                     exclude="#SBATCH --exclude={}\n".format(exclude) if exclude else "")
    (run_dir / "job.sbatch").write_text(job)
    return run_dir


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("config")
    ap.add_argument("--name", required=True)
    ap.add_argument("--partition", default="sequana_gpu")
    ap.add_argument("--time", default="1-00:00:00")
    ap.add_argument("--cpus", type=int, default=6)
    ap.add_argument("--mem", default="32G")
    ap.add_argument("--max-chain", type=int, default=30)
    ap.add_argument("--exclude", default="sdumont8042")
    ap.add_argument("--env", default=None)
    ap.add_argument("--margin-s", type=int, default=600)
    ap.add_argument("--repo", default=str(DEFAULT_REPO))
    a = ap.parse_args(argv)
    try:
        d = prepare(a.repo, a.config, a.name, a.partition, a.time, a.cpus, a.mem, a.max_chain,
                    a.exclude, a.env, a.margin_s)
    except (PrepError, mc.ConfigError, KeyError, ValueError) as e:
        print("prep_mlmd: {}".format(e), file=sys.stderr)
        return 1
    print("prepared {}\nsubmit: cd {} && sbatch job.sbatch".format(d, d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
