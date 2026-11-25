#!/usr/bin/env python3
"""LAMMPS (`pair_style mace`) against ASE on the 1512-atom boxes: energy and force match, MD
speed (docs/experiments/lammps-bench.md). Numpy and ASE (mace for `ref`): the MLMD venv.

  lammps_bench.py inputs <run_dir> --boxes <dir> --box-L <L>   LAMMPS data files and inputs
  lammps_bench.py ref <run_dir> --model <path> --sha256 <hex>   ASE energies and forces, float64
  lammps_bench.py report <run_dir>                              report.json with the rule applied

Run dir layout: run2r10m0_f{64,32}.model-lammps.pt (from mace_env's create_lammps_model),
<box>.data, sp_<box>_f{64,32}.in/.log/.forces, bench_f{64,32}.in/.log, ref.json,
ref_<box>.npy, gpu.log (nvidia-smi --query-compute-apps during the LAMMPS runs).
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

BOXES = ("reagentes", "ionico")
SPECORDER = ["Al", "Cl", "O", "N", "C", "H"]
# Rule (docs/experiments/lammps-bench.md, fixed 2026-11-25): match in float64, then 2 x the ASE
# NVT speed of the smoke bench (job 11758464, runs/smoke-bench/report.json) in each dtype.
TOL_E_PER_ATOM_EV = 1e-6
TOL_F_EV_A = 1e-5
ASE_STEPS_PER_S = {"f64": 6.129869590381892, "f32": 8.93430706023893}
SPEEDUP = 2.0

HEAD = """units metal
boundary p p p
atom_style atomic
atom_modify map yes
newton on
read_data {data}
pair_style mace no_domain_decomposition
pair_coeff * * {model} {elements}
"""
SP = HEAD + """thermo_style custom step pe
thermo_modify format float %.10f
dump f all custom 1 {name}.forces id fx fy fz
dump_modify f sort id format float %.10f
run 0
"""
BENCH = HEAD + """neighbor 2.0 bin
neigh_modify every 1 delay 0 check yes
timestep 0.0005
thermo 50
thermo_style custom step temp pe etotal
minimize 0 1.0e-2 20 200
reset_timestep 0
velocity all create 400.0 12345 mom yes rot no dist gaussian
fix 1 all langevin 400.0 400.0 0.1 12345 zero yes
fix 2 all nve
run 50
run 500
"""


def model_name(dtype):
    return "run2r10m0_{}.model-lammps.pt".format(dtype)


def write_inputs(run_dir, boxes_dir, L):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import mlmd
    from ase.io.lammpsdata import write_lammps_data
    d = Path(run_dir)
    for box in BOXES:
        a = mlmd.read_pdb(Path(boxes_dir) / "r1.0_{}.pdb".format(box), L)
        write_lammps_data(str(d / "{}.data".format(box)), a, specorder=SPECORDER, masses=True,
                          atom_style="atomic", units="metal")
        for dt in ("f64", "f32"):
            name = "sp_{}_{}".format(box, dt)
            (d / (name + ".in")).write_text(SP.format(data=box + ".data", model=model_name(dt),
                                                      elements=" ".join(SPECORDER), name=name))
    for dt in ("f64", "f32"):
        (d / "bench_{}.in".format(dt)).write_text(BENCH.format(
            data="reagentes.data", model=model_name(dt), elements=" ".join(SPECORDER)))


def ase_reference(run_dir, model, sha, device="cuda"):
    import numpy as np
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import mlmd
    h = hashlib.sha256(Path(model).read_bytes()).hexdigest()
    if h != sha:
        raise SystemExit("model sha256 {} != {}".format(h, sha))
    from ase.io.lammpsdata import read_lammps_data
    from mace.calculators import MACECalculator
    calc = MACECalculator(model_paths=model, device=device, default_dtype="float64")
    ref = {}
    for box in BOXES:
        a = read_lammps_data(str(Path(run_dir) / "{}.data".format(box)), atom_style="atomic",
                             units="metal", Z_of_type={i + 1: mlmd_z(s) for i, s in enumerate(SPECORDER)})
        a.pbc = True
        a.calc = calc
        ref[box] = {"natoms": len(a), "energy_eV": float(a.get_potential_energy())}
        np.save(str(Path(run_dir) / "ref_{}.npy".format(box)), a.get_forces())
    (Path(run_dir) / "ref.json").write_text(json.dumps(ref, indent=1) + "\n")
    return ref


def mlmd_z(symbol):
    from ase.data import atomic_numbers
    return atomic_numbers[symbol]


def parse_pe(log_text):
    """Potential energy at step 0 from a LAMMPS log with `thermo_style custom step pe`."""
    lines = log_text.splitlines()
    for i, line in enumerate(lines):
        cols = line.split()
        if cols[:2] == ["Step", "PotEng"]:
            return float(lines[i + 1].split()[1])
    raise ValueError("no 'Step PotEng' thermo header")


def parse_forces(dump_text, natoms):
    """Forces (id-sorted) of the first frame of a `dump custom id fx fy fz`."""
    import numpy as np
    lines = dump_text.splitlines()
    i = lines.index("ITEM: ATOMS id fx fy fz")
    rows = [l.split() for l in lines[i + 1:i + 1 + natoms]]
    ids = [int(r[0]) for r in rows]
    if ids != list(range(1, natoms + 1)):
        raise ValueError("dump not sorted by id 1..N")
    return np.array([[float(v) for v in r[1:4]] for r in rows])


def parse_performance(log_text):
    """timesteps/s of the last `Performance:` line."""
    vals = re.findall(r"^Performance:.*?([0-9.eE+-]+) timesteps/s", log_text, flags=re.M)
    if not vals:
        raise ValueError("no Performance line")
    return float(vals[-1])


def gpu_used(gpu_log_text):
    return any("lmp" in line for line in gpu_log_text.splitlines())


def verdict(match_f64, speeds, gpu, finished):
    if not (finished and gpu and match_f64):
        return "inconclusive"
    ok = all(speeds[d] >= SPEEDUP * ASE_STEPS_PER_S[d] for d in ("f64", "f32"))
    return "yes" if ok else "no"


def report(run_dir):
    import numpy as np
    d = Path(run_dir)
    ref = json.loads((d / "ref.json").read_text())
    out = {"rule": {"tol_e_per_atom_eV": TOL_E_PER_ATOM_EV, "tol_f_eV_A": TOL_F_EV_A,
                    "speedup": SPEEDUP, "ase_steps_per_s": ASE_STEPS_PER_S},
           "sp": {}, "speed": {}}
    match = True
    for box in BOXES:
        n, f_ref = ref[box]["natoms"], np.load(str(d / "ref_{}.npy".format(box)))
        for dt in ("f64", "f32"):
            name = "sp_{}_{}".format(box, dt)
            e = parse_pe((d / (name + ".log")).read_text())
            f = parse_forces((d / (name + ".forces")).read_text(), n)
            de = abs(e - ref[box]["energy_eV"]) / n
            df = float(np.linalg.norm(f - f_ref, axis=1).max())
            out["sp"][name] = {"dE_per_atom_eV": de, "max_dF_eV_A": df}
            if dt == "f64":
                match = match and de <= TOL_E_PER_ATOM_EV and df <= TOL_F_EV_A
    finished = True
    for dt in ("f64", "f32"):
        try:
            out["speed"][dt] = parse_performance((d / "bench_{}.log".format(dt)).read_text())
        except (OSError, ValueError):
            out["speed"][dt], finished = None, False
    gpu = gpu_used((d / "gpu.log").read_text()) if (d / "gpu.log").exists() else False
    out.update(match_f64=match, gpu_used=gpu, finished=finished,
               verdict=verdict(match, out["speed"], gpu, finished))
    (d / "report.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inputs")
    p.add_argument("run_dir")
    p.add_argument("--boxes", required=True)
    p.add_argument("--box-L", type=float, required=True)
    p = sub.add_parser("ref")
    p.add_argument("run_dir")
    p.add_argument("--model", required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--device", default="cuda")
    p = sub.add_parser("report")
    p.add_argument("run_dir")
    a = ap.parse_args(argv)
    if a.cmd == "inputs":
        write_inputs(a.run_dir, a.boxes, a.box_L)
    elif a.cmd == "ref":
        print(json.dumps(ase_reference(a.run_dir, a.model, a.sha256, a.device), indent=1))
    else:
        report(a.run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
