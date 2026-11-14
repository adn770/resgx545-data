#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r15-isp's generator. Writes tables/zcut.txt, predictions/zcut.tsv and the per-row frozen
files predictions/zcut/NAME.MODEL.txt; every repository input is read at the commits
session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data)."""
import gzip
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import scorekit  # noqa: E402
import zcut as Z  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
COPIES = {"gen/guard.py": "data:render/closing-r14-isp/gen/guard.py",
          "gen/q261_rule2.py": "data:cited/closing11/plan/c6-q261/q261_rule2.py"}
HEADER = """# R15 zcut, Q241 (E1045, E287, E606, E1037, E065): E1045's form (80 x 40, CR_ISP_ZLSCTL 0x00171014, the depth
# dumped, compare always with writes 0x01c00200, --pixels) on six triangles with one vertex depth 1.25 (cut at 1) or
# -0.25 (cut at 0) whose cut line passes within 1/512 px of 6 to 20 pixel centres (gen/zcut.py): H-PIXCUT (a pixel
# removed iff its depth is past [0, 1]) against H-POLYCLIP (the MTE clips the polygon, made vertices rounded half away
# from zero to 1/256, E1037's CLIP-HA) and H-POLYCLIP-NR (unrounded); E065's 64 x 64 library triangle with ISP word 0
# bit 15 (E065's 48 pixels, the control) and bits 16, 17 each alone (H-EQUIV: the pixels bit 15 leaves; H-NONE: none).
# Controls that can fail: E1045's wind-zhi and wind-zlo replicated, E065's bit 15 replicate. Stop: any fault or hang
# (#limit 0); a row without job: ok or without its whole image (hook_check, rc 24); the session's only stage."""


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def kept(name):
    t = gzip.decompress(pins.blob(Z.E1045 + name + ".txt.gz")).decode()
    drawn = re.search(r"^tri \d+x\d+ #1: (\d+) triangle", t, re.M).group(1)
    hsh = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", t, re.M).group(1)
    sha = pins.sha(gzip.decompress(pins.blob(Z.E1045 + name + ".depth.1.bin.gz")))
    dl = re.search(r"^depth #1: .*$", t, re.M).group(0)
    return drawn, hsh, sha, dl


def build():
    rows, pred, files = [], [HEAD], {}
    # controls first: E1045's depth rows, then E065's bit 15
    for name, k, vt, zt in Z.CTL_Z:
        rows.append(f"{name}|control|safe|expectdiff reads:job,drawn,depth_changed|t10|"
                    + Z.MAIN % (vt, zt, Z.ALWAYS))
        dr, hs, sha, dl = kept(k)
        src = Z.E1045 + k + ".depth.1.bin.gz"
        pred.append(line(name, "drawn", dr, "KEPT", "control", src))
        pred.append(line(name, "hash", hs, "KEPT", "control", src))
        pred.append(line(name, "depth.1.bin", "sha256:" + sha, "KEPT", "control", src))
        pred.append(line(name, "depthline", dl, "KEPT", "control", Z.E1045 + k + ".txt.gz"))
    n, st, bit, _, poke = Z.E065_ROWS[0]
    rows.append(f"{n}|control|safe|expectdiff reads:job,drawn,hash|t10|"
                f"tri --keep-going --wait-ms 20000 --poke '{poke}' --pixels")
    dr, hs = Z.E065_KEPT[bit]
    pred.append(line(n, "drawn", dr, "KEPT", "control", Z.E065))
    pred.append(line(n, "hash", hs, "KEPT", "control", Z.E065))
    # the cut rows
    for r in Z.ROWS:
        name = r[0]
        rows.append(f"{name}|heldout|safe|expectdiff|t10|{Z.row_args(r)}")
        for m in Z.MODELS:
            t = Z.ztext(Z.model_of(Z.row_flat(r), Z.row_depths(r), m))
            files[f"predictions/zcut/{name}.{m}.txt"] = t.encode()
            pred.append(line(name, "zmodel", "sha256:" + pins.sha(t), m, "heldout", "gen/zcut.py"))
    # E065's bits 16 and 17 alone
    for n, st, bit, _, poke in Z.E065_ROWS[1:]:
        rows.append(f"{n}|heldout|safe|expectdiff|t10|tri --keep-going --wait-ms 20000 --poke '{poke}' --pixels")
        for m, (dr, hs) in (("H-EQUIV", Z.E065_KEPT[0x8000]), ("H-NONE", Z.E065_KEPT[bit])):
            pred.append(line(n, "drawn", dr, m, "heldout", Z.E065))
            pred.append(line(n, "hash", hs, m, "heldout", Z.E065))
    import score as SC
    controls = {}
    for ln in rows:
        name, st, _, knobs, tool, args = ln.split("|", 5)
        if st == "control":
            reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")]
            controls[name] = (tuple(reads[0]) if reads else (), dict(name=name, args=args, stage="zcut"))
    scorekit.refuse_unreadable(controls, SC.producible)
    files["tables/zcut.txt"] = (f"#stage zcut\n#limit 0\n{HEADER}\n" + "\n".join(rows) + "\n").encode()
    files["predictions/zcut.tsv"] = "".join(pred).encode()
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
        for d in ("tables", "predictions", "predictions/zcut"):
            full = os.path.join(KP, d)
            for n in sorted(os.listdir(full)) if os.path.isdir(full) else []:
                if not os.path.isdir(os.path.join(full, n)) and f"{d}/{n}" not in files:
                    bad.append(f"{d}/{n} (not written by the generator)")
        for rel, pin in COPIES.items():
            if open(os.path.join(KP, rel), "rb").read() != pins.blob(pin):
                bad.append(f"{rel} (not the byte copy of {pin})")
        print("\n".join(f"differs: {b}" for b in bad) or f"generator current: {len(files)} files")
        return 1 if bad else 0
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
