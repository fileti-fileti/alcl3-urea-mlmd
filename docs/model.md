# Model run2r10m0

The one model used for MLMD in this repo (ADR-0015). Delivered by Davi on 2026-11-19
(`alcl3_mlmd_rdf_run2r10m0.zip`). His card, verbatim (Portuguese):
`results/legacy-mlmd-rdf-run2r10m0/LEIA-ME.md`. Confidential, unpublished.

## Files
- `data/models/run2r10m0/alcl3_urea_run2_r10_m0.model` (store, read-only), sha256
  `ff0e4578c01cd5ba8d6f08ba35eda9ad27e8d580f50f9085c37222485fd46e3a`, equal to the card
  (checked 2026-11-24). Checksums of the folder: `data/models/run2r10m0/SHA256SUMS`.
- Archive as received: `data/inbox/alcl3_mlmd_rdf_run2r10m0.zip`, sha256
  `a283cdeb2f2e76c8631748892e03e7240615be210e370153562e597d02bdaa03`; content identical to
  the extracted copy (`diff -r`, 2026-11-24).
- Figures of the card (AIMD vs MLMD g(r), 20 trajectories): `data/models/run2r10m0/plots/`.
- Copy outside `/scratch`: Davi's account. TODO(owner): a copy in `$HOME` too?

## What it is (from the card)
- MACE-MP-0 small (`2023-12-10-mace-128-L0_energy_epoch-249.model`), all weights
  fine-tuned; r_max 6 Å; float64; 135 epochs (energy weight raised from epoch 99).
- Labels: CP2K single points with the owner's reference input
  (PBE-D3(BJ)/DZVP-MOLOPT-SR-GTH, 1000 Ry, CP2K 2024.3), energy and forces, **no stress**.
  Labelled by the owner (owner, 2026-11-24). The model reproduces these single points,
  not the 350 Ry AIMD (on 390 labelled AIMD frames the 1000 Ry energy is +0.15 to
  +0.70 meV/atom above the 350 Ry one).
- Training: 1353 labelled frames (10 % validation): 273 AIMD frames of the 27 training
  trajectories (10 or 11 each) and 1080 MLMD frames from 10 active-learning rounds (NVT
  Langevin, 333/400/450 K × r10/r13/r15).
- Member 0 of a 3-model committee (different seeds). Members 1 and 2 are not used here
  (ADR-0015).
- Test error on 60 AIMD frames of the 3 held-out trajectories (committee mean): energy
  0.55 meV/atom, forces 31.7 meV/Å; member 0 alone: forces 31.7 meV/Å.
- Held-out trajectories (no frame in training, no exploration MD started from them):
  T333 r10_mist, T400 r13_ionB, T450 r15_neut. MLMD frames at the same (T, r) did enter.
- Elements: H, C, N, O, Al, Cl. Units: eV, Å, eV/Å.

## Limits
- No stress in training: stress and pressure are untrained and untested. NPT only as a
  short pressure relaxation (ADR-0016).
- The AIMD runs (and Davi's MLMD) at 400 and 450 K are at the 333 K density: the training
  data cover that density only.
- Davi's validation: one model (member 0), one MLMD per trajectory.

## Software
- Davi's MLMD, per the card: ASE 3.29.0, mace-torch 0.3.16, torch 2.11.0, float64, one
  V100 per run; 15–17 steps/s for 400–450 atoms.
- Chosen here (owner, 2026-11-24; ADR-0015): mace-torch 0.3.16 as on the card. Planned env:
  torch 2.11.0+cu126 (the CUDA 12.6 build matches the driver 560.35.03 / CUDA 12.6 seen on
  login node sdumont17; compute-node driver TODO), mace-torch 0.3.16, ASE 3.29.0. Both
  wheels are on PyPI / download.pytorch.org (checked 2026-11-24).
- Here: `mace_env` (mace-torch 0.3.15, torch 2.2.0+cu121, ASE 3.28.0;
  `envs/sdumont.environment.yml`). Check 2026-11-24 (login node, CPU): the model loads
  (`ScaleShiftMACE`, r_max 6.0, Z = 1 6 7 8 13 17) and gives finite energy and forces on
  the r10_mist packed seed (432 atoms, L = 19.581168 Å). Agreement with Davi's numbers
  not checked yet (status block, Later: setup check).

## Use (ASE)
```python
from ase.io import read
from mace.calculators import MACECalculator

atoms = read("init.xyz")                       # symbols and positions in Å
atoms.set_cell([L, L, L]); atoms.pbc = True    # always; L in Å
atoms.wrap()
atoms.calc = MACECalculator(model_paths="data/models/run2r10m0/alcl3_urea_run2_r10_m0.model",
                            device="cuda", default_dtype="float64")
```

## How Davi's MLMD was run (repeats each AIMD run; from the card)
- Per run: the AIMD `init.xyz`, the box from `ABC` of `prod.inp`, the temperature of the
  inputs. Maxwell-Boltzmann velocities, zero total momentum, fixed centre of mass.
- Equilibration: 2000 steps of 0.5 fs, massive CSVR (one thermostat per degree of
  freedom), time constant 10 fs. Production: 10000 steps of 0.5 fs, global CSVR (Bussi),
  time constant 100 fs, one frame every 10 steps (1001 frames).
- Stop if two atoms come closer than 0.6 Å: none of the 30 stopped. Seed 1 per run.
