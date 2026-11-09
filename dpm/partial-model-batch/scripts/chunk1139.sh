#!/bin/bash
# chunk1139.sh TABLE RISK FROM TO (run on the laptop, in ~/p1139): the same frozen runner on lines FROM..TO
# of the risk-filtered table (the harness caps a foreground call at 10 min). The runner and library are
# symlinks, the table a subset of lines in file order; dumps in ~/p1139-dumps/TABLE-RISK.cFROM.
set -eu
T=$1; R=$2; F=$3; TO=$4
H=$HOME/p1139
C=$H/ch/$T-$R-$F
mkdir -p "$C/tables"
ln -sf "$H/lib1139.sh" "$C/lib1139.sh"; ln -sf "$H/run_table.sh" "$C/run_table.sh"
awk -F'|' -v r="$R" -v f="$F" -v t="$TO" '/^#/{print;next} $1==""{next} $3==r{n++; if(n>=f&&n<=t)print}' "$H/tables/$T.txt" > "$C/tables/$T.txt"
echo "chunk $T $R $F-$TO: $(grep -vc '^#' "$C/tables/$T.txt") jobs"
KEEP=$HOME/p1139-dumps/$T-$R.c$F exec "$C/run_table.sh" "$T" "$R"
