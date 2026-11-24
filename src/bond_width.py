#!/usr/bin/env python3
"""Spread of one bond type per block of frames: a thermometer for stiff bonds (e.g. N-H).

Usage (numpy needed: the MLMD venv):
  bond_width.py <traj.xyz> --box <L_A> [--pair N H] [--cut 1.2] [--blocks 5] [-o out.json]

Bonds: each atom of the second element is paired, in the first frame, with its nearest atom of
the first element if closer than --cut (minimum image, cubic box); the pairs are kept for all
frames. Per block of consecutive frames: the standard deviation of all those bond lengths
pooled (A) and their mean. Frames: plain xyz (element x y z ...), as src/mlmd.py and CP2K write.
Used by docs/experiments/thermostat-check-r10neut-T400.md.
"""
import argparse
import json
import sys

import numpy as np


def read_xyz(path):
    lines = open(path).read().splitlines()
    n = int(lines[0])
    nf = len(lines) // (n + 2)
    if nf < 1 or nf * (n + 2) != len(lines):
        raise ValueError("{}: not a sequence of {}-atom frames".format(path, n))
    sym = [line.split()[0] for line in lines[2:2 + n]]
    X = np.empty((nf, n, 3))
    for f in range(nf):
        X[f] = [[float(v) for v in line.split()[1:4]] for line in lines[f * (n + 2) + 2:(f + 1) * (n + 2)]]
    return sym, X


def widths(sym, X, box, a, b, cut, nblocks):
    sym = np.array(sym)
    ia, ib = np.where(sym == a)[0], np.where(sym == b)[0]
    if not len(ia) or not len(ib):
        raise ValueError("no {} or no {} atoms".format(a, b))

    def mic(v):
        return v - box * np.round(v / box)

    D = np.linalg.norm(mic(X[0, ib][:, None] - X[0, ia][None]), axis=2)
    ok = D.min(axis=1) < cut
    pb, pa = ib[ok], ia[D.argmin(axis=1)][ok]
    r = np.linalg.norm(mic(X[:, pb] - X[:, pa]), axis=2)
    blocks = [{"first_frame": int(i[0]), "last_frame": int(i[-1]), "std_A": float(r[i].std()),
               "mean_A": float(r[i].mean())} for i in np.array_split(np.arange(len(X)), nblocks)]
    return {"pair": "{}-{}".format(a, b), "cut_A": cut, "bonds": int(ok.sum()), "frames": len(X),
            "blocks": blocks}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("traj")
    ap.add_argument("--box", type=float, required=True)
    ap.add_argument("--pair", nargs=2, default=["N", "H"])
    ap.add_argument("--cut", type=float, default=1.2)
    ap.add_argument("--blocks", type=int, default=5)
    ap.add_argument("-o", default=None)
    a = ap.parse_args(argv)
    sym, X = read_xyz(a.traj)
    out = dict(widths(sym, X, a.box, a.pair[0], a.pair[1], a.cut, a.blocks), traj=a.traj, box_A=a.box)
    print("{} bonds {} in {} frames of {}".format(out["bonds"], out["pair"], out["frames"], a.traj))
    for k, blk in enumerate(out["blocks"], 1):
        print("block {} (frames {}-{}): std {:.4f} A, mean {:.4f} A".format(
            k, blk["first_frame"], blk["last_frame"], blk["std_A"], blk["mean_A"]))
    if a.o:
        with open(a.o, "w") as f:
            json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
