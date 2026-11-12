#!/usr/bin/env python3
"""score_dump.py: the r7-rp `dump` area's scorer (stages q293 and q139), frozen before the run.  Standard library and the
session's own modules (scorekit, lib_dump and its byte copies of resgx545 1c64f3a pbdump.py and region_tiles.py).

  score_dump.py STAGE KEPT                 rows, then one SUMMARY line (exit 0 also when it cannot tell)
  score_dump.py gate STAGE KEPT            0: neither stage has a driver gate
  score_dump.py verdict ATT_DIR            the SUMMARY lines of Q293 and Q139 (ATT_DIR/q293, ATT_DIR/q139)
  score_dump.py q139-fitdata KEPT          the fold's input: per FIT row, per target tile, the baseline's header slot, the
                                           slots that name the tile in the row's dump, wrong or not (fit rows only)
  score_dump.py q139-heldout KEPT MODEL_SHA [MODEL]
                                           the held-out rows, read only now: MODEL (default KEPT/../q139-model.json) must
                                           hash to MODEL_SHA (sha256) or nothing is read

q293 (plan 3.5; E897 post hoc, E829, E888).  Controls: u1 (no poke, three renders: objects at dwords 0, 27, 54, each with a
zero at +11 and the format word 0x00040101 at +12; render 3 draws 0 triangle pixels) and u2 (E888's t7 again: its kept dump
head, render 2's counts, diff count, target hash and the applied poke).  Rows (gated): u3, the twin's words poked into
render 2's object (3:par:38..53): H-READ2 holds with 4096 triangle, 0 background, 0 other and diff 0 (rival: 0 triangle);
u4, 0xffffffff at dword 38: H-READ2 holds with 0 triangle pixels.  A row whose pokes did not land (the kernel's 'applied'
lines and the dump's dwords) cannot tell.
q139 (plan 3.6; E877).  Controls: the unpoked 256 x 256 and 640 x 480 baselines (an exact image, read from --pixels, and
every target tile with exactly one region header with a stream whose block decodes) and the poked exact control m1-B1-5
(exact image, every header at its baseline's slot).  Replication gate: a case's wrong-tile set must equal the one its
dataset kept (predictions kept_wrong); a case that does not replicate is DROPPED from its set (never a row).  H-MOVED
[infer], frozen, scored on the fit rows (and the replicate, combined with its fit row): a tile is wrong iff its region
header is not at the slot the baseline of the same size has it at (word 0's position at that slot names another tile or
none).  Rival H-INPLACE: a wrong tile with its header in place.  A third outcome, headers moved for tiles that drew, is
reported.  score() never reads a held-out row's files and prints nothing about them but their count.
The q139-heldout model file (JSON, written by the fold after reading q139-fitdata, hashed and committed before this runs):
  {"model": "<name>", "cases": {"<held-out row name>": {"wrong": ["x.y", ...], "slots": {"x.y": <slot> | null, ...}}}}
"wrong" (required for every held-out row of the table): the tiles the model predicts wrong; "slots" (optional): the
header slot the model predicts for each target tile (null: no header).  Scored per replicated held-out row: the model's
wrong set equal to the observed one; slots compared tile by tile (reported); H-MOVED per tile on the held-out rows too.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_dump as L  # noqa: E402
import scorekit as K  # noqa: E402

KP = os.path.dirname(HERE)
REQUIRED = {
    "q293": ("cases.tsv", ".txt", ".dmesg", ".tri.param.bin"),
    "q139": ("cases.tsv", ".txt", ".tri.param.bin", ".tri.tadata.bin"),
}
U1, U2, U3, U4 = "q293-u1-ctl-n3", "q293-u2-ctl-t7", "q293-u3-obj2-twin", "q293-u4-obj2-ffff"
VOID_RC = (2, 124, 125, 126, 127)


def preds(stage, kp=KP):
    return L.load_predictions(os.path.join(kp, "predictions", stage + ".tsv"))


# ---- one job ---------------------------------------------------------------------------------------------------------------------
def job(kept, cases, name, need=(".txt",)):
    """{'name', 'row', 'void': [...], files...}: a job is void (no data) when it did not run, its rc is not the tool's, its
    class is not ok, or a file it needs is missing."""
    j = {"name": name, "void": []}
    row = (cases or {}).get(name)
    if row is None:
        j["void"].append("no cases.tsv row (not run)")
        return j
    j["row"] = row
    rc = row.get("rc", "")
    if not rc.lstrip("-").isdigit() or int(rc) in VOID_RC or int(rc) >= 128:
        j["void"].append("rc %r is not a result of the tool" % rc)
    if row.get("class") != "ok":
        j["void"].append("class %s" % row.get("class"))
    for s in need:
        key = s.strip(".").replace(".", "_")
        j[key] = L.read_bytes(os.path.join(kept, name + s))
        if j[key] is None or (not j[key] and s != ".dmesg"):      # an empty kernel-log slice is a reading
            j["void"].append("%s%s missing or empty (READER-MISS if the row wrote it)" % (name, s))
    j["text"] = None if j.get("txt") is None else j["txt"].decode("utf-8", "replace")
    j["kmsg"] = None if j.get("dmesg") is None else j["dmesg"].decode("utf-8", "replace")
    return j


def void(j):
    return "cannot tell: " + "; ".join(j["void"])


# ---- q293 ------------------------------------------------------------------------------------------------------------------------
Q293_NEED = (".txt", ".dmesg", ".tri.param.bin")


def u1_reading(param, text):
    """(state, text) of u1's control reading: objects at 0, 27, 54 (each zero at +11, format at +12), render 3 0 triangle."""
    if param is None or text is None:
        return "NODATA", "no dump or no output"
    objs = L.objects(L.dwords(param, 4096))
    starts = [o[0] for o in objs]
    lay = [(o[0], o[1], o[2]) for o in objs]
    c3 = L.tri_counts(text, 3)
    if c3 is None:
        return "NODATA", "no render 3 result line; objects %s" % lay
    bad = []
    if starts[:3] != [0, 27, 54]:
        bad.append("objects at %s, frozen 0, 27, 54" % starts)
    for s, off, before in objs[:3]:
        if off != 12 or before != 0:
            bad.append("object at %d: format word at +%s, dword before it %s (frozen +12, 0)" % (
                s, off, "%#x" % before if before is not None else None))
    if c3[0] != 0:
        bad.append("render 3: %s (frozen 0 triangle)" % L.counts_text(c3))
    extra = "; %d objects found" % len(objs) + (" (a fourth at %d)" % starts[3] if len(starts) > 3 else "")
    if bad:
        return "FAILED", "; ".join(bad) + extra
    return "PASS", "objects at 0, 27, 54, each +11 zero, +12 0x00040101; render 3: %s%s" % (L.counts_text(c3), extra)


def u2_reading(param, text, kmsg, P):
    """(state, text) of u2 against E888's t7 (frozen from its kept files)."""
    if param is None or text is None:
        return "NODATA", "no dump or no output"
    got = {"dump_head": ",".join("%08x" % x for x in L.dwords(param, 64)),
           "tri2": L.counts_text(L.tri_counts(text, 2)),
           "diff": None if L.diff_count(text) is None else "%d of %d" % L.diff_count(text),
           "target_hash": L.target_hash(text),
           "kpoke": ",".join(L.kpoke_applied(kmsg)) if kmsg is not None else None}
    bad, none = [], []
    for q, v in got.items():
        want = L.pred(P, U2, q)
        if v is None or v == "":
            none.append(q)
        elif v != want:
            bad.append("%s %s, frozen %s" % (q, v if len(v) < 50 else v[:46] + "...", want if len(want) < 50 else want[:46] + "..."))
    if bad:
        return "FAILED", "; ".join(bad)
    if none:
        return "NODATA", "nothing read for %s" % ", ".join(none)
    return "PASS", "as E888's t7 (dump head 0-63, render 2 %s, diff %s, hash %s, poke applied)" % (
        got["tri2"], got["diff"], got["target_hash"])


def landed(j, P, name):
    """Whether every frozen kpoke of the row was applied (kernel lines) and is in the dump; (ok, text)."""
    want = L.pred(P, name, "kpoke").split(",")
    got = L.kpoke_applied(j["kmsg"])
    w = L.dwords(j["tri_param_bin"], 64)
    miss = [s for s in want if s not in got]
    wrong = []
    for s in want:
        d, v = s[4:].split("=")
        if w[int(d)] != int(v, 16):
            wrong.append("dword %s 0x%08x" % (d, w[int(d)]))
    if miss or wrong:
        return False, "the pokes did not land (%d of %d applied lines missing; %s)" % (
            len(miss), len(want), "; ".join(wrong[:4]) or "dump as poked")
    return True, "%d of %d pokes applied and in the dump" % (len(want), len(want))


def u3_row(j, P):
    if j["void"]:
        return None, void(j)
    ok, t = landed(j, P, U3)
    if not ok:
        return None, "cannot tell: " + t
    c3, d = L.tri_counts(j["text"], 3), L.diff_count(j["text"])
    if c3 is None or d is None:
        return None, "cannot tell: no render 3 line or diff line"
    ct, dt = L.counts_text(c3), "%d of %d" % d
    if ct == L.pred(P, U3, "tri3", "H-READ2") and dt == L.pred(P, U3, "diff", "H-READ2"):
        return True, "H-READ2 held: %s; render 3: %s, diff %s (render 2's object, put in the bit-29-set layout, drew)" % (t, ct, dt)
    if c3[0] == 0:
        return False, "rival: %s; render 3: %s: render 2's object in the bit-29-set layout drew nothing" % (t, ct)
    return False, "%s; render 3: %s, diff %s (frozen %s, %s): neither H-READ2 nor the rival" % (
        t, ct, dt, L.pred(P, U3, "tri3", "H-READ2"), L.pred(P, U3, "diff", "H-READ2"))


def u4_row(j, P):
    if j["void"]:
        return None, void(j)
    ok, t = landed(j, P, U4)
    if not ok:
        return None, "cannot tell: " + t
    c3 = L.tri_counts(j["text"], 3)
    if c3 is None:
        return None, "cannot tell: no render 3 line"
    if c3[0] == 0:
        return True, "H-READ2 held: %s; render 3: %s" % (t, L.counts_text(c3))
    return False, "%s; render 3: %s (frozen 0 triangle): 0xffffffff at render 2's dword 11 drew" % (t, L.counts_text(c3))


Q293_CLAIM = ("Q293: render 2's own object is read as render 1's: put in the bit-29-set layout by a poke before render 3 it "
              "draws (u3, 4096 triangle pixels) and 0xffffffff at its dword 11 draws nothing (u4); three renders leave objects "
              "at 0, 27, 54 in the displaced layout and draw nothing (u1)")


def q293(kept, kp=KP):
    P = preds("q293", kp)
    cases = L.read_cases(kept)
    lines, ctls, rows = [], {}, {}
    js = {n: job(kept, cases, n, Q293_NEED) for n in (U1, U2, U3, U4)}
    j = js[U1]
    ctls[U1], t = ("NODATA", void(j)) if j["void"] else u1_reading(j["tri_param_bin"], j["text"])
    lines.append("%s (control): %s: %s" % (U1, ctls[U1], t))
    j = js[U2]
    ctls[U2], t = ("NODATA", void(j)) if j["void"] else u2_reading(j["tri_param_bin"], j["text"], j["kmsg"], P)
    lines.append("%s (control): %s: %s" % (U2, ctls[U2], t))
    for n, f in ((U3, u3_row), (U4, u4_row)):
        rows[n], t = f(js[n], P)
        lines.append("%s (held out): %s" % (n, t))
    head = K.headline(Q293_CLAIM, ctls, [rows[U3], rows[U4]])
    return lines, "q293: " + head, {"controls": ctls, "rows": rows}


# ---- q139 ------------------------------------------------------------------------------------------------------------------------
Q139_NEED = (".txt", ".tri.param.bin", ".tri.tadata.bin")


def q139_table(P):
    """{row: (set, w, h, ds_case)} from the frozen predictions."""
    out = {}
    for (case, q), vals in P.items():
        if q == "size":
            w, h = (int(x) for x in vals[0][0].split("x"))
            out[case] = (vals[0][2], w, h, L.pred(P, case, "ds_case"))
    return out


def image_reading(j, w, h):
    """(complete, wrong tile set) of a job's --pixels output, None when void."""
    if j["void"]:
        return None
    return L.image_tiles(j["text"], w, h)


def baselines(kept, cases, P, tab):
    """{(w, h): layout or None}, the control states and lines."""
    lay, ctls, lines = {}, {}, []
    for n, (st, w, h, _) in sorted(tab.items()):
        if st != "control" or L.pred(P, n, "kept_count") != "0" or (n, "headers") not in P:
            continue
        j = job(kept, cases, n, Q139_NEED)
        if j["void"]:
            ctls[n], t, lay[(w, h)] = "NODATA", void(j), None
        else:
            complete, bad = L.image_tiles(j["text"], w, h)
            ok, t, ly = L.baseline_layout(j["tri_tadata_bin"], j["tri_param_bin"], w, h)
            img = "exact" if complete and not bad and L.diff_count(j["text"]) == (0, w * h) else \
                "image %s, %d wrong tiles, diff %s" % ("complete" if complete else "INCOMPLETE", len(bad), L.diff_count(j["text"]))
            ctls[n] = "PASS" if ok and img == "exact" else "FAILED"
            lay[(w, h)] = ly if ok else None
            t = "image %s; headers: %s" % (img, t)
        lines.append("%s (control, baseline %dx%d): %s: %s" % (n, w, h, ctls[n], t))
    return lay, ctls, lines


def poked_control(kept, cases, P, tab, lay):
    ctls, lines = {}, []
    for n, (st, w, h, _) in sorted(tab.items()):
        if st != "control" or (n, "headers_in_place") not in P:
            continue
        j = job(kept, cases, n, Q139_NEED)
        if j["void"]:
            ctls[n], t = "NODATA", void(j)
        elif lay.get((w, h)) is None:
            ctls[n], t = "NODATA", "no baseline layout of %dx%d" % (w, h)
        else:
            complete, bad = L.image_tiles(j["text"], w, h)
            moved, emptied = L.moved_tiles(j["tri_tadata_bin"], lay[(w, h)], w, h)
            ok = complete and not bad and not moved
            ctls[n] = "PASS" if ok else "FAILED"
            t = "image %s, %d wrong tiles; %d headers moved, %d emptied" % (
                "complete" if complete else "INCOMPLETE", len(bad), len(moved), len(emptied))
        lines.append("%s (control, poked, exact): %s: %s" % (n, ctls[n], t))
    return ctls, lines


def replicated(j, w, h, P, n):
    """(state, wrong set, text): True when the job's wrong-tile set is its dataset's (kept_wrong), False when not (the case
    is dropped), None when it has no whole image."""
    r = image_reading(j, w, h)
    if r is None:
        return None, None, void(j)
    complete, bad = r
    if not complete:
        return None, bad, "cannot tell: the image is not whole"
    want = L.tiles_parse(L.pred(P, n, "kept_wrong"))
    if bad == want:
        return True, bad, "replicates (%d wrong tiles, as kept)" % len(bad)
    return False, bad, "does NOT replicate: %d wrong tiles, kept %d (common %d): dropped" % (len(bad), len(want), len(bad & want))


def hmoved_row(j, w, h, layout, bad):
    """(state, text, detail) of H-MOVED on one replicated job."""
    moved, emptied = L.moved_tiles(j["tri_tadata_bin"], layout, w, h)
    inplace_wrong = bad - moved
    moved_drew = moved - bad
    t = "%d wrong, %d moved, %d both, %d wrong in place (H-INPLACE), %d moved that drew, %d emptied in place" % (
        len(bad), len(moved), len(bad & moved), len(inplace_wrong), len(moved_drew), len(emptied))
    if not inplace_wrong and not moved_drew:
        return True, "H-MOVED held: " + t, (moved, emptied, inplace_wrong, moved_drew)
    word = []
    if inplace_wrong:
        word.append("H-INPLACE (e.g. %s)" % L.tiles_text(sorted(inplace_wrong)[:3]))
    if moved_drew:
        word.append("headers moved for tiles that drew (e.g. %s)" % L.tiles_text(sorted(moved_drew)[:3]))
    return False, "H-MOVED FAILED: %s: %s" % (t, "; ".join(word)), (moved, emptied, inplace_wrong, moved_drew)


Q139_CLAIM = ("Q139 H-MOVED: a tile of a poked macrotile word is wrong iff its region header is not at the slot the baseline "
              "of its size has it at (fit rows)")


def q139(kept, kp=KP):
    P = preds("q139", kp)
    tab = q139_table(P)
    cases = L.read_cases(kept)
    lay, ctls, lines = baselines(kept, cases, P, tab)
    c2, l2 = poked_control(kept, cases, P, tab, lay)
    ctls.update(c2)
    lines += l2
    states, dropped, third, inplace = {}, [], [], []
    for n, (st, w, h, case) in sorted(tab.items(), key=lambda kv: kv[0]):
        if st not in ("fit", "replicate"):
            continue
        j = job(kept, cases, n, Q139_NEED)
        rep, bad, t = replicated(j, w, h, P, n)
        if rep is not True:
            states.setdefault(case, []).append(("dropped" if rep is False else None, n))
            if rep is False:
                dropped.append(n)
            lines.append("%s (%s, %s): %s" % (n, st, case, t))
            continue
        if lay.get((w, h)) is None:
            states.setdefault(case, []).append((None, n))
            lines.append("%s (%s): %s; H-MOVED cannot tell: no baseline layout of %dx%d" % (n, st, t, w, h))
            continue
        s, ht, det = hmoved_row(j, w, h, lay[(w, h)], bad)
        if det[2]:
            inplace.append(n)
        if det[3]:
            third.append(n)
        states.setdefault(case, []).append((s, n))
        lines.append("%s (%s): %s; %s" % (n, st, t, ht))
    rows = []
    for case, ss in sorted(states.items()):
        if any(s == "dropped" for s, _ in ss):
            lines.append("case %s: dropped (does not replicate in %s)" % (case, ", ".join(n for s, n in ss if s == "dropped")))
            continue
        if len(ss) > 1:
            c = K.combine([s for s, _ in ss])
            lines.append("case %s with its replicate: %s" % (case, c))
            rows.append({"held": True, "refuted": False}.get(c))
        else:
            rows.append(ss[0][0])
    held_out = [n for n, (st, *_r) in tab.items() if st == "heldout"]
    lines.append("held out: %d rows kept, not read here (score_dump.py q139-heldout KEPT MODEL_SHA after the fold's model)"
                 % len(held_out))
    head = K.headline(Q139_CLAIM, ctls, rows)
    extra = []
    if inplace:
        extra.append("H-INPLACE in %d fit rows" % len(inplace))
    if third:
        extra.append("headers moved for tiles that drew in %d fit rows" % len(third))
    if dropped:
        extra.append("%d fit rows dropped (no replication)" % len(dropped))
    return lines, "q139: " + head + ("; " + "; ".join(extra) if extra else ""), {"controls": ctls, "rows": rows,
                                                                                    "layouts": lay}


def q139_fitdata(kept, kp=KP):
    """The fold's placement data, fit rows only: per row and tile 'x.y baseline-slot observed-slots wrong'."""
    P = preds("q139", kp)
    tab = q139_table(P)
    cases = L.read_cases(kept)
    lay, ctls, lines = baselines(kept, cases, P, tab)
    out = lines[:]
    for n, (st, w, h, case) in sorted(tab.items()):
        if st not in ("fit", "replicate"):
            continue
        j = job(kept, cases, n, Q139_NEED)
        rep, bad, t = replicated(j, w, h, P, n)
        out.append("== %s %s %dx%d %s" % (n, case, w, h, t))
        if rep is not True or lay.get((w, h)) is None:
            continue
        base = lay[(w, h)]
        obs = L.observed_slots(j["tri_tadata_bin"], base["base"], w, h)
        for tile in sorted(L.target_tiles(w, h), key=lambda q: (q[1], q[0])):
            out.append("%d.%d %d %s %s" % (tile[0], tile[1], base["slot"][tile], ",".join(map(str, obs.get(tile, []))) or "-",
                                           "wrong" if tile in bad else "drawn"))
    return out


def q139_heldout(kept, model_sha, model_path=None, kp=KP):
    """The held-out rows, after the fitted model: (lines, summary)."""
    model_path = model_path or os.path.join(os.path.dirname(os.path.abspath(kept)), "q139-model.json")
    if not os.path.exists(model_path):
        return ["no model file %s" % model_path], "q139 held out: cannot tell: no fitted model file (nothing read)"
    with open(model_path, "rb") as f:
        raw = f.read()
    got = hashlib.sha256(raw).hexdigest()
    if got != model_sha.lower():
        return ["model %s sha256 %s, given %s" % (model_path, got, model_sha)], \
            "q139 held out: REFUSED: the model file does not hash to the given sha256 (nothing read)"
    model = json.loads(raw.decode())
    P = preds("q139", kp)
    tab = q139_table(P)
    ho = sorted(n for n, (st, *_r) in tab.items() if st == "heldout")
    lack = [n for n in ho if n not in model.get("cases", {}) or "wrong" not in model["cases"][n]]
    if lack:
        return ["the model has no 'wrong' set for %s" % ", ".join(lack)], \
            "q139 held out: REFUSED: the model does not predict every held-out row (nothing read)"
    cases = L.read_cases(kept)
    lay, ctls, lines = baselines(kept, cases, P, tab)
    lines.insert(0, "model %s sha256 %s (%s)" % (model_path, got, model.get("model", "?")))
    rows, hm = [], []
    for n in ho:
        st, w, h, case = tab[n]
        j = job(kept, cases, n, Q139_NEED)
        rep, bad, t = replicated(j, w, h, P, n)
        if rep is not True:
            lines.append("%s (%s): %s" % (n, case, t))
            continue
        mw = L.tiles_parse(",".join(model["cases"][n]["wrong"]) or "none")
        s = mw == bad
        rows.append(s)
        txt = "model %s (predicted %d wrong, observed %d, common %d)" % ("held" if s else "FAILED", len(mw), len(bad),
                                                                         len(mw & bad))
        if lay.get((w, h)) is not None:
            hs, ht, _ = hmoved_row(j, w, h, lay[(w, h)], bad)
            hm.append(hs)
            txt += "; " + ht
            slots = model["cases"][n].get("slots")
            if slots:
                obs = L.observed_slots(j["tri_tadata_bin"], lay[(w, h)]["base"], w, h)
                agree = sum(1 for k, v in slots.items()
                            if (v is None and not obs.get(tuple(int(x) for x in k.split(".")))) or
                            (v is not None and v in obs.get(tuple(int(x) for x in k.split(".")), [])))
                txt += "; header slots as the model predicts for %d of %d tiles" % (agree, len(slots))
        lines.append("%s (%s): %s; %s" % (n, case, t, txt))
    head = K.headline("Q139 held out: the fitted placement model predicts the held-out wrong-tile sets", ctls, rows)
    return lines, "q139 held out: %s; H-MOVED on the held-out rows: %s" % (head, K.tally(hm))


# ---- the contract's entry points -------------------------------------------------------------------------------------------------
def score(stage, kept):
    if stage == "q293":
        lines, summary, _ = q293(kept)
    elif stage == "q139":
        lines, summary, _ = q139(kept)
    else:
        raise ValueError("score_dump.py scores q293 and q139, not %r" % stage)
    return summary, lines


def gate(stage, kept):
    return 0


def verdict(att_dir):
    out = []
    for st in ("q293", "q139"):
        d = os.path.join(att_dir, st)
        if not os.path.exists(os.path.join(d, "cases.tsv")):
            out.append("SUMMARY: %s: not run (no kept stage %s)" % (st, st))
            continue
        s, _ = score(st, d)
        out.append("SUMMARY: " + s)
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    if argv[1] == "gate" and len(argv) == 4:
        print("gate %s: no driver gate" % argv[2])
        return gate(argv[2], argv[3])
    if argv[1] == "verdict" and len(argv) == 3:
        print("\n".join(verdict(argv[2])))
        return 0
    if argv[1] == "q139-fitdata" and len(argv) == 3:
        print("\n".join(q139_fitdata(argv[2])))
        return 0
    if argv[1] == "q139-heldout" and len(argv) in (4, 5):
        lines, s = q139_heldout(argv[2], argv[3], argv[4] if len(argv) == 5 else None)
        print("\n".join(lines))
        print("SUMMARY: " + s)
        return 0
    if argv[1] in ("q293", "q139") and len(argv) == 3:
        s, lines = score(argv[1], argv[2])
        print("\n".join(lines))
        print("SUMMARY: " + s)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
