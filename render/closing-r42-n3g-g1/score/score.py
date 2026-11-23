#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: the scorer of the r42-n3g-* sessions (closing29/n3g/design.md §3, N3g: where sa13's
page comes from, bit 10 with bits 1:0 = 2, and `land` with V0/V2; STEP below says the session: G1
stages c and m, G2 stages s and q, G3 stage lv), built on the r41-n3f-* scorer (rows C, X, Y, LC).
Every verdict rule comes from kit/scorekit.py, the kept files are read through kit/kitscore.py.

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL, OUTCOME and PREDICTION lines, then SUMMARY and
                                       the RULE line (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another: any stop ends the session)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

One row a stage (NAME = STAGE1-a). Its readings, from the kept files:
  page     NAME.own_res.json (the page after the row), else the runner's last stop dump
           NAME.stopI-own_res.json; pre = dwords 128-159 (job 1, entry 0, before the emit), post sa
           = 160-191 and post pa = 192-207 (job 1, entry 1): job 1's words, which no later job
           writes (postsaK, postpaK)
  records  NAME.txt (fwtask_run.py run): job k's record; its `slots` 40-47 are its after-read
           (dwords 224-255, sa0-sa31 of the EDM's own bank at command 6), `slot` its slot (job 1:
           slot 1, M1 and its run id; command 6: slot 6, M6 and its run id), `cmd_after` the cmd
           word as the job ended, `bif` K5's [BIF_INT_STAT, BIF_FAULT] before and after it
           (printed only); every job-scoped quantity is read in its own job's record, never on the
           row-end page (the H3 slip, E1176)
  j1       DONE when job 1's record is done and the page has M1 and X0 (slot 1), S1 (dword 84) and
           M4 (dwords 80-81) with job 1's run id (slot 1 dword 1); else its start outcome (B11's
           table: NEVER, T1, T2, T3, E1, by T = 0x0acc in snap9 and the stop dump, and S1, M4)
  j2, j3   done or notdone (job 2's, job 3's record), unread when the record is missing
  after2   C and S: SAME (after = pre) or DIFF; else REBASE (after = post), NONE (after = pre),
           HIGH (sa0-11 = pre, sa12-31 = post), OTHER, AMBIG (two of the three at once), PREPOST
           (pre = post: rebase and none read alike); unread unless job 2 is done with M6 and its
           run id; after2saK its word K
  heal     job 3's after sa13 = pre sa13: yes or no (unread unless job 3 is done with M6)
  early    LV: yes when job 1 is DONE and a later job was not done or BIF_FAULT names list 15
           after the row, and early0 is not yes; no when every job is done and BIF_FAULT is 0
  early0   LV: yes when job 1 is DONE, job 2 was not done and BIF_FAULT after the row is
           0x0000000f (page 0, list 15: LC2's stop, E1178); no otherwise (once job 1 is DONE)
  gate1    the gate's first tool (the fill): `fault 0xSTAT 0xFAULT`, the first `BIF fault STAT at
           FAULT` kernel line between the marks owntask-gate-begin NAME and owntask-gate NAME
           (kernel.log) when the tool did not draw exactly; exact (`diff: 0 of` 2048 or 4096 in
           NAME.gate-<tool>.txt, no fault line); hang (a `hung` or `timed out` line, no fault);
           other
  gate1page  `cidC page 0xPAGE` of that fault line (C = FAULT bits 3:0, PAGE = bits 31:12), or
           exact, hang, other as gate1; the frozen value @post13 (C 15 and the page of job 1's
           post sa13) is read against it
  gate2    the second tool: exact or other
  @V0 @V2  TA3DCtl dwords 0 and 2 in the row's snap0 (`ta3dctl 0x00`, `0x08`): the kernel's V0
           and V2 at the arm; unread without them
Each frozen outcome (predictions/STAGE.tsv, model = the outcome) holds when every one of its
quantities matches, FAILED when one does not, cannot tell when one is unread. Controls (model
CTL; all can fail): PG page dword 0 = 0x4e574f53; E0 job 1's record: slot 1 = M1 and job 1's run
id, cmd_after 0; T0 snap0's 0x0acc running; B BIF_FAULT 0 in snap9; J1 job 1 DONE; J2 job 2's
record: done, slot 6 = M6 and job 2's run id.

RULE (frozen): `Q128-N3G-<M> RULE: <the outcomes held>` when PG, E0, T0 and J1 passed (B failing
is read by the outcomes that name it: LV-EARLY0, LV-EARLY; with none of them held it is `FAULT`, as
in X and LC2; J2 failing leaves the after-read outcomes unread); `CANNOT TELL (...)` when one of
them did not. M: when M13 is in no word of job 1's post pa0-15 and post sa0-31 (M-MISS), the RULE
adds that the row cannot tell row 3's question (sa13's source). Then one PREDICTION line per
frozen outcome: the prediction (held, failed, held if reached, printed) against the reading; in
LV, with LV-EARLY0 or LV-EARLY held, LV-REBASE, LV-HEAL and LV-FILL read "not reached".
Printed, never scored: the arm line, job 1's start outcome and T, each job's Δtick, slept, kick
reply and K5's BIF words before and after it, the survey (pre, post, each after-read and where
they differ), C's R-BOOT (job 1's post pa against the odd words of nine kept rows, design §0.1),
the gate's two tools, the devcoredumps and the fault page against job 1's post words."""
import json
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STEP = "G1"
# gen/make.py STAGES's: stage: (model, gate order, the row's jobs) (tests/test_gen.py: equal)
STAGES = {
    "G1": {"c": ("C", "fill,tri", ("j1", "kick")), "m": ("M", "fill,tri", ("j1", "kick"))},
    "G2": {"s": ("S", "fill,tri", ("j1", "kick")), "q": ("Q", "fill,tri", ("j1", "kick"))},
    "G3": {"lv": ("LV", "fill,tri", ("j1", "tick", "sleep"))},
}[STEP]
ROW_FILES = (".txt", ".own_res.json", ".gate.json", ".gate-fill.txt", ".gate-tri.txt",
             ".devcd-pre.txt", ".devcd.txt", ".snap0.regs", ".snap9.regs")
REQUIRED = {st: ROW_FILES + ("cases.tsv", "void.tsv", "readings.tsv") for st in STAGES}
GATES = {}
MAGIC, FILL = 0x4E574F53, 0xDEADC0DE
M1, X0, M4, S1, M6, T3 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306, 0x005A3305
PRE_AT, POST_SA_AT, POST_PA_AT, AFTER_AT = 128, 160, 192, 224
AFTER_SLOTS = list(range(40, 48))
TIM, BIF, SERV = 0x0ACC, 0x0C08, 0x0B14
TIM_RUN, TIM_MAX = 1 << 24, 400000
MK13, MK1 = 0x005D3000, 0x005D1000
# the odd post pa of nine kept rows (design §0.1; gen/make.py ODD_PA): C's R-BOOT, printed
ODD_PA = {1: 0x00043000, 3: 0x01555620, 5: 0x00000000, 7: 0x03C3CDAC, 9: 0xDC531A54,
          11: 0x5D50716F, 13: 0x82E151B5, 15: 0x11B5D77A}
# every control read where its job left it (design §3: job-scoped controls from that job's record)
CTLS = {"PG": ("res:0x0",), "E0": ("j1rec:slot0", "j1rec:slot1", "j1rec:cmd"),
        "T0": ("snap0:0x0acc",), "B": ("snap9:0x0c08",), "J1": ("j1",),
        "J2": ("j2rec:done", "j2rec:slot0", "j2rec:slot1")}
NEED = ("PG", "E0", "T0", "J1")
EARLY = ("LV-EARLY0", "LV-EARLY")
NOT_REACHED = ("LV-REBASE", "LV-HEAL", "LV-FILL")
FAULT_LINE = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)")
HANG_LINE = re.compile(r"\bhung\b|timed out")


def state_word(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def hexs(v):
    return "?" if v is None else f"0x{v:08x}"


def producible(row):
    return set()


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n, r in cases.items():
        K.text(d, n + ".txt")
        K.own_res(d, n)
        K.text(d, n + ".snap0.regs")
        K.text(d, n + ".snap9.regs")
        if r["class"] == "ok":
            for s in (".gate.json", ".gate-fill.txt", ".gate-tri.txt", ".devcd-pre.txt",
                      ".devcd.txt"):
                K.text(d, n + s)


def regs_of(text):
    """{offset: value} of `reg 0xOOOO 0xV` lines and {(kind, i): v} of hostctl/ta3dctl lines."""
    out = {}
    for m in re.finditer(r"^(reg|hostctl|ta3dctl) (0x[0-9a-f]+) (0x[0-9a-f]{8})$", text, re.M):
        k = int(m.group(2), 16)
        out[k if m.group(1) == "reg" else (m.group(1), k // 4)] = int(m.group(3), 16)
    return out


def stops(d, n):
    """The stop dumps' indices the runner kept for the row (NAME.stopI-*), in order."""
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
    """The 32 dwords of a command-6 job's slots 40-47 (dwords 224-255), or None."""
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
    """Job 1's start outcome (B11's table; DONE needs its record done and M4 with its run id)."""
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


def label_after(m, pre, post, after):
    if after is None or pre is None:
        return None
    if m in ("C", "S"):
        return "SAME" if after == pre else "DIFF"
    if pre == post:
        return "PREPOST"
    hit = [k for k, ok in (("REBASE", after == post), ("NONE", after == pre),
                           ("HIGH", after[:12] == pre[:12] and after[12:] == post[12:])) if ok]
    return hit[0] if len(hit) == 1 else "AMBIG" if hit else "OTHER"


def gate_window(d, n):
    """The kernel.log lines between the marks owntask-gate-begin NAME and owntask-gate NAME."""
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


def gate_of(d, n, order):
    """(gate1, gate1page, gate2, the fault (stat, word) or None, the window or None)."""
    win = gate_window(d, n)
    first, second = order.split(",")
    t1, t2 = K.text(d, f"{n}.gate-{first}.txt"), K.text(d, f"{n}.gate-{second}.txt")
    if win is None and not t1:
        return None, None, None, None, None
    fault = next(((int(m.group(1), 16), int(m.group(2), 16)) for m in
                  (FAULT_LINE.search(ln) for ln in win or []) if m), None)
    if win is None:             # no marks: no kernel line is the gate's, only an exact draw reads
        g1 = gp = "exact" if tool_exact(t1, first) else None
    elif fault and not tool_exact(t1, first):
        g1 = f"fault 0x{fault[0]:08x} 0x{fault[1]:08x}"
        gp = f"cid{fault[1] & 0xF} page 0x{fault[1] & ~0xFFF & 0xFFFFFFFF:08x}"
    elif tool_exact(t1, first) and not fault:
        g1 = gp = "exact"
    elif any(HANG_LINE.search(ln) for ln in (win or []) + t1.splitlines()):
        g1 = gp = "hang"
    else:
        g1 = gp = "other"
    g2 = "exact" if tool_exact(t2, second) else "other" if t2 else None
    return g1, gp, g2, fault, win


def devcd_of(d, n):
    t = K.text(d, n + ".devcd.txt")
    a = re.search(r"^BIF_INT_STAT: (0x[0-9a-f]+)$", t, re.M)
    b = re.search(r"^BIF_FAULT: (0x[0-9a-f]+)$", t, re.M)
    return f"0x{int(a.group(1), 16):08x} 0x{int(b.group(1), 16):08x}" if a and b else None


def readings_of(d, n, m, order):
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
    r = dict(page=page, where=where, run=run, recs=recs, snaps=snaps, stopregs=stopregs, T=t,
             pre=pre, post=post, pa=pa, runid1=runid1)
    s1 = rec[0].get("slot")
    s1 = s1 if isinstance(s1, list) and len(s1) == 4 and all(isinstance(x, int) for x in s1) \
        else [None] * 4
    c1 = rec[0].get("cmd_after")
    r["j1rec"] = {"slot0": s1[0], "slot1": s1[1], "cmd": c1 if isinstance(c1, int) else None}
    s2 = rec[1].get("slot") if rec[1] else None
    s2 = s2 if isinstance(s2, list) and len(s2) == 4 and all(isinstance(x, int) for x in s2) \
        else [None] * 4
    r["runid2"] = (rec[1].get("job") or {}).get("runid") if rec[1] else None
    r["j2rec"] = {"slot0": s2[0], "slot1": s2[1],
                  "done": None if not rec[1] else "done" if rec[1].get("done") is True
                  else "notdone"}
    v = snaps["snap0.regs"]
    r["V"] = {"@V0": v.get(("ta3dctl", 0)), "@V2": v.get(("ta3dctl", 2))}
    r["start"] = start_of(page, t, rec[0], runid1)
    r["j1"] = r["start"]
    for k, key in ((1, "j2"), (2, "j3")):
        r[key] = None if not rec[k] else "done" if rec[k].get("done") is True else "notdone"
    a2, a3 = after_of(rec[1]), after_of(rec[2])
    r["after"] = [a2, a3]
    r["after2"] = label_after(m, pre, post, a2) if r["j2"] == "done" and m6_ok(rec[1]) else None
    r["after2w"] = a2 if r["j2"] == "done" and m6_ok(rec[1]) else None
    r["heal"] = None if not (r["j3"] == "done" and m6_ok(rec[2]) and a3 and pre) else \
        "yes" if a3[13] == pre[13] else "no"
    bif = [w for w in (stopregs.get(BIF), snaps["snap9.regs"].get(BIF)) if w is not None]
    word = next((w for w in bif if w), 0 if bif else None)
    r["bif"] = word
    notdone = any(x.get("done") is False for x in recs[1:])
    r["kick"] = None if not notdone or word is None else \
        "none" if word == 0 else "cid15" if word & 0xF == 15 else "other"
    r["early"] = r["early0"] = None
    if m == "LV" and r["j1"] == "DONE" and word is not None:
        j2not = len(recs) > 1 and recs[1].get("done") is False
        r["early0"] = "yes" if j2not and word == 0x0000000F else "no"
        anyearly = notdone or bool(word and word & 0xF == 15)
        r["early"] = "no" if r["early0"] == "yes" else "yes" if anyearly else \
            "no" if len(recs) == len(jobs_of(m)) and word == 0 else None
    r["mmiss"] = None if post is None or pa is None else \
        "yes" if MK13 not in post + pa else "no"
    g1, gp, g2, fault, win = gate_of(d, n, order)
    r.update(gate1=g1, gate1page=gp, gate2=g2, fault=fault, window=win, devcd=devcd_of(d, n))
    return r


def jobs_of(m):
    return next(v[2] for v in STAGES.values() if v[0] == m)


def value_ok(spec, q, r):
    """A frozen value against the reading of quantity q: True, False or None."""
    page = r["page"]
    if q in ("j1", "j2", "j3", "after2", "heal", "kick", "early", "early0", "gate1", "gate2",
             "devcd"):
        got = r.get(q)
        if q == "after2" and got in ("PREPOST", "AMBIG"):
            return None             # rebase, none or high read alike: cannot tell
        return None if got is None else got == spec
    if q == "gate1page":
        got = r["gate1page"]
        if got is None:
            return None
        if spec == "@post13":
            if r["post"] is None:
                return None
            return got == f"cid15 page 0x{r['post'][13] & ~0xFFF & 0xFFFFFFFF:08x}"
        return got == spec
    m = re.fullmatch(r"(postsa|postpa|after2sa)([0-9]+)", q)
    if m:
        k = int(m.group(2))
        src = {"postsa": r["post"], "postpa": r["pa"], "after2sa": r["after2w"]}[m.group(1)]
        got = None if src is None or k >= len(src) else src[k]
    elif q == "j2rec:done":
        got = r["j2rec"]["done"]
        return None if got is None else got == spec
    elif q.startswith("j2rec:"):
        got = r["j2rec"].get(q[6:])
    elif q.startswith(("snap0:", "snap9:")):
        got = r["snaps"][q[:5] + ".regs"].get(int(q[6:], 16))
    elif q.startswith("j1rec:"):
        got = r["j1rec"].get(q[6:])
    else:
        i = K.res_index(q)
        got = None if page is None or i is None else page[i]
    if got is None:
        return None
    if spec == "running":
        return running(got)
    if spec == "@runid1":
        return got == r["runid1"]
    if spec == "@runid2":
        return got == r["runid2"]
    if spec in ("@V0", "@V2"):
        return None if r["V"][spec] is None else got == r["V"][spec]
    if spec.startswith("@notof:"):
        return got not in [int(x, 16) for x in spec[7:].split(",")]
    return got == int(spec, 16)


def all_of(states):
    states = list(states)
    if any(s is False for s in states):
        return False
    return None if any(s is None for s in states) else True


def diffs(a, b):
    if a is None or b is None:
        return "?"
    return ", ".join(f"sa{k} {hexs(a[k])}->{hexs(b[k])}" for k in range(32) if a[k] != b[k]) \
        or "none"


def survey_lines(n, r):
    out = []
    pre, post = r["pre"], r["post"]
    out.append(f"SURVEY {n} (printed): pre/post differ at {diffs(pre, post)}")
    for k, a in enumerate(r["after"], 2):
        if a is not None:
            out.append(f"SURVEY {n} job {k} after (printed): after vs pre: {diffs(pre, a)}; "
                       f"after vs post: {diffs(post, a)}")
    for lab, v in (("pre", pre), ("post sa", post), ("post pa", r["pa"])):
        out.append(f"SURVEY {n} {lab}: " + (" ".join(map(hexs, v)) if v else "?"))
    for k, a in enumerate(r["after"], 2):
        if a is not None:
            out.append(f"SURVEY {n} job {k} after: " + " ".join(map(hexs, a)))
    last = r["after"][1] or r["after"][0]
    if r["page"] is not None and last is not None:
        same = r["page"][AFTER_AT:AFTER_AT + 32] == last
        out.append(f"SURVEY {n}: the page's dwords 224-255 are the last after-read's: "
                   f"{'yes' if same else 'no'}")
    return out


def job_lines(n, r):
    out = []
    for k, rec in enumerate(r["recs"], 1):
        kick = rec.get("kick") if isinstance(rec.get("kick"), dict) else None
        out.append(f"JOB {n} {k} (printed): n {(rec.get('job') or {}).get('n')} run id "
                   f"{(rec.get('job') or {}).get('runid')} done {rec.get('done')} slot "
                   f"{' '.join(map(hexs, rec.get('slot') or []))} cmd_after "
                   f"{rec.get('cmd_after')} ticks {rec.get('ticks')}"
                   + (f" slept {rec['slept']}" if rec.get("slept") else "")
                   + (f" kick {json.dumps(kick.get('reply'), sort_keys=True)[:200]}" if kick
                      else ""))
        bif = rec.get("bif") if isinstance(rec.get("bif"), dict) else None
        out.append(f"BIF {n} job {k} (printed, K5): " + (
            "; ".join(f"{w} {bif_words(bif.get(w))}" for w in ("pre", "post")) if bif
            else "no bif words in the record"))
    if r["run"].get("stop"):
        out.append(f"JOB {n} (printed): the runner stopped: {r['run']['stop']}; alive "
                   f"{(r['run'].get('alive_at_stop') or {}).get('advancing')}")
    return out


def bif_words(v):
    if isinstance(v, list) and len(v) == 2:
        return f"BIF_INT_STAT {hexs(v[0])} BIF_FAULT {hexs(v[1])}"
    return json.dumps(v)


def rboot_lines(n, r):
    """C's R-BOOT (design §3.1): job 1's post pa0-pa15 against the odd words that never changed
    in nine kept rows, and the even ones as read. Printed, never scored."""
    pa = r["pa"]
    if pa is None:
        return [f"RBOOT {n} (printed): no post pa"]
    odd = [f"pa{k} {hexs(pa[k])} ({'as' if pa[k] == v else 'not'} §0.1's {hexs(v)})"
           for k, v in ODD_PA.items()]
    same = sum(pa[k] == v for k, v in ODD_PA.items())
    return [f"RBOOT {n} (printed): {same} of 8 odd pa as in nine kept rows: " + "; ".join(odd),
            f"RBOOT {n} (printed): even pa " + " ".join(f"pa{k} {hexs(pa[k])}"
                                                      for k in range(0, 16, 2))]


def gate_lines(n, r, order):
    out = [f"GATE {n} (printed): order {order}; first {r['gate1']} ({r['gate1page']}); second "
           f"{r['gate2']}; devcoredump {r['devcd'] or 'none'}"]
    if r["fault"] and r["post"]:
        page = r["fault"][1] & ~0xFFF & 0xFFFFFFFF
        hit = [f"sa{k}" for k in range(32) if r["post"][k] & ~0xFFF & 0xFFFFFFFF == page] + \
            [f"pa{k}" for k in range(16) if r["pa"][k] & ~0xFFF & 0xFFFFFFFF == page]
        out.append(f"GATE {n} (printed): the fault page 0x{page:08x} is job 1's post "
                   + (", ".join(hit) if hit else "none of its words"))
    if r["window"] is None:
        out.append(f"GATE {n} (printed): no gate marks in kernel.log")
    if r["bif"]:
        out.append(f"FAULT {n} (printed): BIF_FAULT 0x{r['bif']:08x} after the row: list "
                   f"{r['bif'] & 0xF}, page 0x{r['bif'] & ~0xFFF & 0xFFFFFFFF:08x}, offset "
                   f"0x{r['bif'] & 0xFF0:03x} (round 40's FAULT at #14's page + 0x10: E1171)")
    return out


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
    """{outcome: its prediction} from predictions/STAGE.tsv's source column."""
    out = {}
    for ln in open(os.path.join(KP, "predictions", f"{stage}.tsv")).read().splitlines()[1:]:
        f = ln.split("\t")
        if len(f) == 6 and f[3] != "CTL":
            out[f[3]] = pred_word(f[5])
    return out


def verdict(pred, state, held, x=""):
    if x in NOT_REACHED and set(EARLY) & set(held):
        return "not reached (" + ", ".join(e for e in EARLY if e in held) + ")"
    if state is None:
        return "cannot tell"
    if pred == "printed":
        return "printed"
    if pred in ("held", "held if reached"):
        return "held" if state else "FAILED"
    if pred == "failed":
        return "held" if not state else "FAILED"
    return "?"


def score_stage(stage, d):
    m, order, jobs = STAGES[stage]
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    lines, ctl_all, rl = [], {}, []
    for t in K.table(KP, stage):
        n = t["name"]
        if n not in cases and K.own_res(d, n) is None:
            continue
        q = preds.get(n, {})
        r = readings_of(d, n, m, order)
        if r["page"] is None:
            lines.append(f"ROW {n}: no results page kept: cannot tell")
            ctl_all.update({f"{n}:{k}": None for k in CTLS})
            continue
        models = sorted({x for mv in q.values() for x in mv if x != "CTL"})
        hyp = {x: all_of(value_ok(mv[x], k, r) for k, mv in q.items() if x in mv)
               for x in models}
        ctl = {c: all_of(value_ok(q[k]["CTL"], k, r) for k in ks) for c, ks in CTLS.items()}
        ctl_all.update({f"{n}:{k}": s for k, s in ctl.items()})
        p = r["page"]
        lines.append(f"ROW {n}: page {r['where']}; job 1 run id {r['runid1']}; start {r['start']}"
                     f"; T {' '.join(map(hexs, r['T'])) or '?'}; cmd {p[1]}; state {p[2]}; "
                     f"j2 {r['j2']}; after2 {r['after2']}; j3 {r['j3']}; heal {r['heal']}; "
                     f"early0 {r['early0']}; early {r['early']}; M13 nowhere {r['mmiss']}; "
                     f"BIF_FAULT {hexs(r['bif'])}")
        lines += [f"CONTROL {n}:{k}: {state_word(s)}" for k, s in ctl.items()]
        lines += [f"OUTCOME {n} {x}: {'held' if s else 'FAILED' if s is False else 'cannot tell'}"
                  for x, s in hyp.items()]
        held = [x for x, s in hyp.items() if s is True]
        need = [k for k in NEED if ctl[k] is not True]
        rl.append(arm_line(d))
        if need:
            rl.append(f"Q128-N3G-{m} RULE: CANNOT TELL ("
                      + "; ".join(f"control {k} {state_word(ctl[k])}" for k in need) + ")"
                      + (f"; FAULT: BIF_FAULT 0x{r['bif']:08x} after the row (its own reading, "
                         "printed)" if r["bif"] else ""))
        else:
            fault = ctl["B"] is False and not set(EARLY) & set(held)
            rl.append(f"Q128-N3G-{m} RULE: " + (", ".join(held) or "no frozen outcome holds")
                      + ("; FAULT: BIF_FAULT is not 0 after the row and no outcome names it"
                         if fault else "")
                      + ("; M-MISS: M13 in no word of job 1's post pa0-15 and sa0-31: the row "
                         "cannot tell sa13's source (row 3's question)"
                         if m == "M" and r["mmiss"] == "yes" else ""))
        fz = frozen(stage)
        for x in sorted(fz):
            rl.append(f"PREDICTION {x}: predicted {fz[x]}, read "
                      f"{'held' if hyp.get(x) else 'FAILED' if hyp.get(x) is False else 'cannot tell'}"
                      f": {verdict(fz[x], None if need else hyp.get(x), held, x)}")
        if ctl["J2"] is not True:
            rl.append(f"J2 {n} (printed): control J2 {state_word(ctl['J2'])}: job 2's after-read "
                      "outcomes cannot tell")
        rl += job_lines(n, r) + gate_lines(n, r, order) + survey_lines(n, r)
        if m == "C":
            rl += rboot_lines(n, r)
    if not rl:
        rl = [f"Q128-N3G-{m} RULE: CANNOT TELL (no row kept)"]
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
        lines, _, rl = score_stage(argv[1], argv[2])
        print("\n".join(lines + rl))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
