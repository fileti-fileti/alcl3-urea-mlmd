# LAMMPS benchmark: is `pair_style mace` at least 2× faster than ASE on the 1512-atom box?

A benchmark (exempt from the claim rule, CLAUDE.md); its decision rule is fixed here before
the job. Owner's ok 2026-11-25 ("OK", with the 2× limit). If the answer is yes, the engine
changes for the pilot and production through a new ADR (ADR-0015 names ASE).

## Question
With the same model and box, does LAMMPS give the same energies and forces as ASE, and is
its MD speed at least twice ASE's, in float64 and in float32?

## Design
- LAMMPS: the owner's build `shared/software/lammps_mace/bin/lmp` (ACEsuit fork, branch
  `mace`, commit `4d222cb`; packages KSPACE ML-MACE MOLECULE OPENMP RIGID; no KOKKOS, no
  ML-IAP), `pair_style mace no_domain_decomposition`, libtorch 2.2.0+cu121 (uses CUDA when
  available, `src/ML-MACE/pair_mace.cpp`); the module `lammps/10Set25_oneapi-2022_cuda12.6`
  points to the same build.
- Model: run2r10m0 (sha256 `ff0e4578…6e3a`) converted on the login node, 2026-11-25, with
  `mace_env` (mace 0.3.15, torch 2.2.0+cu121): `python -m mace.cli.create_lammps_model
  <copy> --dtype float64|float32`. sha256: f64 `2eb828f827ea739a09809759679480037792b110a8f6668565e144d4e642684c`,
  f32 `22728c1547e0a31679c07b987eb394be80267bb6ff1a0dcdf7f4926dcfa58125`.
- Boxes: `r1.0_{reagentes,ionico}.pdb`, L = 29.729979 Å, through `mlmd.read_pdb` into LAMMPS
  data files (`src/lammps_bench.py inputs`; round trip tested).
- Match: LAMMPS `run 0` energy and forces of both boxes against ASE (`MACECalculator`,
  float64, GPU) in the same job. Login-node dry run (CPU, f64, reagentes): energy per atom
  equal to the smoke bench's ASE value within 1.5e-12 eV.
- Speed: reagentes box, 20 minimiser iterations, velocities at 400 K, `fix langevin` 400 K
  (damp 0.1 ps) + `fix nve`, dt 0.5 fs, 50 steps then 500 timed steps; timesteps/s of the
  last `Performance:` line. ASE reference: smoke bench job 11758464 NVT, 6.1299 (f64) and
  8.9343 (f32) steps/s.
- Job: `src/lammps_bench.sbatch`, `sequana_gpu_dev`, 1 V100, `-c 6`, 20 min,
  `--exclude=sdumont8042`; GPU processes logged by `nvidia-smi` to `gpu.log`. ≈ 35 UA.

## Decision rule (fixed 2026-11-25, before the job)
- Match: in float64, for both boxes, |ΔE| per atom ≤ 1e-6 eV and max |ΔF| per atom ≤ 1e-5 eV/Å.
- Speed: LAMMPS ≥ 12.26 steps/s in float64 and ≥ 17.87 steps/s in float32 (2 × ASE).
- **Yes** (LAMMPS for the pilot, new ADR): match and both speeds. **No** (stay with ASE):
  match and either speed below. **Inconclusive**: no match, no `lmp` process on the GPU, or
  the job did not finish both speed runs.
- Reported, not judged: the float32 energies and forces against ASE float64.
- Applied by `src/lammps_bench.py report` (`report.json`, field `verdict`).

## How to run
- `cd runs/lammps-bench && sbatch <repo>/src/lammps_bench.sbatch <repo> <venv>` at a clean,
  committed tree (the job prints the commit).

## Results
(pending)
