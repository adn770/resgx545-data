#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r9-x's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the five stages
(t3, srgb, zls, zst, far, in run order), the per-pixel predictions predictions/STAGE/NAME.MODEL.txt
and the probe programs bins/NAME.bin (+ .s) of the texture stages, every input read at the commits
session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545, for tools/usse-asm/usse-asm)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import far as FAR  # noqa: E402
import pins  # noqa: E402
import scorekit  # noqa: E402
import srgb as SRGB  # noqa: E402
import t3 as T3  # noqa: E402
import tex  # noqa: E402
import zls as Z  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("t3", "srgb", "zls", "zst", "far")
HEADERS = {
    "t3": """# R9-A, Q078: T3 bits 14, 11 and 12 in smp on named memory (E566's tx_map probes, scratch dword i = 0xD0000000 | i).
# Bit 14: six held-out geometries (W != S, W 48, u off the texel centres, u past the texture); frozen per pixel
# H-UCOL / H-U01 / H-URAW (gen/t3.py), each with its bit-14-clear reference (H-TEXMODEL). Bits 11, 12: E566's strided jobs (frozen: the control's image) and E564's
# twiddled chain (replicates of E564's kept images). Controls that can fail: E566's s64x32-ctl and s64x32-t3b14,
# E564's an-ctl (their kept images). --scratch-pages holds every rival's reads (check 3). Stop: any fault or hang.""",
    "srgb": """# R9-B, Q282: bilinear sRGB (T0 bit 27) in E723's g-bl-st form, each lerp stage alone (a: fy = 0, b: fx = 0) and both
# (c, held out); frozen per pixel H-HALF2 (q282_rule.json) and H-BF11 (q282_rule3.json). Controls that can fail:
# E723's g-bl-st-a rerun (its kept image) and eq (equal corners: every rival returns the decoded half). Stop: any fault.""",
    "zls": """# R9-C, Q242 and Q243: ZLS integer formats over [0, 1) at G 7, 9, 2 (80 x 40: edge tiles), frozen per dword from
# the paired format-0 dump (H-ROUND / H-FLOOR; format 2 layouts H-E490 / H-SLOT512); loads of an integer format and
# of NaN and infinity under less and greater (frozen drawn counts). Controls that can fail: the format-0 jobs (every
# dword of the target's tiles stored, E831) and E467's load under less. Stop: any fault or hang.""",
    "zst": """# R9-D, Q120 (Q121 dropped: t4 has no ISP word 2 with the ZLS stencil buffers): formats 3 to 7 with a loaded index
# stencil at 64 x 32 and 96 x 48; frozen counts for formats 4 and 7 (E466 per tile), a reading table for 3, 5, 6.
# Controls that can fail: format 0 of the same rows (depth every tile dword, stencil store E467's copy). Stop: any fault.""",
    "far": """# R9-E, Q199 and Q261: one or two vertices at 2^22 to 2^25 pixels from a 64 x 64 target (--tri-unit 5, the plan's
# unit 0 is refused by t4); frozen per pixel H-EXACT / H-SAT / H-WRAP / H-CULL (gen/far.py), E684's band undetermined.
# Control that can fail: E684's far21d0 (exact there). Stop: the first fault or hang (new range).""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def img_text(im):
    return "".join("%08x\n" % v for v in im)


def cov_text(c):
    return "".join("".join("?" if v is None else "1" if v else "0" for v in c[y * 64:(y + 1) * 64])
                   + "\n" for y in range(64))


def texture_stage(stage, jobs, files):
    rows, pred = [], [HEAD]
    src = f"gen/{stage}.py"
    for j in jobs:
        name, st, knobs, spec, models, extra = j[:6]
        npages = j[6] if len(j) > 6 else None
        text = tex.text(spec)
        files[f"bins/{name}.s"] = text.encode()
        files[f"bins/{name}.bin"] = tex.assemble(text)
        sp = f" --scratch-pages {npages}" if npages and npages != 16 else ""
        rows.append(f'{name}|{st}|safe|{knobs}|t4|{tex.PROBE}{sp} "$S/bins/{name}.bin"')
        for m, im in models.items():
            body = img_text(im)
            files[f"predictions/{stage}/{name}.{m}.txt"] = body.encode()
            pred.append(line(name, "pixels", "sha256:" + pins.sha(body), m, st, src))
        for q, mv in extra.items():
            for m, v in mv.items():
                pred.append(line(name, q, v, m, st, src))
    return rows, pred


def build():
    files = {}
    tables = {}
    rows, pred = texture_stage("t3", T3.jobs(), files)
    tables["t3"] = (rows, pred)
    rows, pred = texture_stage("srgb", SRGB.jobs(), files)
    tables["srgb"] = (rows, pred)
    for stage, jobs in (("zls", Z.zls_jobs()), ("zst", Z.zst_jobs())):
        rows, pred = [], [HEAD]
        for name, st, knobs, args, q in jobs:
            rows.append(f"{name}|{st}|safe|{knobs}|t4|{args}")
            for quantity, mv in q.items():
                for m, v in mv.items():
                    pred.append(line(name, quantity, v, m, st, "gen/zls.py"))
        tables[stage] = (rows, pred)
    rows, pred = [], [HEAD]
    for name, st, knobs, args, models in FAR.jobs():
        rows.append(f"{name}|{st}|safe|{knobs}|t4|{args}")
        for m, c in models.items():
            body = cov_text(c)
            files[f"predictions/far/{name}.{m}.txt"] = body.encode()
            pred.append(line(name, "pixels", "sha256:" + pins.sha(body), m, st, "gen/far.py"))
    tables["far"] = (rows, pred)
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
        for d in ("bins", "predictions/t3", "predictions/srgb", "predictions/far"):
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
