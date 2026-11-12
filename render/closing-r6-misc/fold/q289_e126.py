# SPDX-License-Identifier: MIT
"""Post hoc (r6-misc fold, 2026-11-12): E126's 128 x 128 pictures against the place rule E884 holds
on the fill.  Rule: the end-of-tile task of the 32 x 16 tile t (per axis) stores at the place its
U1 field names read in half-tile units, place = field >> 1, and nothing where that lies outside
the target.  E126's probe XORs the mask m into the field it built (2t), so the rule predicts that
32-pixel columns move t -> t ^ (m >> 1) and 16-row rows r -> r ^ (m >> 1), and that no pixel is
written once every place lies outside.  The bit 3 (x) and bit 12 (y) pictures stand for the
unflipped one (E126, E043, E044), so those two cases check only that the rule leaves them in
place.  Usage: q289_e126.py DATA (resgx545-data)."""
import os
import sys


def pictures(path):
    pics, cur, name = {}, None, None
    for ln in open(path):
        if ln.startswith("probe-case "):
            name = ln.split()[1]
            cur = pics.setdefault(name, {"rows": {}, "none": False})
        elif ": row " in ln:
            head, vals = ln.split(": row ", 1)
            n, rest = vals.split(":", 1)
            cur["rows"][int(n)] = rest.split()
        elif "failed: no pixel written" in ln:
            cur["none"] = True
    return pics


def moved(base, axis, unit, k, w=128, h=128):
    """base with blocks of `unit` pixels along `axis` moved b -> b ^ k (None where nothing lands)."""
    out = [[None] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if axis == "x":
                b = x // unit
                nb = b ^ k
                nx = nb * unit + x % unit
                if 0 <= nx < w:
                    out[y][nx] = base[y][x]
            else:
                b = y // unit
                nb = b ^ k
                ny = nb * unit + y % unit
                if 0 <= ny < h:
                    out[ny][x] = base[y][x]
    return out


def main(data):
    root = os.path.join(data, "pds/pixel-event")
    total = {"rule": [0, 0]}
    for axis, d, low in (("x", "pds-pixel-event-eot-u1-tile-x-flip", 3), ("y", "pds-pixel-event-eot-u1-tile-y-flip", 12)):
        pics = pictures(os.path.join(root, d, "raw.txt"))
        names = sorted(pics, key=lambda s: int(s.rsplit("__", 1)[1]))
        base = [pics[names[0]]["rows"][y] for y in range(128)]
        for i, n in enumerate(names):
            bit = low + i
            m = 1 << i
            p = pics[n]
            seen = None if p["none"] else [p["rows"][y] for y in range(128)]
            # the rule: 32-pixel columns (x) or 16-row rows (y), place = (2t ^ m) >> 1
            k = m >> 1
            unit = 32 if axis == "x" else 16
            span = 128 // unit
            if k >= span:
                pred_rule = None
            else:
                pred_rule = moved(base, axis, unit, k)
            res = []
            for lab, pred in (("rule", pred_rule),):
                if pred is None:
                    ok = seen is None
                    txt = "no pixel" if ok else "pixels written"
                else:
                    if seen is None:
                        ok, txt = False, "nothing written"
                    else:
                        diff = sum(1 for y in range(128) for x in range(128) if pred[y][x] != seen[y][x])
                        ok, txt = diff == 0, "%d of 16384 differ" % diff
                total[lab][0 if ok else 1] += 1
                res.append("%s %s (%s)" % (lab, "y" if ok else "n", txt))
            print("%s bit %2d mask %3d: %s" % (axis, bit, m, "; ".join(res)))
    for lab in ("rule",):
        print("%s: %d of %d cases match" % (lab, total[lab][0], sum(total[lab])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/Users/jtorra/src/resgx545-data"))
