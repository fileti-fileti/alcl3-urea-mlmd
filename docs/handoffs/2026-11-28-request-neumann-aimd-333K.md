# Request to neumann (alcl3-urea), 2026-11-28 — AIMD at 333 K for the seeds missing there

Outgoing request, drafted by the agent and approved by the owner on 2026-11-28 (ADR-0020); the
owner carries it to neumann. Kept verbatim below the line.

---

Request from alcl3-urea-mlmd (SDumont), 2026-11-28 — AIMD at 333 K for the seeds missing there

## Why
- Owner's decision (2026-11-28): 333 K is the target temperature of the project, and the training
  set must cover it with priority.
- Gap: at 333 K only the ion/ionA/ionB/mist seeds were run (dataset report, section 2.4). No seed with
  free urea (reag, fora) or with neutral adducts (neut) has AIMD at 333 K, so neither the AIMD nor the
  active-learning frames contain those chemistries at 333 K (0 frames with >= 2 free ureas at 333 K).
- These chemistries matter: in every reag start at 400 and 450 K, both the AIMD and the MLMD show
  proton transfer from an Al-bound urea to the O of a free urea (ureate, 3 H + uronium, 5 H).

## What to run
Seven AIMD at 333 K, the seeds that have 400/450 K runs but no 333 K run:
  r10_reag, r10_neut, r10_fora, r13_reag, r13_neut, r15_reag, r15_neut

## How (identical to the existing T333 runs; change nothing else)
- Inputs: copy T333/r10_ion/equil.inp and prod.inp of dataset_AlCl3urea_AIMD; change only the project
  name, the coordinates and, for r13/r15, the box.
- CP2K, PBE + D3(BJ), DZVP-MOLOPT-SR-GTH / GTH-PBE, CUTOFF 350 Ry, REL_CUTOFF 50, EPS_SCF 1e-6, OT DIIS.
- NVT 333 K, dt 0.5 fs. Equilibration 2000 steps, CSVR MASSIVE, TIMECON 10 fs. Production 10000 steps
  (5 ps), CSVR GLOBAL, TIMECON 100 fs. Trajectory every 10 steps; restart every 50 steps.
- Box (cubic, the 333 K density, as for every existing run): r10 L = 19.581168 A, r13 L = 19.487537 A,
  r15 L = 20.550878 A.
- Start: the same init.xyz as the 400/450 K runs of each seed (last frame of its 01_geo GEO_OPT);
  check that it is byte-identical to T400/<seed>/init.xyz (sha256).
- r13_reag: its init.xyz already holds one ureate/uronium pair, formed at step 201 of the GEO_OPT.
  Owner's decision (2026-11-28): use it as it is, for consistency with the 400/450 K runs.

## Deliver (same layout and treatment as dataset_AlCl3urea_AIMD)
- T333/<seed>/: init.xyz, equil.inp, prod.inp, eq_pos.xyz (201 frames), prod_pos.xyz (1001 frames),
  eq.ener, prod.ener, prod_final.restart. Pieces joined in order; equilibration cut at 2000 steps.
- Checks as in section 5.1 of the report: contiguous steps every 10, constant atom count, finite
  coordinates, 201 + 1001 frames. Also report the mean T of the production and the drift of the
  conserved quantity.
- Census with extract_species.py on the production frames (species fractions), and say whether any
  urea has 3 or 5 H (H bonded to N or O, d < 1.37 A).
- New manifest rows (same columns as manifest.csv), a tarball with its sha256, a handoff note with
  the commit of alcl3-urea used. Expected cost on neumann: TODO(owner).

## Not in this request
- DFT labels (1000 Ry single points) on selected frames: a later request, after the frame selection.
- Any change of level of theory, density, box or protocol.
- A hybrid-functional check of the proton-transfer energy (ADR-0020, item 2): a separate request.
