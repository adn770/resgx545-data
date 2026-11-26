# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds a kept attempt of one stage of the session (its one row) for
tests/test_score.py, the way the kit's runner keeps it, from KEPT stages: pinned in session.toml
(resgx545-data 72e07b2d6) round 45's N4 wi (row W: mark, one job, post sa1 = M1 and sa13 = M13,
the disarm's record, no gate; the base of every plant stage), N5 zff (its kept exact fill and
triangle: the draw outputs), N4 lff (land after fill,fill: job 2 not served, its K5 at page 0, the
runner's stop; the base of LFK, LTK, LFK2 and LFKP) and N6 q (landq after no draw: job 2 not
served at M1's page, the stop, begin.reghealth1; the base of R, P, R2 and P2). The base's page,
records, snap0, snap9 and kernel.log are copied as they were kept, the row renamed to the stage's
(NAME = STAGE1-a); the tokens then edit what the session's predictions read, the kernel log's
`ccb_sent` lines following the declared draw lists (K9: 2 + 2 per fill + 6 per triangle) and, for
a PAD stage, the begin load's N0 (900 unless pad= or padlow). A land stage is built beside its plant
stage unless `noplant`. Every stage gets its stage log beside the kept directory (STAGE.log: the
kit's preflight lines `## installed module` and `## loaded module`, control SV).
replay(root, stage, kept) copies a kept stage WHOLE (no token edits; its own stage log; the plant
stage of that attempt beside it as this stage's plant): the design's fixtures (§11.5) round 45's
LFF (E1217), LF2 (E1213), LT (E1215) and Q (E1233) at the pinned data commit, and round 46's n1
lff2 and n4 q2 (with wb and we), byte copies of the kept files under tests/fixtures/ (not yet in
resgx545-data; tests/test_score.py checks each against the kept raw.sha256); doctor `pad900` gives
the replay's begin load ccb_sent 900 (and the arm's 900 + its delta). Not a test module.

Tokens (a set):
  W (a plant stage)  base wi, job 1 alone, snap9 BIF_FAULT 0, the disarm's record with BIF_FAULT
             0; wfault (snap9 BIF_FAULT 0x005d300f), resetfault (the disarm's BIF_FAULT
             0x005d300f), noreset (no disarm record), nosa1 (post sa1 0x04400000)
  land       (lfk ltk lfk2 lfkp: base lff; r p r2 p2: base q) job 2 not done, its K5 at the
             predicted page (M1's for lfk, lfk2, lfkp and r; 0x02400000 for ltk; Q0's for p)
             unless pg=0xWORD; post sa0, sa1, sa2 the predicted words and sa12 V0 unless sa0=,
             sa1=, sa2=, sa12= 0xWORD; serve (job 2 done, its after = post, K5 0, snap9 0);
             drmark, drretry, drbad, drgone, dkbad, dkgone; pad=N (the begin N0), padlow (138)
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

D = "data:render/closing-r45-n3j-"
A4, A5, A6 = "n4/out/20261124-210745/", "n5/out/20261125-092017/", "n6/out/20261125-092604/"
A2, A3 = "n2/out/20261124-210558/", "n3/out/20261124-210651/"
FIX = "fix:"                               # tests/fixtures/ (round 46's kept stages, byte copies)
BASES = {"w": (D + A4 + "wi/", "wi1-a"), "r": (D + A5 + "zff/", "zff1-a"),
         "l": (D + A4 + "lff/", "lff1-a"), "q": (D + A6 + "q/", "q1-a")}
ROW = (".own_res.json.gz", ".txt.gz", ".snap0.regs.gz", ".snap9.regs.gz")
STOP = (".stop1-own_res.json.gz", ".stop1-regs.txt.gz")
FILES = {"w": [BASES["w"][1] + f for f in ROW] + ["kernel.log"],
         "r": ["kernel.log", "begin.fill1.1.txt.gz", "end.health2.txt.gz"],
         "l": [BASES["l"][1] + f for f in ROW + STOP] + ["kernel.log"],
         "q": [BASES["q"][1] + f for f in ROW + STOP] + ["kernel.log", "begin.reghealth1.txt.gz"]}
# the design's fixtures (§11.5): kept stages replayed whole, with their plants
KEPT = {"lff": (D + A4, "lff", "wi"), "lf2": (D + A2, "lf2", "wg"), "lt": (D + A3, "lt", "wh"),
        "q": (D + A6, "q", "wq"), "n1lff2": (FIX + "r46-n1/", "lff2", "wb"),
        "n4q2": (FIX + "r46-n4/", "q2", "we")}


def _plant_files(n):
    return [n + "1-a" + f for f in ROW] + ["kernel.log", "owntask.reset.json.gz"]


KEPT_FILES = {"lff": ["lff1-a" + f for f in ROW + STOP] + ["kernel.log", "begin.fill1.1.txt.gz",
                                                          "begin.fill1.2.txt.gz"],
              "lf2": ["lf21-a" + f for f in ROW + STOP] + ["kernel.log", "begin.fill1.1.txt.gz"],
              "lt": ["lt1-a" + f for f in ROW + STOP] + ["kernel.log", "begin.health1.1.txt.gz"],
              "q": ["q1-a" + f for f in ROW + STOP] + ["kernel.log", "begin.reghealth1.txt.gz"],
              "lff2": ["lff21-a" + f for f in ROW + STOP] + ["kernel.log", "begin.fill1.1.txt.gz",
                                                            "begin.fill1.2.txt.gz"],
              "q2": ["q21-a" + f for f in ROW + STOP] + ["kernel.log", "begin.reghealth1.txt.gz"],
              **{w: _plant_files(w) for w in ("wi", "wg", "wh", "wq", "wb", "we")}}
PINS = sorted({BASES[b][0] + f for b in BASES for f in FILES[b]}
              | {KEPT[k][0] + p + "/" + f for k in KEPT for p in (KEPT[k][1], KEPT[k][2])
                 for f in KEPT_FILES[p] if not KEPT[k][0].startswith(FIX)}
              | {KEPT[k][0] + KEPT[k][1] + ".log" for k in KEPT if not KEPT[k][0].startswith(FIX)})
# the fixture files (tests/fixtures/, each with its kept raw.sha256)
FIXTURES = sorted({KEPT[k][0][len(FIX):] + p + "/" + f for k in KEPT if KEPT[k][0].startswith(FIX)
                   for p in (KEPT[k][1], KEPT[k][2]) for f in KEPT_FILES[p] + ["raw.sha256"]}
                  | {KEPT[k][0][len(FIX):] + KEPT[k][1] + ".log" for k in KEPT
                     if KEPT[k][0].startswith(FIX)})
M6, FILL, MK13, MK1, T3 = 0x5A5A3306, 0xDEADC0DE, 0x005D3000, 0x005D1000, 0x005A3305
SRCV = "10BBF3BFBD51D559106589F"
Q0, L4, T22 = 0x005D2000, 0x04400000, 0x02400000
TIMER_F = 0x01049B60                     # LF's kept sa2 timer word
# a stage's predicted post sa0, sa1, sa2 ("V0" and "V2" the TA3DCtl words of the stage's snap0)
# and the land stages' predicted K5 fault word
WORDS = {"lfk": (2, MK1, TIMER_F), "lfk2": (2, MK1, TIMER_F), "lfkp": (2, MK1, TIMER_F),
         "ltk": (0, T22, TIMER_F), "r": (L4, MK1, "V2"), "r2": (L4, MK1, "V2"),
         "p": ("V0", Q0, "V2"), "p2": ("V0", Q0, "V2")}
PAGE = {"lfk": MK1 | 0xF, "lfk2": MK1 | 0xF, "lfkp": MK1 | 0xF, "ltk": T22 | 0xF,
        "r": MK1 | 0xF, "r2": MK1 | 0xF, "p": Q0 | 0xF, "p2": Q0 | 0xF}
LAND_BASE = {"LFK": "l", "LTK": "l", "LFK2": "l", "LFKP": "l", "R": "q", "R2": "q", "P": "q",
             "P2": "q"}


def blob(src):
    """A kept file's bytes (a .gz unpacked): a data pin, or a fixture under tests/fixtures/."""
    if not src.startswith(FIX):
        return pins.blob(src)
    b = open(os.path.join(KP, "tests/fixtures", src[len(FIX):]), "rb").read()
    return gzip.decompress(b) if src.endswith(".gz") else b


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
    x = dict(page=page, recs=[dict(r) for r in run["records"]],
             snap0=pins.blob(src + bn + ".snap0.regs.gz").decode(),
             snap9=pins.blob(src + bn + ".snap9.regs.gz").decode(),
             klog=pins.blob(src + "kernel.log").decode().replace(bn, n), extra={})
    return x


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
        f"## stage {stage} of r46k1\n## uname\n7.3.0-resgx545\n## installed module\n{inst}\n"
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
    return f"Nov 25 00:57:41 cedar unknown: resgx545 r46k1 health {phase} try {try_} {draws} {run}"


def exact(tool):
    """A kept exact draw: zff's begin fill and end triangle (round 45, as kept)."""
    name = "begin.fill1.1.txt.gz" if tool == "fill" else "end.health2.txt.gz"
    return pins.blob(BASES["r"][0] + name).decode()


def draws_files(extra, phase, try_, draws, bad=False):
    """The kept outputs of health `phase` try `try_` for the list `draws` (K8's names); none: the
    register health's json (q's begin.reghealth1, round 45)."""
    if draws == "none":
        t = pins.blob(BASES["q"][0] + "begin.reghealth1.txt.gz").decode()
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
    """The kernel log's `ccb_sent` at the loads (begin, arm, then disarm and exit when kept) as
    the declared lists make them (K9): n1 = n0 + 2 + 2 per fill + 6 per triangle, the disarm's
    load 2 after the arm's, the exit's the end list's count after it; dkbad (the arm's one too
    high), dkgone (the begin load line removed)."""
    kc = __import__("kitscore")
    lines = x["klog"].splitlines()
    at = [k for k, ln in enumerate(lines) if "ccb_sent" in ln]
    n0 = int(re.search(r"ccb_sent ([0-9]+) ", lines[at[0]]).group(1))
    if stage in make.PADS:
        t = next((x for x in w if x.startswith("pad=")), None)
        n0 = 138 if "padlow" in w else int(t[4:]) if t else 900      # decimal
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
    lines[k + 1:k + 1] = [mark_line("end", 2, "fill,tri")]
    x["klog"] = "\n".join(lines) + "\n"
    for f in [f for f in x["extra"] if f.startswith("end.")]:
        del x["extra"][f]
    draws_files(x["extra"], "end", 2, "fill,tri")


OK_RESET = {"ok": True, "own_arm": "off", "health": {"ok": True, "bif_int_stat": 0,
                                                     "bif_fault": 0, "event_status2": 0x400}}


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
    sa2= override."""
    v0, v2 = vwords(x)
    sa = [{"V0": v0, "V2": v2}.get(c, c) for c in words]
    sa = [tok_word(w, f"sa{k}", sa[k]) for k in range(3)]
    x["page"][160], x["page"][161], x["page"][162] = sa
    x["page"][172] = tok_word(w, "sa12", v0)          # E12: post sa12 = V0 unless sa12=


def build_read(root, stage, w, row, jobs):
    x = load("r", row["name"])
    x["recs"] = x["recs"][:1]
    x["klog"] = strip_gate(x["klog"])
    post_words(w, x, WORDS[stage])
    x["snap9"] = regs_edit(x["snap9"], bif=MK13 | 0xF if "rfault" in w else 0)
    controls(w, x)
    set_begin(x, stage, w)
    set_end(x, w, stage)
    set_kc(x, stage, w)
    return write(root, stage, row, jobs, x, reset=dict(OK_RESET), w=w)


def build_land(root, stage, w, row, jobs, base):
    x = load(base, row["name"])
    r2 = x["recs"][1]
    r2["job"] = dict(jobs[1], runid=2)
    x["recs"] = x["recs"][:2]
    pg = x["page"]
    post_words(w, x, WORDS[stage])
    fw = tok_word(w, "pg", PAGE[stage])
    r2["bif"] = {"pre": [0xD0400, fw], "post": [0xD0400, fw]}
    controls(w, x)
    set_begin(x, stage, w)
    set_kc(x, stage, w)
    if "serve" in w:
        post = pg[160:192]
        x["recs"][1] = dict(r2, done=True, cmd_after=0, slot=[M6, 2, FILL, FILL],
                            slots=after_slots(r2["job"], post),
                            bif={"pre": [0x80000, 0], "post": [0x80000, 0]})
        pg[224:256] = post
        x["snap9"] = regs_edit(x["snap9"], bif=0)
        return write(root, stage, row, jobs, x, reset=dict(OK_RESET), w=w)
    x["snap9"] = regs_edit(x["snap9"], bif=fw)
    return write(root, stage, row, jobs, x, stop="no done within 200 ms (job 2); firmware "
                 "hung: the tick stopped", cls="hang", w=w)


def build(root, stage, tokens):
    """root/STAGE/ under `tokens` (and its planting stage beside it); returns STAGE's dir."""
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
    if m in make.LANDS:
        return build_land(root, stage, w, row, jobs, LAND_BASE[m])
    return build_read(root, stage, w, row, jobs)


def copy_kept(root, src, name, dst, dst_name):
    """A kept stage directory copied file by file from the pins, the row renamed."""
    d = os.path.join(root, dst)
    os.makedirs(d, exist_ok=True)
    for f in KEPT_FILES[name]:
        b = blob(src + name + "/" + f)
        out = f.replace(name + "1-a", dst_name, 1)
        if f == "kernel.log":
            open(os.path.join(d, f), "wb").write(b.decode().replace(name + "1-a", dst_name).encode())
        else:
            gz(os.path.join(d, out[:-3] if out.endswith(".gz") else out), b)
    return d


def replay(root, stage, kept, doctor=None):
    """root/STAGE/ as kept the stage `kept` (a KEPT key), whole, with that attempt's stage log and
    its plant stage beside it as this stage's plant; doctor "pad900": the kernel log's ccb_sent
    lines moved so the begin load reads 900 (the design's doctored n1 lff2); "qdoc": job 2's K5
    BIF_FAULT words at 0x005d200f."""
    src, name, plant = KEPT[kept]
    (row,) = K.table(KP, stage)
    d = copy_kept(root, src, name, stage, row["name"])
    if stage in make.PLANT:
        (prow,) = K.table(KP, make.PLANT[stage])
        pd = copy_kept(root, src, plant, make.PLANT[stage], prow["name"])
        write_cases(pd, prow, make.PLANT[stage], 0, "ok")
    open(os.path.join(root, stage + ".log"), "wb").write(blob(src + name + ".log"))
    if doctor == "pad900":
        p = os.path.join(d, "kernel.log")
        lines = open(p).read().splitlines()
        at = [k for k, ln in enumerate(lines) if "ccb_sent" in ln]
        n = [int(re.search(r"ccb_sent ([0-9]+) ", lines[k]).group(1)) for k in at]
        for k, v in zip(at, n):
            lines[k] = LOAD.sub(f"ccb_sent {900 + v - n[0]} ", lines[k])
        open(p, "w").write("\n".join(lines) + "\n")
    if doctor == "qdoc":
        p = os.path.join(d, row["name"] + ".txt.gz")
        run = json.loads(gzip.decompress(open(p, "rb").read()))
        b = run["records"][1]["bif"]
        for k in b:
            if b[k][1]:
                b[k][1] = Q0 | 0xF
        os.remove(p)
        gz(p[:-3], json.dumps(run))
    write_cases(d, row, stage, 1, "hang")
    return d


def write_cases(d, row, stage, rc, cls):
    cases = ["\t".join(K.COLUMNS), "\t".join([row["name"], stage, row["set"], row["risk"], "-",
                                              "owntask", row["args"], str(rc), cls, "-", "-",
                                              "1000"])]
    open(os.path.join(d, "cases.tsv"), "w").write("\n".join(cases) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(K.COLUMNS) + "\n")
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
