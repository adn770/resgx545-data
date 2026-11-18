# SPDX-License-Identifier: MIT
"""mock/world.py: r35-sa's argv-driven fake laptop for kit/session.py mock (and tests/test_score.py,
which builds attempts from it). answer() sees the tool's name, the argv, the world's tokens and the
fake laptop's state (its reset count and this world's own state files in FAKE_DIR), never a case
name; it returns dict(rc, out, err, kmsg, latch) or a refusal (usage, rc 2). As strict as the tools
on this session's rows: t30 `probe [--temps N] [--coords] [--pixels] [--scratch-show N] FILE` with
FILE one of bins/ (--coords only with c.bin), and t10's bare `fill` and `tri` (the health pair and
the X rows alike, so they count as jobs here too).

The program is known from FILE's base name only (gen/make.py's names): `w-M` writes marker M to
sa(M & 0xff) and outputs K1, `w157-B` writes B|1, B|5, B|7 to sa1, sa5, sa7, `x-M` writes M to sa1
and outputs K2, `r5` reads sa5, `k` outputs K3, `c` outputs pa0 (with --coords (y << 16) | x),
`t-M` writes M to r20 and outputs K1, `t8-B` writes r0-r5 and outputs K1, `u` reads r20.

Tokens (a world is a comma separated set; the default of each axis is the model's):
  positions  shift (model: sa_n's 4 odd pixels are S0 + 2 n), fixed (S0 for every n), var (S0 + 2 n,
             moved by the writer's count), othern (a fifth odd pixel per sa)
  sa5        onejob (model: read by the next job only; a job between replaces it with its output),
             untilwrite (kept across a job that writes another sa)
  r20        lastwriter (model: the last r20 written, every pixel), lastjob (the last job's
             output after a job between), split (512 pixels of the marker, 1536 of the last
             job's most frequent output, after a job between), tri1536 (lastwriter, but after
             the triangle 1536 of its first colour and 512 of the marker), resetclr (0 after a
             debugfs reset)
  badcoords  c.bin under --coords outputs (x << 16) | y (the decode control fails)
  wbad       every W's in-job readback reads 0 (its row is not read)
Stops (EXPECT): noread (the third reader of stage t prints no o0 line: t 24, the session ends),
norows (the first W prints 31 pixel rows: a 24, t runs), fault (the first writer faults: a 4, the
session stops), hang (the first U hangs: t 4).
"""
import os
import re

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECT = {
    "model": (0, {"a": 0, "t": 0}),
    "fixed": (0, {"a": 0, "t": 0}),
    "var": (0, {"a": 0, "t": 0}),
    "othern": (0, {"a": 0, "t": 0}),
    "untilwrite": (0, {"a": 0, "t": 0}),
    "lastjob": (0, {"a": 0, "t": 0}),
    "split": (0, {"a": 0, "t": 0}),
    "tri1536": (0, {"a": 0, "t": 0}),
    "resetclr": (0, {"a": 0, "t": 0}),
    "badcoords": (0, {"a": 0, "t": 0}),
    "wbad": (0, {"a": 0, "t": 0}),
    "noread": (24, {"a": 0, "t": 24}),
    "norows": (0, {"a": 24, "t": 0}),
    "fault": (4, {"a": 4}),
    "hang": (4, {"a": 0, "t": 4}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
NPIX, W, H = 2048, 64, 32
S0 = (5 * 64 + 9, 5 * 64 + 10, 6 * 64 + 9, 6 * 64 + 10)
D = 2


def constants():
    out = {}
    for ln in open(os.path.join(KP, "gen", "constants.txt")).read().splitlines():
        k, _, v = ln.partition("=")
        out[k] = v
    return out


C = constants()
K1, K2, K3, FILL = (int(C[k], 16) for k in ("K1", "K2", "K3", "FILL"))
TRI = [int(v, 16) for v in C["TRI"].split(",")]


def kept(name):
    return open(os.path.join(KP, "mock", "kept", name)).read()


def get(name, default=""):
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, name) if d else None
    return open(p).read().strip() if p and os.path.exists(p) else default


def put(name, value):
    d = os.environ.get("FAKE_DIR")
    if d:
        with open(os.path.join(d, name), "w") as f:
            f.write(str(value))


def resets():
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, "writes") if d else None
    return sum(1 for ln in open(p) if ln.startswith("reset")) if p and os.path.exists(p) else 0


def count(name):
    n = int(get(name, "0")) + 1
    put(name, n)
    return n


def enc(px):
    return " ".join("%08x" % v for v in px)


def dec(s):
    return [int(v, 16) for v in s.split()] if s else [0] * NPIX


def tri_px():
    return [TRI[0]] * 1536 + [TRI[1]] * 512


def report(name, px, dwords, rows=H):
    """t30's probe_report: o0 (the value, or the four most frequent), every pixel row, the
    scratch dwords changed."""
    order, cnt = [], {}
    for v in px:
        if v not in cnt:
            order.append(v)
            cnt[v] = 0
        cnt[v] += 1
    vals = sorted(order, key=lambda v: -cnt[v])        # stable: first seen first on ties
    if len(vals) == 1:
        lines = ["probe %s: o0 0x%08x (%d of %d)" % (name, vals[0], NPIX, NPIX)]
    else:
        s = " ".join("0x%08x x%d" % (v, cnt[v]) for v in vals[:4])
        other = sum(cnt[v] for v in vals[4:])
        lines = ["probe %s: o0 mixed %s%s" % (name, s, " other x%d" % other if other else "")]
    for y in range(rows):
        lines.append("probe %s: row %d: %s" % (name, y, " ".join("%08x" % v for v in px[y * W:(y + 1) * W])))
    for k, v in dwords:
        lines.append("probe %s: scratch +0x%03x 0x%08x" % (name, 4 * k, v))
    return lines


def positions(n, world):
    d = 0 if "fixed" in world else D
    out = [(i + n * d) % NPIX for i in S0]
    if "var" in world:                  # moved by the writer's count: no two writers alike
        out = [(i + int(get("r35s_wpar", "0"))) % NPIX for i in out]
    if "othern" in world:
        out.append((S0[0] + n * d + 1000) % NPIX)
    return out


def sa_state():
    """{sa n: marker} the last job wrote and how many jobs ran since every write since W_5."""
    s = get("r35s_sa", "")
    return {int(k): int(v, 16) for k, v in (w.split(":") for w in s.split())} if s else {}


def job_done(px, wrote_sa=None, wrote_r20=None):
    """The state after a job: its output, the sa it wrote, whether every job since sa5's write
    wrote an sa, the r20 it wrote (and the reset count then), the jobs since."""
    put("r35s_last", enc(px))
    put("r35s_sa", " ".join("%d:%08x" % kv for kv in (wrote_sa or {}).items()))
    if wrote_sa and 5 in wrote_sa:
        put("r35s_sa5", "%08x 1" % wrote_sa[5])
    elif get("r35s_sa5"):
        m, keep = get("r35s_sa5").split()
        put("r35s_sa5", "%s %d" % (m, int(keep) and bool(wrote_sa)))
    if wrote_r20 is not None:
        put("r35s_r20", "%08x 0 %d" % (wrote_r20, resets()))
    elif get("r35s_r20"):
        m, since, at = get("r35s_r20").split()
        put("r35s_r20", "%s %d %s" % (m, int(since) + 1, at))


def probe(argv, world, lastkind=""):
    i, path, temps, coords, pix = 1, None, 32, False, False
    while i < len(argv):
        a = argv[i]
        if a in ("--temps", "--scratch-show") and i + 1 < len(argv) and argv[i + 1].isdigit():
            lim = (1, 128) if a == "--temps" else (1, 64)
            if not lim[0] <= int(argv[i + 1]) <= lim[1]:
                return USAGE
            temps = int(argv[i + 1]) if a == "--temps" else temps
            i += 2
        elif a == "--pixels":
            pix = True
            i += 1
        elif a == "--coords":
            coords = True
            i += 1
        elif a.startswith("--") or path is not None:
            return USAGE
        else:
            path = a
            i += 1
    if path is None:
        return USAGE
    if not os.path.isfile(path):
        return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % path)
    size = os.path.getsize(path)
    if not size or size % 8 or size > 256 * 8:
        return dict(rc=2, err="sgxfive-test: %s: not 1 to 256 USSE words\n" % path)
    name = os.path.basename(path).split(".")[0]
    m = re.fullmatch(r"(w|w157|x|t|t8)-([0-9a-f]{8})", name)
    if not m and name not in ("r5", "k", "c", "u"):
        return USAGE
    if coords != (name == "c") or (temps != 32) != (name.startswith("t8-")) or not pix:
        return USAGE                    # no row of this session runs another form
    head = ["programs asm", "probe %s: scratch at 0x3e003000 (64 KiB)" % name,
            "probe %s: job time: 640 us" % name]
    last = dec(get("r35s_last", ""))

    def done(px, dwords, rows=H, **kw):
        job_done(px, **kw)
        return dict(out="\n".join(head + report(name, px, dwords, rows)) + "\n")

    if m and m.group(1) in ("w", "w157", "x"):
        kind, base = m.group(1), int(m.group(2), 16)
        nw = count("r35s_w")
        if "fault" in world and nw == 1:
            return dict(rc=3, out="\n".join(head + ["probe %s: failed: job faulted, context lost "
                                                    "(Input/output error)" % name]) + "\n",
                        kmsg=["sgxfive: BIF fault 0x80020 at 0x3e003001 (PD 0x5736000) stalls "
                              "job 7, recovering"], latch=(0x1000, 0x3E003001))
        ms = {n: base | n for n in (1, 5, 7)} if kind == "w157" else {base & 0xFF: base}
        if kind == "x":
            ms = {1: base}
        px = [K2 if kind == "x" else K1] * NPIX
        for n in sorted(ms):
            for p in positions(n, world):
                px[p] = ms[n]
        put("r35s_wpar", nw)
        dw = [(k, 0 if "wbad" in world else ms[n]) for k, n in enumerate(sorted(ms))]
        return done(px, dw, rows=31 if "norows" in world and nw == 1 else H, wrote_sa=ms)
    if name == "k":
        return done([K3] * NPIX, [(0, K3)])
    if name == "c":
        px = [((i % W) << 16 | i // W) if "badcoords" in world else ((i // W) << 16 | i % W)
              for i in range(NPIX)]
        return done(px, [(0, px[-1])])
    if name == "r5":
        s5 = get("r35s_sa5", "")
        prev = sa_state()
        if s5 and (5 in prev or ("untilwrite" in world and s5.split()[1] == "1")):
            px = [int(s5.split()[0], 16)] * NPIX
        else:
            px = last
        return done(px, [(0, px[-1])])
    if m and m.group(1) == "t":
        mk = int(m.group(2), 16)
        return done([K1] * NPIX, [(0, mk)], wrote_r20=mk)
    if m and m.group(1) == "t8":
        base = int(m.group(2), 16)
        return done([K1] * NPIX, [(0, base)])
    # u: reads r20
    nu = count("r35s_u")
    if "hang" in world and nu == 1:
        return dict(rc=3, out="\n".join(head + ["probe u: failed: job hung, context lost "
                                                "(Connection timed out)"]) + "\n",
                    kmsg=["sgxfive: job 12 hung, recovering"])
    r20 = get("r35s_r20", "")
    mk, since, at = (int(r20.split()[0], 16), int(r20.split()[1]), int(r20.split()[2])) \
        if r20 else (0, 99, -1)
    if "resetclr" in world and resets() != at:
        px = [0] * NPIX
    elif since == 0:
        px = [mk] * NPIX
    elif "lastjob" in world:
        px = last
    elif "split" in world:
        top = max(set(last), key=last.count)
        px = [top] * 1536 + [mk] * 512
    elif "tri1536" in world and lastkind == "tri":
        px = [TRI[0]] * 1536 + [mk] * 512
    else:
        px = [mk] * NPIX
    out = done(px, [(0, px[-1])])
    if "noread" in world and nu == 3:
        out["out"] = "\n".join(ln for ln in out["out"].splitlines() if ": o0 " not in ln) + "\n"
    return out


def health(argv, world):
    job = argv[0]
    if job == "tri":
        job_done(tri_px())
        put("r35s_lastkind", "tri")
        return dict(out=kept("tri.txt"))
    job_done([FILL] * NPIX)
    put("r35s_lastkind", "fill")
    return dict(out=kept("fill.txt"))


def answer(tool, argv, world):
    if tool == "t10" and argv in (["fill"], ["tri"]):
        return health(argv, world)
    if tool == "t30" and argv and argv[0] == "probe":
        lk = get("r35s_lastkind", "")
        put("r35s_lastkind", "probe")
        return probe(argv, world, lk)
    return USAGE
