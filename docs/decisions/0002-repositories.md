# 0002. Template repo plus one repo per project
- Status: Accepted
- Date: 2026-11-13. Decided by: owner (Eudes Fileti). Process: infrastructure (approval).

## Context
Several projects share the same machinery: hook, scripts,
skills, machine configs. A monorepo would mix unrelated histories and claims.

## Decision
`lab-template` holds the machinery only. A throwaway `sandbox` repo, created from it,
validates the setup with a toy run. Each research project then gets its own repo created
from the template. "Repo on each machine" means clones of the same repo.

## Owner's approval and agent's check
Approved by the owner. Agent's justification: one repo per project keeps claims, ledgers and
journals separable for each paper; the template avoids copying fixes by hand.

## Consequences
- Fixes to the machinery are made in the template and brought into projects deliberately
  (TODO(owner): procedure, e.g. `git remote add template` + merge; decide when a project exists).
- `sandbox` may be deleted only with the owner's explicit ok.
