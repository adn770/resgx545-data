#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r15-isp's scorer, frozen before the run. Every verdict rule comes from kit/scorekit.py
(headline), the kept files are read through kit/kitscore.py (byte copies of resgx545 158bdc5,
pinned in FROZEN.commits); the frozen predictions are predictions/ (gen/make.py), the forms'
frozen images are predictions/zcut/NAME.MODEL.txt (gen/zcut.py). Standard library only.

  score.py zcut KEPT_DIR        CONTROL, ROW, READING lines, then SUMMARY lines (exit 0)
  score.py gate zcut ROOTS...   exit 0 (one stage: nothing is gated by another's controls)
  score.py premise zcut KEPT_DIR  STOP lines and exit 1 when a control has no reading

zcut (Q241): a cut row holds a form (H-PIXCUT, H-POLYCLIP, H-POLYCLIP-NR) when every pixel of the
80 x 40 target (`row N:`, the triangle 0xff00ff00) the form claims is as drawn and the number of
dwords holding 1.0 in the `depth #1:` line lies in the form's range (the dwords it says are 1.0 up
to those plus the band pixels it does not claim; the dump itself is kept, not read: a fold script
checks the dwords against predictions/zcut/*.txt). The controls: E1045's two depth rows, their
frozen drawn count, hash and depth line (counts and commonest words), E065's bit 15 row, its drawn
count and hash. E065's bits 16, 17 rows hold H-EQUIV (the pixels bit 15 leaves: drawn 48 and its
hash) or H-NONE (drawn 0 and its hash). H-PIXCUT, H-POLYCLIP, H-POLYCLIP-NR are gated by
zcut-ctl-zhi and zcut-ctl-zlo, H-EQUIV and H-NONE by zcut-ctl-b15.
READING lines: a cut row's pixels where H-POLYCLIP and H-POLYCLIP-NR differ (and which one the
output drew), and a bits row's pixel set against the control's."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"zcut": (".txt",) + FIXED}
GATES = {}
GREEN = 0xFF00FF00
ROW = re.compile(r"(?:^|: )row (\d+): ([0-9a-fA-Fx ]+)$", re.M)
CUT = ("H-PIXCUT", "H-POLYCLIP", "H-POLYCLIP-NR")


def producible(row):
    a = row["args"].split()
    if a[:1] != ["tri"]:
        return set()
    keys = {"job", "hash", "diff", "drawn"}
    if "--pixels" in a:
        keys.add("pixels")
    if "--depth" in a:
        keys.add("depth_changed")
    return keys


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def done(cases, n):
    return n in cases and K.completed(cases[n]) is True


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")


def frozen(name, want):
    import hashlib
    body = open(os.path.join(KP, "predictions", "zcut", name)).read()
    if "sha256:" + hashlib.sha256(body.encode()).hexdigest() != want:
        raise SystemExit("score.py: zcut/%s is not the frozen file" % name)
    return body


def pixels(text, w, h):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if not rows or sorted(rows) != list(range(len(rows))):
        return None
    px = [v for y in sorted(rows) for v in rows[y]]
    return px if len(px) == w * h else None


def first(text, pattern):
    m = re.search(pattern, text or "", re.M)
    return m.group(1) if m else None


def opt(args, name, default=None):
    a = args.split()
    return a[a.index(name) + 1] if name in a else default


def depth_line(text):
    m = re.search(r"^depth #1: .*$", text or "", re.M)
    return m.group(0) if m else None


# ================================================================================ zcut
def score_zcut(d):
    import zcut as Z
    P, cases, lines = K.predictions(KP, "zcut"), K.rows(d, "cases.tsv"), []
    ctl, per, imgs = {}, {}, {}
    for r in K.table(KP, "zcut"):
        n = r["name"]
        ok = done(cases, n)
        text = K.text(d, n + ".txt") if ok else None
        w, h = int(opt(r["args"], "--width", 64)), int(opt(r["args"], "--height", 64))
        drawn = first(text, r"^tri \d+x\d+ #1: (\d+) triangle")
        hsh = first(text, r"^target: \d+x\d+ hash (0x[0-9a-f]+)")
        px = pixels(text, w, h) if ok else None
        img = None if px is None else [v == GREEN for v in px]
        imgs[n] = img
        pr = P.get(n, {})
        res, extra = {}, ""
        for m in pr.get("drawn", {}):
            res[m] = None if drawn is None or hsh is None else (drawn, hsh) == (str(pr["drawn"][m]), pr["hash"][m])
        if "depthline" in pr:
            got = depth_line(text)
            res["KEPT"] = None if res.get("KEPT") is None or got is None else res["KEPT"] and got == pr["depthline"]["KEPT"]
        rd = "drawn %s, hash %s" % (drawn, hsh)
        for m, hsum in pr.get("zmodel", {}).items():
            zm = Z.zparse(frozen("%s.%s.txt" % (n, m), hsum))
            res[m] = None if not ok else Z.zcheck(zm, text, img)
        if "zmodel" in pr and ok:
            ones = Z.parse_ones(text)
            rd += ", background dwords %s" % ones
            ha, nr = (Z.zparse(frozen("%s.%s.txt" % (n, m), pr["zmodel"][m])) for m in ("H-POLYCLIP", "H-POLYCLIP-NR"))
            part = [i for i in range(Z.W * Z.H) if ha["drawn"][i] is not None and nr["drawn"][i] is not None
                    and ha["drawn"][i] != nr["drawn"][i]]
            if img is not None:
                extra = "; READING parting pixels %d: drawn as H-POLYCLIP %d, as H-POLYCLIP-NR %d" % (
                    len(part), sum(img[i] == ha["drawn"][i] for i in part), sum(img[i] == nr["drawn"][i] for i in part))
        if r["set"] == "control":
            st = None if not res or any(v is None for v in res.values()) else all(res.values())
            ctl[n] = st
            lines.append("CONTROL %s: %s; %s: %s" % (n, rd, "; ".join("%s %s" % (m, word(s)) for m, s in res.items()),
                                                    cword(st)))
            continue
        for m, s in res.items():
            per.setdefault(m, []).append(s)
        lines.append("ROW %s: %s; %s%s" % (n, rd, "; ".join("%s %s" % (m, word(s)) for m, s in res.items()), extra))
    for n in ("zcut-b16", "zcut-b17"):
        a, b = imgs.get("zcut-ctl-b15"), imgs.get(n)
        if a is not None and b is not None:
            lines.append("READING %s: pixel set %s the control's (%d differing of %d)" % (
                n, "is" if a == b else "is not", sum(x != y for x, y in zip(a, b)), len(a)))
    z_ctl = {k: v for k, v in ctl.items() if k in ("zcut-ctl-zhi", "zcut-ctl-zlo")}
    e_ctl = {k: v for k, v in ctl.items() if k == "zcut-ctl-b15"}
    claims = {"H-PIXCUT": "the plane is drawn and a pixel is removed iff its depth is past [0, 1]",
              "H-POLYCLIP": "the MTE clips the polygon at the plane, made vertices rounded half away from zero to 1/256",
              "H-POLYCLIP-NR": "the MTE clips the polygon at the plane, made vertices unrounded",
              "H-EQUIV": "ISP word 0 bits 16 and 17 leave the pixels bit 15 leaves (E065's 48)",
              "H-NONE": "ISP word 0 bits 16 and 17 each leave no pixel"}
    for m, rows in per.items():
        if m == "KEPT":
            continue
        c = z_ctl if m in CUT else e_ctl
        lines.append("SUMMARY: zcut: %s: %s" % (m, SK.headline(claims[m], c, rows)))
    return lines


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        print("\n".join(score_zcut(argv[2])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
