#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r23-dpm's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 b2b6bc0d44fc, pinned in FROZEN.commits).
The text readers, the store window and the library's triangle are r21-zls's (data
render/closing-r21-zls/score/score.py), with t22b's keep and kept-copy lines added.

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage of this session gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Controls of a stage: its control rows, and the premise of every other row (PREMISE: rl and zn,
the kick overflowed, the final did not, 0x0624 = 0xde after it, zn one refill line; og, the first
context did not overflow and the second context's geometry kick was made). Every model's headline
is gated by all of them (a FAILED control voids the stage's headlines).

  rl  render 2's keep line (`tri 1024x768 #2: [overflowed, ]target kept, X pixels changed, colours
      C N, ... (+M more); guard G`): red = 0xffff0000 (render 2's triangle), green = 0xff00ff00
      (render 1's), the sentinel 0xdeadbeef (the library's fill before render 1, E442's reload of
      it). H-RELOAD: X = red, no colour but red, green and the sentinel (none `more`), green > 0.
      H-REPAINT: X > red and no green. Both scored on every row, regime read (ta3d.1.bin dword 38).
      Controls: rl-c1, render 1's line 207456 triangle, wrong 0 inside, 578976 other, no overflow;
      rl-c2, its premise and X = 786432 with colours exactly red 207456, 0xff000080 578976.
  og  the kept copies NAME.kept.closed.1.bin (after the early close), .kept.geo.1.bin (after the
      second context's geometry kick), .kept.1.bin (after its closing render); the owner words
      (E631, E1087): page 1 dword 0 = 0x00200047, page 2 dword 0 = 0x04000417, page 3 dwords 0 and
      1 = 0x00020001, 2 (dword by dword, never a hash). H-TAKICK: all 4 in geo and in after;
      H-RENDEREND: 0 in geo, 4 in after. An empty geo or after copy: cannot tell. Control og-4
      (flag 0x4): no overflow, geo and after copies of 24576 bytes, 0 owner words in both.
  zn  per hi window dword of store.2 (E1093's form, R = 0.75): H-LOADNODRAW = R everywhere (r21's
      LOADNOTEST form), H-HOSTBITS = 0.5 inside T2, R elsewhere (r21's LOADTEST form, the edges
      either); a row read raised: cannot tell. Control zn-c (no load bits): premise, refill, not
      raised, and r21's H-HOSTBITS no-load form (0.5 inside T2, 0.5 or 1.0 in T1 \\ T2, 1.0
      elsewhere) at 0 hi dwords off.

No param or depth buffer is hashed or compared outside its window (no kitscore.param_hash needed:
no param comparison here). REQUIRED: the files the scorer reads, per row. read_files(STAGE, DIR)
reads exactly what verdicts() reads; producible(row) is the set of reading keys a row's job can
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
    "rl": (".txt", ".ta3d.1.bin") + FIXED,
    "og": (".txt", ".kept.closed.1.bin", ".kept.geo.1.bin", ".kept.1.bin") + FIXED,
    "zn": (".txt", ".depth-store.2.bin", ".ta3d.1.bin") + FIXED,
}
GATES = PL.GATES
ONE, HALF, R75 = PL.ONE, PL.HALF, PL.R75
PAGE = 4096


def tool_args(args):
    a = args.split()
    return a[a.index("--") + 2:] if "--" in a else a


def producible(row):
    a = tool_args(row["args"])
    if a[:1] != ["tri"]:
        return set()
    keys = {"ovf1", "ovf2", "diff", "tri1", "oth1", "win1"}
    if "--regs" in a:
        keys.add("thr")
    if row["tool"] == "rt":
        keys |= {"nparts", "peak"}
    if "--depth-store" in a:
        keys.add("sidx")
    if "--refill" in a:
        keys.add("refill")
    if "--keep-target" in a:
        keys |= {"chg", "red2"}
    if "--kept-copy" in a:
        keys |= {"kept", "gsize", "fsize"}
    return keys


# ---- the text: run/hooks.sh's rd_words in Python ------------------------------------------------
TRI1 = re.compile(r"tri \d+x\d+ #1: (?:overflowed, )?(\d+) triangle, \d+ background, (\d+) other; "
                  r"wrong (\d+) inside")
KEEP2 = re.compile(r"tri \d+x\d+ #2: (?:overflowed, )?target kept, (\d+) pixels changed, colours"
                   r"(.*); guard (\d+)$")
KEPT = re.compile(r"tri: render_kept (.*): /.* \((\d+) bytes\)$")


def words(text):
    o, thr, sidx, diff, nref = {}, None, None, None, None
    t1 = keep = None
    nkept, gsize, fsize, anykept = 0, None, None, False
    regs, col, rows, cut, done = [], {}, [], False, False
    for ln in (text or "").splitlines():
        m = re.match(r"tri \d+x\d+ #([12]): (\S+) (\S+)", ln)
        if m:
            k = int(m.group(1))
            if m.group(2) == "overflowed,":
                o[k] = 1
            elif k not in o and (m.group(2) in ("geometry", "target") or m.group(3) == "triangle,"):
                o[k] = 0
        m = TRI1.match(ln)
        if m:
            t1 = m.groups()
        m = KEEP2.match(ln)
        if m:
            c = re.search(r"0xffff0000 (\d+)", m.group(2))
            keep = (m.group(1), c.group(1) if c else "0")
        m = KEPT.match(ln)
        if m:
            anykept = True
            b = int(m.group(2))
            nkept += b > 0
            if m.group(1).startswith("after the second context's geometry kick"):
                gsize = b
            elif m.group(1).startswith("after the second context's render"):
                fsize = b
        if ln.startswith("reg 0x0624 "):
            thr = "0x%x" % int(ln.split()[2], 16)
        elif ln.startswith("depth store #"):
            sidx = 1 if "32768+ distinct" in ln else 0
        elif ln.startswith("refill: render "):
            nref = (nref or 0) + 1
        elif re.match(r"diff: \d+ of ", ln):
            diff = ln.split()[1]
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
    for k, v in (("thr", thr), ("sidx", sidx), ("refill", nref), ("diff", diff)):
        if v is not None:
            out[k] = str(v)
    if t1:
        out["tri1"], out["oth1"], out["win1"] = t1
    if keep:
        out["chg"], out["red2"] = keep
    if anykept:
        out["kept"] = str(nkept)
    if gsize is not None:
        out["gsize"] = str(gsize)
    if fsize is not None:
        out["fsize"] = str(fsize)
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


def keep_line(text):
    """(changed, {colour: count}, more, guard) of render 2's keep line, or None."""
    got = None
    for ln in (text or "").splitlines():
        m = KEEP2.match(ln)
        if m:
            body = m.group(2)
            more = re.search(r"\(\+(\d+) more\)", body)
            cols = {int(c, 16): int(n) for c, n in re.findall(r"(0x[0-9a-f]{8}) (\d+)", body)}
            got = (int(m.group(1)), cols, int(more.group(1)) if more else 0, int(m.group(3)))
    return got


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


# ---- geometry: the library's reference and E465's layout (r21-zls's) -----------------------------
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


_WIN2 = {}


def window2(move):
    """[(dword, T1 state, T2 state)] of the target's pixels at G 33, T2 = T1 moved MOVE px."""
    if move not in _WIN2:
        a, b = tri_default(PL.W, PL.H), tri_default(PL.W, PL.H, move)
        _WIN2[move] = [(store_dword(x, y, 33), tri_expect(a, x, y), tri_expect(b, x, y))
                       for y in range(PL.H) for x in range(PL.W)]
    return _WIN2[move]


def hi_total():
    return sum(1 for i, _, _ in window2(PL.MOVE) if i >= PL.ROW12)


def f32(v):
    return struct.unpack("<f", struct.pack("<I", v))[0]


def hi_forms(s2, move, refill, load):
    """({form: hi window dwords off}, hi window dwords present) of a store after the final
    (r21-zls's zl forms: LOADTEST = H-HOSTBITS of a load row here, LOADNOTEST = H-LOADNODRAW,
    HOSTBITS = the no-load control's form when load is False)."""
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


def _premise_refill(r, controls, lines, n, m):
    txt = r.text(n)
    w = words(txt) if txt else {}
    p, t = premise(r, n)
    ok = p if "refill" not in m else (None if p is None or txt is None else
                                      (p and w.get("refill") == "1"))
    controls[f"premise:{n}"] = ok
    lines.append(f"CONTROL premise:{n}: {t}" + (f", refill {w.get('refill')}" if "refill" in m
                                                 else "") + f": {_st(ok)}")
    return ok


def _row(lines, per_model, n, res):
    for m, (s, _) in res.items():
        per_model.setdefault(m, []).append(s)
    lines.append(f"ROW {n}: " + "; ".join(f"{m} {_st(s).replace('PASS', 'held')} ({t})"
                                          for m, (s, t) in res.items()))


# ---- rl ----------------------------------------------------------------------------------------
def cols_text(cols, more):
    return ", ".join(f"0x{c:08x} {v}" for c, v in sorted(cols.items(), key=lambda x: -x[1])) + (
        f" (+{more} more)" if more else "")


def rl_models(kl):
    """{H-RELOAD, H-REPAINT: (state, text)} of a keep line (changed, colours, more, guard)."""
    if kl is None:
        return {k: (None, "no keep line") for k in ("H-RELOAD", "H-REPAINT")}
    chg, cols, more, guard = kl
    red, green = cols.get(PL.RED, 0), cols.get(PL.GREEN, 0)
    other = more or any(c not in (PL.RED, PL.GREEN, PL.SENT) for c in cols)
    t = f"changed {chg}, red {red}, green {green}; colours {cols_text(cols, more)}; guard {guard}"
    return {"H-RELOAD": (chg == red and not other and green > 0, t),
            "H-REPAINT": (chg > red and green == 0, t)}


def _rl(r, controls, per_model, lines, roots=None):
    for n, m in r.meta.items():
        txt = r.text(n)
        w = words(txt) if txt else {}
        if n == "rl-c1":
            want = (str(PL.T_PIX), "0", str(PL.BG_PIX))
            got = (w.get("tri1"), w.get("win1"), w.get("oth1"))
            ok = None if txt is None or None in got else (w.get("ovf1") == "0" and got == want)
            controls[n] = ok
            lines.append(f"CONTROL {n}: ovf1 {w.get('ovf1')}, triangle {got[0]}, wrong inside "
                         f"{got[1]}, other {got[2]} (frozen 0, {', '.join(want)}): {_st(ok)}")
            continue
        p, pt = premise(r, n)
        kl = keep_line(txt)
        if n == "rl-c2":
            want = {PL.RED: PL.T_PIX, PL.NAVY: PL.BG_PIX}
            ok = None if p is None or kl is None else (p and kl[0] == PL.NPIX and kl[1] == want
                                                       and not kl[2])
            controls[n] = ok
            lines.append(f"CONTROL {n}: {pt}; " + (f"changed {kl[0]}, colours "
                                                   f"{cols_text(kl[1], kl[2])}" if kl else
                                                   "no keep line")
                         + f" (frozen {PL.NPIX}, 0xffff0000 {PL.T_PIX}, 0xff000080 {PL.BG_PIX}): "
                         + _st(ok))
            continue
        _premise_refill(r, controls, lines, n, m)
        rs = r.raised(n) if txt is not None else None
        lines.append(f"READING {n}: raised {rs} (label {m['raised']}); render 1 "
                     f"{tri_line(txt, 1)}")
        _row(lines, per_model, n, rl_models(kl) if txt is not None else
             {k: (None, "not run") for k in ("H-RELOAD", "H-REPAINT")})


# ---- og ----------------------------------------------------------------------------------------
def owner_words(b):
    """(owner words present at their places, other non-zero dwords of pages 1 to 3 as
    [(page, dword, value)]) of a kept copy, or None when it is empty or absent."""
    if not b:
        return None
    w = dwords(b)
    have = sum(1 for (p, i), v in PL.OWNER.items() if p * 1024 + i < len(w) and
               w[p * 1024 + i] == v)
    other = [(i // 1024, i % 1024, v) for i, v in enumerate(w[1024:4096], 1024)
             if v and (i // 1024, i % 1024) not in PL.OWNER]
    return have, other


def _ow_text(name, got, size):
    if got is None:
        return f"{name} empty ({size} bytes)"
    return f"{name} {got[0]} owner words, {len(got[1])} other dwords" + "".join(
        f", p{p}:{i}=0x{v:08x}" for p, i, v in got[1][:4])


def _og(r, controls, per_model, lines, roots=None):
    for n, m in r.meta.items():
        txt = r.text(n)
        w = words(txt) if txt else {}
        geo_ok = txt is not None and re.search(r"^tri2 \d+x\d+ #1: geometry only, the scene left "
                                               r"open$", txt, re.M) is not None
        cp = {k: r.dump(n, f".kept.{k}1.bin") for k in ("closed.", "geo.", "")}
        ow = {k: owner_words(b) for k, b in cp.items()}
        sz = {k: (len(b) if b is not None else None) for k, b in cp.items()}
        t = "; ".join(_ow_text(k.rstrip(".") or "after", ow[k], sz[k]) for k in cp)
        if m["set"] == "control":
            ok = None if txt is None or ow["geo."] is None or ow[""] is None else (
                w.get("ovf1") == "0" and geo_ok and sz["geo."] == sz[""] == PL.OG_SIZE
                and ow["geo."][0] == 0 and ow[""][0] == 0)
            controls[n] = ok
            lines.append(f"CONTROL {n}: ovf1 {w.get('ovf1')}, geometry kick {geo_ok}; {t}: "
                         f"{_st(ok)}")
            continue
        ok = None if txt is None else (w.get("ovf1") == "0" and geo_ok)
        controls[f"premise:{n}"] = ok
        lines.append(f"CONTROL premise:{n}: ovf1 {w.get('ovf1')}, geometry kick {geo_ok}: "
                     f"{_st(ok)}")
        lines.append(f"READING {n}: {t}")
        g, a = ow["geo."], ow[""]
        if txt is None or g is None or a is None:
            why = "not run" if txt is None else "an empty copy (E1085's park race)"
            _row(lines, per_model, n, {"H-TAKICK": (None, why), "H-RENDEREND": (None, why)})
            continue
        tt = f"geo {g[0]}, after {a[0]} of 4"
        _row(lines, per_model, n, {"H-TAKICK": (g[0] == 4 and a[0] == 4, tt),
                                   "H-RENDEREND": (g[0] == 0 and a[0] == 4, tt)})


# ---- zn ----------------------------------------------------------------------------------------
def _zn(r, controls, per_model, lines, roots=None):
    for n, m in r.meta.items():
        txt = r.text(n)
        rs = r.raised(n) if txt is not None else None
        s2 = dwords(r.dump(n, ".depth-store.2.bin")) if txt is not None else None
        off, tot = hi_forms(s2, PL.MOVE, m["refill"], bool(m["ctl"] & 0x4002)) if s2 else ({}, 0)
        full = tot == hi_total()
        t = (f"{'raised' if rs else 'not raised' if rs is False else 'regime unread'}; hi off of "
             f"{tot}: " + ", ".join(f"{k} {v}" for k, v in off.items()))
        lines.append(f"READING {n}: raised {rs} (label {m['raised']}); final check "
                     f"{tri_line(txt, 2)}")
        if m["set"] == "control":
            p, pt = premise(r, n)
            w = words(txt) if txt else {}
            ok = None if p is None or s2 is None or rs is None or not full else (
                p and w.get("refill") == "1" and rs is False and off["HOSTBITS"] == 0)
            controls[n] = ok
            lines.append(f"CONTROL {n}: {pt}, refill {w.get('refill')}; {t}: {_st(ok)}")
            continue
        _premise_refill(r, controls, lines, n, m)
        if txt is None or s2 is None or rs is None or not full:
            why = "not run" if txt is None else "no dump, a short one, or no regime"
            _row(lines, per_model, n, {"H-LOADNODRAW": (None, why), "H-HOSTBITS": (None, why)})
            continue
        if rs:
            _row(lines, per_model, n, {"H-LOADNODRAW": (None, "raised: E1093's regime; " + t),
                                       "H-HOSTBITS": (None, "raised: E1093's regime; " + t)})
            continue
        _row(lines, per_model, n, {"H-LOADNODRAW": (off["LOADNOTEST"] == 0, t),
                                   "H-HOSTBITS": (off["LOADTEST"] == 0, t)})


SCORERS = {"rl": _rl, "og": _og, "zn": _zn}


def verdicts(stage, d, roots=None):
    r = Run(stage, d)
    controls, per_model, lines = {}, {}, []
    SCORERS[stage](r, controls, per_model, lines, roots)
    return controls, per_model, lines


def read_files(stage, d):
    verdicts(stage, d)


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        print(f"gate {argv[2]}: no stage of this session gates another")
        return 0
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
