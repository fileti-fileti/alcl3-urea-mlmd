# 0016. Short NPT to relax the start-box pressure with a stress-free model
- Status: Accepted (protocol, NPT length). Barostat and its other parameters: Proposed,
  pending the owner's ok.
- Date: 2026-11-24. Decided by: owner (Eudes Fileti). Process: ADR-0013.

## Context
The model was trained on energies and forces only (`docs/model.md`): its stress is defined
(energy derivative with respect to strain) but untrained and untested. The neumann pilot
plan reads: minimise → short NVT with small dt and a T ramp → NPT to the model's density →
production (`docs/handoffs/2026-11-24-neumann-mlmd-boxes.md`). The start boxes are rigid
molecules packed by Packmol at the experimental density at 333 K (1.5398 g/cm³), not
equilibrated. The agent had flagged NPT as unsupported by this model.

## Decision
- Protocol: minimise → short NVT (small dt, T ramp) → **short NPT** to bring the pressure
  of the packed box to plausible values → NVT production in the box left by the NPT stage.
- The NPT stage is a relaxation, not a measurement: its density is not a result and no
  claim uses it.
- NPT length: 50 ps (owner).
- The end density is recorded next to 1.5398 g/cm³ (experimental, 333 K, the density of
  the training data) but is not a gate (owner: density is less relevant).
- Proposed by the agent, TODO(owner): ok: ASE `NPTBerendsen` (weak coupling relaxes the
  pressure without sampling the NPT ensemble, which is all this stage needs), isotropic,
  the box stays cubic; target 1 bar; compressibility 4.5e-5 bar⁻¹ (order of magnitude of a
  molecular liquid; with Berendsen it only sets the relaxation rate); coupling time 1 ps;
  the NVT box takes the mean volume of the last 25 ps, positions scaled to it.

## Owner's explanation (verbatim, 2026-11-24) and agent's check
- "Pequenas simulacoes, só para relaxar a caixa e reduzir a pressao inicial sao possiveis
  em NPT. Considere isso, mesmo sem stress. Já fizemos isso em simulacoes anteriores de
  outros sistemas. A ideia nao é produzir uma pressao perfeita, apenas reduzir a pressao na
  caixa para valores plausiveis."
- "O piloto pode ser um NPT seguido de um NVT."
- "Para NPT acredito que 50 ps de trajetoria sejam o bastante. A densidade é menos
  relevante."
- Agent's check: sound for a relaxation stage. The remaining risk is a biased stress that
  moves the box away from the density the model was trained at; the recorded end density
  makes that visible.

## Consequences
- A test in `src/` checks that `MACECalculator` returns a finite stress for the periodic
  box before the first NPT.
