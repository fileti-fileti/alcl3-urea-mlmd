# 0015. Scope, sites, fixed model and MLMD engine
- Status: Accepted
- Date: 2026-11-24. Decided by: owner (Eudes Fileti), proposed by the agent. Process:
  ADR-0013.

## Context
Three sites work on AlCl3:urea: neumann (project `alcl3-urea`: AIMD, dataset and labels,
start boxes, census), SDumont account `davi.fileti` (calibration and MACE training) and
SDumont account `eudes.fileti3` (MLMD). A trained model exists (`run2r10m0`,
`docs/model.md`). An earlier tree in this account (`alcl3_urea_mlip`, 2026-10-13) planned
training, active learning and MLMD here; the training was done in Davi's account. The
neumann pilot plan included committee monitoring and active learning. The agent proposed a
separate repo, ASE as the engine (the route the model was validated with) and asked
whether the committee was needed.

## Decision
- Separate repo `alcl3-urea-mlmd` for the MLMD on SDumont. Scope: MLMD and its analysis;
  no dataset generation, labelling or training.
- Model: `run2r10m0`, sha256 `ff0e4578c01cd5ba8d6f08ba35eda9ad27e8d580f50f9085c37222485fd46e3a`,
  used as is. A different model needs a new ADR; runs with different models never share
  a claim.
- No committee: member 0 only; no disagreement monitoring, no active learning.
- Engine: ASE with `mace.calculators.MACECalculator` (GPU) in a dedicated env with
  mace-torch 0.3.16, the version on the card; `mace_env` (0.3.15) stays as fallback.
  LAMMPS may be considered later, in a new ADR.
- Old tree `alcl3_urea_mlip`: its empty folders removed; model files copied to the store
  with checksums; the rest is removed only with the owner's ok.

## Owner's approval (verbatim, 2026-11-24) and agent's check
- "Faça o repo separado."
- "Voce precisa mesmo do comite? Nao faremos treino algum, tudo que precisaremos é rodas as
  simulacoes no LAMMPS; q é um passo posterior ao treino."
- "Use ASE. Mas talvez precisemos considerar o LAMMPS depois."
- "Use a que versao do Mace que for mais favoravel, se nao me engano foi a q davi usou tb:
  0.3.16"
- "Quanto a estrutura antiga, se estiver vazia, ignore-a/remova, pois ela deve ter sido
  empregada na conta do davi do SD."
- Agent's justification: ASE + MACECalculator is the route on the model's card, so the
  card's MLMD can be repeated as a setup check; a separate repo keeps MLMD claims apart from
  the dataset project.

## Consequences
- Without the committee there is no per-frame uncertainty: an out-of-domain state shows
  only as instability (minimum-distance stop), drift in T or energy, or unphysical
  structure against `docs/rdf-references.md`.
- The census must equal neumann's: `extract_species.py` enters with its commit and sha256
  and a test reproducing a neumann census (TODO(owner): commit).
- `mace_env` is shared and untouchable (ADR-0007): the 0.3.16 env is a new one, created
  outside the repo with the owner's ok and recorded in `envs/sdumont.environment.yml`.
