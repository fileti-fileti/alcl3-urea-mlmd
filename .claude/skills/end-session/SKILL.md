---
name: end-session
description: End a work session - journal entry, new status block, cost ledger, result registration and claims, glossary, then commit and push.
disable-model-invocation: true
---

# /end-session

Never invent a hash, job ID or number; write `unknown`. Copy numbers from command output
or registered files only.

1. Run `python3 scripts/session_facts.py` and `git log --oneline` since the last
   end-of-session commit (`git log --grep 'end-of-session log' -1`).
2. Cost: `python3 scripts/cost_ledger.py add` (machine and unit come from
   `configs/machines/`). With an empty ledger add `--since <date of the first journal
   entry>`. Report rows added and the "outside the project skipped" count;
   if a project job was skipped (submitted outside `runs/`), ask the owner and add it with
   `--jobs`. No `runs/` in the repo (the template): skip this step and say so.
3. Results: for each experiment that ended this session, ask the owner which run dir and
   globs to register, then `python3 scripts/register_result.py <name> <run_dir> '<glob>'`
   and `--check <name>`. Update its claim in `docs/claims.md` only by applying the rule
   fixed before the run; numbers come from the registered files.
4. Glossary: add one line per new project term used this session.
5. Journal: insert at the top of `docs/journal.md`, right below the marker line:
   `## YYYY-MM-DD — <machine> — <short title>` with Goal / Done (commit hashes, job IDs) /
   Results / Decisions / Problems (job IDs, error lines, root cause) / Next.
6. Status block: replace everything between the STATUS markers with the current state
   only, in these fields (ADR-0011): `Updated: YYYY-MM-DD — <machine>`, `State`, `Now`,
   `Later`, `Waiting on owner`, then one `Last sync — <machine>` line per machine.
   One line per task; tasks finished this session leave Now/Later (they are in the
   journal entry). Update this machine's Last sync line to `YYYY-MM-DD, end-of-session
   commit on top of <short hash of HEAD before this commit>`; leave other machines' lines
   as they are.
7. Show the diffs (`git diff`), run `python3 -I -m unittest discover -s tests`, then
   commit as `docs: end-of-session log YYYY-MM-DD` and `git push origin main` (asks).
8. Say what the owner must do next on the other machine (its `/start-session` pulls
   from `origin`).
