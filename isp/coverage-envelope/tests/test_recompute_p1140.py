"""a synthetic dump directory built from a model hardware: the recompute must pass for the right one and fail for another"""
import gzip
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "recompute"))
import model1140 as M  # noqa: E402

PY = sys.executable


def rle(img):
    lines = []
    for y, row in enumerate(img):
        runs, x = [], 0
        while x < len(row):
            e = x + 1
            while e < len(row) and row[e] == row[x]:
                e += 1
            runs.append("0x%08xx%d" % (0xFF00FF00 if row[x] else 0xFF203040, e - x))
            x = e
        lines.append("rle %d: %s" % (y, " ".join(runs)))
    return "\n".join(lines)


def build(tmp, hw_round, picks):
    rows = [l.split("\t") for l in open(os.path.join(ROOT, "cases-1140.tsv")) if l.strip()]
    sel = [r for r in rows if (r[2], r[1]) in picks][:0]
    sel = []
    for grp, st, n in picks:
        sel += [r for r in rows if r[2] == grp and r[1] == st][:n]
    os.makedirs(tmp / "raw")
    with open(tmp / "cases-1140.tsv", "w") as f:
        for r in sel:
            f.write("\t".join(r) + "\n")
    with open(tmp / "jobs.tsv", "w") as j:
        for r in sel:
            w, h, k = int(r[4]), int(r[5]), int(r[6])
            V = np.array([int(x) for x in r[7:13]]).reshape(3, 2)
            img = M.coverage(V, k, w, h, hw_round)
            txt = "tri: clip0 0x0 0x0 0x0 0x0\n%s\ntri %dx%d #1: %d triangle, %d background, 0 other; wrong 0\n" % (
                rle(img), w, h, img.sum(), img.size - img.sum())
            with gzip.open(tmp / "raw" / ("%s.txt.gz" % r[0]), "wb") as g:
                g.write(txt.encode())
            j.write("%s\t0\t0.1\t1\tx\t-\tcmd\n" % r[0])


def run(tmp):
    r = subprocess.run([PY, "-B", os.path.join(ROOT, "recompute/recompute_p1140.py"), str(tmp), "--groups=S2,S3"],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_the_model_hardware_passes_and_another_rounding_fails(tmp_path):
    picks = [("S3", "fit", 12), ("S3", "heldout", 6), ("S2", "fit", 30)]
    build(tmp_path / "a", "HU", picks)
    out = run(tmp_path / "a")
    assert "P5   PASS" in out and "P3   PASS" in out, out
    build(tmp_path / "b", "HD", picks)
    out = run(tmp_path / "b")
    assert "P5   FAIL" in out and "P3   FAIL" in out, out
