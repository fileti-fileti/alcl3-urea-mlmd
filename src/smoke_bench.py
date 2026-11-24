#!/usr/bin/env python3
"""GPU smoke test and benchmark of model run2r10m0 in the MLMD venv (one sequana_gpu_dev job).

Usage (venv python, Python module loaded):
  python -I src/smoke_bench.py --model M --sha256 S --boxes DIR --box-L 29.729979 \
      --seed-xyz X --seed-L 19.581168 --seed-ref-e-per-atom E -o report.json

Checks and measures:
- versions, GPU name, `sm_70` in torch.cuda.get_arch_list();
- both start boxes in float64: energy, forces, stress finite; |F| max; pressure (no kinetic part);
- the r10_mist packed seed: energy per atom against the value from mace_env (0.3.15, CPU,
  docs/model.md);
- float32 vs float64 on both boxes: |dE| per atom and max |dF|;
- steps/s of NVT (Bussi) and NPT (Berendsen) on the reactant box after 50 FIRE steps,
  float64 and float32 (20 warm-up steps, then 100 timed), and ns/day at dt = 0.5 fs.
Writes a JSON report; prints a summary. Exit 1 if a check fails.
"""
import argparse
import importlib.metadata as md
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mlmd  # noqa: E402


def calc_for(model, dtype):
    from mace.calculators import MACECalculator
    return MACECalculator(model_paths=model, device="cuda", default_dtype=dtype)


def single(atoms, calc):
    import numpy as np
    from ase import units
    a = atoms.copy()
    a.calc = calc
    e = a.get_potential_energy()
    f = a.get_forces()
    s = a.get_stress()
    return {"e_per_atom_eV": e / len(a), "fmax_eV_A": float(np.sqrt((f ** 2).sum(1).max())),
            "pressure_bar_no_kinetic": float(-s[:3].sum() / 3 / units.bar),
            "finite": bool(np.isfinite(e) and np.isfinite(f).all() and np.isfinite(s).all())}, f


def bench(atoms, calc, kind, warm=20, n=100, T=400.0, seed=1):
    import numpy as np
    from ase import units
    from ase.constraints import FixCom
    from ase.md.velocitydistribution import MaxwellBoltzmannDistribution, Stationary
    a = atoms.copy()
    a.calc = calc
    a.set_constraint(FixCom())
    MaxwellBoltzmannDistribution(a, temperature_K=T, rng=np.random.default_rng(seed))
    Stationary(a)
    dt = 0.5 * units.fs
    if kind == "nvt":
        from ase.md.bussi import Bussi
        dyn = Bussi(a, dt, temperature_K=T, taut=100 * units.fs, rng=np.random.default_rng(seed))
    else:
        from ase.md.nptberendsen import NPTBerendsen
        dyn = NPTBerendsen(a, dt, temperature_K=T, pressure_au=1.0 * units.bar,
                           taut=100 * units.fs, taup=1000 * units.fs,
                           compressibility_au=4.5e-5 / units.bar, fixcm=True)
    dyn.run(warm)
    t = time.perf_counter()
    dyn.run(n)
    sps = n / (time.perf_counter() - t)
    return {"steps_per_s": sps, "ns_per_day_dt0.5fs": sps * 86400 * 0.5e-6,
            "T_end_K": a.get_temperature(), "finite": bool(np.isfinite(a.get_potential_energy()))}


def main(argv=None):
    import numpy as np
    import torch
    from ase.io import read
    from ase.optimize import FIRE
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for k in ("--model", "--sha256", "--boxes", "--seed-xyz", "-o"):
        ap.add_argument(k, required=True)
    ap.add_argument("--box-L", type=float, required=True)
    ap.add_argument("--seed-L", type=float, required=True)
    ap.add_argument("--seed-ref-e-per-atom", type=float, required=True)
    a = ap.parse_args(argv)
    rep = {"versions": {p: md.version(p) for p in ("torch", "mace-torch", "ase", "numpy")},
           "gpu": torch.cuda.get_device_name(0), "arch_list": torch.cuda.get_arch_list(),
           "torch_cuda": torch.version.cuda, "checks": {}}
    ok = rep["checks"]
    ok["sm_70_in_arch_list"] = "sm_70" in rep["arch_list"]
    ok["model_sha256"] = mlmd.sha256(a.model) == a.sha256
    boxes = {n: mlmd.read_pdb(Path(a.boxes) / "r1.0_{}.pdb".format(n), a.box_L)
             for n in ("reagentes", "ionico")}
    seed = read(a.seed_xyz, index=0)
    seed.set_cell([a.seed_L] * 3)
    seed.pbc = True
    rep["single"], forces = {}, {}
    t = time.perf_counter()
    c64 = calc_for(a.model, "float64")
    rep["load_s_float64"] = time.perf_counter() - t
    for n, at in boxes.items():
        rep["single"][n + "_float64"], forces[n] = single(at, c64)
    rep["single"]["seed_r10_mist_float64"], _ = single(seed, c64)
    d = rep["single"]["seed_r10_mist_float64"]["e_per_atom_eV"] - a.seed_ref_e_per_atom
    rep["seed_dE_per_atom_vs_mace_env_eV"] = d
    ok["seed_matches_mace_env_1e-6_eV_per_atom"] = abs(d) < 1e-6
    ok["boxes_finite_float64"] = all(rep["single"][n + "_float64"]["finite"] for n in boxes)
    mini = boxes["reagentes"].copy()
    mini.calc = c64
    FIRE(mini, logfile=None).run(fmax=0.05, steps=50)
    rep["fire50_fmax_eV_A"] = float(np.sqrt((mini.get_forces() ** 2).sum(1).max()))
    rep["bench"] = {"nvt_float64": bench(mini, c64, "nvt"), "npt_float64": bench(mini, c64, "npt")}
    c32 = calc_for(a.model, "float32")
    for n, at in boxes.items():
        s32, f32 = single(at, c32)
        rep["single"][n + "_float32"] = s32
        rep["single"][n + "_float32_vs_64"] = {
            "dE_per_atom_eV": s32["e_per_atom_eV"] - rep["single"][n + "_float64"]["e_per_atom_eV"],
            "max_dF_eV_A": float(np.abs(f32 - forces[n]).max())}
    rep["bench"]["nvt_float32"] = bench(mini, c32, "nvt")
    rep["bench"]["npt_float32"] = bench(mini, c32, "npt")
    ok["bench_finite"] = all(b["finite"] for b in rep["bench"].values())
    Path(a.o).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))
    bad = [k for k, v in ok.items() if not v]
    print("FAILED: {}".format(bad) if bad else "all checks passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
