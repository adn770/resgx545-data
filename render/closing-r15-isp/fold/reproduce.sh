#!/bin/bash
# reproduce.sh: the frozen scorer re-run on the kept files must print what the run printed.
cd "$(dirname "$0")/.." || exit 1
A=out/20261114-073059
python3 -B score/score.py zcut $A/zcut > fold/score-zcut.reproduce.txt
cmp fold/score-zcut.reproduce.txt $A/score-zcut.txt && echo "score-zcut: byte-identical"
