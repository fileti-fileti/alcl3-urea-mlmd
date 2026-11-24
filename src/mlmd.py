#!/usr/bin/env python3
"""Staged, checkpointed MLMD driver (ASE + MACE) for alcl3-urea-mlmd.

Usage (the venv's python with its Python module loaded; job scripts from scripts/prep_mlmd.py):
  python -I src/mlmd.py run <run_dir> [--budget-s SECONDS] [--device cuda|cpu]

<run_dir>/run.json holds the whole configuration:
  model {path, sha256}, dtype, structure {path (.pdb or .xyz), box_A}, seed,
  min_distance_A, check_every, ckpt_every, stages [...]
Stage kinds (each has a unique `name`):
  minimise       FIRE at fixed cell: fmax_eV_A, max_steps
  nvt            Bussi (CSVR) thermostat: dt_fs, ps, T_K, taut_fs [, T_start_K: linear ramp
                 from T_start_K to T_K over the stage]
  npt_berendsen  isotropic NPTBerendsen: dt_fs, ps, T_K, taut_fs, P_bar, taup_fs,
                 compressibility_per_bar, mean_volume_last_ps; at the end the box is scaled to
                 the mean volume of the last mean_volume_last_ps (positions scaled with it)
MD stages also take thermo_every and dump_every (steps; dump_every 0 = no frames); both, and
ckpt_every, are multiples of check_every. The centre of mass is fixed (FixCom). Velocities are
drawn (Maxwell-Boltzmann, zero total momentum) only when the incoming atoms have none.

Files in <run_dir>: run.json, state.json + ckpt.traj (checkpoint), <stage>.thermo.csv,
<stage>.xyz (frames; comment line `i = <step>` as rdf.py expects), <stage>.final.traj,
<stage>.done, npt volume in <stage>.volume.json, DONE, STOPPED (reason), mlmd.log.

Exit codes: 0 every stage done; 2 configuration error; 3 time budget reached, checkpoint
written (resubmit); 4 stopped on an unphysical state (atoms closer than min_distance_A,
non-finite energy or forces): do not resubmit.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

EXIT_DONE, EXIT_CONFIG, EXIT_BUDGET, EXIT_STOPPED = 0, 2, 3, 4
AMU_G = 1.66053906660e-24          # g per amu
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
THERMO_COLS = ["step", "time_ps", "T_K", "T_target_K", "epot_eV", "ekin_eV", "etot_eV",
               "conserved_eV", "volume_A3", "density_g_cm3", "pressure_bar", "wall_s",
               "steps_per_s"]
MD_KEYS = {
    "nvt": {"dt_fs", "ps", "T_K", "taut_fs", "thermo_every", "dump_every"},
    "npt_berendsen": {"dt_fs", "ps", "T_K", "taut_fs", "P_bar", "taup_fs",
                      "compressibility_per_bar", "mean_volume_last_ps", "thermo_every",
                      "dump_every"},
}
OPTIONAL = {"nvt": {"T_start_K"}, "npt_berendsen": set(), "minimise": set()}
STAGE_KEYS = dict(MD_KEYS, minimise={"fmax_eV_A", "max_steps"})


class ConfigError(Exception):
    pass


class Stopped(Exception):
    pass


class BudgetReached(Exception):
    pass


# ---------- configuration ----------
def sha256(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config(path):
    try:
        cfg = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise ConfigError("{}: {}".format(path, e))
    for k in ("structure", "seed", "min_distance_A", "check_every", "ckpt_every", "stages"):
        if k not in cfg:
            raise ConfigError("run.json: missing {!r}".format(k))
    ce, ck = int(cfg["check_every"]), int(cfg["ckpt_every"])
    if ce < 1 or ck < ce or ck % ce:
        raise ConfigError("ckpt_every must be a positive multiple of check_every")
    names = set()
    for st in cfg["stages"]:
        name, kind = st.get("name", ""), st.get("kind", "")
        if not NAME_RE.match(name) or name in names:
            raise ConfigError("stage name {!r}: invalid or repeated".format(name))
        names.add(name)
        if kind not in STAGE_KEYS:
            raise ConfigError("stage {}: unknown kind {!r}".format(name, kind))
        keys = set(st) - {"name", "kind"}
        missing, extra = STAGE_KEYS[kind] - keys, keys - STAGE_KEYS[kind] - OPTIONAL[kind]
        if missing or extra:
            raise ConfigError("stage {}: missing {} unknown {}".format(
                name, sorted(missing), sorted(extra)))
        if kind in MD_KEYS:
            for k in ("thermo_every", "dump_every"):
                v = int(st[k])
                if v < 0 or (v == 0 and k == "thermo_every") or v % ce:
                    raise ConfigError("stage {}: {} must be a multiple of check_every".format(name, k))
            n = steps_of(st)
            if n < 1 or n % ce:
                raise ConfigError("stage {}: steps ({}) must be a multiple of check_every".format(name, n))
            if kind == "npt_berendsen" and not 0 < st["mean_volume_last_ps"] <= st["ps"]:
                raise ConfigError("stage {}: mean_volume_last_ps out of range".format(name))
    return cfg


def steps_of(st):
    return int(round(st["ps"] * 1000.0 / st["dt_fs"]))


def make_calculator(cfg, device):
    model = cfg.get("model") or {}
    if not model.get("path") or not model.get("sha256"):
        raise ConfigError("run.json: model.path and model.sha256 are required")
    got = sha256(model["path"])
    if got != model["sha256"]:
        raise ConfigError("model sha256 {} != run.json {}".format(got, model["sha256"]))
    from mace.calculators import MACECalculator
    return MACECalculator(model_paths=model["path"], device=device,
                          default_dtype=cfg.get("dtype", "float64"))


# ---------- structures ----------
def read_pdb(path, box):
    """ATOM/HETATM records; element from columns 77-78; cubic cell of edge `box`, wrapped."""
    from ase import Atoms
    symbols, pos = [], []
    with open(str(path)) as f:
        for line in f:
            if line.startswith(("ATOM  ", "HETATM")):
                el = line[76:78].strip()
                if not el:
                    raise ConfigError("{}: empty element columns 77-78".format(path))
                symbols.append(el.capitalize())
                pos.append([float(line[30:38]), float(line[38:46]), float(line[46:54])])
    if not symbols:
        raise ConfigError("{}: no ATOM/HETATM records".format(path))
    atoms = Atoms(symbols=symbols, positions=pos, cell=[box] * 3, pbc=True)
    atoms.wrap()
    return atoms


def load_structure(spec):
    path, box = spec["path"], float(spec["box_A"])
    if str(path).lower().endswith(".pdb"):
        return read_pdb(path, box)
    from ase.io import read
    atoms = read(str(path), index=0)
    atoms.set_cell([box] * 3)
    atoms.pbc = True
    atoms.wrap()
    return atoms


# ---------- checks ----------
def check_physical(atoms, dmin):
    import numpy as np
    from ase.neighborlist import neighbor_list
    e = atoms.get_potential_energy()
    f = atoms.get_forces()
    if not (np.isfinite(e) and np.isfinite(f).all()):
        raise Stopped("non-finite energy or forces")
    i, j, d = neighbor_list("ijd", atoms, dmin)
    if len(d):
        k = int(np.argmin(d))
        raise Stopped("atoms {} and {} at {:.3f} A (< {} A)".format(i[k], j[k], d[k], dmin))


# ---------- run state ----------
class Run:
    def __init__(self, run_dir, budget_s=None, clock=time.monotonic, out=sys.stdout):
        self.dir = Path(run_dir)
        self.cfg = load_config(self.dir / "run.json")
        self.budget_s = budget_s
        self.clock = clock
        self.t0 = clock()
        self.out = out
        self.state_path = self.dir / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else None

    def log(self, msg):
        line = "[{}] {}".format(datetime.datetime.now().isoformat(timespec="seconds"), msg)
        print(line, file=self.out, flush=True)
        with open(str(self.dir / "mlmd.log"), "a") as f:
            f.write(line + "\n")

    def over_budget(self):
        return self.budget_s is not None and self.clock() - self.t0 > self.budget_s

    def rng(self):
        import numpy as np
        rng = np.random.default_rng(int(self.cfg["seed"]))
        if self.state and self.state.get("rng"):
            rng.bit_generator.state = self.state["rng"]
        return rng

    def save_state(self, atoms, stage, steps_done, rng, transferred, files):
        from ase.io import write
        state = {"stage": stage, "steps_done": steps_done, "rng": rng.bit_generator.state,
                 "transferred_energy": transferred,
                 "files": {n: (self.dir / n).stat().st_size for n in files if (self.dir / n).exists()},
                 "saved": datetime.datetime.now().isoformat(timespec="seconds")}
        if atoms is not None:
            tmp = self.dir / "ckpt.tmp.traj"
            write(str(tmp), atoms.copy(), format="traj")
            os.replace(str(tmp), str(self.dir / "ckpt.traj"))
        tmp = self.dir / "state.tmp.json"
        tmp.write_text(json.dumps(state, indent=1) + "\n")
        os.replace(str(tmp), str(self.state_path))
        self.state = state


def _truncate(path, size):
    if path.exists() and path.stat().st_size > size:
        with open(str(path), "r+b") as f:
            f.truncate(size)


def _thermo_row(atoms, step, st, dyn_kind, t_target, transferred, wall, sps):
    from ase import units
    epot, ekin = atoms.get_potential_energy(), atoms.get_kinetic_energy()
    vol = atoms.get_volume()
    stress = atoms.get_stress(include_ideal_gas=True)
    p_bar = -sum(stress[:3]) / 3.0 / units.bar
    conserved = epot + ekin - transferred if dyn_kind == "nvt" else float("nan")
    dens = atoms.get_masses().sum() * AMU_G / (vol * 1e-24)
    vals = [step, step * st["dt_fs"] / 1000.0, atoms.get_temperature(), t_target, epot, ekin,
            epot + ekin, conserved, vol, dens, p_bar, wall, sps]
    return ",".join("{:d}".format(v) if isinstance(v, int) else "{:.10g}".format(v) for v in vals)


def _frame(atoms, step, st):
    L = atoms.cell.lengths()
    head = ('i = {}, time = {:.3f} fs, E = {:.8f} eV, Lattice="{:.8f} 0 0 0 {:.8f} 0 0 0 {:.8f}" '
            'Properties=species:S:1:pos:R:3'.format(step, step * st["dt_fs"],
                                                    atoms.get_potential_energy(), *L))
    lines = [str(len(atoms)), head]
    for s, (x, y, z) in zip(atoms.get_chemical_symbols(), atoms.get_positions()):
        lines.append("{} {:.8f} {:.8f} {:.8f}".format(s, x, y, z))
    return "\n".join(lines) + "\n"


def run_minimise(run, st, atoms):
    from ase.optimize import FIRE
    import numpy as np
    opt = FIRE(atoms, logfile=str(run.dir / "{}.fire.log".format(st["name"])))
    conv = opt.run(fmax=st["fmax_eV_A"], steps=int(st["max_steps"]))
    fmax = float(np.sqrt((atoms.get_forces() ** 2).sum(axis=1).max()))
    run.log("{}: FIRE {} steps, fmax {:.4f} eV/A, converged={}".format(
        st["name"], opt.get_number_of_steps(), fmax, bool(conv)))
    check_physical(atoms, run.cfg["min_distance_A"])


def run_md(run, st, atoms, rng, steps_done, transferred):
    import numpy as np
    from ase import units
    from ase.constraints import FixCom
    from ase.md.velocitydistribution import MaxwellBoltzmannDistribution, Stationary
    name, kind = st["name"], st["kind"]
    nsteps, ce, ck = steps_of(st), int(run.cfg["check_every"]), int(run.cfg["ckpt_every"])
    t_end = float(st["T_K"])
    t_start = float(st.get("T_start_K", t_end))

    def t_at(step):
        return t_start + (t_end - t_start) * min(step, nsteps) / nsteps

    atoms.set_constraint(FixCom())
    if steps_done == 0 and not np.any(atoms.get_momenta()):
        MaxwellBoltzmannDistribution(atoms, temperature_K=t_at(0), rng=rng)
        Stationary(atoms)
        run.log("{}: Maxwell-Boltzmann velocities at {:.1f} K".format(name, t_at(0)))
    dt = st["dt_fs"] * units.fs
    if kind == "nvt":
        from ase.md.bussi import Bussi
        dyn = Bussi(atoms, dt, temperature_K=t_at(steps_done), taut=st["taut_fs"] * units.fs,
                    rng=rng)
        dyn.transferred_energy = transferred
    else:
        from ase.md.nptberendsen import NPTBerendsen
        dyn = NPTBerendsen(atoms, dt, temperature_K=t_end, pressure_au=st["P_bar"] * units.bar,
                           taut=st["taut_fs"] * units.fs, taup=st["taup_fs"] * units.fs,
                           compressibility_au=st["compressibility_per_bar"] / units.bar,
                           fixcm=True)
    thermo, frames = "{}.thermo.csv".format(name), "{}.xyz".format(name)
    files = [thermo, frames]
    tpath, fpath = run.dir / thermo, run.dir / frames
    if steps_done == 0:
        for p in (tpath, fpath):
            if p.exists():
                p.unlink()
        tpath.write_text(",".join(THERMO_COLS) + "\n")
    else:
        for n, size in (run.state or {}).get("files", {}).items():
            _truncate(run.dir / n, size)
    check_physical(atoms, run.cfg["min_distance_A"])
    step, w0 = steps_done, run.clock()
    last_w, last_s = w0, step

    def tr():
        return getattr(dyn, "transferred_energy", 0.0)

    def record(step):
        nonlocal last_w, last_s
        w = run.clock()
        if step % int(st["thermo_every"]) == 0:
            sps = (step - last_s) / (w - last_w) if w > last_w and step > last_s else float("nan")
            with open(str(tpath), "a") as f:
                f.write(_thermo_row(atoms, step, st, kind, t_at(step), tr(), w - w0, sps) + "\n")
            last_w, last_s = w, step
        if int(st["dump_every"]) and step % int(st["dump_every"]) == 0:
            with open(str(fpath), "a") as f:
                f.write(_frame(atoms, step, st))

    if steps_done == 0:
        record(0)
    while step < nsteps:
        dyn.run(ce)
        step += ce
        if kind == "nvt" and t_start != t_end:
            dyn.temp = t_at(step) * units.kB
            dyn.target_kinetic_energy = 0.5 * dyn.temp * dyn.ndof
        check_physical(atoms, run.cfg["min_distance_A"])
        record(step)
        if step < nsteps and (step % ck == 0 or run.over_budget()):
            run.save_state(atoms, name, step, rng, tr(), files)
            if run.over_budget():
                run.log("{}: budget reached at step {}/{}; checkpoint written".format(name, step, nsteps))
                raise BudgetReached()
    if kind == "npt_berendsen":
        rows = [r.split(",") for r in tpath.read_text().splitlines()[1:]]
        iv, it = THERMO_COLS.index("volume_A3"), THERMO_COLS.index("time_ps")
        tmin = st["ps"] - st["mean_volume_last_ps"] - 1e-9
        vols = [float(r[iv]) for r in rows if float(r[it]) >= tmin]
        vmean = sum(vols) / len(vols)
        L = vmean ** (1.0 / 3.0)
        atoms.set_cell([L, L, L], scale_atoms=True)
        info = {"mean_volume_A3": vmean, "L_A": L, "rows": len(vols),
                "window_ps": st["mean_volume_last_ps"],
                "density_g_cm3": atoms.get_masses().sum() * AMU_G / (vmean * 1e-24)}
        (run.dir / "{}.volume.json".format(name)).write_text(json.dumps(info, indent=1) + "\n")
        run.log("{}: box scaled to the mean volume of the last {} ps: L = {:.6f} A, {:.4f} g/cm3".format(
            name, st["mean_volume_last_ps"], L, info["density_g_cm3"]))
    return tr()


def run(run_dir, budget_s=None, device="cuda", calc_factory=None, clock=time.monotonic,
        out=sys.stdout):
    from ase.io import read, write
    r = Run(run_dir, budget_s, clock, out)
    if (r.dir / "DONE").exists():
        r.log("all stages already done")
        return EXIT_DONE
    if (r.dir / "STOPPED").exists():
        r.log("STOPPED earlier: " + (r.dir / "STOPPED").read_text().strip())
        return EXIT_STOPPED
    calc = calc_factory() if calc_factory else make_calculator(r.cfg, device)
    rng = r.rng()
    prev = None
    try:
        for st in r.cfg["stages"]:
            name = st["name"]
            done = r.dir / "{}.done".format(name)
            if done.exists():
                prev = r.dir / "{}.final.traj".format(name)
                continue
            transferred, steps_done = 0.0, 0
            if r.state and r.state.get("stage") == name:
                atoms = read(str(r.dir / "ckpt.traj"))
                steps_done = int(r.state["steps_done"])
                transferred = float(r.state.get("transferred_energy", 0.0))
                r.log("{}: resuming at step {}".format(name, steps_done))
            elif prev is not None:
                atoms = read(str(prev))
            else:
                atoms = load_structure(r.cfg["structure"])
                r.log("start: {} atoms, L = {} A, model sha256 checked".format(
                    len(atoms), r.cfg["structure"]["box_A"]))
            atoms.calc = calc
            r.log("{}: {} stage".format(name, st["kind"]))
            if st["kind"] == "minimise":
                run_minimise(r, st, atoms)
            else:
                transferred = run_md(r, st, atoms, rng, steps_done, transferred)
            prev = r.dir / "{}.final.traj".format(name)
            write(str(prev), atoms.copy(), format="traj")
            r.save_state(None, None, 0, rng, 0.0, [])
            done.write_text(datetime.datetime.now().isoformat(timespec="seconds") + "\n")
            r.log("{}: done".format(name))
    except BudgetReached:
        return EXIT_BUDGET
    except Stopped as e:
        (r.dir / "STOPPED").write_text(str(e) + "\n")
        r.log("STOPPED: {}".format(e))
        return EXIT_STOPPED
    (r.dir / "DONE").write_text(datetime.datetime.now().isoformat(timespec="seconds") + "\n")
    r.log("all stages done")
    return EXIT_DONE


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run", help="run or resume the stages of <run_dir>/run.json")
    p.add_argument("run_dir")
    p.add_argument("--budget-s", type=float, default=None,
                   help="stop with a checkpoint (exit 3) once this many seconds have passed")
    p.add_argument("--device", default="cuda")
    a = ap.parse_args(argv)
    try:
        return run(a.run_dir, a.budget_s, a.device)
    except ConfigError as e:
        print("configuration error: {}".format(e), file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
