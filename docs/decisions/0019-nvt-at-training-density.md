# 0019. NVT at the training density for both starts; no NPT stage
- Status: Accepted. Supersedes [0016](0016-npt-pressure-relaxation.md) and the NPT stage of
  [0018](0018-per-dof-thermostat.md).
- Date: 2026-11-27. Decided by: owner (Eudes Fileti). Process: ADR-0013.

## Context
- Pilot phase 1 ran the protocol of ADR-0016 and ADR-0018 (jobs 11759186 reag, 11759187
  ion; commit `0577a54`; `docs/experiments/pilot-r10-T400.md`). Both COMPLETED, all stages
  done.
- Model pressure at the start density (1.5398 g/cm³, 400 K; `eq` stage, mean ± standard
  deviation of the instantaneous values over 1–2 ps): 6.4 ± 1.1 kbar (reag), 5.9 ± 1.2 kbar
  (ion) (`runs/pilot-r10-T400-*/eq.thermo.csv`).
- The 50 ps NPT Berendsen then expanded both boxes. Mean density of the last 25 ps:
  1.0869 g/cm³ (reag, −29 %, still falling: 1.095 → 1.079 g/cm³ from 25–37.5 to 37.5–50 ps)
  and 1.2365 g/cm³ (ion, −20 %, flat) (`npt.volume.json`, `npt.thermo.csv`).
- The two starts then ran NVT production at different volumes. Those are two thermodynamic
  states, so they cannot reach the same speciation by construction, and the pilot question
  (the same speciation from opposite starts) is ill-posed on them.
- The NPT is driven by the model's stress, which is untrained (`docs/model.md`). It took the
  boxes to densities absent from the training data, which covers 1.5398 g/cm³ only. This is
  the risk ADR-0016 had recorded.
- At fixed volume the pressure is only a readout; the dynamics uses forces only. Whether the
  ~6 kbar also means wrong forces at 1.5398 g/cm³ is not known. There are three cases:
  1. The error is in the virial only: force training does not fix the pair decomposition of
     the virial.
  2. The D3 tail beyond r_max = 6 Å is missing.
  3. The pressure belongs to the DFT itself. It would then be shared with the AIMD, which
     ran NVT at the same density and is the reference the MLMD is compared with.

  In cases 1 and 2 the forces at that density stay close to the trained ones. The AIMD batch
  inputs on SDumont (`alcl3_urea_data`) compute no stress tensor, so the DFT pressure is
  unknown.

## Decision
- Both starts run NVT at the same density, 1.5398 g/cm³ (L = 29.729979 Å). This is the
  experimental density at 333 K and the density of the training data and of the AIMD. There
  is no NPT stage.
- Pilot protocol:
  1. Minimise (FIRE, fmax 0.05 eV/Å or 2000 steps).
  2. `massive_ou` for 2 ps at 400 K, τ 10 fs, dt 0.25 fs.
  3. Production with `massive_ou`, τ 100 fs, dt 0.5 fs.

  Configs: `configs/mlmd/pilot-r10-T400-nvt-{reag,ion}.json`. ADR-0018's thermostat
  decision stands.
- The pressure stays in the thermo output, recorded. It is not a gate and no claim uses it.
- The production matrix follows the same rule unless a new ADR changes it, for example after
  a DFT stress check.

## Owner's approval (2026-11-27) and agent's justification
- Agent's proposal (2026-11-27, chat): "NVT com a mesma densidade para os dois inícios, a de
  1.5398, que é a do treino e do AIMD." Owner: "ok, vamos seguir sua recomendacao."
- Agent's justification:
  - At the training density the model interpolates (test force error 31.7 meV/Å,
    `docs/model.md`), and the MLMD compares with the AIMD at the same density.
  - The NPT chases the least reliable quantity of the model into densities without training
    data.
  - A common volume makes the two starts one thermodynamic state.

## Consequences
- The model's pressure at the run density (~6 kbar) remains. If it were physical (case 3),
  it would bias the speciation against experiment: ΔG shifts by P·ΔV_r, with ΔV_r unknown.
  That bias would be shared with the AIMD. It is not measured.
  TODO(owner): DFT stress on a few AIMD frames (neumann), to separate the three cases.
- The real density at 400 K is below the 333 K value by thermal expansion. It is not used.
  TODO(owner): the measured density of AlCl3:urea at r = 1.0 and 400 K, if known.
- The first phase-1 runs (jobs 11759186, 11759187) are superseded. They were exploration at
  densities this ADR excludes, and they do not size the reading rule. Phase 1 reruns under
  this ADR.
