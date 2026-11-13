#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r10-x's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the six stages
(dcmp, zov, zbits, isp0x, sb, win0, in run order), the per-pixel predictions
predictions/STAGE/NAME.MODEL.txt of the probe stages and the probe programs bins/*.bin (byte copies
of published bins), every input read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545)."""
import gzip
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import probes as P  # noqa: E402
import scorekit  # noqa: E402
import z as Z  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("dcmp", "zov", "zbits", "isp0x", "sb", "win0")
HEADERS = {
    "dcmp": """# R10-A, Q241 and Q243: the depth compare truth table on a loaded depth (E977's z243 form, 64 x 32, flat --tri-full at t, depth
# filled with L, loaded and stored): modes 0-7 at L = t = 0.5, 2/3/5/6 one ulp above and below (H-GL), NaN under 2/3/5/6 and negative
# loaded depths (H-UBITS / H-ABS / H-IEEE / H-CLAMP0); the reading is the drawn count. Controls that can fail: E977's z243-ctl (2048),
# eq-m0 (0), eq-m7 (2048). Stop: any fault or hang (gen/z.py).""",
    "zov": """# R10-C, Q242: overlapping tiles. A plane with a distinct float at every pixel (z 0, ZX, 1 at (0,0) (2W,0) (0,2H)) stored at full
# pitch (controls: E831's count, every dword distinct) and at G under the tiles across (64x32 G0, 128x32 G1, 96x48 G1, 160x48 G2,
# 256x64 G3; 64x32 G0 also format 1). Frozen per shared slot: H-LATE / H-EARLY in region header and raster order. Stop: any fault.""",
    "zbits": """# R10-D, Q071: E977's z242-c (80x40 G 2) and z243-ctl load rows with the inert control bits together (15, 21-23, 27-31 set;
# 12, 16, 20 cleared), each half alone, and bit 0 with formats 0, 1, 2 and the load. Frozen: E977's kept dumps, drawn and hash
# (H-INERT; bit 0 H-E665: no colour pixel, stores as without it). Controls that can fail: z242-c-f0, -f1 reruns. Stop: any fault.""",
    "isp0x": """# R10-E, Q241: z242-c-f0 with ISP word 0 bits 15, 16, 17 and ISP word 1 (blk:2) bits 3 and 23 flipped one at a time (bit 18:
# not run, E065's fault). Frozen: H-NULL (E977's kept dump, drawn count and hash). Control that can fail: the unpoked rerun.""",
    "sb": """# R10-F, Q046: E383's form (eot_plain, two colours whose bytes all differ, every pixel) in pack modes 20 and 27 with sideband
# bits 8:6 at 0-3. Frozen per pixel from E383's kept images: H-LOW16 (mode 15's image) and H-M7 (mode 7's, field 0 and 1).
# Controls that can fail: E383's mode 8 jobs at field 0 (0x208, both colours). Stop: any fault or hang.""",
    "win0": """# R10-B, Q030: E502's identity maps (E437's PDS, pa0/pa1 shaders, --tri-full) in mode 0 with TE 0x60000000, 0xa0000000,
# 0xe0000000 at 64x64 and 128x96, every row dbg:render_rgn_arrays=1 (a context that takes TE bits 31/30; E502's one array).
# Frozen per pixel: H-IDENT (region model holes, own pixel), H-IDFULL, H-WIN. Controls that can fail: E502's A-m1-tee0-64x64-x
# and A-m0-te20-64x64-x (kept images). Run last: a kernel refusal of the knob would stop the session. Stop: any fault or hang.""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def img_text(im):
    return "".join("%08x\n" % v for v in im)


def kept_sha(job, dump):
    return pins.sha(gzip.decompress(pins.blob(f"data:{Z.KEPT}/{job}.{dump}.gz")))


def kept_line(job, prefix):
    text = gzip.decompress(pins.blob(f"data:{Z.KEPT}/{job}.txt.gz")).decode()
    (ln,) = [x for x in text.splitlines() if x.startswith(prefix)]
    return ln


def e383(code):
    return P.case_images(pins.blob(f"data:{P.E383}/pbe-sideband-channels-{code:04x}/raw.txt").decode())


def e502(name):
    ims = P.case_images(gzip.decompress(pins.blob(f"data:{P.E502}/{name}.txt.gz")).decode())
    (im,) = ims.values()
    return im


def build():
    files, tables = {}, {}
    for stage, jobs in (("dcmp", Z.dcmp_jobs()), ("zov", Z.zov_jobs()),
                        ("zbits", Z.bits_jobs(Z.zbits_rows(), kept_sha, kept_line)),
                        ("isp0x", Z.bits_jobs(Z.isp0x_rows(), kept_sha, kept_line))):
        rows, pred = [], [HEAD]
        for name, st, knobs, args, q in jobs:
            rows.append(f"{name}|{st}|safe|{knobs}|t4|{args}")
            for quantity, mv in q.items():
                for m, v in mv.items():
                    pred.append(line(name, quantity, v, m, st, "gen/z.py"))
        tables[stage] = (rows, pred)
    for b, src in P.BINS.items():
        files[f"bins/{b}"] = pins.blob(f"data:{src}")
    M = pins.module("data:texture/p1141/recompute/msaa_model.py")
    for stage, jobs in (("sb", P.sb_jobs(e383)), ("win0", P.win_jobs(M, e502))):
        rows, pred = [], [HEAD]
        for name, st, knobs, args, models in jobs:
            rows.append(f"{name}|{st}|safe|{knobs}|t4|{args}")
            for m, im in models.items():
                body = img_text(im)
                files[f"predictions/{stage}/{name}.{m}.txt"] = body.encode()
                pred.append(line(name, "pixels", "sha256:" + pins.sha(body), m, st, "gen/probes.py"))
        tables[stage] = (rows, pred)
    import score as SC
    for stage in ORDER:
        rows, pred = tables[stage]
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
        for d in ("bins", "predictions/sb", "predictions/win0"):
            full = os.path.join(KP, d)
            for n in sorted(os.listdir(full)) if os.path.isdir(full) else []:
                if f"{d}/{n}" not in files:
                    bad.append(f"{d}/{n} (not written by the generator)")
        print("\n".join(f"differs: {b}" for b in bad) or f"generator current: {len(files)} files")
        return 1 if bad else 0
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
