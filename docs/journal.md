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
## 2026-11-27 — sdumont — First phase 1 superseded (NPT expanded the boxes), ADR-0019 NVT, rerun submitted
- Goal: read the first pilot phase 1 and continue the pilot.
- Done:
  - First phase 1, jobs 11759186 (reag) and 11759187 (ion): COMPLETED, exit 0, all stages
    done, no STOPPED. Ledger 1646.5333 + 1624.3028 UA (`45ca01d`).
  - ADR-0019 (NVT at 1.5398 g/cm³, no NPT) supersedes ADR-0016 and the NPT stage of
    ADR-0018. Configs `pilot-r10-T400-nvt-{reag,ion}.json`; the first phase-1 run dirs
    moved to `runs/_superseded/` (`45ca01d`).
  - Phase-1 rerun prepared at `45ca01d` and submitted 2026-11-27 03:48: jobs 11760903
    (reag), 11760904 (ion), PENDING (Priority), Slurm start estimate 2026-11-28 07:35.
    Run records checked this session: commit, config, box (`MANIFEST.csv`) and model sha256
    match; stages min / eq / prod, all at L = 29.729979 Å.
  - This log: the 03:47 session ended without `/end-session`.
- Results:
  - First phase 1 (exploration, not judged; pilot doc, First phase 1): `eq` pressure at
    1.5398 g/cm³ 6.4 ± 1.1 kbar (reag), 5.9 ± 1.2 kbar (ion); the NPT took the boxes to
    1.0869 g/cm³ (reag, still falling) and 1.2365 g/cm³ (ion), mean of the last 25 ps. Two
    volumes, two states: the pilot question is ill-posed on these runs (ADR-0019).
  - Rerun length estimate: ≈ 13.8–14.0 h per start, one 24 h segment, no resubmission.
    Rate from the first phase-1 `eq` stage at the same density: 8000 steps in 969 s (reag)
    and 984 s (ion), 8.26 and 8.13 steps/s. End ≈ 2026-11-28 21:30 if the start estimate
    holds.
- Decisions:
  - ADR-0019 (owner, 2026-11-27: "ok, vamos seguir sua recomendacao").
  - Rerun submission: the owner's ok was given in the 03:47 session; its wording was not
    recorded. Owner in this session: "submetemos nova rodada de jobs ... Estao submetidos".
- Problems:
  - The 03:47 session ended without `/end-session`: `45ca01d` unpushed, no journal entry,
    status block and pilot doc stale ("Rerun: not yet submitted"). Fixed by this log.
  - First phase-1 dirs moved to `runs/_superseded/pilot-r10-T400-{reag,ion}/` without the
    `-<commit>-<reason>` suffix of the glossary convention; left as is (ADR-0019 and the
    pilot doc cite these paths).
  - `bond_width.py` not run on the first phase-1 frames (superseded); it moves to the rerun.
- Next: when the rerun starts, the model sha256 line in `mlmd.log`; then the `eq` end
  (temperature, no STOPPED), production, `bond_width.py` on the prod frames, ledger at the
  end; then the reading rule for phase 2.

## 2026-11-25 — sdumont — Setup accepted, LAMMPS no, ADR-0018, pilot phase 1 submitted
- Goal: close the setup and thermostat checks, decide the engine, start the pilot.
- Done:
  - Thermostat check D (job 11758822) entered in the ledger (41.9583 UA) and its doc.
  - Setup-check repeat on run A (RDF `r10_neut.T400.mlmd-setupcheck-v2`); `f7051c5`.
  - LAMMPS benchmark: model converted with `mace_env` (sha256 f64 `2eb828f8…`, f32
    `22728c15…`); login-node CPU single point equal to ASE within 1.5e-12 eV/atom;
    `src/lammps_bench.py` (+3 tests), `src/lammps_bench.sbatch`, doc with its rule
    (`f7051c5`). Job 11759180 failed (all `lmp` rc 127: `libcudart.so.11.0` not found);
    fixed in `f78bc43` (CUDA 11 runtime path, recorded in `sdumont.yaml`); job 11759182
    COMPLETED. Ledger 4.6522 + 20.1694 UA.
  - `0577a54`: ADR-0018 and configs `pilot-r10-T400-ou-{reag,ion}.json`; the Bussi runs
    prepared at `3540181` moved to `runs/_superseded/`; pilot phase 1 submitted: jobs
    11759186 (reag), 11759187 (ion), running since about 05:59.
  - 82 tests OK with the venv.
- Results:
  - Setup check v2: **FAIL** by its rule (N-H passes; Al-Al and Cl-H peak positions, C-O
    4.10 errors, mean T 405.07 K fail); accepted by the owner.
  - LAMMPS benchmark: **no** (`runs/lammps-bench/report.json`): 1.848 / 2.042 steps/s in
    f64 / f32 against ASE 6.130 / 8.934; energies and forces match (1.7e-12 eV/atom,
    8.5e-11 eV/Å).
- Decisions (owner, 2026-11-25):
  - Run A as the setup-check repeat ("segue"); setup accepted despite its fail ("Aceita
    já"), recorded in the setup-check doc with the agent's justification.
  - LAMMPS benchmark with the 2× limit ("OK"), and its rerun after the library fix ("ok").
  - Engine stays ASE; thermostat `massive_ou` for equilibration and production (ADR-0018:
    "sigamos então com ASE e vamos submeter os dois inícios").
  - GROMACS NNPot (owner's collaborator): the agent read the nightly docs (2027.0-dev):
    full-system NN and pair lists exist, no MACE wrapper, the 2027 I/O format breaks older
    exports, not built on SDumont; evaluated in parallel for production once the
    collaborator sends numbers and the wrapper.
- Problems:
  - Job 11759180: compute nodes do not read `$HOME`, hence not the profile that adds the
    CUDA 11 runtime used by the own LAMMPS build.
  - Results of the three checks not registered: the owner has not named the globs.
- Next: check the pilot's `eq` end (log, temperature, no STOPPED), then NPT volume and
  production; N-H spread on phase-1 frames; register the checks once the globs are named.

## 2026-11-24 — sdumont — Setup-check fail diagnosed; thermostat check inconclusive (A holds)
- Goal: find the cause of the setup-check fail before the pilot.
- Done:
  - Push of `252340d`, `3540181`, `f669c2c` (the previous session's push had not run).
  - Diagnosis, read-only (session scratchpad scripts; Davi's run dir read, not changed):
    same `init.xyz` potential energy in both runs (−89435.083640 vs −89435.083638 eV);
    model N-H curvature 40.5–41.9 eV/Å² in four frames, expected spread at 400 K
    0.0289–0.0294 Å; Davi's driver (`aimd_replay.py`, `f2b50475cb51`) uses the same
    `ase.md.bussi.Bussi` + `FixCom` in production; AIMD N-H peak 111.2 between Davi's MLMD
    104.8 and ours 118.7 (owner's ok to read Davi's AIMD RDF copy).
  - `9e87a3f`: stage kinds `massive_ou` and `nve` in `src/mlmd.py` (+3 tests),
    `src/bond_width.py` (+2 tests), thermostat check doc with its rule and 4 configs;
    79 tests OK with the venv.
  - Thermostat check jobs 11758819 (A, Bussi), 11758820 (B, NVE), 11758821 (C, massive_ou):
    COMPLETED 0:0, 871–903 s; ledger 25.6461 + 26.5000 + 26.5883 UA. Job 11758822 (D,
    Bussi at 0.25 fs) running at the end of the session.
- Results: thermostat check **inconclusive** by its fixed rule: A holds (last-ps N-H spread
  0.0280 Å ≥ 0.0275), B 0.0304, C 0.0293; all starts 0.0296 Å
  (`docs/experiments/thermostat-check-r10neut-T400.md`). Davi's cooling is not reproduced;
  with his equilibration, our global-Bussi production keeps the expected spread.
- Decisions (owner, 2026-11-24, "ok para tudo"): push; thermostat check A–D with the two new
  stage kinds; reading Davi's AIMD RDF copy.
- Problems:
  - In this interactive shell `LD_LIBRARY_PATH` starts with `mace_env/lib` (from the profile)
    and `module load` is unavailable, so the venv's python loaded conda's libpython and
    `import mace` failed (pandas/platform). Fix used: `env -i HOME=$HOME USER=$USER TERM=dumb
    bash -l -c "module purge; module load python/3.10.16_sequana; ..."`. Jobs are not
    affected (`--export=NONE`, `module purge`).
  - Writes to the session scratchpad fail from that clean login shell; outputs went to the
    run dirs.
  - A's N-H spread dips to 0.0265 Å in block 3 and returns: 1 ps block values fluctuate more
    than the rule's threshold assumed. B (NVE) heats to 467.84 K mean as the start relaxes:
    a weaker control than planned.
- Next: owner's ok on run A as the setup-check repeat (RDF + `rdf_compare.py`, the
  setup-check rule); D's numbers; the pilot's equilibration thermostat (proposal:
  `massive_ou` for the ramp); register both checks' outputs.

## 2026-11-24 — sdumont — Smoke passes, setup check fails, pilot phase 1 prepared
- Goal: read the smoke + bench; run the setup check; set up the pilot's first 200 ps.
- Done:
  - Smoke + bench job 11758464 (`sequana_gpu_dev`, sdumont8090, 368 s, COMPLETED 0:0):
    all 5 checks true; driver rc 3 then 0; GPU peak 4.72 GB (float64) and 2.38 GB
    (float32); NVT 6.13 / 8.93 steps/s (float64 / float32) = 0.265 / 0.386 ns/day at
    0.5 fs; NPT 3.19 / 4.66 steps/s; float32 − float64: ΔE −0.80 / −0.78 meV/atom
    (reagentes / ionico), max |ΔF| 1.4e-4 eV/Å. Ledger: 10.8356 UA.
  - `252340d`: `scripts/prep_mlmd.py` accepts upper case in run names (`T400`, the
    CLAUDE.md convention); test `test_run_name`.
  - Setup check job 11758552 (`sequana_gpu`, sdumont8053, 14 min 05 s, COMPLETED 0:0) from
    `runs/setup-r10neut-T400/` at `252340d`; RDF (`rdf.py`, sha256 `7c710bba…`) and
    `rdf_compare.py` run. Ledger: 24.8806 UA.
  - `3540181`: pilot phase 1 (configs `configs/mlmd/pilot-r10-T400-{reag,ion}.json`, doc
    updated, ADR-0016 barostat accepted), test `test_extend_after_done_equals_planned`;
    74 tests OK with the venv. `runs/pilot-r10-T400-{reag,ion}/` prepared at `3540181`,
    not submitted.
- Results: setup check **FAIL** by its fixed rule
  (`docs/experiments/setup-check-r10neut-T400.md`): N-H g at the peak +13.9 on 104.8
  (8.1 errors), Cl-H peak −0.06 Å, production mean T 394.69 K (rule: 400 ± 5 K); the other
  8 pairs pass.
- Decisions (owner, 2026-11-24, "ok"):
  - Pilot in two phases: phase 1 = 200 ps of production, exploration, never judged; it
    sizes the reading rule; phase 2 = the extension, judged; rule and pending claim ID-1
    fixed between the phases. Owner asked for 200 ps first ("não faça um teste inicial com
    1ns ... 200ps"), generous frames and a possible extension; agent's justification:
    deciding the use of data after seeing them breaks ADR-0013.
  - Pilot dtype float32: max |ΔF| about 200× below the model's test force error
    (31.7 meV/Å), 1.46× faster. Both starts. Frames every 10 fs in production.
  - Ramp and minimiser values of the pilot draft; Berendsen parameters of ADR-0016
    (status line updated).
  - Run-name fix in `prep_mlmd.py`.
- Problems:
  - Setup check fails. Agent's hypothesis: the N-H stretches are still cold after a 1 ps
    global-Bussi equilibration (N-H bond-length std 0.0248 → 0.0254 Å across the five 1 ps
    production blocks); Davi equilibrated with a massive CSVR. Not tested. The pilot's
    pre-production also uses global thermostats (Bussi ramp, Berendsen NPT).
  - `python3` on PATH is `mace_env`'s: stdlib scripts are called with `/usr/bin/python3`
    (3.6.8). This session's first `session_facts.py` and `cost_ledger.py` calls ran under
    `mace_env` (stdlib only; output unaffected).
  - `cp` is `cp -i` in this shell: a non-interactive `cp` over an existing file does
    nothing; use `/bin/cp -f`.
- Next: owner decides the fix for the setup check (proposal: per-atom Langevin
  equilibration, setup check v2); then pilot phase 1 (re-prep if the protocol changes).

## 2026-11-24 — sdumont — Env 0.3.16 ready, ledger in UA, smoke job submitted
- Goal: finish the env with mace-torch 0.3.16; UA conversion in `cost_ledger.py`; GPU
  smoke + benchmark on the 1512-atom box.
- Done:
  - Env build job 11758427 (`sequana_cpu`) COMPLETED in 6 min 15 s: "lock: identical";
    torch 2.11.0+cu126 | mace-torch 0.3.16 | ase 3.29.0 | numpy 2.2.6 | cuda build 12.6.
    Tests with the venv: 70 OK, then 72 OK after this session's changes.
  - `92f72b7`: `cost_ledger.py` unit UA (ADR-0017), `sdumont.yaml` `cost.unit: UA`, two
    new tests. Dry run on job 11613155 (another project, 1 GPU, 12 cores): 5.1333 UA
    (165 s × 112 / 3600). Job 11758427 recorded: 0.4167 UA.
  - `92f72b7`: `src/smoke_bench.py` writes `report.json` after each of its 7 stages with
    the elapsed time and the GPU peak memory of the stage. CPU check with LJ in place of
    MACE (harness in the session scratchpad, not in git): 7 stages written, only the seed
    check failed (expected with LJ). The check found a `numpy.bool_` in a check result that
    broke `json.dumps`; fixed with `bool()`.
  - `runs/smoke-driver/` prepared at `92f72b7`. Smoke + bench job 11758464 submitted from
    `runs/smoke-bench/` with `--exclude=sdumont8042` on the command line; running on
    sdumont8090 since 11:58:32 at the end of the session.
- Results: none (the smoke is a test; its report is read next session).
- Decisions:
  - ADR-0017 (owner, 2026-11-24, "Ok para A e B. Prossiga."): SDumont cost in UA =
    ElapsedRaw × (AllocCPUS + 100 × GPUs) / 3600; GPU jobs count cores + GPUs (upper bound).
  - Smoke-bench report per stage with GPU peak memory (same answer). Owner: at 1512 atoms
    both GPU memory and the 20 min wall time of `sequana_gpu_dev` are at risk.
  - Davi's setup-check box has 432 atoms (`data/setup-check/`), not ~500: ours is 3.5×
    larger. The setup check stays on his box by design (RDF comparison); the pilot is sized
    by our 1512-atom benchmark, not by his 15.33 steps/s.
- Problems:
  - Ledger row of 11758413 stays `unknown`: written before ADR-0017; the ledger is
    append-only.
  - `src/smoke_bench.sbatch` lacks `--exclude=sdumont8042` (the node is in
    `sequana_gpu_dev`); given on the command line this time, the file is unchanged.
  - Davi's `docs/hpc-guide.md` not found under
    `/scratch/acmes/davi.fileti/mlff-efficiency-studies/docs/`; wanted for the UA rule of
    GPU jobs (TODO(owner) in ADR-0017).
  - At submission, `sequana_gpu_dev` had 14 nodes draining and 4 drained (sinfo); cause
    unknown.
- Next: read job 11758464 (`runs/smoke-bench/report.json` and its Slurm output: checks,
  steps/s, ns/day, GPU peak memory, driver rc 3 then 0), `cost_ledger.py add`; then the
  setup check (owner's ok given).

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
