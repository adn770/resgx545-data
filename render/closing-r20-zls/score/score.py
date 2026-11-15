#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r20-zls's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 c0f8c41fbbf9, pinned in FROZEN.commits);
q107_rule.py (closing12 c3-q107, frozen there) is read at the frozen data commit (gen/pins.py).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of zc passed (zr, zm, zq)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Controls of a stage: its control rows, and the premise of every geometry row (PREMISE: the kick
overflowed, the final did not, 0x0624 = 0xde after it; zr: the refill line). Every model's
headline is gated by all of them.

The store window: the dwords of the 1024x768 target's pixels at G 33 (E465: 512 (34 ty + tx) +
the in-tile index of a 32 x 16 tile, crates/sgx-pipe zls.rs store_dword), those inside the dump.
No dump is compared or hashed outside it. T1, T2: the default triangle and its move, pixel by
pixel as the library's sgxfive_tri_expect (inside, outside, within a pixel of an edge: either).
The regime: raised iff TA3DCtl dword 38 of ta3d.1.bin is non-zero (E625, E1082).

  zc  zc-nl, zc-ld: render 1 did not overflow and the store report's sidx is 0 / 1 (E628).
      zc-geo: premise, ssame 1, one partial render, store.2 = store.1 at every window dword.
      zregs (REGCONTROL, not a control: it gates no headline): on zc-nl and zc-ld one timeline
      sample reads 0x0480 = rd:11 | (rd:53 bit 4) (E169), 0x0484 = the load buffer's address,
      0x0488 = the store buffer's (the tool's `depth:` and `depth store:` lines). If it fails or
      zc has not run, every register reading of zr is void.
  zr  per window dword of store.2 against the row's own store.1 (a = store.1 with bit 31 clear):
        H-LOADBASE   0.25 everywhere
        H-STOREBASE  T2 inside: 0.5 where a is 1.0 or 0.5, else a; T2 edge: a or 0.5; outside: a
        H-NOSTORE    store.1
        H-HOSTBITS   no load bits: T2 inside 0.5, edge 0.5 or 1.0, outside 1.0; load bits: 0.25
      A row that is not raised is scored by H-HOSTBITS's form under every model (the regime
      rule). A model holds on a row with 0 window dwords off. zr-28-e336 is a reading only.
      Readings: H-RDREG (0x0480 during the partial renders = render 1's rd:11 | bit 0, and after
      them render 2's) vs H-EDMPATCH (any other word); 0x0480 bit 19 during the partial renders;
      the load buffer after the final; the final's target check.
  zm  the final's target check (`tri 1024x768 #2:`): H-REPAINT wrong in + out + edge 0; H-HOLES
      `other` > 0 (pixels left at the library's sentinel, which it writes before every kick).
  zq  raised rows cannot tell. G 33: signed window dwords in depth.2 and zeros in its window
      below tile row 12: H-NR-PLAIN 0 and 0, H-AFTERPR zeros > 0. G 1: q107_rule's RULE on
      depth.2 against the G 33 twin's: H-NR-PLAIN every scored dword, H-AFTERPR fewer.

REQUIRED: the files the scorer reads, per row (zc-geo's store after the final by name; zc-geo
runs first in zc, so a stop on a later zc row still finds it). read_files(STAGE, DIR) reads
exactly what verdicts() reads; producible(row) is the set of reading keys a row's job can
produce."""
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
    "zc": (".txt", ".depth-store.1.bin", ".words.1.txt", "zc-geo.depth-store.2.bin") + FIXED,
    "zr": (".txt", ".depth-store.1.bin", ".depth-store.2.bin", ".depth.2.bin", ".ta3d.1.bin",
           ".words.1.txt", ".words.2.txt") + FIXED,
    "zm": (".txt", ".ta3d.1.bin") + FIXED,
    "zq": (".txt", ".depth.2.bin", ".ta3d.1.bin") + FIXED,
}
GATES = PL.GATES
Q107 = "data:cited/closing12/plan/c3-q107/q107_rule.py"
ONE, HALF, QUARTER = PL.ONE, PL.HALF, PL.QUARTER


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


def t1_minus_t2(move):
    a, b = tri_default(PL.W, PL.H), tri_default(PL.W, PL.H, move)
    return sum(1 for y in range(PL.H) for x in range(PL.W)
               if tri_expect(a, x, y) == 1 and tri_expect(b, x, y) == 0)


def off_counts(s1, s2, move, load):
    """{model form: window dwords off} for zr (score.py's docstring)."""
    off = {"LOADBASE": 0, "STOREBASE": 0, "NOSTORE": 0, "HOSTBITS": 0}
    n = 0
    for i, e in window(move):
        if i >= len(s1) or i >= len(s2):
            continue
        n += 1
        v, a = s2[i], s1[i] & 0x7FFFFFFF
        off["LOADBASE"] += v != QUARTER
        off["NOSTORE"] += v != s1[i]
        if e == 1:
            off["STOREBASE"] += v != (HALF if a in (ONE, HALF) else a)
            hb = v != HALF
        elif e == -1:
            off["STOREBASE"] += v not in (a, HALF)
            hb = v not in (HALF, ONE)
        else:
            off["STOREBASE"] += v != a
            hb = v != ONE
        off["HOSTBITS"] += (v != QUARTER) if load else hb
    return off, n


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


# ---- zc ----------------------------------------------------------------------------------------
def zregs(r, n):
    """(PASS/FAILED/None, text): one sample with 0x0480, 0x0484, 0x0488 = word, load, store."""
    txt = r.text(n)
    if txt is None:
        return None, "not run"
    col, rows = timeline(txt)
    want = zls_word(r.text(n, ".words.1.txt"))
    ld, st = tool_addrs(txt)
    if col is None or not {"0x0480", "0x0484", "0x0488"} <= set(col) or None in (want, ld, st):
        return None, f"no timeline of 0x0480-0x0488 or no word ({want}) or addresses ({ld}, {st})"
    a, b, c = col["0x0480"], col["0x0484"], col["0x0488"]
    seen = sorted({(x[a], x[b], x[c]) for x in rows})
    ok = (want, ld, st) in seen
    return ok, (f"want 0x{want:08x} 0x{ld:08x} 0x{st:08x}; read "
                + ", ".join("0x%08x 0x%08x 0x%08x" % t for t in seen[:6])
                + (f" (+{len(seen) - 6})" if len(seen) > 6 else ""))


def _zc(r, controls, per_model, lines):
    for n, m in r.meta.items():
        txt = r.text(n)
        w = words(txt) if txt else {}
        if m["geo"]:
            p, t = premise(r, n)
            s1, s2 = dwords(r.dump(n, ".depth-store.1.bin")), dwords(r.dump(n, ".depth-store.2.bin"))
            if s1 is None or s2 is None:
                eq = tot = None
            else:
                idx = [i for i, _ in window(0) if i < len(s1) and i < len(s2)]
                tot, eq = len(idx), sum(1 for i in idx if s1[i] == s2[i])
            ok = None if p is None or eq is None or "nparts" not in w else (
                p and w.get("ssame") == "1" and w["nparts"] == "1" and eq == tot)
            controls[n] = ok
            lines.append(f"CONTROL {n}: {t}, ssame {w.get('ssame')}, nparts {w.get('nparts')}, "
                         f"store.2 = store.1 in {eq} of {tot} window dwords: {_st(ok)}")
            continue
        want = str(int(m["ctl"] == PL.LD33))
        s = None if txt is None or "sidx" not in w else (w.get("ovf1") == "0" and w["sidx"] == want)
        controls[n] = s
        lines.append(f"CONTROL {n}: ovf1 {w.get('ovf1')}, sidx {w.get('sidx')} (frozen 0, {want}): "
                     f"{_st(s)}")
        z, t = zregs(r, n)
        lines.append(f"REGCONTROL zregs {n}: {t}: {_st(z)}")


def zregs_of(roots):
    """zc's zregs from the newest attempt that has zc: (True/False/None, text)."""
    for root in roots or ():
        d = os.path.join(root, "zc")
        if os.path.isdir(os.path.join(d)) and os.path.exists(os.path.join(d, "cases.tsv")):
            r = Run("zc", d)
            got = [zregs(r, n)[0] for n in ("zc-nl", "zc-ld")]
            if None in got:
                return None, f"zc in {root}: not read"
            return all(got), f"zc in {root}: {got}"
    return None, "zc has not run"


# ---- zr ----------------------------------------------------------------------------------------
def rdreg(r, n, m):
    """H-RDREG's reading: 0x0480 values during the partial renders (0x0658 bit 0) and after the
    last one, against render 1's and render 2's words."""
    col, rows = timeline(r.text(n))
    w1, w2 = zls_word(r.text(n, ".words.1.txt")), zls_word(r.text(n, ".words.2.txt"))
    if col is None or "0x0480" not in col or "0x0658" not in col or None in (w1, w2):
        return None, "no 0x0480 timeline or words"
    a, p = col["0x0480"], col["0x0658"]
    last = max((i for i, x in enumerate(rows) if x[p] & 1), default=None)
    pr = sorted({x[a] for x in rows if x[p] & 1})
    after = sorted({x[a] for x in rows[last + 1:]}) if last is not None else []
    ok = None if last is None else (pr == [w1] and w2 in after)
    b19 = sorted({x >> 19 & 1 for x in pr})
    return ok, ("render 1 0x%08x, render 2 0x%08x; during the partial renders %s (bit 19 %s); "
                "after them %s" % (w1, w2, " ".join("0x%08x" % v for v in pr), b19,
                                   " ".join("0x%08x" % v for v in after[:6])))


def _zr(r, controls, per_model, lines, roots=None):
    zr_ok, zr_t = zregs_of(roots)
    lines.append(f"READING zregs: {zr_t}: {_st(zr_ok)}"
                 + ("" if zr_ok else " (every register reading below is void)"))
    for n, m in r.meta.items():
        txt = r.text(n)
        w = words(txt) if txt else {}
        p, t = premise(r, n)
        ok = None if p is None or txt is None else (p and w.get("refill") == "1")
        controls[f"premise:{n}"] = ok
        lines.append(f"CONTROL premise:{n}: {t}, refill {w.get('refill')}: {_st(ok)}")
        if txt is None:
            if not m["reading_only"]:
                _row(lines, per_model, n, {k: (None, "not run") for k in
                                           ("H-LOADBASE", "H-STOREBASE", "H-NOSTORE", "H-HOSTBITS")})
            continue
        rs = r.raised(n)
        s1, s2 = dwords(r.dump(n, ".depth-store.1.bin")), dwords(r.dump(n, ".depth-store.2.bin"))
        d2 = dwords(r.dump(n, ".depth.2.bin"))
        hit, ht = rdreg(r, n, m)
        lines.append(f"READING {n}: H-RDREG {_st(hit) if zr_ok else 'void'} ({ht})")
        q = None if d2 is None else sum(1 for i, _ in window(m["move"]) if i < len(d2)
                                         and d2[i] == QUARTER)
        lines.append(f"READING {n}: raised {rs} (label {m['raised']}); load buffer after the final "
                     f"0.25 in {q} window dwords; final check {tri_line(txt, 2)}")
        if m["reading_only"]:
            if s1 is not None and s2 is not None:
                idx = sorted({i for i, _ in window(0, 1)})
                eq = sum(1 for i in idx if i < len(s1) and i < len(s2) and s1[i] == s2[i])
                lines.append(f"READING {n}: G 1 store.2 = store.1 in {eq} of {len(idx)} window "
                             "dwords")
            continue
        if s1 is None or s2 is None or rs is None:
            _row(lines, per_model, n, {k: (None, "no dump") for k in
                                       ("H-LOADBASE", "H-STOREBASE", "H-NOSTORE", "H-HOSTBITS")})
            continue
        off, tot = off_counts(s1, s2, m["move"], m["ctl"] == PL.LD33)
        t = (f"{'raised' if rs else 'not raised'}; off of {tot}: " +
             ", ".join(f"{k} {v}" for k, v in off.items()))
        res = {}
        for mod in ("LOADBASE", "STOREBASE", "NOSTORE"):
            res["H-" + mod] = (off[mod if rs else "HOSTBITS"] == 0, t)
        res["H-HOSTBITS"] = (off["HOSTBITS"] == 0, t)
        _row(lines, per_model, n, res)


# ---- zm ----------------------------------------------------------------------------------------
def _zm(r, controls, per_model, lines, roots=None):
    k = None
    for n, m in r.meta.items():
        p, t = premise(r, n)
        controls[f"premise:{n}"] = p
        lines.append(f"CONTROL premise:{n}: {t}: {_st(p)}")
        c = tri_line(r.text(n), 2)
        if c is None:
            _row(lines, per_model, n, {"H-REPAINT": (None, "no check"), "H-HOLES": (None, "no check")})
            continue
        if k is None:
            k = t1_minus_t2(m["move"])
        t = (f"raised {r.raised(n)}; {c['tri']} triangle, {c['bg']} background, {c['other']} other;"
             f" wrong {c['win']} in, {c['wout']} out, {c['wedge']} edge; |T1 \\ T2| {k}")
        _row(lines, per_model, n, {"H-REPAINT": (c["win"] + c["wout"] + c["wedge"] == 0, t),
                                   "H-HOLES": (c["other"] > 0, t)})


# ---- zq ----------------------------------------------------------------------------------------
def rule_hits(g1, g33):
    """q107_rule.py's RULE: (equal dwords, scored dwords) of a G 1 dump against its G 33 twin
    (E1020's q107_score.py: a dword whose source lies past the G 33 dump is left out)."""
    import pins
    q = pins.module(Q107, "q107_rule")
    pred = {i: v for i, v in q.predict(tuple(g33) + (None,) * (1700 * 512), q.W, q.H, 1,
                                       "RULE").items() if v is not None}
    return sum(1 for i, v in pred.items() if i < len(g1) and g1[i] == v), len(pred)


def g33_plain(d2):
    """(signed window dwords, zero window dwords below tile row 12) of a G 33 depth.2."""
    idx = [i for i, _ in window(0) if i < len(d2)]
    return sum(1 for i in idx if d2[i] >> 31), sum(1 for i in idx if i < PL.ROW12 and d2[i] == 0)


def _zq(r, controls, per_model, lines, roots=None):
    for n, m in r.meta.items():
        p, t = premise(r, n)
        controls[f"premise:{n}"] = p
        lines.append(f"CONTROL premise:{n}: {t}: {_st(p)}")
        rs = r.raised(n)
        d2 = dwords(r.dump(n, ".depth.2.bin"))
        lines.append(f"READING {n}: raised {rs} (frozen not raised, E625 with U {PL.U_RAMP})")
        if rs is not False or d2 is None:
            why = "raised: cannot tell" if rs else "no dump or regime"
            _row(lines, per_model, n, {"H-NR-PLAIN": (None, why), "H-AFTERPR": (None, why)})
            continue
        if m["g"] == 33:
            sg, z = g33_plain(d2)
            t = f"sign2 {sg}, zero2_lo {z} (window)"
            res = {"H-NR-PLAIN": (sg == 0 and z == 0, t), "H-AFTERPR": (z > 0, t)}
        else:
            tw = dwords(r.dump(m["twin"], ".depth.2.bin"))
            hit = None if tw is None else rule_hits(d2, tw)
            t = f"RULE {hit}"
            res = {"H-NR-PLAIN": (None if hit is None else hit[0] == hit[1], t),
                   "H-AFTERPR": (None if hit is None else hit[0] < hit[1], t)}
        _row(lines, per_model, n, res)


SCORERS = {"zc": _zc, "zr": _zr, "zm": _zm, "zq": _zq}


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
