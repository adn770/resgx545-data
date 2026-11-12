#!/usr/bin/env python3
"""r6-render4x stage B scorer (set B), written and frozen before the run.  Each command prints its rows and ends with SUMMARY lines.

  score_b.py STAGE OUTDIR          one stage: s0b b k r (s0b read where OUTDIR/../gate-STAGE.txt says, else OUTDIR's parent)
  score_b.py gate STAGE ROOT...    exit 0 if the stage may run: s0b's four controls passed (every stage but s0b)
  score_b.py verdict ROOT...       set B: H-ROOM (b), the knob's exact limit (k, with k3's held set), the largest targets (r)

Hypotheses (frozen in predictions/{s0b,b,k,kh,r}.tsv; DISCLOSED: frozen after stage A held H-TPM 11 of 11, out/20261112-144822):
  H-ROOM  b: with the r6-kernel's automatic room (4 x a 1x context's, fork 56f8b932) the eight own-maximum cells that faulted on the
          rgn4 kernel (E845, E868, stage A's h1, h2) complete with 0 wrong, 0 headers off the rule from the new td.rgn.  b9 is the
          control (1024 x 768, completes on either kernel); s0b's controls check the new TA-data size of a 4x context.
  H-TPM   k: the exact form, not the bound: with render_tail_room one page apart, 1280 x 1024 completes at 0xb000 (k2) and faults at
          0xa000 (k3, held: the lost set frozen offset by offset, 171 headers from 0xd000), 1024 x 768 faults at 0x3000 (k4).  Controls:
          k1 (0x4000 at 1280 x 1024 reproduces the rgn4 layout: must fault; if it completes the knob does not do what it says and k is
          void) and k5 (0x4000 at 1024 x 768: complete at the limit).
  r       r2 (2048 x 2032, 1017 pages) and r1 (4096 x 960) complete; r3 (4096 x 1152, 1153 pages) ends in -ENOSPC without a fault
          [explore: the 4096-wide residue].
The helpers (job, ctl, rule_obs, outcome, dims, lost_cmp, right_pixels) are set A's score/score_r.py, imported unchanged; the header
readers take the r6-kernel's td.rgn (gen/layout_b.py).  Refuses to score unless `run/freeze_k.sh verify B` passes.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import layout_b as B  # noqa: E402
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import score_r as S  # noqa: E402
import scorekit as K  # noqa: E402

PRED = {}
STAGE_NAMES = ("s0b", "b", "k", "r")
S0B_CTL = ("s0b-1x-1024x768", "s0b-1xf-1024x768", "s0b-4x-288x144", "s0b-4x-1024x768")
B_CTL = "b9-1024x768"
B_ROWS = ("b1-1280x1024", "b2-1184x768", "b3-1024x800", "b4-2048x240", "b5-768x2048", "b6-2048x1536", "b7-1280x768", "b8-1024x1024")
K_CTL = ("k1-1280x1024-room4000", "k5-1024x768-room4000")
K_ROWS = ("k2-1280x1024-roomb000", "k4-1024x768-room3000")
K_HELD = "k3-1280x1024-rooma000-held"
R_ROWS = ("r2-2048x2032", "r1-4096x960")
R_OVER = "r3-4096x1152"


def preds():
    for st in STAGE_NAMES + ("kh",):
        PRED[st] = L.load_predictions(st + ".tsv")


def verify_freeze():
    r = subprocess.run([os.path.join(L.KP, "run", "freeze_k.sh"), "verify", "B"], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def room_of(row):
    m = re.search(r"(?:^| )room:(0x[0-9a-f]+)", row.get("knobs") or "")
    return int(m.group(1), 16) if m else 0


def s0b_stage(outdir):
    P = PRED["s0b"]
    cases = L.read_cases(outdir)
    res, lines = {}, []
    for n in S0B_CTL:
        v, t = S.ctl(S.job(outdir, cases, n), P, n)
        res[n] = v
        lines.append("%s: %s: %s" % (n, v, t))
    g = K.gate(res)
    return lines, {"verdicts": res, "gate": g, "summary": "s0b: controls %s; later stages %s" % (res, "open" if g.ok else "CLOSED (set B is void)")}


def s0b_controls(sdir):
    if sdir and os.path.exists(os.path.join(sdir, "cases.tsv")):
        return dict(("s0b:" + k, v) for k, v in s0b_stage(sdir)[1]["verdicts"].items())
    return dict(("s0b:" + n, "NODATA") for n in S0B_CTL)


def gate(stage, roots):
    if stage == "s0b":
        return 0, "gate s0b: no prerequisite"
    d = S.stage_dir(roots, "s0b")
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        return 1, "gate %s: closed: no s0b stage was kept (run: run/k.sh --set B --only s0b)" % stage
    _, r = s0b_stage(d)
    if not r["gate"].ok:
        return 1, "gate %s: closed: s0b controls %s (set B is void: the lead decides)\ns0b at %s" % (stage, "; ".join(r["gate"].problems), d)
    return 0, "gate %s: open (s0b's four controls passed)\ns0b at %s" % (stage, d)


def where(outdir, stage):
    att = os.path.dirname(os.path.abspath(outdir))
    g = os.path.join(att, "gate-%s.txt" % stage)
    if os.path.exists(g):
        m = re.search(r"^s0b at (\S+)$", open(g).read(), re.M)
        if m and os.path.exists(os.path.join(m.group(1), "cases.tsv")):
            return m.group(1)
    return os.path.join(att, "s0b")


def aux_b(j, P, n):
    """A completed row's side quantities against the r6-kernel layout (reported; never the verdict)."""
    if j["miss"]:
        return j["miss"]
    g = S.got_of(j)
    w, h, mw, mh = S.dims(j["row"]["args"])
    base = B.layout(mw, mh, True, room_of(j["row"]))["rgn"]
    off = B.headers_off(j["tadata"], w, h, base)
    nz = L.nonzero_below(j["tadata"], base)
    got = {"pb_used": g["pb_used"], "tadata_size": g["tadata_size"], "hdr_off": None if off is None else str(len(off)),
           "nonzero_below_rgn": None if nz is None else str(nz)}
    out = []
    for q in ("pb_used", "tadata_size", "hdr_off", "nonzero_below_rgn"):
        want = L.pred_or(P, n, q)
        if want is None and got[q] is None:
            continue
        out.append("%s %s%s" % (q, got[q], "" if got[q] == want else " (frozen %s: DIFFERS)" % want))
    return "; ".join(out)


def row_state(j, P, n):
    """(observation, state, text): observation complete | fault | overflow | None; state against the frozen outcome."""
    want = L.pred(P, n, "outcome")
    if j["void"]:
        return None, None, S.void_text(j)
    oc, fi = S.outcome(j)
    if oc == "overflow":
        ob, t = ("overflow", "-ENOSPC (the scene overflowed), no fault") if j["row"]["class"] == "ok" else (None, "overflow with class %s" % j["row"]["class"])
    else:
        ob, t = S.rule_obs(j)
        dc = L.diff_count(j.get("out"))
        if ob is None and oc == "other" and j["row"]["class"] == "ok" and dc and dc[0] > 0:
            ob, t = "wrong", "completed with %d of %d pixels wrong" % dc
    if ob is None:
        return None, None, t
    st = ob == want
    extra = ""
    if ob == "complete" and j.get("tadata") is not None:
        extra = "; " + aux_b(j, P, n)
    elif ob == "fault":
        extra = "; right pixels before the fault %s (explore)" % S.right_pixels(j)
    return ob, st, "%s (frozen %s: %s)%s" % (t, want, "held" if st else "FAILED", extra)


def stage_rows(stage, outdir, names):
    P = PRED[stage]
    cases = L.read_cases(outdir)
    out = {}
    for n in names:
        j = S.job(outdir, cases, n)
        out[n] = (j,) + row_state(j, P, n)
    return out


def b_stage(outdir, s0dir=None):
    ctls = s0b_controls(s0dir or where(outdir, "b"))
    rs = stage_rows("b", outdir, (B_CTL,) + B_ROWS)
    lines = []
    j, ob, st, t = rs[B_CTL]
    ctls[B_CTL] = {True: "PASS", False: "FAILED", None: "NODATA"}[st]
    lines.append("%s (control): %s: %s" % (B_CTL, ctls[B_CTL], t))
    rows = []
    for n in B_ROWS:
        j, ob, st, t = rs[n]
        rows.append(st)
        lines.append("%s: %s" % (n, t if "row" in j else "not run (%s)" % "; ".join(j["void"])))
    claim = ("H-ROOM: with the r6-kernel's automatic 4x room the eight own-maximum cells that faulted on the rgn4 kernel complete with "
             "0 wrong (b1-b8)")
    hl = K.headline(claim, ctls, rows)
    return lines, {"controls": ctls, "rows": rows, "hroom": hl, "summary": "b: %s" % hl}


def k_stage(outdir, s0dir=None):
    ctls = s0b_controls(s0dir or where(outdir, "k"))
    rs = stage_rows("k", outdir, K_CTL + K_ROWS + (K_HELD,))
    lines = []
    for n in K_CTL:
        j, ob, st, t = rs[n]
        ctls[n] = {True: "PASS", False: "FAILED", None: "NODATA"}[st]
        lines.append("%s (control): %s: %s" % (n, ctls[n], t))
    rows = []
    for n in K_ROWS:
        j, ob, st, t = rs[n]
        rows.append(st)
        lines.append("%s: %s" % (n, t))
    j, ob, st, t = rs[K_HELD]
    held = "cannot tell"
    if ob == "fault":
        w, h, mw, mh = S.dims(j["row"]["args"])
        base = B.layout(mw, mh, True, room_of(j["row"]))["rgn"]
        want = [int(x, 16) for x in L.pred(PRED["kh"], K_HELD, "lost").split(",")]
        got = B.lost_offsets(j["heldtadata"], w, h, base)
        if got is None:
            st, held = None, "held TA data not read (%s bytes): the lost set cannot tell" % (None if j["heldtadata"] is None else len(j["heldtadata"]))
        else:
            held, eq = S.lost_cmp(got, want)
            st = eq
            if got:
                held += "; lost from 0x%x to 0x%x, header 0 %s (frozen %s)" % (min(got), max(got), "lost" if min(got) == base else "intact",
                                                                              L.pred(PRED["kh"], K_HELD, "header0_lost"))
        hp = j["heldparam"]
        if hp is not None and len(hp) >= 4096:
            held += "; held scene pages %d (explore)" % M.pages_nonzero(hp)
    rows.append(st)
    lines.append("%s (held): %s; lost offsets: %s" % (K_HELD, t, held))
    claim = ("H-TPM's exact limit through the knob: 1280 x 1024 completes with the room at 0xb000 (td.rgn 0xe000, entries end 0xd800) "
             "and faults one page lower losing exactly the frozen 171 offsets; 1024 x 768 faults with the room at 0x3000")
    hl = K.headline(claim, ctls, rows)
    return lines, {"controls": ctls, "rows": rows, "htpm": hl, "held": held, "summary": "k: %s" % hl}


def r_stage(outdir, s0dir=None):
    ctls = s0b_controls(s0dir or where(outdir, "r"))
    rs = stage_rows("r", outdir, R_ROWS + (R_OVER,))
    lines, rows = [], []
    for n in R_ROWS + (R_OVER,):
        j, ob, st, t = rs[n]
        rows.append(st)
        lines.append("%s%s: %s" % (n, " (explore)" if n != "r2-2048x2032" else "", t if "row" in j else "not run (%s)" % "; ".join(j["void"])))
    claim = "the largest targets: 2048 x 2032 and 4096 x 960 complete with 0 wrong; 4096 x 1152 ends in -ENOSPC without a fault [explore]"
    hl = K.headline(claim, ctls, rows)
    return lines, {"controls": ctls, "rows": rows, "r": hl, "summary": "r: %s" % hl}


def score_stage(st, outdir):
    if st == "s0b":
        return s0b_stage(outdir)
    return {"b": b_stage, "k": k_stage, "r": r_stage}[st](outdir)


def verdict(roots):
    out = []
    s0d = S.stage_dir(roots, "s0b")
    if not os.path.exists(os.path.join(s0d, "cases.tsv")):
        out.append("SUMMARY: set B: not run (no kept stage s0b)")
    else:
        out.append("SUMMARY: set B: %s" % s0b_stage(s0d)[1]["summary"])
    for st, f, key, label in (("b", b_stage, "hroom", "H-ROOM (b)"), ("k", k_stage, "htpm", "H-TPM knob (k)"), ("r", r_stage, "r", "largest (r)")):
        d = S.stage_dir(roots, st)
        if not os.path.exists(os.path.join(d, "cases.tsv")):
            out.append("SUMMARY: %s: not run (no kept stage %s)" % (st, st))
            continue
        r = f(d, s0d)[1]
        out.append("SUMMARY: %s: %s" % (label, r[key]))
        if st == "k":
            out.append("SUMMARY: k3: %s" % r["held"])
    return "\n".join(out)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    ok, msg = verify_freeze()
    if not ok:
        print("FROZEN FILES CHANGED (set B): refusing to score\n%s" % msg)
        return 3
    preds()
    if argv[1] == "verdict":
        print(verdict(argv[2:]))
        return 0
    if argv[1] == "gate":
        code, m = gate(argv[2], argv[3:])
        print(m)
        return code
    st, outdir = argv[1], argv[2]
    if st not in STAGE_NAMES:
        print("unknown stage %s" % st)
        return 2
    lines, r = score_stage(st, outdir)
    print("\n".join(lines))
    print("SUMMARY: %s" % r["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
