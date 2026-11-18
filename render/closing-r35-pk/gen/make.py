#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r35-pk's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the five
stages (s0, r1, r2, r3, pw, in run order), the frozen control images
predictions/STAGE/NAME.MODEL.txt (one dword a pixel, raster order, hex) and bins/ (the kept
programs byte for byte, and src/ramp_xy.s assembled by tools/usse-asm), every pinned input read
at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545; its tools/usse-asm/usse-asm assembles the ramp)."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import pk as Q  # noqa: E402
import scorekit  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("s0", "r1", "r2", "r3", "pw")
TOOL = "t10"
HEADERS = {
    "s0": """# r35-pk s0, Q302 (rank-round35.md 3.3, R35-1 (a)): the known-value controls of every decoder form, gating every
# later stage (score.py GATES): the ramp in mode 0 at 0x80 (its image by construction: the o0 decoder), the ramp in
# mode 4 (E1136's alpha split at 0x80: 127 clear, 128 set), E031's kept colour images of modes 3, 4, 5, 6, 7, 9, 10
# (each mode's layout). Stop: any fault or hang; a control without its rows (25); the second row without its 64 pixel
# rows (24). A stop here ends the session (on_stop = "end").""",
    "r1": """# r35-pk r1, Q302 (d) and (a): the ramp at 0x80 in modes 3, 4, 5, 6 (match: each mode's packer under H-RZ, H-RN,
# H-RNE, H-SCALE from this stage's mode 0 reference), 9 and 10 (whole: H-WHOLE against H-NARROW) and 11 (H-AS0
# against H-AS0-PART); two replicates, the second in reverse order. Control that can fail: the stage's mode 0
# reference (H-RAMP). Gate: s0.""",
    "r2": """# r35-pk r2, Q302 (a): the ramp at 0x80 in the 40 ARGB8888-like modes other than 0 (E031's class), one replicate:
# match H-AS0 (the stage's mode 0 reference, dword for dword) against H-AS0-PART. Control that can fail: the stage's
# mode 0 reference (H-RAMP). Gate: s0.""",
    "r3": """# r35-pk r3, Q302 (e): bit 25 with another low byte (0x02000040, 0x020000c0) in modes 0, 4, 5, 6, two replicates
# (the second reversed), each read against the stage's 0x80 reference of its mode: rel H-1136 (bit 25 inverts the
# alpha field, the low byte sets mode 4's alpha at alpha >= it) against H-LOWDEP. Sideband bits 8:6 stay 0, bit 11
# never set (E383). Control that can fail: the stage's mode 0 reference (H-RAMP). Gate: s0.""",
    "pw": """# r35-pk pw, Q302 (a) and (b): the ramp in modes 12 and 13, which write past the target into the tool's 64 KiB
# scratch (E031: no fault in two runs, r34-q044 again), two replicates each, last so that an unplanned end costs
# nothing else: whole H-WHOLE (target and scratch) against H-NARROW; the scratch layout is a reading. Controls that
# can fail: the stage's mode 0 reference (H-RAMP), E031's kept images of modes 12 and 13. Mode 14 never runs. Gate:
# s0.""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def body(tokens):
    return "".join(t + "\n" for t in tokens)


def assemble():
    asm = os.path.join(pins.MAIN, "tools", "usse-asm", "usse-asm")
    with tempfile.TemporaryDirectory(prefix="r35p-asm.") as d:
        out = os.path.join(d, Q.RAMP_BIN)
        r = subprocess.run([asm, "-o", out, os.path.join(KP, Q.RAMP_SRC)], capture_output=True,
                           text=True, timeout=60)
        if r.returncode:
            raise SystemExit(f"usse-asm {Q.RAMP_SRC}: {r.stderr.strip()}")
        return open(out, "rb").read()


def build():
    files, tables = {}, {}
    for n, pin in Q.BINS.items():
        files[f"bins/{n}"] = pins.blob(pin)
    files[f"bins/{Q.RAMP_BIN}"] = assemble()
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
