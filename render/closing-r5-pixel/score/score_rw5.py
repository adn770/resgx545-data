# SPDX-License-Identifier: MIT
"""Scorer of g5-rw (Q230, the 1/w word), parts g5-rwa (controls, q jobs) and g5-rw (m rows, replicates, dense table).  Written
before the run; frozen with the predictions.  Plan: closing5/pixel/exp-pixel-r5.md section 4.
Decode: R4's score_rw.py unchanged (decode_object, read_job: pbdump's first object; each predicted vertex matched at its frozen window
within 1/32 pixel); R4's word table (word_table here reproduces R4's printed table byte for byte: tests/test_replay.py).
Controls (rw-k0..k5): shape and the known words exact; scorekit.gate; a control that is not a pass makes every row cannot tell.
Gate of part a (the driver's, before part b): every control passes and fewer than 3 q jobs FAILED shape.
Rows: per word "RZ or RZ + 1" (q, m, replicate and dense words; the dense ones tallied FIT and HELD OUT apart); per job shape (object,
3 vertices at the frozen window, depth 0x3f000000): a job without it is FAILED shape, its words cannot tell; three FAILED shapes in the
dense table void it (the design is wrong again).
Verdict H-MANT (word - RZ follows the 23-bit mantissa of w): held iff the controls pass and 42 of 42 m words equal R4's delta; one
miss refutes it unless a replicate differs from R4 (then "not deterministic": cannot tell); any m word not read: cannot tell.
The q words: shape, RZ / RZ + 1, and H-MANT on the 4 words whose mantissa was read (reported with the verdict).
  score(kept_a, kept_b, preds) -> (text, result); the last line starts with SUMMARY:"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import rwdesign as D  # noqa: E402
import score_rw as R4  # noqa: E402  (R4's reader, unchanged)
import scorekit as SK  # noqa: E402
from r4lib import table  # noqa: E402

SHAPE_STOP = 3


class Both:
    """Two kept stage directories read as one (a job name is in one of them)."""

    def __init__(self, *ks):
        self.ks = [k for k in ks if k is not None]

    def _k(self, name):
        return next((k for k in self.ks if name in k.names()), self.ks[0] if self.ks else None)

    def names(self):
        return [n for k in self.ks for n in k.names()]

    def case(self, name):
        k = self._k(name)
        return k.case(name) if k else {}

    def void(self, name, dumps=()):
        k = self._k(name)
        return k.void(name, dumps) if k else "no kept stage directory"

    def out(self, name):
        k = self._k(name)
        return k.out(name) if k else None

    def dump(self, name, suffix):
        k = self._k(name)
        return k.dump(name, suffix) if k else None


def word_records(k, preds, names, split):
    """R4's per-word records (job, vertex, w, RZ, got, half, state, void) and the jobs read, R4's rules exactly."""
    jobs = {n: R4.read_job(k, preds, n) for n in names}
    recs = []
    for n in names:
        j = jobs[n]
        ww = R4._list(R4.pq(preds, n, "w_words"))
        rzw = R4._list(R4.pq(preds, n, "rz_words"))
        for i in range(3):
            got = j["words"][i]
            st = None if (j["void"] or got is None) else got in (rzw[i], rzw[i] + 1)
            recs.append([n, i, ww[i], rzw[i], got, split.get(ww[i], "?"), st, j["void"]])
    return jobs, recs


def word_table(recs):
    """R4's printed table (score_rw.py) of the records."""
    tb = []
    for n, i, w, rzv, got, half, st, vd in recs:
        diff = "-" if got is None else got - rzv
        tb.append((n, i, "%g" % float(D.fval(w)), D.hx(w), D.hx(rzv), "-" if got is None else D.hx(got), diff, half,
                   "void" if vd else {True: "held", False: "FAILED", None: "cannot tell"}[st]))
    return table(tb, ["job", "v", "w", "w word", "RZ", "got", "got - RZ", "half", "RZ or RZ+1"])


def controls(k, preds):
    names = [n for n in preds if n.startswith("rw-k")]
    jobs = {n: R4.read_job(k, preds, n) for n in names}
    ctl = {n: R4.control_state(jobs[n], preds) for n in sorted(names)}
    return ctl, jobs


def q_shapes(k, preds):
    qs = sorted(n for n in preds if n.startswith("q-"))
    return {n: R4.read_job(k, preds, n) for n in qs}


def gate_a(k, preds):
    """(Gate, lines) of part a: the controls and the q shapes."""
    ctl, _ = controls(k, preds)
    qj = q_shapes(k, preds)
    failed = [n for n, j in qj.items() if not j["void"] and j["shape"] is False]
    void = [n for n, j in qj.items() if j["void"]]
    g = dict(ctl)
    g["fewer than 3 q jobs FAILED shape"] = False if len(failed) >= SHAPE_STOP else (None if len(failed) + len(void) >= SHAPE_STOP else True)
    lines = [f"q shapes: FAILED {failed or 'none'}; void {void or 'none'}"]
    return SK.gate(g), lines


def score(ka, kb, preds):
    k = Both(ka, kb)
    out = []
    ctl, cj = controls(k, preds)
    g = SK.gate(ctl)
    out.append("Q230 (g5-rw): controls " + "; ".join(f"{n} {SK._state(v)}" for n, v in ctl.items()))
    split = {}
    for q in ("FIT", "HELD_OUT"):
        for v, m, s in preds.get("@split", {}).get(q, []):
            split[int(v, 16)] = q.replace("_", " ")
    names = [n for n in preds if not n.startswith(("rw-k", "@"))]
    order = lambda n: ({"q": 0, "m": 1, "r": 2, "d": 3}[n[0]], n)
    names.sort(key=order)
    jobs, recs = word_records(k, preds, names, split)
    out += ["", word_table(recs), ""]
    shape = {n: (None if jobs[n]["void"] else bool(jobs[n]["shape"])) for n in names}
    for n in names:
        if jobs[n]["notes"]:
            out.append(f"{n}: {'FAILED shape' if shape[n] is False else 'shape'} ({', '.join(jobs[n]['notes'])})")
    for grp, pre in (("q jobs", "q-"), ("m jobs", "m-"), ("replicates", "rw-"), ("dense table", "d-")):
        out.append(f"job shape, {grp}: {SK.tally([SK.gated(g, shape[n]) for n in names if n.startswith(pre)])}")
    for grp, pre in (("q", "q-"), ("m", "m-"), ("replicates", "rw-")):
        out.append(f"'RZ or RZ+1', {grp}: {SK.tally([SK.gated(g, r[6]) for r in recs if r[0].startswith(pre)])}")
    for half in ("FIT", "HELD OUT"):
        out.append(f"'RZ or RZ+1', dense {half}: {SK.tally([SK.gated(g, r[6]) for r in recs if r[0].startswith('d-') and r[5] == half])}")
    got = {(r[0], r[1]): r[4] for r in recs}
    rz = {(r[0], r[1]): r[3] for r in recs}
    # replicates: R4's six words
    rep = []
    for n in ("rw-07", "rw-10"):
        if n not in preds:
            continue
        want = R4._list(R4.pq(preds, n, "r4_words"))
        for i in range(3):
            gv = got.get((n, i))
            rep.append(None if gv is None or jobs[n]["void"] else gv == want[i])
    out.append(f"replicates (R4's six words): {SK.tally(rep)}")
    # H-MANT on the m rows
    hm, miss = [], []
    for n in names:
        if not n.startswith("m-"):
            continue
        ds = R4.pq(preds, n, "hmant").split(",")
        for i in range(3):
            gv = got.get((n, i))
            st = None if gv is None or jobs[n]["void"] or shape[n] is False else (gv - rz[(n, i)]) == int(ds[i])
            hm.append(SK.gated(g, st))
            if st is False:
                miss.append(f"{n}.{i} got RZ{gv - rz[(n, i)]:+d}, R4 RZ{int(ds[i]):+d}")
    th = SK.tally(hm)
    out.append(f"H-MANT on the m rows (R4's delta): {th}" + (f"; misses {miss}" if miss else ""))
    qh = []
    for n in names:
        if n.startswith("q-"):
            ds = R4.pq(preds, n, "hmant").split(",")
            for i in range(3):
                if ds[i] != "?":
                    gv = got.get((n, i))
                    qh.append(SK.gated(g, None if gv is None or shape[n] is False else (gv - rz[(n, i)]) == int(ds[i])))
    out.append(f"H-MANT on the q words with a read mantissa: {SK.tally(qh)}")
    dfail = sum(1 for n in names if n.startswith("d-") and shape[n] is False)
    if dfail >= SHAPE_STOP:
        out.append(f"dense table VOID: {dfail} jobs FAILED shape (the design is wrong again)")
    if not g.ok:
        verdict = "H-MANT cannot tell: controls " + "; ".join(g.problems)
    elif False in rep:
        verdict = "H-MANT cannot tell: a replicate differs from R4 (not deterministic)"
    elif th.failed:
        verdict = f"H-MANT REFUTED: {th.failed} of {len(hm)} m words differ from R4's delta ({'; '.join(miss[:4])})"
    elif th.cannot_tell or None in rep:
        verdict = f"H-MANT cannot tell: {th.cannot_tell} m words not read" + ("; a replicate not read" if None in rep else "")
    else:
        verdict = f"H-MANT held: {th.held} of {len(hm)} m words equal R4's delta at another exponent"
    res = dict(gate=g, controls=ctl, hmant=th, replicate=rep, verdict=verdict, shape=shape, dense_void=dfail >= SHAPE_STOP, recs=recs)
    head = SK.headline("every word is RZ or RZ+1 of 1/w", ctl, [SK.gated(g, r[6]) for r in recs])
    out.append("SUMMARY: " + verdict + "; " + head)
    return "\n".join(out), res
