---
name: recap
description: Plain-language recap of the last sessions - what was asked, run, found and decided, and why - then define every term used. For when the owner feels lost.
disable-model-invocation: true
---

# /recap

Read-only. Never invent a hash, job ID or number; write `unknown`.

1. Read the newest 3 entries of `docs/journal.md` (or the number the owner gives), the
   status block in `CLAUDE.md`, the ADRs and claims those entries name, and
   `git log --oneline -20`.
2. Tell the story in Portuguese, plain language, oldest to newest: what was asked, what
   was run (job IDs), what was found (numbers only from claims or registered results),
   what was decided and why (cite the ADR), what failed and the root cause.
3. Then a list "Termos" defining every technical term or acronym you used, one line each,
   using `docs/glossary.md` when it has the term.
4. End with where things stand now (status block State) and its Now tasks.
