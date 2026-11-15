#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r26-vol's generator (round 26's plan, closing26/plan/rank-round26.md sections 2.1 and
4; DECISIONS-R26: R26-2 a). Writes tables/vc.txt, tables/vb.txt, predictions/vc.tsv,
predictions/vb.tsv, the programs bins/NAME.bin and mock/e567.json (the mock's copy of E567's
four kept control images), every input read at the commits session.toml's [freeze] names
(gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Programs: E567's case text (resgx545 probes/texture/tx-types.toml and tx-types-risky.toml, phase
11.32) in its template (probes/texture/templates/tx_map.s), assembled by usse-asm built from the
same resgx545 commit (git archive of tools/usse-asm and tools/usse-dis into debug/asm/, never a
working tree's binary); tests/test_plan.py checks that the four control programs are E567's kept
programs byte for byte (resgx545-data texture/p1132-recomp/raw/.../bins).

Stage vc (5 controls, gate of vb, on_stop end): c-w0 (E567's ty0-3d-w0), c-w15 (ty0-3d-w15),
c-cube-w5 and c-cube-w15 (rt2-3d-w5 and -w15: TEXTYPE 2, where w acts), c-w0b (c-w0 again). Each
reads E567's kept pixel sha256 (H-E567).

Stage vb (40 rows): for each of the 19 bits that ran on a twiddled texture without a fault (BITS),
E567's ty0-3d-w0 and ty0-3d-w15 programs with that one bit of T0 (r20) or T3 (r23) flipped:
vb-tNbK-w0 and vb-tNbK-w15; the repeats vb-t0b27-w0r and vb-t0b30-w0r (E564: those bits read
values that are no name of the buffer). H-NOVOL: each pair is equal at all 2048 pixels; H-VOL
(per bit): it differs. A bit is cannot tell when a job of its pair did not complete or print 2048
pixels, or (t0b27, t0b30) its repeat differs from its w 0 job."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

TOOL = "t24"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("vc", "vb")
PROBE = "probe --temps 32 --coords --pixels"
TYPES = "resgx545:probes/texture/tx-types.toml"
RISKY = "resgx545:probes/texture/tx-types-risky.toml"
TEMPLATE = "resgx545:probes/texture/templates/tx_map.s"
RECOMP = "data:texture/p1132-recomp/raw/"
KEPT = "data:texture/p1132/"
T0, T3 = 0x07FE0000, 0x00800800          # E567's twiddled 16 x 16 control (T1 0x0c00f00f)
REG = {"t0": ("r20", T0), "t3": ("r23", T3)}

# the controls: row, E567's table, label, its kept program (index in the table)
CONTROLS = (("c-w0", TYPES, "ty0-3d-w0", "tx-types", 1),
            ("c-w15", TYPES, "ty0-3d-w15", "tx-types", 4),
            ("c-cube-w5", RISKY, "rt2-3d-w5", "tx-types-risky", 4),
            ("c-cube-w15", RISKY, "rt2-3d-w15", "tx-types-risky", 5),
            ("c-w0b", TYPES, "ty0-3d-w0", "tx-types", 1))

# the 19 bits (word, bit) and where each ran on a twiddled texture without a fault
BITS = ((("t0", 14), "E564"), (("t0", 15), "E564"), (("t0", 16), "E564"),
        (("t0", 27), "E564, E567 ind-t0b27"), (("t0", 28), "E564"), (("t0", 29), "E564"),
        (("t0", 30), "E564, E567 ind-t0b30"),
        (("t3", 8), "E564"), (("t3", 9), "E564"), (("t3", 10), "E567 ind-t3b10, E722"),
        (("t3", 11), "E564, E1027"), (("t3", 12), "E564, E1027"), (("t3", 15), "E564"),
        (("t3", 18), "E567 ind-t3b18, E722"), (("t3", 20), "E564"), (("t3", 21), "E564"),
        (("t3", 22), "E564"), (("t3", 27), "E567 ind-t3b27, E722"),
        (("t3", 28), "E567 ind-t3b28, E722"))
REPEATS = (("t0", 27), ("t0", 30))
W = {"w0": "ty0-3d-w0", "w15": "ty0-3d-w15"}       # w 0 and w 1.5 (r26 0x00000000, 0x3fc00000)


def bitname(word, k):
    return f"t{word[1]}b{k}"


def asm_path():
    """usse-asm built from the frozen resgx545 commit (git archive, make), in debug/asm/."""
    c = pins.COMMIT["resgx545"]
    d = os.path.join(KP, "debug", "asm", c[:12])
    exe = os.path.join(d, "tools", "usse-asm", "usse-asm")
    if not os.path.exists(exe):
        os.makedirs(d, exist_ok=True)
        a = subprocess.run(["git", "-C", pins.MAIN, "archive", c, "tools/usse-asm", "tools/usse-dis"],
                           capture_output=True, check=True, timeout=120)
        subprocess.run(["tar", "-x", "-C", d], input=a.stdout, check=True, timeout=120)
        subprocess.run(["make", "-s", "-C", os.path.join(d, "tools", "usse-asm"), "usse-asm"],
                       check=True, capture_output=True, timeout=600)
    return exe


def assemble(text):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "p.bin")
        r = subprocess.run([asm_path(), "-l", "-o", out, "-"], input=text.encode(),
                           capture_output=True, timeout=60)
        if r.returncode:
            raise SystemExit("usse-asm: " + r.stderr.decode().strip())
        return open(out, "rb").read()


def case_text(table, label):
    p = tomllib.loads(pins.blob(table).decode())["probe"][0]
    assert p["inputs"] == ["PRE", "SETUP", "SMP"] and not p["params"], p["name"]
    pre, setup, smp = p["cases"][p["labels"].index(label)]
    return (pins.blob(TEMPLATE).decode().replace("{PRE}", pre).replace("{SETUP}", setup)
            .replace("{SMP}", smp))


def flipped(text, word, k):
    reg, base = REG[word]
    old = f"mov {reg}, #0x{base:08x}\n"
    assert text.count(old) == 1, (word, k)
    return text.replace(old, f"mov {reg}, #0x{base ^ (1 << k):08x}\n")


def kept_text(path):
    return pins.blob(KEPT + path).decode()


def pixels(text):
    """the 2048 pixels (8 hex digits each, raster order) from `probe NAME: row Y: ...` lines."""
    vals = []
    for ln in text.splitlines():
        if ln.startswith("probe ") and ": row " in ln:
            vals += [v.rjust(8, "0") for v in ln.split(": ", 2)[2].split()]
    return vals


def pixsha(text):
    v = pixels(text)
    return hashlib.sha256(",".join(v).encode()).hexdigest() if len(v) == 2048 else None


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def vc(files):
    rows, pred, images = [], [HEAD], {}
    for n, table, label, kdir, _ in CONTROLS:
        files[f"bins/{n}.bin"] = assemble(case_text(table, label))
        t = kept_text(f"{kdir}/{label}.txt.gz")
        sha = pixsha(t)
        assert sha, label
        images[label] = pixels(t)
        rows.append(f'{n}|control|safe|reads:o0,rows|{TOOL}|{PROBE} "$S/bins/{n}.bin"')
        pred.append(line(n, "pixsha", sha, "H-E567", "control",
                         f"E567: the kept {label} (texture/p1132/{kdir}), its pixel sha256"))
    return rows, pred, images


def vb(files):
    rows, pred = [], [HEAD]
    for (word, k), where in BITS:
        b = bitname(word, k)
        names = [f"vb-{b}-w0", f"vb-{b}-w15"] + ([f"vb-{b}-w0r"] if (word, k) in REPEATS else [])
        for n in names:
            w = n.rsplit("-", 1)[1].rstrip("r")
            files[f"bins/{n}.bin"] = assemble(flipped(case_text(TYPES, W[w]), word, k))
            rows.append(f'{n}|heldout|safe|-|{TOOL}|{PROBE} "$S/bins/{n}.bin"')
            if n.endswith("-w0"):
                pred.append(line(n, "pixels", 2048, "H-PRINT", "heldout",
                                 "--pixels: 2048 pixels printed (the pair's premise)"))
            elif n.endswith("-w15"):
                src = (f"{word.upper()} bit {k} flipped (ran without a fault on twiddled in "
                       f"{where}); w 1.5 against w 0, the pixels equal")
                pred.append(line(n, "equal_w0", 2048, "H-NOVOL", "heldout",
                                 src + ": E567's w3d=ignore (8 of 8) with the bit set"))
                pred.append(line(n, "equal_w0", "lt2048", "H-VOL", "heldout",
                                 src + ": the bit makes the third coordinate act"))
            else:
                pred.append(line(n, "equal_w0", 2048, "H-REPEAT", "heldout",
                                 "the w 0 job again: a run-to-run change makes the bit cannot tell"))
    return rows, pred


HEADERS = {
    "vc": """#stage vc
#limit 0
# vc (Q114, rank-round26.md 2.1, R26-2 a): E567's programs on t24 (probe --temps 32 --coords --pixels), each reading E567's
# kept pixel sha256 (H-E567): c-w0 and c-w15 (ty0-3d-w0 and -w15, twiddled 16 x 16, w ignored), c-cube-w5 and
# c-cube-w15 (rt2-3d-w5 and -w15, TEXTYPE 2: two different images, the control that a w that acts is seen), c-w0b
# (c-w0 again: no state left by the jobs moves the image). Gates vb. Stop: a probe row without its 32 pixel rows
# (run/hooks.sh), any fault or hang; on_stop end.""",
    "vb": """#stage vb
#limit 0
# vb (Q114, rank-round26.md 2.1, R26-2 a): per bit of the 19 that ran on a twiddled texture without a fault (T0 14, 15,
# 16, 27, 28, 29, 30; T3 8, 9, 10, 11, 12, 15, 18, 20, 21, 22, 27, 28), E567's ty0-3d-w0 and ty0-3d-w15 with that one
# bit flipped (w 0 and w 1.5); t0b27 and t0b30 repeat their w 0 job. Frozen H-NOVOL (each pair equal at 2048 pixels)
# against H-VOL (the pair differs). Gated on vc. Stop: a probe row without its 32 pixel rows (run/hooks.sh), any fault
# or hang.""",
}


def build():
    files = {}
    r1, p1, images = vc(files)
    r2, p2 = vb(files)
    files["tables/vc.txt"] = (HEADERS["vc"] + "\n" + "\n".join(r1) + "\n").encode()
    files["tables/vb.txt"] = (HEADERS["vb"] + "\n" + "\n".join(r2) + "\n").encode()
    files["predictions/vc.tsv"] = "".join(p1).encode()
    files["predictions/vb.tsv"] = "".join(p2).encode()
    files["mock/e567.json"] = (json.dumps(images, sort_keys=True, separators=(",", ":"))
                               + "\n").encode()
    return files


def main(argv):
    files = build()
    if "--check" in argv:
        bad = [p for p, b in files.items()
               if not os.path.exists(os.path.join(KP, p)) or open(os.path.join(KP, p), "rb").read() != b]
        for p in bad:
            print(f"stale: {p}")
        return 1 if bad else 0
    for p, b in files.items():
        f = os.path.join(KP, p)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "wb") as fh:
            fh.write(b)
    print(f"wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
