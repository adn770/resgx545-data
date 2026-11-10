#!/usr/bin/env python3
"""score_r2.py STAGE KEPTDIR: score one R2 stage from its kept files.

  STAGE    g-t3 g-t4 g-t5v g-c3 g-c3f g-c2
  KEPTDIR  out/STAGE (copied from the laptop's ~/r2-out/STAGE): cases.tsv (rc, class), NAME.txt.gz, dumps, regs files
Refuses to run unless `run/freeze_r2.sh verify` passes.  Prints the per-job table and one `SUMMARY:` line.
Run with the scratch venv (numpy is not needed here):
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python score/score_r2.py g-t5v out/g-t5v
Tests call `run_stage(...)` directly.  The readers and the C1-style raise measure are score_geo2.py's (R1, unchanged).

Rules (as R1): a job with no output, an rc that is not a result of the tool, a missing dump, a skipped class, or a knob that did
not land is NODATA, tested before any match; a failing control makes the group `cannot tell`; held-out and replicate rows are
tallied apart from repeats; every scorer ends with one `SUMMARY:` line naming the hypothesis and the count.
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
import score_geo2 as G  # noqa: E402
from r1lib import Kept, load_preds, peak_status, runs, support, table  # noqa: E402

C_R1 = 0x371                       # R1: the limit at 4096x4096 (raise iff thr0 + 0x20 <= C)
BASE = 0x3F200000                  # T5: the stored depth word of a loop of N iterations is BASE + N


def status2(txt):
    """CR_EVENT_STATUS2 (reg 0x0118) from a kept debugfs regs file, or None."""
    m = re.search(r"^reg 0x0118 (0x[0-9a-fA-F]+)", txt or "", re.M)
    return int(m[1], 16) if m else None


def regs_file(k: Kept, n, which):
    b = k._gz(f"{n}.{which}.regs.txt.gz")
    return b.decode(errors="replace") if b is not None else None


# ------------------------------------------------------------------------------------------------ T3, T4 (objects)
def _entries(v):
    """'x,y=0xw;...' -> [((x, y), word)]"""
    out = []
    for part in v.split(";"):
        if not part:
            continue
        pos, w = part.split("=")
        x, y = pos.split(",")
        out.append(((float(x), float(y)), int(w, 16)))
    return out


def by_xy(d, ents, tol=1 / 32):
    """For each predicted ((x, y), word) the stored vertex at that position: (stored rhw word, stored depth word) or None."""
    xy = G._xy(d)
    res = []
    for (px, py), w in ents:
        best = min(range(len(xy)), key=lambda i: abs(xy[i][0] - px) + abs(xy[i][1] - py))
        if abs(xy[best][0] - px) + abs(xy[best][1] - py) > 2 * tol:
            res.append((w, None, None))
        else:
            res.append((w, d["rhw"][best], d["packed"][best][2]))
    return res


def hits2(preds, n, d):
    """G.hits plus the T3 per-position quantities (rhw_by_xy exact / within 1 ulp by the model label, depth_made_by_xy)."""
    hit = G.hits(preds, n, d)
    for q in ("rhw_by_xy", "depth_made_by_xy"):
        for v, m, s in preds.get(n, {}).get(q, []):
            if d["state"] != "present":
                hit[(q, m)] = False
                continue
            got = by_xy(d, _entries(v))
            if q == "rhw_by_xy":
                tol1 = m.endswith("within 1 ulp")
                ok = all(g is not None and (abs(g - w) <= 1 if tol1 else g == w) for w, g, _ in [(a, b, c) for a, b, c in got])
            else:
                ok = all(z is not None and z == w for w, _, z in got)
            hit[(q, m)] = ok
    return hit


def score_objects2(k: Kept, preds, title):
    """G.score_objects with hits2 (the control rows' predictions must all hold; then the tally per model label)."""
    dec, rows, void = G.decode_all(k)
    hit = {n: hits2(preds, n, d) for n, d in dec.items()}
    out = [f"{title}: object decode per job", table(rows, ["job", "object", "nvert", "x,y (pixels)", "1/w words"]), ""]
    ctls = [n for n in preds if any(s == "control" for qs in preds[n].values() for v, m, s in qs)]
    need = lambda c: [(q, m) for q, lst in preds[c].items() for v, m, s in lst if s == "control" and v not in ("?", "")]
    failed = [c for c in ctls if c not in dec or any(hit[c].get(qm) is not True for qm in need(c))]
    if not ctls:
        return "\n".join(out + ["SUMMARY: cannot tell: no control row"]), {}
    if failed:
        return "\n".join(out + [f"SUMMARY: cannot tell: control(s) {failed} failed or void; void jobs {void}"]), {}
    entries = []
    for n in preds:
        if n in ctls:
            continue
        for q, lst in preds[n].items():
            for v, m, s in lst:
                if s in ("heldout", "replicate", "repeat"):
                    if v in ("?", "") or q == "object" and v.startswith(("monotone", "same")):
                        continue
                    entries.append((m, s, hit[n].get((q, m)) if n in dec else None))
    miss = [n for n in preds if n not in ctls and n not in dec]
    out.append("SUMMARY: controls pass; " + support(entries) + (f"; void jobs {void}" if void else "")
               + (f"; not run {miss}" if miss and not void else ""))
    return "\n".join(out), {}


def ulps(a, b):
    return b - a


def score_t3(k: Kept, preds):
    text, res = score_objects2(k, preds, "T3")
    dec, _, _ = G.decode_all(k)
    lines = []
    for n, d in dec.items():
        if n == "z-cut-p" or d["state"] != "present":
            continue
        for v, m, s in preds.get(n, {}).get("rhw_by_xy", []):
            if m.endswith("within 1 ulp") or m.startswith("HI-rhw"):
                continue
            got = by_xy(d, _entries(v))
            lines.append(f"{n}: stored 1/w minus {m.split(' ')[0]}'s word, per vertex: "
                         + " ".join("-" if g is None else f"{g - w:+d}" for w, g, _ in got))
    return text.replace("\nSUMMARY", "\n" + "\n".join(lines) + "\nSUMMARY") if lines else text, res


def score_t4(k: Kept, preds):
    """Candidates D1..D7: the controls must read their frozen word; the verdict is the candidate right in every usable
    pair (6 of 6), or `none` with the words recorded.  Side line: each pair's stored word and the candidates that give it."""
    text, res = score_objects2(k, preds, "T4")
    dec, _, _ = G.decode_all(k)
    lines = ["stored depth word per pair (candidates giving it):"]
    for n, d in dec.items():
        if d["state"] != "present" or n.startswith("t4-ctl"):
            continue
        ws = {f"0x{z:08x}" for _, _, z in d["packed"]}
        cands = [m.split(" ")[0] for v, m, s in preds.get(n, {}).get("depth_words", []) if v == ",".join([w for w in sorted(ws)] * 3)]
        lines.append(f"  {n}: {sorted(ws)} <- {cands or 'no candidate'}")
    return text.replace("\nSUMMARY", "\n" + "\n".join(lines) + "\nSUMMARY") if len(lines) > 1 else text, res


# ------------------------------------------------------------------------------------------------ T5v (the vertex loop)
def score_t5v(k: Kept, preds):
    dec, rows, void = G.decode_all(k)
    res, tab, first_set, seq, hang = {}, [], None, [], []
    ladder, skipped = [], []
    for n in k.names():
        c = k.case(n)
        m = re.fullmatch(r"t5v-(?:i|n)(\d+)", n)
        N = int(m[1]) if m else None
        pre, post = status2(regs_file(k, n, "pre")), status2(regs_file(k, n, "after"))
        if c.get("class") == "skipped":
            skipped.append(n)
            tab.append((n, N, "-", "-", "-", "skipped by the sweep stop (bit 7 already set)"))
            continue
        if c.get("class") in ("hang", "fault", "fail"):
            hang.append(f"{n} ({c.get('class')})")
            tab.append((n, N, "-", "-", "-", f"class {c.get('class')}"))
            continue
        v = k.void(n, ("param.bin", "tadata.bin"))
        if v:
            tab.append((n, N, "-", "-", "-", "NODATA: " + v))
            continue
        d = dec.get(n)
        if d is None:
            tab.append((n, N, "-", "-", "-", "NODATA: dump unreadable"))
            continue
        ws = [f"0x{z:08x}" for _, _, z in d["packed"]] if d["state"] == "present" else []
        want = BASE + (N or 0) if n != "t5v-ctl0" else BASE
        loop_ok = d["state"] == "present" and len(ws) == 3 and all(int(w, 16) == want for w in ws)
        pre_ok = pre == 0x400
        b7 = None if post is None else bool(post & 0x80)
        res[n] = dict(N=N, loop_ok=loop_ok, pre=pre, post=post, b7=b7, words=ws, pre_ok=pre_ok)
        note = ("loop ran on every vertex" if loop_ok else f"LOOP FAILED: depth words {ws or d['state']}, wanted 0x{want:08x}")
        tab.append((n, N, ws[0] if ws else d["state"], hex(pre) if pre is not None else "-", hex(post) if post is not None else "-", note))
        if n.startswith("t5v-i"):
            ladder.append((N, n))
    out = ["T5v: per job (loop knob proof = the stored depth word of every vertex; STATUS2 before and after)",
           table(tab, ["job", "N", "depth word", "STATUS2 pre", "STATUS2 post", "note"]), ""]
    ctl = ["t5v-ctl0", "t5v-n1", "t5v-n3"]
    bad = [n for n in ctl if n not in res or not res[n]["loop_ok"] or not res[n]["pre_ok"] or res[n]["b7"] is not False]
    if hang:
        out.append(f"hang, fault or failure in {hang}")
    if bad:
        why = ("the first backward branch did not loop as the sim says (t5v-n3): HLOOP refuted on hardware, no ladder row is a reading"
               if "t5v-n3" in bad and "t5v-n1" not in bad and "t5v-ctl0" not in bad else "control(s) failed")
        out.append(f"SUMMARY: cannot tell: {why}: {bad}; void {void}")
        return "\n".join(out), res
    used = [(N, n) for N, n in sorted(ladder) if n in res]
    notrun = [n for N, n in used if not res[n]["loop_ok"]]
    good = [(N, n) for N, n in used if res[n]["loop_ok"] and res[n]["pre_ok"] and res[n]["b7"] is not None]
    seq = [(N, res[n]["b7"]) for N, n in good]
    mono = all(not (a[1] and not b[1]) for a, b in zip(seq, seq[1:]))
    first = next((N for N, s in seq if s), None)
    if notrun:
        out.append(f"loop did NOT run on every vertex in {notrun}: those lengths are void (E770's failure mode)")
    if hang:
        verdict = f"stage stopped at {hang[-1]}: the first length that hangs brackets the latch (no STATUS2 read for it)"
    elif not seq:
        verdict = "cannot tell: no usable ladder cell"
    elif not mono:
        verdict = "bit 7 is not monotone along the ladder (set then clear): neither H-TIME nor H-INSTR/H-ITER as stated"
    elif first is None:
        verdict = (f"bit 7 never set up to N = {seq[-1][0]} ({8 * seq[-1][0]} instructions a vertex): H-NEVER consistent, "
                   "H-ITER / H-INSTR (set from 55) REFUTED, H-TIME not reached")
    else:
        prev = max((N for N, s in seq if not s and N < first), default=None)
        h55 = first == 55 and prev is not None and prev <= 53
        verdict = (f"bit 7 first set at N = {first} (last clear {prev}): H-ITER / H-INSTR (set from 55) "
                   f"{'consistent' if h55 else 'REFUTED'}; H-TIME consistent (monotone); H-NEVER REFUTED")
    out.append(f"SUMMARY: controls pass (loop proof n1, n3; STATUS2 0x400 after the reset and bit 7 clear on t5v-ctl0, n1, n3); "
               f"{verdict}; skipped by the sweep stop {skipped}; void {void}")
    return "\n".join(out), res


# ------------------------------------------------------------------------------------------------ C3
def _c3_parse(n):
    m = re.fullmatch(r"c3f?-(\d+)(?:x(\d+))?-(0x[0-9a-f]+|cal)", n)
    if not m:
        return None
    w = int(m[1])
    h = int(m[2]) if m[2] else w
    return (w, h), (None if m[3] == "cal" else int(m[3], 16))


def score_c3(k: Kept, preds):
    res, out, live = G.e1_measure(k, preds)
    g = lambda n: res.get(n, dict(void="not run"))
    valid = lambda n: not g(n).get("void") and g(n)["reach"] and g(n)["nparts"] > 1
    d36, tal = G.d36_lines(k, live)
    out += d36
    ctl = G.control_rows(preds, "raise")
    out.append("raise per job: " + " ".join(f"{n}:{'void' if not valid(n) else 'R' if g(n)['raised'] else '-'}" for n in k.names()))
    bad = [n for n, v in ctl.items() if not valid(n) or g(n)["raised"] != (v == "yes")]
    cal = [n for n in k.names() if n.endswith("-cal")]
    for n in cal:
        if n in live and not live[n].get("void"):
            prs, peaks = runs(live[n]["tl"])
            out.append(f"{n}: page need at P = 0x422: peak status {peaks and max(peaks):#x}, {len(prs)} partial render(s)"
                       + ("" if not prs else " (it overflowed)"))
    if bad:
        out.append(f"SUMMARY: cannot tell: control(s) {bad} void or not as R1 measured at 4096x4096 (raise at 0x372, none at 0x374)")
        return "\n".join(out), res
    groups = {}
    for n in k.names():
        pp = _c3_parse(n)
        if pp and pp[1] is not None and n not in ctl:
            groups.setdefault(pp[0], []).append((pp[1], g(n)["raised"] if valid(n) else None))
    parts = []
    for (w, h), cells in sorted(groups.items()):
        cells.sort()
        usable = [(P, r) for P, r in cells if r is not None]
        txt = f"{w}x{h}: " + " ".join(f"{P:#x}:{'void' if r is None else 'R' if r else '-'}" for P, r in cells)
        if not usable:
            parts.append(txt + " -> NODATA in every cell (no first abort or the second run does not reach thr0): C at this target is not "
                         "testable with 1500 vertices")
            continue
        kind, info = G.c1_ladder(cells)
        same = sum(1 for P, r in usable if r == (P - 2 <= C_R1))
        if kind == "flip":
            Pa, Pb = info
            parts.append(txt + f" -> flip: last raise {Pa:#x}, first silent {Pb:#x}: C in [{Pa - 2:#x}, {Pb - 2:#x}); H-same "
                         f"{'holds' if Pa - 2 <= C_R1 < Pb - 2 else 'REFUTED'} ({same} of {len(usable)} cells as 0x371 predicts)")
        elif kind == "multi":
            parts.append(txt + " -> more than one flip: the monotone form fails at this target")
        elif kind == "void":
            parts.append(txt + f" -> cannot tell: a void cell sits inside the flip {info[0]:#x} .. {info[1]:#x}")
        else:
            side = "raise" if usable[0][1] else "none"
            hi = max(P for P, r in usable)
            parts.append(txt + f" -> no flip: all usable cells {side}; "
                         + (f"H-same consistent on {same} of {len(usable)} cells, C >= {hi - 2:#x} at this target (a bound only: "
                            f"the cells above 0x373 were not reached)" if side == "raise" and same == len(usable) else
                            f"H-same {same} of {len(usable)}"))
    guard = "controls pass; " if ctl else "no control row in this table (the 4096 controls are g-c3's): unguarded readings; "
    out.append("SUMMARY: " + guard + ("; ".join(parts) if parts else "no 2048 cell was run") + f"; D36 unraised {tal[False][0]}/{tal[False][1]}, "
               f"raised {tal[True][0]}/{tal[True][1]}")
    return "\n".join(out), res


# ------------------------------------------------------------------------------------------------ C2
def score_c2(k: Kept, preds):
    res, out, live = G.e1_measure(k, preds)
    ctl = G.control_rows(preds, "raise")
    rows, ent, usable = [], [], {}
    for n in k.names():
        r = res.get(n, dict(void="not run"))
        m = re.fullmatch(r"k-(?:tri|1500)-(0x[0-9a-f]+)", n)
        V = int(m[1], 16) if m else None
        if V is None:
            continue                                            # not a C2 job (another stage's name): nothing to score
        if r.get("void"):
            rows.append((n, hex(V), "-", "-", "NODATA: " + r["void"]))
            continue
        first = r["thr0"]
        tri = n.startswith("k-tri")
        landed = first == V
        reach_ok = tri or r["reach"]
        ok = landed and reach_ok and r["nparts"] >= 1
        tl = live[n].get("tl")
        zero = live[n].get("knob")
        why = "" if ok else ("the poke did not land: first abort status " + hex(first) if not landed else "second run does not reach thr0")
        rows.append((n, hex(V), hex(first) if first is not None else "-", f"0x0624 {zero:#x}" if zero is not None else "-",
                     ("raise" if r["raised"] else "none") + (f"  NODATA: {why}" if not ok else "")))
        if ok:
            usable[n] = r["raised"]
    out += ["C2: first abort status (the poked threshold) and the raise per job", table(rows, ["job", "V", "first status", "0x0624 read", "raise"]), ""]
    d36, tal = G.d36_lines(k, live)
    out += d36
    bad = [n for n, v in ctl.items() if n not in usable or usable[n] != (v == "yes")]
    if bad:
        out.append(f"SUMMARY: cannot tell: control(s) {bad} void or not as E625 measured (poke 0x80 raise, 0x100 none)")
        return "\n".join(out), res
    entries = []
    for n, lst in preds.items():
        for v, mdl, st in lst.get("raise", []):
            if st != "control" and mdl.startswith("H-"):
                entries.append((mdl.split(" (")[0], st, (usable[n] == (v == "yes")) if n in usable else None))
    ladder = sorted((int(re.fullmatch(r"k-1500-(0x[0-9a-f]+)", n)[1], 16), r) for n, r in usable.items() if n.startswith("k-1500"))
    flip = next((f"raise at {a[0]:#x}, none at {b[0]:#x}" for a, b in zip(ladder, ladder[1:]) if a[1] and not b[1]), "no raise -> none step")
    out.append("poked ladder: " + " ".join(f"{V:#x}:{'R' if r else '-'}" for V, r in ladder) + f"  ({flip})")
    out.append("SUMMARY: controls pass; " + support(entries) + f"; {flip}; D36 unraised {tal[False][0]}/{tal[False][1]}, raised "
               f"{tal[True][0]}/{tal[True][1]}")
    return "\n".join(out), res


TABLE = {"g-t3": score_t3, "g-t4": score_t4, "g-t5v": score_t5v, "g-c3": score_c3, "g-c3f": score_c3, "g-c2": score_c2}


def run_stage(stage, kept_dir, preds_path=None):
    k = Kept(kept_dir)
    preds = load_preds(preds_path, stage)
    text, _ = TABLE[stage](k, preds)
    return text


def main(a):
    if len(a) != 2 or a[0] not in TABLE:
        print(__doc__)
        return 2
    stage, d = a
    r = subprocess.run([str(HERE.parent / "run" / "freeze_r2.sh"), "verify"], capture_output=True, text=True)
    if r.returncode:
        print("REFUSING: the frozen files do not verify:\n" + r.stdout + r.stderr)
        return 3
    try:
        print(run_stage(stage, d))
    except SystemExit as e:
        print(f"REFUSING: {e}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
