# 0005. Cost accounting and ask-first limits
- Status: Accepted (partial)
- Date: 2026-11-13. Decided by: owner (Eudes Fileti). Process: infrastructure (approval).

## Context
neumann is the owner's own cluster: cost is queue time and opportunity, measured in
core-hours. SDumont charges an allocation in a unit whose conversion from `sacct` is not
known yet.

## Decision
- neumann: core-hours from `sacct` (elapsed × allocated CPUs).
- SDumont: TODO(owner): allocation unit, conversion from `sacct`, balance command.
- Ask-first limits per machine: deferred by the owner. Until set, the agent asks before
  submitting or cancelling **any** job.

## Owner's approval and agent's check
Approved by the owner (limits explicitly deferred). Agent's justification: core-hours are
the only unit verifiable on neumann today; asking for every job is the conservative default.

## Consequences
- `cost_ledger.py` records raw `sacct` fields and the estimate; the SDumont estimate column
  stays `unknown` until the unit is known.
- A new ADR supersedes this one when limits and the SDumont unit are fixed.
