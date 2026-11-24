# Pilot: r = 1.0, 400 K, two opposite starts (DRAFT — reading rule not fixed)

Status: draft written 2026-11-24 by the agent. Nothing runs until the owner fixes the reading
rule below and the pending claim enters `docs/claims.md` (CLAUDE.md, Hard rules).

## Question
1. Throughput (ns/day) and stability of 1512-atom MLMD with run2r10m0 on one V100.
2. Starting from the molecular box (Al2Cl6 + urea) and from the fully ionic box
   ([AlCl2(urea)2]+ + AlCl4-) at r = 1.0 and 400 K, do the two runs reach the same Al
   speciation, and after how long? That time sizes the production matrix (handoff
   2026-11-24).

## Design
- Boxes: `data/boxes/mlmd-boxes-r1.0-v2/r1.0_{reagentes,ionico}.pdb`, L = 29.729979 Å
  (1.5398 g/cm³, experimental at 333 K).
- Model run2r10m0; dtype: float64 unless the benchmark (`runs/smoke-bench/report.json`)
  shows float32 forces within a tolerance the owner accepts. TODO(owner): dtype.
- Protocol (ADR-0016), same for both starts, seeds 1 (reagentes) and 2 (ionico):

  | Stage | Kind | dt | Length | Thermostat / barostat | Output |
  |---|---|---|---|---|---|
  | min | FIRE, fixed cell | — | fmax 0.05 eV/Å or 2000 steps | — | log |
  | ramp | NVT Bussi, 100 → 400 K | 0.25 fs | 2 ps | τ_T 10 fs | thermo / 100 steps |
  | npt | NPT Berendsen, 1 bar | 0.5 fs | 50 ps | τ_T 100 fs, τ_P 1 ps, β 4.5e-5 bar⁻¹ | thermo / 100 steps, frames / 2000 steps |
  | prod | NVT Bussi, 400 K | 0.5 fs | ≤ max length | τ_T 100 fs | thermo / 100, frames / 100 steps (50 fs) |

  The ramp values (100 K start, 2 ps, 0.25 fs, τ 10 fs) and the minimiser settings are the
  agent's; TODO(owner): ok. The NVT box takes the mean NPT volume of its last 25 ps.
- Jobs: `scripts/prep_mlmd.py`, `sequana_gpu`, 1 V100, `-c 6`, 24 h segments that checkpoint
  and resubmit themselves (owner's ok 2026-11-24), `--exclude=sdumont8042`.
- Census: the neumann criterion (CLAUDE.md, Same model, same census), on every production
  frame. TODO(owner): `extract_species.py` (sha256) to copy into `src/`, with a test
  reproducing a neumann census.

## Reading rule — TODO(owner): fix before the pilot runs
Proposals, to accept or change:
- Census quantity: the fraction of Al in each species class per frame; primary: x(AlCl4-).
- Convergence: over a trailing window W, the block means of the primary quantity of the
  two runs differ by less than 2 combined block errors, blocks longer than the quantity's
  autocorrelation time. TODO(owner): W and the block length.
- Maximum length: TODO(owner) (ns or GPU-days); reaching it without convergence is
  "inconclusive", not "no".
- Pending claim: `docs/claims.md` ID-1, once the rule is fixed.

## Results
(pending)
