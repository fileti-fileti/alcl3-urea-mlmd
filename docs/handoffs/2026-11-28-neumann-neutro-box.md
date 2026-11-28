# Handoff from neumann (alcl3-urea), 2026-11-28 — neutral r = 1.0 start box (neutro)

Received 2026-11-28, pasted by the owner in the chat; kept verbatim below the line. Answers
the request drafted in this repo on 2026-11-28 (journal, "Carrasco-Busturia 2021 read;
neutral start box requested").

---

# Delivery from alcl3-urea (neumann), 2026-11-28 — third r = 1.0 start box (neutro)

Confidential, unpublished. Answers the request of 2026-11-28.

## Tarball
- mlmd-boxes-r1.0-neutro-v2.tar.gz
  sha256 6a919bab21c81d39d02a798eb884351954632c058393c18d2a5553f239a63b6b
- Contents: r1.0_neutro.pdb (sha256 1a2291b71d1bb7908e7de1b056af456c5f236565dad077d21681fa39bc7709bb),
  MANIFEST.csv (same columns as mlmd-boxes-r1.0-v2), contacts_check.txt.

## Box
- [AlCl3(urea)] x 126, urea O-bound to Al; 1512 atoms, 126 molecules; cubic L = 29.729979 A
  (CRYST1 29.730), rho = 1.5398 g/cm3. Same composition, box and density as the v2 boxes.
- PDB as in v2: one residue per molecule (resName AU1), chain A, element in columns 77-78,
  whole molecules, no CONECT. NOT equilibrated.
- Adduct geometry: the AlCl3U.pdb of the v1 r1.0/neutro box, extracted by extract_species.py
  from the DTU SI Starting_Configuration_Model_P3.xyz (the same source as the species in
  reagentes, from model R1, and ionico, from models P1 and P2a). Al-O 1.785 A;
  Al-Cl 2.116 / 2.132 / 2.172 A; C-O 1.295 A.
- Recipe: v2 unchanged (r = 1.0 Packmol radii with 0.01 A margin, Packmol seed of the v1 input).

## Checks (run on the PDB that is shipped)
- extract_species.py: 126 x AlCl3U and nothing else; Al coordination number 4 for all 126.
- Contacts: 0 intermolecular contacts below the AIMD r = 1.0 minima (PASS); smallest Cl...Cl 3.105 A.
- Molecules rigid (RMSD to the adduct PDB <= 0.0006 A); PDB read-back equal to packed.xyz.

## Provenance
alcl3-urea commit 38e4eb4 (no code change; scripts as for v2), docs/mlmd-boxes.md.
