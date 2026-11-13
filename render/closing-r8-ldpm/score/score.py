#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r8-ldpm's frozen scorer. Every verdict rule comes from kit/scorekit.py, the kept files
are read through kit/kitscore.py (byte copies of resgx545 91f21da, pinned in FROZEN.commits) and
one job's output through score/read.py (R7-dpm's reader).

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL and ROW lines, MODEL tallies, SUMMARY lines
  score.py gate STAGE ROOTS...         exit 0 when every control of a0 passed (sp to u)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A row is scored only when its job completed (kitscore.completed) and its knob proof holds (0x0624
read = the row's thr0); otherwise it is cannot tell. A control passes when every value it is
frozen with holds: a number (ctl:, CTL) equal, a step S_k inside the bracket its job read. The
stage's controls gate its rows (scorekit.gate). Per model of predictions/STAGE.tsv the scorer
tallies held, FAILED and cannot tell over the rows it predicts; the plan's verdicts:

  sp  H-STEPMODEL against H-R7S6 (2048x3072 S6) and H-KEPTS3 (2048x4096 S3): gps_abort per cell
      (1 + the steps below thr0), S_k inside the calibrations' brackets
  m6  H-SPAN against H-BIG6, H-ANY6 and H-6LATE (tallied) at the A_6 cell of each target, aligned
      on its calibration (R7's rule: the run's cell thr0 is the model's cell thr0 - (S_6 read -
      S_6 model)); a calibration without S_6 or an aligned A_6 outside the run's window voids its
      target (cannot tell); the fit rows (3072x3072, 2560x2560 mapped) score nothing
  v   H-DET: the three written N 8 calibrations give the same steps, need and object block sizes
      (their dumps, read as OL7 (a) reads them); one differing refutes it (and P3); explore rows
      tallied only
  f9  F9's count and run peaks; rivals E854's d = 7/4 and d = 1 (counts), E625 (an overflow iff
      thr0 < U); a first run with no sample (run peak 0) is cannot tell (E916)
  k   HU1's need at the five calibrations (held out); H-KICKS against H-UNION (explore)
  u   HU1 against H-BBOX: the need of each shape's calibration

REQUIRED: the files each stage reads (the runner and sessioncheck.py kept check them);
read_files(STAGE, DIR) reads exactly those; producible(row) is the set of reading keys the row's
job can produce (score/read.py's words: the freeze refuses a control that reads anything else)."""
import collections
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import read as R  # noqa: E402
import plan as PL  # noqa: E402

STAGES = PL.STAGES
BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
DUMP = (".p1139-green.param.bin", ".p1139-green.tadata.bin")
REQUIRED = {s: BASE + (DUMP if s == "v" else ()) for s in STAGES}
GATES = {s: "a0" for s in STAGES if s != "a0"}
MAIN = {"sp": ("H-STEPMODEL", "H-R7S6", "H-KEPTS3"), "m6": ("H-SPAN", "H-BIG6", "H-ANY6", "H-6LATE"),
        "v": ("H-DET",), "f9": ("F9", "d=7/4", "d=1", "E625"), "k": ("HU1", "H-KICKS", "H-UNION"),
        "u": ("HU1", "H-BBOX")}


def producible(row):
    """The reading keys of the row's job by its frozen outcome: every job reads knob, nparts,
    gmax and runpeaks; a probe job its steps below min(thr0, U) and mono; a completed job its
    need; one with a partial render gps_abort and gps_left."""
    keys = {"knob", "nparts", "gmax", "runpeaks"}
    args = row["args"]
    thr0 = int(next(k for k in row["knobs"] if k.startswith("dbg:")).split("=")[1], 16) - PL.D_OFF
    w, h = PL.target(dict(args=args))
    if " probe " in f" {args} ":
        if "--vtx-coords" in args:
            U = PL.VCAL4[1] if "--vtx-coords 4" in args else 691
            S = PL.VCAL4[0] if "--vtx-coords 4" in args else {}
        else:
            S, A, B, U = PL.model(w, h)
        keys |= {f"s{k}" for k, v in S.items() if v < min(thr0, U)} | {"mono"}
    else:
        U = need_of(row)
    keys |= {"need"} if thr0 >= U else {"gps_abort", "gps_left"}
    return keys


def need_of(row):
    """HU1's U of a `tri` row (the frozen tables)."""
    a = row["args"]
    w, h = PL.target(row)
    if "--tri-v" in a:
        return next(s["U_hu1"] for s in PL.T["u"] if s["triv"] in a)
    if w == h == 4096 and "--move" not in a:
        return 287
    if "-n 1 " in a:
        return PL.S22[2]
    return next(s["U"] for s in PL.T["k"] if f"{s['w']}x{s['h']}" == f"{w}x{h}" and
                PL.tri(s["w"], s["h"], PL.k_moves(s)).split(" -- ", 1)[1].split(" ", 1)[1]
                .split(" --keep-going")[0] + " " in a)


# ---- reading ------------------------------------------------------------------------------------
def thr0_of(r):
    return int(next(k for k in r["knobs"] if k.startswith("dbg:")).split("=")[1], 16) - PL.D_OFF


def completed(c, text):
    """A kept row whose job ran to its end: kitscore.completed, or (post-run fix, POSTRUN-FIX.md)
    an `expectdiff` row of class ok that ended rc 1 with its diff line, as the runner took it."""
    if K.completed(c):
        return True
    words = c.get("knobs", "").split()
    return (c.get("class") == "ok" and c["rc"] == 1 and "expectdiff" in words
            and any(ln.startswith("diff:") for ln in text.splitlines()))


def readings(stage, d):
    cases = K.rows(d, "cases.tsv")
    out = {}
    for r in K.table(KP, stage):
        n = r["name"]
        c = cases.get(n)
        text = K.text(d, n + ".txt") if c is not None else ""
        if c is None or not completed(c, text):
            out[n] = None
            continue
        rd = R.reading(text)
        if rd.get("void") or rd.get("knob") != thr0_of(r):
            out[n] = None
            continue
        out[n] = rd
    return out


def value(rd, q):
    """A reading's value of quantity q, as the predictions write it (None: not read)."""
    if rd is None:
        return None
    if q.startswith("s") and q[1:].isdigit():
        return rd["iv"].get(int(q[1:]))
    if q == "runpeaks":
        return ",".join(f"0x{x:x}" for x in rd["runpeaks"]) if rd["runpeaks"] else None
    if q == "overflow":
        return str(int(rd["nparts"] >= 1))
    v = rd.get(q)
    if v is None:
        return None
    if isinstance(v, bool):
        return str(int(v))
    return v


def holds(got, want):
    """True / False / None of one predicted value against a reading's."""
    if got is None:
        return None
    if isinstance(got, tuple):                      # a step bracket (a, max(a, b - 1))
        return got[0] <= int(want, 16) <= got[1]
    if isinstance(got, int):
        return got == int(want, 0)
    return str(got) == want


# ---- controls -----------------------------------------------------------------------------------
def control_states(stage, rds, preds, rows):
    out, lines = {}, []
    for r in rows:
        if r["set"] != "control":
            continue
        n, rd = r["name"], rds[r["name"]]
        st, why = True, []
        for q, by in preds.get(n, {}).items():
            for mdl, v in by.items():
                if mdl not in ("CTL", "H-STEPMODEL", "R7-REPEAT"):
                    continue
                h = holds(value(rd, q), v)
                if h is not True:
                    why.append(f"{q} {value(rd, q)} (frozen {v})")
                    st = None if h is None and st is not False else False if h is False else st
        if rd is None:
            st = None
        out[n] = st
        lines.append(f"CONTROL {n}: {'PASS' if st else 'FAILED' if st is False else 'cannot tell'}"
                     + (": " + "; ".join(why) if why else ""))
    return out, lines


# ---- per-stage row states -------------------------------------------------------------------------
def plain_rows(stage, rds, preds, rows, skip=()):
    """{model: [(row, state, detail)]} over the predicted quantities of non-control rows."""
    res = collections.defaultdict(list)
    for r in rows:
        n = r["name"]
        if r["set"] == "control" or n in skip:
            continue
        for q, by in preds.get(n, {}).items():
            for mdl, v in by.items():
                if mdl == "CTL" or v.startswith("="):
                    continue
                got = value(rds[n], q)
                st = holds(got, v)
                if q == "runpeaks" and got and got.split(",")[0] == "0x0":
                    st = None                        # E916: a first run no sample fell in
                shown = ("[0x%x, 0x%x]" % got if isinstance(got, tuple) else
                         f"0x{got:x}" if isinstance(got, int) else got)
                res[mdl].append((r, st, f"{q} {shown} (frozen {v})"))
    return res


def m6_rows(rds, rows):
    res = collections.defaultdict(list)
    by_tag = collections.defaultdict(list)
    for r in rows:
        if r["set"] in ("heldout",) and "-cal-" not in r["name"]:
            by_tag[r["name"].split("-")[1]].append(r)
    for tag, cells in by_tag.items():
        w, h = PL.target(cells[0])
        S, A, B, U = PL.model(w, h)
        cal = rds.get(f"m6-cal-{tag}")
        iv = cal["iv"].get(6) if cal else None
        # R7's alignment: the model's S_6 inside the read bracket is no shift; else the run's
        # S_6 (max(a, b - 1), the bracket's top) less the model's; no S_6 read voids the target
        shift = None if iv is None else 0 if iv[0] <= S[6] <= iv[1] else iv[1] - S[6]
        runs = sorted(thr0_of(r) for r in cells)
        a6_run = A[6] + shift if shift is not None else None
        void = shift is None or not (runs[0] <= a6_run <= runs[-1])
        cls = PL.M6_CLASS[(w, h)]
        for r in cells:
            t = thr0_of(r)
            rd = rds.get(r["name"])
            got = rd["gps_left"] if rd else None
            tm = t - shift if shift is not None else None
            pr = {"H-SPAN": PL.span_left(tm, S, A) if not void else None}
            if not void and tm == A[6]:
                for mdl in ("H-BIG6", "H-ANY6", "H-6LATE"):
                    pr[mdl] = PL.M6_RIVALS[mdl][cls]
            for mdl, v in pr.items():
                if v is None or v == "?":
                    if mdl == "H-SPAN":
                        res[mdl].append((r, None, f"gps_left {got}: target void (calibration S6 {iv}, shift {shift})"
                                         if void else f"gps_left {got}: a step cell"))
                    continue
                st = None if got is None else got == v
                res[mdl].append((r, st, f"gps_left {got} (model cell 0x{tm:x}, frozen {v})"))
    return res


def v_rows(rds, d):
    res = collections.defaultdict(list)
    names = ["v-w8-1", "v-w8-2", "v-w8-3"]
    got = {}
    for n in names:
        rd = rds.get(n)
        if rd is None:
            got[n] = None
            continue
        try:
            sizes = blocks(os.path.join(d, n + ".p1139-green."))
        except Exception as e:  # noqa: BLE001  a dump the reader cannot read: cannot tell
            sizes = None
            print(f"NOTE {n}: dump not read ({e})")
        got[n] = (tuple(sorted(rd["S"].items())), rd["need"], tuple(sizes) if sizes else None)
    vals = [g for g in got.values()]
    if any(v is None or v[2] is None for v in vals):
        st = None
    else:
        st = all(v == vals[0] for v in vals)
    for n in names:
        g = got[n]
        res["H-DET"].append((dict(name=n, set="heldout"), st,
                             f"steps {len(g[0]) if g else '-'} need {g[1] if g else '-'} blocks "
                             f"{(len(g[2]), g[2][:6]) if g and g[2] else '-'}"))
    return res


def blocks(pre):
    """OL7 (a)'s object block sizes of one dump (gen/ol7/ol7_a_dumps.py blocks(), the readers
    imported pinned): the sizes in dwords by rank of ISP address on the global list."""
    import gzip
    import struct
    f3, pb = PINNED or _pinned()
    param = gzip.open(pre + "param.bin.gz").read()
    tad = gzip.open(pre + "tadata.bin.gz").read()
    seqs = []
    for r in f3.regions(tad, 2048, 2048):
        if r.stream:
            seqs.append([a for addr, ents, used in f3.chain(param, r.stream) for _, a, _, _ in ents])
    pages = sorted({a // 1024 for s in seqs for a in s})
    before = collections.defaultdict(set)
    for s in seqs:
        ps = []
        for a in s:
            if not ps or ps[-1] != a // 1024:
                ps.append(a // 1024)
        for x, y in zip(ps, ps[1:]):
            before[y].add(x)
    order, left = [], set(pages)
    while left:
        nxt = sorted(p for p in left if not (before[p] & left))
        if len(nxt) != 1:
            raise ValueError("global page order not total")
        order.append(nxt[0])
        left.discard(nxt[0])
    gpos = {p: i for i, p in enumerate(order)}
    lin = sorted({(gpos[a // 1024] * 1024 + a % 1024, a) for s in seqs for a in s})
    out = []
    for i, (la, a) in enumerate(lin):
        end = lin[i + 1][0] if i + 1 < len(lin) else la + 256
        out.append(len(struct.unpack_from(f"<{min(end - la, 1024 - a % 1024)}I", param, 4 * a - pb.PB_BASE)))
    return out


PINNED = None


def _pinned():
    global PINNED
    import pinned
    PINNED = pinned.load()
    return PINNED


def verdicts(stage, d):
    rows = K.table(KP, stage)
    preds = K.predictions(KP, stage)
    rds = readings(stage, d)
    controls, lines = control_states(stage, rds, preds, rows)
    g = SK.gate(controls) if controls else None
    if stage == "m6":
        res = m6_rows(rds, rows)
        res.update({k: v for k, v in plain_rows(stage, rds, preds, rows,
                                               skip={r["name"] for r in rows if "-cal-" not in r["name"]}).items()
                    if k == "H-STEPMODEL"})
    elif stage == "v":
        res = v_rows(rds, d)
    else:
        res = plain_rows(stage, rds, preds, rows)
    tallies = {}
    for mdl, items in sorted(res.items()):
        states = []
        for r, st, det in items:
            if g is not None and not g.ok:
                st = None
            states.append(st if r.get("set") != "explore" else None)
            lines.append(f"ROW {r['name']} [{mdl}, {r.get('set')}]: "
                         f"{'held' if st else 'FAILED' if st is False else 'cannot tell'}: {det}")
        tallies[mdl] = ([s for (r, _, _), s in zip(items, states) if r.get("set") in ("heldout", "control")],
                        [st for r, st, _ in items if r.get("set") == "explore"])
    return controls, lines, tallies


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
        st = argv[1]
        controls, lines, tallies = verdicts(st, argv[2])
        print("\n".join(lines))
        for mdl, (held, expl) in tallies.items():
            print(f"MODEL {mdl}: {SK.tally(held)}" + (f"; explore {SK.tally(expl)}" if expl else ""))
        if st == "a0":
            print("SUMMARY: a0: " + SK.headline("the premise held (R7's s-a0 controls repeat on 37EC97AB)",
                                                controls, [True] if controls else []))
        for mdl in MAIN.get(st, ()):
            held = tallies.get(mdl, ([], []))[0]
            print(f"SUMMARY: {st}: {mdl}: " + SK.headline(
                f"{mdl} holds", controls or {"a0 (the gate score.py gate opened)": True}, held))
        return 0
    print(__doc__)
    return 2


def read_files(stage, d):
    """Exactly the files score() reads in the kept directory."""
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.text(d, "readings.tsv")
    for n in cases:
        K.text(d, n + ".txt")
        if stage == "v":
            for s in DUMP:
                K.text(d, n + s)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
