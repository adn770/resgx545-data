#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r14-isp's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the three
stages (wind, g14, clipr, in run order) and the per-row frozen files predictions/STAGE/...; every
repository input is read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data)."""
import gzip
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import far as FA  # noqa: E402
import guard as G  # noqa: E402
import pins  # noqa: E402
import rows as RW  # noqa: E402
import scorekit  # noqa: E402
import wind as WD  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("wind", "g14", "clipr")
GREEN = 0xFF00FF00
COPIES = {"gen/far.py": "data:render/closing-r13-isp/gen/far.py",
          "gen/pivot.py": "data:render/closing-r13-isp/gen/pivot.py",
          "gen/q261_rule2.py": "data:cited/closing11/plan/c6-q261/q261_rule2.py",
          "gen/clip.py": "data:render/closing-r13-isp/gen/clip.py"}
HEADERS = {
    "wind": """# R14-1 (a) wind, Q241 (E998, E977, E287, E981): E998's form (E977's z242-c-f0 ramp, 80 x 40, compare less with writes),
# ISP word 0 bits 15, 16, 17 each alone on the triangle with its vertex order reversed (H-CULL: E977's ramp; H-KILL: no
# pixel), and a vertex depth above 1 (zhi) or below 0 (zlo) under the compare always with writes (H-CLAMP, H-ZCLIP, H-RAW,
# H-ABS per dword and pixel). Controls that can fail: the reversed triangle unpoked, E998's bit 15 replicate, the
# compare always at E977's depths. First stage, in range. Stop: any fault or hang (#limit 0); a row without job: ok.""",
    "g14": """# R14-1 (a), R14-2 (a) g14, Q261 (E1023, E1024): the quarter-target guard held out: H-VP (a quarter of the viewport past
# each edge, clip x, y within 1.5 w) against H-TGT (of the target), H-MAX4, H-MIN4, H-ABS, H-EXACT, and per row the side's
# bound as a family; 64 x 64 along -x (a 9 or 16), 128 x 128 (+x 147/160/173/186, -x, -y, +y), 256 x 256, 128 x 64 and
# 64 x 128; --tri-unit 5. Controls that can fail: E979's far-ctl first, E1023's t128-1 replicate after the in-range rows.
# LAST (R14-2 a): three poked-viewport rows (--poke blk:6..9 = 32.0 on 128 x 128, 64.0 on 64 x 64). Stop: any fault or
# hang (#limit 0); the first job that is not `job: ok` (hook_check, rc 24).""",
    "clipr": """# R14-1 (a), R14-3 (a) clipr, Q199 (E1012, E1024, E607, E914, E943): the rounding of a clip-made vertex on 1/512 ties at
# H-VP's x = 80 on 64 x 64 (HU, HA, RNE, TR), vertices inside the guard of 4096 x 16 on a y tie (x 5000 and -1000) and a
# far vertex at 2^24 px along +x there, E684's far21d0 first and E1024's far-x30p replicate (controls that can fail).
# LAST (R14-3 a): the int32 ends at --tri-unit 0 (x = 2^31 - 1, y = -2^31) on 64 x 64. The session's last stage: it stops
# at the first job that is not ok (any fault or hang: #limit 0; a job line other than ok: hook_check, rc 24).""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def kept_bitmap(pin, W, H):
    text = gzip.decompress(pins.blob(pin)).decode(errors="replace")
    px = pins.pixels(text, W * H)
    assert px is not None, pin
    return [v == GREEN for v in px]


# ---------------------------------------------------------------- wind
def build_wind():
    rows, pred, files = [], [HEAD], {}
    src = "gen/wind.py"
    ramp = pins.sha(gzip.decompress(pins.blob(WD.E977 + ".depth.1.bin.gz")))
    none = pins.sha(gzip.decompress(pins.blob(WD.E998 + ".depth.1.bin.gz")))
    for r in WD.ROWS:
        name, st, order, isp0, z, kind = r
        rows.append(f"{name}|{st}|safe|{WD.knobs(r)}|t10|{WD.args(r)}")
        if kind in ("ramp", "none", "cull"):
            sets = {"ramp": {"KEPT": ("ramp",)}, "none": {"KEPT": ("none",)},
                    "cull": {"H-CULL": ("ramp",), "H-KILL": ("none",)}}[kind]
            for m, (what,) in sets.items():
                src_m = (WD.E977 if what == "ramp" else WD.E998) + ".depth.1.bin.gz"
                pred.append(line(name, "drawn", 3200 if what == "ramp" else 0, m, st, src_m))
                pred.append(line(name, "hash", WD.HASH_RAMP if what == "ramp" else WD.HASH_BG, m, st, src_m))
                pred.append(line(name, "depth.1.bin", "sha256:" + (ramp if what == "ramp" else none), m, st, src_m))
        if kind in ("ramp", "z"):
            for m in WD.ZMODELS if kind == "z" else ("H-CLAMP",):
                t = WD.ztext(WD.zmodel(WD.fwd_depths(r), m))
                lab = m if kind == "z" else "PLANE"
                files[f"predictions/wind/{name}.{lab}.txt"] = t.encode()
                pred.append(line(name, "zmodel", "sha256:" + pins.sha(t), lab, st, src))
    return rows, pred, files


# ---------------------------------------------------------------- g14, clipr
def models_of(r):
    """[(label, image)] of the row's frozen models; the first is the reference"""
    W, H, unit, vt, vp = r["W"], r["H"], r["unit"], r["vt"], r["vp"]
    bx = G.boxes(W, H, vp)
    if r["kind"] == "tie":
        out = [("CLIP-HU", G.predict(vt, unit, W, H, vp, bx["H-VP"], "HU"))]
        out += [("CLIP-" + k, G.predict(vt, unit, W, H, vp, bx["H-VP"], k)) for k in ("HA", "RNE", "TR")]
        return out + [("H-EXACT", G.predict(vt, unit, W, H, vp, None))]
    if r["kind"] == "intie":
        out = [("IN-" + k, G.predict(vt, unit, W, H, vp, bx["H-VP"], "HU", k)) for k in ("E607", "HU", "RNE", "TR")]
        return out + [(m, G.predict(vt, unit, W, H, vp, bx[m])) for m in ("H-MIN4", "H-ABS")]
    out = [(m, G.predict(vt, unit, W, H, vp, bx[m])) for m in G.GUARD_MODELS]
    if r["kind"] == "int32":
        sub = [(G.F(x, 256), G.F(y, 256)) for x, y in G.variants(vt, unit, W, H, vp)[0]]
        fp = FA.predictions(sub)
        out += [(m, fp[m]) for m in ("H-SAT", "H-WRAP", "H-CULL")]
    return out


def family_of(r):
    if r["kind"] in ("tie", "intie"):
        return []
    W, H, unit, vt, vp = r["W"], r["H"], r["unit"], r["vt"], r["vp"]
    base = G.boxes(W, H, vp)["H-VP"]
    vals = RW.F_FAMILY if r["name"] == "clipr-w4-f" else G.family_values(W, H, r["side"], vp)
    return [("%d" % v, G.predict(vt, unit, W, H, vp, G.with_bound(base, r["side"], G.F(v)))) for v in vals]


def clip_stage(stage, rowlist):
    rows, pred, files = [], [HEAD], {}
    src = "gen/guard.py"
    for r in rowlist:
        name, st, W = r["name"], r["set"], r["W"]
        rows.append(f"{name}|{st}|safe|{r['knobs']}|t10|{RW.args(r)}")
        ms = models_of(r)
        ref = ms[0][1]
        bm = G.bitmap(ref, W)
        files[f"predictions/{stage}/{name}.ref.txt"] = bm.encode()
        pred.append(line(name, "ref", "sha256:" + pins.sha(bm), ms[0][0], st, src))
        mt = G.diff_text(ref, ms, W)
        files[f"predictions/{stage}/{name}.models.txt"] = mt.encode()
        pred.append(line(name, "models", "sha256:" + pins.sha(mt), ",".join(m for m, _ in ms), st, src))
        fam = family_of(r)
        if fam:
            ft = G.diff_text(ref, fam, W)
            files[f"predictions/{stage}/{name}.family.txt"] = ft.encode()
            pred.append(line(name, "family", "sha256:" + pins.sha(ft), "bound:" + r["side"], st, src))
        if r["kept"]:
            pin = RW.KEPT[r["kept"]]
            kb = G.bitmap(kept_bitmap(pin, W, r["H"]), W)
            files[f"predictions/{stage}/{name}.KEPT.txt"] = kb.encode()
            pred.append(line(name, "pixels", "sha256:" + pins.sha(kb), "KEPT", st, pin))
    return rows, pred, files


def build():
    files = {}
    tables = {"wind": build_wind(), "g14": clip_stage("g14", RW.g14_rows()),
              "clipr": clip_stage("clipr", RW.clipr_rows())}
    import score as SC
    for stage in ORDER:
        rows, pred, extra = tables[stage]
        files.update(extra)
        files[f"tables/{stage}.txt"] = (f"#stage {stage}\n#limit 0\n{HEADERS[stage]}\n"
                                        + "\n".join(rows) + "\n").encode()
        files[f"predictions/{stage}.tsv"] = "".join(pred).encode()
        controls = {}
        for ln in rows:
            name, st, _, knobs, tool, args = ln.split("|", 5)
            if st == "control":
                reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")]
                controls[name] = (tuple(reads[0]) if reads else (), dict(name=name, args=args, stage=stage))
        scorekit.refuse_unreadable(controls, SC.producible)
    return files


def main(argv):
    files = build()
    check = "--check" in argv
    bad = []
    for rel, b in sorted(files.items()):
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                bad.append(rel)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b)
    if check:
        for d in ("tables", "predictions") + tuple("predictions/" + s for s in ORDER):
            full = os.path.join(KP, d)
            for n in sorted(os.listdir(full)) if os.path.isdir(full) else []:
                if not os.path.isdir(os.path.join(full, n)) and f"{d}/{n}" not in files:
                    bad.append(f"{d}/{n} (not written by the generator)")
        for rel, pin in COPIES.items():
            if open(os.path.join(KP, rel), "rb").read() != pins.blob(pin):
                bad.append(f"{rel} (not the byte copy of {pin})")
        print("\n".join(f"differs: {b}" for b in bad) or f"generator current: {len(files)} files")
        return 1 if bad else 0
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
