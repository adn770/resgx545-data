# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""kitscore.py: what a kit session's scorer reads (tools/closing/kit, HACKING.md "Session kit").
Standard library only; the verdict rules stay in scorekit.py. A scorer imports both from the
session's kit/ (byte copies, pinned by commit in FROZEN.commits).

  table(kp, stage)        the rows of tables/STAGE.txt: dicts name, set, risk, knobs, tool, args,
                          reads (the control's keys)
  predictions(kp, stage)  {case: {quantity: {model: value}}} of predictions/STAGE.tsv
  rows(d, name)           {name: row} of a kept cases.tsv or void.tsv (rc an int)
  text(d, name)           a kept file, plain or gzipped, as text ("" when absent)
  readings(d)             {control: {key: value}} of readings.tsv, the runner's premise readings
  premise(kp, stage, d)   the STOP lines of the premise: every control row of the table must have
                          run and read every key it declares (scorekit.premise_stops)
  controls(kp, stage)     {name: (keys, row)} of the table's control rows, for
                          scorekit.refuse_unreadable
  param_hash(b)           a param buffer dump's stream-bounded sha256 (hex; None for None): the
                          dwords as "%08x\n" lines, a terminate word 0xc0000000 that follows
                          another written 00000000, so each stream ends at its first terminate
                          word and the words past it (stale, r19-k0) are not compared;
                          lib_kit.sh param_hash FILE is its twin (r19-k0b's pmask, E1077)
  snap_regs(d, name)      {offset: value} of the `reg` lines of the kept NAME.snap0.regs (the
                          kit's register snapshot before the job; {} when absent); snaps0(d) is
                          {row: that} of every row of cases.tsv that has one. A control's idle
                          register value is read from here (scorekit.reg_expect, "@snap0"),
                          never frozen from a mid-session reading (E1116)
  calibration(d, names, tol)
                          scorekit.calibration of the `ivl` readings (readings.tsv) of the named
                          rows (default: every row) of a kept calibration stage: the sample
                          interval of a register set in the job window, for scorekit.ivl_control
                          ("@cal:STAGE", E1131)
  miscinfo(d, name)       the kept NAME.miscinfo of a pre:miscinfo row (None when absent): text,
                          served (the kernel's "GETMISCINFO answered after N us" and "all
                          values match" lines, no MISMATCH line: the kick was served) and us
                          (N, or None)
  kc(d, begin, end)       the command count of a stage (K9, round 45): the kernel's `ccb_sent` at
                          each firmware load of the stage's kernel.log, begin (the first load
                          after `row begin` to the first after `owntask-arm`) and end (the first
                          after `owntask-disarm` to the last): {begin, end} each {n0, n1, delta,
                          draws, expected, state, why}; state "ok", "failed" or None (cannot
                          tell: a load or mark missing). kc_expected(draws) = 2 + 2 x fills + 6 x
                          tris; kc_state(kc, side) is DK; kc_text(name, kc) the KC lines;
                          hkc_words(draws, base) H-KC's word of each entry (printed, never scored)
  completed(row)          a kept row whose job ran to its end: class ok, with rc 0, rc 1 of an
                          `expectdiff` row (the runner took it as a reading only with `job: ok`
                          and a diff line) or the rc of an expected outcome its knobs declare
                          (OUTCOMES, `expect:NAME`)
  own_res(d, name)        the kept NAME.own_res.json of an owntask row (the results page the
                          kit's fwtask_run.py page dumped after the job, or a runner stop's
                          <tag>-own_res.json): its 1024 dwords, or None
  own_dword(d, name, i)   dword I of that page (None when absent): a frozen rule names a result
                          by its dword index, the prediction quantity `res:I` (res_index)
  own_slot(d, name, n)    the 4 dwords of result slot N (RESULTS + 4 N, tools/fwtask/layout.py)
  res_index(quantity)     I of a `res:I` quantity (decimal or 0x hex, below 1024), None for any
                          other quantity; ValueError for a `res:` that is not one
  own_json(d, name, sfx)  a kept owntask JSON file of the row (".txt": fwtask_run.py run's
                          output; ".gate.json": its gate after the job), or None

OUTCOMES: {NAME: (rc, line)} the expected outcomes a row may declare with the knob word
`expect:NAME`: a job that ends with that rc and prints that line is a completed job, not a
failure (kit/run_stage.sh classifies it ok the same way). rc3-overflow: a `probe` DPM cell's
normal end, "scene overflowed the parameter buffer" (R7-dpm's runner took it the same way).
rc0-overflow: a `tri --keep-overflow` run, which counts an overflowed render and ends rc 0: the
summary must say "N overflowed" (the line is a grep pattern); rc 0 without it is a failure.
"""
import gzip
import hashlib
import os
import re

import scorekit

OUTCOMES = {"rc3-overflow": (3, "scene overflowed the parameter buffer"),
            "rc0-overflow": (0, "renders ok, [0-9]* overflowed")}
COLUMNS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
           "fault_word", "free_kb")


def _read(path):
    if os.path.exists(path + ".gz"):
        with gzip.open(path + ".gz", "rb") as f:
            return f.read()
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


TERMINATE = 0xC0000000


def param_hash(b):
    """A param buffer dump's sha256 bounded by its streams: lib_kit.sh param_hash's twin."""
    if b is None:
        return None
    h, prev = hashlib.sha256(), False
    for i in range(0, len(b) - len(b) % 4, 4):
        w = int.from_bytes(b[i:i + 4], "little")
        t = w == TERMINATE
        h.update(b"00000000\n" if t and prev else b"%08x\n" % w)
        prev = t
    return h.hexdigest()


def text(d, name):
    b = _read(os.path.join(d, name))
    return "" if b is None else b.decode(errors="replace")


def table(kp, stage):
    out = []
    for ln in open(os.path.join(kp, "tables", stage + ".txt")).read().splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        name, sset, risk, knobs, tool, args = ln.split("|", 5)
        words = knobs.split()
        reads = ()
        for w in words:
            if w.startswith("reads:"):
                reads = tuple(w[len("reads:"):].split(","))
        out.append(dict(name=name, set=sset, risk=risk, knobs=words, tool=tool, args=args,
                        reads=reads))
    return out


def predictions(kp, stage):
    out = {}
    lines = open(os.path.join(kp, "predictions", stage + ".tsv")).read().splitlines()
    for ln in lines[1:]:
        if not ln.strip():
            continue
        f = ln.split("\t")
        out.setdefault(f[0], {}).setdefault(f[1], {})[f[3]] = f[2]
    return out


def rows(d, name="cases.tsv"):
    out = {}
    for ln in text(d, name).splitlines()[1:]:
        f = ln.split("\t")
        if len(f) < len(COLUMNS) or not f[0]:
            continue
        r = dict(zip(COLUMNS, f))
        r["rc"] = int(r["rc"])
        out[f[0]] = r
    return out


def readings(d):
    out = {}
    for ln in text(d, "readings.tsv").splitlines()[1:]:
        f = ln.split("\t")
        if f and f[0]:
            r = f[2] if len(f) > 2 else ""
            out[f[0]] = dict(w.split("=", 1) for w in r.split() if "=" in w)
    return out


def snap_regs(d, name):
    out = {}
    for ln in text(d, name + ".snap0.regs").splitlines():
        p = ln.split()
        if len(p) >= 3 and p[0] == "reg":
            try:
                out[int(p[1], 16)] = int(p[2], 16)
            except ValueError:
                pass
    return out


def snaps0(d):
    out = {}
    for n in rows(d):
        regs = snap_regs(d, n)
        if regs:
            out[n] = regs
    return out


def calibration(d, names=None, tol=0.25):
    rd = readings(d)
    names = list(rd) if names is None else names
    ivls = []
    for n in names:
        v = rd.get(n, {}).get("ivl")
        ivls.append(int(v) if v is not None and v.isdigit() else None)
    return scorekit.calibration(ivls, tol=tol)


def controls(kp, stage):
    return {r["name"]: (r["reads"], r) for r in table(kp, stage) if r["set"] == "control"}


def premise(kp, stage, d):
    want = {n: keys for n, (keys, _) in controls(kp, stage).items()}
    return scorekit.premise_stops(want, readings(d))


# the kernel's lines of a served miscinfo read (fork 8bc0877e8603, sgxfive_miscinfo's
# drm_printf): the answer, then each value checked; a mismatch prints MISMATCH and MISMATCHES
MISCINFO_ANSWERED = re.compile(r"^GETMISCINFO answered after ([0-9]+) us$", re.M)
MISCINFO_MATCH = re.compile(r"^all values match$", re.M)


def miscinfo(d, name):
    """The kept NAME.miscinfo of a pre:miscinfo row: {text, served, us}, or None."""
    b = _read(os.path.join(d, name + ".miscinfo"))
    if b is None:
        return None
    t = b.decode(errors="replace")
    m = MISCINFO_ANSWERED.search(t)
    served = bool(m and MISCINFO_MATCH.search(t) and "MISMATCH" not in t)
    return dict(text=t, served=served, us=int(m.group(1)) if m else None)


# the results page of our own firmware tasks (tools/fwtask/layout.py)
OWN_PAGE = 1024
OWN_RESULTS = 0x40
RES_QTY = re.compile(r"res:(0x[0-9a-f]+|[0-9]+)")


def res_index(q):
    """I of a prediction quantity `res:I` (a dword of the results page), None for any other."""
    if not isinstance(q, str) or not q.startswith("res:"):
        return None
    m = RES_QTY.fullmatch(q)
    if not m or int(m.group(1), 0) >= OWN_PAGE:
        raise ValueError(f"quantity {q!r} is not res:I with I a dword 0 to {OWN_PAGE - 1}")
    return int(m.group(1), 0)


def own_json(d, name, suffix):
    import json
    b = _read(os.path.join(d, name + suffix))
    if b is None:
        return None
    try:
        return json.loads(b)
    except ValueError:
        return None


def own_res(d, name):
    """The kept results page of an owntask row ({"page": [...]} of fwtask_run.py page, or a stop
    dump's plain list): 1024 dwords, or None."""
    p = own_json(d, name, ".own_res.json")
    p = p.get("page") if isinstance(p, dict) else p
    if not isinstance(p, list) or len(p) != OWN_PAGE or not all(isinstance(x, int) for x in p):
        return None
    return p


def own_dword(d, name, i):
    p = own_res(d, name)
    return None if p is None else p[i]


def own_slot(d, name, n):
    p = own_res(d, name)
    return None if p is None else p[OWN_RESULTS + 4 * n:OWN_RESULTS + 4 * n + 4]


def completed(row):
    """A kept row (rows()) whose job ran to its end: class ok, and rc 0, rc 1 of an
    `expectdiff` row or the rc of an expected outcome its knobs declare."""
    if row.get("class") != "ok":
        return False
    if row["rc"] == 0:
        return True
    words = row.get("knobs", "")
    words = words.split() if isinstance(words, str) else words
    if row["rc"] == 1 and "expectdiff" in words:
        return True
    return any(w.startswith("expect:") and OUTCOMES.get(w[len("expect:"):], (None,))[0] == row["rc"]
               for w in words)


# ---- K9: the command count (round 45, the n3j design section 2) ----------------------
# E768: an event's pa1 bits 31:24 count the CCB commands since the last firmware load; the kernel
# prints `ccb_sent N` at each load. From the begin load to the arm's load N rises by 2 (the
# debugfs reset's boot and the arm's power-off) + 2 per fill + 6 per triangle (E747's kicks); from
# the disarm's load to the exit's by 2 + the end draws' kicks.
CCB_LINE = re.compile(r"\[drm\] loaded \d+ live \d+ sw_events \d+ bif_faults \d+ "
                      r"ccb_sent ([0-9]+)")
KC_MARK = re.compile(r"resgx545 \S+ (row begin|owntask-arm|owntask-disarm|"
                     r"health (begin|end) try ([0-9]+) (\S+))")
KICKS = {"fill": 2, "tri": 6}


def kc_items(draws):
    items = [] if draws in ("none", "") else draws.split(",")
    for w in items:
        if w not in KICKS:
            raise ValueError(f"draw {w!r} of {draws!r} is not fill or tri")
    return items


def kc_expected(draws):
    """The commands a draw list sends: 2 + 2 per fill + 6 per triangle (none: 2)."""
    return 2 + sum(KICKS[w] for w in kc_items(draws))


def _events(d):
    """The kernel log's (kind, value) in order: `load` (ccb_sent), `row begin`, `owntask-arm`,
    `owntask-disarm`, `health` ((phase, try, list))."""
    out = []
    for ln in text(d, "kernel.log").splitlines():
        m = CCB_LINE.search(ln)
        if m:
            out.append(("load", int(m.group(1))))
            continue
        m = KC_MARK.search(ln)
        if m:
            out.append(("health", (m.group(2), int(m.group(3)), m.group(4))) if m.group(2)
                       else (m.group(1), None))
    return out


def _seg(declared, n0, n1, marks, what, retry_ok):
    seg = dict(n0=n0, n1=n1, delta=None, draws=declared or (marks[0][2] if marks else None),
               expected=None, state=None, why="")
    if seg["draws"] is not None:
        try:
            seg["expected"] = kc_expected(seg["draws"])
        except ValueError as e:
            seg["state"], seg["why"] = "failed", f"{what}: {e}"
            return seg
    if n0 is None or n1 is None:
        seg["why"] = f"{what}: a `loaded ... ccb_sent` line is missing"
        return seg
    seg["delta"] = n1 - n0
    if not marks:
        seg["why"] = f"{what}: no health mark names the draws"
        return seg
    if len(marks) != 1 or (not retry_ok and marks[0][1] != 1):
        seg["state"] = "failed"
        seg["why"] = (f"{what}: {len(marks)} health marks, the first at try {marks[0][1]} "
                      "(a retry adds a reset and draws)")
        return seg
    if declared and marks[0][2] != declared:
        seg["state"] = "failed"
        seg["why"] = f"{what}: the draws were {marks[0][2]}, declared {declared}"
        return seg
    seg["state"] = "ok" if seg["delta"] == seg["expected"] else "failed"
    if seg["state"] == "failed":
        seg["why"] = f"{what}: delta {seg['delta']}, expected {seg['expected']}"
    return seg


def kc(d, begin=None, end=None):
    """{begin, end}: the command count of a stage's kernel.log (K9); each a dict n0, n1, delta,
    draws (the declared list, else the mark's), expected, state (ok, failed, None), why. A
    begin health at try 2 or more (a retry) is failed; the end path's own `try 2` is not."""
    ev = _events(d)
    kinds = [k for k, _ in ev]

    def at(kind):
        return kinds.index(kind) if kind in kinds else None
    i, j, k = at("row begin"), at("owntask-arm"), at("owntask-disarm")
    nxt = lambda a: None if a is None else next(  # noqa: E731
        (v for kk, v in ev[a + 1:] if kk == "load"), None)
    bm = [v for kk, v in ev[i:j] if kk == "health" and v[0] == "begin"] \
        if i is not None and j is not None else []
    # the begin load is the one between `row begin` and the begin health mark (the arm's load
    # comes after the arm): a missing one must not read the arm's
    h = next((x for x in range(i + 1, len(ev)) if ev[x][0] == "health"), None) \
        if i is not None else None
    b0 = next((v for kk, v in ev[i + 1:h] if kk == "load"), None) if h is not None else None
    after = [v for kk, v in ev[k + 1:] if kk == "load"] if k is not None else []
    em = [v for kk, v in ev[k:] if kk == "health" and v[0] == "end"] if k is not None else []
    return dict(begin=_seg(begin, b0, nxt(j), bm, "begin", False),
                end=_seg(end, after[0] if after else None,
                         after[-1] if len(after) > 1 else None, em, "end", True))


def kc_state(got, side=None):
    """DK: ok when the stage's begin (and end) deltas are the expected ones, failed when one is
    not, None (cannot tell) when one could not be read and none failed."""
    ss = [got[side]["state"]] if side else [got["begin"]["state"], got["end"]["state"]]
    if "failed" in ss:
        return "failed"
    return None if None in ss else "ok"


def kc_text(name, got):
    out = []
    for side, b in (("begin", "arm"), ("end", "exit")):
        s = got[side]
        if s["delta"] is None:
            out.append(f"KC {name}: {side} cannot tell ({s['why']})")
            continue
        items = kc_items(s["draws"]) if s["draws"] else []
        out.append(f"KC {name}: {side} N0 {s['n0']}, {b} N1 {s['n1']}, delta {s['delta']}, "
                   f"expected 2 + 2 x {items.count('fill')} + 6 x {items.count('tri')} = "
                   f"{s['expected']} ({s['state'] or 'cannot tell'}"
                   + (f": {s['why']}" if s["why"] else "") + ")")
    return out


def hkc_words(draws, base):
    """H-KC's word of each entry of the list (printed, never scored): K = base + the commands
    before the entry + 1; a fill's 3:4 gives K << 24 | 0x10, a triangle's 3:22 K << 24 | 0x400000
    and its 3:4 K << 24 | 0x10. base is 1 at the begin draws, 2 at the end draws."""
    out, cmds = [], 0
    for i, w in enumerate(kc_items(draws), 1):
        k = base + cmds + 1
        if w == "fill":
            out.append(f"fill {i}: 3:4 K {k} 0x{k << 24 | 0x10:08x}")
        else:
            out.append(f"tri {i}: 3:22 K {k} 0x{k << 24 | 0x400000:08x}; "
                       f"3:4 K {k} 0x{k << 24 | 0x10:08x}")
        cmds += KICKS[w]
    return out
