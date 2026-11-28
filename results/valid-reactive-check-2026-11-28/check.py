"""m0 against the DFT labels of Davi's round-10 validation frames (valid.xyz), split by frames
with and without urea proton transfer (src/urea_scan.py, neumann radii). Written 2026-11-28 by
the agent; exploratory, no claim. Usage: check.py <repo> <valid.xyz> <model> <first> <last> <out.csv>
Per frame: origin (al/source), T, natoms, transfer (0/1), dE (meV/atom, model - ref), force RMSE
(meV/A) over all atoms, over H on N, over H on O (census bond < 1.37 A)."""
import sys, re, csv
import numpy as np
repo, path, model, first, last, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
sys.path.insert(0, repo + "/src"); import urea_scan
import torch; torch.set_num_threads(3)
from ase import Atoms
from mace.calculators import MACECalculator
calc = MACECalculator(model_paths=model, device="cpu", default_dtype="float64")
rows = []
with open(path) as f:
    i = 0
    while True:
        h = f.readline()
        if not h.strip(): break
        n = int(h); com = f.readline(); lines = [f.readline().split() for _ in range(n)]
        if not first <= i <= last: i += 1; continue
        kv = dict(re.findall(r'(\w+)=("[^"]*"|\S+)', com))
        cell = np.array([float(v) for v in kv["Lattice"].strip('"').split()]).reshape(3, 3)
        sym = [l[0] for l in lines]; X = np.array([[float(v) for v in l[1:4]] for l in lines])
        Fref = np.array([[float(v) for v in l[4:7]] for l in lines])
        a = Atoms(sym, positions=X, cell=cell, pbc=True); a.wrap(); a.calc = calc
        E = a.get_potential_energy(); F = a.get_forces()
        L = cell[0, 0]; c = urea_scan.scan_frame(sym, X, L)
        s = np.array(sym); iH, iN, iO = (np.where(s == e)[0] for e in ("H", "N", "O"))
        het = np.concatenate([iN, iO]); v = X[iH][:, None] - X[het][None]; v -= L * np.round(v / L)
        d = np.linalg.norm(v, axis=2); j = d.argmin(1); onO = (j >= len(iN)) & (d[np.arange(len(iH)), j] < 1.37)
        dF = F - Fref; rm = lambda idx: float(np.sqrt((dF[idx] ** 2).mean())) * 1000 if len(idx) else float("nan")
        rows.append(dict(frame=i, origin=kv.get("origin"), T=kv["system"].split("_")[0], natoms=n,
                         transfer=int(c["tautomer"] + c["ureate"] + c["uronium"] > 0),
                         dE_meV_atom=(E - float(kv["REF_energy"])) / n * 1000, F_rmse=rm(np.arange(n)),
                         F_rmse_HonN=rm(iH[~onO]), F_rmse_HonO=rm(iH[onO]), n_HonO=int(onO.sum())))
        i += 1
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(out, len(rows), "frames")
