#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: the scorer of the r43-n3h-* sessions (closing29/n3h/design.md §3, N3h: who writes
attribute 1, what the tick pass reads, which pass faults; STEP below says the session: N1 stages
w and v, N2 stages w2 and f), built on the r42-n3g-* scorer (rows M, LV). Every verdict rule
comes from kit/scorekit.py, the kept files are read through kit/kitscore.py.

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL, OUTCOME and PREDICTION lines, then SUMMARY and
                                       the RULE line (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another: any stop ends the session)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

One row a stage (NAME = STAGE1-a). Its readings, from the kept files:
  page     NAME.own_res.json (the page after the row), else the runner's last stop dump
           NAME.stopI-own_res.json; pre = dwords 128-159 (job 1, entry 0, before the emit), post sa
           = 160-191 and post pa = 192-207 (job 1, entry 1): job 1's words, which no later job
           writes (postsaK, postpaK)
  records  NAME.txt (fwtask_run.py run): job k's record; `slot` its slot (job 1: slot 1, M1 and
           its run id; command 6: slot 6, M6 and its run id), `cmd_after` the cmd word as it
           ended, `slots` 40-47 a command 6's after-read, `bif` K5's [BIF_INT_STAT, BIF_FAULT]
           pre, mid (a kicked job's, K6: right after the kick's reply) and post, `kick` its reply;
           every job-scoped quantity is read in its own job's record, never on the row-end page
           (the H3 slip, E1176)
  j1       DONE when job 1's record is done and the page has M1 and X0 (slot 1), S1 (dword 84) and
           M4 (dwords 80-81) with job 1's run id; else its start outcome (B11's table)
  j2, j3   done or notdone (job 2's, job 3's record), unread when the record is missing
  sa1kind  job 1's post sa1: M1 (0x005d1000), V1 (0x32005000), EVT4 or EVT22 (an event word:
           bits 31:24 in 1-15, bits 23:0 = 0x000010 or 0x400000), else OTHER
  fault1   W: yes when snap9's BIF_FAULT or the disarm's (owntask.reset.json health) is not 0, no
           when both are 0, unread without the disarm's record and snap9 0
  j2fault  V: the first BIF_FAULT not 0 among job 2's K5 pre, mid, post as `cidC page 0xPAGE`
           (C = bits 3:0), none when all are 0
  j2pre, j2post  F: job 2's K5 pre and post BIF_FAULT
  j2kick   F: the first BIF_FAULT not 0 among job 2's mid and post, as j2fault
  j2reply, j3reply  answered (a `GETMISCINFO answered` reply), error (the read failed), other
  after3   F: job 3's after-read against job 1's: REBASE (= post), NONE (= pre), HIGH, OTHER, AMBIG,
           PREPOST; unread unless job 3 is done with M6 and its run id
  gate1page  the gate's fill fault `cidC page 0xPAGE` between the marks owntask-gate-begin NAME
           and owntask-gate NAME (kernel.log), exact, hang or other
  @post1 @post13  CID 15 and the page of job 1's post sa1 / sa13; @V0 @V2 TA3DCtl dwords 0 and 2 in
           the row's snap0
Each frozen outcome (predictions/STAGE.tsv, model = the outcome) holds when every one of its
quantities matches, FAILED when one does not, cannot tell when one is unread. Controls (model
CTL; all can fail): PG, E0, T0, B, J1 and the job controls (V: J2; F: J2 the kick-only shape, J3).

RULE (frozen): `Q128-N3H-<STAGE> RULE: <the outcomes held>` when PG, E0, T0 and J1 passed (B
failing is read by the outcomes that name a fault; with none of them held it is `FAULT`); else
`CANNOT TELL (...)`. V's V-KEEP, V-EVT and V-V1 and F's F-FILL4 and F-KEEP read cannot tell unless
the planting stage of the same attempt (w for v, w2 for f; its kept directory beside KEPT_DIR, or
in ROOTS) read W-SA1 (post sa1 = M1). Then one PREDICTION line per frozen outcome: the prediction
(held, failed, held if reached, printed) against the reading; F-GATE reads "not reached" when no
gate ran. Printed, never scored: the arm line, each job's line (Δtick, kick reply), K5's words, the
survey, attributes 3-12 (post sa3-sa12), every fault page against job 1's post sa0, sa1 and sa13,
the kernel's "events seen" lines and the notes of the design's cannot-tell rules."""
import json
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STEP = "N2"
# gen/make.py STAGES's: stage: (model, the row's jobs) (tests/test_gen.py: equal)
STAGES = {
    "N1": {"w": ("W", ("j1",)), "v": ("V", ("j1", "tick"))},
    "N2": {"w2": ("W", ("j1",)), "f": ("F", ("j1", "kickonly", "kick"))},
}[STEP]
PLANT = {"v": "w", "f": "w2"}
NEEDS_PLANT = ("V-KEEP", "V-EVT", "V-V1", "F-FILL4", "F-KEEP")
ROW_FILES = (".txt", ".own_res.json", ".snap0.regs", ".snap9.regs")
GATE_FILES = (".gate.json", ".gate-fill.txt", ".gate-tri.txt", ".devcd-pre.txt", ".devcd.txt")
STAGE_FILES = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {st: ROW_FILES + (GATE_FILES if m == "F" else ()) + STAGE_FILES
            + (() if m == "F" else ("owntask.reset.json",)) for st, (m, _) in STAGES.items()}
GATES = {}
MAGIC, FILL = 0x4E574F53, 0xDEADC0DE
M1, X0, M4, S1, M6, T3 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306, 0x005A3305
PRE_AT, POST_SA_AT, POST_PA_AT, AFTER_AT = 128, 160, 192, 224
AFTER_SLOTS = list(range(40, 48))
TIM, BIF = 0x0ACC, 0x0C08
TIM_RUN, TIM_MAX = 1 << 24, 400000
MK13, MK1, V1 = 0x005D3000, 0x005D1000, 0x32005000
CTLS = {"PG": ("res:0x0",), "E0": ("j1rec:slot0", "j1rec:slot1", "j1rec:cmd"),
        "T0": ("snap0:0x0acc",), "B": ("snap9:0x0c08",), "J1": ("j1",)}
JOB_CTLS = {"W": {}, "V": {"J2": ("j2rec:done", "j2rec:slot0", "j2rec:slot1")},
            "F": {"J2": ("j2rec:done", "j2rec:cmd", "j2rec:kicked"),
                  "J3": ("j3rec:done", "j3rec:slot0", "j3rec:slot1")}}
NEED = ("PG", "E0", "T0", "J1")
NAMES_FAULT = ("W-FAULT", "V-EARLY1", "V-EARLY13", "V-EARLY0", "K-KICK", "F-GATE")
FAULT_LINE = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)")
HANG_LINE = re.compile(r"\bhung\b|timed out")
EVENTS_LINE = re.compile(r"SGX stopped, [0-9]+ events seen")


def state_word(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def hexs(v):
    return "?" if not isinstance(v, int) else f"0x{v:08x}"


def producible(row):
    return set()


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    if STAGES[stage][0] != "F":     # F's planned end (the gate's failure) leaves no disarm record
        K.text(d, "owntask.reset.json")
    for n, r in cases.items():
        for s in ROW_FILES[:1] + ROW_FILES[2:]:
            K.text(d, n + s)
        K.own_res(d, n)
        if r["class"] == "ok" and STAGES[stage][0] == "F":
            for s in GATE_FILES:
                K.text(d, n + s)


def regs_of(text):
    """{offset: value} of `reg 0xOOOO 0xV` lines and {(kind, i): v} of hostctl/ta3dctl lines."""
    out = {}
    for m in re.finditer(r"^(reg|hostctl|ta3dctl) (0x[0-9a-f]+) (0x[0-9a-f]{8})$", text, re.M):
        k = int(m.group(2), 16)
        out[k if m.group(1) == "reg" else (m.group(1), k // 4)] = int(m.group(3), 16)
    return out


def stops(d, n):
    names = set()
    for p in os.listdir(d):
        m = re.match(re.escape(n) + r"\.stop([0-9]+)-", p)
        if m:
            names.add(int(m.group(1)))
    return sorted(names)


def page_of(d, n):
    """(the page, where): own_res.json, else the last stop dump; (None, None)."""
    p = K.own_res(d, n)
    if p is not None:
        return p, "own_res.json"
    for i in reversed(stops(d, n)):
        p = K.own_json(d, n, f".stop{i}-own_res.json")
        p = p.get("page") if isinstance(p, dict) else p
        if isinstance(p, list) and len(p) == K.OWN_PAGE and all(isinstance(x, int) for x in p):
            return p, f"stop{i}-own_res.json"
    return None, None


def run_of(d, n):
    try:
        r = json.loads(K.text(d, n + ".txt"))
        return r if isinstance(r, dict) else {}
    except (ValueError, TypeError):
        return {}


def after_of(rec):
    sl = rec.get("slots") if isinstance(rec, dict) else None
    if not isinstance(sl, dict) or not all(str(s) in sl for s in AFTER_SLOTS):
        return None
    out = [x for s in AFTER_SLOTS for x in sl[str(s)]]
    return out if len(out) == 32 and all(isinstance(x, int) for x in out) else None


def m6_ok(rec):
    s = rec.get("slot") if isinstance(rec, dict) else None
    return isinstance(s, list) and len(s) >= 2 and s[0] == M6 and \
        s[1] == (rec.get("job") or {}).get("runid")


def running(v):
    return v is not None and bool(v & TIM_RUN) and (v & 0xFFFFFF) <= TIM_MAX


def start_of(page, t, rec1, runid1):
    if page is None:
        return None
    s1, m4 = page[0x54] == S1, page[0x50] == M4 and page[0x51] == runid1
    if s1 and m4 and page[0x44] == M1 and page[0x46] == X0 and rec1.get("done") is True:
        return "DONE"
    if s1:
        return "E1"
    stopped = t and not any(running(x) for x in t) and len(set(t)) == 1
    if not stopped:
        return "NEVER" if t and all(running(x) for x in t) else None
    return {0: "T1", 0x200: "T2", T3: "T3"}.get(t[0])


def label_after(pre, post, after):
    if after is None or pre is None or post is None:
        return None
    if pre == post:
        return "PREPOST"
    hit = [k for k, ok in (("REBASE", after == post), ("NONE", after == pre),
                           ("HIGH", after[:12] == pre[:12] and after[12:] == post[12:])) if ok]
    return hit[0] if len(hit) == 1 else "AMBIG" if hit else "OTHER"


def sa1_kind(w):
    if w is None:
        return None
    if w == MK1:
        return "M1"
    if w == V1:
        return "V1"
    if 1 <= w >> 24 <= 15 and w & 0xFFFFFF in (0x10, 0x400000):
        return "EVT4" if w & 0xFFFFFF == 0x10 else "EVT22"
    return "OTHER"


def cidpage(w):
    return f"cid{w & 0xF} page 0x{w & ~0xFFF & 0xFFFFFFFF:08x}"


def bif_fault(rec, which):
    """BIF_FAULT of a record's K5 read `which` (pre, mid, post), or None."""
    b = rec.get("bif") if isinstance(rec, dict) else None
    v = b.get(which) if isinstance(b, dict) else None
    return v[1] if isinstance(v, list) and len(v) == 2 and isinstance(v[1], int) else None


def first_fault(rec, which):
    """`cidC page` of the first BIF_FAULT not 0 among the reads `which`, none, or None."""
    ws = [bif_fault(rec, w) for w in which]
    if all(w is None for w in ws):
        return None
    hit = next((w for w in ws if w), None)
    return cidpage(hit) if hit else "none"


def reply_of(rec):
    k = rec.get("kick") if isinstance(rec, dict) else None
    if not isinstance(k, dict):
        return None
    r = k.get("reply")
    if not isinstance(r, dict):
        return "other"
    if "error" in r:
        return "error"
    return "answered" if "GETMISCINFO answered" in str(r.get("text", "")) else "other"


def gate_window(d, n):
    lines, out, on = K.text(d, "kernel.log").splitlines(), [], False
    for ln in lines:
        if re.search(r"resgx545 \S+ owntask-gate-begin " + re.escape(n) + r" ", ln):
            on, out = True, []
            continue
        if on and re.search(r"resgx545 \S+ owntask-gate " + re.escape(n) + r" ", ln):
            return out
        if on:
            out.append(ln)
    return out if on else None


def tool_exact(text, tool):
    return f"diff: 0 of {2048 if tool == 'fill' else 4096}" in text and "FAIL" not in text


def gate_of(d, n):
    """(gate1, gate1page, gate2, the fault (stat, word) or None, the window or None)."""
    win = gate_window(d, n)
    t1, t2 = K.text(d, f"{n}.gate-fill.txt"), K.text(d, f"{n}.gate-tri.txt")
    if win is None and not t1:
        return None, None, None, None, None
    fault = next(((int(m.group(1), 16), int(m.group(2), 16)) for m in
                  (FAULT_LINE.search(ln) for ln in win or []) if m), None)
    if win is None:
        g1 = gp = "exact" if tool_exact(t1, "fill") else None
    elif fault and not tool_exact(t1, "fill"):
        g1 = f"fault 0x{fault[0]:08x} 0x{fault[1]:08x}"
        gp = cidpage(fault[1])
    elif tool_exact(t1, "fill") and not fault:
        g1 = gp = "exact"
    elif any(HANG_LINE.search(ln) for ln in (win or []) + t1.splitlines()):
        g1 = gp = "hang"
    else:
        g1 = gp = "other"
    g2 = "exact" if tool_exact(t2, "tri") else "other" if t2 else None
    return g1, gp, g2, fault, win


def reset_fault(d):
    """The disarm's BIF_FAULT (owntask.reset.json health), or None without the record."""
    try:
        r = json.loads(K.text(d, "owntask.reset.json"))
    except ValueError:
        return None
    h = r.get("health") if isinstance(r, dict) else None
    v = h.get("bif_fault") if isinstance(h, dict) else None
    return v if isinstance(v, int) else None


def rec_ctl(rec, k):
    """{done, slot0, slot1, cmd, kicked} of a later job's record (unread values None)."""
    if not rec:
        return {"done": None, "slot0": None, "slot1": None, "cmd": None, "kicked": None}
    s = rec.get("slot")
    s = s if isinstance(s, list) and len(s) == 4 and all(isinstance(x, int) for x in s) \
        else [None] * 4
    c = rec.get("cmd_after")
    return {"done": "done" if rec.get("done") is True else "notdone",
            "slot0": s[0], "slot1": s[1], "cmd": c if isinstance(c, int) else None,
            "kicked": "yes" if isinstance(rec.get("kick"), dict) else "no"}


def readings_of(d, n, m):
    page, where = page_of(d, n)
    run = run_of(d, n)
    recs = [r for r in run.get("records", []) if isinstance(r, dict)]
    st = stops(d, n)
    snaps = {k: regs_of(K.text(d, f"{n}.{k}")) for k in ("snap0.regs", "snap9.regs")}
    stopregs = regs_of(K.text(d, f"{n}.stop{st[-1]}-regs.txt")) if st else {}
    t = [x for x in (snaps["snap9.regs"].get(TIM), stopregs.get(TIM)) if x is not None]
    rec = (recs + [{}, {}, {}])[:3]
    runid1 = (rec[0].get("job") or {}).get("runid")
    pre = page[PRE_AT:PRE_AT + 32] if page else None
    post = page[POST_SA_AT:POST_SA_AT + 32] if page else None
    pa = page[POST_PA_AT:POST_PA_AT + 16] if page else None
    r = dict(page=page, where=where, run=run, recs=recs, snaps=snaps, T=t, pre=pre, post=post,
             pa=pa, runid1=runid1)
    s1 = rec[0].get("slot")
    s1 = s1 if isinstance(s1, list) and len(s1) == 4 and all(isinstance(x, int) for x in s1) \
        else [None] * 4
    c1 = rec[0].get("cmd_after")
    r["j1rec"] = {"slot0": s1[0], "slot1": s1[1], "cmd": c1 if isinstance(c1, int) else None}
    r["j2rec"], r["j3rec"] = rec_ctl(rec[1], 2), rec_ctl(rec[2], 3)
    r["runid2"] = (rec[1].get("job") or {}).get("runid") if rec[1] else None
    r["runid3"] = (rec[2].get("job") or {}).get("runid") if rec[2] else None
    v = snaps["snap0.regs"]
    r["V"] = {"@V0": v.get(("ta3dctl", 0)), "@V2": v.get(("ta3dctl", 2))}
    r["start"] = r["j1"] = start_of(page, t, rec[0], runid1)
    r["j2"], r["j3"] = r["j2rec"]["done"], r["j3rec"]["done"]
    r["sa1kind"] = sa1_kind(post[1]) if post else None
    b9 = snaps["snap9.regs"].get(BIF)
    rf = reset_fault(d)
    r["fault1"] = "yes" if b9 or rf else "no" if b9 == 0 and rf == 0 else None
    r["resetfault"] = rf
    r["j2fault"] = first_fault(rec[1], ("pre", "mid", "post")) if rec[1] else None
    r["j2kick"] = first_fault(rec[1], ("mid", "post")) if rec[1] else None
    r["j2pre"], r["j2post"] = bif_fault(rec[1], "pre"), bif_fault(rec[1], "post")
    r["j2reply"], r["j3reply"] = reply_of(rec[1]), reply_of(rec[2])
    a3 = after_of(rec[2])
    r["after3w"] = a3
    r["after3"] = label_after(pre, post, a3) if r["j3"] == "done" and m6_ok(rec[2]) else None
    r["after2w"] = after_of(rec[1])
    r["bif"] = next((w for w in (stopregs.get(BIF), b9) if w), b9)
    g1, gp, g2, fault, win = gate_of(d, n)
    r.update(gate1=g1, gate1page=gp, gate2=g2, fault=fault, window=win)
    return r


def value_ok(spec, q, r):
    """A frozen value against the reading of quantity q: True, False or None."""
    page = r["page"]
    if q in ("j1", "j2", "j3", "after3", "fault1", "sa1kind", "j2reply", "j3reply", "gate1",
             "gate2", "j2fault", "j2kick", "gate1page"):
        got = r.get(q)
        if got is None or (q == "after3" and got in ("PREPOST", "AMBIG")):
            return None
        if spec.startswith("@in:"):
            return got in spec[4:].split(",")
        if spec.startswith("@notin:"):
            return got not in spec[7:].split(",")
        if spec in ("@post1", "@post13"):
            if r["post"] is None:
                return None
            return got == cidpage(r["post"][1 if spec == "@post1" else 13] | 0xF)
        return got == spec
    m = re.fullmatch(r"(postsa|postpa)([0-9]+)", q)
    if m:
        k = int(m.group(2))
        src = {"postsa": r["post"], "postpa": r["pa"]}[m.group(1)]
        got = None if src is None or k >= len(src) else src[k]
    elif q in ("j2pre", "j2post"):
        got = r[q]
    elif re.fullmatch(r"j[23]rec:(done|kicked)", q):
        got = r[q[:5]][q[6:]]
        return None if got is None else got == spec
    elif re.fullmatch(r"j[123]rec:\w+", q):
        got = r[q[:5]].get(q[6:])
    elif q.startswith(("snap0:", "snap9:")):
        got = r["snaps"][q[:5] + ".regs"].get(int(q[6:], 16))
    else:
        i = K.res_index(q)
        got = None if page is None or i is None else page[i]
    if got is None:
        return None
    if spec == "running":
        return running(got)
    if spec in ("@runid1", "@runid2", "@runid3"):
        return got == r["runid" + spec[-1]]
    if spec in ("@V0", "@V2"):
        return None if r["V"][spec] is None else got == r["V"][spec]
    return got == int(spec, 16)


def all_of(states):
    states = list(states)
    if any(s is False for s in states):
        return False
    return None if any(s is None for s in states) else True


def plant_of(stage, d, roots):
    """(W-SA1 of the planting stage of the same attempt: True, False or None, where)."""
    w = PLANT.get(stage)
    if w is None:
        return None, None
    cands = [os.path.join(os.path.dirname(os.path.abspath(d)), w)] + \
        [os.path.join(x, w) for x in roots]
    for c in cands:
        if os.path.isdir(c):
            page, _ = page_of(c, f"{w}1-a")
            return (None if page is None else page[POST_SA_AT + 1] == MK1), c
    return None, None


def diffs(a, b):
    if a is None or b is None:
        return "?"
    return ", ".join(f"sa{k} {hexs(a[k])}->{hexs(b[k])}" for k in range(32) if a[k] != b[k]) \
        or "none"


def survey_lines(n, r):
    pre, post = r["pre"], r["post"]
    out = [f"SURVEY {n} (printed): pre/post differ at {diffs(pre, post)}"]
    for k, a in ((2, r["after2w"]), (3, r["after3w"])):
        if a is not None:
            out.append(f"SURVEY {n} job {k} after (printed): after vs pre: {diffs(pre, a)}; "
                       f"after vs post: {diffs(post, a)}")
    for lab, v in (("pre", pre), ("post sa", post), ("post pa", r["pa"])):
        out.append(f"SURVEY {n} {lab}: " + (" ".join(map(hexs, v)) if v else "?"))
    if post:
        out.append(f"ATTR {n} (printed): attributes 3-12 as post sa3-sa12: "
                   + " ".join(f"sa{k} {hexs(post[k])}" for k in range(3, 13)))
    return out


def bif_words(v):
    if isinstance(v, list) and len(v) == 2:
        return f"BIF_INT_STAT {hexs(v[0])} BIF_FAULT {hexs(v[1])}"
    return json.dumps(v)


def job_lines(n, r):
    out = []
    for k, rec in enumerate(r["recs"], 1):
        kick = rec.get("kick") if isinstance(rec.get("kick"), dict) else None
        out.append(f"JOB {n} {k} (printed): n {(rec.get('job') or {}).get('n')} run id "
                   f"{(rec.get('job') or {}).get('runid')} done {rec.get('done')} slot "
                   f"{' '.join(map(hexs, rec.get('slot') or []))} cmd_after "
                   f"{rec.get('cmd_after')} ticks {rec.get('ticks')}"
                   + (f" kick {json.dumps(kick.get('reply'), sort_keys=True)[:200]}" if kick
                      else ""))
        bif = rec.get("bif") if isinstance(rec.get("bif"), dict) else None
        out.append(f"BIF {n} job {k} (printed, K5): " + (
            "; ".join(f"{w} {bif_words(bif.get(w))}" for w in ("pre", "mid", "post")
                      if w in bif) if bif else "no bif words in the record"))
    if r["run"].get("stop"):
        out.append(f"JOB {n} (printed): the runner stopped: {r['run']['stop']}; alive "
                   f"{(r['run'].get('alive_at_stop') or {}).get('advancing')}")
    return out


def fault_lines(n, r):
    """Every fault page we read against job 1's post sa0, sa1 and sa13 (printed)."""
    post = r["post"]
    seen = []
    for k, rec in enumerate(r["recs"], 1):
        for w in ("pre", "mid", "post"):
            f = bif_fault(rec, w)
            if f:
                seen.append((f"job {k} {w}", f))
    if r["bif"]:
        seen.append(("snap9/stop", r["bif"]))
    if r["fault"]:
        seen.append(("gate", r["fault"][1]))
    if r["resetfault"]:
        seen.append(("disarm", r["resetfault"]))
    out = []
    for where, f in seen:
        pg = f & ~0xFFF & 0xFFFFFFFF
        hit = [f"sa{k}" for k in (0, 1, 13) if post and post[k] & ~0xFFF & 0xFFFFFFFF == pg]
        out.append(f"FAULT {n} (printed): {where} BIF_FAULT {hexs(f)} ({cidpage(f)}): "
                   + ("job 1's post " + ", ".join(hit) if hit else "none of job 1's post sa0, "
                      "sa1, sa13"))
    return out


def events_lines(d, n):
    return [f"EVENTS {n} (printed): " + ln.strip()[:160]
            for ln in K.text(d, "kernel.log").splitlines() if EVENTS_LINE.search(ln)]


def arm_line(d):
    for ln in K.text(d, "kernel.log").splitlines():
        m = re.search(r"own task armed: .*?(emit image \S+).*?(pds=\S+)(?: (pdsat=\S+))?"
                      r"(?: (pds2=\S+))?(?: (form=\S+))?", ln)
        if m:
            return "ARM (printed, not scored): " + " ".join(x for x in m.groups() if x)
    return "ARM (printed, not scored): no arm line in kernel.log"


def pred_word(text):
    m = re.search(r"\[predicted: ([^\]]+)\]", text)
    return m.group(1) if m else None


def frozen(stage):
    out = {}
    for ln in open(os.path.join(KP, "predictions", f"{stage}.tsv")).read().splitlines()[1:]:
        f = ln.split("\t")
        if len(f) == 6 and f[3] != "CTL":
            out[f[3]] = pred_word(f[5])
    return out


def verdict(pred, state, held, x, r, plant):
    if x == "F-GATE" and r["gate1"] is None:
        return "not reached" + (" (K-STALL)" if "K-STALL" in held else "")
    if x in NEEDS_PLANT and plant is not True:
        return f"cannot tell (W-SA1 {state_word(plant)} in the planting stage)"
    if state is None:
        return "cannot tell"
    if pred == "printed":
        return "printed"
    if pred in ("held", "held if reached"):
        return "held" if state else "FAILED"
    if pred == "failed":
        return "held" if not state else "FAILED"
    return "?"


def notes(stage, m, r, held):
    out = []
    if m == "W" and "W-FAULT" in held:
        out.append(f"NOTE {stage}: W-FAULT: a pass ran that we did not expect: stop the session "
                   "for the user")
    if m == "W" and "W-SA1" not in held:
        out.append(f"NOTE {stage}: W-SA1 not held: the next stage's attribute-1 outcomes read "
                   "cannot tell (nothing was planted)")
    if m == "V" and "V-EARLY1" in held and r["post"] and r["post"][1] == 0x04400000:
        out.append(f"NOTE {stage}: V-EARLY1 with post sa1 = 0x04400000: LV again, Q2 not "
                   "advanced")
    if m == "V" and "V-SERVE" in held and not r["bif"] and r["j2fault"] in (None, "none"):
        out.append(f"NOTE {stage}: no fault and V-SERVE: the tick-pass reading of design §0.2 "
                   "fails")
    if m == "F" and r["j2kick"] is None and r["j2post"] is None:
        out.append(f"NOTE {stage}: K-KICK and K-KICKOK unread (job 2's record missing): Q3 "
                   "cannot tell")
    return out


def score_stage(stage, d, roots=()):
    m, jobs = STAGES[stage]
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    lines, ctl_all, rl = [], {}, []
    ctls = dict(CTLS, **JOB_CTLS[m])
    plant, where_plant = plant_of(stage, d, roots)
    for t in K.table(KP, stage):
        n = t["name"]
        if n not in cases and K.own_res(d, n) is None:
            continue
        q = preds.get(n, {})
        r = readings_of(d, n, m)
        if r["page"] is None:
            lines.append(f"ROW {n}: no results page kept: cannot tell")
            ctl_all.update({f"{n}:{k}": None for k in ctls})
            continue
        models = sorted({x for mv in q.values() for x in mv if x != "CTL"})
        hyp = {x: all_of(value_ok(mv[x], k, r) for k, mv in q.items() if x in mv)
               for x in models}
        ctl = {c: all_of(value_ok(q[k]["CTL"], k, r) for k in ks) for c, ks in ctls.items()}
        ctl_all.update({f"{n}:{k}": s for k, s in ctl.items()})
        p = r["page"]
        lines.append(f"ROW {n}: page {r['where']}; job 1 run id {r['runid1']}; start {r['start']}"
                     f"; T {' '.join(map(hexs, r['T'])) or '?'}; cmd {p[1]}; state {p[2]}; "
                     f"j2 {r['j2']}; j3 {r['j3']}; sa1kind {r['sa1kind']}; fault1 {r['fault1']}; "
                     f"j2fault {r['j2fault']}; j2kick {r['j2kick']}; after3 {r['after3']}; "
                     f"BIF_FAULT {hexs(r['bif'])}")
        if stage in PLANT:
            lines.append(f"PLANT {n}: W-SA1 of stage {PLANT[stage]} {state_word(plant)} "
                         f"({where_plant or 'no kept directory'})")
        lines += [f"CONTROL {n}:{k}: {state_word(s)}" for k, s in ctl.items()]
        lines += [f"OUTCOME {n} {x}: {'held' if s else 'FAILED' if s is False else 'cannot tell'}"
                  for x, s in hyp.items()]
        held = [x for x, s in hyp.items() if s is True]
        need = [k for k in NEED if ctl[k] is not True]
        rl.append(arm_line(d))
        tag = f"Q128-N3H-{stage.upper()}"
        if need:
            rl.append(f"{tag} RULE: CANNOT TELL ("
                      + "; ".join(f"control {k} {state_word(ctl[k])}" for k in need) + ")"
                      + (f"; FAULT: BIF_FAULT {hexs(r['bif'])} after the row (its own reading, "
                         "printed)" if r["bif"] else ""))
        else:
            fz = frozen(stage)
            counted = [x for x in held if fz.get(x) != "printed"
                       and not (x in NEEDS_PLANT and plant is not True)]
            fault = ctl["B"] is False and not set(NAMES_FAULT) & set(held)
            rl.append(f"{tag} RULE: " + (", ".join(counted) or "no frozen outcome holds")
                      + ("; FAULT: BIF_FAULT is not 0 after the row and no outcome names it"
                         if fault else ""))
        fz = frozen(stage)
        for x in sorted(fz):
            rl.append(f"PREDICTION {x}: predicted {fz[x]}, read "
                      f"{'held' if hyp.get(x) else 'FAILED' if hyp.get(x) is False else 'cannot tell'}"
                      f": {verdict(fz[x], None if need else hyp.get(x), held, x, r, plant)}")
        for k in JOB_CTLS[m]:
            if ctl[k] is not True:
                rl.append(f"{k} {n} (printed): control {k} {state_word(ctl[k])}")
        rl += notes(stage, m, r, held)
        rl += job_lines(n, r) + fault_lines(n, r) + survey_lines(n, r) + events_lines(d, n)
        if m == "F":
            rl.append(f"GATE {n} (printed): first {r['gate1']} ({r['gate1page']}); second "
                      f"{r['gate2']}")
    if not rl:
        rl = [f"Q128-N3H-{stage.upper()} RULE: CANNOT TELL (no row kept)"]
    lines.append(f"SUMMARY: {stage}: controls: " + ("every control passed" if SK.gate(ctl_all).ok
                                                     else "; ".join(SK.gate(ctl_all).problems)))
    return lines, ctl_all, rl


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops_ = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops_) if stops_ else f"premise {argv[2]}: every control read")
        return 1 if stops_ else 0
    if len(argv) >= 3 and argv[1] in STAGES:
        lines, _, rl = score_stage(argv[1], argv[2], argv[3:])
        print("\n".join(lines + rl))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
