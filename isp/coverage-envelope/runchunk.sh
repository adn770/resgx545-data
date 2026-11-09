#!/bin/bash
# runchunk.sh FIRST LAST [extra args]: run the laptop script for cases FIRST..LAST into ~/p1140-dumps/main (appending)
F=$1; L=$2; shift 2
ssh -o HostKeyAlias=cedar -o ConnectTimeout=15 jtorra@10.42.0.2 "cd ~/p1140-run && date +%s >> ~/p1140-dumps/main.epochs && python3 -B run/run_p1140.py --cases cases-1140.tsv --out ~/p1140-dumps/main --first $F --last $L --resume $* 2>&1 | tail -15"
