# 0010. Ledger attribution by WorkDir; one shared list of blocked extensions
- Status: Accepted
- Date: 2026-11-13. Decided by: the agent, under the owner's explicit delegation ("choose
  the most conservative default, record it and go on"). Process: infrastructure.

## Context
1. A dry run of `cost_ledger.py add` on neumann picked up every ended job of the user,
   including production jobs of another project. One Slurm account serves
   several projects, so "all jobs of the user" overstates a project's cost.
2. The pre-commit hook and `register_result.py` each had their own idea of forbidden
   files: a small text `.extxyz` was registered and only blocked later, at commit time.

## Decision
1. `cost_ledger.py add` counts a job only if its Slurm `WorkDir` is inside the repo's
   `runs/` (both the link path and the directory it resolves to) or inside a `--workdir`
   given explicitly, or if its ID is passed with `--jobs`. With neither `runs/` nor
   `--workdir`/`--jobs`, it refuses. The ledger stores `workdir` per row.
2. `scripts/blocked_extensions.txt` is the single list of blocked extensions, read by the
   hook and by `register_result.py`. If the file is missing, both refuse (fail closed).

## Approval and agent's check
Delegated by the owner. Agent's justification: both choices err on refusing: a job
submitted from outside `runs/` is left out (visible as "skipped" and addable with
`--jobs`) rather than charged to the wrong project, and a missing list blocks instead of
silently allowing everything.

## Consequences
- Project jobs must be submitted from a directory under `runs/` (as Slurm records the
  submission directory); jobs submitted elsewhere need `--jobs`.
- `/end-session` reports the "skipped" count so missing jobs are noticed.
