# Glossary

One line per term.

- **ADR**: Architecture Decision Record, `docs/decisions/NNNN-*.md`; never edited once accepted, only superseded.
- **AIMD system labels** (`r10_mist`, `r13_ionA`, `r15_neut`, ...): start seeds of the neumann AIMD; `rNN` is r × 10. TODO(owner): meaning of mist, neut, fora, reag, ion, ionA, ionB.
- **AIMD**: ab initio molecular dynamics (here CP2K, PBE-D3(BJ)/DZVP, on neumann); the quantum reference for the MLMD RDFs.
- **Block error**: standard error from contiguous blocks of frames; a lower bound when blocks are shorter than the correlation time.
- **Census**: count of Al species per frame with the neumann bond criterion (CLAUDE.md, Same model, same census).
- **Chain**: the self-resubmitting sequence of 24 h jobs of one run (`scripts/prep_mlmd.py`): exit 3 of `src/mlmd.py` (budget reached, checkpoint written) submits the next job, up to `--max-chain`.
- **Checkpoint**: `state.json` + `ckpt.traj` of a run dir: positions, momenta, cell, step, RNG state; a resumed run continues exactly where it stopped.
- **Claim**: a statement in `docs/claims.md` with a reading rule fixed before the result.
- **Committee**: models trained alike with different seeds; their disagreement estimates the model's uncertainty. Not used here (ADR-0015).
- **CSVR**: canonical sampling through velocity rescaling (Bussi thermostat); used in Davi's MLMD.
- **Deploy key**: an ssh key with access to one GitHub repo only; one per (repo, machine) (ADR-0012).
- **Free urea**: a urea none of whose N and O atoms is within 2.0 Å of an Al (census radii Al 1.0, N 1.0, O 1.0 Å).
- **Handoff**: a note from another site (neumann, Davi) about what was sent; `docs/handoffs/`.
- **Legacy result**: a result made outside this repo, registered verbatim as `results/legacy-*` (ADR-0008).
- **massive_ou / nve**: stage kinds of `src/mlmd.py`: one Ornstein-Uhlenbeck thermostat per degree of freedom (Davi's massive CSVR), and velocity Verlet without thermostat.
- **MLMD**: molecular dynamics driven by a machine-learned force field (here MACE).
- **N-H spread**: standard deviation of the N-H bond lengths per block of frames (`src/bond_width.py`); a thermometer for the N-H stretches (classical value at 400 K ≈ 0.029 Å from the model's curvature).
- **NPT relaxation**: short NPT stage that only brings the start-box pressure to plausible values; not a measurement (ADR-0016). Superseded by ADR-0019: no NPT stage.
- **Pilot phases**: phase 1 = the first 200 ps of production, exploration, never judged; phase 2 = its extension (`prod2`), judged by the reading rule fixed between the phases (`docs/experiments/pilot-r10-T400.md`).
- **r**: AlCl3:urea molar ratio (r = 1.3: 39 Al per 30 urea in the AIMD seed).
- **rdf-aimd-v1**: the owner's test comparing MLMD and AIMD RDFs (`docs/rdf-references.md`).
- **Reading rule**: question, metric, threshold and yes/no/inconclusive, fixed before the result (ADR-0013).
- **reagentes / ionico**: the two opposite r = 1.0 start boxes: molecular (Al2Cl6 + urea) and fully ionic ([AlCl2(urea)2]+ + AlCl4-).
- **run2r10m0**: the MACE model of this repo (run 2, round 10, committee member 0; `docs/model.md`).
- **Setup check**: a repeat of one of Davi's MLMD with our driver and env, its RDF compared with his (`docs/experiments/setup-check-r10neut-T400.md`).
- **Smoke-bench**: the GPU test job `src/smoke_bench.sbatch`: model and env checks, float32 vs float64, steps/s and GPU peak memory per stage on the 1512-atom box, then the driver's checkpoint/resume on `runs/smoke-driver`.
- **Status block**: the State / Now / Later / Waiting on owner section of `CLAUDE.md` (ADR-0011).
- **Store**: `../alcl3-urea-mlmd-store/{data,runs,logs}`, outside git, reached through the `data`, `runs`, `logs` symlinks.
- **Superseded run**: a prepared or finished run dir replaced by a new protocol, moved to `runs/_superseded/<run>-<commit>-<reason>`, never deleted.
- **Thermostat check**: the test of what cools the N-H stretches under a global Bussi thermostat (`docs/experiments/thermostat-check-r10neut-T400.md`).
- **Training density**: 1.5398 g/cm³ at r = 1.0 (L = 29.729979 Å for 1512 atoms), the density of the training data, of the AIMD and of the v2 boxes; every MLMD stage runs at it (ADR-0019).
- **UA**: LNCC allocation unit: 1 per CPU core-hour, 100 per GPU-hour; the ledger counts a GPU job as cores + GPUs (ADR-0017).
- **Urea proton transfer**: an H moves from an Al-bound urea, which becomes a ureate (3 H, bound to Al through N and O), to the O of a free urea, which becomes a uronium (5 H); H counted with the census radii (N-H, O-H < 1.37 Å). Seen only in starts with free urea (journal 2026-11-28).
