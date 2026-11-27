# Pilot: r = 1.0, 400 K, two opposite starts (phase 1 approved; reading rule not fixed)

Status: phase-1 rerun under ADR-0019 (NVT at 1.5398 g/cm³, no NPT; owner's ok
2026-11-27) submitted 2026-11-27 (jobs 11760903 reag, 11760904 ion). The first phase 1
(jobs 11759186, 11759187, with NPT) is superseded: see First phase 1.
Draft written 2026-11-24 by the agent. Phase 1 (below) approved by the owner
2026-11-24 ("ok"); it is submitted after the setup check passes. The reading rule is fixed
after phase 1 and before phase 2 runs, and the pending claim ID-1 enters `docs/claims.md`
then (CLAUDE.md, Hard rules).

## Question
1. Throughput (ns/day) and stability of 1512-atom MLMD with run2r10m0 on one V100.
2. Starting from the molecular box (Al2Cl6 + urea) and from the fully ionic box
   ([AlCl2(urea)2]+ + AlCl4-) at r = 1.0 and 400 K, do the two runs reach the same Al
   speciation, and after how long? That time sizes the production matrix (handoff
   2026-11-24).

## Phases (owner's ok 2026-11-24)
- Phase 1, exploration: production 0–200 ps of both starts. It shows how each start
  evolves and sizes the reading rule (autocorrelation time of the census quantity, hence
  the block length; window; maximum length). Never judged: no phase-1 frame enters ID-1.
- Phase 2, judged: the same runs, extended. The reading rule and the pending claim ID-1 are
  fixed before phase 2 is submitted; ID-1 is judged on phase-2 frames only.
- Agent's justification: the owner asked for 200 ps first and an extension if the run is
  usable. Deciding the use of data after seeing them breaks ADR-0013; fixing the rule
  between the phases keeps the extension usable without that.
- Extension: add to `run.json` a stage `prod2` (a copy of `prod` with the new `name` and the
  phase-2 `ps`), delete `DONE`, `sbatch job.sbatch` in the run dir. The driver continues from
  `prod.final.traj` with its velocities and RNG state, as a run planned with `prod2` from
  the start would (`tests/test_mlmd.py`, `test_extend_after_done_equals_planned`). The first
  frame of `prod2.xyz` (step 0) repeats the last frame of `prod.xyz`: the census drops it.
  The `run.json` edit goes in the journal (its `provenance` describes the original config).

## Design
- Boxes: `data/boxes/mlmd-boxes-r1.0-v2/r1.0_{reagentes,ionico}.pdb`, L = 29.729979 Å
  (1.5398 g/cm³, experimental at 333 K).
- Model run2r10m0, float32 (owner's ok 2026-11-24). Smoke-bench job 11758464
  (`runs/smoke-bench/report.json`): float32 vs float64 max |ΔF| 1.4e-4 eV/Å on both boxes,
  about 200× below the model's test force error (31.7 meV/Å, `docs/model.md`); ΔE −0.80 and
  −0.78 meV/atom, a near-constant shift; NVT 8.93 vs 6.13 steps/s (1.46×).
- Protocol (ADR-0018, ADR-0019), same for both starts, seeds 1 (reagentes) and 2 (ionico);
  configs `configs/mlmd/pilot-r10-T400-nvt-{reag,ion}.json` (2026-11-27). Superseded:
  `pilot-r10-T400-ou-{reag,ion}.json` (with NPT, ran as the first phase 1) and the
  global-Bussi `pilot-r10-T400-{reag,ion}.json` (prepared at `3540181`, never ran):

  | Stage | Kind | dt | Length | Thermostat / barostat | Output |
  |---|---|---|---|---|---|
  | min | FIRE, fixed cell | — | fmax 0.05 eV/Å or 2000 steps | — | log |
  | eq | `massive_ou`, 400 K | 0.25 fs | 2 ps | τ_T 10 fs | thermo / 10 fs, frames / 50 fs |
  | prod | `massive_ou`, 400 K | 0.5 fs | 200 ps (phase 1) | τ_T 100 fs | thermo / 10 fs, frames / 10 fs |

  Checkpoint every 2000 steps; physical check (finite energy and forces, no pair closer
  than 0.6 Å) every 20 steps. Minimiser values: the agent's, owner's ok 2026-11-24. The
  `eq` stage replaces the Bussi ramp 100 → 400 K (ADR-0018, owner's ok 2026-11-25).
  Every stage runs at L = 29.729979 Å (1.5398 g/cm³); no NPT (ADR-0019, owner's ok
  2026-11-27).
- Frames: about 56 KB each (smoke run); phase-1 `prod.xyz` ≈ 1.1 GB per start (20 001
  frames).
- Jobs: `scripts/prep_mlmd.py configs/mlmd/pilot-r10-T400-nvt-<start>.json --name
  pilot-r10-T400-<start> --max-chain 3`; `sequana_gpu`, 1 V100, `-c 6`, 24 h segments that
  checkpoint and resubmit themselves (owner's ok 2026-11-24), `--exclude=sdumont8042`.
  First phase 1: submitted 2026-11-25 at commit `0577a54` (owner: "vamos submeter os dois
  inícios"), jobs 11759186 (reag), 11759187 (ion); superseded (ADR-0019). Rerun: submitted
  2026-11-27 03:48 at commit `45ca01d`, jobs 11760903 (reag), 11760904 (ion).
- Cost estimate, phase-1 rerun (UA per ADR-0017 = 106 UA/h; rate 8.2 steps/s, the `eq`
  stage of the first phase 1 at this density): ≈ 14 h ≈ 1.5k UA per start, one 24 h
  segment; ≈ 3.0k UA for both. The ledger gives the real cost.
- Census: the neumann criterion (CLAUDE.md, Same model, same census), on every production
  frame. TODO(owner): `extract_species.py` (sha256) to copy into `src/`, with a test
  reproducing a neumann census.

## First phase 1 (superseded, ADR-0019)
- Jobs 11759186 (reag), 11759187 (ion): COMPLETED, exit 0, all stages done, no STOPPED
  (ended 2026-11-25 21:31 and 21:19). Cost (sacct): 1646.5333 and 1624.3028 UA.
- min: FIRE 756 and 723 steps, converged. `eq` (1.5398 g/cm³), second half: T 399.1 ± 7.3 K
  and 403.8 ± 7.8 K; pressure over 1–2 ps 6.4 ± 1.1 and 5.9 ± 1.2 kbar.
- NPT, mean density of the last 25 ps: 1.0869 g/cm³ (reag, still falling) and
  1.2365 g/cm³ (ion, flat). Production (200 ps at those volumes): T 400.6 and 399.8 K
  (second half), 11.2 and 11.0 steps/s.
- Not used: the two starts ran at different volumes, and the rerun's density differs. Data
  kept in `runs/_superseded/pilot-r10-T400-{reag,ion}/`.

## Reading rule — TODO(owner): fix after phase 1, before phase 2 runs
Proposals, to accept or change:
- Census quantity: the fraction of Al in each species class per frame; primary: x(AlCl4-).
- Convergence: over a trailing window W, the block means of the primary quantity of the
  two runs differ by less than 2 combined block errors, blocks longer than the quantity's
  autocorrelation time. TODO(owner): W and the block length (phase 1 gives the
  autocorrelation time).
- Maximum length: TODO(owner) (ns or GPU-days); reaching it without convergence is
  "inconclusive", not "no".
- Only phase-2 frames are judged (see Phases).
- Pending claim: `docs/claims.md` ID-1, once the rule is fixed.

## Results
(pending)
