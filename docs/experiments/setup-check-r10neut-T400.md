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
Job 11758552 (`sequana_gpu`, sdumont8053, 14 min 05 s, COMPLETED 0:0), `runs/setup-r10neut-T400/`
at commit `252340d`: 1001 frames, steps 0–10 000; 18.2 steps/s (median). Output of
`rdf_compare.py` (report `runs/setup-r10neut-T400/rdf/compare.json`, exit 1) and of the
production thermo file:
- 8 of 10 pairs pass. N-H fails: g at the reference peak (1.01 Å) is higher by 13.9
  (reference 104.8), 8.1 combined errors; peak position and cn agree. Cl-H fails: peak
  position −0.06 Å (3 bins); its g at the peak and cn are within 0.7 and 0.1 errors.
  Al-Cl passes with g at the peak higher by 2.1 (reference 25.6), 2.6 errors.
- Production mean temperature 394.69 K (5 block means 394.26, 389.54, 400.08, 398.59,
  390.97 K; standard error 2.06 K): outside 400 ± 5 K.
- **Reading: FAIL.** The pilot waits until the cause is found.
- Agent's diagnosis (a hypothesis, not tested): the N-H stretches are colder than the
  rest. A higher N-H peak means a narrower bond-length distribution, and its width grows
  through the production (N-H bond-length std per 1 ps block: 0.0248, 0.0249, 0.0250,
  0.0254, 0.0254 Å), so those modes were still heating up. Davi's massive CSVR heats every
  degree of freedom directly; our global Bussi equilibration (1 ps) exchanges energy with
  the high-frequency modes only slowly. The low mean temperature fits a heat sink still
  being filled. Candidate fix (owner's decision): a per-atom thermostat (ASE Langevin) for
  the equilibration, then this check again as a new version.
- Follow-up (2026-11-24): `thermostat-check-r10neut-T400.md`. Davi's reference is itself not
  stationary (its N-H spread falls during his production); with Davi's equilibration our
  global-Bussi production keeps the expected spread (inconclusive by that test's rule, which
  asks for this check to be repeated with that equilibration).
- Repeat (v2), 2026-11-25, owner's ok ("segue"): run A of the thermostat check
  (`runs/thermo-r10neut-T400-bussi`, job 11758819, Davi's equilibration), RDF
  `r10_neut.T400.mlmd-setupcheck-v2` (`runs/thermo-r10neut-T400-bussi/rdf/compare.json`), the
  rule above. N-H passes (0.020 Å, 1.42 errors at the peak). Fail: Al-Al peak −0.06 Å, Cl-H
  peak −0.18 Å (both broad peaks; their g and cn within 0.7 errors), C-O g at the peak 4.10
  errors; production mean T 405.07 K (5 block means 409.49, 404.57, 406.64, 401.61, 403.00 K;
  standard error 1.39 K), outside 400 ± 5 K. **Reading: FAIL.**
- **Owner's decision (2026-11-25, "Aceita já"): the setup is accepted despite the fail; the
  pilot no longer waits on this check.** Agent's justification: the same start gives the
  same potential energy in both drivers (−89435.083640 vs −89435.083638 eV), which excludes a
  wrong cell, unit or model load; the v1 N-H fail is gone with Davi's equilibration; what
  fails in v2 are positions of broad peaks and two marginal values, from two single 5 ps
  trajectories that are still relaxing (their potential energy falls in both). Not
  measured: the run-to-run spread of this rule (a second seed was proposed and declined).
