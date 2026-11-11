#!/usr/bin/env python3
"""score_r3.py STAGE KEPTDIR [FITKEPTDIR]: score one R3GC stage from its kept files.

  STAGE    g-z  g-qf  g-qh
  KEPTDIR  out/STAGE (copied from the laptop's ~/r3gc-out/STAGE): cases.tsv (rc, class), NAME.txt.gz, depth dumps, timelines
  g-qh also reads g-qf's kept data (default out/g-qf next to KEPTDIR) for the pairs the fit stage leaves.
Refuses to run unless `run/freeze_r3.sh verify` passes.  Prints the per-job table and one `SUMMARY:` line.
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python score/score_r3.py g-z out/g-z
Tests call `run_stage(...)` directly.

Rules (as R1, R2): a job with no output, an rc that is not a result of the tool, a missing dump, a skipped class, a hang or a fault
or a knob that did not land is NODATA, tested before any match; a failing control makes the group `cannot tell`; held-out and
replicate rows are tallied apart from repeats; every scorer ends with one `SUMMARY:` line.

g-z: the observable is E465's (E730 post hoc reader): a tile-area dword is stored iff it is not 1.0f.  Gates from the kept dump: no
tile-area dword still 0xdeadbeef; for a full-screen triangle the tool's `diff: 0 of W*H pixels`.
g-qf / g-qh: the count of partial renders = the 0x0658 bit 0 stretches of the job's timeline; the knob proof is the job's own
0x0624 (P - 0x22).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import pathlib  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402
import subprocess  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "gen"))
import r3_geo as M  # noqa: E402
import score_geo2 as G  # noqa: E402
from r1lib import Kept, load_preds, outcome, peak_status, runs, support, table  # noqa: E402


def _arg(c, opt):
    m = re.search(rf"{re.escape(opt)} (\S+)", c.get("args", ""))
    return m[1] if m else None


# ----------------------------------------------------------------------------------------------------------- g-z (C1)
def _model_key(label):
    return label.split(" ")[0]


def score_z(k: Kept, preds):
    rows, void, res = [], [], {}
    for n in k.names():
        c = k.case(n)
        v = k.void(n, ("depth.1.bin",))
        if v:
            void.append(n)
            rows.append((n, "-", "-", "-", "-", "NODATA: " + v))
            continue
        txt = k.out(n)
        dm = k.dmesg(n)
        oc = outcome(txt, dm)
        if oc in ("hang", "fault") or c.get("class") in ("hang", "fault", "fail"):
            void.append(n)
            rows.append((n, "-", "-", "-", "-", f"NODATA: class {c.get('class')} / {oc}"))
            continue
        w, h = int(_arg(c, "--width")), int(_arg(c, "--height"))
        raw = k.depth(n, 1)
        if raw is None or len(raw) % 4:
            void.append(n)
            rows.append((n, f"{w}x{h}", "-", "-", "-", "NODATA: depth dump unreadable"))
            continue
        words = struct.unpack("<%dI" % (len(raw) // 4), raw)
        need = 512 * ((M.tiles(w, h)[1] - 1) * (M.pitch_g(w) + 1) + M.tiles(w, h)[0])
        if len(words) < need:
            void.append(n)
            rows.append((n, f"{w}x{h}", "-", "-", "-", f"NODATA: dump has {len(words)} dwords, the tiles need {need}"))
            continue
        st, dead = M.stored_set(words, w, h)
        full = "--tri-full" in c.get("args", "")
        dm_ok = re.search(rf"^diff: 0 of {w * h} pixels", txt or "", re.M) is not None if full else True
        note = []
        if dead:
            note.append(f"NODATA: {dead} tile-area dwords still 0xdeadbeef (the store did not write whole tiles)")
        if not dm_ok:
            note.append(f"NODATA: no `diff: 0 of {w * h} pixels` line")
        xs = max((x for x, _ in st), default=-1) + 1
        ys = max((y for _, y in st), default=-1) + 1
        res[n] = dict(w=w, h=h, st=st, dead=dead, full=full, xs=xs, ys=ys, ok=not note)
        if note:
            void.append(n)
        rows.append((n, f"{w}x{h}", len(st), f"{xs},{ys}", " ".join(f"{r}={M.extent(r, w, h)[0]},{M.extent(r, w, h)[1]}" for r in M.RULES),
                     "; ".join(note) or "ok"))
    out = ["Z: stored (not 1.0f) tile-area dwords per job; stored extent (max x + 1, max y + 1) and each rule's extent",
           table(rows, ["job", "size", "stored", "extent", "rule extents (A FLOOR ROUND CEIL RSTRICT)", "note"]), ""]
    ctl = {n: v for n, qs in preds.items() for v, m, s in qs.get("stored_count", []) if s == "control"}
    ctlsha = {n: v for n, qs in preds.items() for v, m, s in qs.get("stored_set_sha", []) if s == "control" and m.startswith("E730")}
    bad = [n for n in ctl if n not in res or not res[n]["ok"] or len(res[n]["st"]) != int(ctl[n])
           or M.set_sha(res[n]["st"]) != ctlsha.get(n)]
    if not ctl:
        return "\n".join(out + ["SUMMARY: cannot tell: no control row"]), res
    if bad:
        return "\n".join(out + [f"SUMMARY: cannot tell: control(s) {bad} did not reproduce E730's stored set (924 / 924 / 3444, rule A's "
                                f"set); void jobs {void}"]), res
    entries, unmatched, tri_rows = [], [], []
    for n, qs in preds.items():
        if n not in res and not any(s in ("heldout", "repeat") for lst in qs.values() for v, m, s in lst):
            continue
        r = res.get(n)
        for v, m, s in qs.get("stored_set_sha", []):
            if s in ("heldout", "repeat"):
                entries.append((_model_key(m), s, (M.set_sha(r["st"]) == v) if r and r["ok"] else None))
        if r and r["ok"] and qs.get("stored_set_sha") and s_is_held(qs):
            if not any(M.set_sha(r["st"]) == v for v, m, s in qs["stored_set_sha"] if s == "heldout"):
                unmatched.append(f"{n} (stored {len(r['st'])}, extent {r['xs']},{r['ys']})")
        if qs.get("tri_raster"):
            c = k.case(n)
            args = c.get("args", "")
            vv = re.search(r"--tri-v (\S+)", args)
            if not vv or n not in res or not res[n]["ok"]:
                for v, m, s in qs["tri_raster"]:
                    entries.append((_model_key(m) + " raster", s, None))
                continue
            v256 = [int(t) for t in vv[1].split(",")]
            for v, m, s in qs["tri_raster"]:
                rule = _model_key(m)
                d, a = M.tri_raster(v256, rule, r["w"], r["h"])
                ok = d <= r["st"] <= (d | a)
                entries.append((rule + " raster", s, ok))
                tri_rows.append(f"{n}: {rule} raster (definite {len(d)}, ambiguous {len(a)}): stored {len(r['st'])}, "
                                f"{'inside' if ok else 'OUTSIDE'} (missing definite {len(d - r['st'])}, beyond {len(r['st'] - (d | a))})")
    out += tri_rows
    verdict = support(entries)
    # the rule A verdict in words: every held-out full-screen cell
    held_full = [n for n, qs in preds.items() if n in res and res[n]["ok"] and res[n]["full"]
                 and any(s == "heldout" for _, _, s in qs.get("stored_set_sha", []))]
    a_hits = [n for n in held_full if any(M.set_sha(res[n]["st"]) == v for v, m, s in preds[n]["stored_set_sha"]
                                          if s == "heldout" and _model_key(m) == "A")]
    out.append(f"rule A on the held-out full-screen cells: {len(a_hits)} of {len(held_full)} sets equal"
               + (f"; no model's set matches: {unmatched}" if unmatched else ""))
    out.append("SUMMARY: controls pass (E730's 924, 924, 3444 and rule A's sets); " + verdict
               + f"; rule A {len(a_hits)} of {len(held_full)} held-out full-screen cells"
               + (f"; void jobs {void}" if void else ""))
    return "\n".join(out), res


def s_is_held(qs):
    return any(s == "heldout" for v, m, s in qs.get("stored_set_sha", []))


# ----------------------------------------------------------------------------------------------------------- g-qf, g-qh (C2)
PAIR_RE = re.compile(r"E625 count \(k=(-?\d+), s=(0x[0-9a-f]+)\)")


def _counts(k: Kept, preds, early_void=False):
    """{job: count} for the usable jobs, {job: reason} for the void ones, {job: P}."""
    counts, void, P = {}, {}, {}
    for n in k.names():
        j = G.live_job(k, preds, n)
        if j["void"]:
            void[n] = j["void"]
            continue
        oc = outcome(j["txt"], k.dmesg(n))
        if oc in ("hang", "fault") or k.case(n).get("class") in ("hang", "fault", "fail"):
            void[n] = f"class {k.case(n).get('class')} / {oc}"
            continue
        if early_void:
            K = int(_arg(k.case(n), "-n") or 1)
            early = [int(x) for x in re.findall(r"^tri \d+x\d+ #(\d+): overflowed", j["txt"] or "", re.M) if int(x) < K]
            if early:
                void[n] = f"a kick lost: render(s) {early} overflowed before the last (E773's rule)"
                continue
        prs, _ = runs(j["tl"])
        counts[n] = len(prs)
        P[n] = j["knob"] + 0x22
    return counts, void, P


def _pair_models(preds, jobs, sets):
    """{(k, s): [bool, ...]} over the usable jobs of the given sets."""
    models = {}
    for n in jobs:
        for v, m, st in preds.get(n, {}).get("nparts", []):
            mm = PAIR_RE.fullmatch(m)
            if mm and st in sets:
                models.setdefault((int(mm[1]), int(mm[2], 16)), []).append(int(v) == jobs[n])
    return models


def _monotone(cells):
    """cells [(P, count)] (one scene): non-increasing count with P."""
    s = sorted(cells)
    return all(b[1] <= a[1] for a, b in zip(s, s[1:])), s


def _ctl_check(counts, void, preds):
    ctl = G.control_rows(preds, "nparts")
    return [n for n, v in ctl.items() if counts.get(n) != int(v)], ctl


def score_qf(k: Kept, preds):
    counts, void, P = _counts(k, preds)
    rows = [(n, hex(P[n]) if n in P else "-", counts.get(n, "NODATA: " + void.get(n, "not run"))) for n in k.names()]
    out = ["QF: partial renders per job (the 0x0658 bit 0 stretches)", table(rows, ["job", "P", "count"]), ""]
    bad, ctl = _ctl_check(counts, void, preds)
    if bad or not ctl:
        out.append(f"SUMMARY: cannot tell: control(s) {bad} did not read their frozen count (E625: 2 at 0xa0, 1 at 0xb0; E779: 1 at 0xa3); "
                   f"void {sorted(void)}")
        return "\n".join(out), {}
    mono, srt = _monotone([(P[n], counts[n]) for n in counts])
    if not mono:
        out.append("count by P: " + " ".join(f"{p:#x}:{c}" for p, c in srt))
        out.append(f"SUMMARY: cannot tell: the counts are not monotone in P (stop condition); void {sorted(void)}")
        return "\n".join(out), {}
    fitjobs = {n: counts[n] for n in counts if any(s == "fit" for _, _, s in preds.get(n, {}).get("nparts", []))}
    models = _pair_models(preds, fitjobs, ("fit",))
    left = sorted(p for p, r in models.items() if r and all(r))
    cls = M.classes(left, [(M.U_DEFAULT, P[n]) for n in fitjobs]) if left else []
    res = dict(left=left, cells=len(fitjobs), classes=len(cls))
    out.append("count by P: " + " ".join(f"{p:#x}:{c}" for p, c in srt))
    if not models:
        out.append(f"SUMMARY: cannot tell: no usable fit cell; void {sorted(void)}")
    elif not left:
        out.append(f"SUMMARY: controls pass; monotone; E625's count family REFUTED at U = 287: none of {len(models)} (k, s) pairs fits the "
                   f"{len(fitjobs)} usable fit cells; void {sorted(void)}")
    else:
        out.append(f"SUMMARY: controls pass; monotone; {len(left)} of {len(models)} (k, s) pairs fit all {len(fitjobs)} fit cells, "
                   f"{len(cls)} class(es) of pairs predicting the same counts here: {left}; void {sorted(void)}")
    return "\n".join(out), res


def score_qh(k: Kept, preds, fit_dir=None):
    counts, void, P = _counts(k, preds, early_void=True)
    rows = [(n, hex(P[n]) if n in P else "-", counts.get(n, "NODATA: " + void.get(n, "not run"))) for n in k.names()]
    out = ["QH: partial renders per job", table(rows, ["job", "P", "count"]), ""]
    # the fit stage's survivors
    fitk = Kept(fit_dir) if fit_dir else None
    fpreds = load_preds(None, "g-qf")
    fres = score_qf(fitk, fpreds)[1] if fitk and fitk.names() else {}
    left = fres.get("left")
    if left is None:
        out.append("SUMMARY: cannot tell: the fit stage's kept data is missing or its controls failed (no survivors to test)")
        return "\n".join(out), {}
    # the scene gates (control rows U): the peak of the 0x0724 low half equals the scene's need, no partial render
    bad_sc = []
    for n in k.names():
        if not n.startswith("qc-"):
            continue
        j = G.live_job(k, preds, n)
        want = int(G.pred1(preds, n, "U"))
        got = None if j["void"] else peak_status(j["tl"])
        okc = got == want and not j["void"] and not runs(j["tl"])[0]
        out.append(f"scene gate {n}: U {got if got is not None else 'NODATA ' + str(j['void'])} (E773: {want}) "
                   f"{'ok' if okc else 'FAILED'}")
        if not okc:
            bad_sc.append(n[3:])
    scenes = {n: re.fullmatch(r"qh-(s\d+)-0x[0-9a-f]+", n)[1] for n in counts if re.fullmatch(r"qh-(s\d+)-0x[0-9a-f]+", n)}
    use = {n: c for n, c in counts.items() if n in scenes and scenes[n] not in bad_sc}
    if bad_sc and not use:
        out.append(f"SUMMARY: cannot tell: scene gate(s) {bad_sc} failed (the scene is not E773's); void {sorted(void)}")
        return "\n".join(out), {}
    mono_bad = []
    for sc in sorted(set(scenes.values())):
        cells = [(P[n], c) for n, c in use.items() if scenes[n] == sc]
        ok, srt = _monotone(cells)
        out.append(f"count by P, scene {sc}: " + " ".join(f"{p:#x}:{c}" for p, c in srt))
        if not ok:
            mono_bad.append(sc)
    if mono_bad:
        out.append(f"SUMMARY: cannot tell: counts not monotone in P in scene(s) {mono_bad} (stop condition); void {sorted(void)}")
        return "\n".join(out), {}
    models = _pair_models(preds, use, ("heldout",))
    survive = [p for p in left if p in models and all(models[p])]
    entries = [(f"E625 count (k={p[0]}, s={p[1]:#x})", "heldout", all(models[p])) for p in left if p in models]
    agree = [n for n in use if len({v for v, m, s in preds[n]["nparts"]}) == 1]
    agree_bad = [n for n in agree if use[n] != int(preds[n]["nparts"][0][0])]
    res = dict(left=left, survive=survive, cells=len(use))
    if not use:
        out.append(f"SUMMARY: cannot tell: no usable held-out cell; void {sorted(void)}")
    elif not survive:
        out.append(f"SUMMARY: held out ({len(use)} cells of scenes {sorted(set(scenes.values()))}): REFUTED, none of the {len(left)} pairs "
                   f"the fit left predicts all held-out counts" + (f"; agree-cell misses {agree_bad}" if agree_bad else "")
                   + f"; void {sorted(void)}")
    elif len(survive) == 1:
        out.append(f"SUMMARY: held out ({len(use)} cells): pinned (k, s) = {survive[0]}; the fit left {len(left)} pair(s) "
                   f"{left}; the others were refuted by the held-out cells; {support(entries)}"
                   + (f"; agree-cell misses {agree_bad}" if agree_bad else "") + f"; void {sorted(void)}")
    else:
        out.append(f"SUMMARY: held out ({len(use)} cells): {len(survive)} of the {len(left)} pairs the fit left survive: {survive}; "
                   f"{support(entries)}" + (f"; agree-cell misses {agree_bad}" if agree_bad else "") + f"; void {sorted(void)}")
    return "\n".join(out), res


TABLE = {"g-z": score_z, "g-qf": score_qf, "g-qh": score_qh}


def run_stage(stage, kept_dir, preds_path=None, fit_dir=None):
    k = Kept(kept_dir)
    preds = load_preds(preds_path, stage)
    if stage == "g-qh":
        fit_dir = fit_dir or str(pathlib.Path(kept_dir).resolve().parent / "g-qf")
        text, _ = score_qh(k, preds, fit_dir)
    else:
        text, _ = TABLE[stage](k, preds)
    return text


def main(a):
    if len(a) not in (2, 3) or a[0] not in TABLE:
        print(__doc__)
        return 2
    r = subprocess.run([str(HERE.parent / "run" / "freeze_r3.sh"), "verify"], capture_output=True, text=True)
    if r.returncode:
        print("REFUSING: the frozen files do not verify:\n" + r.stdout + r.stderr)
        return 3
    try:
        print(run_stage(a[0], a[1], fit_dir=a[2] if len(a) == 3 else None))
    except SystemExit as e:
        print(f"REFUSING: {e}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
