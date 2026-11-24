# Journal

Append-only. Newest entry first, directly below the marker line.
Title: `## YYYY-MM-DD — <machine> — <short title>`.

```
## YYYY-MM-DD — <machine> — <short title>
- Goal: ...
- Done: ... (each item with its commit hash and job ID)
- Results: the conclusion and the few numbers that carry it, linked to the doc
- Decisions: ADRs added or changed (owner approval recorded there)
- Problems: what failed, with job IDs and error lines (root cause)
- Next: concrete steps
```

<!-- NEW ENTRIES BELOW -->
## 2026-11-24 — sdumont — Project start
- Goal: create the MLMD project on SDumont around Davi's model; record the model, the
  reference RDFs and the neumann handoff on the start boxes; tidy the old tree.
- Interview summary (owner, 2026-11-24): MLMD of AlCl3:urea with the ready model, no
  training; dataset and labels are the owner's (neumann), training was Davi's (SDumont);
  MLMD in the owner's SDumont account. Pilot: r = 1.0, 400 K, two opposite starts, NPT
  relaxation then NVT; ASE now, maybe LAMMPS later; no committee. AIMD RDFs: the owner sends
  a directory with all of them when asked.
- Done: repo `alcl3-urea-mlmd` and store `alcl3-urea-mlmd-store` created; machinery copied
  from the lab-template layer on SDumont (mentions of other projects removed); model and
  archive copied to `data/` (sha256 = card); Davi's 30 MLMD RDFs registered as
  `results/legacy-mlmd-rdf-run2r10m0` (61 files, `--check` OK); 20 card figures in
  `data/models/run2r10m0/plots/` (sha256 equal to source); empty folders of
  `alcl3_urea_mlip` removed. Boxes `mlmd-boxes-r1.0-v2.tar.gz` (scp by the owner) copied to
  `data/inbox/` (sha256 = handoff) and extracted to `data/boxes/` (both PDBs = MANIFEST,
  contacts PASS, 1512 atoms each). First commit and push.
- Results: the model loads and evaluates in `mace_env` (mace-torch 0.3.15, torch 2.2.0)
  on CPU (`docs/model.md`); agreement with Davi's numbers not checked. The RDF CSVs in the
  delivery are MLMD, not AIMD (`docs/rdf-references.md`). Slurm survey (facts in
  `configs/machines/sdumont.yaml`): all GPUs V100; assoc limits 4 running jobs on
  `sequana_gpu` (4 days), 3 on `_long` (31 days), 1 on `_dev` (20 min); the owner's 1-GPU
  jobs of November started with a median wait of 0 min (sacct). Login driver 560.35.03
  (CUDA 12.6); torch 2.11.0+cu126 and mace-torch 0.3.16 are downloadable.
- Decisions: ADR-0015 (separate repo, fixed model, no committee, ASE, mace-torch 0.3.16),
  ADR-0016 (short NPT relaxation of 50 ps then NVT; density not a gate; barostat values
  proposed).
- Problems: `ssh -T github-alcl3-urea-mlmd` failed ("Could not resolve hostname"): no
  `Host` block for the alias in `~/.ssh/config`; fixed by the owner.
- Next: env 0.3.16; smoke + benchmark job; MLMD driver; setup check; pilot doc.
