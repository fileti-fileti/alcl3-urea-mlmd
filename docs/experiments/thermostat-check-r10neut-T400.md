# Thermostat check: what cools the N-H stretches under a global Bussi thermostat? (r10_neut, 400 K)

A test (exempt from the claim rule, CLAUDE.md), with its reading fixed here before the runs.
Owner's ok 2026-11-24 ("ok para tudo"). It follows the failed setup check
(`setup-check-r10neut-T400.md`, Results) and decides the pilot's production thermostat.

## Question
In Davi's MLMD and in our setup check, under a global Bussi thermostat (`ase.md.bussi.Bussi`,
τ = 100 fs, dt = 0.5 fs) the spread of the N-H bond lengths sits below the classical value
expected at 400 K. Davi's run starts at that value (after a per-degree-of-freedom thermostat)
and loses it. Is the cause the global thermostat, the dynamics (velocity Verlet at
dt = 0.5 fs), or neither?

## Background (measured 2026-11-24, before this test; scripts in the session scratchpad)
- Expected N-H spread at 400 K, sqrt(kT/k), with k the model's curvature along the bond (H
  moved, all else fixed; the same 12 bonds in Davi's equilibration end and production end,
  our production start and end): 0.0289–0.0294 Å (standard error 0.0007), k 40.5–41.9
  eV/Å². A lower bound: anharmonicity and a relaxing environment widen the distribution.
- Observed (`src/bond_width.py`, pooled std, five 1 ps blocks): Davi's equilibration (massive
  CSVR, τ = 10 fs) 0.0294–0.0319 Å; Davi's production 0.0304 → 0.0267 Å; our setup-check
  production (after 1 ps of global Bussi) 0.0248 → 0.0254 Å.
- Same start, same model, same cell: potential energy of `init.xyz` −89435.083640 eV (ours)
  and −89435.083638 eV (Davi's). Conserved-energy drift of our production −0.001 eV/ps.
- Davi's driver (`aimd_replay.py`, commit `f2b50475cb51`): massive CSVR = an
  Ornstein-Uhlenbeck update per degree of freedom before velocity Verlet; production
  `ase.md.bussi.Bussi` with `FixCom`, as ours.
- The AIMD of the same run (CP2K, same protocol) has the N-H first-peak height 111.2,
  between Davi's MLMD (104.8) and ours (118.7) (`rdf_compare.py` against Davi's copy
  `data/raw/alcl3_urea/rdf-aimd-v1/r10_neut.T400.aimd.rdf.csv`, sha256 `bc90f0ff…`).

## Design
- Start `data/setup-check/r10_neut.T400.init.xyz` (sha256 `2fe053fe…`), L = 19.581168 Å,
  model run2r10m0, float64, seed 1; the setup check's model, start, box and seed.
- Equilibration, the same in every run: `massive_ou` (new stage kind of `src/mlmd.py`, the
  update of Davi's massive CSVR), 1 ps at 0.5 fs, 400 K, τ = 10 fs; a frame every 5 fs.
- Production 5 ps, a frame every 5 fs, one variant per run:

  | Run | Production | dt | Config |
  |---|---|---|---|
  | A `thermo-r10neut-T400-bussi` | global Bussi, τ 100 fs (Davi's production) | 0.5 fs | `configs/mlmd/thermo-r10neut-T400-bussi.json` |
  | B `thermo-r10neut-T400-nve` | none (NVE) | 0.5 fs | `…-nve.json` |
  | C `thermo-r10neut-T400-ou` | `massive_ou`, τ 100 fs | 0.5 fs | `…-ou.json` |
  | D `thermo-r10neut-T400-bussi025` | global Bussi, τ 100 fs | 0.25 fs | `…-bussi025.json` |

- Jobs: `sequana_gpu`, 1 V100, `--time 01:00:00 --max-chain 2`, `--exclude=sdumont8042`.
  Estimate from the setup check (18 steps/s): ≈ 25 UA each for A–C, ≈ 40 UA for D.

## Reading rule (fixed 2026-11-24, before the runs)
- Metric: N-H spread of the last 1 ps of production, block 5 of
  `bond_width.py <run>/prod.xyz --box 19.581168 --pair N H --cut 1.2 --blocks 5`.
- Start check: block 5 of the same command on `<run>/eq.xyz` ≥ 0.0285 Å; otherwise that run
  is inconclusive.
- A run **cools** if its metric is < 0.0275 Å and **holds** if it is ≥ 0.0275 Å (0.0275 Å lies
  between the expected ~0.029 Å and the 0.025–0.027 Å the global-Bussi runs reached).
- Reading:
  - A cools and B holds → the global thermostat causes it: the pilot's production thermostat
    changes (to C's if C holds), with an ADR.
  - A cools and B cools → the dynamics causes it: D holds → the time step (dt 0.25 fs, ADR);
    D cools → unexplained, the owner decides.
  - A holds → Davi's cooling is not reproduced: inconclusive; the setup check is repeated
    with this equilibration.
  - C cools → the expected spread is wrong: inconclusive.
- Reported, not judged: potential energy per block, mean temperature, conserved-energy drift.

## How to run
- After the commit with the new stage kinds: for each run `<v>` in bussi, nve, ou, bussi025:
  `scripts/prep_mlmd.py configs/mlmd/thermo-r10neut-T400-<v>.json --name
  thermo-r10neut-T400-<v> --time 01:00:00 --max-chain 2`, then `cd runs/<run> && sbatch job.sbatch`.
- After the jobs: the `bond_width.py` commands above on `eq.xyz` and `prod.xyz` of each run.

## Results
(pending)
