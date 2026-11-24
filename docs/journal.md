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
## 2026-11-24 — sdumont — MLMD driver, env rebuild, Davi's area, tests ready
- Goal: env with mace-torch 0.3.16; ASE MLMD driver with checkpoints and self-resubmitting
  jobs; smoke/benchmark and setup check ready to submit; Slurm/GPU survey.
- Done:
  - `b0d96ee`: env recipe (Davi's lock: torch 2.11.0+cu126, mace-torch 0.3.16, ase 3.29.0),
    `python.module` in the machine config, purge and UA facts.
  - Env build job 11758413 (`sequana_cpu_dev`) TIMEOUT at 20 min; partial venv removed;
    rebuild job 11758427 on `sequana_cpu`, 2 h limit.
  - `src/mlmd.py` (stages minimise / nvt Bussi with ramp / npt_berendsen with mean-volume
    rescale; checkpoint + resume; 0.6 Å and non-finite stop), `scripts/prep_mlmd.py` (run dir,
    provenance, 24 h self-resubmitting job), `src/smoke_bench.py` + `.sbatch`,
    `src/rdf_compare.py`; tests for each (70 tests pass with the `mace_env` python, ASE 3.28,
    after fixing one wrong test expectation). Restart test: a run interrupted after every
    chunk ends identical to the uninterrupted one.
  - From Davi's area (owner's ok): `src/rdf_aimd_v1/rdf.py` (sha256 `7c710bba…`, equal to
    the card) and the exact start of his T400 r10_neut MLMD (`data/setup-check/`, sha256
    `2fe053fe…` = his DONE.json).
  - Configs `smoke-driver`, `setup-r10neut-T400`; `docs/experiments/setup-check-r10neut-T400.md`
    (rule fixed before the run) and `pilot-r10-T400.md` (draft, rule pending).
  - Old tree `alcl3_urea_mlip/` deleted (owner's ok; every file had a checked copy).
  - Job 11623564 (`pbA2_rep5`, another project, held since 2026-10-24) cancelled at the
    owner's request.
- Results: Davi's HPC guide (his code snapshot `2ea4809ba93a`, `docs/hpc-guide.md`): GPU
  nodes V100-SXM2-32GB, driver 560.35.03; on compute nodes `/prj` is a link to `/scratch`;
  `/scratch` deletes files unmodified for 60 days; UA = 1 per core-hour, 100 per GPU-hour;
  compute nodes cannot install from PyPI; SDumont2nd is not open to standard projects;
  module `lammps/10Set25_oneapi-2022_cuda12.6` has ML-MACE with libtorch 2.11. Davi's T400
  r10_neut MLMD (job 11750922): 15.33 steps/s, 0.217 h. The 20 AIMD RDFs are also in his
  area (`docs/rdf-references.md`).
- Decisions (owner, 2026-11-24, "OK. pra tudo"): env path, smoke job, NPT values of
  ADR-0016, Slurm scheme (1 V100, `-c 6`, 24 h self-resubmitting segments), reading Davi's
  area, deleting `alcl3_urea_mlip/`. Agent, for a test: the setup-check rule (4 combined
  errors, peak shift ≤ 0.04 Å, T 400 ± 5 K).
- Problems:
  - Env build 11758413: TIMEOUT on `sequana_cpu_dev`, stalled on the large NVIDIA wheels;
    Davi's identical build took 5.5 min (2026-10-20). Slow Lustre I/O suspected, not verified.
  - `/end-session` was not available: this Claude Code session started in `$HOME`, so the
    repo's skills, CLAUDE.md and `.claude/settings.json` were not loaded. End of session done
    by hand, following `.claude/skills/end-session/SKILL.md`.
- Next: open the next session in the repo dir; when 11758427 ends: tests with the venv,
  `prep_mlmd.py configs/mlmd/smoke-driver.json --name smoke-driver`, submit the smoke job;
  then the setup check; owner: the pilot's reading rule.

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
