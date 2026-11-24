#!/usr/bin/env python3
"""Compare two RDF tables written by src/rdf_aimd_v1/rdf.py (same bins), pair by pair.

Usage (numpy needed):
  rdf_compare.py <test.rdf.csv> <reference.rdf.csv> [-o report.json] [--max-sigma 4]
                 [--max-peak-shift 0.04]

Per pair, on the reference: onset = first bin with g >= 0.5; first peak = max of g within
1.0 A after the onset; first minimum = min of g within 2.0 A after the peak. Quantities:
  dr_peak   peak position (test, same definition) minus reference, A;
  g_peak    g at the reference peak bin; sigma = sqrt(se_test^2 + se_ref^2);
  cn_min    cn at the reference minimum bin; its error is the upper bound
            e = sum over bins up to r of k_i * se_i, with k_i = (cn_i - cn_(i-1)) / g_i the shell
            factor read from the table (bins treated as fully correlated); sigma combines both.
A pair passes when |dr_peak| <= --max-peak-shift and |g_peak| and |cn_min| differences are
<= --max-sigma sigma. Also reported: the fraction of bins with |dg| > 2 sigma.
Pairs whose reference never reaches g = 0.5 are reported as "no peak" and not judged.
Exit 0 if every judged pair passes, 1 otherwise.
"""
import argparse
import json
import sys

import numpy as np


def read(path):
    with open(path) as f:
        cols = f.readline().strip().split(",")
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    t = {c: data[:, i] for i, c in enumerate(cols)}
    pairs = [c[2:] for c in cols if c.startswith("g_")]
    return t, pairs


def cn_error(g, se, cn):
    dcn = np.diff(np.concatenate([[0.0], cn]))
    k = np.divide(dcn, g, out=np.zeros_like(g), where=g > 1e-12)
    return np.cumsum(k * se)


def landmarks(r, g, onset_g=0.5, peak_win=1.0, min_win=2.0):
    above = np.nonzero(g >= onset_g)[0]
    if not len(above):
        return None
    i0 = above[0]
    w = np.nonzero((r >= r[i0]) & (r <= r[i0] + peak_win))[0]
    ip = w[np.argmax(g[w])]
    w = np.nonzero((r > r[ip]) & (r <= r[ip] + min_win))[0]
    im = w[np.argmin(g[w])] if len(w) else len(r) - 1
    return ip, im


def compare(test, ref, max_sigma=4.0, max_peak_shift=0.04):
    t, pairs = read(test)
    f, pairs_ref = read(ref)
    if pairs != pairs_ref or not np.allclose(t["r_center_A"], f["r_center_A"]):
        raise SystemExit("tables differ in pairs or bins")
    r = f["r_center_A"]
    out, ok = {}, True
    for p in pairs:
        gt, gf, st, sf = t["g_" + p], f["g_" + p], t["se_" + p], f["se_" + p]
        lf = landmarks(r, gf)
        if lf is None:
            out[p] = {"status": "no peak"}
            continue
        ipf, imf = lf
        lt = landmarks(r, gt)
        ipt = lt[0] if lt else ipf
        sig_g = float(np.hypot(st[ipf], sf[ipf]))
        et, ef = cn_error(gt, st, t["cn_" + p]), cn_error(gf, sf, f["cn_" + p])
        sig_cn = float(np.hypot(et[imf], ef[imf]))
        d_r = float(r[ipt] - r[ipf])
        d_g = float(gt[ipf] - gf[ipf])
        d_cn = float(t["cn_" + p][imf] - f["cn_" + p][imf])
        comb = np.hypot(st, sf)
        mask = (gt > 0) | (gf > 0)
        frac = float(np.mean(np.abs(gt - gf)[mask] > 2 * comb[mask])) if mask.any() else 0.0
        z_g = abs(d_g) / sig_g if sig_g > 0 else (0.0 if d_g == 0 else float("inf"))
        z_cn = abs(d_cn) / sig_cn if sig_cn > 0 else (0.0 if d_cn == 0 else float("inf"))
        passed = abs(d_r) <= max_peak_shift + 1e-9 and z_g <= max_sigma and z_cn <= max_sigma
        ok &= passed
        out[p] = {"status": "pass" if passed else "FAIL", "r_peak_ref_A": float(r[ipf]),
                  "dr_peak_A": d_r, "g_peak_ref": float(gf[ipf]), "dg_peak": d_g,
                  "z_g_peak": z_g, "r_min_ref_A": float(r[imf]),
                  "cn_min_ref": float(f["cn_" + p][imf]), "dcn_min": d_cn, "z_cn_min": z_cn,
                  "frac_bins_beyond_2sigma": frac}
    return ok, out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("test")
    ap.add_argument("reference")
    ap.add_argument("-o", default=None)
    ap.add_argument("--max-sigma", type=float, default=4.0)
    ap.add_argument("--max-peak-shift", type=float, default=0.04)
    a = ap.parse_args(argv)
    ok, out = compare(a.test, a.reference, a.max_sigma, a.max_peak_shift)
    rep = {"test": a.test, "reference": a.reference, "max_sigma": a.max_sigma,
           "max_peak_shift_A": a.max_peak_shift, "all_pass": ok, "pairs": out}
    if a.o:
        with open(a.o, "w") as f:
            json.dump(rep, f, indent=1)
            f.write("\n")
    print("{:6} {:>6} {:>8} {:>7} {:>7} {:>7} {:>7} {:>6}  {}".format(
        "pair", "r_pk", "dr_pk", "z_gpk", "r_min", "cn_min", "z_cn", "f>2s", "status"))
    for p, d in out.items():
        if d["status"] == "no peak":
            print("{:6} {:>63}".format(p, "no peak"))
            continue
        print("{:6} {:6.2f} {:+8.3f} {:7.2f} {:7.2f} {:7.3f} {:7.2f} {:6.3f}  {}".format(
            p, d["r_peak_ref_A"], d["dr_peak_A"], d["z_g_peak"], d["r_min_ref_A"],
            d["cn_min_ref"], d["z_cn_min"], d["frac_bins_beyond_2sigma"], d["status"]))
    print("ALL PASS" if ok else "AT LEAST ONE PAIR FAILS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
