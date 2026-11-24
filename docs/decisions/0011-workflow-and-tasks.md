# 0011. Session and task workflow; tasks live in the status block
- Status: Accepted
- Date: 2026-11-13. Decided by: owner (Eudes Fileti), proposed by the agent.
  Process: infrastructure (ADR-0001).

## Context
The guide defines the session routines and the record files, but no place for pending
work. The status block already carried "Next" and "Waiting on owner" lines, and
`/start-session` reports under Now / Later / Waiting on owner. A separate task file would
be a second source of truth that drifts from the status block.

## Decision
- Tasks live only in the `CLAUDE.md` status block, in fixed fields, in this order:
  `Updated: YYYY-MM-DD — <machine>`, `State`, `Now`, `Later`, `Waiting on owner`, then one
  `Last sync — <machine>` line per machine. One line per task.
- A task that ends leaves the block; it is recorded in that session's journal entry
  (Done or Problems). The block holds no history.
- The session loop and the task loop are written in `CLAUDE.md`, section Workflow.
- Skills stay the guide's three (`/start-session`, `/end-session`, `/recap`). New
  experiments and projects follow `docs/experiment-template.md` and `docs/new-project.md`.

## Owner's explanation (verbatim) or approval, and agent's check
- Approved by the owner, 2026-11-13: chose "status block" for tasks and "only the guide's
  three skills".
- Agent's justification: one place answers "what now?", and `/start-session` already reads
  it; the journal keeps the history, so nothing is lost when a task leaves the block.

## Consequences
- `/end-session` rewrites Now / Later / Waiting on owner every session; `/start-session`
  checks the Now tasks against git and the queue.
- If Later grows into a long backlog, revisit with a new ADR.
