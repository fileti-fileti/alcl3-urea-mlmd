# 0020. Target temperature 333 K; training to be reformulated to cover it with priority
- Status: Accepted. Relates to [0015](0015-scope-sites-model-engine.md): the model change it
  leads to gets its own ADR when the new model arrives.
- Date: 2026-11-28. Decided by: owner (Eudes Fileti). Process: ADR-0013.

## Context
- The volume of every AIMD and MLMD box is the experimental density at 333 K (Liu et al.,
  J. Mol. Liq. 247, 57 (2017), measured for r = 1.2–1.5, extrapolated to r = 1.0 by
  Carrasco-Busturia et al., ChemSusChem 14, 2034 (2021); `docs/journal.md` 2026-11-28).
- AIMD design (dataset report, section 2.4): 333 K was run only for the ion, ionA, ionB and
  mist seeds; 400 K for all 15; 450 K only for reag, neut and fora. Every seed starts from the
  same `init.xyz` at every temperature (sha256 checked 2026-11-28).
- Training set of run2r10m0 (round 10, train + valid; `results/urea-scan-2026-11-28` and the
  journal): frames per temperature 431 / 501 / 421 (333 / 400 / 450 K); frames with two or more
  free ureas 0 / 163 / 320; frames with urea proton transfer 0 / 132 / 168. The active learning
  started each walker from the speciations available at its temperature, so it inherited the
  AIMD gap.
- Every reag start at 400 and 450 K shows urea proton transfer, in the AIMD and in the MLMD;
  no trajectory with at most one free urea shows any (`results/urea-scan-2026-11-28`). The
  model's force error on the transferred H is about 80 meV/Å against about 24–31 meV/Å on H
  bonded to N (`results/valid-reactive-check-2026-11-28`); no such frame exists at 333 K.

## Decision
- The production temperature of the project is 333 K.
- The training set is reformulated to cover 333 K with priority:
  1. AIMD at 333 K for the seven seeds missing there (r10_reag, r10_neut, r10_fora, r13_reag,
     r13_neut, r15_reag, r15_neut), with the protocol and level of the existing runs
     (PBE-D3(BJ), DZVP-MOLOPT-SR-GTH, 350 Ry), from the same `init.xyz`; r13_reag starts as it
     is, with the ureate/uronium pair formed during its GEO_OPT. Request:
     `docs/handoffs/2026-11-28-request-neumann-aimd-333K.md` (neumann).
  2. A hybrid-functional check of the proton-transfer energy on a few pairs, in parallel, on
     neumann; it does not block item 1.
  3. The weight of 333 K comes from the training side (more 333 K frames and active-learning
     walkers from every start type at 333 K; model selection and acceptance at 333 K by
     category, reactive frames included). The numbers are open (owner and Davi).
- The 450 K runs of the ion, ionA, ionB and mist seeds are optional, for later.
- Until the new model exists, run2r10m0 is an exploration model: no pilot phase 2 and no
  production with it. The 400 K pilot (reag, ion, neutro) continues as exploration.

## Owner's approval (2026-11-28, chat) and agent's justification
- Owner: "A temperatura deve ser de 333K. É facil justificar isso no nosso artigo pois há
  experimentos prévios." — "precisamos reformular o treino, fechar a lacuna, priorizar 333K
  dando mais peso a ela." — on the agent's items 1–4 (PBE-D3 kept with a hybrid check; the
  seven 333 K AIMD now and the weight in training; r13_reag as it is; this ADR): "ok. Nada a
  corrigir". On the 450 K ionic seeds as optional and later: "ok" (the agent read it as
  approval of its recommendation).
- Agent's justification:
  - The simulation volume is the 333 K density, so 333 K is the temperature at which the box
    matches experiment.
  - The present training has none of the chemistries of the reag, neut and fora starts at
    333 K, and its test set has no reactive frame: a 333 K production from those starts would
    run where the model has no data.
  - PBE-D3 keeps the new labels consistent with the 1353 existing ones; the hybrid check
    measures the risk of a spurious proton transfer (LeBlanc et al., Angew. Chem. 2018)
    without stopping the AIMD.

## Consequences
- The pilot at 400 K sizes neither the 333 K protocol nor its length; dynamics at 333 K is
  slower. A 333 K equilibration protocol (for example, equilibrate at 400 K and cool) is fixed
  in an experiment doc before production.
- TODO(owner): the prior experiments at 333 K to compare with (speciation: Raman, NMR?).
- TODO(owner): cost on neumann of one AIMD and of one 1000 Ry label.
- The pending choices for the training (label ratio 333 : 400 : 450, frames per 333 K AIMD,
  loss weights, acceptance limits per category, retraining from scratch or fine-tuning) go in
  the request to Davi.
