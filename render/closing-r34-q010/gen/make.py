#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r34-q010's table and frozen predictions (closing29/plan/rank-round34.md section 3.1,
Q010; safe class). Standard library only. Every kept input is read at the data commit of
session.toml [freeze] (`git show`, never the working tree) and pinned there.

  python3 gen/make.py          write tables/c.txt, predictions/c.tsv, mock/kept/
  python3 gen/make.py --check  exit 1 when a written file is not what the generator writes

One stage `c`, every row in it (no `after` word, no stage boundary between a load and its read:
the kit's health pair runs at every stage's begin and end, E1112). Copies on t30 with E1103's and
E1112's forms (E037's UYVY copy: `copy --every-value --pixels --poke tex:1=0x7d03f01f --poke
tex:0^=0x90`; a load adds `--poke xfer:17^=0x1` and set 0's five words in xfer:18 to 22).

  Z  load zeros (control: black)          R  the copy without the load (the reading)
  L  load BT.601 (control: E037's hash)   X  the job under test, between L and R

Two in-session references open the stage (z0-ld, z0-rd: a load of zeros, then R reads black on
this module and tool), then triples L, X, R:

  T0  no X (R right after L and a debugfs reset: clause (a), the control that can fail)  x2
  T1  t10 `fill` (the health fill's argv, as lib_kit.sh health_ok runs it)              x2
  T2  t10 `tri` (the health triangle's argv)                                            x2
  T3  t30 `copy --every-value --pixels` (a transfer that is not a fill, no YUV, no load) x2
  T4  none, `idle:60` on R (a 60 s wait after R's reset, right before R)                x1
  T5  none, `idle:120` on R                                                              x1
  T6  t10 `fill` then t10 `tri` with `noreset` (the pair as health runs it)              x1

The second replicates (T3, T2, T1, T0) run after T6 in reversed order; every prediction is frozen
before the first is read. 32 jobs.

R's reading is the copy's `target: 64x32 hash H`: KEPT (0xb6067a95fa98de2d, E037's BT.601
conversion; r29-flag2's q010-pre and q010-ld2, E1112), CLEARED (0xd3522437a14b6325, black; r29-flag2's
q010-af and q010-p1), anything else cannot tell. Both values are job outputs the hardware already
gave (L3 of the plan), and this session re-reads each: every L must read KEPT and z0-ld, z0-rd
CLEARED (controls), so no value is frozen from another session's idle or register readings."""
import gzip
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
DATA_COMMIT = CFG["freeze"]["data"]
DATA = os.environ.get("RESGX545_DATA_REPO", "/Users/jtorra/src/resgx545-data")

# ---- the kept records the frozen values come from (pinned in session.toml) --------------------
F2 = "render/closing-r29-flag2/out/20261116-073242/h1"   # E1112 (module E0CC4027, t22)
KEPT = {  # mock/kept/NAME: the kept job outputs the mock answers with and the tests replay
    "bt601.txt.gz": f"{F2}/q010-pre.txt.gz",      # no load after a load and a debugfs reset: KEPT
    "zeros.txt.gz": f"{F2}/q010-af.txt.gz",       # no load after the health pair: CLEARED
    "load.txt.gz": f"{F2}/q010-ld2.txt.gz",       # the BT.601 load
    "fill.txt.gz": f"{F2}/begin.fill1.txt.gz",    # the health fill (t10 `fill`)
    "tri.txt.gz": f"{F2}/begin.health1.txt.gz",   # the health triangle (t10 `tri`)
}
KEPT_HASH = "0xb6067a95fa98de2d"
CLEARED_HASH = "0xd3522437a14b6325"

COPY = "copy --every-value --pixels --poke tex:1=0x7d03f01f --poke tex:0^=0x90"
BT601 = ("0x950095", "0x95", "0x10203ce", "0x39800cc", "0")
ZEROS = ("0", "0", "0", "0", "0")


def load(words):
    return COPY + " --poke xfer:17^=0x1" + "".join(
        f" --poke xfer:{18 + i}={w}" for i, w in enumerate(words))


L_ARGS, Z_ARGS, R_ARGS = load(BT601), load(ZEROS), COPY
X = {  # the jobs under test: (tool, args)
    "fill": ("t10", "fill"),
    "tri": ("t10", "tri"),
    "copy": ("t30", "copy --every-value --pixels"),
}
CTL = "expectdiff reads:job,hash"

# triple: (name, [X kinds], idle seconds before R, R is a control)
TRIPLES = [
    ("t0a", [], 0, True),
    ("t1a", ["fill"], 0, False),
    ("t2a", ["tri"], 0, False),
    ("t3a", ["copy"], 0, False),
    ("t4", [], 60, False),
    ("t5", [], 120, False),
    ("t6", ["fill", "tri"], 0, False),
    # second replicates, reversed (L4)
    ("t3b", ["copy"], 0, False),
    ("t2b", ["tri"], 0, False),
    ("t1b", ["fill"], 0, False),
    ("t0b", [], 0, True),
]
# which held-out R rows each hypothesis says read CLEARED (every other R row: KEPT)
R_ROWS = [t[0] + "-rd" for t in TRIPLES if not t[3]]
CLEARS = {
    "H-FILL": {"t1a-rd", "t1b-rd", "t6-rd"},
    "H-TRI": {"t2a-rd", "t2b-rd", "t6-rd"},
    "H-BOTH": {"t1a-rd", "t1b-rd", "t2a-rd", "t2b-rd", "t6-rd"},
    "H-NONE": set(),
}
# side hypotheses, scored on their own rows only (their rivals: every full pattern above)
SIDE = {
    "H-IDLE": {"t4-rd": CLEARED_HASH, "t5-rd": CLEARED_HASH},
    "H-COPYNL": {"t3a-rd": CLEARED_HASH, "t3b-rd": CLEARED_HASH},
}
SRC_KEPT = "E1112 q010-pre, q010-ld2 (E037's hash; E1097, E1103)"
SRC_CLR = "E1112 q010-af, q010-p1 (E037's black; E1103 y28-zc)"

HEADER = """#stage c
#limit 0
# r34-q010 c (Q010, rank-round34.md 3.1; safe: no expectfault, #limit 0, no kreg, no knob): which job clears
# colour-space set 0? z0-ld/z0-rd: a zeros load, then the copy without the load reads black (references of this
# session). Triples L (load BT.601, control: E037's hash), X (the job under test), R (the copy without the load:
# KEPT 0xb6067a95fa98de2d or CLEARED 0xd3522437a14b6325). T0 no X (control), T1 t10 fill, T2 t10 tri, T3 t30 plain
# copy, T4 idle 60 s, T5 idle 120 s, T6 fill then tri (noreset, the health pair); T3-T0 again reversed.
# Frozen: H-FILL, H-TRI, H-BOTH, H-NONE (every R row), H-IDLE (T4, T5), H-COPYNL (T3). Stop: any fault or hang (4), a
# control without job/hash (25), a row without its job line, target hash or draw (hook_check, 24).
"""


def rows():
    out = [("z0-ld", "control", CTL, "t30", Z_ARGS), ("z0-rd", "control", CTL, "t30", R_ARGS)]
    for name, xs, idle, rctl in TRIPLES:
        out.append((f"{name}-ld", "control", CTL, "t30", L_ARGS))
        for k, x in enumerate(xs):
            tool, args = X[x]
            knobs = "expectdiff" if x == "copy" else "-"
            if k > 0:
                knobs = "noreset"       # T6: the triangle right after the fill, as health_ok runs it
            out.append((f"{name}-x{x[0]}", "between", knobs, tool, args))
        rk = CTL if rctl else "expectdiff"
        if idle:
            rk += f" idle:{idle}"
        out.append((f"{name}-rd", "control" if rctl else "heldout", rk, "t30", R_ARGS))
    return out


def table():
    return HEADER + "".join(f"{n}|{s}|safe|{k}|{t}|{a}\n" for n, s, k, t, a in rows())


def predictions():
    lines = ["case\tquantity\tvalue\tmodel\tset\tsource"]
    for n, s, _, _, a in rows():
        if s != "control":
            continue
        h = CLEARED_HASH if n.startswith("z0") else KEPT_HASH
        src = SRC_CLR if h == CLEARED_HASH else SRC_KEPT
        lines.append(f"{n}\tjob\tok\tH-REF\tcontrol\tthe copy's job line (E1112)")
        lines.append(f"{n}\thash\t{h}\tH-REF\tcontrol\t{src}")
    for n in R_ROWS:
        for m, clr in CLEARS.items():
            h = CLEARED_HASH if n in clr else KEPT_HASH
            lines.append(f"{n}\thash\t{h}\t{m}\theldout\t{SRC_CLR if h == CLEARED_HASH else SRC_KEPT}")
        for m, rr in SIDE.items():
            if n in rr:
                lines.append(f"{n}\thash\t{rr[n]}\t{m}\theldout\t{SRC_CLR}")
    return "\n".join(lines) + "\n"


def data(path):
    return subprocess.run(["git", "-C", DATA, "show", f"{DATA_COMMIT}:{path}"], check=True,
                          capture_output=True).stdout


def kept_checked():
    """The kept files, checked against the values this generator freezes."""
    out = {}
    for name, path in KEPT.items():
        b = data(path)
        t = gzip.decompress(b).decode()
        h = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", t, re.M)
        want = {"bt601.txt.gz": KEPT_HASH, "load.txt.gz": KEPT_HASH, "zeros.txt.gz": CLEARED_HASH}.get(name)
        if want and (not h or h.group(1) != want):
            sys.exit(f"{path}: hash {h and h.group(1)}, not {want}: nothing written")
        out[name] = b
    return out


def outputs():
    files = {"tables/c.txt": table().encode(), "predictions/c.tsv": predictions().encode()}
    for name, b in kept_checked().items():
        files["mock/kept/" + name] = b
    return files


def main(argv):
    files = outputs()
    if argv[1:] == ["--check"]:
        bad = [p for p, b in files.items()
               if not os.path.exists(os.path.join(KP, p)) or open(os.path.join(KP, p), "rb").read() != b]
        if bad:
            print("not current: " + ", ".join(bad))
            return 1
        print("current")
        return 0
    for p, b in files.items():
        full = os.path.join(KP, p)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(b)
    print("wrote " + ", ".join(sorted(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
