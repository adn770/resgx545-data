#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r21-zls's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 fa073da2ef13, pinned in FROZEN.commits).
The text readers, the window and the library's triangle are r20-zls's (data
render/closing-r20-zls/score/score.py), unchanged.

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of zc passed (zl, zw, zz)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Controls of a stage: its control rows, and the premise of every geometry row (PREMISE: the kick
overflowed, the final did not, 0x0624 = 0xde after it; the refill rows: one refill line). Every
model's headline is gated by all of them.

The store window: the dwords of the 1024x768 target's pixels at G 33 (E465, crates/sgx-pipe zls.rs
store_dword), those inside the dump; hi = window dwords of tile rows 12 and below (index >= 512 *
34 * 12), lo = tile rows 0-11. No dump is compared or hashed outside the window, and no depth rule
is scored on lo (E1088's zero region: readings for Q107). T1, T2: the default triangle and T1
moved 96 px right, pixel by pixel as the library's sgxfive_tri_expect (inside, outside, within a
pixel of an edge). The regime: raised iff TA3DCtl dword 38 of ta3d.1.bin is non-zero (E625); a row
is scored under the regime read, not its label.

  zc  zc-r25 (E1088's zr-28-nl-1): premise and refill; store.2 = 0.25 at every hi window dword and
      store.1 = depth.1 at every hi window dword. zc-nl: render 1 did not overflow, sidx 0 (E628).
      zregs2 (REGCONTROL, gates no headline; H-OFFS): on zc-r25, from the first partial render's
      sample on, every sample with a non-zero 0x0480, 0x0484 or 0x0488 reads 0x0484 = rd:12 and
      0x0488 = rd:13 of words.1.txt (at least one such sample). If it fails or zc has not run,
      every H-PRMASK verdict of zl and zw is void (cannot tell).
  zl  per hi window dword of store.2, R = the row's refill (0.75):
        H-LOADTEST    inside T2: 0.5 if 0.5 < R else R; T2 edge: that or R; elsewhere R
        H-LOADNOTEST  R everywhere
        H-HOSTBITS    load bits (0x4002 in the word): H-LOADTEST's form; none: inside T2 0.5,
                      T2 edge or inside or on the edge of T1: 0.5 or 1.0, elsewhere 1.0
      A raised row scores H-LOADTEST and H-LOADNOTEST; a not-raised row scores H-HOSTBITS, its
      rivals' forms printed on the row. A model holds on a row with 0 hi dwords off.
      H-PRMASK on every row (as zw). Readings: lo zero counts of store.2 and depth.2, the final's
      target check.
  zw  0x0480 during the partial renders (0x0658 bit 0), rd:11 of words.1.txt: H-PRMASK holds when
      at least 80 % of the samples read rd:11 | 0x000c4000 and every other reads rd:11; H-PR1419
      the same with rd:11 | 0x00084000; H-OTHER when neither holds. Void unless zregs2 passed.
      Readings: the G 1 store after the final against the store after render 1.
  zz  depth.2's window: zero dwords in lo and signed dwords. H-ZCOUNT: zeros = 184320 raised,
      118784 not raised, and 0 signed; H-ZP: zeros another count.

REQUIRED: the files the scorer reads, per row (zc-r25's dumps by name; zc-r25 runs first in zc, so
a stop on zc-nl still finds them). read_files(STAGE, DIR) reads exactly what verdicts() reads;
producible(row) is the set of reading keys a row's job can produce."""
import os
import re
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import plan as PL  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {
    "zc": (".txt", ".depth-store.1.bin", ".depth.1.bin", ".words.1.txt", "zc-r25.depth-store.2.bin",
           "zc-r25.ta3d.1.bin") + FIXED,
    "zl": (".txt", ".depth-store.1.bin", ".depth-store.2.bin", ".depth.2.bin", ".ta3d.1.bin",
           ".words.1.txt") + FIXED,
    "zw": (".txt", ".depth-store.1.bin", ".depth-store.2.bin", ".ta3d.1.bin", ".words.1.txt")
    + FIXED,
    "zz": (".txt", ".depth.2.bin", ".ta3d.1.bin") + FIXED,
}
GATES = PL.GATES
ONE, HALF, R75, QUARTER = PL.ONE, PL.HALF, PL.R75, PL.QUARTER


def producible(row):
    a = row["args"].split()
    keys = {"ovf1", "ovf2", "thr", "diff", "nparts", "peak"} if "tri" in a else set()
    if "--depth-store" in a:
        keys |= {"sidx", "ssame"}
    if "--refill" in a:
        keys.add("refill")
    return keys


# ---- the text: run/hooks.sh's rd_words in Python ------------------------------------------------
def words(text):
    o, thr, sidx, diff, inpl, srep, nref = {}, None, None, None, None, {}, None
    regs, col, rows, cut, done = [], {}, [], False, False
    for ln in (text or "").splitlines():
        m = re.match(r"tri \d+x\d+ #([12]): (\S+) (\S+)", ln)
        if m:
            k = int(m.group(1))
            if m.group(2) == "overflowed,":
                o[k] = 1
            elif k not in o and (m.group(2) == "geometry" or m.group(3) == "triangle,"):
                o[k] = 0
        if ln.startswith("reg 0x0624 "):
            thr = "0x%x" % int(ln.split()[2], 16)
        elif ln.startswith("depth store #"):
            sidx = 1 if "32768+ distinct" in ln else 0
            m = re.match(r"depth store #(\d+): (.*)$", ln)
            if m:
                srep[int(m.group(1))] = m.group(2)
        elif ln.startswith("refill: render "):
            nref = (nref or 0) + 1
        elif re.match(r"diff: \d+ of ", ln):
            diff = ln.split()[1]
        elif " layer texels in place" in ln:
            m = re.search(r"(\d+) layer texels in place", ln)
            inpl = m.group(1) if m else inpl
        elif ln.startswith("timeline: regs"):
            if regs:
                done = True
                continue
            f = ln.split()
            regs = f[2:f.index("samples")] if "samples" in f else f[2:]
            col = {r: i for i, r in enumerate(regs)}
        elif ln.startswith("tl ") and regs and not done:
            f = ln.split()
            if len(f) != len(regs) + 2:
                cut = done = True
                continue
            rows.append([int(x, 16) for x in f[2:]])
    out = {}
    for k in (1, 2):
        if k in o:
            out[f"ovf{k}"] = str(o[k])
    for k, v in (("thr", thr), ("sidx", sidx)):
        if v is not None:
            out[k] = str(v)
    if 1 in srep and 2 in srep:
        out["ssame"] = str(int(srep[1] == srep[2]))
    for k, v in (("refill", nref), ("diff", diff), ("inplace", inpl)):
        if v is not None:
            out[k] = str(v)
    if not cut and rows and "0x0658" in col and "0x0724" in col:
        prs, peaks = runs(rows, col)
        out["nparts"] = str(len(prs))
        out["peak"] = "0x%x" % peaks[-1]
    return out


def runs(rows, col):
    """dpm_raise.py's runs(): (the status at each partial render's start, the peak of each TA
    run between partial renders)."""
    ip, ist = col["0x0658"], col["0x0724"]
    prs, peaks, cur, inpr = [], [], 0, False
    for r in rows:
        if r[ip] & 1:
            if not inpr:
                prs.append(r[ist] & 0xFFFF)
                peaks.append(cur)
                cur, inpr = 0, True
            continue
        inpr = False
        cur = max(cur, r[ist] & 0xFFFF)
    peaks.append(cur)
    return prs, peaks


def timeline(text):
    regs, rows = None, []
    for ln in (text or "").splitlines():
        if ln.startswith("timeline: regs") and regs is None:
            f = ln.split()
            regs = f[2:f.index("samples")]
        elif ln.startswith("tl ") and regs is not None:
            f = ln.split()
            if len(f) != len(regs) + 2:
                break
            rows.append([int(x, 16) for x in f[2:]])
    return ({r: i for i, r in enumerate(regs)}, rows) if regs else (None, [])


def tool_addrs(text):
    """The load and store buffers' addresses as the tool printed them (`depth: 0x...`,
    `depth store: 0x...`)."""
    a = {}
    for ln in (text or "").splitlines():
        m = re.match(r"(depth|depth store): (0x[0-9a-f]+) ", ln)
        if m and m.group(1) not in a:
            a[m.group(1)] = int(m.group(2), 16)
    return a.get("depth"), a.get("depth store")


def rd_words(wtext):
    """{index: value} of the render details (`rd:N=V`) of a words.N.txt."""
    out = {}
    for ln in (wtext or "").splitlines():
        m = re.match(r"rd:(\d+)=(0x[0-9a-f]+)$", ln.strip())
        if m:
            out[int(m.group(1))] = int(m.group(2), 16)
    return out


def zls_word(wtext):
    """The word CR_ISP_ZLSCTL should read: rd:11 with bit 0 set iff rd:53 bit 4 (E169)."""
    rd = rd_words(wtext)
    if 11 not in rd or 53 not in rd:
        return None
    return rd[11] | (rd[53] >> 4 & 1)


def tri_line(text, k):
    m = None
    for ln in (text or "").splitlines():
        mm = re.match(rf"tri \d+x\d+ #{k}: (?:overflowed, )?(\d+) triangle, (\d+) background, "
                      r"(\d+) other; wrong (\d+) inside, (\d+) outside, (\d+) at edges", ln)
        if mm:
            m = mm
    if not m:
        return None
    return dict(zip(("tri", "bg", "other", "win", "wout", "wedge"), map(int, m.groups())))


def dwords(b):
    return None if b is None else struct.unpack("<%dI" % (len(b) // 4), b[:len(b) // 4 * 4])


def _st(s):
    return "PASS" if s else "FAILED" if s is False else "cannot tell"


# ---- geometry: the library's reference and E465's layout ----------------------------------------
def tri_expect(v, x, y):
    """sgxfive_tri_expect (libsgxfive render.c): 1 inside, 0 outside, -1 within a pixel of an
    edge."""
    px, py = x * 16 + 8, y * 16 + 8
    area = (v[1][0] - v[0][0]) * (v[2][1] - v[0][1]) - (v[1][1] - v[0][1]) * (v[2][0] - v[0][0])
    near = False
    for i in range(3):
        p0, p1 = v[i], v[(i + 1) % 3]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        e = dx * (py - p0[1]) - dy * (px - p0[0])
        if area < 0:
            e = -e
        if e * e < 256 * (dx * dx + dy * dy):
            near = True
        elif e < 0:
            return 0
    return -1 if near else 1


def tri_default(w, h, dx=0, dy=0):
    """sgxfive_tri_default's vertices (1/16 px), moved as the tool's --move does."""
    return [(a * 16 * w // 64 + 16 * dx, b * 16 * h // 64 + 16 * dy)
            for a, b in ((8, 8), (56, 20), (20, 56))]


def in_tile_index(x, y):
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= ((y >> b) & 1) << (2 * b) | ((x >> b) & 1) << (2 * b + 1)
    return i | ((x >> 4) & 1) << 8


def store_dword(x, y, g):
    return 512 * ((y >> 4) * (g + 1) + (x >> 5)) + in_tile_index(x, y)


_WIN = {}


def window(move, g=33):
    """[(dword, T2 state)] of the target's pixels at pitch G + 1, T2 = the default triangle moved
    MOVE px right (state as tri_expect)."""
    if (move, g) not in _WIN:
        v = tri_default(PL.W, PL.H, move)
        _WIN[(move, g)] = [(store_dword(x, y, g), tri_expect(v, x, y))
                           for y in range(PL.H) for x in range(PL.W)]
    return _WIN[(move, g)]


class Run:
    def __init__(self, stage, d):
        self.d = d
        self.cases = K.rows(d, "cases.tsv")
        K.rows(d, "void.tsv")
        K.rows(d, "readings.tsv")
        self.preds = K.predictions(KP, stage)
        self.table = K.table(KP, stage)
        self.meta = {r["name"]: r for r in PL.tables()[stage]}
        self.seen = {}

    def done(self, n):
        return n in self.cases and K.completed(self.cases[n])

    def text(self, n, suffix=".txt"):
        if not self.done(n):
            return None
        if (n, suffix) not in self.seen:
            self.seen[(n, suffix)] = K.text(self.d, n + suffix)
        return self.seen[(n, suffix)]

    def dump(self, n, suffix):
        if (n, suffix) not in self.seen:
            self.seen[(n, suffix)] = (K._read(os.path.join(self.d, n + suffix))
                                      if self.done(n) else None)
        return self.seen[(n, suffix)]

    def raised(self, n):
        w = dwords(self.dump(n, ".ta3d.1.bin"))
        return None if w is None or len(w) < 39 else w[38] != 0


def premise(r, n):
    w = words(r.text(n)) if r.done(n) else None
    if w is None:
        return None, "not run"
    got = (w.get("ovf1"), w.get("ovf2"), w.get("thr"))
    return got == ("1", "0", "0x%x" % PL.THR_N), "ovf1 %s ovf2 %s thr %s" % got


def _row(lines, per_model, n, res):
    for m, (s, _) in res.items():
        per_model.setdefault(m, []).append(s)
    lines.append(f"ROW {n}: " + "; ".join(f"{m} {_st(s).replace('PASS', 'held')} ({t})"
                                          for m, (s, t) in res.items()))


def f32(v):
    return struct.unpack("<f", struct.pack("<I", v))[0]


_WIN2 = {}


def window2(move):
    """[(dword, T1 state, T2 state)] of the target's pixels at G 33, T2 = T1 moved MOVE px."""
    if move not in _WIN2:
        a, b = tri_default(PL.W, PL.H), tri_default(PL.W, PL.H, move)
        _WIN2[move] = [(store_dword(x, y, 33), tri_expect(a, x, y), tri_expect(b, x, y))
                       for y in range(PL.H) for x in range(PL.W)]
    return _WIN2[move]


def hi_forms(s2, move, refill, load):
    """({model form: hi window dwords off}, hi window dwords present) of a store after the final
    (score.py's docstring, zl)."""
    tin = HALF if f32(HALF) < f32(refill) else refill
    off = {"LOADTEST": 0, "LOADNOTEST": 0, "HOSTBITS": 0}
    n = 0
    for i, e1, e2 in window2(move):
        if i < PL.ROW12 or i >= len(s2):
            continue
        n += 1
        v = s2[i]
        if e2 == 1:
            lt = v != tin
            hb = v != HALF
        elif e2 == -1:
            lt = v not in (tin, refill)
            hb = v not in (HALF, ONE)
        else:
            lt = v != refill
            hb = v not in (HALF, ONE) if e1 != 0 else v != ONE
        off["LOADTEST"] += lt
        off["LOADNOTEST"] += v != refill
        off["HOSTBITS"] += lt if load else hb
    return off, n


def lo_zeros(d):
    """Zero window dwords of tile rows 0-11 (lo) of a G 33 dump."""
    if d is None:
        return None
    return sum(1 for i, _ in window(0) if i < PL.ROW12 and i < len(d) and d[i] == 0)


# ---- zc ----------------------------------------------------------------------------------------
def zregs2(r, n):
    """H-OFFS (PASS/FAILED/None, text): from the first partial render's sample on, every sample
    with a non-zero 0x0480-0x0488 reads 0x0484 = rd:12 and 0x0488 = rd:13 (words.1.txt)."""
    txt = r.text(n)
    if txt is None:
        return None, "not run"
    col, rows = timeline(txt)
    rd = rd_words(r.text(n, ".words.1.txt"))
    if col is None or not {"0x0480", "0x0484", "0x0488", "0x0658"} <= set(col) or not {12, 13} <= set(rd):
        return None, "no timeline of 0x0480-0x0488 and 0x0658, or no rd:12 / rd:13"
    a, b, c, p = col["0x0480"], col["0x0484"], col["0x0488"], col["0x0658"]
    first = next((i for i, x in enumerate(rows) if x[p] & 1), None)
    if first is None:
        return None, "no partial render sampled"
    nz = [(x[b], x[c]) for x in rows[first:] if x[a] or x[b] or x[c]]
    if not nz:
        return None, "no non-zero sample after the first partial render"
    bad = sorted({t for t in nz if t != (rd[12], rd[13])})
    return not bad, (f"want 0x{rd[12]:08x} 0x{rd[13]:08x} in {len(nz)} samples; off {len(bad)}"
                     + "".join(f", 0x{x:08x} 0x{y:08x}" for x, y in bad[:4]))


def zc_store(r, n):
    """(PASS/FAILED/None, text): store.2 = 0.25 and store.1 = depth.1 at every hi window dword."""
    s1, s2, d1 = (dwords(r.dump(n, x)) for x in (".depth-store.1.bin", ".depth-store.2.bin",
                                                 ".depth.1.bin"))
    if None in (s1, s2, d1):
        return None, "no dump"
    hi = [i for i, _ in window(0) if i >= PL.ROW12]
    if any(i >= min(len(s1), len(s2), len(d1)) for i in hi):
        return None, "a dump ends inside the hi window"
    q = sum(1 for i in hi if s2[i] == QUARTER)
    e = sum(1 for i in hi if s1[i] == d1[i])
    return q == e == len(hi), f"store.2 0.25 at {q}, store.1 = depth.1 at {e}, of {len(hi)} hi"


def _zc(r, controls, per_model, lines):
    for n, m in r.meta.items():
        txt = r.text(n)
        w = words(txt) if txt else {}
        if m["geo"]:
            p, t = premise(r, n)
            s, st = zc_store(r, n) if txt is not None else (None, "not run")
            ok = None if p is None or s is None else (p and w.get("refill") == "1" and s)
            controls[n] = ok
            lines.append(f"CONTROL {n}: {t}, refill {w.get('refill')}, {st}: {_st(ok)}")
            z, zt = zregs2(r, n)
            lines.append(f"REGCONTROL zregs2 {n}: {zt}: {_st(z)}")
            continue
        s = None if txt is None or "sidx" not in w else (w.get("ovf1") == "0" and w["sidx"] == "0")
        controls[n] = s
        lines.append(f"CONTROL {n}: ovf1 {w.get('ovf1')}, sidx {w.get('sidx')} (frozen 0, 0): "
                     f"{_st(s)}")


def zregs2_of(roots):
    """zc's zregs2 from the newest attempt that has zc: (True/False/None, text)."""
    for root in roots or ():
        d = os.path.join(root, "zc")
        if os.path.exists(os.path.join(d, "cases.tsv")):
            z, t = zregs2(Run("zc", d), "zc-r25")
            return z, f"zc in {root}: {t}"
    return None, "zc has not run"


# ---- H-PRMASK (zl, zw) -------------------------------------------------------------------------
def pr_samples(r, n):
    """(rd:11, [0x0480 during the partial renders]) or None."""
    col, rows = timeline(r.text(n))
    rd = rd_words(r.text(n, ".words.1.txt"))
    if col is None or "0x0480" not in col or "0x0658" not in col or 11 not in rd:
        return None
    a, p = col["0x0480"], col["0x0658"]
    return rd[11], [x[a] for x in rows if x[p] & 1]


def mask_holds(rd11, pr, mask):
    if not pr:
        return None
    want = rd11 | mask
    return sum(v == want for v in pr) >= 0.8 * len(pr) and all(v in (want, rd11) for v in pr)


def pr_verdicts(r, n, regs_ok):
    """{H-PRMASK, H-PR1419, H-OTHER: (state, text)} of a row (void unless zregs2 passed)."""
    got = pr_samples(r, n) if r.done(n) else None
    if got is None or not got[1]:
        why = "not run" if not r.done(n) else "no partial render sampled or no rd:11"
        return {k: (None, why) for k in ("H-PRMASK", "H-PR1419", "H-OTHER")}
    rd11, pr = got
    vals = sorted(set(pr))
    t = (f"rd:11 0x{rd11:08x}; {len(pr)} samples: "
         + ", ".join(f"0x{v:08x} x {pr.count(v)}" for v in vals[:5]))
    if not regs_ok:
        return {k: (None, "void: zregs2 " + _st(regs_ok) + "; " + t)
                for k in ("H-PRMASK", "H-PR1419", "H-OTHER")}
    a, b = mask_holds(rd11, pr, PL.PRMASK), mask_holds(rd11, pr, PL.PR1419)
    return {"H-PRMASK": (a, t), "H-PR1419": (b, t), "H-OTHER": (not a and not b, t)}


# ---- zl ----------------------------------------------------------------------------------------
def _premise_refill(r, controls, lines, n, m):
    txt = r.text(n)
    w = words(txt) if txt else {}
    p, t = premise(r, n)
    ok = p if "refill" not in m else (None if p is None or txt is None else
                                      (p and w.get("refill") == "1"))
    controls[f"premise:{n}"] = ok
    lines.append(f"CONTROL premise:{n}: {t}" + (f", refill {w.get('refill')}" if "refill" in m
                                                 else "") + f": {_st(ok)}")


def _zl(r, controls, per_model, lines, roots=None):
    zok, zt = zregs2_of(roots)
    lines.append(f"READING zregs2: {zt}: {_st(zok)}"
                 + ("" if zok else " (every H-PRMASK verdict below is void)"))
    for n, m in r.meta.items():
        _premise_refill(r, controls, lines, n, m)
        _row(lines, per_model, n, {"H-PRMASK": pr_verdicts(r, n, zok)["H-PRMASK"]})
        txt = r.text(n)
        if txt is None:
            _row(lines, per_model, n, {"H-LOADTEST": (None, "not run"),
                                       "H-LOADNOTEST": (None, "not run"),
                                       "H-HOSTBITS": (None, "not run")})
            continue
        rs = r.raised(n)
        s2, d2 = dwords(r.dump(n, ".depth-store.2.bin")), dwords(r.dump(n, ".depth.2.bin"))
        lines.append(f"READING {n}: raised {rs} (label {m['raised']}); lo zeros store.2 "
                     f"{lo_zeros(s2)}, depth.2 {lo_zeros(d2)}; final check {tri_line(txt, 2)}")
        if s2 is None or rs is None:
            _row(lines, per_model, n, {"H-LOADTEST": (None, "no dump or regime"),
                                       "H-LOADNOTEST": (None, "no dump or regime"),
                                       "H-HOSTBITS": (None, "no dump or regime")})
            continue
        off, tot = hi_forms(s2, PL.MOVE, m["refill"], bool(m["ctl"] & 0x4002))
        t = (f"{'raised' if rs else 'not raised'}; hi off of {tot}: "
             + ", ".join(f"{k} {v}" for k, v in off.items()))
        if tot != sum(1 for i, _ in window(0) if i >= PL.ROW12):
            res = {k: (None, "store.2 ends inside the hi window; " + t)
                   for k in ("H-LOADTEST", "H-LOADNOTEST", "H-HOSTBITS")}
        elif rs:
            res = {"H-LOADTEST": (off["LOADTEST"] == 0, t),
                   "H-LOADNOTEST": (off["LOADNOTEST"] == 0, t)}
        else:
            res = {"H-HOSTBITS": (off["HOSTBITS"] == 0, t)}
        _row(lines, per_model, n, res)


# ---- zw ----------------------------------------------------------------------------------------
def _zw(r, controls, per_model, lines, roots=None):
    zok, zt = zregs2_of(roots)
    lines.append(f"READING zregs2: {zt}: {_st(zok)}"
                 + ("" if zok else " (every verdict below is void)"))
    for n, m in r.meta.items():
        _premise_refill(r, controls, lines, n, m)
        _row(lines, per_model, n, pr_verdicts(r, n, zok))
        if not r.done(n):
            continue
        s1, s2 = dwords(r.dump(n, ".depth-store.1.bin")), dwords(r.dump(n, ".depth-store.2.bin"))
        g = PL.g_of(m["ctl"])
        if s1 is not None and s2 is not None:
            idx = sorted({i for i, _ in window(0, g)})
            eq = sum(1 for i in idx if i < len(s1) and i < len(s2) and s1[i] == s2[i])
            lines.append(f"READING {n}: raised {r.raised(n)} (label {m['raised']}); G {g} store.2 = "
                         f"store.1 in {eq} of {len(idx)} window dwords")


# ---- zz ----------------------------------------------------------------------------------------
def zcount(d2):
    """(zero window dwords in lo, signed window dwords) of a G 33 depth.2."""
    idx = [i for i, _ in window(0) if i < len(d2)]
    return sum(1 for i in idx if i < PL.ROW12 and d2[i] == 0), sum(1 for i in idx if d2[i] >> 31)


def _zz(r, controls, per_model, lines, roots=None):
    for n, m in r.meta.items():
        _premise_refill(r, controls, lines, n, m)
        rs = r.raised(n)
        d2 = dwords(r.dump(n, ".depth.2.bin"))
        if rs is None or d2 is None:
            why = "not run" if not r.done(n) else "no dump or regime"
            _row(lines, per_model, n, {"H-ZCOUNT": (None, why), "H-ZP": (None, why)})
            continue
        z, sg = zcount(d2)
        want = PL.ZC_RAISED if rs else PL.ZC_NOT
        t = f"raised {rs} (label {m['raised']}); zero2_lo {z} (frozen {want}), sign2 {sg}"
        _row(lines, per_model, n, {"H-ZCOUNT": (z == want and sg == 0, t), "H-ZP": (z != want, t)})


SCORERS = {"zl": _zl, "zw": _zw, "zz": _zz}


def verdicts(stage, d, roots=None):
    r = Run(stage, d)
    controls, per_model, lines = {}, {}, []
    if stage == "zc":
        _zc(r, controls, per_model, lines)
    else:
        SCORERS[stage](r, controls, per_model, lines, roots)
    return controls, per_model, lines


def read_files(stage, d):
    verdicts(stage, d)


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            d = os.path.join(root, dep)
            if os.path.isdir(d):
                g = SK.gate(verdicts(dep, d)[0])
                print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
                return 0 if g.ok else 1
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2], argv[3:])
        print("\n".join(lines))
        g = SK.gate(controls)
        print("SUMMARY: " + argv[1] + ": controls " + ("all passed" if g.ok else
                                                         "; ".join(g.problems)))
        for m, states in sorted(per_model.items()):
            h = SK.headline(m, controls, states)
            print("SUMMARY: " + argv[1] + ": " + (h if h.startswith(m) else f"{m}: {h}"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
