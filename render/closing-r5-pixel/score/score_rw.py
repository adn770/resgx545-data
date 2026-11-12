# SPDX-License-Identifier: MIT
"""Scorer of g4-rw (Q230, the 1/w word table).  Written before the run; frozen with the predictions.

Decode (R2-geo's way): pbdump.first_object of the job's parameter buffer and TA data: vertices with packed window coordinates and
the PB_OBJ.RHW words; each predicted vertex (window xy = 32 + 32 x / w, input order) is matched to the stored vertex at that
position (tolerance 1/32 pixel, as r2-geo's by_xy) and its word read.
Controls rw-k0..k3 (object present, 3 vertices, window rule, depth 0x3f000000, the known words exact) gate every table row:
scorekit.gate; a control that is not a pass makes every table row cannot tell.  Table rows: the frozen assertion "the word is RZ or
RZ + 1 of 1/w" per word, tallied FIT and HELD OUT apart; a job-level row (object, 3 vertices, window, depth) apart.  A void job (no
output, no dump, an rc that is not a result, class not ok) is cannot tell, never a pass.
Analysis (only when all 60 words were read and the controls passed): the families of rwfam.py are fitted on the 30 FIT words (30 of
30 exactly), the fits are scored on the 30 HELD OUT words; stop condition frozen: more than one FAMILY at 30 of 30 held out, or none:
the words are recorded and no rule is adopted.  E783's lesson (4 of 257 models fit six words by chance): the number of models that fit
30 of 30 FIT words whose pairing with w was shuffled (fixed seeds) is printed.
  score(k, preds) -> (text, result); the last line starts with SUMMARY:"""
from __future__ import annotations

import os
import pathlib
import random
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(pathlib.Path(os.environ.get("RESGX545_MAIN", str(pathlib.Path.home() / "src/resgx545"))) / "tools/usse-asm"))

import rwdesign as D  # noqa: E402
import rwfam as R  # noqa: E402
import scorekit as SK  # noqa: E402
from r4lib import table  # noqa: E402

XY_TOL = 1 / 32
SHUFFLE_SEEDS = (1, 2, 3, 4, 5)


def decode_object(param, tadata):
    """{'state': present|none|written-unlisted|bad dump, 'rhw': [...], 'xy': [(x, y)...], 'depth': [...]}."""
    import pbdump
    try:
        ws = pbdump.obj(param) if param else []
        o = pbdump.first_object(param, tadata) if param and tadata else None
    except Exception as e:
        return dict(state="bad dump", why=str(e)[:60])
    if not ws:
        return dict(state="none")
    if o is None:
        return dict(state="written-unlisted")
    big = 0
    for i, w in enumerate(o["packed"]):
        big |= w << (32 * i)
    nv = len(o["vertices"])
    packed = [((big >> (80 * v)) & 0xffffff, (big >> (80 * v + 24)) & 0xffffff, (big >> (80 * v + 48)) & 0xffffffff) for v in range(nv)]
    return dict(state="present", nvert=nv, rhw=list(o["PB_OBJ.RHW"]),
                xy=[(x / 256 - 4096, y / 256 - 4096) for y, x, _ in packed], depth=[d for _, _, d in packed])


def _list(v, conv=lambda s: int(s, 16)):
    return [None if s == "?" else conv(s) for s in v.split(",")]


def _xy_list(v):
    return [tuple(float(c) for c in s.split(",")) for s in v.split(";")]


def pq(preds, name, q):
    r = preds.get(name, {}).get(q, [])
    return r[0][0] if r else None


def read_job(k, preds, name):
    """dict(void, state, words (per predicted vertex, None if unmatched), shape (bool), notes)."""
    r = dict(name=name, void=None, words=[None] * 3, shape=None, notes=[], depth_ok=None, window_ok=None, nvert=None)
    v = k.void(name, dumps=("param.bin", "tadata.bin"))
    if v:
        r["void"] = v
        return r
    if k.case(name).get("class") not in ("ok", None, ""):
        r["void"] = f"class {k.case(name).get('class')}"
        return r
    d = decode_object(k.dump(name, "param.bin"), k.dump(name, "tadata.bin"))
    if d["state"] == "bad dump":
        r["void"] = "dump unreadable"
        return r
    if d["state"] != "present":
        r["shape"], r["notes"] = False, [f"object {d['state']}"]
        return r
    exp = _xy_list(pq(preds, name, "xy_ordered"))
    r["nvert"] = d["nvert"]
    got, win = [None] * 3, []
    for i, (px, py) in enumerate(exp):
        best = min(range(d["nvert"]), key=lambda j: abs(d["xy"][j][0] - px) + abs(d["xy"][j][1] - py))
        ok = abs(d["xy"][best][0] - px) + abs(d["xy"][best][1] - py) <= 2 * XY_TOL
        win.append(ok)
        if ok:
            got[i] = (d["rhw"][best], d["depth"][best])
    r["window_ok"] = all(win)
    r["words"] = [g[0] if g else None for g in got]
    r["depth_ok"] = all(g is not None and g[1] == 0x3f000000 for g in got)
    r["shape"] = d["nvert"] == 3 and r["window_ok"] and r["depth_ok"]
    if d["nvert"] != 3:
        r["notes"].append(f"{d['nvert']} vertices")
    if not r["window_ok"]:
        r["notes"].append("window mismatch")
    if not r["depth_ok"]:
        r["notes"].append("depth word")
    return r


def control_state(r, preds):
    if r["void"]:
        return None
    if not r["shape"]:
        return False
    known = _list(pq(preds, r["name"], "rhw_known"))
    return all(kn is None or w == kn for w, kn in zip(r["words"], known))


def analysis(fit_pairs, held_pairs):
    """([models fitting 30 of 30 FIT], [of those holding 30 of 30 HELD OUT], families, chance counts)."""
    ms = R.models()
    fit = [n for n, (f, fn) in ms.items() if R.fits(fn, fit_pairs) == len(fit_pairs)]
    held = [n for n in fit if R.fits(ms[n][1], held_pairs) == len(held_pairs)]
    chance = []
    ws, gs = [w for w, g in fit_pairs], [g for w, g in fit_pairs]
    for seed in SHUFFLE_SEEDS:
        sh = gs[:]
        random.Random(seed).shuffle(sh)
        chance.append(sum(1 for n, (f, fn) in ms.items() if R.fits(fn, list(zip(ws, sh))) == len(ws)))
    return fit, held, sorted({ms[n][0] for n in held}), chance, len(ms)


def score(k, preds):
    out = []
    names = sorted(n for n in preds if n.startswith("rw-"))
    jobs = {n: read_job(k, preds, n) for n in names}
    ctl_names = [n for n in names if n.startswith("rw-k")]
    ctl = {n: control_state(jobs[n], preds) for n in ctl_names}
    g = SK.gate(ctl)
    out.append("Q230 (g4-rw): controls " + "; ".join(f"{n} {SK._state(v)}" for n, v in ctl.items()))
    split = {}
    for q in ("FIT", "HELD_OUT"):
        for v, m, s in preds.get("@split", {}).get(q, []):
            split[int(v, 16)] = q.replace("_", " ")
    # table rows: one per (job, vertex) word
    rows, recs = [], []
    shape_rows = []
    for n in names:
        if n.startswith("rw-k"):
            continue
        j = jobs[n]
        ww = _list(pq(preds, n, "w_words"))
        rzw = _list(pq(preds, n, "rz_words"))
        shape_rows.append(SK.gated(g, None if j["void"] else bool(j["shape"])))
        for i in range(3):
            got = j["words"][i]
            half = split.get(ww[i], "?")
            if j["void"] or got is None:
                st = None
            else:
                st = got in (rzw[i], rzw[i] + 1)
            st = SK.gated(g, st)
            rows.append((half, st))
            recs.append((n, i, ww[i], rzw[i], got, half, st, j["void"]))
    out.append("")
    tb = []
    for n, i, w, rzv, got, half, st, vd in recs:
        diff = "-" if got is None else got - rzv
        tb.append((n, i, "%g" % float(D.fval(w)), D.hx(w), D.hx(rzv), "-" if got is None else D.hx(got), diff, half,
                   "void" if vd else {True: "held", False: "FAILED", None: "cannot tell"}[st]))
    out.append(table(tb, ["job", "v", "w", "w word", "RZ", "got", "got - RZ", "half", "RZ or RZ+1"]))
    out.append("")
    for half in ("FIT", "HELD OUT"):
        t = SK.tally([s for h, s in rows if h == half])
        out.append(f"frozen assertion 'every word is RZ or RZ+1', {half}: {t}")
    ts = SK.tally(shape_rows)
    out.append(f"job shape (object, 3 vertices, window, depth 0x3f000000): {ts}")
    t_all = SK.tally([s for h, s in rows])
    # analysis
    fit_pairs = [(w, got) for n, i, w, rzv, got, half, st, vd in recs if half == "FIT" and got is not None and not vd]
    held_pairs = [(w, got) for n, i, w, rzv, got, half, st, vd in recs if half == "HELD OUT" and got is not None and not vd]
    res = dict(gate_ok=g.ok, tally=t_all, analysis=None, controls=ctl, gate=g)
    if not g.ok:
        verdict = "analysis not run: controls " + "; ".join(g.problems)
    elif len(fit_pairs) < 30 or len(held_pairs) < 30:
        verdict = f"analysis not run: {len(fit_pairs)} of 30 FIT and {len(held_pairs)} of 30 HELD OUT words read"
    else:
        fit, held, fams, chance, nm = analysis(fit_pairs, held_pairs)
        res["analysis"] = dict(fit=fit, held=held, families=fams, chance=chance)
        out.append(f"analysis: {nm} models of 5 families; "
                   f"{len(fit)} fit 30 of 30 FIT words: {fit[:12]}{' ...' if len(fit) > 12 else ''}; {len(held)} of them hold 30 of 30 HELD OUT: "
                   f"{held[:12]}{' ...' if len(held) > 12 else ''}; families {fams}")
        out.append(f"chance: models fitting 30 of 30 FIT words with the word pairing shuffled (seeds {list(SHUFFLE_SEEDS)}): {chance}")
        if len(fams) == 1:
            verdict = f"family {fams[0]} alone fits 30 of 30 held out ({len(held)} models: {held[:4]}): a candidate rule, to be reread, not yet adopted knowledge"
        elif not fams:
            verdict = "no family fits 30 of 30 held out: the words are recorded, no rule adopted"
        else:
            verdict = f"families {fams} all fit 30 of 30 held out: the words are recorded, no rule adopted"
    res["verdict"] = verdict
    claim = "every table word is RZ or RZ+1 of 1/w"
    head = SK.headline(claim, ctl, [s for h, s in rows])
    out.append("SUMMARY: " + head + "; " + verdict)
    res["headline"] = head
    return "\n".join(out), res
