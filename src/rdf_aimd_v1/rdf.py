#!/usr/bin/env python3
"""Partial radial distribution functions g_ab(r) and running coordination numbers n_ab(r)
for cubic periodic boxes, with block-average standard errors.

One code and one parameter set for AIMD and MLMD, so their RDFs can be compared
(method fixed in docs/rdf.md). The parameters are constants on purpose: a run cannot
change them; a different set needs a new version of this file and of the doc.

Usage (numpy needed: call an env's python explicitly, e.g. the `analysis` env):
  rdf.py aimd <run_dir> --name <system>.T<T>.aimd -o <outdir> [--check-only]
  rdf.py xyz <traj.xyz>... --box <L_A> --name <system>.T<T>.mlmd-<model> -o <outdir>
  rdf.py selftest

aimd: CP2K run dir of the legacy layout: production positions in `<sys>-pos-1.part*.xyz`
      plus `<sys>-pos-1.xyz` (the `_eq` files are equilibration and are not read), cubic
      cell from `prod.inp` (&CELL ABC). Steps written twice by restarts: the last written
      copy is kept. The run must give steps 0..10000 every 10 (1001 frames).
xyz:  frames in the order given; `i = <step>` in the comment line deduplicates as above.
Output: <outdir>/<name>.rdf.csv (r, then g, se, cn per pair) and <name>.rdf.json (metadata).
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np

PAIRS = ["Al-Cl", "Al-O", "Al-N", "Al-Al", "Cl-Cl", "Cl-H", "O-H", "C-O", "C-N", "N-H"]
RMAX = 9.70          # A; below L/2 of the smallest box (r = 1.3: L = 19.488 A)
DR = 0.02            # A, bin width
NBLOCKS = 5          # 1 ps blocks for 5 ps of production
AIMD_STEPS = list(range(0, 10001, 10))
VERSION = 1
STEP_RE = re.compile(r"\bi\s*=\s*(\d+)")


def read_xyz(paths):
    """Frames from xyz files in order; returns (elements, {step: coords}, n_read)."""
    frames, elements, n_read = {}, None, 0
    for path in paths:
        with open(path) as f:
            while True:
                head = f.readline()
                if not head.strip():
                    break
                n = int(head)
                comment = f.readline()
                rows = [f.readline().split() for _ in range(n)]
                el = np.array([r[0] for r in rows])
                if elements is None:
                    elements = el
                elif not np.array_equal(el, elements):
                    sys.exit("{}: atom order differs from the first frame".format(path))
                m = STEP_RE.search(comment)
                step = int(m.group(1)) if m else n_read
                frames[step] = np.array([r[1:4] for r in rows], dtype=float)  # last copy wins
                n_read += 1
    return elements, frames, n_read


def aimd_inputs(run_dir):
    files = sorted(glob.glob(os.path.join(run_dir, "*-pos-1.part*.xyz")))
    files = [f for f in files if "_eq-pos" not in os.path.basename(f)]
    last = [f for f in glob.glob(os.path.join(run_dir, "*-pos-1.xyz"))
            if "_eq-pos" not in os.path.basename(f)]
    if len(last) != 1:
        sys.exit("{}: expected one production *-pos-1.xyz, found {}".format(run_dir, len(last)))
    with open(os.path.join(run_dir, "prod.inp")) as f:
        m = re.search(r"&CELL.*?ABC\s*(?:\[angstrom\])?\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)",
                      f.read(), re.S | re.I)
    abc = [float(x) for x in m.groups()]
    if max(abc) - min(abc) > 1e-6:
        sys.exit("{}: cell is not cubic: {}".format(run_dir, abc))
    return files + last, abc[0]


def compute(elements, coords, L, nblocks=NBLOCKS):
    """coords: (nframes, natoms, 3). Returns r_center, r_upper, {pair: (g, se, cn)}."""
    nb = int(round(RMAX / DR))
    edges = np.linspace(0.0, nb * DR, nb + 1)
    shell = 4.0 / 3.0 * np.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    V = L ** 3
    nf = coords.shape[0]
    blocks = np.array_split(np.arange(nf), nblocks)
    out = {}
    for pair in PAIRS:
        a, b = pair.split("-")
        ia, ib = np.where(elements == a)[0], np.where(elements == b)[0]
        same = a == b
        if len(ia) == 0 or len(ib) == 0 or (same and len(ia) < 2):
            continue
        hist = np.zeros((nf, nb))
        tri = np.triu_indices(len(ia), k=1) if same else None
        for k in range(nf):
            d = coords[k, ia][:, None, :] - coords[k, ib][None, :, :]
            d -= L * np.round(d / L)
            r = np.sqrt((d * d).sum(axis=2))
            r = r[tri] if same else r.ravel()
            hist[k] = np.histogram(r, bins=edges)[0]
        if same:
            hist *= 2.0                       # i<j pairs counted for both atoms
        rho_b = (len(ia) - 1 if same else len(ib)) / V

        def g_of(h, nframes):
            per_atom = h / (nframes * len(ia))
            return per_atom / (rho_b * shell), per_atom

        g, per_atom = g_of(hist.sum(axis=0), nf)
        gb = np.array([g_of(hist[idx].sum(axis=0), len(idx))[0] for idx in blocks])
        se = gb.std(axis=0, ddof=1) / np.sqrt(nblocks)
        out[pair] = (g, se, np.cumsum(per_atom))
    centers = 0.5 * (edges[1:] + edges[:-1])
    return centers, edges[1:], out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_state():
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        head = subprocess.check_output(["git", "-C", here, "rev-parse", "HEAD"],
                                       universal_newlines=True).strip()
        dirty = subprocess.check_output(["git", "-C", here, "status", "--porcelain", "--",
                                         "."], universal_newlines=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True
    return head, bool(dirty)


def write(outdir, name, centers, uppers, res, meta):
    os.makedirs(outdir, exist_ok=True)
    cols, data = ["r_center_A", "r_upper_A"], [centers, uppers]
    for pair, (g, se, cn) in res.items():
        cols += ["g_" + pair, "se_" + pair, "cn_" + pair]
        data += [g, se, cn]
    np.savetxt(os.path.join(outdir, name + ".rdf.csv"), np.column_stack(data),
               delimiter=",", header=",".join(cols), comments="", fmt="%.6f")
    with open(os.path.join(outdir, name + ".rdf.json"), "w") as f:
        json.dump(meta, f, indent=1, sort_keys=True)
        f.write("\n")


def run(paths, L, name, outdir, mode, check_only, require_steps):
    elements, frames, n_read = read_xyz(paths)
    steps = sorted(frames)
    if require_steps is not None and steps != require_steps:
        sys.exit("{}: steps {}..{} ({} unique) instead of 0..10000 every 10 (1001)".format(
            name, steps[0], steps[-1], len(steps)))
    counts = {str(e): int((elements == e).sum()) for e in sorted(set(elements))}
    print("{}: {} frames read, {} unique, steps {}..{}, L = {} A, atoms {}".format(
        name, n_read, len(steps), steps[0], steps[-1], L, counts))
    if check_only:
        return
    commit, dirty = repo_state()
    if dirty:
        sys.exit("src/ has uncommitted changes: commit before computing (record the commit)")
    coords = np.array([frames[s] for s in steps])
    centers, uppers, res = compute(elements, coords, L)
    meta = {
        "name": name, "mode": mode, "rdf_version": VERSION, "pairs": list(res),
        "rmax_A": RMAX, "dr_A": DR, "nblocks": NBLOCKS, "box_A": L, "atoms": counts,
        "frames_used": len(steps), "frames_read": n_read, "step_first": steps[0],
        "step_last": steps[-1], "sources": [{"path": os.path.abspath(p), "sha256": sha256(p)}
                                            for p in paths],
        "repo_commit": commit, "script_sha256": sha256(os.path.abspath(__file__)),
        "numpy": np.__version__, "python": sys.version.split()[0],
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "definition": "g: all pairs (intra + inter), minimum image, cubic box; se: standard "
                      "error of the block means (blocks of consecutive frames); cn: running "
                      "count of b atoms per a atom up to r_upper",
    }
    write(outdir, name, centers, uppers, res, meta)
    print("wrote {}/{}.rdf.csv and .json".format(outdir, name))


def selftest():
    rng = np.random.default_rng(7)
    L, nf = 20.0, 200
    elements = np.array(["Al"] * 40 + ["Cl"] * 120 + ["O"] * 40 + ["N"] * 40 + ["C"] * 40
                        + ["H"] * 120)
    coords = rng.uniform(-L, 2 * L, size=(nf, len(elements), 3))   # unwrapped on purpose
    centers, uppers, res = compute(elements, coords, L)
    ok = True
    for pair, (g, se, cn) in res.items():
        a, b = pair.split("-")
        nb_ = (elements == b).sum() - (1 if a == b else 0)
        mask = centers > 3.0
        mean_g = g[mask].mean()
        cn_ideal = nb_ / L ** 3 * 4.0 / 3.0 * np.pi * uppers[-1] ** 3
        good = abs(mean_g - 1) < 0.01 and abs(cn[-1] / cn_ideal - 1) < 0.01 and se.max() > 0
        ok &= good
        print("{:6s} <g(r>3)> = {:.4f}  cn(rmax)/ideal = {:.4f}  {}".format(
            pair, mean_g, cn[-1] / cn_ideal, "ok" if good else "FAIL"))
    # two atoms at a known distance across the boundary: one count in the right bin
    el2 = np.array(["Al", "Cl"])
    c2 = np.array([[[0.5, 0.0, 0.0], [L - 1.61, 0.0, 0.0]]] * 5)   # minimum image: 2.11 A
    _, up2, res2 = compute(el2, c2, L)
    k = int(np.argmax(res2["Al-Cl"][2] > 0.5))
    good = abs(up2[k] - 2.12) < 1e-9 and abs(res2["Al-Cl"][2][-1] - 1.0) < 1e-12
    ok &= good
    print("Al-Cl at 2.11 A across the boundary: first count at r_upper = {:.2f}  {}".format(
        up2[k], "ok" if good else "FAIL"))
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("aimd")
    pa.add_argument("run_dir")
    pa.add_argument("--name", required=True)
    pa.add_argument("-o", "--outdir", default=".")
    pa.add_argument("--check-only", action="store_true")
    px = sub.add_parser("xyz")
    px.add_argument("traj", nargs="+")
    px.add_argument("--box", type=float, required=True)
    px.add_argument("--name", required=True)
    px.add_argument("-o", "--outdir", default=".")
    px.add_argument("--check-only", action="store_true")
    sub.add_parser("selftest")
    a = p.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "aimd":
        paths, L = aimd_inputs(a.run_dir)
        run(paths, L, a.name, a.outdir, "aimd", a.check_only, AIMD_STEPS)
    else:
        run(a.traj, a.box, a.name, a.outdir, "xyz", a.check_only, None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
