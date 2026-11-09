#!/bin/bash
# analyze1138.sh DIR OUTDIR: the frozen recompute and the post-freeze extras on one dump directory (numpy: ~/src/nhc/.venv).
PY=${PY:-$HOME/src/nhc/.venv/bin/python}
cd "$(dirname "$0")" || exit 1
D=$1; O=$2; mkdir -p "$O"
$PY -W ignore recompute/recompute_p1138.py "$D" > "$O/recompute.txt" 2>&1
$PY -W ignore recompute/extra_p1138.py "$D" > "$O/extra-sweeps.txt" 2>&1
$PY -W ignore recompute/extra2_p1138.py "$D" > "$O/extra2-errors.txt" 2>&1
$PY -W ignore recompute/extra3_p1138.py "$D" fit,heldout > "$O/extra3-f32-planes.txt" 2>&1
$PY -W ignore recompute/extra5_p1138.py "$D" fit,heldout > "$O/extra5-snaps.txt" 2>&1
$PY -W ignore recompute/extra6_p1138.py "$D" > "$O/extra6-pairs.txt" 2>&1
ls -la "$O"
