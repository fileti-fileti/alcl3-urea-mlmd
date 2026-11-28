#!/bin/bash
# urea_scan.py on the start structures of the 15 AIMD compositions: packed (01_geo/<s>/init.xyz),
# GEO_OPT trajectory (01_geo/<s>/<s>-pos-1.xyz) and AIMD start (dataset T400/<s>/init.xyz).
# Written 2026-11-28 by the agent. Run in a clean login shell (no $HOME profile).
set -u
R=/scratch/acmes/eudes.fileti3/projects/alcl3-urea-mlmd; D=$R/runs/urea-scan/geo; O=$D/out
G=/scratch/acmes/eudes.fileti3/projects/alcl3_urea_data/01_geo
A=/scratch/acmes/davi.fileti/mlff-efficiency-studies/data/raw/alcl3_urea/dataset_AlCl3urea_AIMD
P=/scratch/acmes/eudes.fileti3/projects/shared/envs/mace0316_env/bin/python
cd $R || exit 5
[ -z "$(git status --porcelain)" ] || { echo "dirty tree: refused"; exit 6; }
COMMIT=$(git rev-parse HEAD); CODE=$(sha256sum src/urea_scan.py | cut -c1-64)
echo -e "name\tinput\tbox_A\tinput_sha256\tcommit\turea_scan_sha256" > $D/MANIFEST.tsv
one() {
  echo -e "$1\t$2\t$3\t$(sha256sum "$2" | cut -c1-64)\t$COMMIT\t$CODE" >> $D/MANIFEST.tsv
  $P -I src/urea_scan.py "$2" --box "$3" --csv $O/$1.csv -o $O/$1.json > $O/$1.log 2>&1 || echo "FAILED $1"
}
echo "start $(date -Is) commit $COMMIT"
for s in r10_fora r10_ion r10_mist r10_neut r10_reag r13_ionA r13_ionB r13_mist r13_neut r13_reag r15_ionA r15_ionB r15_mist r15_neut r15_reag; do
  case $s in r10*) L=19.581168;; r13*) L=19.487537;; r15*) L=20.550878;; esac
  one $s.packed $G/$s/init.xyz $L; one $s.geoopt $G/$s/$s-pos-1.xyz $L; one $s.aimdinit $A/T400/$s/init.xyz $L
done
echo "end $(date -Is); json: $(ls $O/*.json | wc -l)"
