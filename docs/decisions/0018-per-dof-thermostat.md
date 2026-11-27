# 0018. One thermostat per degree of freedom (massive_ou) for MLMD equilibration and production
- Status: Accepted. NPT stage superseded by [0019](0019-nvt-at-training-density.md).
- Date: 2026-11-25. Decided by: owner (Eudes Fileti). Process: ADR-0013.

## Context
The setup check failed (`docs/experiments/setup-check-r10neut-T400.md`): after a 1 ps global
Bussi equilibration from fresh velocities, the N-H stretches stayed cold (bond-length spread
0.0248 Å against ~0.029 Å expected at 400 K from the model's curvature). The thermostat
check (`docs/experiments/thermostat-check-r10neut-T400.md`) was inconclusive by its rule (A
holds in its last block), but, reported and not judged: the two global-Bussi runs (A, dt
0.5 fs; D, dt 0.25 fs) sat at 0.026–0.027 Å for most of their production, while the run with
one thermostat per degree of freedom (C, τ 100 fs) stayed at 0.029–0.031 Å at the same mean
temperature. The potential energy fell in every run: the starts release energy as they
relax, and a global thermostat removes it from all modes alike, cooling the stiff ones. The
pilot's boxes (Packmol, 1512 atoms) will relax more than those starts.

The LAMMPS benchmark (`docs/experiments/lammps-bench.md`, job 11759182) answered no (1.85 and
2.04 steps/s in f64 and f32 against ASE's 6.13 and 8.93): the engine stays ASE (ADR-0015).

## Decision
- MLMD equilibration and production use `massive_ou` (`src/mlmd.py`): an Ornstein-Uhlenbeck
  update of every momentum component before each velocity Verlet step (CSVR with one degree
  of freedom; the update of Davi's massive CSVR and of CP2K's REGION MASSIVE).
- Pilot (r = 1.0, 400 K): minimise (FIRE, fmax 0.05 eV/Å or 2000 steps) → `massive_ou` 2 ps
  at 400 K, τ 10 fs, dt 0.25 fs (replaces the Bussi ramp 100 → 400 K; `massive_ou` has no
  ramp) → NPT Berendsen 50 ps as ADR-0016 → production `massive_ou` τ 100 fs, dt 0.5 fs.
  Configs `configs/mlmd/pilot-r10-T400-ou-{reag,ion}.json` (the Bussi configs
  `pilot-r10-T400-{reag,ion}.json` are superseded).
- The NPT stage keeps ASE's NPTBerendsen with its own (global) velocity rescaling.

## Owner's approval (2026-11-25) and agent's justification
- Agent's proposal (2026-11-25): "Pilot inteiro com termostato por grau de liberdade
  (`massive_ou`): τ 10 fs na rampa e τ 100 fs na produção … O NPT continua Berendsen, como na
  ADR-0016"; then the protocol above. Owner: "sigamos então com ASE e vamos submeter os dois
  inícios."
- Agent's justification: a per-degree-of-freedom thermostat keeps every mode at the target
  temperature while the structure relaxes and releases energy; in the thermostat check it was
  the variant that held the expected N-H spread.

## Consequences
- The stochastic coupling (friction 1/τ per degree of freedom) slows the dynamics somewhat:
  the time for the two starts to converge may be longer than with a global thermostat; the
  equilibrium speciation is not affected by the choice of a canonical thermostat.
- Not measured: the effect of τ on diffusion or on the speciation kinetics.
- The pilot's phase-1 frames (every 10 fs) let the N-H spread be followed with
  `src/bond_width.py`.
