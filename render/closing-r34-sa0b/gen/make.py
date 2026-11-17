#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r34-sa0b's generator, the corrected rerun of r34-sa0 (E1139; closing29/plan/rank-round34.md
section 3.6, Q136). Writes
tables/s.txt, predictions/s.tsv and the programs bins/NAME.bin; every input is read at the
commits session.toml's [freeze] names or at the bound tool sources' own commits (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Q136: "how long does a value written to sa0 last across jobs, and is the 0xff00ff00 and
0xff203040 mixture that pa0 reads in the first jobs of a table the colour left by the job before
it?" Every program is a plain `probe` fill (t30, 64 x 32, 2048 instances, as E484's and E496's
tables ran), so the job before a reader is the one the colour rule names (E484, E496 [infer]).

  W  (writer, control)  every instance `iaddu32.testtaz.chan0 sa0, p0, r1, r2` with r1 = 1 and
     r2 = M - 1 (E521/E1106: (r1 & 0xffff) + r2 = M), then `mov r3, sa0` stored to scratch dword 0
     (the in-job readback, E496/E1106: M) and o0 = K1. M is distinct per row (both replicates).
  R  (sa0 reader)  `mov r10, sa0`, r10 stored to dword 0 and output as o0 (E496's reader form).
     E1139: r34-sa0's readers output sa0 ^ key and their pixels came in pairs {v, v ^ key}, about
     1904 and 144 of 2048: what a reader reads aliases what earlier instances of the same job
     wrote to o0 [infer]. A reader that outputs the value it read is that alias's fixed point.
  P  (pa0 reader)  `mov r10, pa0`, the same.
  K  (colour job, control)  writes no sa, pa: dword 0 and o0 = K3.
  X  t10 `fill` (0xff336699, its own output line) and t10 `tri` (colours[0] of t10's source:
     0xff00ff00 triangle, 0xff203040 background), the kit's health pair's argv.

Groups (first replicate in this order, the second reversed; markers M = 0x5a0c0000 | rep << 8 | i):
  nr   W, R noreset                      rs   W, R after a debugfs reset (no job between)
  i10  W, R noreset idle:10              i60  W, R noreset idle:60      i120  W, R noreset idle:120
  k3   W, K, R (noreset)                 fl   W, t10 fill, R            tr    W, t10 tri, R
  ptr  t10 tri, P noreset (fit: E496's mixture re-read)
  pk3  K, P noreset    pfl  t10 fill, P noreset    pk3r  K, P after a debugfs reset
"""
import hashlib
import os
import pathlib
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

sys.path.insert(0, os.path.join(pins.MAIN, "tools", "usse-asm"))
import probe as P  # noqa: E402

STAGE = "s"
PROBE_TOOL = "t30"
HEALTH_TOOL = "t10"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
K1 = 0xC0DE0A01          # W's colour
K2 = 0x00000000          # no key: R outputs sa0 (r34-sa0 had 0x33330000, E1139)
K3 = 0xC0DE0A03          # K's colour (a job that writes no sa or pa)
K4 = 0x00000000          # no key: P outputs pa0 (r34-sa0 had 0x00550000)
REPS = {"a": 0x0A, "b": 0x0B}
# E1139's post hoc reading of r34-sa0 (the fit of this rerun's frozen hypotheses)
E1139_POSTHOC = "data:render/closing-r34-sa0/fold/posthoc.out"
# E496's pa-dest table (usse-pa-dest, published): its first job's pa0 mixture and its "before" job
E496_RAW = "data:usse/pa-dest/usse-pa-dest-persist/raw.txt"
E496_ENV = "data:usse/pa-dest/env.toml"
# the health pair's kept texts on this module and tools (r34-q010, E1134): the mock's t10 answers
Q010_C = "data:render/closing-r34-q010/out/20261116-231015/c"
KEPT_FILL = Q010_C + "/begin.fill1.txt.gz"
KEPT_TRI = Q010_C + "/begin.health1.txt.gz"
FULL_A = ("H-PERSIST", "H-ONEJOB", "H-COLOUR")
# (group, reader kind, X jobs between, the reader's knob words)
GROUPS = [
    ("nr", "R", [], "noreset"),
    ("rs", "R", [], "-"),
    ("i10", "R", [], "noreset idle:10"),
    ("i60", "R", [], "noreset idle:60"),
    ("i120", "R", [], "noreset idle:120"),
    ("k3", "R", ["k"], "noreset"),
    ("fl", "R", ["fill"], "noreset"),
    ("tr", "R", ["tri"], "noreset"),
    ("ptr", "P", ["tri"], "noreset"),
    ("pk3", "P", ["k"], "noreset"),
    ("pfl", "P", ["fill"], "noreset"),
    ("pk3r", "P", ["k"], "-"),
]
IDLE = ("i10", "i60", "i120")


def marker(rep, i):
    return 0x5A0C0000 | REPS[rep] << 8 | i


def tri_colours():
    """t10's first-render colours (cmd_tri colours[0]) from its bound source."""
    src = pins.tool_source(HEALTH_TOOL).decode()
    m = re.search(r"cmd_tri\(.*?colours\[2\]\[2\] = \{\s*\{ (0x[0-9a-f]+), (0x[0-9a-f]+) \}",
                  src, re.S)
    return int(m.group(1), 16), int(m.group(2), 16)


def fill_colour():
    """t10's bare `fill` colour (its default fill job) from its bound source."""
    src = pins.tool_source(HEALTH_TOOL).decode()
    m = re.search(r"\.width = 64, \.height = 32, \.stride = 256, \.colour = (0x[0-9a-f]+)", src)
    return int(m.group(1), 16)


def e496_first():
    """E496's first pa0 reader's o0 line and its table's `before` job (the runner's baseline)."""
    raw = pins.blob(E496_RAW).decode()
    o0 = re.search(r"^probe usse-pa-dest-persist__0: o0 (.*)$", raw, re.M).group(1)
    env = pins.blob(E496_ENV).decode()
    before = re.search(r'^before = "(.*)"$', env, re.M).group(1)
    return o0, before


def posthoc_fit():
    """E1139's post hoc labels of r34-sa0's readers, as `M` and `PREV` counts per kind."""
    txt = pins.blob(E1139_POSTHOC).decode()
    labs = re.findall(r"^(\S+?): pairs .*: POST HOC (\w+)$", txt, re.M)
    r = [lab for n, lab in labs if not n.startswith("p")]
    p = [lab for n, lab in labs if n.startswith("p")]
    return (f"R M {r.count('M')} PREV {r.count('PREV')} of {len(r)}; "
            f"P PREV {p.count('PREV')} of {len(p)}")


def program(kind, m=None):
    lines = [f"; r34-sa0 {kind} (gen/make.py)", "phas #0, #0, pixel, end, parallel",
             "mov.skipinv r29, #0x5CAF0000"]
    if kind == "w":
        lines += ["mov.skipinv r1, #0x00000001", "mov.skipinv r2, #0x%08X" % (m - 1),
                  "iaddu32.testtaz.chan0 sa0, p0, r1, r2", "mov r3, sa0",
                  "stad [r29,+#0], r3", "mov.skipinv r10, #0x%08X" % K1]
    elif kind in ("r", "p"):
        lines += ["mov r10, %s" % ("sa0" if kind == "r" else "pa0"), "stad [r29,+#0], r10"]
    elif kind == "k":
        lines += ["mov.skipinv r10, #0x%08X" % K3, "stad [r29,+#0], r10"]
    lines += ["idf drc0, bif", "wdf drc0", "mov.skipinv.end o0, r10"]
    return "\n".join(lines) + "\n"


def asm(text):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "x.bin"
        P._assemble(text, f, "usse")
        return f.read_bytes()


def probe_args(binname):
    return f'probe --temps 32 "$S/bins/{binname}.bin"'


def group_rows(g, kind, xs, knobs, rep, idx):
    """[(name, set, knobs, tool, args, role, extra)] of one group's replicate."""
    out = []
    t = g + rep
    if kind == "R":
        m = marker(rep, idx)
        out.append((f"{t}-w", "control", "reads:sa,top", PROBE_TOOL, probe_args("w-%08x" % m),
                    "W", m))
        for x in xs:
            if x == "k":
                out.append((f"{t}-x", "control", "noreset reads:sa,top", PROBE_TOOL,
                            probe_args("k"), "K", None))
            else:
                out.append((f"{t}-x", "between", "noreset", HEALTH_TOOL, x, x.upper(), None))
        out.append((f"{t}-r", "heldout", knobs, PROBE_TOOL,
                    probe_args("r"), "R", m))
    else:
        (x,) = xs
        if x == "k":
            out.append((f"{t}-x", "control", "reads:sa,top", PROBE_TOOL, probe_args("k"), "K",
                        None))
        else:
            out.append((f"{t}-x", "between", "-", HEALTH_TOOL, x, x.upper(), None))
        out.append((f"{t}-p", "fit" if g == "ptr" else "heldout", knobs, PROBE_TOOL,
                    probe_args("p"), "P", None))
    return out


def all_rows():
    idx = {g: i + 1 for i, (g, kind, _, _) in enumerate(GROUPS) if kind == "R"}
    rows = []
    for rep, order in (("a", GROUPS), ("b", list(reversed(GROUPS)))):
        for g, kind, xs, knobs in order:
            rows += group_rows(g, kind, xs, knobs, rep, idx.get(g))
    return rows


def predictions(rows):
    pred = [HEAD]

    def line(*f):
        pred.append("\t".join(str(x) for x in f) + "\n")

    for name, sset, knobs, tool, args, role, m in rows:
        g = name.split("-")[0][:-1]
        if role == "W":
            line(name, "sa", "0x%08x" % m, "H-REF", sset,
                 "E1106/E521 [HW]: iaddu32 writes (r1 & 0xffff) + r2 into sa0, read back in the "
                 "same job (E496 job 7); this program's own constants")
            line(name, "top", "0x%08x" % K1, "H-REF", sset, "this program's own o0 constant")
        elif role == "K":
            line(name, "sa", "0x%08x" % K3, "H-REF", sset, "this program's own stored constant")
            line(name, "top", "0x%08x" % K3, "H-REF", sset, "this program's own o0 constant")
        elif role == "R":
            job_between = g in ("k3", "fl", "tr")
            line(name, "cat", "M", "H-PERSIST", sset,
                 "sa0 keeps M across every job, reset and idle of the stage")
            line(name, "cat", "PREV" if job_between else "M", "H-ONEJOB", sset,
                 "E484's sa rule: read by the next job only; a job between replaces it with that "
                 "job's colour (fit: E1139's post hoc reading, 20 of 20)")
            line(name, "cat", "PREV", "H-COLOUR", sset,
                 "sa0 never persists: the reader reads the colour the job before it output "
                 "(E496's job 8 read as the colour rule)")
            if g == "rs":
                line(name, "cat", "!M", "H-RESET", sset, "the debugfs reset replaces sa0")
            if g in IDLE:
                line(name, "cat", "!M", "H-IDLE", sset, "sa0 is lost over the idle time")
        elif role == "P":
            line(name, "cat", "PREV", "H-PREV", sset,
                 "pa0 reads the colour the job before it output (E496 [infer], E484; fit: E1139's "
                 "post hoc reading, 8 of 8)")
            line(name, "cat", "TRI", "H-FIXED", sset,
                 "pa0 reads the 0xff00ff00 and 0xff203040 mixture whatever ran before it")
            if g == "pk3r":
                line(name, "cat", "!PREV", "H-RESETP", sset,
                     "the debugfs reset replaces what pa0 reads")
    return pred


HEADER = """#stage s
#limit 0
# r34-sa0b s, the corrected rerun of r34-sa0 (E1139: its xor readers' pixels came in pairs; readers now output the value
# read, E496's form) (Q136, rank-round34.md 3.6; safe: no expectfault, #limit 0, no kreg, no dbg knob): how long does an sa0
# write last across jobs, and is pa0's 0xff00ff00/0xff203040 mixture the colour the job before left? Every probe is a
# plain t30 fill. W (control): iaddu32 writes a per-row marker M to sa0 in every instance, reads it back (dword 0 = M)
# and outputs K1. R (held out): reads sa0, o0 = sa0. K (control): a job writing no sa/pa, o0 = K3. P: reads pa0,
# o0 = pa0. X: t10 fill / tri (the health pair's argv). Groups nr (noreset), rs (reset), i10/i60/i120 (noreset
# idle), k3, fl, tr (a job between, noreset), ptr (fit), pk3, pfl, pk3r (clause b); second
# replicate reversed. Frozen: H-PERSIST, H-ONEJOB, H-COLOUR (every R), H-RESET (rs), H-IDLE (idle); H-PREV against
# H-FIXED (every P), H-RESETP (pk3r). Stop: any fault or hang (4); a control without its reading (25); a probe
# without its o0 line, a W or K without its dword 0, a fill without `fill: ok`, a tri not drawn exactly (24, end)."""


def build():
    files = {}
    rows = all_rows()
    for name, sset, knobs, tool, args, role, m in rows:
        if role == "W":
            files["bins/w-%08x.bin" % m] = asm(program("w", m))
    for k in ("r", "p", "k"):
        files[f"bins/{k}.bin"] = asm(program(k))
    tab = [HEADER] + [f"{n}|{s}|safe|{k}|{t}|{a}" for n, s, k, t, a, _, _ in rows]
    files[f"tables/{STAGE}.txt"] = ("\n".join(tab) + "\n").encode()
    files[f"predictions/{STAGE}.tsv"] = "".join(predictions(rows)).encode()
    # the frozen constants the scorer, the mock and the tests read (one place)
    tri, fill = tri_colours(), fill_colour()
    o0, before = e496_first()
    fit = posthoc_fit()
    consts = (f"K1=0x{K1:08x}\nK2=0x{K2:08x}\nK3=0x{K3:08x}\nK4=0x{K4:08x}\n"
              f"TRI=0x{tri[0]:08x},0x{tri[1]:08x}\nFILL=0x{fill:08x}\n"
              f"E496_FIRST={o0}\nE496_BEFORE={before}\nE1139_POSTHOC={fit}\n"
              f"T10_SOURCE={hashlib.sha256(pins.tool_source(HEALTH_TOOL)).hexdigest()}\n")
    files["gen/constants.txt"] = consts.encode()
    files["mock/kept/fill.txt"] = pins.blob(KEPT_FILL)
    files["mock/kept/tri.txt"] = pins.blob(KEPT_TRI)
    return files


def main(argv):
    files = build()
    if "--check" in argv:
        bad = [p for p, b in files.items()
               if not os.path.exists(os.path.join(KP, p)) or open(os.path.join(KP, p), "rb").read() != b]
        for d in ("bins", "tables", "predictions"):
            full = os.path.join(KP, d)
            bad += [f"{d}/{n}" for n in sorted(os.listdir(full)) if f"{d}/{n}" not in files] \
                if os.path.isdir(full) else []
        for p in bad:
            print(f"stale: {p}")
        return 1 if bad else 0
    for d in ("tables", "predictions"):
        for n in os.listdir(os.path.join(KP, d)):
            if f"{d}/{n}" not in files:
                os.unlink(os.path.join(KP, d, n))
    for p, b in files.items():
        f = os.path.join(KP, p)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "wb") as fh:
            fh.write(b)
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
