#!/bin/bash -l
# LAMMPS (pair_style mace) vs ASE benchmark (docs/experiments/lammps-bench.md). The run dir
# holds the converted models and the inputs (src/lammps_bench.py inputs). Submit from it:
#   cd runs/lammps-bench && sbatch <repo>/src/lammps_bench.sbatch <repo> <venv>
#SBATCH -J lammps-bench
#SBATCH -p sequana_gpu_dev
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH -c 6
#SBATCH --mem=32G
#SBATCH -t 00:20:00
#SBATCH --no-requeue
#SBATCH --export=NONE
#SBATCH --exclude=sdumont8042
#SBATCH -o slurm-%x-%j.out
set -uo pipefail
repo=$1 venv=$2
SH=/scratch/acmes/eudes.fileti3/projects/shared
LMP=$SH/software/lammps_mace/bin/lmp
MODEL=$repo/data/models/run2r10m0/alcl3_urea_run2_r10_m0.model
cd "${SLURM_SUBMIT_DIR:-.}" || exit 5
echo "job=${SLURM_JOB_ID:-local} node=$(hostname) start=$(date -Is) commit=$(git -C "$repo" rev-parse HEAD 2>/dev/null || echo unknown)"
export OMP_NUM_THREADS=6
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
sha256sum run2r10m0_f64.model-lammps.pt run2r10m0_f32.model-lammps.pt
# 1. ASE reference, float64, on the GPU (the MLMD venv)
( module purge; module load python/3.10.16_sequana || exit 5; unset PYTHONPATH
  "$venv/bin/python" -I "$repo/src/lammps_bench.py" ref . --model "$MODEL" \
    --sha256 ff0e4578c01cd5ba8d6f08ba35eda9ad27e8d580f50f9085c37222485fd46e3a )
echo "ref rc=$?"
# 2. LAMMPS: libraries of the owner's earlier LAMMPS-MACE jobs plus the CUDA 11 runtime that
#    the login-node profile adds (compute nodes do not read $HOME, hence not the profile)
export LD_LIBRARY_PATH=$SH/software/libtorch-gpu/lib:$SH/envs/mace_env/lib:$SH/cuda-links/cuda-11.4/lib64:${LD_LIBRARY_PATH:-}
if ldd "$LMP" | grep 'not found'; then echo "lmp: missing libraries"; exit 7; fi
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader -l 5 > gpu.log 2>&1 &
smi=$!
for f in sp_reagentes_f64 sp_ionico_f64 sp_reagentes_f32 sp_ionico_f32 bench_f64 bench_f32; do
  "$LMP" -in "$f.in" -log "$f.log" > "$f.out" 2>&1
  echo "$f rc=$? $(date -Is)"
done
kill "$smi" 2>/dev/null
# 3. report with the rule applied
( module purge; module load python/3.10.16_sequana || exit 5; unset PYTHONPATH
  "$venv/bin/python" -I "$repo/src/lammps_bench.py" report . )
echo "report rc=$? end=$(date -Is)"
