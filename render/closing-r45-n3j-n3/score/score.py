#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: the scorer of the r45-n3j-* sessions (the n3j design §3: which client event lands in
attribute 1, second reads, and what land's page follows; STEP below says the session: N1 stages wa
ff2 wb t2 wc tf2 wd tt we f3 f2b, N2 stages wg lf2, N3 stages wh lt, N4 stages wi lff), built on the
r44-n3i-* scorer. Every verdict rule comes from kit/scorekit.py, the kept files are read through
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
           M4 (dwords 80-81) with job 1's run id; else its start outcome (B11's table)
  j2       done or notdone (job 2's record), unread when the record is missing
  fault1   W: yes when snap9's BIF_FAULT or the disarm's (owntask.reset.json health) is not 0, no
           when both are 0, unread without the disarm's record and snap9 0
  j2fault  land rows: the first BIF_FAULT not 0 among job 2's K5 pre, mid, post as `cidC page
           0xPAGE` (C = bits 3:0), none when all are 0; @other: a cid page that is not post sa1's,
           page 0's or post sa13's; @hsa0: the page of design §0.4's H-SA0 rule (page 0 when post
           sa0 < 0x1000, post sa1's page when post sa0 = V0; unread for any other sa0)
  sa2shape job 1's post sa2: TIMER (top byte 0x01, bits 23:0 below 0x400000, not 0x061a70) or OTHER
  sa02kind land rows: job 1's post sa0 and sa2: LF (sa0 2 and a TIMER sa2), TRIPLE (sa0 0 and a
           TIMER sa2), ONE (V0 and V2), else OTHER
  dr       DR, the read rows' control: ok when the kernel log's marks between `row begin` and the
           owntask-arm name exactly one `health begin try 1 LIST` with LIST the stage's declared
           begin draws and each kept draw output is exact (fill: diff 0 of 2048, triangle: diff 0
           of 4096; none: the register health json ok), else the first thing that is not
  dk       DK (K9), the command count of the begin draws: ok when `ccb_sent` rises from the begin
           load to the arm's load by 2 + 2 x fills + 6 x tris, failed when not or on a begin
           health retry, unread (cannot tell) when a load or mark is missing; the KC lines print
           the begin and end counts and H-KC's word of each entry of the declared list (HKC)
  @post1 @post13  CID 15 and the page of job 1's post sa1 / sa13; @V0 @V2 TA3DCtl dwords 0 and 2 in
           the row's snap0; @any:W1,W2 and @notany:W1,W2 on postsa1: one of / none of those words
           (the word `tick` is a tick's: bits 23:0 0, top byte 1-4)
Each frozen outcome (predictions/STAGE.tsv, model = the outcome) holds when every one of its
quantities matches, FAILED when one does not, cannot tell when one is unread. Controls (model
CTL; all can fail): PG, E0, T0, B, J1, DR and DK (read and land rows) and the job controls (land
rows: J2).

RULE (frozen): `Q128-N3J-<STAGE> RULE: <the outcomes held>` when PG, E0, T0, J1 and DR (read and
land rows) passed (B failing is read by the outcomes that name a fault; with none of them held it
is `FAULT`); else `CANNOT TELL (...)`. A read or land stage's attribute-1 and page outcomes read
cannot tell unless the plant stage right before it in the same attempt (FF2: wa, T2: wb, TF2: wc,
TT: wd, F3: we, LF2: wg, LT: wh, LFF: wi; its kept directory beside KEPT_DIR, or in ROOTS) read W-SA1
(post sa1 = M1); F2b has no plant. DK failing or unread makes the outcomes that name a K read
cannot tell (design §3.2: FF2-FILL, T2-34, TF2-FILL, TT-LAST, TT-FIRST, TT-KEEP, F3-TICK, F3-FILL;
every F2b outcome; the -SA outcomes of the land rows); the -KEEP and -SAME outcomes of the other
reads still stand. F2b-SAME and its siblings also read cannot tell unless F3's end health was exact
and its end command count 10 (F3's kept directory beside KEPT_DIR). LT-PAGE and LT-HIST read cannot
tell when LT-ONE holds and job 2 was served (the page is mapped). Then one PREDICTION line per
frozen outcome: the prediction (held, failed, printed) against the reading. Printed, never scored:
the arm line, each job's line (Δtick), K5's words, the survey, attributes 3-12 (post sa3-sa12),
every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, KC
and HKC, and the notes of the design's cannot-tell rules."""
import json
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STEP = "N3"
# gen/make.py STAGES's: stage: (model, the row's jobs) (tests/test_gen.py: equal)
STAGES = {
    "N1": {"wa": ("W", ("j1",)), "ff2": ("FF2", ("j1",)), "wb": ("W", ("j1",)),
           "t2": ("T2", ("j1",)), "wc": ("W", ("j1",)), "tf2": ("TF2", ("j1",)),
           "wd": ("W", ("j1",)), "tt": ("TT", ("j1",)), "we": ("W", ("j1",)),
           "f3": ("F3", ("j1",)), "f2b": ("F2B", ("j1",))},
    "N2": {"wg": ("W", ("j1",)), "lf2": ("LF2", ("j1", "tick"))},
    "N3": {"wh": ("W", ("j1",)), "lt": ("LT", ("j1", "tick"))},
    "N4": {"wi": ("W", ("j1",)), "lff": ("LFF", ("j1", "tick"))},
}[STEP]
PLANT = {"ff2": "wa", "t2": "wb", "tf2": "wc", "tt": "wd", "f3": "we", "lf2": "wg", "lt": "wh",
         "lff": "wi"}
# the begin draws each stage declares (session.toml's begin_draws; tests/test_gen.py: equal) and
# the end draws (K9's end count; a land stage stops, its end draws are the recovery's)
DRAWS = {"ff2": "fill,fill", "t2": "tri", "tf2": "tri,fill", "tt": "tri,tri", "f3": "fill",
         "f2b": "fill", "lf2": "fill", "lt": "tri", "lff": "fill,fill"}
ENDS = {"wa": "none", "wb": "none", "wc": "none", "wd": "none", "we": "none", "wg": "none",
        "wh": "none", "wi": "none", "ff2": "fill,tri", "t2": "fill,tri", "tf2": "fill,tri",
        "tt": "fill,tri", "f3": "fill,tri", "f2b": "fill,tri"}
READS = ("FF2", "T2", "TF2", "TT", "F3", "F2B")
LANDS = ("LF2", "LT", "LFF")
# the outcomes that read cannot tell when the plant stage's W-SA1 did not hold (design §3.2,
# §3.4-§3.6: every word-reading outcome of a read stage; the attribute-1 and page outcomes of a
# land stage); the quiet and the printed OTHER ones never need it
NEEDS_PLANT = {
    "FF2": ("FF2-KEEP", "FF2-FILL", "FF2-TICK"), "T2": ("T2-SAME", "T2-34", "T2-KEEP"),
    "TF2": ("TF2-SAME", "TF2-FILL", "TF2-KEEP"),
    "TT": ("TT-LAST", "TT-FIRST", "TT-KEEP"), "F3": ("F3-KEEP", "F3-TICK", "F3-FILL"),
    "LF2": ("LF2-SA1", "LF2-TICK", "LF2-PAGE", "LF2-EARLY0", "LF2-EARLY1", "LF2-SERVE"),
    "LT": ("LT-SA1", "LT-PAGE", "LT-HIST", "LT-SERVE"),
    "LFF": ("LFF-SA1", "LFF-PAGE", "LFF-HIST"),
}
# the outcomes that name a K (design §3.2-§3.6): DK failing or unread makes them cannot tell
NEEDS_DK = {
    "FF2": ("FF2-FILL",), "T2": ("T2-34",), "TF2": ("TF2-FILL",),
    "TT": ("TT-LAST", "TT-FIRST", "TT-KEEP"), "F3": ("F3-TICK", "F3-FILL"),
    "F2B": ("F2b-SAME", "F2b-TICK", "F2b-FILL"),
    "LF2": ("LF2-SA1", "LF2-SA0", "LF2-SA2"), "LT": ("LT-SA1", "LT-TRIPLE"),
    "LFF": ("LFF-SA1", "LFF-SA0", "LFF-V0"),
}
ROW_FILES = (".txt", ".own_res.json", ".snap0.regs", ".snap9.regs")
STAGE_FILES = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {st: ROW_FILES + STAGE_FILES + ("owntask.reset.json",) for st, (m, _) in STAGES.items()}
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
JOB_CTLS.update({m: {"J2": ("j2rec:done", "j2rec:slot0", "j2rec:slot1")} for m in LANDS})
JOB_CTLS.update({m: {} for m in READS})
NEED = ("PG", "E0", "T0", "J1")
NAMES_FAULT = ("W-FAULT", "LF2-PAGE", "LF2-EARLY0", "LF2-EARLY1", "LT-PAGE", "LT-HIST",
               "LFF-PAGE", "LFF-HIST")
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
             "gate2", "j2fault", "j2kick", "gate1page"):
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
        if spec == "@hsa0":
            return None if r["hsa0"] is None else got == r["hsa0"]
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


def f3_end(stage, d, roots):
    """F2b: F3's end draws exact at their health and F3's end command count 10 (2 + the fill's 2
    + the triangle's 6: the end triangle's 3:22 is then at K 5): True, False, or None (no kept
    directory of f3)."""
    if stage != "f2b":
        return None
    cands = [os.path.join(os.path.dirname(os.path.abspath(d)), "f3")] + \
        [os.path.join(x, "f3") for x in roots]
    for c in cands:
        if os.path.isdir(c):
            ok = end_ok(c)
            e = K.kc(c, begin=DRAWS["f3"], end=ENDS["f3"])["end"]
            return None if ok is None else bool(ok and e["state"] == "ok" and e["delta"] == 10)
    return None


def unreadable(stage, m, x, r, plant, hyp, ctx):
    """The design's cannot-tell rule that makes outcome x unreadable, or None."""
    if stage in PLANT and x in NEEDS_PLANT.get(m, ()) and plant is not True:
        return f"cannot tell (W-SA1 {state_word(plant)} in the planting stage)"
    if x in NEEDS_DK.get(m, ()) and r["dk"] != "ok":
        return f"cannot tell (DK {'failed' if r['dk'] == 'failed' else 'unread'}: the begin " \
               "command count is not the expected one, so the entry K names is not known)"
    if m == "F2B" and x in NEEDS_DK["F2B"] and ctx["f3end"] is not True:
        return "cannot tell (F3's end health or end command count 10 not ok: the word before " \
               "F2b's fill is not the one assumed)"
    if m == "LT" and x in ("LT-PAGE", "LT-HIST") and hyp.get("LT-ONE") is True and \
            r["j2"] == "done":
        return "cannot tell (LT-ONE and job 2 served: the page of post sa1 is mapped, no fault " \
               "to read; the fault page is printed against post sa13)"
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
    if m in READS and r["bif"]:
        out.append(f"NOTE {stage}: B failing (a fault with no pass planned): stop the session "
                   "for the user")
    if m in LANDS and any(x.endswith("-SERVE") for x in held) and not r["bif"] and \
            r["j2fault"] in (None, "none"):
        out.append(f"NOTE {stage}: no fault and job 2 done: the tick-pass reading of design "
                   "§0.3 fails")
    return out


def score_stage(stage, d, roots=()):
    m, jobs = STAGES[stage]
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    lines, ctl_all, rl = [], {}, []
    ctls = dict(CTLS, **JOB_CTLS[m])
    if m != "W":
        ctls["DR"] = ("dr",)
        ctls["DK"] = ("dk",)
    need_ctls = NEED + (("DR",) if m != "W" else ())
    plant, where_plant = plant_of(stage, d, roots)
    ctx = {"f3end": f3_end(stage, d, roots)}
    for t in K.table(KP, stage):
        n = t["name"]
        if n not in cases and K.own_res(d, n) is None:
            continue
        q = preds.get(n, {})
        r = readings_of(d, n, m, stage)
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
                     f"j2 {r['j2']}; post sa1 {hexs(r['post'][1] if r['post'] else None)}; "
                     f"sa02kind {r['sa02kind']}; fault1 {r['fault1']}; j2fault {r['j2fault']}; "
                     f"DR {r['dr']}; DK {r['dk']}; BIF_FAULT {hexs(r['bif'])}")
        if stage in PLANT:
            lines.append(f"PLANT {n}: W-SA1 of stage {PLANT[stage]} {state_word(plant)} "
                         f"({where_plant or 'no kept directory'})")
        lines += [f"CONTROL {n}:{k}: {state_word(s)}" for k, s in ctl.items()]
        lines += [f"OUTCOME {n} {x}: {'held' if s else 'FAILED' if s is False else 'cannot tell'}"
                  for x, s in hyp.items()]
        held = [x for x, s in hyp.items() if s is True]
        need = [k for k in need_ctls if ctl[k] is not True]
        rl.append(arm_line(d))
        tag = f"Q128-N3J-{stage.upper()}"
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
        rl += kc_lines(d, n, stage)
        if r["dr"] != "ok" and m != "W":
            rl.append(f"DR {n} (printed): {r['dr']}")
        if m != "W" and r["dk"] != "ok":
            why = K.kc(d, begin=DRAWS.get(stage))["begin"]["why"] or "unread"
            rl.append(f"DK {n} (printed): control DK {state_word(ctl['DK'])}: {why}")
    if not rl:
        rl = [f"Q128-N3J-{stage.upper()} RULE: CANNOT TELL (no row kept)"]
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
