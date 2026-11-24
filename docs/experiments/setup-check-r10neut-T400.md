# Setup check: Davi's MLMD T400 r10_neut repeated with our driver

A test (exempt from the claim rule, CLAUDE.md), but its reading is fixed here before the run
so the pilot does not start on a broken setup. Owner's ok to run it: 2026-11-24 ("OK pra
tudo"). Rule written 2026-11-24, before any output.

## Question
Does `src/mlmd.py` in the `mace0316_env` venv reproduce the RDFs of Davi's MLMD of the same
system (same model, start, box, temperature, timestep, production thermostat and frame
interval)? A wrong cell, unit, thermostat or model load would show as shifted peaks or
coordination numbers far outside the statistical error.

## Design
- Reference: `results/legacy-mlmd-rdf-run2r10m0/rdf/r10_neut.T400.mlmd-run2r10m0.rdf.csv`
  (Davi, job 11750922; his `DONE.json`: start `init.xyz` sha256 `2fe053fe…`, L = 19.581168 Å,
  400 K, seeds [1, 11], ASE 3.29.0, mace-torch 0.3.16).
- Ours: `configs/mlmd/setup-r10neut-T400.json`. Start: the same `init.xyz`
  (`data/setup-check/`, sha256 checked); model run2r10m0 (sha256 checked), float64.
  - Equilibration 1 ps (2000 × 0.5 fs) with a global Bussi thermostat, τ = 10 fs. Davi used
    a massive CSVR (one thermostat per degree of freedom), τ = 10 fs; this differs on purpose
    (ASE has no massive CSVR) and only affects the equilibration.
  - Production 5 ps (10 000 × 0.5 fs), global Bussi, τ = 100 fs, a frame every 10 steps
    (1001 frames, steps 0–10 000), as Davi. Centre of mass fixed (3N − 3 degrees of freedom),
    as Davi. Seed 1 (Davi's random streams are not reproduced: the trajectories differ, the
    statistics should not).
- RDF: `src/rdf_aimd_v1/rdf.py` (sha256 `7c710bba…`, the same file as Davi's), `xyz` mode,
  `--box 19.581168`, name `r10_neut.T400.mlmd-setupcheck`.
- Comparison: `src/rdf_compare.py <ours> <reference>` with its defaults.

## Reading rule (fixed 2026-11-24, before the run)
- **Pass**: every pair with a first peak has |Δr_peak| ≤ 0.04 Å (2 bins), and the
  differences of g at the reference first peak and of cn at the reference first minimum
  are ≤ 4 combined errors (`rdf_compare.py`: block standard errors; for cn an upper bound
  that treats bins as fully correlated); and the production mean temperature is within
  400 ± 5 K.
- **Fail**: any of those violated → the pilot waits; the cause is found first.
- 4 errors (not 2): 10 pairs × 2 quantities with errors from 5 blocks each; at 2 errors
  several chance exceedances are expected. Fractions of bins beyond 2 errors are reported,
  not judged.

## How to run
- `scripts/prep_mlmd.py configs/mlmd/setup-r10neut-T400.json --name setup-r10neut-T400
  --time 01:00:00 --max-chain 2`, then `cd runs/setup-r10neut-T400 && sbatch job.sbatch`.
- After the job: `rdf.py xyz runs/setup-r10neut-T400/prod.xyz --box 19.581168 --name
  r10_neut.T400.mlmd-setupcheck -o runs/setup-r10neut-T400/rdf`, then `rdf_compare.py`.

## Results
(pending)
