# 0007. Python environments recorded per machine
- Status: Accepted
- Date: 2026-11-13. Decided by: owner (Eudes Fileti). Process: infrastructure (approval).

## Context
Existing environments are in use by running projects and must not change.
- Mac: miniforge3 `base`.
- neumann: `base` (`/home/eudes/miniforge3`), `analysis`, `deepmd_intel`, prefix env
  `/home/eudes/deepmd-v3`.
- SDumont: shared `mace_env` under `/scratch/acmes/eudes.fileti3/projects/shared/envs/`
  (pinned versions).

## Decision
One `environment.yml` per machine in the repo, as a record only (`conda env export` /
`pip freeze`). Existing envs are never modified; a new env only with the owner's ok.
`scripts/` uses the standard library only.

## Owner's approval and agent's check
Approved by the owner. Agent's justification: a record lets a result be traced to package
versions without the repo owning or rebuilding the env.

## Consequences
- TODO: export the files (later block of setup F5).
