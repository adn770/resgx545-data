# SPDX-License-Identifier: MIT
"""Post hoc (2026-11-11, at the fold; not frozen, not the analysis): what the kept dumps of g4-rw's 20 table jobs hold,
decoded by the frozen scorer's own decode_object, against the frozen window positions.  Run with the scratch venv and
RESGX545_MAIN naming a tree with tools/usse-asm/pbdump.py:
  python -I fold/posthoc_rw_objects.py > fold/posthoc_rw_objects.txt"""
import gzip
import pathlib
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R4 / "score"))
import score_rw as S  # noqa: E402

out = R4 / "out/20261111-210423/g4-rw"
preds = {}
for line in (R4 / "predictions/g4-rw.tsv").read_text().splitlines():
    p = line.split("\t")
    if len(p) >= 3:
        preds.setdefault(p[0], {})[p[1]] = p[2]
for j in [f"rw-{i:02d}" for i in range(1, 21)]:
    d = S.decode_object(gzip.open(out / f"{j}.{j}.param.bin.gz").read(), gzip.open(out / f"{j}.{j}.tadata.bin.gz").read())
    xy = " ".join(f"({x:.3f},{y:.3f})" for x, y in d.get("xy") or [])
    edge = all(x in (-16.0, 80.0) or y in (-16.0, 80.0) for x, y in d.get("xy") or [])
    print(f"{j} {d['state']} nvert {d.get('nvert')} every vertex on x or y = -16 or 80: {edge}")
    print(f"   stored {xy}")
    print(f"   frozen {preds[j]['xy_ordered']}")
