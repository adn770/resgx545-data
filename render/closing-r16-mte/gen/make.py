#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r16-mte's generator. Writes tables/rclip.txt and predictions/rclip.tsv from gen/model.py,
and checks bins/pix_green.bin against its pin (data:render/closing-r3k-regress/bins/pix_green.bin at
the commit session.toml's [freeze] names; the same bytes as p1139-green.bin).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now"""
import hashlib
import os
import subprocess
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import model as M  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
BIN_PIN = "data:render/closing-r3k-regress/bins/pix_green.bin"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
TABLE_HEAD = """#stage rclip
#limit 0
# R16-4 (a) rclip, Q116 (E347, E348): the MTE state's region clip (presence bit 7, two words) added to the probe triangle's
# block by t10's `--blk-add 7=C0,C1` (0xdf43 -> 0xdfc3, the closed driver's own triangle-with-clip block), never run before.
# One program on every row: pix_green.bin (0xff00ff00), the background object 0xff203040, the target's sentinel 0xdeadbeef.
# Frozen (gen/model.py): H-TILECLIP (E348: 32 x 16 tiles, inclusive, rows from the window's y = 0 = memory row 0 under the
# tool's positive y scale) + H-BG (outside: the background) + H-EN (bit 31 clear: no clip); rivals H-EXCL, H-FLIP (rows from
# the last tile row), H-PIXEL (bounds in pixels) and their mixes, H-NOCLIP, H-UNTOUCHED, H-ALWAYS, H-OFFDROP.
# Gate first: E348's clear clip of the whole 64 x 64 target (0x80000001, 0x00000003 = its formula), then its no-clip twin.
# The empty-clip row last (on_stop = "end"). Stop: any fault or hang (#limit 0); hook_check: a row without its W x H pixels,
# a value other than the three, or a gate row whose image is not all 0xff00ff00."""


def pinned_blob(pin):
    cfg = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
    assert pin in cfg["freeze"]["pins"], pin
    repo, _, path = pin.partition(":")
    assert repo == "data"
    r = subprocess.run(["git", "-C", DATA, "show", "%s:%s" % (cfg["freeze"]["data"], path)],
                       capture_output=True, timeout=60, check=True)
    return r.stdout


def table():
    out = [TABLE_HEAD]
    for n in M.NAMES:
        r = M.row(n)
        knobs = "reads:pixels,o0" if r["set"] == "control" else "-"
        out.append("%s|%s|safe|%s|t10|%s" % (n, r["set"], knobs, M.args(r)))
    return "\n".join(out) + "\n"


def predictions():
    out = [HEAD]
    src = "E348 (layout, the clear's formula); gen/model.py"
    for n in M.NAMES:
        r = M.row(n)
        f = M.predict(r, M.FROZEN)
        fz = M.combo_name(M.FROZEN)
        out.append("%s\tmap\tsha256:%s\t%s\t%s\t%s\n" % (n, M.sha(f), fz, r["set"], src))
        for q, c in (("green", "G"), ("bg", "B"), ("sentinel", "S"), ("either", "g")):
            out.append("%s\t%s\t%d\t%s\t%s\t%s\n" % (n, q, f.count(c), fz, r["set"], src))
        if r["set"] == "control":
            out.append("%s\to0\t0x%08x\t%s\t%s\t%s\n" % (n, M.GREEN, fz, r["set"], src))
        for c in M.RIVALS:
            p = M.predict(r, c)
            out.append("%s\tmap\tsha256:%s\t%s\trival\t%s\n" % (n, M.sha(p), M.combo_name(c), src))
            out.append("%s\tparts\t%d\t%s\trival\t%s\n" % (n, M.parts(f, p), M.combo_name(c), src))
    return "".join(out)


def main(argv):
    want = {"tables/rclip.txt": table(), "predictions/rclip.tsv": predictions()}
    b = open(os.path.join(KP, "bins/pix_green.bin"), "rb").read()
    if b != pinned_blob(BIN_PIN):
        print("bins/pix_green.bin is not %s" % BIN_PIN)
        return 1
    bad = 0
    for path, body in want.items():
        full = os.path.join(KP, path)
        have = open(full).read() if os.path.exists(full) else None
        if "--check" in argv:
            if have != body:
                print("%s is not current" % path)
                bad = 1
        elif have != body:
            with open(full, "w") as f:
                f.write(body)
            print("wrote %s (sha256 %s)" % (path, hashlib.sha256(body.encode()).hexdigest()[:12]))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
