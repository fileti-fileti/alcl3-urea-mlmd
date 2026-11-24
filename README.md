# alcl3-urea-mlmd

MLMD of AlCl3:urea on SDumont with the MACE model `run2r10m0`. Private, unpublished.

Start with `CLAUDE.md` (project, rules, status), then `docs/model.md`,
`docs/rdf-references.md` and the newest entry of `docs/journal.md`.

```
CLAUDE.md                 rules + status block
configs/machines/         machine facts (sdumont.yaml)
docs/                     journal, claims, glossary, model card, RDF references
docs/decisions/           ADRs
docs/experiments/         one doc per experiment, reading rule fixed before the run
docs/handoffs/            notes received from neumann / Davi
envs/                     record of the conda env used (mace_env)
scripts/                  stdlib tools: machine config, cost ledger, result registration
src/  tests/              analysis and MD code, with tests
results/                  registered evidence (verbatim + PROVENANCE.json)
data runs logs -> ../alcl3-urea-mlmd-store/   large files, never in git
```
