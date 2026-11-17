#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/fit.py: the kept rows r34-ev2's hypotheses are frozen from, read with score/score.py's own
analyse() (the readings the held-out rows are scored on), from the data repository at the
session's frozen data commit (session.toml [freeze], every file pinned).

  fit.py           write gen/fit.txt
  fit.py --check   exit 1 when gen/fit.txt is not what this script writes

Fit sets (none of them a row of this session): r13-dpm pr2 (E1032: 0x012c, 0x0660, 0x0748 and
twelve more at 7.5 us, the same overflow probe, with snap0), r15-dpm pr4 (E1057: 0x0748 alone at
1.7 us, the same probe), E547's event timelines (0x0118 + 0x012c at 1.7 and 3.7 us: copies,
fills, 1024x768 partial jobs)."""
import gzip
import os
import subprocess
import sys
import tomllib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402

CFG = tomllib.loads(open(os.path.join(HERE, "session.toml")).read())
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
R13 = "render/closing-r13-dpm/out/20261113-212348/pr2/"
R15 = "render/closing-r15-dpm/out/20261114-071243/pr4/"
EV = "platform/event-bits/dumps/event-timelines/"
R13_ROWS = ["pr2-c0-1", "pr2-c1-1", "pr2-c2-1", "pr2-c4-1", "pr2-c1-2", "pr2-c0-2", "pr2-c4-2",
            "pr2-c2-2"]
R15_ROWS = ["pr4-c0-1", "pr4-c1-1", "pr4-c4-1", "pr4-c7-1", "pr4-c1-2", "pr4-c0-2", "pr4-c7-2",
            "pr4-c4-2", "pr4-c7-3", "pr4-c4-3"]
EV_ROWS = [f"tl-{k}-r{r}-{i}" for k in ("copy", "fill", "partial") for r in (2, 7)
           for i in range(1, 6)]
R34 = "render/closing-r34-ev/out/20261117-001058/"
R34_ROWS = (["e0/e0-o1", "e0/e0-c1", "e0/e0-l1", "e0/e0-l2", "e0/e0-c2", "e0/e0-o2"]
            + [f"e1/e1-{n}" for n in ("c0a", "p1a", "p2a", "p4a", "p7a", "cpc", "cp1", "lcc",
                                     "lc1", "lc2", "cp2", "p7b", "p4b", "p2b", "p1b", "c0b")]
            + ["e2c/e2c-o1", "e2c/e2c-c1", "e2c/e2c-c2", "e2c/e2c-o2"]
            + [f"e2/e2-{n}" for n in ("c0", "p1", "p4", "cpc", "cp1", "p7")]
            + ["d0/d0-o1", "d0/d0-o2"])
PB = {"c0": "0x422", "c1": "0x2b6", "c2": "0x1c2", "c4": "0xe2", "c7": "0x82"}


def pins():
    """Every data file this script reads (session.toml must pin each)."""
    out = [R13 + n + ".txt.gz" for n in R13_ROWS] + [R13 + n + ".snap0.regs.gz" for n in R13_ROWS]
    out += [R15 + n + ".txt.gz" for n in R15_ROWS] + [EV + n + ".txt.gz" for n in EV_ROWS]
    out += [R34 + n + ".txt.gz" for n in R34_ROWS]
    return ["data:" + p for p in out]


def blob(path):
    r = subprocess.run(["git", "-C", DATA, "show", f"{CFG['freeze']['data']}:{path}"],
                       capture_output=True, timeout=60, check=True)
    return (gzip.decompress(r.stdout) if path.endswith(".gz") else r.stdout).decode(
        errors="replace")


KEYS = ("ivl", "r012c", "r0118", "r0660", "r0748", "img", "ovl", "bits", "oom", "mt", "gbl",
        "thr", "e0", "e14", "e18", "w0max", "w1max", "w13max", "w18max", "s2", "s2words", "b0n",
        "b0max", "b1n", "b1max", "b2n", "b2max", "b3n", "b3max", "b4n", "b4ms", "pcn", "pcfin")


def line(name, a, extra=""):
    return f"{name}{extra}: " + " ".join(f"{k}={a[k]}" for k in KEYS if k in a)


def text():
    out = ["# gen/fit.py: the kept rows' readings (score.analyse), the fit of r34-ev2's hypotheses",
           f"# data {CFG['freeze']['data']}"]
    out.append("## r13-dpm pr2 (E1032): overflow probe, 16 registers at 7.5 us; snap0's 0x012c, "
               "0x0118, 0x0660 against the first samples")
    for n in R13_ROWS:
        a = SC.analyse(blob(R13 + n + ".txt.gz"))
        snap = blob(R13 + n + ".snap0.regs.gz")
        same = []
        for off in ("0x012c", "0x0118", "0x0660"):
            v = next((ln.split()[2] for ln in snap.splitlines()
                      if ln.split()[:2] == ["reg", off]), None)
            key = "r" + off[2:]
            same.append(f"{off} snap0 {v} first {a.get(key, '-')}")
        out.append(line(n, a, f" (PB {PB[n[4:6]]})") + " | " + "; ".join(same))
    out.append("## r15-dpm pr4 (E1057): overflow probe, 0x0748 alone at 1.7 us")
    for n in R15_ROWS:
        out.append(line(n, SC.analyse(blob(R15 + n + ".txt.gz")), f" (PB {PB[n[4:6]]})"))
    out.append("## E547 event timelines: 0x0118 + 0x012c (copy, fill, 1024x768 partial)")
    for n in EV_ROWS:
        out.append(line(n, SC.analyse(blob(EV + n + ".txt.gz"))))
    out.append("## r34-ev (E1137, E1138): the same probe and copies on 7CE8E38E, one or two "
               "registers at 3.1 to 4.2 us")
    for n in R34_ROWS:
        out.append(line(n.split("/")[1], SC.analyse(blob(R34 + n + ".txt.gz"))))
    return "\n".join(out) + "\n"


def main(argv):
    p = os.path.join(HERE, "gen", "fit.txt")
    t = text()
    if "--check" in argv:
        if not os.path.exists(p) or open(p).read() != t:
            print("gen/fit.txt: not what gen/fit.py writes")
            return 1
        return 0
    open(p, "w").write(t)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
