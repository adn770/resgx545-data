#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/q139b_lastflag.py (post hoc, the fold, not frozen): a reading of the 1280 x 720 residue,
checked on every kept dump. H-LAST [infer]: the headers of a macrotile are read in slot order up
to the one whose flags have bit 7 set (the TA's last region of the macrotile); a tile is drawn
iff its header sits at or before that slot. Per job: tiles drawn / wrong, and how many of each
the reading gets right (the headers from the same size's baseline base, lib_dump). Inputs: r9-lgeo
out/20261113-080029/q139b and r8-lgeo's kept q139 dumps (resgx545-data at 2d666bfa, git show).
    python3 fold/q139b_lastflag.py"""
import gzip
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("kit", "gen", "score"):
    sys.path.insert(0, os.path.join(KP, d))
import kitscore as K  # noqa: E402
import lib_dump as L  # noqa: E402

DATA, DC = "/Users/jtorra/src/resgx545-data", "2d666bfafa21c4d0de0e1e5e87c10dada15b7e45"
R8 = "render/closing-r8-lgeo/out/20261113-024441/q139/"


def r8(n):
    g = lambda p: gzip.decompress(subprocess.run(["git", "-C", DATA, "show", "%s:%s%s" % (DC, R8, p)],  # noqa: E731
                                                 capture_output=True, check=True).stdout)
    return g(n + ".txt.gz").decode(), g(n + ".tri.param.bin.gz"), g(n + ".tri.tadata.bin.gz")


def r9(n):
    d = os.path.join(KP, "out/20261113-080029/q139b")
    return (K.text(d, n + ".txt"), L.read_bytes(os.path.join(d, n + ".tri.param.bin")),
            L.read_bytes(os.path.join(d, n + ".tri.tadata.bin")))


def size(text):
    import re
    m = re.search(r"render context for targets up to (\d+)x(\d+)", text)
    return int(m.group(1)), int(m.group(2))


def check(name, job, base):
    text, par, tad = job
    w, h = size(text)
    comp, bad = L.image_tiles(text, w, h)
    hs = L.headers(tad, base, stop_zero=1 << 30)
    last = sorted(i for i, c, r, fl, st in hs if fl & 0x80)
    want = L.target_tiles(w, h)
    # a target tile's header with a stream is read iff its slot is at or before the last-flagged one
    pred_drawn = {L.tile_of(c, r) for i, c, r, fl, st in hs if st and last and i <= last[-1]} & want
    got = want - bad
    right = len((pred_drawn & got)) + len((want - pred_drawn) & bad)
    print("%-40s %4dx%-4d wrong %3d; last-flag slots %d (max %s); H-LAST right on %d of %d tiles" % (
        name, w, h, len(bad), len(last), last[-1] if last else "-", right, len(want)))
    return right == len(want)


bases = {}
for n, src in (("q139-ctl-256x256", r8), ("q139-ctl-640x480", r8), ("q139b-ctl-1280x720", r9), ("q139b-ctl-768x640", r9)):
    j = src(n)
    ok, txt, ly = L.baseline_layout(j[2], j[1], *size(j[0]))
    bases[size(j[0])] = ly["base"]
jobs = [(n, r8) for n in ("q139-ctl-256x256", "q139-ctl-640x480", "q139-ctl-256x256-stride-4", "q139-fit-256x256-stride-1",
                          "q139-fit-256x256-stride-2") + tuple("q139-h-256x256-stride-%d" % s for s in (3, 5, 6, 7, 12, 20))
        + tuple("q139-h-640x480-stride-%d" % s for s in (5, 6, 7, 8, 12))
        + ("q139-res-256x256-m1-B2-10", "q139-res-256x256-m1-B2-11", "q139-res-640x480-m1-B1-23", "q139-res-1280x720-m2-B3p1")]
jobs += [(n, r9) for n in ("q139b-ctl-1280x720", "q139b-ctl-768x640", "q139b-res-768x640-m2-B3p1", "q139b-res-1280x720-m2-B3p1")]
n_ok = 0
for n, src in jobs:
    j = src(n)
    wh = size(j[0])
    if wh not in bases:
        print("%-40s no baseline base" % n)
        continue
    n_ok += check(n, j, bases[wh])
print("H-LAST right on every tile of %d of %d jobs" % (n_ok, len(jobs)))

# the model side, no dump read: H-EVEN's surviving headers, the last-region flag on the header of the last
# target tile the TA writes in block order, a tile drawn iff its slot is at or before that one
sys.path.insert(0, os.path.join(KP, "gen"))
import q139even as E  # noqa: E402
import q139model as Q  # noqa: E402


def model_wrong(w, h, a):
    pred = E.predict(w, h, a, "H-EVEN")
    key = Q.KEYS["blkrow"]
    n, bx, by, s, fx, fy = E.geometry(w, h, a)
    lastt = max((t for t, v in pred.items() if v is not None), key=lambda t: key(t[1], t[0], 0, 0, n))
    return {t for t, v in pred.items() if v is None or v > pred[lastt]}


tab = {}
for ln in subprocess.run(["git", "-C", DATA, "show", "%s:render/closing-r8-lgeo/tables/q139.txt" % DC],
                         capture_output=True, check=True, text=True).stdout.splitlines():
    if ln and not ln.startswith("#"):
        p = ln.split("|", 5)
        tab[p[0]] = p[5]
for ln in open(os.path.join(KP, "tables/q139b.txt")):
    if ln.strip() and not ln.startswith("#"):
        p = ln.rstrip("\n").split("|", 5)
        tab[p[0]] = p[5]
m_ok = 0
for n, src in jobs:
    text = src(n)[0]
    w, h = size(text)
    a = " ".join("--kpoke-render " + x for x in __import__("re").findall(r"--kpoke-render (\S+)", tab[n]))
    comp, bad = L.image_tiles(text, w, h)
    mw = model_wrong(w, h, a)
    plain = E.wrong(E.predict(w, h, a, "H-EVEN"))
    m_ok += mw == bad
    print("%-40s H-EVEN %s, H-EVEN + H-LAST %s (%d wrong)" % (n, "=" if plain == bad else "differs",
                                                            "=" if mw == bad else "differs", len(bad)))
print("H-EVEN + H-LAST gives the wrong-tile set of %d of %d jobs" % (m_ok, len(jobs)))
