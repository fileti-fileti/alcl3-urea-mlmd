# 0009. One cost ledger file per machine
- Status: Accepted
- Date: 2026-11-13. Decided by: owner (Eudes Fileti). Process: teach-back (owner chose to
  give one).

## Context
The guide has one `results/cost_ledger.csv`. With two machines appending rows on separate
clones, a single file conflicts on merge. Alternatives: one CSV with a `machine` column and
`merge=union` in `.gitattributes`, or one file per machine.

## Decision
`results/cost_ledger_<machine>.csv`, one per machine; `scripts/cost_ledger.py` aggregates
them (e.g. `--jobs` across machines).

## Owner's explanation (verbatim) and agent's check
> "o merge=union pode manter linha velha ou duplicar sem avisar e o custo sai errado;
> arquivo por máquina não tem como dar conflito e cada um fica numa unidade só."

Agent's check: correct and complete.

## Consequences
- Each ledger has a single cost unit; aggregation across machines reports per unit and
  never adds core-hours to SDumont allocation units.
