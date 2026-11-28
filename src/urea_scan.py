#!/usr/bin/env python3
"""Protonation and Al binding of every urea, frame by frame (neumann census radii).

Usage (numpy needed: the MLMD venv):
  urea_scan.py <traj.xyz> --box <L_A> [--blocks 5] [--csv per_frame.csv] [-o summary.json]

Radii as the neumann census (CLAUDE.md, Same model, same census): bond if d < r_i + r_j with
H 0.37, C 1.0, N 1.0, O 1.0, Al 1.0 A; minimum image, cubic box. Each N and O belongs to the
urea of its nearest C if bonded to it (d < 2.0 A; otherwise an orphan atom). Each H belongs to
its nearest N or O if bonded to it (d < 1.37 A; otherwise an unbonded H). Per urea: the number
of its H and how many sit on O; Al-bound through O and/or N if an Al is within 2.0 A of that
atom. Classes: normal (4 H, none on O), tautomer (4 H, one or more on O), ureate (3 H or
fewer), uronium (5 H or more); free (no Al bond), Al-O, Al-N, Al-NO (both).
A frame "with transfer" has at least one tautomer, ureate or uronium.
Frames: plain xyz (element x y z ...), as src/mlmd.py and CP2K write; the element order must
not change. A truncated last frame (a running job) is dropped and reported.
Used by: journal 2026-11-28 (urea proton transfer), docs/experiments/pilot-r10-T400.md.
"""
import argparse
import csv
import json
import sys

import numpy as np

R = {"H": 0.37, "C": 1.0, "N": 1.0, "O": 1.0, "Al": 1.0}
COLUMNS = ["frame", "free", "al_O", "al_N", "al_NO", "normal", "tautomer", "ureate", "uronium",
           "h_on_O", "orphan_NO", "unbonded_H"]


def iter_frames(path, info):
    """Yield (elements, positions) per complete frame; info["partial_last_frame"] tells if a
    truncated last frame was dropped."""
    info["partial_last_frame"] = False
    sym0 = None
    with open(path) as f:
        while True:
            head = f.readline()
            if not head.strip():
                return
            n = int(head)
            f.readline()
            rows = [f.readline().split() for _ in range(n)]
            if any(len(r) < 4 for r in rows):
                if f.read(1) == "":
                    info["partial_last_frame"] = True
                    return
                raise ValueError("{}: malformed frame".format(path))
            sym = [r[0] for r in rows]
            if sym0 is None:
                sym0 = sym
            elif sym != sym0:
                raise ValueError("{}: element order changes between frames".format(path))
            yield sym0, np.array([[float(v) for v in r[1:4]] for r in rows])


def scan_frame(sym, X, box):
    """Counts of one frame (dict with the COLUMNS except "frame")."""
    sym = np.asarray(sym)
    iC, iN, iO, iH, iAl = (np.where(sym == e)[0] for e in ("C", "N", "O", "H", "Al"))
    if not len(iC):
        raise ValueError("no C atom: no urea")

    def dist(a, b):
        v = X[a][:, None, :] - X[b][None, :, :]
        v -= box * np.round(v / box)
        return np.linalg.norm(v, axis=2)

    het = np.concatenate([iN, iO])
    is_O = np.r_[np.zeros(len(iN), bool), np.ones(len(iO), bool)]
    dC = dist(het, iC)
    owner = dC.argmin(axis=1)
    orphan = dC[np.arange(len(het)), owner] >= R["C"] + R["N"]
    owner[orphan] = -1

    dH = dist(iH, het)
    j = dH.argmin(axis=1)
    bonded = dH[np.arange(len(iH)), j] < R["H"] + R["N"]
    on_urea = bonded & (owner[j] >= 0)
    nH = np.zeros(len(iC), int)
    nHO = np.zeros(len(iC), int)
    np.add.at(nH, owner[j[on_urea]], 1)
    np.add.at(nHO, owner[j[on_urea & is_O[j]]], 1)

    alO = np.zeros(len(iC), bool)
    alN = np.zeros(len(iC), bool)
    if len(iAl):
        near = dist(het, iAl).min(axis=1) < R["Al"] + R["N"]
        alN[owner[near & ~is_O & (owner >= 0)]] = True
        alO[owner[near & is_O & (owner >= 0)]] = True

    return {"free": int((~alO & ~alN).sum()), "al_O": int((alO & ~alN).sum()),
            "al_N": int((alN & ~alO).sum()), "al_NO": int((alO & alN).sum()),
            "normal": int(((nH == 4) & (nHO == 0)).sum()),
            "tautomer": int(((nH == 4) & (nHO > 0)).sum()),
            "ureate": int((nH <= 3).sum()), "uronium": int((nH >= 5).sum()),
            "h_on_O": int((bonded & is_O[j]).sum()), "orphan_NO": int(orphan.sum()),
            "unbonded_H": int((~bonded).sum())}


def summarise(rows, nblocks):
    keys = COLUMNS[1:]
    a = np.array([[r[k] for k in keys] for r in rows])
    moved = (a[:, keys.index("tautomer")] + a[:, keys.index("ureate")]
             + a[:, keys.index("uronium")]) > 0
    blocks = [{"first_frame": int(i[0]), "last_frame": int(i[-1]),
               "mean": {k: float(a[i, c].mean()) for c, k in enumerate(keys)}}
              for i in np.array_split(np.arange(len(rows)), nblocks) if len(i)]
    return {"frames": len(rows), "frames_with_transfer": int(moved.sum()),
            "first_transfer_frame": int(moved.argmax()) if moved.any() else None,
            "max": {k: int(a[:, c].max()) for c, k in enumerate(keys)},
            "first": {k: rows[0][k] for k in keys}, "last": {k: rows[-1][k] for k in keys},
            "blocks": blocks}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("traj")
    ap.add_argument("--box", type=float, required=True)
    ap.add_argument("--blocks", type=int, default=5)
    ap.add_argument("--csv", default=None, help="per-frame counts")
    ap.add_argument("-o", default=None, help="summary JSON")
    a = ap.parse_args(argv)
    info, rows, ureas = {}, [], None
    for k, (sym, X) in enumerate(iter_frames(a.traj, info)):
        if ureas is None:
            ureas = sym.count("C")
        rows.append(dict(frame=k, **scan_frame(sym, X, a.box)))
    if not rows:
        raise ValueError("{}: no complete frame".format(a.traj))
    out = dict(traj=a.traj, box_A=a.box, ureas=ureas,
               partial_last_frame=info["partial_last_frame"], **summarise(rows, a.blocks))
    print("{}: {} ureas, {} frames{}, {} with transfer (first: {})".format(
        a.traj, ureas, out["frames"], " (truncated last frame dropped)" if
        out["partial_last_frame"] else "", out["frames_with_transfer"], out["first_transfer_frame"]))
    print("last frame: " + ", ".join("{} {}".format(k, v) for k, v in out["last"].items()))
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
    if a.o:
        with open(a.o, "w") as f:
            json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
