#!/bin/bash -l
# Build the MLMD venv offline on a CPU node: Python module python/3.10.16_sequana + the pins of
# envs/mace0316.requirements-lock.txt (Davi's env lock: mace-torch 0.3.16, torch 2.11.0+cu126,
# ase 3.29.0). Wheels: Davi's wheelhouse (read-only). Compute nodes cannot reach PyPI (proxy).
# Submit from runs/env-mace0316/ (ledger attribution):
#   sbatch <repo>/envs/build_mace0316.sbatch <venv_dir> <wheelhouse> <lockfile>
# If the wheelhouse is gone: on the login node, `pip download -r <lockfile> -d <dir>
#   --extra-index-url https://download.pytorch.org/whl/cu126` (python 3.10 module), then rerun.
#SBATCH -J env-mace0316
#SBATCH -p sequana_cpu_dev
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH -c 4
#SBATCH --mem=16G
#SBATCH -t 00:20:00
#SBATCH --no-requeue
#SBATCH --export=NONE
#SBATCH -o slurm-%x-%j.out
set -euo pipefail
(( $# == 3 )) || { echo "usage: build_mace0316.sbatch <venv_dir> <wheelhouse> <lockfile>"; exit 2; }
venv=$1 wheels=$2 lock=$3
echo "job=${SLURM_JOB_ID:-local} node=$(hostname) start=$(date -Is)"
[[ ! -e $venv ]] || { echo "refusing: $venv exists"; exit 1; }
module purge
module load python/3.10.16_sequana
unset PYTHONPATH          # the module's PYTHONPATH would leak its own packages into the venv
python3 -m venv "$venv"
pip=("$venv/bin/pip" install -q --no-index --find-links "$wheels")
"${pip[@]}" --upgrade pip
"${pip[@]}" -r "$lock"
"$venv/bin/pip" freeze > "$venv/requirements-lock.txt"
if diff <(sort -f "$lock") <(sort -f "$venv/requirements-lock.txt"); then echo "lock: identical"; else echo "lock: DIFFERS"; exit 1; fi
"$venv/bin/python" -c 'import importlib.metadata as m, torch, ase, numpy, mace.calculators; print("torch", torch.__version__, "| mace-torch", m.version("mace-torch"), "| ase", ase.__version__, "| numpy", numpy.__version__, "| cuda build", torch.version.cuda)'
echo "end=$(date -Is)"
