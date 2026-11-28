# CLAUDE.md — alcl3-urea-mlmd

Instructions for the agent working in this repo. Personal preferences (tone, name, execution
habits) live in `~/.claude/CLAUDE.md`, not here. This file holds project rules and
conventions only. Keep it under ~160 lines; history goes to `docs/journal.md`.

## Project
- **alcl3-urea-mlmd**: MLMD of AlCl3:urea liquids on SDumont with a ready MACE model, for
  the Al speciation in 1512-atom boxes at r = 1.0, 1.3, 1.5 (r = AlCl3:urea molar ratio);
  equilibrium is judged by two opposite starts (molecular, ionic) reaching the same
  speciation (owner, 2026-11-24); neutral start added 2026-11-28; target temperature 333 K
  (ADR-0020). TODO(owner): confirm this as the research question.
  Out of scope: dataset generation, DFT labelling, training.
- Three sites (ADR-0015):
  - neumann, project `alcl3-urea` (owner): AIMD, dataset and its DFT labels, MLMD start
    boxes, species census (`extract_species.py`), AIMD RDFs.
  - SDumont, account `davi.fileti` (Davi): calibration and training of the model (done).
  - SDumont, this account: MLMD (pilot, production) and its analysis. This repo.
  Files from neumann arrive through the owner (one VPN at a time): `data/inbox/` + sha256.
- Model (fixed, ADR-0015): `run2r10m0`, `data/models/run2r10m0/alcl3_urea_run2_r10_m0.model`,
  sha256 `ff0e4578…6e3a` (full hash and card: `docs/model.md`). Energies and forces only,
  no stress: NPT only as a short pressure relaxation, never for production (ADR-0016).
- Start boxes (r = 1.0, 1512 atoms): `data/boxes/mlmd-boxes-r1.0-v2/` (reagentes, ionico;
  sha256 checked 2026-11-24) and `data/boxes/mlmd-boxes-r1.0-neutro-v2/` (neutro; 2026-11-28);
  handoffs in `docs/handoffs/`. Use
  L = 29.729979 Å, not the rounded CRYST1. Never the v1 boxes (`08_mlmd_boxes`).
- Quality references (AIMD RDFs, the model's own MLMD RDFs): `docs/rdf-references.md`.
- Engine: ASE + mace-torch 0.3.16 in a dedicated env (to create; ADR-0015), `mace_env`
  (0.3.15) as fallback; LAMMPS may come later (new ADR).
- Legacy (read-only, ADR-0008): `/scratch/acmes/eudes.fileti3/projects/alcl3_urea_data`
  (CP2K inputs of the AIMD batch run on SDumont; trajectories moved to neumann).
- Unpublished work: private repo; data and results stay on the owner's machines.
- Machinery (scripts, hook, skills, ADRs 0001–0014) copied from the owner's lab-template
  layer on SDumont, 2026-11-24; no `template` remote yet (ADR-0012).

## Hard rules
- **Never fabricate** numbers, paths, versions, parameters, job IDs, hashes or references.
  Unknown → `TODO(owner): <question>`, and list it in the report.
- **Fix the reading rule first** (ADR-0013). Before the output of a run whose result will
  support a claim or a comparison is analysed, its experiment doc
  (`docs/experiments/<name>.md`) fixes the question, the census quantity, the convergence
  criterion, the error, the maximum length and what counts as yes, no or inconclusive, and
  `docs/claims.md` gets a *pending* claim with that rule. The rule is never changed after
  the results are seen; a changed rule makes a new claim.
  Benchmarks, tests and toy jobs are exempt (still ask-first).
- **Decisions** (ADR-0013, no teach-back): the agent proposes in 2–3 lines (what and why);
  the owner answers "ok" or "approved"; the record keeps that answer and the agent's
  justification. An ADR only for general choices (physics, simulation protocol, analysis
  method, infrastructure); experiment choices go in the experiment doc, small ones in the
  journal entry (Decisions).
- **Ask first before:** submitting or cancelling **any** job, `salloc`/`srun` (until
  per-machine limits are set, ADR-0005); deleting or overwriting files the agent did not
  create; force-push; `sudo` or any system-wide change; anything outside the repo.
  Existing work directories (`alcl3_urea_data`, the owner's other projects) are **read-only**.
- **Secrets:** never ask for or write passwords, passphrases, tokens, VPN credentials or keys.
  Give the owner the command; the owner types it.
- **Explain commands:** git, SSH, VS Code and Claude Code commands get one line (what and
  why). Shell and Slurm: no explanation unless unusual.
- **Same model, same census:** every run uses the model of ADR-0015 and checks its sha256
  at start. The species census uses the neumann criterion only, so results compare with
  the AIMD: bond if d < r_i + r_j with r = Al 1.0, Cl 1.7, O 1.0, N 1.0, C 1.0, H 0.37 Å;
  Cl bonds only to Al (`extract_species.py`, SI S2.2).
- **Periodic cell always:** xyz/PDB structures get cell, `pbc=True` and wrap before the
  calculator is attached (without a cell the energies are those of a cluster in vacuum).
- **Style:** simplest design, surgical changes, a check for every step (then run it). Show
  the diff before editing an existing file.

## Workflow
**Session loop**: `/start-session` (read-only recap, fast-forward pull) → work the *Now*
tasks → `/end-session` (journal, status, ledger, results, commit, push). Skills in
`.claude/skills/`; their facts come from `python3 scripts/session_facts.py`.

**Tasks** live only in the status block (ADR-0011): *Now* (this session), *Later*
(backlog), *Waiting on owner* (blocked on the owner's decision or a fact). One line each.
A finished task leaves the block and goes to the journal entry (Done or Problems).

**Task loop** — every step has a check; run it and report its output:
1. Decision involved? Propose it in 2–3 lines; apply only after the owner's "ok"
   (ADR-0013); a general choice gets its ADR before it is applied.
2. Run that will support a claim or comparison? Copy `docs/experiment-template.md` to
   `docs/experiments/`, fix the reading rule and add the *pending* claim before anything runs.
3. Job? Ask first; submit from a dir under `runs/`, clean tree, commit recorded.
4. Ended? At `/end-session`: register results, apply the fixed rule to the claim, cost
   from the ledger.

## Machines
- Runs on SDumont. `origin` = private GitHub repo `fileti-fileti/alcl3-urea-mlmd`
  (ADR-0012), ssh alias `github-alcl3-urea-mlmd` (deploy key of this repo and machine):
  pull at `/start-session`, push at `/end-session`.
- Clone and store in `/scratch/acmes/eudes.fileti3/projects/` (ADR-0014). `/scratch` deletes
  files unmodified for 60 days, no backup; on compute nodes `/prj` is a link to `/scratch`
  (`$HOME` files invisible to jobs). Both from Davi's HPC guide (2026-10). Anything
  irreplaceable also lives elsewhere; envs are rebuilt from `envs/`.
- Cost: UA = 1 per CPU core-hour, 100 per GPU-hour (LNCC manual via Davi's guide): one V100
  for a day ≈ 2400 UA. Compute nodes cannot install from the internet: wheels come from the
  login node.
- Machine facts (paths, partitions, modules, envs, cost unit) live in
  `configs/machines/<machine>.yaml`, never hard-coded; `unknown` = unverified, never guessed
  (`scripts/machine_config.py detect|show|validate`). `neumann.yaml` serves the tests only.
- `scripts/`: Python standard library only, Python >= 3.6, never the active conda env.
  `src/` and its tests run with the MLMD venv: `module load python/3.10.16_sequana; unset
  PYTHONPATH; <venv>/bin/python -I ...` (venv path and module in `sdumont.yaml`).
- MLMD jobs: `scripts/prep_mlmd.py <config> --name <run>` writes `runs/<run>/` (run.json +
  self-resubmitting `job.sbatch`: 1 V100, `-c 6`, 24 h segments, checkpoint at the budget,
  `--exclude=sdumont8042`); driver `src/mlmd.py` (exit 0 done, 3 resubmit, 4 stopped).
- SDumont: the login node limits CPU time per process (`ulimit -t 1800`); heavy interactive
  work goes to `salloc`/`srun` on a `*_dev` partition. TODO(owner): confirm usage policy.

## Conventions
- **Journal** (`docs/journal.md`): append-only, newest first, below the marker line.
  Title: `## YYYY-MM-DD — <machine> — <short title>`; fields Goal / Done (commit hashes, job
  IDs) / Results / Decisions / Problems / Next.
- **ADRs** (`docs/decisions/NNNN-title.md`): Context → Decision (who, date) → owner's
  explanation or approval + agent's check → Consequences. Never edit an accepted ADR;
  supersede it (linked both ways). Index and template: `docs/decisions/README.md`.
- **Claims** (`docs/claims.md`): status final / provisional / pending (+ "negative").
  A number not in a claim is not stated.
- **Results** (`results/<name>/`): verbatim copies + `PROVENANCE.json`, via
  `scripts/register_result.py`; never hand-edited. Legacy results enter as `legacy-*`
  (ADR-0008). Binary files (figures) stay in the store, with `SHA256SUMS`.
- **Inputs from outside** (model, boxes, AIMD RDFs): `data/inbox/` as received, sha256
  recorded and checked against the sender's; then extracted read-only under `data/`.
- **Runs**: `runs/<experiment>-r<NN>-T<T>-<start>` (e.g. `runs/pilot-r10-T400-reag`);
  each records the exact commit (`git rev-parse HEAD`) and refuses a dirty tree.
- **Cost**: `results/cost_ledger_sdumont.csv`, appended by `scripts/cost_ledger.py` from
  scheduler accounting; failed and cancelled jobs count. Only jobs submitted under `runs/`
  (or given with `--jobs`) are charged to the project (ADR-0005, ADR-0009, ADR-0010).
- **Never in git**: `data/`, `runs/`, `logs/` (gitignored; symlinks to the store),
  extensions in `scripts/blocked_extensions.txt` (models, archives, trajectories, ...),
  files > 1 MiB. Enforced by `.githooks/pre-commit` → `scripts/check_staged_files.sh`.
- Docs in English; chat with the owner in Portuguese (ADR-0006).
- Commit messages: `<type>: <summary>` (feat, fix, docs, chore, test).

## Where things live
| Question | Place |
|---|---|
| What is true now? What next? | status block below (Now / Later / Waiting on owner) |
| What happened? | `docs/journal.md` |
| Why is it built this way? | `docs/decisions/` |
| What can we state? | `docs/claims.md` |
| Which model, with which limits? | `docs/model.md` |
| Reference RDFs for the model's quality? | `docs/rdf-references.md` |
| What arrived from neumann or Davi? | `docs/handoffs/`, `data/inbox/` |
| What is it based on? | `results/<name>/` |
| What did it cost? | `results/cost_ledger_sdumont.csv` |
| What does this word mean? | `docs/glossary.md` |
| Machine facts | `configs/machines/<machine>.yaml` |
| Python envs (record only) | `envs/sdumont.environment.yml` |
| Agent permissions | `.claude/settings.json` (ask: jobs, push; deny: force-push, `rm -rf`, edits in `results/`) |

## New clone checklist
1. `git config core.hooksPath .githooks` (turns on the pre-commit hook; per clone).
2. Create the `data`, `runs`, `logs` symlinks to `../alcl3-urea-mlmd-store/{data,runs,logs}`.
3. Run the tests: `python3 -I -m unittest discover -s tests` (stdlib only).
4. `python3 scripts/machine_config.py detect` prints this machine's name.

## Status
<!-- BEGIN STATUS -->
- Updated: 2026-11-28 — sdumont
- State: on SDumont and GitHub; model run2r10m0 (exploration only since ADR-0020: target 333 K,
  training to be reformulated); boxes v2 + neutro; env `mace0316_env`; engine ASE; `massive_ou`
  NVT at 1.5398 g/cm³ (ADR-0018/0019); pilot 400 K: reag and ion done, neutro job 11761928 pending
  (commit 984537c); `src/urea_scan.py` (results `urea-scan-2026-11-28`); no claims.
- Now (SDumont):
  - Neutro job 11761928: at start, model sha256 and `eq` end; at the end, urea scan of its prod (no transfer expected without free urea), ledger, energy against reag and ion.
  - Item 2 of ADR-0020 (333 K weight in training): the owner's and Davi's choices, then the request to Davi.
- Later:
  - Hybrid-functional check of the proton-transfer energy (neumann; ADR-0020 item 2): draft the request.
  - 333 K equilibration protocol (experiment doc) once the new model exists; reading rule + ID-1 after it.
  - `docs/model.md`: 1.5398 g/cm³ is extrapolated (Carrasco-Busturia 2021 from Liu et al. 2017), not measured (diff first).
  - `bond_width.py`: report pairs beyond the cut apart and the std of intact pairs (+ test).
  - Census: `extract_species.py` (sha256) into `src/` + a test reproducing a neumann census on one AIMD frame.
  - Backup of the model, boxes and setup-check start outside `/scratch` (60-day purge).
  - 450 K AIMD for the ion/ionA/ionB/mist seeds (optional, factorial design).
  - Production matrix at 333 K (r = 1.0, 1.3, 1.5; starts); GROMACS NNPot once the collaborator's numbers arrive.
- Waiting on owner:
  - Send `docs/handoffs/2026-11-28-request-neumann-aimd-333K.md` to neumann; cost of one AIMD and of one 1000 Ry label.
  - Item 2 choices: label ratio 333:400:450 (proposal 2:1:1), frames per 333 K AIMD (~20), loss weights (proposal no), acceptance limits per category at 333 K, retrain from scratch (proposal) or fine-tune.
  - Experiments at 333 K for the paper (speciation: Raman, NMR?); is r = 1.0 liquid at room temperature?
  - Committee check (`m1/m2_stagetwo` vs m0): ADR-0015 says "no committee"; ok for an ADR allowing one-off diagnostics?
  - Globs for the setup check, thermostat check, LAMMPS benchmark and the first phase-1 files ADR-0019 cites.
  - ADR-0019 TODO: DFT stress on a few AIMD frames (neumann).
  - `~/.bashrc` lines 97–102 (`mace_env/lib` first in `LD_LIBRARY_PATH`) break the venv on the login node: scope them to LAMMPS?
  - GROMACS NNPot from the collaborator: model (MACE? size), atoms, GPU, ns/day; export script/wrapper; version and build recipe.
  - `extract_species.py` from neumann (`git ls-files` in alcl3-urea finds it); does it classify ureate and uronium?
  - Backup location outside `/scratch` (e.g. `$HOME`): ok to copy ~20 MB there.
  - UA of GPU jobs: does LNCC bill the CPU cores on top of the GPU? (ADR-0017 counts both until known.)
- Last sync — sdumont: 2026-11-28, end-of-session commit on top of 5881c32
<!-- END STATUS -->
