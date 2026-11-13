#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""lgen.py: write r9-lgeo's job tables (tables/STAGE.txt), frozen predictions (predictions/STAGE.tsv
and the per-row slot files under predictions/q139b/), the probe programs (bins/, bins/SHA256SUMS)
and the fake laptop's program index (mock/progs.tsv) from the models (gen/tx6model.py over
gen/texmodel.py, gen/q139even.py over gen/q139model.py) and the published records' kept files,
every one read at the pinned resgx545-data commit (git show, never the working tree; session.toml
[freeze] pins lists them all: tests/test_gen.py checks it). Deterministic: a second run writes the
same bytes (tests/test_gen.py). Plan: closing9/seeds/exp-seeds-r9.md sections 5 and 6 (S9-lgeo).

  python3 gen/lgen.py [OUT_DIR]     (default: this session; the test writes to a scratch copy)

Table line: name|set|risk|knobs|tool|args (tool t4 = ~/sgxfive-test-rgn4; $S the staged tree,
$W the job's work directory). Prediction line: case quantity value model set source.
The programs are assembled with usse-asm built from `git archive` of the pinned resgx545 commit
(tools/usse-asm, tools/usse-dis; debug/asm, tests/run_all.sh builds it)."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import tomllib  # noqa: E402

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
import q139even as E  # noqa: E402
import scorekit  # noqa: E402
import texbuild as TB  # noqa: E402
import texcatalog as TC  # noqa: E402
import texmodel as T  # noqa: E402
import tx6model as X  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data"
ASM = os.path.join(KP, "debug/asm/tools/usse-asm/usse-asm")
R7G = "render/closing-r7-geo"
R7G_OUT = R7G + "/out/20261112-211113"
MTF = "ta/mtile-fields"
PINS = []           # every data path read (session.toml [freeze] pins must hold each as data:PATH)


def data_commit():
    with open(os.path.join(KP, "session.toml"), "rb") as f:
        return tomllib.load(f)["freeze"]["data"]


DC = data_commit()


def blob(path):
    """A resgx545-data file at the pinned commit."""
    if path not in PINS:
        PINS.append(path)
    return subprocess.run(["git", "-C", DATA, "show", "%s:%s" % (DC, path)], capture_output=True,
                          check=True).stdout


def gz_text(path):
    return gzip.decompress(blob(path)).decode(errors="replace")


ROWS, PREDS, CONTROLS, PROGS, FILES = {}, {}, [], {}, {}


def row(stage, name, sset, risk, knobs, tool, args):
    ROWS.setdefault(stage, []).append("%s|%s|%s|%s|%s|%s" % (name, sset, risk, knobs, tool, args))


def pred(stage, case, q, v, model, sset, source):
    PREDS.setdefault(stage, []).append((case, q, str(v), model, sset, source))


def control(stage, name, reads):
    CONTROLS.append((name, stage, tuple(reads)))


def pfile(rel, text):
    FILES[rel] = text


# ================================================================================ the programs
def lwin(w, h, xo=0, yo=0):
    """u, v rules of the linear axis that put texel ((x + xo) mod w, (y + yo) mod h) at pixel
    (x, y): u = (x + xo + 1/2) / w, v = (y + yo + 1/2) / h (the repeat mode wraps both). At xo =
    yo = 0 these are texcatalog.swin's rules, bit for bit (tests/test_gen.py)."""
    ku, kv = 64.0 / w, 32.0 / h
    return TC.linx(ku, -ku + (xo + 0.5) / w), TC.liny(kv, -kv + (yo + 0.5) / h)


def spec(ty, w, h, xo=0, yo=0, linear=False, fmt=12):
    u, v = lwin(w, h, xo, yo) if linear else TC.window(w, h, xo, yo)
    return dict(base=0, t0=TC.T0_REP, t1=TC.t1tw(w, h, fmt, ty), t3=TC.T3_TW, u=u, v=v, ins="none")


def assemble(sp, name, out_dir):
    tmpl = open(os.path.join(KP, "templates/tx_map.s")).read()
    pre, setup, smp = TB.case_inputs(sp)
    text = tmpl.replace("{PRE}", pre).replace("{SETUP}", setup).replace("{SMP}", smp)
    out = os.path.join(out_dir, "bins", name + ".bin")
    r = subprocess.run([ASM, "-l", "-o", out, "-"], input=text, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(name + ": " + r.stderr)
    b = open(out, "rb").read()
    assert len(b) % 8 == 0 and len(b) // 8 <= 256, (name, len(b))
    return b


def prog(name, out_dir, ty, w, h, *, xo=0, yo=0, linear=False, fmt=12, same_as=None):
    """Assemble one probe program; same_as: a published program it must equal byte for byte."""
    sp = spec(ty, w, h, xo, yo, linear, fmt)
    b = assemble(sp, name, out_dir)
    if same_as:
        assert b == blob(same_as), (name, same_as)
    meta = dict(ty=ty, w=w, h=h, xo=xo, yo=yo, linear=linear, t0=sp["t0"], fmt=fmt, stored=[])
    PROGS[hashlib.sha256(b).hexdigest()] = meta
    return "probe --temps 32 --coords --pixels \"$S/bins/%s.bin\"" % name


def kept_image(name):
    return T.probe_rows(gz_text("%s/tx/%s.txt.gz" % (R7G_OUT, name)))


# ================================================================================ tx6 (Q283)
TX_KNOBS = "after needrows"
SCRATCH = "64 KiB"          # t4's default 16 pages, every row (tests/test_gen.py reads t4's source)
WINDOWS = [(48, 64, 0, 0), (48, 64, 0, 32), (96, 32, 64, 0),
           (80, 64, 0, 0), (80, 64, 64, 0), (80, 64, 0, 32), (80, 64, 64, 32)]


def tx6(out_dir):
    st = "tx6"
    # controls: E910's type 4 64 x 32 and E725's type 3 32 x 16 map images, their programs byte for byte
    for name, ty, w, h, same, kname, hyp, src in (
            ("tx6-ctl-ty4-64x32", 4, 64, 32, R7G + "/bins/r7g-ty4-64x32.bin", "tx-ty4-64x32", "H-BLKROW", "E910"),
            ("tx6-ctl-ty3-32x16", 3, 32, 16, R7G + "/bins/r7g-ty3-32x16.bin", "tx-ctl-ty3-32x16", "RASTERW", "E725")):
        args = prog("r9l-ctl-ty%d-%dx%d" % (ty, w, h), out_dir, ty, w, h, same_as=same)
        row(st, name, "control", "safe", TX_KNOBS + " reads:rows", "t4", args)
        control(st, name, ("rows",))
        k = kept_image(kname)
        assert k and k == T.tex_image(hyp, w, h), name
        pred(st, name, "size", "%dx%d" % (w, h), "all", "control", "table")
        pred(st, name, "type", ty, "all", "control", "table")
        pred(st, name, "scratch", SCRATCH, "all", "control", "sgxfive-test.c SCRATCH_FILL over SCRATCH_PAGES")
        pred(st, name, "pixels_sha", T.sha_list(k), "kept", "control", "%s %s/tx/%s.txt.gz" % (src, R7G_OUT, kname))
    # type 4 past a multiple of 32: 64 x 32 windows through the linear axis with offsets
    for w, h, xo, yo in WINDOWS:
        name = "tx6-ty4-%dx%d-x%dy%d" % (w, h, xo, yo)
        args = prog("r9l-ty4-%dx%d-x%dy%d" % (w, h, xo, yo), out_dir, 4, w, h, xo=xo, yo=yo, linear=True)
        row(st, name, "heldout", "safe", TX_KNOBS, "t4", args)
        imgs = {hy: X.type4_image(hy, w, h, xo, yo) for hy in X.TYPE4}
        assert all(None not in im for im in imgs.values()), name       # every rival's texel inside the tag fill
        pred(st, name, "size", "%dx%d" % (w, h), "all", "heldout", "table")
        pred(st, name, "type", 4, "all", "heldout", "table")
        pred(st, name, "window", "%d,%d" % (xo, yo), "all", "heldout", "table")
        pred(st, name, "scratch", SCRATCH, "all", "heldout", "sgxfive-test.c SCRATCH_FILL over SCRATCH_PAGES")
        pred(st, name, "parts", " ".join("%s/%s" % p for p in X.parts(imgs)) or "none", "all", "heldout",
             "gen/tx6model.py")
        for hy in X.TYPE4:
            pred(st, name, "pixels_sha", T.sha_list(imgs[hy]), hy, "heldout", "gen/tx6model.py")
    # type 3's padding at a 16-bit format (5, B5G6R5), two texels a dword
    for w, h in ((4, 8), (8, 8)):
        name = "tx6-ty3-f5-%dx%d" % (w, h)
        args = prog("r9l-ty3-f5-%dx%d" % (w, h), out_dir, 3, w, h, fmt=5)
        row(st, name, "heldout", "safe", TX_KNOBS, "t4", args)
        pred(st, name, "size", "%dx%d" % (w, h), "all", "heldout", "table")
        pred(st, name, "type", 3, "all", "heldout", "table")
        pred(st, name, "format", 5, "all", "heldout", "table")
        pred(st, name, "scratch", SCRATCH, "all", "heldout", "sgxfive-test.c SCRATCH_FILL over SCRATCH_PAGES")
        words = {hy: X.pad16_words(hy, w, h) for hy in X.PAD16}
        pred(st, name, "parts", " ".join("%s/%s" % p for p in X.parts(words)) or "none", "all", "heldout",
             "gen/tx6model.py")
        for hy in X.PAD16:
            pred(st, name, "words_sha", X.words_sha(words[hy]), hy, "heldout", "gen/tx6model.py")
            pred(st, name, "pixels_sha", T.sha_list(X.pad16_image(hy, w, h)), hy, "heldout",
                 "gen/tx6model.py widen565 (sgx-sim tex.rs colour_texel, format 5)")
            pred(st, name, "words_sha", X.words_sha(X.pad16_words(hy, w, h, hi_first=True)), hy + ":hi", "reading",
                 "gen/tx6model.py the high half first (a reading, no verdict)")
    # soft, last: type 1 at 24 and 40 wide through the linear axis, with its bridge (type 1 32 x 16)
    for name, sset, w, h in (("tx6-lin-ty1-32x16", "bridge", 32, 16), ("tx6-lin-ty1-24x8", "heldout", 24, 8),
                             ("tx6-lin-ty1-40x8", "heldout", 40, 8)):
        args = prog("r9l-lin-ty1-%dx%d" % (w, h), out_dir, 1, w, h, linear=True)
        row(st, name, sset, "safe", TX_KNOBS + " soft", "t4", args)
        pred(st, name, "size", "%dx%d" % (w, h), "all", sset, "table")
        pred(st, name, "type", 1, "all", sset, "table")
        pred(st, name, "scratch", SCRATCH, "all", sset, "sgxfive-test.c SCRATCH_FILL over SCRATCH_PAGES")
        for hy in X.TYPE1:
            pred(st, name, "pixels_sha", T.sha_list(T.tex_image(hy, w, h, linear=True)), hy, sset, "gen/texmodel.py")
        if sset == "bridge":
            k = kept_image("tx-ctl-ty3-32x16")
            assert k == T.tex_image("RASTERW", 32, 16, linear=True)
            pred(st, name, "pixels_sha", T.sha_list(k), "kept", sset,
                 "E725 (types 1 and 3 read a raster of the width at 32 wide): the 32 x 16 map image")
    return ["#stage tx6", "#limit 0",
            "# Q283's remaining texture types (E910, E940, E941). Controls that can fail (kept images, reads:rows): E910's type 4",
            "# 64 x 32 and E725's type 3 32 x 16 map programs byte for byte. Held out: type 4 at 48 x 64 (windows y 0, 32), 96 x 32",
            "# (x 64) and 80 x 64 (x 0, 64 by y 0, 32) through the linear axis with offsets (texel ((x + xo) mod w, (y + yo) mod",
            "# h)); frozen H-CEIL (ceil(w / 32) blocks a block row, E941's rule) against H-P2 (the width rounded up to a power",
            "# of two) and H-PACK (a partial block (w mod 32) columns wide); 48 x 64 parts H-PACK, 80 x 64 at y 32 all three.",
            "# Type 3 at 4 x 8 and 8 x 8 of format 5 (16 bits, two texels a dword): rows of H-DW8 (max(16, w) texels: 8",
            "# dwords) against H-TX8 (max(8, w) texels) and RASTERW (w), read as 16-bit words. Soft, last: type 1 at 24 x 8 and",
            "# 40 x 8 through the linear axis (RASTERW against RASTERP2), their bridge type 1 32 x 16 through the same axis (it",
            "# must give E725's 32 x 16 image, or the two cannot tell); the second soft failure in a row stops tx6 (rc 24).",
            "# Every row at t4's default 16 scratch pages (64 KiB, 16384 dwords; no rival reads past 7151). after: the health",
            "# fill and triangle after every job. needrows: the second probe with no pixel rows stops tx6 (rc 24). No fault",
            "# expected: any fault, hang or other failure stops the stage (rc 4) and the session."]


# ================================================================================ q139b (Q139)
def q139_cmd(w, h, poke):
    return ("tri --tri-full --pixels --width %d --height %d --max-width %d --max-height %d%s --wait-ms 20000 --keep-going "
            "--dump-render \"$W\"" % (w, h, w, h, " --kpoke-render %s" % poke if poke else ""))


def image_wrong(text, w, h):
    """The kept wrong-tile set of a --pixels output (E877's reading: a tile with any pixel not 0xff00ff00)."""
    import lib_dump as L
    comp, bad = L.image_tiles(text, w, h)
    assert comp
    return bad


def q139b(out_dir):
    st = "q139b"
    ds = {}
    for ln in blob(MTF + "/cases.tsv").decode().splitlines()[1:]:
        p = ln.split("\t")
        ds[p[0]] = (int(p[2]), int(p[3]), p[4] if len(p) > 4 else "")
    jobs = [("q139b-ctl-1280x720", "control", "q100-1280x720-ctl-r1"),
            ("q139b-ctl-768x640", "control", "q100-768x640-ctl-r1"),
            ("q139b-res-768x640-m2-B3p1", "heldout", "q100-768x640-m2-B3p1"),
            ("q139b-res-1280x720-m2-B3p1", "residue", "q100-1280x720-m2-B3p1")]
    for name, sset, dsn in jobs:
        w, h, a = ds[dsn]
        poke = a.split()[1] if a else ""
        assert (a == "") == (sset == "control"), name
        knobs = "expectdiff needhash" + (" reads:hash,dump" if sset == "control" else "")
        row(st, name, sset, "safe", knobs, "t4", q139_cmd(w, h, poke))
        if sset == "control":
            control(st, name, ("hash", "dump"))
        n, bx, by, s, fx, fy = E.geometry(w, h, a)
        pred(st, name, "size", "%dx%d" % (w, h), "all", sset, "table")
        pred(st, name, "geometry", "n %d bx %s by %s S %d fx %d fy %d" % (n, ",".join(map(str, bx)), ",".join(map(str, by)),
                                                                        s, fx, fy), "all", sset, "gen/q139_fit.py")
        preds = {m: E.predict(w, h, a, m) for m in E.MODELS}
        for m in E.MODELS:
            pred(st, name, "wrong", E.tiles_text(E.wrong(preds[m])), m, sset, "gen/q139even.py")
            pfile("predictions/q139b/%s.%s.slots" % (name, m), E.slots_text(preds[m]) + "\n")
        same = [m for m in E.MODELS[1:] if preds[m] == preds["H-EVEN"]]
        pred(st, name, "same_as_H-EVEN", ",".join(same) or "none", "all", sset, "gen/q139even.py")
        kept = image_wrong(gz_text("%s/dumps/%s.txt.gz" % (MTF, dsn)), w, h)
        pred(st, name, "wrong", E.tiles_text(kept), "kept", sset, "E944 %s/dumps/%s.txt.gz" % (MTF, dsn))
        if sset != "residue":
            assert kept == E.wrong(preds["H-EVEN"]), name
        else:
            assert kept != E.wrong(preds["H-EVEN"]), name
    return ["#stage q139b", "#limit 0",
            "# Q139's residue (E944; the round 9 seeds plan section 6, after E950's offline H-EVEN: a block row of the first",
            "# macrotile takes 8 floor(fx / 2) slots, R7-BLK 16 floor(fx / 4)). The datasets' own command (ta/mtile-fields, token",
            "# for token) with --keep-going and --dump-render into the job's work directory; every row drew without a fault in its",
            "# dataset (safe class). Controls (reads:hash,dump; the scorer reads the image and the headers): the unpoked 1280 x 720",
            "# and 768 x 640 baselines, exact image and one header with a stream for every target tile; they give the header base",
            "# E944 lacked at these sizes, and their slots are scored against H-EVEN (= R7-BLK there). Held out: 768 x 640",
            "# m2-B3p1 (its dataset's 24 wrong tiles; H-EVEN = R7-BLK = the round 8 rivals there, fx 8): the wrong-tile set and",
            "# every header slot. Residue (a reading, scored nothing): 1280 x 720 m2-B3p1 (52 wrong tiles in its dataset, 40",
            "# under every model: the last y bound 37, not a multiple of 4), its slots read after the run against the baseline.",
            "# needhash: the second row without a hash stops q139b (rc 24). No fault expected: any fault or hang stops the stage",
            "# (rc 4) and the session."]


STAGES = {"tx6": tx6, "q139b": q139b}


def producible(row_):
    a = row_.split("|", 5)[5]
    if a.startswith("probe"):
        return {"rows"}
    keys = {"hash"}
    if "--dump-render" in a:
        keys.add("dump")
    return keys


def write(out_dir=KP):
    os.makedirs(os.path.join(out_dir, "bins"), exist_ok=True)
    for f in os.listdir(os.path.join(out_dir, "bins")):
        os.remove(os.path.join(out_dir, "bins", f))
    heads = {st: fn(out_dir) for st, fn in STAGES.items()}
    byname = {r.split("|")[0]: r for rows in ROWS.values() for r in rows}
    scorekit.refuse_unreadable({n: (reads, byname[n]) for n, _, reads in CONTROLS}, producible)
    for d in ("tables", "predictions", "predictions/q139b", "mock"):
        os.makedirs(os.path.join(out_dir, d), exist_ok=True)
    for f in os.listdir(os.path.join(out_dir, "predictions/q139b")):
        os.remove(os.path.join(out_dir, "predictions/q139b", f))
    for st in STAGES:
        with open(os.path.join(out_dir, "tables", st + ".txt"), "w") as f:
            f.write("\n".join(heads[st] + ROWS[st]) + "\n")
        with open(os.path.join(out_dir, "predictions", st + ".tsv"), "w") as f:
            f.write("case\tquantity\tvalue\tmodel\tset\tsource\n")
            for p in PREDS[st]:
                f.write("\t".join(p) + "\n")
    for rel, text in sorted(FILES.items()):
        with open(os.path.join(out_dir, rel), "w") as f:
            f.write(text)
    with open(os.path.join(out_dir, "bins/SHA256SUMS"), "w") as f:
        for b in sorted(os.listdir(os.path.join(out_dir, "bins"))):
            if b.endswith(".bin"):
                f.write("%s  %s\n" % (hashlib.sha256(open(os.path.join(out_dir, "bins", b), "rb").read()).hexdigest(), b))
    with open(os.path.join(out_dir, "mock/progs.tsv"), "w") as f:
        f.write("# mock/progs.tsv (gen/lgen.py): each program's sha256 and what it samples, for the fake tool\n")
        for sha, meta in sorted(PROGS.items()):
            f.write("%s\t%s\n" % (sha, json.dumps(meta, sort_keys=True)))
    with open(os.path.join(out_dir, "gen/pins.txt"), "w") as f:
        f.write("".join("data:%s\n" % p for p in sorted(PINS)))
    return {st: len(ROWS[st]) for st in STAGES}


if __name__ == "__main__":
    n = write(sys.argv[1] if len(sys.argv) > 1 else KP)
    print("tables:", ", ".join("%s %d" % kv for kv in n.items()), "; total", sum(n.values()))
