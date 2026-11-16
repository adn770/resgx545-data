#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r34-q044's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the four
stages (s0, p1, p2, pw, in run order), the frozen images predictions/STAGE/NAME.MODEL.txt (one
dword a pixel, raster order, hex), the ramp's alpha map predictions/p2/alpha.txt (one token a
pixel: the alpha byte on the triangle, `-` elsewhere) and bins/ (the kept programs, byte for
byte), every input read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import q044 as Q  # noqa: E402
import scorekit  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("s0", "p1", "p2", "pw")
TOOL = "t10"
HEADERS = {
    "s0": """# r34-q044 s0, Q044 (rank-round34.md 3.2, R34-1 (a)): the controls every later stage is gated on (score.py GATES), each a
# kept image that can fail: E268's mode 0 at 0x80, at bit 25 and at bit 11 (colour form), E031's mode 4 (colour), E385's
# mode 4 at 0x80 and at bit 25 and mode 8 at bit 25 (ramp form). Stop: any fault or hang; a control without its rows (25);
# the second row without its 64 pixel rows (24). A stop here ends the session (on_stop = "end").""",
    "p1": """# r34-q044 p1, Q044 (b): bit 25 of the word that loads CR_REG_0400 in every pack mode 4 to 63 but 14 (E031: faults) and 12,
# 13 (stage pw), colour form: per mode the 0x80 reference, then 0x02000080; 22, 26, 34 a second reference after it.
# Frozen per mode: `xor` (the bit-25 row against this stage's reference) H-INV25 (the mode's alpha field, E031's classes;
# mode 8 none, E385) against H-SUBSET (only 0-2, 4, 5); the references H-E031 (E031's kept image). 22 and 34: read on the
# dwords their two references repeat, no model (Q012). Control that can fail: E268's mode 0 image. Gate: s0.""",
    "p2": """# r34-q044 p2, Q044 (a): the low byte and bits 11:8, ramp form (E385). Mode 4 at nine low bytes equal to ramp alphas on
# the triangle: `thr` H-GE (alpha >= low byte sets) against H-GT (>); modes 5-8 at 0x00, 0x40, 0xc0, 0xff and 0xf80, 1, 2,
# 9, 10, 11 at 0x40, 0xc0, 0xf80: `xor` against the mode's reference H-THR1 / H-NULL (0) against H-THRN / H-ACT; one
# mode a class without alpha (3, 15, 20, 24, 26, 27) at 0xf80. Controls that can fail: E385's mode 0, 4, 5 and 8 images
# (mode 0 is the alpha map). Gate: s0.""",
    "pw": """# r34-q044 pw, Q044 (b): bit 25 in modes 12 and 13, which write past the target into the scratch (E031: no fault in two
# runs), last so that an unplanned end costs nothing else; colour form, `xor` H-INV25 (0xff000000) against H-SUBSET (0).
# Control that can fail: E268's mode 0 image. Gate: s0.""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def body(tokens):
    return "".join(t + "\n" for t in tokens)


def build():
    files, tables = {}, {}
    for n, pin in Q.BINS.items():
        files[f"bins/{n}"] = pins.blob(pin)
    alpha = Q.alpha_map(pins.blob)
    files["predictions/p2/alpha.txt"] = body("-" if a is None else "%02x" % a
                                             for a in alpha).encode()
    import score as SC
    for stage, rows in Q.jobs(pins.blob).items():
        tab, pred = [], [HEAD]
        for r in rows:
            tab.append(f"{r['name']}|{r['set']}|safe|{r['knobs']}|{TOOL}|{r['args']}")
            for m, im in r["pixels"].items():
                b = body("%08x" % v for v in im)
                files[f"predictions/{stage}/{r['name']}.{m}.txt"] = b.encode()
                pred.append(line(r["name"], "pixels", "sha256:" + pins.sha(b), m, r["set"],
                                 r["src"]))
            for q, ms in r["q"].items():
                for m, v in ms.items():
                    pred.append(line(r["name"], q, v, m, r["set"], r["src"]))
        files[f"tables/{stage}.txt"] = (f"#stage {stage}\n#limit 0\n{HEADERS[stage]}\n"
                                        + "\n".join(tab) + "\n").encode()
        files[f"predictions/{stage}.tsv"] = "".join(pred).encode()
        controls = {}
        for t in tab:
            name, st, _, knobs, tool, a = t.split("|", 5)
            if st == "control":
                reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")]
                controls[name] = (tuple(reads[0]) if reads else (),
                                  dict(name=name, args=a, stage=stage))
        scorekit.refuse_unreadable(controls, SC.producible)
        tables[stage] = tab
    assert tuple(tables) == ORDER
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
        for d in ("bins", "tables") + tuple(f"predictions/{s}" for s in ORDER):
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
