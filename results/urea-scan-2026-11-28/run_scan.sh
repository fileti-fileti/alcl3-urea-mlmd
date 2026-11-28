#!/bin/bash
# urea_scan.py over the pilot, superseded, setup-check, AIMD (Davi's copy) and Davi's MLMD
# trajectories; written 2026-11-28 by the agent. Run in a clean login shell (no $HOME profile).
set -u
R=/scratch/acmes/eudes.fileti3/projects/alcl3-urea-mlmd; D=$R/runs/urea-scan; O=$D/out
DV=/scratch/acmes/davi.fileti/mlff-efficiency-studies
A=$DV/data/raw/alcl3_urea/dataset_AlCl3urea_AIMD; M=$DV/runs/rdf/alcl3_urea/run2r10m0
P=/scratch/acmes/eudes.fileti3/projects/shared/envs/mace0316_env/bin/python
cd $R || exit 5
[ -z "$(git status --porcelain)" ] || { echo "dirty tree: refused"; exit 6; }
COMMIT=$(git rev-parse HEAD); CODE=$(sha256sum src/urea_scan.py | cut -c1-64)
echo -e "name\tinput\tbox_A\tinput_sha256\tcommit\turea_scan_sha256" > $D/MANIFEST.tsv
lat() { sed -n 2p "$1" | sed -E 's/.*Lattice="([0-9.]+) .*/\1/'; }
one() {  # name input box
  echo -e "$1\t$2\t$3\t$(sha256sum "$2" | cut -c1-64)\t$COMMIT\t$CODE" >> $D/MANIFEST.tsv
  $P -I src/urea_scan.py "$2" --box "$3" --csv $O/$1.csv -o $O/$1.json > $O/$1.log 2>&1 || echo "FAILED $1 (see out/$1.log)"
}
echo "start $(date -Is) commit $COMMIT"
one pilot-r10-T400-reag.prod runs/pilot-r10-T400-reag/prod.xyz 29.729979 &
one pilot-r10-T400-ion.prod runs/pilot-r10-T400-ion/prod.xyz 29.729979 &
one superseded-pilot-r10-T400-reag.prod runs/_superseded/pilot-r10-T400-reag/prod.xyz $(lat runs/_superseded/pilot-r10-T400-reag/prod.xyz) &
one superseded-pilot-r10-T400-ion.prod runs/_superseded/pilot-r10-T400-ion/prod.xyz $(lat runs/_superseded/pilot-r10-T400-ion/prod.xyz) &
one setup-r10neut-T400.prod runs/setup-r10neut-T400/prod.xyz 19.581168
tail -n +2 $A/manifest.csv | while IFS=, read T run src nat comp box rest; do
  L=${box%% *}
  for ph in eq prod; do
    one aimd-${T}-${run}.$ph $A/$T/$run/${ph}_pos.xyz $L
    one davi-${T}-${run}.$ph $M/${T}_$run/$ph.xyz $L
  done
done
wait
echo "end $(date -Is); outputs: $(ls $O/*.json | wc -l) json; failures: $(grep -c FAILED $D/run.log 2>/dev/null)"
