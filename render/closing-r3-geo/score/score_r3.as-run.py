#!/usr/bin/env python3
"""score_r3.py STAGE KEPTDIR [--ctl DIR]: score one R3 stage from its kept files.

  STAGE    g-da g-db g-dc g-dd g-c4 g-d36 g-c6 g-c5 g-c7
  KEPTDIR  out/STAGE (copied from the laptop's ~/r3g-out/STAGE): cases.tsv (rc, class, the P actually written), NAME.txt.gz,
           dumps, regs files
  --ctl    the kept directory of g-c4 (default: the sibling out/g-c4): the DPM stages after g-c4 take their controls and the
           measured 2048x2048 limit from it
Refuses to run unless `run/freeze_r3.sh verify` passes.  Prints the per-job table and one `SUMMARY:` line.  Run with the scratch venv
(numpy is not needed here): PYTHONDONTWRITEBYTECODE=1 .venv/bin/python score/score_r3.py g-c4 out/g-c4

Rules (as R1 and R2): a job with no output, an rc that is not a result of the tool, a missing dump, a skipped class, or a knob that did
not land is NODATA, tested before any match; a failing control makes the group `cannot tell`; held-out and replicate rows are tallied
apart from repeats; every scorer ends with one `SUMMARY:` line naming the hypothesis and the count.  Depth stages read the stored depth
word of every vertex; DPM stages read the raise (dword 38 of the control block), the cells the runner picked (re-derived here: a pick
that is not the midpoint of the kept observations is flagged) and the H-last side table (dword 36 against the count before the LAST
abort), never gating except in g-d36.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import pathlib  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "gen"))
import dpm3  # noqa: E402
import r3models as M  # noqa: E402
import score_geo2 as G  # noqa: E402
import score_r2 as S2  # noqa: E402
from r1lib import Kept, load_preds, table  # noqa: E402

R3 = HERE.parent
LT_C2048 = 0xd4                    # LT's frozen last raise at 2048x2048 (thr0); C = 0xf4
C2048_BRACKET = (0xc0, 0x100)      # E785: raise at thr0 0xc0, none at 0x100
DEPTH_STAGES = ("g-da", "g-db", "g-dc", "g-dd")


# ------------------------------------------------------------------------------------------------ tables, depth words
def table_rows(stage, tables=None):
    out = []
    for ln in (pathlib.Path(tables or R3 / "tables") / f"{stage}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            f = ln.split("|", 6)
            out.append(dict(name=f[0], set=f[1], P=f[3], knobs=f[4].split(), args=f[6]))
    return out


def knob(row, key):
    return next((k.split(":", 1)[1] for k in row["knobs"] if k.startswith(key + ":")), None)


def stored_word(d):
    """The one stored depth word of a decoded object (all vertices alike), or None."""
    if d["state"] != "present":
        return None
    ws = {z for _, _, z in d["packed"]}
    return next(iter(ws)) if len(ws) == 1 else None


def _with_extra(text, lines):
    return text.replace("\nSUMMARY", "\n" + "\n".join(lines) + "\nSUMMARY") if lines else text


def pred_one(preds, n, q):
    return next((v for v, m, s in preds.get(n, {}).get(q, [])), None)


# ------------------------------------------------------------------------------------------------ g-da
def score_da(k: Kept, preds):
    text, _ = S2.score_objects2(k, preds, "g-da")
    dec, _, _ = G.decode_all(k)
    rows, lines = [], []
    out_ok, out_n, inside = 0, 0, []
    for n, d in dec.items():
        kind = pred_one(preds, n, "cell")
        if kind not in ("outside-lo", "outside-mid", "outside-hi", "above-half", "inside"):
            continue
        w = stored_word(d)
        down, up = pred_one(preds, n, "word_down"), pred_one(preds, n, "word_up")
        dirn = "none" if w is None else "down" if w == int(down, 16) else "up" if w == int(up, 16) else "other"
        fr = float(pred_one(preds, n, "frac"))
        rows.append((n, kind, f"{fr:.4f}", f"0x{w:08x}" if w is not None else d["state"], dirn))
        if kind == "inside":
            inside.append((fr, dirn))
        else:
            want = "down" if kind in ("outside-lo", "outside-mid") else "up"
            out_n += 1
            out_ok += dirn == want
    if rows:
        lines += ["g-da: direction of the stored word per cell (down = RZ of the product, up = one ulp above it)",
                  table(sorted(rows, key=lambda r: float(r[2])), ["job", "cell", "frac", "word", "direction"])]
    inside.sort()
    seq = [dr for _, dr in inside]
    flips = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    mono = all(not (a == "up" and b == "down") for a, b in zip(seq, seq[1:]))
    other = [dr for _, dr in inside if dr not in ("down", "up")]
    verdict = None
    if out_n and "controls pass" in text:
        if out_ok < out_n:
            verdict = f"H-thr REFUTED: {out_n - out_ok} of {out_n} outside cells off the frozen direction (low and mid down, high and above half up)"
        elif other or len(inside) < 10:
            verdict = f"H-thr: the outside cells hold ({out_ok} of {out_n}); {len(inside)} inside cells readable, {len(other)} neither neighbour: cannot tell for the interval"
        elif not mono:
            verdict = "H-thr REFUTED: the inside cells are not monotone along the fraction (the fraction is not the variable)"
        else:
            down = [f for f, dr in inside if dr == "down"]
            up = [f for f, dr in inside if dr == "up"]
            iv = f"t in ({max(down):.4f}, {min(up):.4f}]" if down and up else (
                "all inside cells down: t at or above 0.4667" if down else "all inside cells up: t at or below 0.37")
            verdict = f"H-thr HOLDS: outside {out_ok} of {out_n}, inside monotone with {flips} flip(s); {iv}"
    if verdict:
        lines.append(verdict)
    return _with_extra(text, lines).replace("SUMMARY: controls pass;", f"SUMMARY: controls pass; {verdict};" if verdict else "SUMMARY: controls pass;"), {}


# ------------------------------------------------------------------------------------------------ g-db, g-dc, g-dd
def _words_lines(k, preds, title):
    dec, _, _ = G.decode_all(k)
    lines = [f"{title}: stored word per job (models giving it)"]
    for n, d in dec.items():
        w = stored_word(d)
        if w is None:
            continue
        pr = [m.split(" ")[0] for v, m, s in preds.get(n, {}).get("depth_words", []) if v == ",".join([f"0x{w:08x}"] * 3)]
        lines.append(f"  {n}: 0x{w:08x} <- {pr or 'no candidate'}")
    return lines if len(lines) > 1 else []


def _tally_nocontrol(k: Kept, preds, title):
    """S2.score_objects2 for a stage with no control job of its own: every held-out row is tallied per model label."""
    dec, rows, void = G.decode_all(k)
    hit = {n: S2.hits2(preds, n, d) for n, d in dec.items()}
    out = [f"{title}: object decode per job", table(rows, ["job", "object", "nvert", "x,y (pixels)", "1/w words"]), ""]
    entries = []
    for n in preds:
        for q, lst in preds[n].items():
            for v, m, s in lst:
                if s in ("heldout", "replicate", "repeat") and (q, m) in hit.get(n, {}):
                    entries.append((m, s, hit[n][(q, m)]))
                elif s in ("heldout", "replicate", "repeat") and n not in dec and q == "depth_words":
                    entries.append((m, s, None))
    miss = [n for n in preds if n not in dec]
    return out, entries, void, miss


def _depth_gate(ctl_dir):
    """g-da's controls as g-db's: (ok, message).  g-da's own scorer must say `controls pass`."""
    if not ctl_dir or not pathlib.Path(ctl_dir, "cases.tsv").exists():
        return False, "g-da's kept directory is missing (its controls are the controls of g-db)"
    text = score_da(Kept(ctl_dir), load_preds(None, "g-da"))[0]
    if "controls pass" not in summary_of(text):
        return False, "g-da's controls failed: " + summary_of(text)[:160]
    return True, ""


def summary_of(text):
    return next((ln for ln in text.splitlines() if ln.startswith("SUMMARY:")), "no SUMMARY")


def score_db(k, preds, ctl_dir=None):
    ok, msg = _depth_gate(ctl_dir)
    if not ok:
        return f"SUMMARY: cannot tell: {msg}", {}
    out, entries, void, miss = _tally_nocontrol(k, preds, "g-db")
    out += _words_lines(k, preds, "g-db")
    out.append("SUMMARY: controls pass (g-da's); " + S2.support(entries) + (f"; void jobs {void}" if void else "") + (f"; not run {miss}" if miss and not void else ""))
    return "\n".join(out), {}


def score_dc(k, preds):
    text, _ = S2.score_objects2(k, preds, "g-dc")
    return _with_extra(text, _words_lines(k, preds, "g-dc")), {}


def score_dd(k, preds):
    """The four made-vertex jobs: no frozen control job; the structure (set, order, prims, window position) of each object is the
    control (E782's rules held out again): a job whose structure fails is reported and its made depth words are not read."""
    dec, rows, void = G.decode_all(k)
    hit = {n: S2.hits2(preds, n, d) for n, d in dec.items()}
    lines = ["g-dd: per job (structure = nvert, xy_set, xy_ordered, prims; then the made vertices' 1/w and depth words)"]
    struct_ok, made = {}, []
    for n, d in dec.items():
        sq = [(q, m) for q, lst in preds.get(n, {}).items() for v, m, s in lst if q in ("object", "nvert", "xy_set", "xy_ordered", "prims")]
        ok = d["state"] == "present" and all(hit[n].get(qm) is not False for qm in sq)
        struct_ok[n] = ok
        if d["state"] != "present":
            lines.append(f"  {n}: {d['state']}")
            continue
        entries = S2._entries(pred_one(preds, n, "depth_made_by_xy") or "")
        got = S2.by_xy(d, entries)
        words = [f"0x{z:08x}" if z is not None else "-" for _, _, z in got]
        rh = [f"0x{g:08x}" if g is not None else "-" for _, g, _ in got]
        lines.append(f"  {n}: structure {'ok' if ok else 'FAILED'}; made vertices' depth words {words} (HDP-made: 1.0 / 0.0 exactly), 1/w words {rh}")
        if ok:
            made.append(all(z is not None and z == w for w, _, z in got))
    ent = []
    for n, d in dec.items():
        for q, lst in preds.get(n, {}).items():
            for v, m, s in lst:
                if s == "heldout" and (q, m) in hit[n] and (q != "depth_made_by_xy" or struct_ok[n]):
                    ent.append((m, s, hit[n][(q, m)]))
    nok = sum(struct_ok.values())
    if not dec:
        return "\n".join(lines + [f"SUMMARY: cannot tell: no readable job; void jobs {void}"]), {}
    s = (f"SUMMARY: structure (the control) holds in {nok} of {len(dec)} jobs; " + S2.support(ent)
         + f"; made depth exactly 1.0 / 0.0 in {sum(made)} of {len(made)} readable jobs (E782 refuted it at 1 of 4 vertices)"
         + (f"; void jobs {void}" if void else ""))
    if nok < len(dec):
        s = s.replace("SUMMARY:", "SUMMARY: cannot tell for the failed jobs:")
    return "\n".join(lines + [s]), {}


# ------------------------------------------------------------------------------------------------ DPM stages
def _P_thr0(j):
    return j["knob"] if not j.get("void") else None


def read_all(k: Kept, rows):
    """{name: reading} for every row the runner kept (a skipped or missing row has class skipped / no entry)."""
    out = {}
    for r in rows:
        c = k.case(r["name"])
        if not c:
            out[r["name"]] = dict(void="not run", P="-", skipped=False)
        elif c.get("class") == "skipped":
            out[r["name"]] = dict(void="skipped: " + c.get("note", ""), P=c.get("P", "-"), skipped=True)
        else:
            out[r["name"]] = dpm3.read_job(k, r["name"])
    return out


def group_obs(rd, rows, G_):
    """{thr0: class} over the usable jobs of the rows with knob obs:G_ (table order), and the list [(name, thr0, class)]."""
    obs, seq = {}, []
    for r in rows:
        if knob(r, "obs") != G_:
            continue
        j = rd[r["name"]]
        if j.get("void") and j.get("skipped"):
            continue
        t = (int(j["P"], 16) - 0x22) if j.get("P", "-") not in ("-", "") else None
        if t is None:
            continue
        c = dpm3.cls_of(j) if not j.get("void") else "V"
        seq.append((r["name"], t, c))
        obs[t] = c
    return obs, seq


def check_picks(rows, rd, G_):
    """The rows named B:G_ must each be the midpoint of the observations of the rows before them in the group; returns the
    names that are not."""
    off, obs = [], {}
    for r in rows:
        if knob(r, "obs") != G_:
            continue
        j = rd[r["name"]]
        if j.get("skipped") or j.get("P", "-") in ("-", ""):
            continue
        t = int(j["P"], 16) - 0x22
        if r["P"] == f"B:{G_}":
            want, why = dpm3.pick(obs)
            if want != t:
                off.append(f"{r['name']} (thr0 {t:#x}, midpoint {want if want is None else hex(want)} {why})")
        obs[t] = dpm3.cls_of(j) if not j.get("void") else "V"
    return off


def controls_state(rd, rows):
    """([control rows that failed, are void or were not run], [rows that pass]): a control (knob ctl:R or ctl:N) must be valid and read
    its raise."""
    bad, good = [], []
    for r in rows:
        want = knob(r, "ctl")
        if want is None:
            continue
        j = rd[r["name"]]
        ok = not j.get("void") and j["valid"] and j["raised"] == (want == "R")
        (good if ok else bad).append(r["name"])
    return bad, good


def hlast_table(k: Kept, rd, rows):
    """H-last side table: per job with 0x072c sampled: counts before each abort, predicted, dword 36, separating flag.  Returns
    (lines, tallies dict)."""
    out, tal = [], dict(n=0, ok=0, sep=0, sep_ok=0, amb=0)
    for r in rows:
        j = rd[r["name"]]
        if j.get("void") or j.get("cnt") is None:
            continue
        c = j["cnt"]
        pred = M.hlast(c["before"])
        ok = pred == j["dw36"]
        first, last = (c["before"][0], c["before"][-1]) if c["before"] else (None, None)
        second = c["before"][1] if len(c["before"]) > 1 else first
        fl = lambda v: max(v - 2, 0)
        sep = bool(c["before"]) and (fl(last) != fl(c["peak"]) or fl(last) != fl(second))
        tal["n"] += 1
        tal["ok"] += ok
        tal["sep"] += sep
        tal["sep_ok"] += sep and ok
        tal["amb"] += c["amb"]
        out.append((r["name"], c["before"], c["peak"], pred, j["dw36"], "SEP" if sep else "", "ok" if ok else "MISS"))
    lines = []
    if out:
        lines = ["H-last side table: dword 36 = max(count before the LAST abort - 2, 0); SEP = H-last's value differs from the peak "
                 "reading's or the second-abort reading's (the jobs that separate H-last from them)",
                 table(out, ["job", "counts before aborts", "peak", "H-last", "dword 36", "", ""]),
                 f"H-last: {tal['ok']} of {tal['n']} jobs fit; separating jobs {tal['sep_ok']} of {tal['sep']}; "
                 f"jobs whose count changed in the two samples before the last edge: {tal['amb']}"]
    return lines, tal


def dpm_table(rd, rows, extra_cols=False):
    out = []
    for r in rows:
        j = rd[r["name"]]
        if j.get("void"):
            out.append((r["name"], r["set"], j.get("P", "-"), "-", "-", "-", "NODATA: " + str(j["void"])))
            continue
        thr0 = j["knob"]
        out.append((r["name"], r["set"], j["P"], f"{thr0:#x}", j["nparts"], [hex(p) for p in j["peaks"][:3]],
                    ("raise" if j["raised"] else "none") + ("" if j["valid"] else "  (void: second run does not reach thr0 or one abort)")))
    return table(out, ["job", "set", "P", "thr0", "parts", "peaks", "raise"])


def _flip_text(obs):
    lo, hi, kind = dpm3.flip_of(obs)
    return lo, hi, kind


def c2048_measured(ctl_dir, tables=None):
    """(clo, chi, kind) of the measured last raise thr0 at 2048x2048 from g-c4's kept files: exact (lo = hi - 1) or bracket."""
    k = Kept(ctl_dir)
    rows = table_rows("g-c4", tables)
    rd = read_all(k, rows)
    obs, _ = group_obs(rd, rows, "c4")
    lo, hi, kind = dpm3.flip_of(obs)
    return lo, hi, kind, rd, rows, k


def _c4_controls_gate(rd, rows):
    bad, good = controls_state(rd, rows)
    return bad, good


def score_c4(k: Kept, preds, tables=None):
    rows = table_rows("g-c4", tables)
    rd = read_all(k, rows)
    out = ["g-c4: per job (the 0x0624 of the job itself is the knob proof)", dpm_table(rd, rows), ""]
    hl, _ = hlast_table(k, rd, rows)
    out += hl
    bad, good = controls_state(rd, rows)
    obs, seq = group_obs(rd, rows, "c4")
    out.append("c4 observations: " + " ".join(f"{t:#x}:{c}" for t, c, in sorted(obs.items())))
    off = check_picks(rows, rd, "c4")
    if off:
        out.append(f"PICK OFF THE RULE (the runner's choice is not the midpoint of the kept observations): {off}")
    if bad:
        out.append(f"SUMMARY: cannot tell: control(s) {bad} void or not as measured (4096x4096: 0x372 raise, 0x374 none; 2048x2048: 0xe2 raise, 0x122 none)")
        return "\n".join(out), {}
    lo, hi, kind = dpm3.flip_of(obs)
    skipped = [r["name"] for r in rows if rd[r["name"]].get("skipped")]
    tail = (f"; bisect ended early (skipped {skipped}: {rd[skipped[0]]['void']})" if skipped else "") + (f"; PICK OFF THE RULE {off}" if off else "")
    if kind == "exact":
        if lo == LT_C2048:
            v = f"LT HOLDS: last raise thr0 {lo:#x} (C {lo + 0x20:#x}), first silent {hi:#x}, exactly the frozen prediction (0xd4)"
        else:
            v = (f"LT REFUTED: exact flip, last raise thr0 {lo:#x} (C = {lo + 0x20:#x}), first silent {hi:#x}; LT said {LT_C2048:#x}; "
                 f"the measured C replaces it")
    elif kind == "bracket":
        inside = lo <= LT_C2048 < hi
        v = (f"bracket only: last raise in [{lo:#x}, {hi - 1:#x}], first silent {hi:#x}; LT's 0xd4 "
             + ("is still inside (cannot tell)" if inside else "is OUTSIDE: LT REFUTED"))
    elif kind == "not monotone":
        v = "the monotone form is REFUTED at this target: a silent cell below a raise (two flips)"
    elif kind == "no silent cell above":
        v = f"no silent cell above the last raise {lo:#x}: the flip is above the bracket (LT REFUTED: 0xd4 < {lo:#x})" if lo > LT_C2048 else "no flip seen: cannot tell"
    else:
        v = "no raise in any valid cell: the flip is below the bracket (LT REFUTED)" if kind == "no raise" else f"cannot tell ({kind})"
    out.append(f"SUMMARY: controls pass ({len(good)} of {len(good)}); {v}{tail}")
    return "\n".join(out), {}


def _ctl_gate(ctl_dir, tables=None):
    """Controls of g-c4 as the session control of the stages after it.  Returns (ok, message, (lo, hi, kind))."""
    if not ctl_dir or not pathlib.Path(ctl_dir, "cases.tsv").exists():
        return False, "g-c4's kept directory is missing (its controls are the session's)", (None, None, "none")
    lo, hi, kind, rd, rows, k = c2048_measured(ctl_dir, tables)
    bad, _ = controls_state(rd, rows)
    if bad:
        return False, f"g-c4's control(s) {bad} failed or void", (lo, hi, kind)
    return True, "", (lo, hi, kind)


def score_d36(k: Kept, preds, ctl_dir=None, tables=None):
    rows = table_rows("g-d36", tables)
    rd = read_all(k, rows)
    out = ["g-d36: per job", dpm_table(rd, rows), ""]
    hl, tal = hlast_table(k, rd, rows)
    out += hl
    ok, msg, _ = _ctl_gate(ctl_dir, tables)
    if not ok:
        out.append(f"SUMMARY: cannot tell: {msg}")
        return "\n".join(out), {}
    good_rows = [r for r in rows if not rd[r["name"]].get("void")]
    if tal["sep"] >= 3 and tal["sep_ok"] == tal["sep"]:
        v = f"H-last HOLDS: all {tal['sep']} separating jobs fit ({tal['ok']} of {tal['n']} jobs)"
    elif tal["sep"] and tal["sep_ok"] < tal["sep"]:
        v = f"H-last REFUTED: {tal['sep'] - tal['sep_ok']} of {tal['sep']} separating jobs miss"
    else:
        v = f"cannot tell: only {tal['sep']} separating job(s) (3 needed); {tal['ok']} of {tal['n']} fit"
    out.append(f"SUMMARY: controls pass (g-c4's); {v}; usable jobs {len(good_rows)} of {len(rows)}")
    return "\n".join(out), {}


def score_c6(k: Kept, preds, ctl_dir=None, tables=None):
    rows = table_rows("g-c6", tables)
    rd = read_all(k, rows)
    out = ["g-c6: per job", dpm_table(rd, rows), ""]
    hl, _ = hlast_table(k, rd, rows)
    out += hl
    ok, msg, (lo, hi, kind) = _ctl_gate(ctl_dir, tables)
    if not ok:
        out.append(f"SUMMARY: cannot tell: {msg}")
        return "\n".join(out), {}
    cal = next((rd[r["name"]] for r in rows if knob(r, "cal")), None)
    note = ""
    if cal and not cal.get("void"):
        note = f"page need {cal['need']:#x} at P 0x422 ({cal['nparts']} partial renders)" + ("" if cal["need"] == 0x213 else "; NOT the 0x213 of the plain 2048x2048 context: the cells are a measurement")
    cells = [(r["name"], dpm3.cls_of(rd[r["name"]]), (int(rd[r["name"]]["P"], 16) - 0x22) if not rd[r["name"]].get("skipped") else None)
             for r in rows if knob(r, "cal") is None]
    use = [(n, c, t) for n, c, t in cells if c in ("R", "N") and t is not None]
    if kind != "exact" and kind != "bracket" or lo is None:
        out.append(f"SUMMARY: controls pass; cannot tell: g-c4 gave no flip ({kind}); {note}")
        return "\n".join(out), {}
    tgt = lambda t: "R" if t <= lo else "N"
    h_t = [c == tgt(t) for n, c, t in use]
    h_c = [c == "R" for n, c, t in use]
    if not use:
        v = "cannot tell: no valid cell"
    elif all(h_t) and not all(h_c):
        v = f"H-target HOLDS ({len(use)} of {len(use)} cells as g-c4's flip at {lo:#x}); H-context REFUTED"
    elif all(h_c) and not all(h_t):
        v = f"H-context HOLDS (raise at every valid cell: the 4096 limit); H-target REFUTED"
    elif all(h_t) and all(h_c):
        v = "cannot tell: every cell is on the same side for both"
    else:
        v = f"neither: cells {[(n, c) for n, c, t in use]}"
    out.append(f"SUMMARY: controls pass (g-c4's); {v}; {note}")
    return "\n".join(out), {}


def _interval(obs):
    """Last-raise interval [a, b] (thr0) from valid observations: lo..hi-1 for a flip; [max R, inf) all raise; (-inf, min N - 1]."""
    R = [t for t, c in obs.items() if c == "R"]
    N = [t for t, c in obs.items() if c == "N"]
    if R and N and max(R) < min(N):
        return max(R), min(N) - 1, "flip" if min(N) - max(R) > 1 else "exact"
    if R and N:
        return None, None, "not monotone"
    if R:
        return max(R), 10 ** 9, "above"
    if N:
        return -10 ** 9, min(N) - 1, "below"
    return None, None, "none"


def law_pred(law, w, h, c2048):
    """Last-raise thr0 interval (a, b) of a law at target (w, h); c2048 = (lo, hi) of the measured 2048x2048 last raise thr0
    (equal when exact)."""
    if law == "LT":
        v = M.lt_last_thr0(w, h)
        return v, v
    key = {"AR": "R", "AS": "side2", "AM": "mt"}[law]
    v = [M.affine_C(w, h, c + 0x20, key) - 0x20 for c in c2048]
    return min(v), max(v)


C5_TARGETS = {"c5a": (4096, 2048), "c5b": (2048, 4096), "c5c": (3072, 3072)}
LAWS = {"LT": "LT (the last raise thr0 proportional to the region count)",
        "AR": "affine in regions through the two exact points", "AS": "affine in the tail-pointer side squared",
        "AM": "affine in the macrotile area"}


def score_c5(k: Kept, preds, ctl_dir=None, tables=None):
    rows = table_rows("g-c5", tables)
    rd = read_all(k, rows)
    out = ["g-c5: per job", dpm_table(rd, rows), ""]
    hl, _ = hlast_table(k, rd, rows)
    out += hl
    ok, msg, (clo, chi, ckind) = _ctl_gate(ctl_dir, tables)
    if not ok:
        out.append(f"SUMMARY: cannot tell: {msg}")
        return "\n".join(out), {}
    c2 = (clo, chi - 1) if ckind in ("exact", "bracket") else None
    res, parts, verdicts = {}, [], {l: [] for l in LAWS}
    for g, (w, h) in C5_TARGETS.items():
        obs, seq = group_obs(rd, rows, g)
        off = check_picks(rows, rd, g)
        a, b, kind = _interval(obs)
        cal = next((rd[r["name"]] for r in rows if knob(r, "cal") == g), None)
        need = cal["need"] if cal and not cal.get("void") else None
        txt = f"{w}x{h}: " + " ".join(f"{t:#x}:{c}" for t, c in sorted(obs.items())) + (f" (page need {need:#x})" if need else "")
        if off:
            txt += f"; PICK OFF THE RULE {off}"
        if kind in ("none", "not monotone"):
            parts.append(txt + f" -> {'no valid cell' if kind == 'none' else 'not monotone: the monotone form is refuted at this target'}")
            res[g] = (None, None, kind)
            continue
        res[g] = (a, b, kind)
        lo_t = "-inf" if a < -10 ** 8 else hex(a)
        hi_t = "inf" if b >= 10 ** 8 else hex(b)
        parts.append(txt + f" -> last raise thr0 in [{lo_t}, {hi_t}] ({kind})")
        if c2 is None:
            continue
        for law in LAWS:
            pa, pb = law_pred(law, w, h, c2)
            hit = pb >= a and pa <= b                     # the law's range overlaps the measured interval
            sure = (pa == pb and a <= pa <= b)
            verdicts[law].append((g, "consistent" if hit else "REFUTED", pa, pb, sure))
    lines = []
    for law, v in verdicts.items():
        if v:
            lines.append(f"{LAWS[law]}: " + "; ".join(f"{g} {s} (predicts {hex(pa)}{'' if pa == pb else '..' + hex(pb)})" for g, s, pa, pb, _ in v))
    sep = ""
    ra, rb = res.get("c5a"), res.get("c5b")
    if ra and rb and ra[2] in ("exact", "flip") and rb[2] in ("exact", "flip"):
        sep = ("; 4096x2048 and 2048x4096 (equal regions) have DIFFERENT limits: every law in regions alone is REFUTED"
               if ra[:2] != rb[:2] and (ra[1] < rb[0] or rb[1] < ra[0]) else
               "; 4096x2048 and 2048x4096 (equal regions) have overlapping limits: regions alone not refuted")
    consistent = [l for l, v in verdicts.items() if v and all(s == "consistent" for _, s, _, _, _ in v) and len(v) == len(C5_TARGETS)]
    refuted = [l for l, v in verdicts.items() if any(s == "REFUTED" for _, s, _, _, _ in v)]
    out += parts + lines
    out.append(f"SUMMARY: controls pass (g-c4's); laws consistent with all three targets {consistent or 'none'}, refuted {refuted or 'none'}{sep}; "
               + ("2048x2048 limit from g-c4 " + (f"{clo:#x}" if ckind == "exact" else f"in [{clo:#x}, {chi - 1:#x}]") if c2 else "g-c4 gave no flip: laws not evaluated"))
    return "\n".join(out), res


def score_c7(k: Kept, preds, ctl_dir=None, tables=None):
    rows = table_rows("g-c7", tables)
    rd = read_all(k, rows)
    out = ["g-c7: per job", dpm_table(rd, rows), ""]
    hl, _ = hlast_table(k, rd, rows)
    out += hl
    ok, msg, (lo, hi, kind) = _ctl_gate(ctl_dir, tables)
    if not ok:
        out.append(f"SUMMARY: cannot tell: {msg}")
        return "\n".join(out), {}
    cal = next((rd[r["name"]] for r in rows if knob(r, "cal")), None)
    if not cal or cal.get("void"):
        out.append(f"SUMMARY: cannot tell: the calibration job is void ({cal and cal.get('void')})")
        return "\n".join(out), {}
    skipped = [r["name"] for r in rows if rd[r["name"]].get("skipped")]
    gate = f"calibration: page need {cal['need']:#x} at P 0x422, {cal['nparts']} partial renders (gate: at most 3)"
    if cal["nparts"] > 3:
        out.append(f"SUMMARY: gate closed ({gate}): the stage ended after one job; scene and target stay unseparated")
        return "\n".join(out), {}
    obs, _ = group_obs(rd, rows, "c7")
    off = check_picks(rows, rd, "c7")
    a, b, k7 = _interval(obs)
    if kind not in ("exact", "bracket"):
        out.append(f"SUMMARY: cannot tell: g-c4 gave no flip ({kind}); {gate}")
        return "\n".join(out), {}
    lo7, hi7, kind7 = dpm3.flip_of(obs)
    if kind7 == "exact":
        v = (f"H-target HOLDS: flip at {lo7:#x} / {hi7:#x} equals g-c4's {lo:#x}" if (lo7, hi7) == (lo, hi) else
             f"H-scene: the flip moved to last raise {lo7:#x} (g-c4: {lo:#x}); the limit follows the scene")
    elif kind7 == "bracket":
        v = (f"bracket [{lo7:#x}, {hi7 - 1:#x}] " + (f"contains g-c4's {lo:#x}: cannot tell" if lo7 <= lo < hi7 else f"excludes g-c4's {lo:#x}: H-scene"))
    elif a is not None and k7 in ("above", "below"):
        v = f"no flip among the valid cells ({k7}): last raise {'above' if k7 == 'above' else 'below'} the cells; " + (f"H-scene (g-c4's {lo:#x} is outside)" if not (a <= lo <= b) else "cannot tell")
    else:
        v = f"cannot tell ({kind7})"
    out.append(f"SUMMARY: controls pass (g-c4's); {v}; {gate}" + (f"; skipped {skipped}" if skipped else "") + (f"; PICK OFF THE RULE {off}" if off else ""))
    return "\n".join(out), {}


TABLE = {"g-da": score_da, "g-db": score_db, "g-dc": score_dc, "g-dd": score_dd, "g-c4": score_c4,
         "g-d36": score_d36, "g-c6": score_c6, "g-c5": score_c5, "g-c7": score_c7}


def run_stage(stage, kept_dir, preds_path=None, ctl_dir=None, tables=None):
    k = Kept(kept_dir)
    preds = load_preds(preds_path, stage) if (preds_path or (R3 / "predictions" / f"{stage}.tsv").exists()) else {}
    if stage in ("g-d36", "g-c6", "g-c5", "g-c7"):
        ctl = ctl_dir or str(pathlib.Path(kept_dir).resolve().parent / "g-c4")
        text, _ = TABLE[stage](k, preds, ctl, tables)
    elif stage == "g-c4":
        text, _ = score_c4(k, preds, tables)
    elif stage == "g-db":
        text, _ = score_db(k, preds, ctl_dir or str(pathlib.Path(kept_dir).resolve().parent / "g-da"))
    else:
        text, _ = TABLE[stage](k, preds)
    return text


def main(a):
    ctl = None
    if "--ctl" in a:
        i = a.index("--ctl")
        ctl = a[i + 1]
        a = a[:i] + a[i + 2:]
    if len(a) != 2 or a[0] not in TABLE:
        print(__doc__)
        return 2
    r = subprocess.run([str(HERE.parent / "run" / "freeze_r3.sh"), "verify"], capture_output=True, text=True)
    if r.returncode:
        print("REFUSING: the frozen files do not verify:\n" + r.stdout + r.stderr)
        return 3
    try:
        print(run_stage(a[0], a[1], None, ctl))
    except SystemExit as e:
        print(f"REFUSING: {e}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
