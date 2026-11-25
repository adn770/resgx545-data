#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: the scorer of the r46-n3k-* sessions (closing29/n3k/design.md §4 and §10: B5, B6 and
N1-N8, every session on the r46-kernel module; STEP below says the session), built on round 45's
scorer. Every verdict rule comes from kit/scorekit.py, the kept files are read through
kit/kitscore.py (K9's kc: the command count).

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
           pre, mid (a kicked job's) and post; every job-scoped quantity is read in its own job's
           record, never on the row-end page (the H3 slip, E1176)
  j1       DONE when job 1's record is done and the page has M1 and X0 (slot 1), S1 (dword 84) and
           M4 (dwords 80-81) with job 1's run id; else its start outcome (B11's table); start the
           same word (the B rows' start table: NEVER, T1, T2, T3, E1, DONE)
  j2       done or notdone (job 2's record), unread when the record is missing
  fault1   yes when snap9's BIF_FAULT or the disarm's (owntask.reset.json health) is not 0, no
           when both are 0, unread without the disarm's record and snap9 0
  j2fault  the first BIF_FAULT not 0 among job 2's K5 pre, mid, post as `cidC page 0xPAGE` (C =
           bits 3:0), none when all are 0; @faultnotin:P1,P2: a fault that is none of the listed
           pages; @notin:P: anything but that page, none (job 2 served, no fault) included
  sa02kind job 1's post sa0 and sa2: LF (sa0 2 and a TIMER sa2: top byte 0x01, bits 23:0 below
           0x400000, not 0x061a70), TRIPLE (sa0 0 and a TIMER sa2), ONE (V0 and V2), else OTHER
  zffkind  ZFF2: KEEP (sa1 M1 with LF), FILL2 (sa1 0x04000010 with TRIPLE), else OTHER
  prepost  the B rows: SAME when job 1's post sa0-sa31 = its pre sa0-sa31, else DIFF
  after2   the B rows: job 2's after-read (dwords 224-255, done with M6 and its run id) against
           job 1's pre and post: PRE, POST, BOTH (pre = post = after) or OTHER
  landing  the B rows: EVERY4 (V0 at pa0, pa4, pa8, pa12 and V2 at pa2, pa6, pa10, pa14), NONE (no
           V0 or V2 in pa0-pa15) or OTHER
  gate1    the gate's fill (exact, `fault STAT WORD`, hang, other); gate2 its triangle
  dr       DR: ok when the kernel log's marks between `row begin` and the owntask-arm name exactly
           one `health begin try 1 LIST` with LIST the stage's declared begin draws and each kept
           draw output is exact (fill: diff 0 of 2048, triangle: diff 0 of 4096; none: the
           register health json ok), else the first thing that is not
  dk       DK (K9), the command count of the begin draws: ok when `ccb_sent` rises from the begin
           load to the arm's load by 2 + 2 x fills + 6 x tris, failed when not or on a begin
           health retry, unread (cannot tell) when a load or mark is missing; the KC lines print
           the begin and end counts and H-KC's word of each entry of the declared list (HKC)
  @V0 @V2  TA3DCtl dwords 0 and 2 in the row's snap0; @any:W1,W2 and @notany:W1,W2 on postsa1: one
           of / none of those words
Each frozen outcome (predictions/STAGE.tsv, model = the outcome) holds when every one of its
quantities matches, FAILED when one does not, cannot tell when one is unread. Controls (model CTL;
all can fail): PG, E0, T0, B, J1, SV (design §4.1: the attempt's stage log names the r46-kernel
srcversion, installed and loaded), PLANT (the plant stage right before the stage in the same
attempt read W-SA1; its kept directory beside KEPT_DIR, or in ROOTS), DR and DK (ZFF2 and the land
rows after fills; printed in the page and B rows) and J2 (two-job rows, printed).

RULE (frozen): `Q128-N3K-<STAGE> RULE: <the outcomes held>` when PG, E0, T0, J1 (not in the B
rows, whose start is the reading), SV and DR (ZFF2 and the land rows after fills) passed (B
failing is read by the outcomes that name a fault; with none of them held it is `FAULT`); else
`CANNOT TELL (...)`. PLANT not held makes the outcomes of NEEDS_PLANT cannot tell; DK failing or
unread those of NEEDS_DK; a page row's -WRITE not held every page outcome of the row; a B row's
start not DONE its after-read, HID and landing outcomes. Then one PREDICTION line per frozen
outcome: the prediction (held, failed, printed) against the reading. Printed, never scored: the arm
line, each job's line (delta tick), K5's words, the survey (post sa0-sa31, pa0-pa15), attributes
3-12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines, KC and HKC, and the notes of the design's cannot-tell and stop rules.
"""
import json
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STEP = "B6"
SRCV = "10BBF3BFBD51D559106589F"   # the r46-kernel module (fork c5094783eb88): control SV
# gen/make.py STAGES's: stage: (model, the row's jobs) (tests/test_gen.py: equal)
STAGES = {
    "B5": {"b5": ("B5", ("j1", "kick"))},
    "B6": {"b6": ("B6", ("j1", "kick"))},
    "N1": {"wa": ("W", ("j1",)), "zff2": ("ZFF2", ("j1",)), "wb": ("W", ("j1",)),
           "lff2": ("LFF2", ("j1", "tick"))},
    "N2": {"wc": ("W", ("j1",)), "lff3": ("LFF3", ("j1", "tick"))},
    "N3": {"wd": ("W", ("j1",)), "lf3f": ("LF3F", ("j1", "tick"))},
    "N4": {"we": ("W", ("j1",)), "q2": ("Q2", ("j1", "tick"))},
    "N5": {"wf": ("W", ("j1",)), "r": ("R", ("j1", "tick"))},
    "N6": {"wg": ("W", ("j1",)), "p": ("P", ("j1", "tick"))},
    "N7": {"wh": ("W", ("j1",)), "r2": ("R2", ("j1", "tick"))},
    "N8": {"wi": ("W", ("j1",)), "p2": ("P2", ("j1", "tick"))},
}[STEP]
PLANT = {"zff2": "wa", "lff2": "wb", "lff3": "wc", "lf3f": "wd", "q2": "we", "r": "wf", "p": "wg",
         "r2": "wh", "p2": "wi"}
BUILD_CONTROL = "wa"
# the begin draws each stage declares (session.toml's begin_draws, the B rows the kit's default;
# tests/test_gen.py: equal) and the end draws (K9's end count; a land stage stops)
DRAWS = {"b5": "fill,tri", "b6": "fill,tri", "zff2": "fill,fill", "lff2": "fill,fill",
         "lff3": "fill,fill", "lf3f": "fill,fill,fill", "q2": "none", "r": "none", "p": "none",
         "r2": "none", "p2": "none"}
ENDS = {"wa": "none", "wb": "none", "wc": "none", "wd": "none", "we": "none", "wf": "none",
        "wg": "none", "wh": "none", "wi": "none", "zff2": "fill,tri", "b5": "fill,tri",
        "b6": "fill,tri"}
READS = ("ZFF2",)
LANDS = ("LFF2", "LFF3", "LF3F", "Q2", "R", "P", "R2", "P2")
FILLS = ("LFF2", "LFF3", "LF3F")
PAGES = ("Q2", "R", "P", "R2", "P2")
BROWS = ("B5", "B6")
# the outcomes that read cannot tell when the plant stage's W-SA1 did not hold (design §4.3-§4.5:
# the attribute-1 outcomes; the page rows write sa0 and sa1 themselves and print PLANT only)
NEEDS_PLANT = {
    "ZFF2": ("ZFF2-KEEP", "ZFF2-FILL2"),
    "LFF2": ("LFF2-KEEP", "LFF2-FILL2", "LFF2-FILL1"),
    "LFF3": ("LFF3-KEEP", "LFF3-FILL2", "LFF3-FILL1"),
    "LF3F": ("LF3F-KEEP", "LF3F-SECOND", "LF3F-LAST", "LF3F-FIRST"),
}
# the outcomes that name a K (design §4.4, §4.5): DK failing or unread makes them cannot tell
NEEDS_DK = {
    "ZFF2": ("ZFF2-FILL2",), "LFF2": ("LFF2-FILL2", "LFF2-FILL1"),
    "LFF3": ("LFF3-FILL2", "LFF3-FILL1"),
    "LF3F": ("LF3F-SECOND", "LF3F-LAST", "LF3F-FIRST"),
}
# a page row's outcomes that need its -WRITE (design §4.7-§4.9: J1 not DONE or -WRITE failed)
NEEDS_WRITE = {m: tuple(f"{m}-{x}" for x in xs) for m, xs in (
    ("Q2", ("SAME", "SA0", "OTHER", "SERVE")), ("R", ("LOW", "SA0", "OTHER", "SERVE")),
    ("R2", ("LOW", "SA0", "OTHER", "SERVE")), ("P", ("UNMAP", "MAPPED", "OTHER")),
    ("P2", ("UNMAP", "MAPPED", "OTHER")))}
# a B row's outcomes that need the program to have run to DONE (job 2, the survey, the landing)
NEEDS_DONE = {m: tuple(f"{m}-{x}" for x in ("HID", "SAME", "REBASE", "AOTHER", "NOKICK", "LAND4",
                                            "LANDNONE")) for m in BROWS}
ROW_FILES = (".txt", ".own_res.json", ".snap0.regs", ".snap9.regs")
STAGE_FILES = ("cases.tsv", "void.tsv", "readings.tsv")
# the disarm's record: not kept after a failed gate's recovery, the B rows' planned end
REQUIRED = {st: ROW_FILES + STAGE_FILES + (() if m in BROWS else ("owntask.reset.json",))
            for st, (m, _) in STAGES.items()}
GATES = {}
MAGIC, FILL = 0x4E574F53, 0xDEADC0DE
M1, X0, M4, S1, M6, T3 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306, 0x005A3305
PRE_AT, POST_SA_AT, POST_PA_AT, AFTER_AT = 128, 160, 192, 224
AFTER_SLOTS = list(range(40, 48))
TIM, BIF = 0x0ACC, 0x0C08
TIM_RUN, TIM_MAX = 1 << 24, 400000
MK13, MK1, V1 = 0x005D3000, 0x005D1000, 0x32005000
TICK_SA2 = 0x01061A70                        # a tick's sa2 (E746)
CTLS = {"PG": ("res:0x0",), "E0": ("j1rec:slot0", "j1rec:slot1", "j1rec:cmd"),
        "T0": ("snap0:0x0acc",), "B": ("snap9:0x0c08",), "J1": ("j1",)}
JOB_CTLS = {"W": {}}
JOB_CTLS.update({m: {"J2": ("j2rec:done", "j2rec:slot0", "j2rec:slot1")} for m in LANDS + BROWS})
JOB_CTLS.update({m: {} for m in READS})
LOADED = re.compile(r"^## (installed|loaded) module\n(\S+)$", re.M)
NEED = ("PG", "E0", "T0", "J1")
NAMES_FAULT = ("W-FAULT", "ZFF2-FAULT") + tuple(f"{m}-{x}" for m in LANDS for x in (
    "PAGE0", "SAME", "SA0", "LOW", "UNMAP", "OTHER", "MAPPED")) + tuple(f"{m}-FILL" for m in BROWS)
L4, Q0 = 0x04400000, 0x005D2000
W_FILL2 = 0x04000010
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
    if STAGES[stage][0] not in BROWS:
        K.text(d, "owntask.reset.json")
    for n, r in cases.items():
        for s in ROW_FILES[:1] + ROW_FILES[2:]:
            K.text(d, n + s)
        K.own_res(d, n)


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


def sa2_shape(post):
    """Job 1's post sa2 as a timer word: top byte 0x01, bits 23:0 below 0x400000, not a tick's
    0x061a70 (None when unread)."""
    if post is None:
        return None
    sa2 = post[2]
    return "TIMER" if sa2 >> 24 == 1 and sa2 & 0xFFFFFF < 0x400000 and sa2 != TICK_SA2 \
        else "OTHER"


def sa02_kind(post, v0, v2):
    """Land rows: job 1's post sa0 and sa2: LF, TRIPLE, ONE or OTHER (None when unread)."""
    if post is None or v0 is None or v2 is None:
        return None
    sa0, shape = post[0], sa2_shape(post)
    if sa0 == v0 and post[2] == v2:
        return "ONE"
    if sa0 == 2 and shape == "TIMER":
        return "LF"
    if sa0 == 0 and shape == "TIMER":
        return "TRIPLE"
    return "OTHER"


def landing_of(pa, v0, v2):
    """The B rows' landing lines: EVERY4 (V0 at pa0, pa4, pa8, pa12 and V2 at pa2, pa6, pa10,
    pa14, as 0x003 read, E1164), NONE (no V0 or V2 in pa0-pa15, as 0x843, E1162), else OTHER."""
    if pa is None or v0 is None or v2 is None:
        return None
    if all(pa[k] == v0 for k in (0, 4, 8, 12)) and all(pa[k] == v2 for k in (2, 6, 10, 14)):
        return "EVERY4"
    return "NONE" if v0 not in pa and v2 not in pa else "OTHER"


def hsa0_page(post, v0):
    """design §0.4's H-SA0 rule: the stop page `cid15 page 0x...` (page 0 when post sa0 < 0x1000,
    post sa1's page when post sa0 = V0), None for any other sa0 or when unread."""
    if post is None or v0 is None:
        return None
    if post[0] < 0x1000:
        return cidpage(0xF)
    if post[0] == v0:
        return cidpage(post[1] | 0xF)
    return None


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


MARK_LINE = re.compile(r"resgx545 \S+ (row begin|health (begin|end) try ([0-9]+) (\S+) |"
                       r"owntask-arm (\S+) )")


def marks(d):
    """The kernel log's kit marks in order: ('row begin',), ('health', phase, try, list) or
    ('arm', name)."""
    out = []
    for ln in K.text(d, "kernel.log").splitlines():
        m = MARK_LINE.search(ln)
        if not m:
            continue
        if m.group(1) == "row begin":
            out.append(("row begin",))
        elif m.group(5):
            out.append(("arm", m.group(5)))
        else:
            out.append(("health", m.group(2), int(m.group(3)), m.group(4)))
    return out


def kept_draws(d, phase, try_, draws):
    """Each draw's kept output of health `phase` try `try_` for the list `draws` (K8: the default
    fill,tri keeps NAME.fill<HN> and NAME.health<HN>; an explicit list NAME.fill<HN>.<i> and
    NAME.health<HN>.<i>): [(tool, text)], or the register health's json text for none."""
    if draws == "none":
        return [("none", K.text(d, f"{phase}.reghealth{try_}.txt"))]
    out = []
    for i, tool in enumerate(draws.split(","), 1):
        suf = "" if draws == "fill,tri" else f".{i}"
        name = f"{phase}.{'fill' if tool == 'fill' else 'health'}{try_}{suf}.txt"
        out.append((tool, K.text(d, name)))
    return out


def draws_exact(d, phase, try_, draws):
    """True when every kept output of the list is exact (an empty kept file is not)."""
    for tool, text in kept_draws(d, phase, try_, draws):
        if tool == "none":
            try:
                if json.loads(text).get("ok") is not True:
                    return False
            except (ValueError, AttributeError):
                return False
        elif not tool_exact(text, tool):
            return False
    return True


def dr_of(d, stage):
    """DR: 'ok', a reason it failed, or None when the kernel log has no row begin."""
    want = DRAWS.get(stage)
    ms = marks(d)
    if want is None or not any(x[0] == "row begin" for x in ms):
        return None
    i = [k for k, x in enumerate(ms) if x[0] == "row begin"][0]
    j = next((k for k, x in enumerate(ms) if k > i and x[0] == "arm"), len(ms))
    hs = [x for x in ms[i:j] if x[0] == "health" and x[1] == "begin"]
    if len(hs) != 1:
        return f"{len(hs)} begin health marks before the arm, one wanted"
    _, _, try_, got = hs[0]
    if try_ != 1:
        return f"the begin health ran at try {try_}, not 1"
    if got != want:
        return f"the begin draws were {got}, declared {want}"
    if not draws_exact(d, "begin", 1, want):
        return f"a kept draw of {want} is not exact"
    return "ok"


def end_ok(d):
    """A read stage's end health: exactly one end mark (try any, the default list) and every kept
    draw exact; None without a kernel log."""
    ms = marks(d)
    if not ms:
        return None
    hs = [x for x in ms if x[0] == "health" and x[1] == "end"]
    return len(hs) == 1 and hs[0][3] == "fill,tri" and draws_exact(d, "end", hs[0][2], "fill,tri")


def kc_of(d, stage):
    """K9's command count of the stage's kernel.log (begin and end), the declared lists given."""
    return K.kc(d, begin=DRAWS.get(stage), end=ENDS.get(stage))


def dk_of(d, stage):
    """DK: the begin command count: ok, failed or None (cannot tell)."""
    return K.kc_state(kc_of(d, stage), "begin")


def kc_lines(d, n, stage):
    """KC (printed): the begin and end counts, then HKC: H-KC's word of each entry of the declared
    begin list at K base 1 (the begin draws start after the debugfs reset's boot), never scored."""
    out = [f"{ln} (printed)" for ln in K.kc_text(n, kc_of(d, stage))]
    if stage in DRAWS:
        words = K.hkc_words(DRAWS[stage], 1)
        out.append(f"HKC {n} (printed, never scored): begin draws {DRAWS[stage]} (K from 1): "
                   + ("; ".join(words) if words else "no entry"))
    return out


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


def readings_of(d, n, m, stage=None):
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
    r["sa02kind"] = sa02_kind(post, r["V"]["@V0"], r["V"]["@V2"])
    r["sa2shape"] = sa2_shape(post)
    r["hsa0"] = hsa0_page(post, r["V"]["@V0"])
    r["zffkind"] = None if r["sa02kind"] is None else \
        "KEEP" if post[1] == MK1 and r["sa02kind"] == "LF" else \
        "FILL2" if post[1] == W_FILL2 and r["sa02kind"] == "TRIPLE" else "OTHER"
    r["prepost"] = None if pre is None or post is None else "SAME" if pre == post else "DIFF"
    a2 = after_of(rec[1]) if r["j2rec"]["done"] == "done" and m6_ok(rec[1]) else None
    r["after2"] = None if a2 is None or pre is None or post is None else \
        "BOTH" if a2 == pre and a2 == post else "PRE" if a2 == pre else \
        "POST" if a2 == post else "OTHER"
    r["landing"] = landing_of(pa, r["V"]["@V0"], r["V"]["@V2"])
    r["dk"] = dk_of(d, stage) if stage in DRAWS else None
    r["dr"] = dr_of(d, stage) if stage in DRAWS else None
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
    if q in ("j1", "j2", "j3", "after3", "fault1", "sa02kind", "sa2shape", "dr", "dk", "gate1",
             "gate2", "j2fault", "j2kick", "gate1page", "zffkind", "prepost", "after2", "landing",
             "start"):
        got = r.get(q)
        if got is None or (q == "after3" and got in ("PREPOST", "AMBIG")):
            return None
        if spec.startswith("@in:"):
            return got in spec[4:].split(",")
        if spec.startswith("@notin:"):
            return got not in spec[7:].split(",")
        if spec == "@other":          # a fault page that is none of post sa1's, page 0's, sa13's
            if r["post"] is None:
                return None
            return got not in ("none",) and got not in (
                cidpage(r["post"][1] | 0xF), cidpage(0xF), cidpage(r["post"][13] | 0xF))
        if spec.startswith("@faultnotin:"):   # a fault at a page that is none of the listed
            return got != "none" and got not in spec[12:].split(",")
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
        if got is not None and spec.startswith(("@any:", "@notany:")):
            hit = any(word_is(got, x) for x in spec.split(":", 1)[1].split(","))
            return hit if spec.startswith("@any:") else not hit
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
    if spec == "ok":
        return got == "ok"
    if spec == "running":
        return running(got)
    if spec in ("@runid1", "@runid2", "@runid3"):
        return got == r["runid" + spec[-1]]
    if spec in ("@V0", "@V2"):
        return None if r["V"][spec] is None else got == r["V"][spec]
    return got == int(spec, 16)


def word_is(got, item):
    """A word against one item of an @any/@notany list: a 0xHEX word, or `tick` (bits 23:0 zero,
    top byte 1-4: a tick's pa1, E746)."""
    if item == "tick":
        return got & 0xFFFFFF == 0 and 1 <= got >> 24 <= 4
    return got == int(item, 16)


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
        hit = [f"sa{k}" for k in (0, 1, 2, 13) if post and post[k] & ~0xFFF & 0xFFFFFFFF == pg]
        out.append(f"FAULT {n} (printed): {where} BIF_FAULT {hexs(f)} ({cidpage(f)}): "
                   + ("job 1's post " + ", ".join(hit) if hit else "none of job 1's post sa0, "
                      "sa1, sa2, sa13"))
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


def sv_of(d):
    """Control SV (design §9.2): the preflight of the attempt's stage log (the file STAGE.log
    beside the kept directory, the kit's `## installed module` and `## loaded module` lines) names
    the r46-kernel build's srcversion twice: True, False, or None (no log or no such lines)."""
    log = os.path.join(os.path.dirname(os.path.abspath(d)), os.path.basename(d) + ".log")
    try:
        t = open(log, errors="replace").read()
    except OSError:
        return None, None
    got = dict(LOADED.findall(t))
    if set(got) != {"installed", "loaded"}:
        return None, log
    return got["installed"] == SRCV and got["loaded"] == SRCV, log


def unreadable(stage, m, x, r, plant, hyp, ctx):
    """The design's cannot-tell rule that makes outcome x unreadable, or None."""
    if m in PAGES and x in NEEDS_WRITE[m] and hyp.get(f"{m}-WRITE") is not True:
        return f"cannot tell ({m}-WRITE not held: the image's words are not in sa0 and sa1)"
    if m in BROWS and x in NEEDS_DONE[m] and r["start"] != "DONE":
        return f"cannot tell (the start is {r['start']}, not DONE: no after-read, survey or landing)"
    if x in NEEDS_PLANT.get(m, ()) and plant is not True:
        return f"cannot tell (W-SA1 {state_word(plant)} in the planting stage)"
    if x in NEEDS_DK.get(m, ()) and r["dk"] != "ok":
        return f"cannot tell (DK {'failed' if r['dk'] == 'failed' else 'unread'}: the begin " \
               "command count is not the expected one, so the entry K names is not known)"
    return None


def verdict(pred, state, x, why):
    if why:
        return why
    if state is None:
        return "cannot tell"
    if pred == "printed":
        return "printed"
    if pred == "held":
        return "held" if state else "FAILED"
    if pred == "failed":
        return "held" if not state else "FAILED"
    return "?"


def notes(stage, m, r, held, hyp):
    out = []
    if m == "W" and "W-FAULT" in held:
        out.append(f"NOTE {stage}: W-FAULT: a pass ran that we did not expect: stop the session "
                   "for the user")
    if m == "W" and "W-SA1" not in held:
        out.append(f"NOTE {stage}: W-SA1 not held: the next stage's attribute-1 outcomes read "
                   "cannot tell (nothing was planted)")
    if stage == BUILD_CONTROL and (not {"W-SA1", "W-SA13", "W-QUIET"} <= set(held)
                                   or "W-FAULT" in held):
        out.append(f"NOTE {stage}: WA (the build control on the r46-kernel module, design §10.3) "
                   "failed an outcome: stop the round's N rows for the user (the rebuild changed "
                   "the arm path or the mark bytes)")
    if m in READS and r["bif"]:
        out.append(f"NOTE {stage}: ZFF2-FAULT (a BIF fault in a quiet read): the row's read "
                   "stands, stop the session for the user")
    if m in LANDS and r["j2"] == "done" and r["j2fault"] in (None, "none") and m not in ("P",
                                                                                     "P2"):
        out.append(f"NOTE {stage}: no fault and job 2 done: the tick-pass stop of every land row "
                   "so far did not come")
    if m in BROWS and r["start"] not in (None, "DONE"):
        out.append(f"NOTE {stage}: the start is {r['start']}, not DONE: "
                   + ("NEVER for this sideband: the rule 'bits 1:0 decide' is wrong for it; stop "
                      "the round's B rows and bring it to the user" if r["start"] == "NEVER" else
                      "a partial start: stop the B rows for the user"))
    if m in BROWS and r["bif"]:
        out.append(f"NOTE {stage}: a BIF fault after the row ({hexs(r['bif'])}): stop the B "
                   "rows for the user")
    return out


def score_stage(stage, d, roots=()):
    m, jobs = STAGES[stage]
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    lines, ctl_all, rl = [], {}, []
    ctls = dict(CTLS, **JOB_CTLS[m])
    scored = m in READS + FILLS        # DR and DK scored; printed in the page and B rows
    if scored:
        ctls["DR"] = ("dr",)
        ctls["DK"] = ("dk",)
    need_ctls = tuple(k for k in NEED if not (m in BROWS and k == "J1")) + \
        (("DR",) if scored else ()) + ("SV",)
    plant, where_plant = plant_of(stage, d, roots)
    ctx = {}
    sv, where_sv = sv_of(d)
    for t in K.table(KP, stage):
        n = t["name"]
        if n not in cases and K.own_res(d, n) is None:
            continue
        q = preds.get(n, {})
        r = readings_of(d, n, m, stage)
        if r["page"] is None:
            lines.append(f"ROW {n}: no results page kept: cannot tell")
            ctl_all.update({f"{n}:{k}": None for k in list(ctls) + ["SV"]})
            continue
        models = sorted({x for mv in q.values() for x in mv if x != "CTL"})
        hyp = {x: all_of(value_ok(mv[x], k, r) for k, mv in q.items() if x in mv)
               for x in models}
        ctl = {c: all_of(value_ok(q[k]["CTL"], k, r) for k in ks) for c, ks in ctls.items()}
        ctl["SV"] = sv
        if stage in PLANT:
            ctl["PLANT"] = plant
        ctl_all.update({f"{n}:{k}": s for k, s in ctl.items() if k != "PLANT"})
        p = r["page"]
        lines.append(f"ROW {n}: page {r['where']}; job 1 run id {r['runid1']}; start {r['start']}"
                     f"; T {' '.join(map(hexs, r['T'])) or '?'}; cmd {p[1]}; state {p[2]}; "
                     f"j2 {r['j2']}; post sa0 {hexs(r['post'][0] if r['post'] else None)}; "
                     f"post sa1 {hexs(r['post'][1] if r['post'] else None)}; "
                     f"sa02kind {r['sa02kind']}; fault1 {r['fault1']}; j2fault {r['j2fault']}; "
                     f"DR {r['dr']}; DK {r['dk']}; BIF_FAULT {hexs(r['bif'])}")
        if stage in PLANT:
            lines.append(f"PLANT {n}: W-SA1 of stage {PLANT[stage]} {state_word(plant)} "
                         f"({where_plant or 'no kept directory'})"
                         + ("; printed only (the image writes sa0 and sa1 itself)"
                            if m in PAGES else ""))
        lines.append(f"SV {n}: srcversion {SRCV} installed and loaded: {state_word(sv)} "
                     f"({where_sv or 'no stage log'})")
        lines += [f"CONTROL {n}:{k}: {state_word(s)}" for k, s in ctl.items()]
        lines += [f"OUTCOME {n} {x}: {'held' if s else 'FAILED' if s is False else 'cannot tell'}"
                  for x, s in hyp.items()]
        held = [x for x, s in hyp.items() if s is True]
        need = [k for k in need_ctls if ctl[k] is not True]
        rl.append(arm_line(d))
        tag = f"Q128-N3K-{stage.upper()}"
        if need:
            rl.append(f"{tag} RULE: CANNOT TELL ("
                      + "; ".join(f"control {k} {state_word(ctl[k])}" for k in need) + ")"
                      + (f"; FAULT: BIF_FAULT {hexs(r['bif'])} after the row (its own reading, "
                         "printed)" if r["bif"] else ""))
        else:
            fz = frozen(stage)
            counted = [x for x in held if fz.get(x) != "printed"
                       and not unreadable(stage, m, x, r, plant, hyp, ctx)]
            fault = ctl["B"] is False and not set(NAMES_FAULT) & set(held)
            rl.append(f"{tag} RULE: " + (", ".join(counted) or "no frozen outcome holds")
                      + ("; FAULT: BIF_FAULT is not 0 after the row and no outcome names it"
                         if fault else ""))
        fz = frozen(stage)
        for x in sorted(fz):
            rl.append(f"PREDICTION {x}: predicted {fz[x]}, read "
                      f"{'held' if hyp.get(x) else 'FAILED' if hyp.get(x) is False else 'cannot tell'}"
                      f": {verdict(fz[x], None if need else hyp.get(x), x, unreadable(stage, m, x, r, plant, hyp, ctx))}")
        for k in JOB_CTLS[m]:
            if ctl[k] is not True:
                rl.append(f"{k} {n} (printed): control {k} {state_word(ctl[k])}")
        rl += notes(stage, m, r, held, hyp)
        rl += job_lines(n, r) + fault_lines(n, r) + survey_lines(n, r) + events_lines(d, n)
        rl.append(f"AFTER {n} (printed): job 2's after-read against job 1's pre and post: "
                  f"{r['after2']}; post against pre: {r['prepost']}; landing {r['landing']}; "
                  f"gate fill {r['gate1']}, triangle {r['gate2']}")
        rl += kc_lines(d, n, stage)
        if r["dr"] != "ok" and m != "W":
            rl.append(f"DR {n} (printed{'' if scored else ', not scored here'}): {r['dr']}")
        if m != "W" and r["dk"] != "ok":
            why = K.kc(d, begin=DRAWS.get(stage))["begin"]["why"] or "unread"
            rl.append(f"DK {n} (printed{'' if scored else ', not scored here'}): control DK "
                      f"{state_word(None if r['dk'] is None else False)}: {why}")
    if not rl:
        rl = [f"Q128-N3K-{stage.upper()} RULE: CANNOT TELL (no row kept)"]
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
