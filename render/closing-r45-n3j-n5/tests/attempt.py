# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds a kept attempt of one stage of the session (its one row) for
tests/test_score.py, the way the kit's runner keeps it, from the KEPT stages of round 44 (pinned
in session.toml, resgx545-data ebfeaa775): N1's wa (row W: mark, one job, post sa1 = M1 and sa13 =
M13, the disarm's record, no gate), N1's ff (crumb3 after fill,fill: job 1's page and record, the
begin draws kept as begin.fill1.1, the end draws as end.fill2 and end.health2; the base of every Z
stage) and N2's lm (land after no draw: V0, M1, V2, job 2 not served, its K5 at M1's page, the
runner's stop, begin.reghealth1: the base of stage q and of ZN's begin draws `none`). The base's
page, job 1's record, snap0, snap9 and kernel.log are copied as they were kept, the row renamed to
the stage's (NAME = STAGE1-a); the tokens then edit what the session's predictions read, as
fwtask_run.py run and the kit keep it, the kernel log's `ccb_sent` lines following the declared
draw lists (K9: 2 + 2 per fill + 6 per triangle). A Z stage is built beside its plant stage (wj
wk wl wm wn wo wp) unless `noplant`, and beside zn (ZN's control) unless `nozn`. Every stage gets
its stage log beside the kept directory (STAGE.log: the kit's preflight lines `## installed
module` and `## loaded module`, control SV). Not a test module (no test_ prefix).

Tokens (a set):
  W (a plant stage)  base wa, job 1 alone, snap9 BIF_FAULT 0, the disarm's record
             (owntask.reset.json) with BIF_FAULT 0; wfault (snap9 BIF_FAULT 0x005d300f),
             resetfault (the disarm's BIF_FAULT 0x005d300f), noreset (no disarm record), nosa1
             (post sa1 0x04400000)
  Z (zn zt zft zf zff ztf ztt)  base ff, job 1 alone, snap9 BIF_FAULT 0, the disarm's record, begin
             draws as the stage declares (the health mark at try 1 and each draw kept exact; zn's
             `none` the register health), the end draws (fill,tri at try 2, kept), ccb_sent as
             the lists make it; post sa0, sa1, sa2 the stage's predicted words unless sa0=, sa1=,
             sa2= 0xWORD; one (sa0 V0, sa2 V2), drmark, drretry, drbad, drgone, dkbad, dkgone,
             rfault (snap9 BIF_FAULT 0x005d300f), znbad (zn reads other), nozn (no zn beside it)
  land (q)   base lm; job 2 not done, its K5 at Q0's page (the H-SA0 page); post sa0 Q0, sa1 M1,
             sa2 V2; sa0=, sa1=, sa2= override; low (the K5 page M1's), early0, early13, other
             (the K5 fault page), serve (job 2 done, its after = post, K5 0, snap9 0)
  plant      noplant (no planting stage), wfail (the planting stage's sa1 not M1)
  controls   pgbad, e0bad (job 1's record's slot 1 marker 0), e0cmd (its cmd_after 1), t0stop,
             j1bad (M4 absent), svbad (the loaded module another), svinst (the installed one),
             svgone (no stage log)"""
import gzip
import json
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import make  # noqa: E402
import pins  # noqa: E402

D = "data:render/closing-r44-n3i-"
A1, A2 = "n1/out/20261124-005624/", "n2/out/20261124-010001/"
BASES = {"w": (D + A1 + "wa/", "wa1-a"), "r": (D + A1 + "ff/", "ff1-a"),
         "l": (D + A2 + "lm/", "lm1-a")}
ROW = (".own_res.json.gz", ".txt.gz", ".snap0.regs.gz", ".snap9.regs.gz")
STOP = (".stop1-own_res.json.gz", ".stop1-regs.txt.gz")
FILES = {"w": [BASES["w"][1] + f for f in ROW] + ["kernel.log"],
         "r": [BASES["r"][1] + f for f in ROW] + ["kernel.log", "begin.fill1.1.txt.gz",
                                                  "end.health2.txt.gz"],
         "l": [BASES["l"][1] + f for f in ROW + STOP] + ["kernel.log", "begin.reghealth1.txt.gz"]}
PINS = [BASES[b][0] + f for b in BASES for f in FILES[b]]
M6, FILL, MK13, MK1 = 0x5A5A3306, 0xDEADC0DE, 0x005D3000, 0x005D1000
FAULT = [0x000D0400, MK13 | 0xF]
SRCV = "EC553F41FD8324BB6BF1764"
Q0 = 0x005D2000
# a Z stage's predicted post sa0, sa1, sa2 (the held outcomes of design §9.4; "V0" and "V2" the
# TA3DCtl words of the stage's snap0; the timer words are LC's and LF's kept ones) and the land
# stage's (§9.5)
TIMER_T, TIMER_F = 0x0104B95B, 0x01049B60
ZWORDS = {"zn": ("V0", MK1, "V2"), "zt": (0, 0x02400000, TIMER_T),
          "zft": (0, 0x04400000, TIMER_T), "zf": (2, MK1, TIMER_F), "zff": (2, MK1, TIMER_F),
          "ztf": (2, 0x02400000, TIMER_F), "ztt": (0, 0x08400000, TIMER_T)}
LWORDS = {"q": (Q0, MK1, "V2")}


def gz(path, data):
    with open(path + ".gz", "wb") as f:
        f.write(gzip.compress(data if isinstance(data, bytes) else data.encode(), mtime=0))


def regs_edit(t, tim=None, bif=None):
    if tim is not None:
        t = re.sub(r"^reg 0x0acc 0x[0-9a-f]{8}$", f"reg 0x0acc 0x{tim:08x}", t, flags=re.M)
    if bif is not None:
        t = re.sub(r"^reg 0x0c08 0x[0-9a-f]{8}$", f"reg 0x0c08 0x{bif:08x}", t, flags=re.M)
    return t


def after_slots(job, after):
    return {str(s): after[4 * i:4 * i + 4] for i, s in enumerate(job["slots"])}


def load(b, n):
    src, bn = BASES[b]
    page = json.loads(pins.blob(src + bn + ".own_res.json.gz"))
    page = list(page["page"] if isinstance(page, dict) else page)
    run = json.loads(pins.blob(src + bn + ".txt.gz"))
    return dict(page=page, recs=[dict(x) for x in run["records"]],
                snap0=pins.blob(src + bn + ".snap0.regs.gz").decode(),
                snap9=pins.blob(src + bn + ".snap9.regs.gz").decode(),
                klog=pins.blob(src + "kernel.log").decode().replace(bn, n), extra={})


def strip_gate(klog):
    return "\n".join(ln for ln in klog.splitlines()
                     if "owntask-gate" not in ln and "BIF fault" not in ln) + "\n"


def controls(w, x):
    if "e0bad" in w:
        x["recs"][0]["slot"] = [0, *x["recs"][0]["slot"][1:]]
    if "e0cmd" in w:
        x["recs"][0]["cmd_after"] = 1
    if "pgbad" in w:
        x["page"][0] = 0
    if "j1bad" in w:
        x["page"][0x50] = FILL
    if "t0stop" in w:
        x["snap0"] = regs_edit(x["snap0"], tim=0)


def stage_log(root, stage, w):
    """STAGE.log beside the kept directory: the preflight's installed and loaded module lines
    (control SV); svbad (loaded another), svinst (installed another), svgone (no log)."""
    if "svgone" in w:
        return
    loaded = "0123456789ABCDEF0123456" if "svbad" in w else SRCV
    inst = "0123456789ABCDEF0123456" if "svinst" in w else SRCV
    open(os.path.join(root, stage + ".log"), "w").write(
        f"## stage {stage} of r45j5\n## uname\n6.1.0\n## installed module\n{inst}\n"
        f"## loaded module\n{loaded}\n## debugfs directory: /sys/kernel/debug/dri/0/sgx\n")


def write(root, stage, row, jobs, x, stop=None, reset=None, cls=None, w=()):
    d = os.path.join(root, stage)
    os.makedirs(d, exist_ok=True)
    n = row["name"]
    run = {"name": n, "records": x["recs"], "stop": stop, "n_jobs": len(jobs),
           "ran": len(x["recs"])}
    if stop:
        run["alive_at_stop"] = {"advancing": False, "ticks": [7, 7, 7]}
        gz(os.path.join(d, f"{n}.stop1-own_res.json"), json.dumps(x["page"]))
        gz(os.path.join(d, f"{n}.stop1-regs.txt"), x["snap9"])
    gz(os.path.join(d, n + ".own_res.json"), json.dumps({"page": x["page"]}))
    gz(os.path.join(d, n + ".txt"), json.dumps(run))
    gz(os.path.join(d, n + ".snap0.regs"), x["snap0"])
    gz(os.path.join(d, n + ".snap9.regs"), x["snap9"])
    open(os.path.join(d, "kernel.log"), "w").write(x["klog"])
    for f, body in x["extra"].items():
        gz(os.path.join(d, f), body)
    if reset is not None:
        gz(os.path.join(d, "owntask.reset.json"), json.dumps(reset))
    stage_log(root, stage, w)
    rc, c = (1, cls or "fail") if stop else (0, "ok")
    cases = ["\t".join(K.COLUMNS), "\t".join([n, stage, row["set"], row["risk"], "-", "owntask",
                                              row["args"], str(rc), c, "-", "-", "1000"])]
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(cases) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(K.COLUMNS) + "\n")
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d


def plant_stage(stage):
    return next((s for s in make.STAGES[make.STEP] if s[0] == stage), None)


def tok_word(w, key, default):
    t = next((x for x in w if x.startswith(key + "=")), None)
    return default if t is None else int(t.split("=", 1)[1], 16)


def mark_line(phase, try_, draws, run="1795478253-20968"):
    """A kit health mark line as the kernel log keeps it."""
    return f"Nov 24 00:57:41 cedar unknown: resgx545 r45j1 health {phase} try {try_} {draws} {run}"


def exact(tool):
    """A kept exact draw: ff's begin fill and end triangle (round 44, as kept)."""
    name = "begin.fill1.1.txt.gz" if tool == "fill" else "end.health2.txt.gz"
    return pins.blob(BASES["r"][0] + name).decode()


def draws_files(extra, phase, try_, draws, bad=False):
    """The kept outputs of health `phase` try `try_` for the list `draws` (K8's names); none: the
    register health's json (lm's begin.reghealth1, round 44)."""
    if draws == "none":
        t = pins.blob(BASES["l"][0] + "begin.reghealth1.txt.gz").decode()
        extra[f"{phase}.reghealth{try_}.txt"] = t.replace('"ok": true}', '"ok": false}') if bad else t
        return
    for i, tool in enumerate(draws.split(","), 1):
        suf = "" if draws == "fill,tri" else f".{i}"
        extra[f"{phase}.{'fill' if tool == 'fill' else 'health'}{try_}{suf}.txt"] = \
            exact(tool).replace("diff: 0 of", "diff: 7 of") if bad else exact(tool)


LOAD = re.compile(r"ccb_sent [0-9]+ ")


def set_begin(x, stage, w):
    """The stage's begin health in the kernel log and the kept files: the declared list at try 1,
    right after the begin load (as the kit writes it); drmark, drretry, drbad, drgone edit it."""
    want = make.DRAWS[stage]
    logged = "fill,tri" if "drmark" in w and want != "fill,tri" else want
    if "drmark" in w and want == "fill,tri":
        logged = "fill"
    lines = [ln for ln in x["klog"].splitlines() if " health begin try " not in ln]
    i = next(k for k, ln in enumerate(lines) if "row begin" in ln)
    j = next(k for k in range(i, len(lines)) if "ccb_sent" in lines[k])
    lines.insert(j + 1, mark_line("begin", 1, logged))
    if "drretry" in w:
        lines.insert(j + 2, mark_line("begin", 2, logged))
    x["klog"] = "\n".join(lines) + "\n"
    for k in [k for k in x["extra"] if k.startswith("begin.")]:
        del x["extra"][k]
    if "drgone" not in w:
        draws_files(x["extra"], "begin", 1, want, bad="drbad" in w)


def set_kc(x, stage, w):
    """The kernel log's `ccb_sent` at the four loads (begin, arm, disarm, exit) as the declared
    lists make them (K9): n1 = n0 + 2 + 2 per fill + 6 per triangle, the disarm's load 2 after the
    arm's, the exit's the end list's count after it; dkbad (the arm's one too high), dkgone (the
    begin load line removed)."""
    kc = __import__("kitscore")
    lines = x["klog"].splitlines()
    at = [k for k, ln in enumerate(lines) if "ccb_sent" in ln]
    n0 = int(re.search(r"ccb_sent ([0-9]+) ", lines[at[0]]).group(1))
    n1 = n0 + kc.kc_expected(make.DRAWS[stage]) + ("dkbad" in w)
    want = [n0, n1]
    if len(at) >= 4:
        e0 = n1 + 2
        want += [e0, e0 + kc.kc_expected(make.ENDS.get(stage) or "fill,tri")]
    for k, n in zip(at, want):
        lines[k] = LOAD.sub(f"ccb_sent {n} ", lines[k])
    if "dkgone" in w:
        del lines[at[0]]
    x["klog"] = "\n".join(lines) + "\n"


def set_end(x, w, stage):
    """The stage's end draws (the default fill,tri at try 2, kept exact)."""
    lines = [ln for ln in x["klog"].splitlines() if " health end try " not in ln]
    j = next(k for k, ln in enumerate(lines) if "owntask-disarm" in ln)
    k = next(k for k in range(j, len(lines)) if "ccb_sent" in lines[k])
    marks = [mark_line("end", 2, "fill,tri")]
    lines[k + 1:k + 1] = marks
    x["klog"] = "\n".join(lines) + "\n"
    for f in [f for f in x["extra"] if f.startswith("end.")]:
        del x["extra"][f]
    draws_files(x["extra"], "end", 2, "fill,tri")


def build_w(root, stage, w, row, jobs):
    x = load("w", row["name"])
    x["recs"] = x["recs"][:1]
    x["snap9"] = regs_edit(x["snap9"], bif=MK13 | 0xF if "wfault" in w else 0)
    if "nosa1" in w:
        x["page"][161] = 0x04400000
    controls(w, x)
    reset = None if "noreset" in w else {
        "ok": True, "own_arm": "off", "health": {"ok": "resetfault" not in w, "bif_int_stat": 0,
                                                 "bif_fault": MK13 | 0xF if "resetfault" in w
                                                 else 0, "event_status2": 0x400}}
    return write(root, stage, row, jobs, x, reset=reset, w=w)


def vwords(x):
    """TA3DCtl dwords 0 and 2 of the row's snap0."""
    return tuple(int(re.search(rf"^ta3dctl 0x{4 * i:02x} (0x[0-9a-f]{{8}})$", x["snap0"],
                               re.M).group(1), 16) for i in (0, 2))


def post_words(w, x, words):
    """Job 1's post sa0, sa1, sa2 (page dwords 160-162): the stage's, V0 and V2 spelt; sa0=, sa1=,
    sa2= override; `one` (sa0 V0, sa2 V2); znbad (zn: sa0 0)."""
    v0, v2 = vwords(x)
    sa = [{"V0": v0, "V2": v2}.get(c, c) for c in words]
    sa = [tok_word(w, f"sa{k}", sa[k]) for k in range(3)]
    if "one" in w:
        sa[0], sa[2] = v0, v2
    x["page"][160], x["page"][161], x["page"][162] = sa


def build_read(root, stage, w, row, jobs):
    x = load("r", row["name"])
    x["recs"] = x["recs"][:1]
    x["klog"] = strip_gate(x["klog"])
    post_words(w if stage != "zn" or "znbad" not in w else w | {"sa0=0x00000000"}, x,
               ZWORDS[stage])
    x["snap9"] = regs_edit(x["snap9"], bif=MK13 | 0xF if "rfault" in w else 0)
    controls(w, x)
    set_begin(x, stage, w)
    set_end(x, w, stage)
    set_kc(x, stage, w)
    reset = {"ok": True, "own_arm": "off", "health": {"ok": True, "bif_int_stat": 0,
                                                      "bif_fault": 0, "event_status2": 0x400}}
    return write(root, stage, row, jobs, x, reset=reset, w=w)


def build_land(root, stage, w, row, jobs):
    x = load("l", row["name"])
    r2 = x["recs"][1]
    r2["job"] = dict(jobs[1], runid=2)
    x["recs"] = x["recs"][:2]
    pg = x["page"]
    v0, v2 = vwords(x)
    post_words(w, x, LWORDS[stage])
    page = {"low": MK1 | 0xF, "early0": 0xF, "early13": MK13 | 0xF, "other": 0x12345000 | 0xF}
    fw = next((v for k, v in page.items() if k in w), Q0 | 0xF)
    r2["bif"] = {"pre": [0xD0400, fw], "post": [0xD0400, fw]}
    controls(w, x)
    set_begin(x, stage, w)
    set_kc(x, stage, w)
    ok = {"ok": True, "own_arm": "off", "health": {"ok": True, "bif_int_stat": 0,
                                                   "bif_fault": 0, "event_status2": 0x400}}
    if "serve" in w:
        post = pg[160:192]
        x["recs"][1] = dict(r2, done=True, cmd_after=0, slot=[M6, 2, FILL, FILL],
                            slots=after_slots(r2["job"], post),
                            bif={"pre": [0x80000, 0], "post": [0x80000, 0]})
        pg[224:256] = post
        x["snap9"] = regs_edit(x["snap9"], bif=0)
        return write(root, stage, row, jobs, x, reset=ok, w=w)
    x["snap9"] = regs_edit(x["snap9"], bif=fw)
    return write(root, stage, row, jobs, x, stop="no done within 200 ms (job 1); firmware "
                 "hung: the tick stopped", cls="hang", w=w)


def build(root, stage, tokens):
    """root/STAGE/ under `tokens` (and its planting stage and zn beside it); returns STAGE's dir."""
    w = set(tokens)
    st = plant_stage(stage)
    m = st[1]
    (row,) = K.table(KP, stage)
    a = json.loads(row["args"])
    jobs = a if isinstance(a, list) else [a]
    if m == "W":
        return build_w(root, stage, w, row, jobs)
    if stage in make.PLANT and "noplant" not in w:
        pw = make.PLANT[stage]
        (prow,) = K.table(KP, pw)
        build_w(root, pw, {"nosa1"} if "wfail" in w else set(), prow, [jobs[0]])
    if m in make.READS and stage != "zn" and "nozn" not in w:
        (zrow,) = K.table(KP, "zn")
        build_read(root, "zn", {"znbad"} if "znbad" in w else set(), zrow, [jobs[0]])
    if m in make.LANDS:
        return build_land(root, stage, w, row, jobs)
    return build_read(root, stage, w, row, jobs)
