# Handoff from neumann (alcl3-urea), 2026-11-24 — MLMD pilot start boxes

Received 2026-11-24, pasted by the owner in the chat; kept verbatim below the line.

Owner's corrections for this repo (2026-11-24):
- The dataset was labelled by the owner. The lines on labels, reference level and stress
  under "Facts the model and the census depend on" describe the neumann project's record;
  they are outdated and not needed here (no training planned, ADR-0015).
- Committee monitoring and active learning are dropped (ADR-0015).
- "NPT to the model's density" becomes a short NPT to relax the pressure, followed by NVT
  (ADR-0016).

---

# Context from project alcl3-urea (neumann), 2026-11-24 — MLMD pilot start boxes

Confidential, unpublished.

## What arrived
- `mlmd-boxes-r1.0-v2.tar.gz`, sha256
  b38c48db8427cfcbfaaed429b958b43e61ce87fe4891bbfbf656778e1fb2cba7
  Contents: two PDB boxes, MANIFEST.csv (sha256 of each PDB in column 2), contacts_check.txt.
- Verify: `sha256sum mlmd-boxes-r1.0-v2.tar.gz`; after extracting, `sha256sum r1.0_*.pdb`
  against MANIFEST.csv.

| File               | Start                 | Species                           | Atoms | Molecules |
|--------------------|-----------------------|-----------------------------------|-------|-----------|
| r1.0_reagentes.pdb | reactants (molecular) | Al2Cl6 x 63, urea x 126           | 1512  | 189       |
| r1.0_ionico.pdb    | fully ionic           | [AlCl2(urea)2]+ x 63, AlCl4- x 63 | 1512  | 126       |

- AlCl3:urea r = 1.0 (Al:urea 126:126), cubic, L = 29.729979 A (CRYST1 rounds to 29.730),
  rho = 1.5398 g/cm3 (experimental, 333 K).
- PDB: one residue per molecule (resName AU2, AL4, A26, URE), chain A, element in columns
  77-78, whole molecules (a few atoms slightly outside [0, L): wrap on conversion), no CONECT.
  Type order used on neumann for LAMMPS data: 1 Al 2 C 3 Cl 4 H 5 N 6 O.
- NOT equilibrated. Rigid molecules packed by Packmol. For each element pair, no intermolecular
  contact is shorter than the smallest one seen in 7 AIMD runs at r = 1.0 (333 and 400 K,
  PBE-D3(BJ)/DZVP, 7007 frames). Smallest Cl...Cl: 3.106 A (reagentes), 2.825 A (ionico).
- DO NOT USE the v1 boxes (08_mlmd_boxes, built 2026-11-21, possibly copied here earlier):
  Packmol tolerance 2.0 A left Cl...Cl at 2.19 A; a CP2K single point gave |F| max 9.64 eV/A,
  all large forces on Cl.

## Pilot plan (owner's ok, 2026-11-24)
- r = 1.0, the two opposite starts above, 400 K (all five r = 1.0 seeds have AIMD at 400 K
  in the training pool). Equilibrium is judged by both runs reaching the same speciation;
  a single start cannot tell equilibrium from a trapped state.
- Protocol: minimise -> short NVT with small dt and a T ramp -> NPT to the model's density
  -> production. Monitor committee disagreement (frames above threshold -> active learning).
- The pilot measures ns/day for 1512 atoms, stability, and the time for the two runs to reach
  the same speciation. That time sizes the production matrix (r = 1.0, 1.3, 1.5; 1 or 2 starts
  per state point; temperatures).
- Before any output is analysed: write the experiment doc with the reading rule (census
  quantity, convergence criterion, error, maximum length) and a pending claim.

## Facts the model and the census depend on
- Species census on neumann: bond if d < r_i + r_j with r = Al 1.0, Cl 1.7, O 1.0, N 1.0,
  C 1.0, H 0.37 A, and Cl bonds only to Al (extract_species.py, SI S2.2). Use the same
  criterion so that results compare.
- As of 2026-11-24 in alcl3-urea: no frame selected or labelled; the reference level is still
  open (keep PBE-D3(BJ)/DZVP or validate first); the AIMD runs saved no forces, so training
  needs single-point labels. NPT needs stress in the labels.
- Not known on neumann: the MACE model, its labels, GPU queue and paths on SDumont.

## Provenance
alcl3-urea commit 169885d, docs/mlmd-boxes.md (recipe, checks, results); scripts
src/contacts.py, src/repack_radii.py, src/export_box_pdb.py.
