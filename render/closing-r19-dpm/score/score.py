#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r19-dpm's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 50606dc1cd12, pinned in FROZEN.commits);
q107_rule.py (closing12 c3-q107, frozen there) is read at the frozen data commit (gen/pins.py).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed (dza on
                                       dzl, zs on zsc)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Controls of a stage: its control rows, and the premise of every geometry row (PREMISE: the kick
overflowed, the final did not, 0x0624 = 0xde after it; ld's zero rows also: page 6 held lists
after render 1, before the fill). Every model's headline is gated by all of them.

  ld   H-NOLOAD: a zero row's final param dump, 0x0730 and 0x0660 and target hash equal its base
       twin's; H-LOAD: the param dump or the counts differ. Control: the 0x28 base pair repeat
       (param, TA data, target hash).
  ldb  the state page (TA data 0x42000, E627) of tri.1: sum of the 16 macrotile counts against
       the last run's peak status - 1 (R-PEAK), thr0 - 1 (R-THR), within 3 (R-NEAR); thr0 and
       the peaks as dpm_raise.py's runs(). Controls (0xc0, 0x100): not raised and R-THR.
  dz   dl: idx_hi (final store dwords past tile row 11 that hold their index) > 0 H-PRPATH, 0
       H-HOSTBITS (no-load rows); z1_lo (zeros below row 12 in depth.1, index 0 aside) > 0
       H-PRZERO, 0 H-CLRREAD. bg: diff 0 H-WHOLE, > 0 H-LOSS. ov: of the partial render's
       triangle dwords past row 11 (depth.1 not the fill, the clear or 0), the share the final's
       store keeps: >= 0.5 H-PRLOAD, <= 0.05 H-OWNCLEAR.
  zs   G 33 rows: sign bits past row 11 in depth.1 (> 0 when raised at 0x28, else 0), none in
       depth.2 and no zero below row 12 in depth.2 (H-PRSIGN); sign in depth.2 when raised
       (H-FINALSIGN). G 1 rows: q107_rule's RULE on depth.2 against the G 33 twin's (H-E996: every
       scored dword, 64512 less those past the G 33 window; E1020: fewer). Controls: the -n 1 0x422 pair, RULE on depth.1.
  rd   the G of depth.1's layout: 33 when any dword at slot 127 or above is not the fill, else 1;
       H-RD: render 1's G; H-FW-CONST: 1; H-FW-FINAL: render 2's G.

REQUIRED: the files the scorer reads, per row (every row of a stage writes them: dz and zs are
split into stages by their dumps, gen/plan.py tables()). read_files(STAGE, DIR) reads
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
    "ld": (".txt", ".tri.param.bin", ".tri.tadata.bin", ".tri.1.tadata.bin") + FIXED,
    "ldb": (".txt", ".tri.1.tadata.bin", ".ta3d.1.bin") + FIXED,
    "dzl": (".txt", ".depth.1.bin") + FIXED,
    "dza": (".txt", ".depth.1.bin", ".depth-store.2.bin") + FIXED,
    "dzc": (".txt", ".depth.1.bin") + FIXED,
    "dzo": (".txt", ".depth.1.bin", ".depth.2.bin") + FIXED,
    "zsc": (".txt", ".depth.1.bin") + FIXED,
    "zs": (".txt", ".depth.1.bin", ".depth.2.bin") + FIXED,
    "rd": (".txt", ".depth.1.bin", ".depth.2.bin") + FIXED,
}
GATES = PL.GATES
Q107 = "data:cited/closing12/plan/c3-q107/q107_rule.py"
CLEAR = 0x3F800000


def producible(row):
    a = row["args"].split()
    keys = {"ovf1", "ovf2", "thr", "diff", "nparts", "peak"} if "tri" in a else set()
    if "--depth-store" in a:
        keys.add("sidx")
    if "--bg-layer" in a:
        keys.add("inplace")
    return keys


# ---- the text: run/hooks.sh's rd_words in Python ------------------------------------------------
def words(text):
    o, thr, sidx, diff, inpl = {}, None, None, None, None
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
    for k, v in (("thr", thr), ("sidx", sidx), ("diff", diff), ("inplace", inpl)):
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


def last_regs(text):
    """{offset: value} of the last --regs block."""
    out = {}
    for ln in (text or "").splitlines():
        if ln.startswith("regs: 0x"):
            out = {}
        elif ln.startswith("reg 0x"):
            f = ln.split()
            out[int(f[1], 16)] = int(f[2], 16)
    return out


def target_hash(text):
    h = re.findall(r"^target: \S+ hash (0x[0-9a-f]+)", text or "", re.M)
    return h[-1] if h else None


def dwords(b):
    return None if b is None else struct.unpack("<%dI" % (len(b) // 4), b[:len(b) // 4 * 4])


def _st(s):
    return "PASS" if s else "FAILED" if s is False else "cannot tell"


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

    def text(self, n):
        return K.text(self.d, n + ".txt") if self.done(n) else None

    def dump(self, n, suffix):
        if (n, suffix) not in self.seen:
            self.seen[(n, suffix)] = (K._read(os.path.join(self.d, n + suffix))
                                      if self.done(n) else None)
        return self.seen[(n, suffix)]


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


def _cmp(v, rule):
    """A count against a frozen '>0', '0', '>=1' ..."""
    if v is None:
        return None
    return {">0": v > 0, "0": v == 0, ">=1": v >= 1}[rule]


# ---- ld ----------------------------------------------------------------------------------------
def page6_nonzero(b):
    d = dwords(b)
    return None if d is None or len(d) < 0x7000 // 4 else sum(1 for x in d[0x1800:0x1C00] if x)


def _ld(r, controls, per_model, lines):
    a, b = "ld-b28-1", "ld-b28-2"
    rep = None
    if r.done(a) and r.done(b):
        rep = all(r.dump(a, s) is not None and r.dump(a, s) == r.dump(b, s)
                  for s in (".tri.param.bin", ".tri.tadata.bin")) and \
            target_hash(r.text(a)) == target_hash(r.text(b)) is not None
    for n in (a, b):
        p, t = premise(r, n)
        controls[n] = None if p is None or rep is None else (p and rep)
        lines.append(f"CONTROL {n}: premise {t}; the pair repeats (param, TA data, target "
                     f"hash): {rep}: {_st(controls[n])}")
    for n, m in r.meta.items():
        if not m.get("zero"):
            if m["set"] != "control":
                p, t = premise(r, n)
                controls[f"premise:{n}"] = p
                lines.append(f"CONTROL premise:{n}: {t}: {_st(p)}")
            continue
        p, t = premise(r, n)
        pg = page6_nonzero(r.dump(n, ".tri.1.tadata.bin"))
        controls[f"premise:{n}"] = None if p is None or pg is None else (p and pg >= 1)
        lines.append(f"CONTROL premise:{n}: {t}, page 6 before the fill {pg} non-zero dwords: "
                     f"{_st(controls[f'premise:{n}'])}")
        tw = m["twin"]
        res = {}
        if not (r.done(n) and r.done(tw)):
            res = {"H-NOLOAD": (None, "not run"), "H-LOAD": (None, "not run")}
        else:
            sp = r.dump(n, ".tri.param.bin") == r.dump(tw, ".tri.param.bin")
            ra, rb = last_regs(r.text(n)), last_regs(r.text(tw))
            sc = all(ra.get(o) is not None and ra.get(o) == rb.get(o) for o in (0x730, 0x660))
            si = target_hash(r.text(n)) == target_hash(r.text(tw))
            ta, tb = dwords(r.dump(n, ".tri.tadata.bin")), dwords(r.dump(tw, ".tri.tadata.bin"))
            out6 = None if ta is None or tb is None else sum(
                1 for i, (x, y) in enumerate(zip(ta, tb)) if x != y and not 0x1800 <= i < 0x1C00)
            lines.append(f"READING {n}: TA data dwords off the twin outside page 6: {out6}; page 6 "
                         f"after the job {page6_nonzero(r.dump(n, '.tri.tadata.bin'))} non-zero")
            t = f"param {sp}, counts {sc}, image {si}"
            res = {"H-NOLOAD": (sp and sc and si, t), "H-LOAD": ((not sp) or (not sc), t)}
        _row(lines, per_model, n, res)


# ---- ldb ---------------------------------------------------------------------------------------
def _ldb(r, controls, per_model, lines):
    for n, m in r.meta.items():
        txt = r.text(n)
        col, rows = timeline(txt)
        sp = dwords(r.dump(n, ".tri.1.tadata.bin"))
        w38 = dwords(r.dump(n, ".ta3d.1.bin"))
        if txt is None or col is None or "0x0658" not in col or sp is None or len(sp) < 0x42088 // 4 \
                or w38 is None or len(w38) < 39:
            tot = thr0 = peak = raised = None
        else:
            prs, peaks = runs(rows, col)
            tot = sum(sp[0x42000 // 4 + 2 * i] >> 16 for i in range(16))
            thr0 = prs[0] if prs else None
            peak = peaks[-1]
            raised = w38[38] == 0x20
        ovf = words(txt).get("ovf1") if txt else None
        t = f"sum {tot}, thr0 {thr0}, last peak {peak}, raised {raised}, ovf1 {ovf}"
        if m["set"] == "control":
            s = None if None in (tot, thr0, raised) else (ovf == "1" and not raised and tot == thr0 - 1)
            controls[n] = s
            lines.append(f"CONTROL {n}: R-THR not raised ({t}): {_st(s)}")
            continue
        ok = None if None in (tot, thr0, peak) else True
        res = {"R-PEAK": (ok and tot == peak - 1, t), "R-THR": (ok and tot == thr0 - 1, t),
               "R-NEAR": (ok and abs(tot - (peak - 1)) <= 3, t),
               "E625-raised": (None if raised is None else raised == m["raised"], t)}
        _row(lines, per_model, n, res)


# ---- dz ----------------------------------------------------------------------------------------
def _dz(r, controls, per_model, lines):
    for n, m in r.meta.items():
        txt = r.text(n)
        w = words(txt) if txt else {}
        if m["set"] == "control":
            if m["form"] == "dl":
                want = str(int(m["ctl"] == PL.LD33))
                s = None if txt is None or "sidx" not in w else (w.get("ovf1") == "0" and w["sidx"] == want)
                lines.append(f"CONTROL {n}: ovf1 {w.get('ovf1')}, sidx {w.get('sidx')} (frozen 0, "
                             f"{want}): {_st(s)}")
            else:
                s = None if txt is None or "diff" not in w else (w.get("ovf1") == "0" and w["diff"] == "0")
                lines.append(f"CONTROL {n}: ovf1 {w.get('ovf1')}, diff {w.get('diff')}, layer "
                             f"texels in place {w.get('inplace')} (frozen 0, 0): {_st(s)}")
            controls[n] = s
            continue
        if m.get("geo"):
            p, t = premise(r, n)
            controls[f"premise:{n}"] = p
            lines.append(f"CONTROL premise:{n}: {t}: {_st(p)}")
        if m["form"] == "bg":
            d = None if txt is None or "diff" not in w else int(w["diff"])
            controls[f"premise:{n}"] = None if txt is None else w.get("ovf1") == "1"
            lines.append(f"CONTROL premise:{n}: ovf1 {w.get('ovf1')}: {_st(controls[f'premise:{n}'])}")
            res = {"H-WHOLE": (_cmp(d, "0"), f"diff {d}"), "H-LOSS": (_cmp(d, ">0"), f"diff {d}")}
        elif m["form"] == "dl":
            st, d1 = dwords(r.dump(n, ".depth-store.2.bin")), dwords(r.dump(n, ".depth.1.bin"))
            hi = None if st is None else sum(1 for i in range(PL.ROW12, len(st)) if st[i] == i)
            anyi = None if st is None else sum(1 for i, v in enumerate(st) if v == i and i)
            z1 = None if d1 is None else sum(1 for v in d1[1:PL.ROW12] if v == 0)
            t = f"idx_hi {hi}, idx_any {anyi}, z1_lo {z1}"
            if m["ctl"] == PL.NL33:
                res = {"H-PRPATH": (_cmp(hi, ">0"), t), "H-HOSTBITS": (_cmp(hi, "0"), t)}
            else:
                res = {"H-PRPATH": (_cmp(anyi, ">0"), t), "H-HOSTBITS": (_cmp(anyi, ">0"), t)}
            res["H-PRZERO"] = (_cmp(z1, ">0"), t)
            res["H-CLRREAD"] = (_cmp(z1, "0"), t)
        else:
            d1, d2 = dwords(r.dump(n, ".depth.1.bin")), dwords(r.dump(n, ".depth.2.bin"))
            if d1 is None or d2 is None:
                t1 = k1 = None
            else:
                idx = [i for i in range(PL.ROW12, min(len(d1), len(d2)))
                       if d1[i] not in (m["fill"], CLEAR, 0)]
                t1, k1 = len(idx), sum(1 for i in idx if d2[i] == d1[i])
            t = f"kept1 {k1} of t1 {t1}"
            ok = None if not t1 else True
            res = {"H-PRLOAD": (ok and k1 >= 0.5 * t1, t), "H-OWNCLEAR": (ok and k1 <= 0.05 * t1, t)}
        _row(lines, per_model, n, res)


# ---- zs ----------------------------------------------------------------------------------------
def rule_hits(g1, g33):
    """q107_rule.py's RULE: (equal dwords, scored dwords) of a G 1 dump against its G 33 twin.
    As q107_score.py (E1020): a dword whose source tile lies past the G 33 dump's window is
    cannot tell and left out of both counts (the dump padded with None)."""
    import pins
    q = pins.module(Q107, "q107_rule")
    pred = {i: v for i, v in q.predict(tuple(g33) + (None,) * (1700 * 512), q.W, q.H, 1,
                                       "RULE").items() if v is not None}
    return sum(1 for i, v in pred.items() if i < len(g1) and g1[i] == v), len(pred)


def _zs(r, controls, per_model, lines):
    for n, m in r.meta.items():
        txt = r.text(n)
        w = words(txt) if txt else {}
        if m["set"] == "control":
            s = None if txt is None or "ovf1" not in w else w["ovf1"] == "0"
            t = f"ovf1 {w.get('ovf1')}"
            if m["twin"]:
                a, b = dwords(r.dump(n, ".depth.1.bin")), dwords(r.dump(m["twin"], ".depth.1.bin"))
                hit = None if a is None or b is None else rule_hits(a, b)
                t += f", RULE {hit}"
                s = None if hit is None or s is None else (s and hit[0] == hit[1])
            controls[n] = s
            lines.append(f"CONTROL {n}: {t}: {_st(s)}")
            continue
        p, t = premise(r, n)
        controls[f"premise:{n}"] = p
        lines.append(f"CONTROL premise:{n}: {t}: {_st(p)}")
        d1, d2 = dwords(r.dump(n, ".depth.1.bin")), dwords(r.dump(n, ".depth.2.bin"))
        if m["g"] == 33:
            raised = m["p"] == 0x28
            if d1 is None or d2 is None:
                res = {"H-PRSIGN": (None, "no dump"), "H-FINALSIGN": (None, "no dump")}
            else:
                s1 = sum(1 for v in d1[PL.ROW12:] if v >> 31)
                s2 = sum(1 for v in d2 if v >> 31)
                z2 = sum(1 for v in d2[:PL.ROW12] if v == 0)
                t = f"sign1_hi {s1}, sign2 {s2}, zero2_lo {z2}"
                res = {"H-PRSIGN": ((s1 > 0) == raised and s2 == 0 and z2 == 0, t),
                       "H-FINALSIGN": ((s2 > 0) == raised, t)}
        else:
            tw = dwords(r.dump(m["twin"], ".depth.2.bin"))
            hit = None if d2 is None or tw is None else rule_hits(d2, tw)
            t = f"RULE {hit}"
            res = {"H-E996": (None if hit is None else hit[0] == hit[1], t),
                   "E1020": (None if hit is None else hit[0] < hit[1], t)}
        _row(lines, per_model, n, res)


# ---- rd ----------------------------------------------------------------------------------------
def g_layout(d, fill):
    return None if d is None else 33 if any(v != fill for v in d[512 * PL.G1_SLOTS:]) else 1


def _rd(r, controls, per_model, lines):
    for n, m in r.meta.items():
        p, t = premise(r, n)
        controls[f"premise:{n}"] = p
        lines.append(f"CONTROL premise:{n}: {t}: {_st(p)}")
        g1 = g_layout(dwords(r.dump(n, ".depth.1.bin")), m["fill"])
        g2 = g_layout(dwords(r.dump(n, ".depth.2.bin")), m["fill"])
        t = f"depth.1 layout G {g1} (render 1 G {m['g1']}, render 2 G {m['g2']}); depth.2 G {g2}"
        res = {"H-RD": (None if g1 is None else g1 == m["g1"], t),
               "H-FW-CONST": (None if g1 is None else g1 == 1, t),
               "H-FW-FINAL": (None if g1 is None else g1 == m["g2"], t)}
        _row(lines, per_model, n, res)


SCORERS = {"ld": _ld, "ldb": _ldb, "dzl": _dz, "dza": _dz, "dzc": _dz, "dzo": _dz, "zsc": _zs,
           "zs": _zs, "rd": _rd}


def verdicts(stage, d, roots=None):
    r = Run(stage, d)
    controls, per_model, lines = {}, {}, []
    SCORERS[stage](r, controls, per_model, lines)
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
