# RDF references for the model's quality

Two references, kept apart. Neither has been judged yet.

## 1. AIMD RDFs (quantum reference): not on SDumont yet
- What: g(r) of the owner's AIMD (CP2K, PBE-D3(BJ)/DZVP, 350 Ry), computed on neumann with
  the owner's `rdf.py` (sha256
  `7c710bba297009d50a4714a032a20b4d9c28e5eb4cc621b311cc11d6722767a1`, `rdf_version` 1).
  This is the test `rdf-aimd-v1`.
- Coverage on 2026-11-19 (card): AIMD RDF for 20 of the 30 trajectories. Without one then:
  T333 r13_ionB, r15_ionA, r15_ionB, r15_mist; T450 r10_fora, r10_neut, r10_reag,
  r13_neut, r15_neut, r15_reag.
- Transfer: the owner sends one directory with all AIMD RDFs to SDumont. **The agent asks
  for it when a comparison is due** (status block, Waiting on owner). On arrival:
  `data/inbox/` + sha256, then `scripts/register_result.py legacy-aimd-rdf-reference ...`.
- Until then the AIMD curves exist here only as figures:
  `data/models/run2r10m0/plots/<system>.T<T>.png` (AIMD blue, MLMD orange dashed,
  ±2 standard errors, 5 blocks; the title says whether the trajectory was held out).

## 2. MLMD RDFs of the model (model baseline)
- `results/legacy-mlmd-rdf-run2r10m0/` (registered 2026-11-24: 30 csv + 30 json + the card):
  Davi's MLMD with run2r10m0 repeating each of the 30 AIMD runs (same start, box and T;
  1 ps equilibration + 5 ps production; `docs/model.md`), RDFs by the owner's `rdf.py`
  unchanged (same sha256 as above, in each JSON).
- Format: CSV columns `r_center_A`, `r_upper_A`, then `g_<pair>`, `se_<pair>`, `cn_<pair>`;
  dr 0.02 Å; r_max per file in its JSON (9.7 Å for r10_mist T333); 5 blocks; g over all
  pairs (intra + inter), minimum image, cubic box. Pairs: Al-Cl, Al-O, Al-N, Al-Al, Cl-Cl,
  Cl-H, O-H, C-O, C-N, N-H.
- Uses: check of our MD setup (same model and system → same RDF within error), and
  baseline for the 1512-atom runs.
- 27 of the 30 trajectories gave frames to training; only T333 r10_mist, T400 r13_ionB and
  T450 r15_neut are independent tests.

## Comparison rule of rdf-aimd-v1 (owner's, quoted in the card)
- First-peak position and coordination number at the first minimum; a difference larger
  than 2 × the combined error is a disagreement.
- Status: not applied ("Nada aqui foi julgado", card, 2026-11-19).
  TODO(owner): apply it here when the AIMD RDFs arrive, or say where its result lives.

## For the pilot (r = 1.0, 400 K)
- AIMD with RDF figure at r10, T400: r10_fora, r10_ion, r10_mist, r10_neut, r10_reag.
- The 1512-atom box allows r up to L/2 = 14.86 Å; compare with the AIMD only up to the
  AIMD r_max.
