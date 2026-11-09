#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""The bilinear jobs of the 11.39 texture batch in the form the vector converter reads.

    make_raw.py DATA

DATA is the data repository. For the 8 jobs of texture/p1141/out-hw/p1141tex-dumps/tex-b-bilin
(cases.tsv order) it writes texture/p1141-recomp/raw/p1141-bilin/raw.txt, each job's output
preceded by a `probe-case NAME` line, with the programs the jobs ran (texture/p1141/stage-bins)
in bins/. The probe table (raw/p1141-bilin.toml) and the template (raw/tx_map.s) are copies of
texture/p1141/probes/p1141-bilin.toml and templates/tx_map.s. Standard library only.
"""
import csv
import gzip
import pathlib
import shutil
import sys

data = pathlib.Path(sys.argv[1])
src = data / "texture/p1141"
raw = data / "texture/p1141-recomp/raw"
dumps = src / "out-hw/p1141tex-dumps/tex-b-bilin"
(raw / "p1141-bilin/bins").mkdir(parents=True, exist_ok=True)
shutil.copyfile(src / "probes/p1141-bilin.toml", raw / "p1141-bilin.toml")
shutil.copyfile(src / "templates/tx_map.s", raw / "tx_map.s")
out = []
for row in csv.DictReader(open(dumps / "cases.tsv"), delimiter="\t"):
    out.append(f"probe-case {row['bin'][:-4]}\n" + gzip.open(dumps / f"{row['name']}.txt.gz", "rt").read())
    shutil.copyfile(src / "stage-bins" / row["bin"], raw / "p1141-bilin/bins" / row["bin"])
(raw / "p1141-bilin/raw.txt").write_text("".join(out))
