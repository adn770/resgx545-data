#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r35-sa's generator (closing29/plan/rank-round35.md sections 1, 3.2 and 3.4: Q129 and
Q193). Writes tables/a.txt, tables/t.txt, predictions/a.tsv, predictions/t.tsv, the programs
bins/NAME.bin and gen/constants.txt; every input is read at the commits session.toml's [freeze]
names or at the bound tool sources' own commits (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Every probe is a plain t30 `probe --pixels` fill (64 x 32, 2048 instances, our program as the
pixel task; t30 prints every pixel, row by row), except c1 (`--coords`: a copy whose source texel
(x, y) is (y << 16) | x, so pa0 holds the pixel's coordinates, E1106/E513).

Stage a (Q129): "why do 12 pixels (4 each of three values) of every fill that writes sa1, sa5 and
sa7 show those sa values as their output, and how long does an sa written by one job stay
readable (one job, or until the next job that writes it)".
  W_n   every instance `iaddu32.testtaz.chan0 sa_n, p0, r1, r2` (r1 = 1, r2 = M - 1: E1106's
        zero-extended sum = M), `mov r3, sa_n`, dword 0 = r3 (the in-job readback), o0 = K1
        (E1139's writer on sa_n); W_157 the same for sa1, sa5 and sa7 (dwords 0, 1, 2).
  X_1   W_1's body with its own marker and o0 = K2 (a gap job writing sa1 only).
  R_5   `mov r10, sa5`, dword 0 = r10, o0 = r10 (E1140's reader form, no key: D3).
  K     dword 0 = o0 = K3 (writes no sa, no pa, no r20).
  C     `mov r10, pa0`, dword 0 = r10, o0 = r10 (under --coords: o0 = the pixel's coordinates).
Stage t (Q193): "what holds a temporary a task did not write: which earlier job's value does it
read, per instance, and what clears it".
  T     every instance r20 = M (0x7e00RR14), dword 0 = r20, o0 = K1.
  T8    `--temps 8`: r0-r5 = 0x7e08RR0k, r7 the scratch base, dword 0 = r0, o0 = r6 = K1.
  U     `mov r10, r20` (r20 not written), dword 0 = r10, o0 = r10.
  K     as in stage a; X: t10 `tri` (the health pair's argv).
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

PROBE_TOOL = "t30"
HEALTH_TOOL = "t10"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
K1 = 0xC0DE0A01          # W's and T's colour
K2 = 0xC0DE0A02          # X_1's colour (the gap job of Q129's body)
K3 = 0xC0DE0A03          # K's colour (a job that writes no sa, pa or r20)
NPIX = 2048
# the health pair's kept texts on this module and tools (r34-q010, E1134): the mock's t10 answers
Q010_C = "data:render/closing-r34-q010/out/20261116-231015/c"
KEPT_FILL = Q010_C + "/begin.fill1.txt.gz"
KEPT_TRI = Q010_C + "/begin.health1.txt.gz"
# the sa writers of stage a: n with two replicates (the plan's f and h rows) and with one
TWO_REP = (2, 3, 5, 7, 15)
ONE_REP = (4, 6, 8, 9, 10, 11, 12, 13, 14)
FIT_N = (0, 1)
U157 = (1, 5, 7)
# Q129's frozen hypotheses (D2: tests/test_score.py produces each name)
A_POS = ("H-FIXED4", "H-SHIFT")
A_ALL = ("H-FIXED4", "H-SHIFT", "H-VAR", "H-UNION", "H-FOUR", "H-OTHERN", "H-ONEJOB",
         "H-UNTILWRITE")
T_ALL = ("H-LASTWRITER", "H-LASTJOB", "H-SPLIT", "H-TRI1536", "H-RESETCLR")


def a_marker(rr, n):
    return 0x5A350000 | rr << 8 | n


def t_marker(rr):
    return 0x7E000014 | rr << 8


def t8_markers(rr):
    return [0x7E080000 | rr << 8 | k for k in range(6)]


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


def t30_facts():
    """What the rows rely on in t30's own source: --pixels prints every pixel row by row,
    --coords' texel (x, y) is (y << 16) | x, every probe opens its own VM and context, and the
    probe's PDS secondary has 16 attributes (sa0-sa15)."""
    src = pins.tool_source(PROBE_TOOL).decode()
    return {
        "pixels": bool(re.search(r'printf\("probe %s: row %u:", name, y\);', src)),
        "coords": bool(re.search(r"coord_texel\(uint32_t x, uint32_t y\)\n\{\n\treturn y << 16 \| x;",
                                 src)),
        "context": bool(re.search(r"sgxfive_vm_create\(t->dev, &s->vm\);\n\tif \(!ret\)\n\t\tret = "
                                  r"sgxfive_ctx_create\(s->vm, &s->ctx\);", src)),
        "attrs16": "#define PROBE_PDS_ATTRS\t16" in src,
    }


PRE = ["phas #0, #0, pixel, end, parallel", "mov.skipinv r29, #0x5CAF0000"]
POST = ["idf drc0, bif", "wdf drc0"]


def program(kind, ms=None, n=None):
    """The listing of one program (kind w: ms = {n: M}; x: ms = {1: M}; t: ms = M; t8: ms = the
    six markers; r: n the sa read; k, c, u)."""
    lines = [f"; r35-sa {kind} (gen/make.py)"]
    if kind == "t8":
        lines += ["phas #0, #0, pixel, end, parallel", "mov.skipinv r7, #0x5CAF0000"]
        lines += ["mov.skipinv r%d, #0x%08X" % (k, m) for k, m in enumerate(ms)]
        lines += ["mov.skipinv r6, #0x%08X" % K1, "stad [r7,+#0], r0"] + POST
        lines += ["mov.skipinv.end o0, r6"]
        return "\n".join(lines) + "\n"
    lines += PRE
    if kind in ("w", "x"):
        lines += ["mov.skipinv r1, #0x00000001"]
        for k, (sa, m) in enumerate(sorted(ms.items())):
            lines += ["mov.skipinv r2, #0x%08X" % (m - 1),
                      "iaddu32.testtaz.chan0 sa%d, p0, r1, r2" % sa, "mov r3, sa%d" % sa,
                      "stad [r29,+#%d], r3" % k]
        lines += ["mov.skipinv r10, #0x%08X" % (K1 if kind == "w" else K2)]
    elif kind == "r":
        lines += ["mov r10, sa%d" % n, "stad [r29,+#0], r10"]
    elif kind == "c":
        lines += ["mov r10, pa0", "stad [r29,+#0], r10"]
    elif kind == "u":
        lines += ["mov r10, r20", "stad [r29,+#0], r10"]
    elif kind == "t":
        lines += ["mov.skipinv r20, #0x%08X" % ms, "stad [r29,+#0], r20",
                  "mov.skipinv r10, #0x%08X" % K1]
    elif kind == "k":
        lines += ["mov.skipinv r10, #0x%08X" % K3, "stad [r29,+#0], r10"]
    lines += POST + ["mov.skipinv.end o0, r10"]
    return "\n".join(lines) + "\n"


def asm(text):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "x.bin"
        P._assemble(text, f, "usse")
        return f.read_bytes()


def probe_args(binname, temps=32, coords=False):
    return (f"probe --temps {temps}" + (" --coords" if coords else "")
            + f' --pixels "$S/bins/{binname}.bin"')


# a row: dict(name, set, knobs, tool, args, role, ms (markers), n, bin, prog)
def row(name, sset, knobs, role, binname=None, prog=None, ms=None, n=None, tool=PROBE_TOOL,
        args=None, temps=32, coords=False):
    return dict(name=name, set=sset, knobs=knobs, tool=tool, role=role, ms=ms, n=n, bin=binname,
                prog=prog, args=args or probe_args(binname, temps, coords))


class Rows:
    def __init__(self):
        self.rr = 0

    def next(self):
        self.rr += 1
        return self.rr


def a_rows():
    """Stage a's rows in run order (replicate a, then b with the groups reversed)."""
    c = Rows()
    rk = "reads:sa,top"

    def w(name, sset, knobs, ns):
        rr = c.next()
        ms = {n: a_marker(rr, n) for n in ns}
        base = "w157-%08x" % a_marker(rr, 0) if len(ns) > 1 else "w-%08x" % ms[ns[0]]
        return row(name, sset, knobs, "W", base, program("w", ms), ms=ms,
                   n=ns[0] if len(ns) == 1 else 157)

    def x1(name):
        rr = c.next()
        ms = {1: a_marker(rr, 1)}
        return row(name, "control", "noreset " + rk, "X", "x-%08x" % ms[1], program("x", ms),
                   ms=ms, n=1)

    def r5(name, sset, knobs):
        return row(name, sset, knobs, "R", "r5", program("r", n=5), n=5)

    def k(name, sset, knobs):
        return row(name, sset, knobs, "K", "k", program("k"))

    def grp(g, rep):
        t = g + rep
        if g == "c0":
            return [k(f"{t}-k", "control", "reads:sa,top,rows")]
        if g == "c1":
            return [row(f"{t}-c", "control", "reads:rows", "C", "c", program("c"), coords=True)]
        if g == "c2":
            return [w(f"{t}-w", "control", rk, [5]),
                    r5(f"{t}-r", "control", "noreset " + rk)]
        if g == "p":
            return [w(f"{t}-w", "control", rk, [5]), x1(f"{t}-x"),
                    r5(f"{t}-r", "heldout", "noreset")]
        if g == "q":
            return [w(f"{t}-w", "control", rk, [5]), k(f"{t}-x", "control", "noreset " + rk),
                    r5(f"{t}-r", "fit", "noreset")]
        n = int(g[1:])
        ns = list(U157) if n == 157 else [n]
        return [w(f"{t}-w", "fit" if g[0] == "f" else "heldout", "-", ns)]

    hs = [f"h{n}" for n in sorted(TWO_REP + ONE_REP)] + ["h157"]
    order_a = ["c0", "c1", "f0", "f1", "c2"] + hs + ["p", "q"]
    two = [g for g in order_a if g in ("f0", "f1", "c2", "p", "h157")
           or (g[0] == "h" and int(g[1:]) in TWO_REP)]
    order_b = list(reversed(two))
    rows = []
    for rep, order in (("a", order_a), ("b", order_b)):
        for g in order:
            rows += grp(g, rep)
    return rows


def t_rows():
    """Stage t's rows in run order."""
    c = Rows()
    rk = "reads:sa,top"

    def tw(name):
        m = t_marker(c.next())
        return row(name, "control", rk, "T", "t-%08x" % m, program("t", m), ms={20: m})

    def u(name, sset, knobs):
        return row(name, sset, knobs, "U", "u", program("u"))

    def grp(g, rep):
        t = g + rep
        out = [tw(f"{t}-t")]
        if g == "c":
            return out + [u(f"{t}-u", "control", "noreset reads:sa,top")]
        if g == "t1":
            out.append(row(f"{t}-x", "control", "noreset reads:sa,top", "K", "k", program("k")))
        elif g == "t2":
            out.append(row(f"{t}-x", "between", "noreset", "TRI", tool=HEALTH_TOOL, args="tri"))
        elif g == "t4":
            ms = t8_markers(c.next())
            out.append(row(f"{t}-x", "control", "noreset reads:sa,top", "T8", "t8-%08x" % ms[0],
                           program("t8", ms), ms=dict(enumerate(ms)), temps=8))
        return out + [u(f"{t}-u", "heldout", "-" if g == "t3" else "noreset")]

    order_a = ["c", "t1", "t2", "t3", "t4"]
    order_b = ["t3", "t2", "t1", "c"]
    rows = []
    for rep, order in (("a", order_a), ("b", order_b)):
        for g in order:
            rows += grp(g, rep)
    return rows


def group_of(name):
    return name.split("-")[0][:-1]


def predictions_a(rows):
    pred = [HEAD]

    def line(*f):
        pred.append("\t".join(str(x) for x in f) + "\n")

    own = "this program's own constant"
    for r in rows:
        name, sset, role, ms = r["name"], r["set"], r["role"], r["ms"]
        g = group_of(name)
        if role == "K":
            line(name, "sa", "0x%08x" % K3, "H-REF", sset, own + " (dword 0)")
            line(name, "top", "0x%08x" % K3, "H-REF", sset, own + " (o0)")
            if g == "c0":
                line(name, "rows", "32", "H-REF", sset,
                     "t30's --pixels: 32 rows of 64 pixels (D1: the position decode on K3)")
        elif role == "C":
            line(name, "rows", "32", "H-REF", sset,
                 "t30's --pixels: 32 rows of 64 pixels (D1: the decode on (y << 16) | x, t30's "
                 "coord_texel, scored per pixel by score.py)")
        elif role == "X":
            line(name, "sa", "0x%08x" % ms[1], "H-REF", sset,
                 "E1106 [HW]: iaddu32 writes (r1 & 0xffff) + r2, read back in the job; " + own)
            line(name, "top", "0x%08x" % K2, "H-REF", sset, own + " (o0)")
        elif role == "R" and sset == "control":
            m = rows[rows.index(r) - 1]["ms"][5]
            line(name, "sa", "0x%08x" % m, "H-REF", sset,
                 "D1: E1140's reader form on sa5 reads the writer's marker right after it")
            line(name, "top", "0x%08x" % m, "H-REF", sset, "the same, as o0 (E484: 2048 of 2048)")
        elif role == "R":
            line(name, "cat", "PREV", "H-ONEJOB", sset,
                 "E1140's rule for sa0 on sa5: any job between replaces it with that job's "
                 "output, also one that writes another sa")
            line(name, "cat", "M" if g == "p" else "PREV", "H-UNTILWRITE", sset,
                 "a job between that writes an sa (X_1: sa1) leaves sa5 as written; a job "
                 "writing no sa replaces it with its output (E484, the fit q)")
        elif role == "W" and sset == "control":
            line(name, "sa", "0x%08x" % ms[5], "H-REF", sset,
                 "E1106 [HW]: iaddu32 writes (r1 & 0xffff) + r2, read back in the job; " + own)
            line(name, "top", "0x%08x" % K1, "H-REF", sset, own + " (o0)")
        elif role == "W":
            n = r["n"]
            k = len(ms)
            line(name, "count", str(4 * k), "H-FOUR", sset,
                 "E484/E1139: exactly 4 pixels per sa written show its marker, the rest K1")
            line(name, "count", "!%d" % (4 * k), "H-OTHERN", sset,
                 "another number of odd pixels than 4 per sa written")
            if n == 157:
                line(name, "pos", "W1|W5|W7", "H-UNION", sset,
                     "E484's 12 = the union of W_1's, W_5's and W_7's positions (same replicate)")
            else:
                line(name, "pos", "S0", "H-FIXED4", sset,
                     "the same 4 positions for every n, both replicates (S0: f0a's)")
                line(name, "pos", "S0+%dd" % n, "H-SHIFT", sset,
                     "sa0's positions (f0a) shifted by n d pixel indices, d fitted on f1a")
            if (n in FIT_N + TWO_REP or n == 157) and name.split("-")[0].endswith("b"):
                line(name, "rep", "!same", "H-VAR", sset,
                     "the positions differ between the two replicates of one n")
    return pred


def predictions_t(rows):
    pred = [HEAD]

    def line(*f):
        pred.append("\t".join(str(x) for x in f) + "\n")

    own = "this program's own constant"
    first_m = None
    for r in rows:
        name, sset, role, ms = r["name"], r["set"], r["role"], r["ms"]
        g = group_of(name)
        if role == "T":
            first_m = ms[20]
            line(name, "sa", "0x%08x" % ms[20], "H-REF", sset, own + " (r20 stored, dword 0)")
            line(name, "top", "0x%08x" % K1, "H-REF", sset, own + " (o0)")
        elif role == "K":
            line(name, "sa", "0x%08x" % K3, "H-REF", sset, own + " (dword 0)")
            line(name, "top", "0x%08x" % K3, "H-REF", sset, own + " (o0)")
        elif role == "T8":
            line(name, "sa", "0x%08x" % ms[0], "H-REF", sset, own + " (r0 stored, dword 0)")
            line(name, "top", "0x%08x" % K1, "H-REF", sset, own + " (o0)")
        elif role == "U" and sset == "control":
            line(name, "sa", "0x%08x" % first_m, "H-REF", sset,
                 "D1: the unwritten r20 read right after its writer (E593's first order, E484's "
                 "r40: 2048 of 2048)")
            line(name, "top", "0x%08x" % first_m, "H-REF", sset, "the same, as o0")
        elif role == "U":
            between = g in ("t1", "t2", "t4")
            line(name, "cat", "M", "H-LASTWRITER", sset,
                 "every pixel reads the last job that wrote r20 (E484's r40 after a gap job)")
            line(name, "cat", "LASTJOB" if between else "M", "H-LASTJOB", sset,
                 "every pixel reads what the last job left, whatever it wrote: no r20 marker "
                 "after a job between")
            line(name, "cat", "SPLIT" if between else "M", "H-SPLIT", sset,
                 "pixels split between an r20 marker and other values by instance slots after "
                 "a job between (E593's 1536/512)")
            if g == "t2":
                line(name, "cat", "TRI1536", "H-TRI1536", sset,
                     "the triangle overwrites the slots of its instances: two values, 1536 and "
                     "512 pixels (the E496/E1140 counts)")
            if g == "t3":
                line(name, "cat", "!M", "H-RESETCLR", sset,
                     "the debugfs reset replaces r20 (E593 [infer]: it does not)")
    return pred


HEADER_A = """#stage a
#limit 0
# r35-sa a (Q129, rank-round35.md 3.2; safe: no expectfault, #limit 0, no kreg, no dbg knob): which pixels of a fill
# that writes sa_n show the marker, and does sa5 survive a job between that writes another sa? Every probe is a t30
# fill with --pixels (c1: --coords). c0 (K) and c1 (o0 = pa0 = (y << 16) | x) are the position decode's controls (D1);
# c2 (W_5, R_5) the reader form's on sa5. f (fit: W_0, W_1) and h (held out: W_2..W_15, W_157 = sa1, sa5 and sa7)
# write a per-row marker with iaddu32 and output K1. p (W_5, X_1 writing sa1, R_5) is clause (b); q (W_5, K, R_5) is
# E484's form (fit). Second replicate: the two-replicate groups reversed. Frozen: H-FOUR/H-OTHERN, H-FIXED4/H-SHIFT,
# H-VAR, H-UNION (positions), H-ONEJOB/H-UNTILWRITE (p, q). Stop: any fault or hang (4); a control without its
# reading (25); a probe without its o0 line, its 32 pixel rows or (a writer, K, X) its dword 0 (24)."""

HEADER_T = """#stage t
#limit 0
# r35-sa t (Q193, rank-round35.md 3.4; safe: no expectfault, #limit 0, no kreg, no dbg knob): which earlier job's
# value does an unwritten r20 read, per pixel? T writes a per-row marker to r20 and outputs K1; U reads r20 without
# writing it (o0 = dword 0 = r20). c (T, U) is the reader's control (D1); t1 (K between), t2 (the t10 triangle
# between), t3 (a debugfs reset between), t4 (a --temps 8 writer of r0-r5 between); second replicate reversed, t4
# once. Frozen: H-LASTWRITER, H-LASTJOB, H-SPLIT (every U), H-TRI1536 (t2), H-RESETCLR (t3). Stop: any fault or hang
# (4); a control without its reading (25); a probe without its o0 line, its 32 pixel rows or (T, T8, K) its dword 0,
# the triangle not drawn exactly (24, end)."""


def table(header, rows):
    return "\n".join([header] + [f"{r['name']}|{r['set']}|safe|{r['knobs']}|{r['tool']}|{r['args']}"
                                 for r in rows]) + "\n"


def build():
    files = {}
    ra, rt = a_rows(), t_rows()
    for r in ra + rt:
        if r["prog"] is not None:
            b = asm(r["prog"])
            p = f"bins/{r['bin']}.bin"
            assert files.get(p, b) == b, p
            files[p] = b
    files["tables/a.txt"] = table(HEADER_A, ra).encode()
    files["tables/t.txt"] = table(HEADER_T, rt).encode()
    files["predictions/a.tsv"] = "".join(predictions_a(ra)).encode()
    files["predictions/t.tsv"] = "".join(predictions_t(rt)).encode()
    tri, fill = tri_colours(), fill_colour()
    facts = t30_facts()
    consts = (f"K1=0x{K1:08x}\nK2=0x{K2:08x}\nK3=0x{K3:08x}\n"
              f"TRI=0x{tri[0]:08x},0x{tri[1]:08x}\nFILL=0x{fill:08x}\n"
              + "".join(f"T30_{k.upper()}={'yes' if v else 'no'}\n" for k, v in facts.items())
              + f"T10_SOURCE={hashlib.sha256(pins.tool_source(HEALTH_TOOL)).hexdigest()}\n"
              f"T30_SOURCE={hashlib.sha256(pins.tool_source(PROBE_TOOL)).hexdigest()}\n")
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
    for d in ("tables", "predictions", "bins"):
        full = os.path.join(KP, d)
        for n in os.listdir(full) if os.path.isdir(full) else []:
            if f"{d}/{n}" not in files:
                os.unlink(os.path.join(full, n))
    for p, b in files.items():
        f = os.path.join(KP, p)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "wb") as fh:
            fh.write(b)
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
