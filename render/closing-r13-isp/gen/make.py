#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r13-isp's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the three
stages (q201, q261, far, in run order), the per-row frozen files predictions/STAGE/..., and bins/
(the five program files, byte copies of their pins); every repository input is read at the
commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data)."""
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import clip as C  # noqa: E402
import pins  # noqa: E402
import q201 as Q  # noqa: E402
import scorekit  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("q201", "q261", "far")
GREEN = 0xFF00FF00
BINS = {"bins/pos.bin": "data:render/closing-r10-x/bins/pos.bin",
        "bins/cset.bin": "data:render/closing-r7-geo/bins/p1138-it-a0__0.bin",
        "bins/pix_pa0.bin": "data:render/closing-r10-x/bins/pix_pa0.bin",
        "bins/pix_pa1.bin": "data:render/closing-r10-x/bins/pix_pa1.bin",
        "bins/vtx_coords.bin": "data:pds/iteration-sources/pds-iteration-sources-iter-coords/bins/vtx_coords.bin"}
COPIES = {"gen/far.py": "data:render/closing-r9-x/gen/far.py",
          "gen/pivot.py": "data:render/closing-r10-geo/gen/pivot.py",
          "gen/q261_rule2.py": "data:cited/closing11/plan/c6-q261/q261_rule2.py",
          "gen/sample0_rule.py": "data:cited/closing12/plan/c6-q201/sample0_rule.py"}
KEPT_OF = {"q261-ctl-far21": "far-ctl", "q261-ctl-x24p": "far-x24p", "far-ctl": "far-ctl",
           "far-x25n": "far-x25n"}
HEADERS = {
    "q201": """# R13-1 (a) q201, Q201 (E1018): CR_ISP_MULTISAMPLECTL byte 0 (--cmd 16=0x000000NN) at 0x3c, 0x0f, 0xf0, 0x5a on one
# 64 x 64 triangle (--tri-v, not the default), read by E437's source-0 program (pos.bin) and by coordinate set 0 iterating
# the vertices' clip x, y (cset.bin, vtx_coords.bin, --vtx-coords 2 on every row); pix_pa0 = x, pix_pa1 = y (one per job).
# Frozen per row: the drawn set at E1018's point; the offset s (value = pixel + s) per model: H-SAMPLE0 (lo/16, hi/16),
# H-CENTRE (1/2), H-SWAP (hi/16, lo/16), H-SPLIT (src0 moves, cset at 1/2). Controls that can fail: 0x88 cset x, y (E606),
# 0x26 src0 x, y (E1010), the 0x88 cset x replicate last. Stop: any fault or hang (#limit 0); a row without 64 pixel rows.""",
    "q261": """# R13-1 (a) q261, Q261 (E1005, E1012): held-out far vertices under E1012's guard-band clip (c6's engine, q261_rule2.py):
# 4 along +x (G = 16..22), 3 along -x (lower bound a = 8..32; c6's vertices), 4 along -y (g = 8..32; designed, c6's far-y
# rows depend on the x bounds too), 3 on 128 x 128 (guard relative 128 + G, or absolute h = 80..86); --tri-unit 5.
# Frozen per row: H-EXACT, the clip family (per value, the pixels off H-EXACT), H-PIVOT's pixel intervals (64 x 64, +-x).
# Controls that can fail: E979's far-ctl (E684's far21d0) first, E979's far-x24p (E1005 d = 0) last, their kept images.
# Stop: any fault or hang (#limit 0); a row without job: ok.""",
    "far": """# R13-2 (a) far, Q199 past 2^25 px (E979): one far vertex at 2^26, 2^28, 2^30 px in x and y (both signs on both axes),
# ascending distance, --tri-unit 0 (whole pixels, int32), after E684's far21d0 (control) and E979's far-x25n (replicate).
# Frozen per row: the clip family at E1012's survivors (G 16..22, a 8..32, g 8..32), H-EXACT, H-EXACT-BAND, H-F32 (the
# float32 window vertex), H-SAT, H-WRAP (24.8), H-CULL. Untested range: the stage stops at the first job that is not
# `job: ok` (any fault, hang or failure: #limit 0, kit rc 4; a job line other than ok: hook_check, rc 24). Last stage.""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def kept_bitmap(name):
    text = gzip.decompress(pins.blob(C.KEPT % name)).decode(errors="replace")
    px = pins.pixels(text, 4096)
    assert px is not None, name
    return [v == GREEN for v in px]


def build_q201():
    rows, pred, files = [], [HEAD], {}
    for name, st, knobs, args, b, p, c in Q.jobs():
        rows.append(f"{name}|{st}|safe|{knobs}|t10|{args}")
        cov = Q.cov_text(Q.coverage(b))
        files[f"predictions/q201/{name}.coverage.txt"] = cov.encode()
        pred.append(line(name, "coverage", "sha256:" + pins.sha(cov), "E1018", st, "gen/q201.py"))
        for m in Q.MODELS:
            o = Q.offset(m, b, p, c)
            pred.append(line(name, "offset", "%d/%d" % (o.numerator, o.denominator), m, st, "gen/q201.py"))
    return rows, pred, files


def clip_stage(stage, rowlist):
    import far as FA
    import pivot as PIV
    rows, pred, files = [], [HEAD], {}
    src = "gen/clip.py"
    for name, st, knobs, w, unit, vt, vp, side, abs_too in rowlist:
        rows.append(f"{name}|{st}|safe|{knobs}|t10|{C.tri_args(w, unit, vt)}")
        V3 = [(vt[0], vt[1]), (vt[2], vt[3]), (vt[4], vt[5])]
        exact, fam = C.predict(V3, unit, w, side, abs_too)
        bm = C.bitmap(exact, w)
        files[f"predictions/{stage}/{name}.H-EXACT.txt"] = bm.encode()
        pred.append(line(name, "pixels", "sha256:" + pins.sha(bm), "H-EXACT", st, src))
        ft = C.family_text(exact, fam, w)
        files[f"predictions/{stage}/{name}.clip.txt"] = ft.encode()
        pred.append(line(name, "family", "sha256:" + pins.sha(ft), "H-CLIP", st, src))
        if name in KEPT_OF:
            kb = C.bitmap(kept_bitmap(KEPT_OF[name]), w)
            files[f"predictions/{stage}/{name}.KEPT.txt"] = kb.encode()
            pred.append(line(name, "pixels", "sha256:" + pins.sha(kb), "KEPT", st,
                             C.KEPT % KEPT_OF[name]))
        if stage == "q261" and st != "control" and w == 64 and side in ("pos-x", "neg-x"):
            iv = PIV.ivals_text(PIV.pixel_intervals(vp))
            files[f"predictions/{stage}/{name}.ivals.txt"] = iv.encode()
            pred.append(line(name, "ivals", "sha256:" + pins.sha(iv), "H-PIVOT", st, "gen/pivot.py"))
        if stage == "far" and st == "heldout":
            subs = C.variants(V3, unit, w)
            sub_px = [(C.F(x, 256), C.F(y, 256)) for x, y in subs[0]]
            fp = FA.predictions(sub_px)
            for m in ("H-EXACT-BAND", "H-SAT", "H-WRAP", "H-CULL"):
                b = C.bitmap(fp["H-EXACT" if m == "H-EXACT-BAND" else m], w)
                files[f"predictions/{stage}/{name}.{m}.txt"] = b.encode()
                pred.append(line(name, "pixels", "sha256:" + pins.sha(b), m, st, "gen/far.py"))
            f32v = [[(C.g256(C.window_f32(C.submitted(x, unit, w))),
                      C.g256(C.window_f32(C.submitted(y, unit, w)))) for x, y in V3]]
            b = C.bitmap(C.image(f32v[0], None, w), w)
            files[f"predictions/{stage}/{name}.H-F32.txt"] = b.encode()
            pred.append(line(name, "pixels", "sha256:" + pins.sha(b), "H-F32", st, src))
    return rows, pred, files


def build():
    files = {}
    for rel, pin in sorted(BINS.items()):
        files[rel] = pins.blob(pin)
    tables = {"q201": build_q201()}
    proposals = json.loads(pins.blob(C.PROPOSALS).decode())
    tables["q261"] = clip_stage("q261", C.q261_rows(proposals))
    tables["far"] = clip_stage("far", C.far_rows())
    import score as SC
    for stage in ORDER:
        rows, pred, extra = tables[stage]
        files.update(extra)
        files[f"tables/{stage}.txt"] = (f"#stage {stage}\n#limit 0\n{HEADERS[stage]}\n"
                                        + "\n".join(rows) + "\n").encode()
        files[f"predictions/{stage}.tsv"] = "".join(pred).encode()
        controls = {}
        for r in rows:
            name, st, _, knobs, tool, args = r.split("|", 5)
            if st == "control":
                reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")]
                controls[name] = (tuple(reads[0]) if reads else (),
                                  dict(name=name, args=args, stage=stage))
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
        for d in ("tables", "predictions", "bins") + tuple("predictions/" + s for s in ORDER):
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
