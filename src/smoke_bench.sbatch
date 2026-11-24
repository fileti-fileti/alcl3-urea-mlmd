#!/bin/bash -l
# GPU smoke test + benchmark (src/smoke_bench.py) and the driver's checkpoint/resume on the
# real box (runs/smoke-driver, prepared by scripts/prep_mlmd.py). Submit from runs/smoke-bench/:
#   sbatch <repo>/src/smoke_bench.sbatch <repo> <venv>
#SBATCH -J smoke-bench
#SBATCH -p sequana_gpu_dev
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH -c 6
#SBATCH --mem=32G
#SBATCH -t 00:20:00
#SBATCH --no-requeue
#SBATCH --export=NONE
#SBATCH -o slurm-%x-%j.out
set -uo pipefail
repo=$1 venv=$2
S=/scratch/acmes/eudes.fileti3/projects/alcl3-urea-mlmd-store/data
echo "job=${SLURM_JOB_ID:-local} node=$(hostname) start=$(date -Is)"
module purge
module load python/3.10.16_sequana || exit 5
unset PYTHONPATH
export OMP_NUM_THREADS=6
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
py=("$venv/bin/python" -I)
# 1. checks + benchmark; seed reference: mace_env 0.3.15 on CPU, 2026-11-24 (docs/model.md)
"${py[@]}" "$repo/src/smoke_bench.py" \
  --model "$S/models/run2r10m0/alcl3_urea_run2_r10_m0.model" \
  --sha256 ff0e4578c01cd5ba8d6f08ba35eda9ad27e8d580f50f9085c37222485fd46e3a \
  --boxes "$S/boxes/mlmd-boxes-r1.0-v2" --box-L 29.729979 \
  --seed-xyz /scratch/acmes/eudes.fileti3/projects/alcl3_urea_data/01_geo/r10_mist/init.xyz \
  --seed-L 19.581168 --seed-ref-e-per-atom -206.77601684757508 -o report.json
echo "smoke_bench rc=$?"
# 2. driver on the real box: budget 1 s forces a checkpoint after the first MD chunk (rc 3),
#    then the resume must finish every stage (rc 0)
D="$repo/runs/smoke-driver"
"${py[@]}" "$repo/src/mlmd.py" run "$D" --budget-s 1; echo "driver pass 1 rc=$? (expect 3)"
"${py[@]}" "$repo/src/mlmd.py" run "$D"; echo "driver pass 2 rc=$? (expect 0)"
ls "$D"
echo "end=$(date -Is)"
