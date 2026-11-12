#!/usr/bin/env python3
"""asm_l.py: stage L's five pixel programs (Q111: `lock #0` twice in a pixel program), assembled with resgx545's usse-asm from
probes/usse/templates/counter.s (our own template, E088's counter probe: r29 the scratch buffer, r3 = 1, OP, the stored value as the
pixel) into bins/*.bin, with their listings in bins/LISTING.txt.  Run before the freeze; tests/test_gen.py runs it with --check.

  PY gen/asm_l.py            assemble and write bins/ (and LISTING.txt)
  PY gen/asm_l.py --check    exit 1 if a bin or the listing differs from what it would write (nothing written)

The counter op is E088's (probes/usse/quad-lock.toml, probe usse-quad-lock-counter) byte for byte; l0 must assemble to E088's kept
usse-quad-lock-counter__1.bin (lock #0 ... release #0) and l4 to __3.bin (lock #0, no release): both are checked here, so the
assembler (the Mac's tools/usse-asm/usse-asm, used as built, never rebuilt by this session) gives the words the kept run ran.
"""
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
ASM = MAIN + "/tools/usse-asm/usse-asm"
TEMPLATE = MAIN + "/probes/usse/templates/counter.s"
KEPT = DATA + "/usse/quad-lock/usse-quad-lock-counter/bins"
ADD = ("ldad.skipinv r2, [r29,+#0], drc0\nwdf drc0\niadd32.skipinv.testtaz.chan0 r2, p0, r3, r2\nstad.skipinv [r29,+#0], r2\n"
       "idf drc0, bif\nwdf drc0")

# name: the lines around the counter op (the plan's table, closing7/c/exp-faults-r7.md section 2.2)
PROGS = [
    ("l0-lock-release", ["lock #0"], ["release #0"]),
    ("l1-lock0-lock1", ["lock #0", "lock #1"], ["release #1", "release #0"]),
    ("l2-lock-lock-rel-rel", ["lock #0", "lock #0"], ["release #0", "release #0"]),
    ("l3-lock-lock-rel", ["lock #0", "lock #0"], ["release #0"]),
    ("l4-lock-norel", ["lock #0"], []),
]
SAME_AS_KEPT = {"l0-lock-release": "usse-quad-lock-counter__1.bin", "l4-lock-norel": "usse-quad-lock-counter__3.bin"}


def source(pre, post):
    return open(TEMPLATE).read().replace("{OP}", "\n".join(pre + [ADD] + post))


def assemble(text):
    """(bytes, listing) of one program, through a pipe (nothing written but a file in debug/)."""
    out = os.path.join(KP, "debug", ".asm_l.bin")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run([ASM, "-l", "-o", out, "-"], input=text, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("usse-asm failed: %s" % r.stderr.strip())
    b = open(out, "rb").read()
    os.remove(out)
    return b, r.stdout


def files():
    out, listing = {}, []
    for name, pre, post in PROGS:
        b, lst = assemble(source(pre, post))
        out["bins/%s.bin" % name] = b
        listing.append("== %s\n%s" % (name, lst.rstrip("\n")))
    out["bins/LISTING.txt"] = ("# stage L's programs (gen/asm_l.py; usse-asm listings; do not edit)\n" + "\n".join(listing) + "\n").encode()
    return out


def main(argv):
    check = "--check" in argv
    fs = files()
    bad = 0
    for name, kept in SAME_AS_KEPT.items():
        if fs["bins/%s.bin" % name] != open(os.path.join(KEPT, kept), "rb").read():
            print("%s is not E088's kept %s byte for byte" % (name, kept))
            bad = 1
    for rel, b in fs.items():
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                print("differs: %s" % rel)
                bad = 1
            continue
        if not bad:
            with open(p, "wb") as f:
                f.write(b)
    if not check and not bad:
        print("written: %s" % ", ".join(sorted(fs)))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv))
