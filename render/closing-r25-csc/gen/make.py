#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r25-csc's generator (round 24's plan, closing24/plan/rank-round24.md sections 2.2 and
5; DECISIONS-R24 all (a)). Writes tables/csc.txt, predictions/csc.tsv and the programs
bins/NAME.bin, every input read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

One stage, csc (Q181), run in table order (the kit runs no health job between rows). Per format
F of 28 and 29 (E568's fy-F-p0 program as r23-pk ran it), eight rows:

  yF-zc  E037's UYVY copy loading set 0 with zeros       control  hash: E037's black
  yF-a   the fill, unpoked                                control  both models: black
  yF-b   the fill, poked: load set 0 with BT.601          fit      H-FILLLOAD conv, H-FILLIGNORE black
  yF-c   the fill, unpoked (after b)                      fit      H-FILLLOAD conv, H-FILLIGNORE black
  yF-bc  E037's UYVY copy loading set 0 with BT.601       control  hash: E037's conversion
  yF-d   the fill, unpoked                                control  both models: conv
  yF-e   the fill, poked: load set 0 with zeros           heldout  H-FILLLOAD black, H-FILLIGNORE conv
  yF-f   the fill, unpoked (after e)                      heldout  H-FILLLOAD black, H-FILLIGNORE conv

conv is E1097's measured pixels (r23-pk's kept fy-F-p0-csc: E037's conversion of texel x mod 16,
2048 of 2048), black E037's opaque black (0xff000000 at every pixel). Each fill is scored against
the controls of its own half (zc and a before b and c; bc and d before e and f): a control that
does not read its frozen value makes the half's rows cannot tell, never a verdict. Every poke row
reads its echo (`probe NAME: poked ...`) as a premise. Inputs: RESGX545_DATA."""
import gzip  # noqa: F401  (pins unpacks the kept .gz)
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

TOOL = "t22"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("csc",)
FORMATS = (28, 29)
R23 = "data:render/closing-r23-pk/"
BIN = {f: R23 + f"bins/fy-{f}-p0-csc.bin" for f in FORMATS}
KEPT = {f: R23 + f"out/20261115-202948/q181/fy-{f}-p0-csc.txt.gz" for f in FORMATS}

# E037 (texture-tpu-csc): the UYVY copy; set 0 loaded with the BT.601 words, or with zeros
UYVY = "--poke tex:1=0x7d03f01f --poke tex:0^=0x90"
BT601 = ("--poke xfer:17^=0x1 --poke xfer:18=0x00950095 --poke xfer:19=0x00000095 "
         "--poke xfer:20=0x010203ce --poke xfer:21=0x039800cc --poke xfer:22=0")
ZEROS = ("--poke xfer:17^=0x1 --poke xfer:18=0 --poke xfer:19=0 --poke xfer:20=0 "
         "--poke xfer:21=0 --poke xfer:22=0")
ECHO = {"bt601": "xfer:17=0x00000001,xfer:18=0x00950095,xfer:19=0x00000095,"
                 "xfer:20=0x010203ce,xfer:21=0x039800cc,xfer:22=0x00000000",
        "zeros": "xfer:17=0x00000001,xfer:18=0x00000000,xfer:19=0x00000000,"
                 "xfer:20=0x00000000,xfer:21=0x00000000,xfer:22=0x00000000",
        None: "-"}
E037_CSC, E037_BLACK = "0xb6067a95fa98de2d", "0xd3522437a14b6325"
BLACK_SHA = "e3a911a400487825d8d19475cac4c31d8146d8662e054851c42cfe4282b308d4"  # 2048 x ff000000
FILL = "--temps 32 --coords --pixels"
COPY = "copy --every-value --pixels"

# (suffix, set, the copy's set words or the fill's poke, H-FILLLOAD, H-FILLIGNORE)
ROWS = (("zc", "control", "zeros", None, None),
        ("a", "control", None, "black", "black"),
        ("b", "fit", "bt601", "conv", "black"),
        ("c", "fit", None, "conv", "black"),
        ("bc", "control", "bt601", None, None),
        ("d", "control", None, "conv", "conv"),
        ("e", "heldout", "zeros", "black", "conv"),
        ("f", "heldout", None, "black", "conv"))
HALF = {"a": "zc", "b": "zc", "c": "zc", "d": "bc", "e": "bc", "f": "bc"}
CONTROLS_BEFORE = {"a": ("zc",), "b": ("zc", "a"), "c": ("zc", "a"),
                   "d": ("bc",), "e": ("bc", "d"), "f": ("bc", "d")}
POKES = {"bt601": BT601, "zeros": ZEROS}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def pixsha(text):
    """the sha256 of the 2048 pixels as E568's (8 hex digits a pixel, raster order, comma
    joined), from t22's `probe NAME: row Y: ...` lines; None unless 2048."""
    vals = []
    for m in re.finditer(r"^probe \S+: row \d+: ([0-9a-f ]+)$", text, re.M):
        vals += [v.rjust(8, "0") for v in m[1].split()]
    return hashlib.sha256(",".join(vals).encode()).hexdigest() if len(vals) == 2048 else None


def conv_sha(f):
    """E1097's measured conversion of fy-F-p0 (r23-pk's kept fill)."""
    s = pixsha(pins.blob(KEPT[f]).decode())
    assert s and s != BLACK_SHA
    return s


def csc(files):
    rows, pred = [], [HEAD]
    for f in FORMATS:
        sha = {"conv": conv_sha(f), "black": BLACK_SHA}
        for suf, st, w, load, ign in ROWS:
            n = f"y{f}-{suf}"
            if suf in ("zc", "bc"):
                rows.append(f"{n}|{st}|safe|expectdiff reads:hash|{TOOL}|{COPY} {UYVY} {POKES[w]}")
                h = E037_BLACK if w == "zeros" else E037_CSC
                pred.append(line(n, "hash", h, "H-E037", st,
                                 f"E037: the UYVY copy with set 0 loaded with {w}"
                                 + (" (opaque black)" if w == "zeros" else " (BT.601)")))
                continue
            files[f"bins/{n}.bin"] = pins.blob(BIN[f])
            poke = POKES[w] + " " if w else ""
            knobs = "reads:o0" if st == "control" else "-"
            rows.append(f'{n}|{st}|safe|{knobs}|{TOOL}|probe {FILL} {poke}"$S/bins/{n}.bin"')
            pred.append(line(n, "echo", ECHO[w], "H-ECHO", st,
                             "rank-round24.md 2.2: every poke row reads its echo; no poke, none"))
            src = {"conv": "E1097: E037's conversion of texel x mod 16 (r23-pk's kept fy-%d-p0-csc)"
                   % f, "black": "E037: opaque black at 2048 pixels (a set of zeros)"}
            if st == "control":
                pred.append(line(n, "pixsha", sha[load], "H-STATE", st,
                                 f"after {HALF[suf]}: the set its copy loaded; " + src[load]))
                continue
            pred.append(line(n, "pixsha", sha[load], "H-FILLLOAD", st,
                             "the fill's transfer command loads set 0 when poked; " + src[load]))
            pred.append(line(n, "pixsha", sha[ign], "H-FILLIGNORE", st,
                             "the fill ignores the load; the copy's set is read; " + src[ign]))
    return rows, pred


HEADERS = {
    "csc": """#stage csc
#limit 0
# csc (Q181, rank-round24.md 2.2, R24 all a): does a fill's transfer command load colour-space set 0? Per format 28, 29
# (E568's fy-F-p0 on t22): E037's UYVY copy loading set 0 with zeros (control: black), the fill unpoked (control:
# black), poked with BT.601 (fit), unpoked (fit); E037's copy loading BT.601 (control: E037's hash), the fill unpoked
# (control: E1097's conversion), poked with zeros (held out), unpoked (held out). Frozen H-FILLLOAD (poked fills load
# the set; the next fill keeps it) against H-FILLIGNORE (the fills read the copy's set). In table order, no health job
# between rows. Stop: a probe row whose echo count is not its poke count (run/hooks.sh), any fault or hang.""",
}


def build():
    files = {}
    rows, pred = csc(files)
    files["tables/csc.txt"] = (HEADERS["csc"] + "\n" + "\n".join(rows) + "\n").encode()
    files["predictions/csc.tsv"] = "".join(pred).encode()
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
