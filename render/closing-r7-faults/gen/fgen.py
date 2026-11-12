#!/usr/bin/env python3
"""fgen.py: r7-faults (round 7, area faults: Q003's -110 after a held reset, Q111's `lock #0` twice), the one source of the tables,
the predictions, TABLES.md, stages.txt and gen/data/sources.lst.  Written and run before the freeze; tests/test_gen.py checks that
the files are what this makes.

  PY gen/fgen.py            write the files
  PY gen/fgen.py --check    exit 1 if any file differs from what it would write (nothing written)

Plan closing7/c/exp-faults-r7.md (sections 1.3 to 1.5 and 2.2), decisions closing7/DECISIONS-R7.md R7-2 (a) and the plan's own
decisions 2 (a) and 3 (a): stages L, d and m; a -110 is a reading; budget 16 timed-out boots.  No Q294 rows (O4 failed its controls,
E902).  Predictions start from E901's frozen rule R-PAGE.  Every control declares the readings it needs, and scorekit.refuse_unreadable
refuses one that its row's job cannot produce (HACKING "Session build rules"); the generator stops before writing anything if one does.

Hypotheses (frozen in predictions/*.tsv; [infer] where ours):
  Stage L (Q111, the lockup path's `lock #0` twice; E088's counter probe, a 64 x 32 fill whose 2048 instances add 1 to a scratch
  dword; `count` = the dword minus 0xd0000000, the quads that added, 512 when every quad did):
    H-SELF    [infer]: the second `lock` of a mutex its quad holds blocks the holder: l2 and l3 hang with 0.
    H-REFLAG  [infer]: it does not block, and one `release` frees the mutex (a flag): l2 and l3 complete with 512.
    H-RECOUNT [infer]: it does not block, and the locks are counted: l2 completes with 512, l3 hangs after one quad (1).
    controls: l0 (lock #0 ... release #0, E088's case 1: 512) and l1 (lock #0, lock #1, ..., release #1, release #0: 512 [infer]);
    l4 (lock #0, no release) replicates E088's case 3 (hang, 1).
  Stage d (Q003, the fault-page dose: E848's held job at seven sizes; `boot_held` = the first boot after the held reset, `timeout` (no
  INIT_COMPLETE, "SGX recovery failed: -110") or `up`):
    H-PAGE    (E901's frozen rule R-PAGE, fit 770 of 771, SEMI 16 of 17 on r6-held): the boot after a 0x90004 fault with SB 6 times
              out iff the job's fault page is 0x20006 to 0x20008; so also the first replay's boot (`boot_replay1`).
    H-SIZE    (E892's wording read literally: "the timeouts followed the 288 x 144 cells"): it times out iff the size is 288 x 144.
    controls: d0 640 x 480 up, d1 288 x 144 timeout (both rules; a 640 x 480 time-out stops the stage, the plan's premise).
    H-DONE (the plan's rival) is NOT frozen: its number per size (F2, the pages a completed four-array job allocates) was not compiled
    and no kept file reads it; CR_DPM_PAGE_STATUS at the hold is printed per cell (explore) for a later fold.
  Stage m (Q003, two manipulations at 288 x 144, order M0 M1 M2 M2 M1 M0):
    H-CLR     [infer, E826 f2 against E789 a6]: toggling CR_BIF_CTRL.CLEAR_FAULT (debugfs kregnow 0x0c00^=0x10 twice) while the fault
              is held makes the boot come up.
    H-TIME    [infer, the same pair: f2 was held 9.1 s]: a hold of 9 s before the reset makes the boot come up.
    H-NULL    (R-PAGE): the boot times out as in M0, whatever the manipulation.
    controls: M0 times out (both m0 cells); M1's kregnow lines show the registers hidden and back (E826, 4 of 4).
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
import scorekit  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data"
E848 = DATA + "/render/closing-r4-render4x/out/20261111-211649/h"
R6H = DATA + "/render/closing-r6-held/out/20261112-154536/q"
E826 = DATA + "/render/closing-r3k-pixel/out/20261110-193547/k-bif"
E088 = DATA + "/usse/quad-lock/usse-quad-lock-counter"

POKES = "--poke cmd:1=0xe0000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26"


def job(w, h):
    """E848's cell job byte for byte but the size (r6-held's): the 4x full triangle, E824's words, no --aa4, maximum = size."""
    return ("tri --tri-full --keep-going --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d %s"
            % (w, h, w, h, POKES))


# ---- the TA-data layout of the fork (branch resgx545 at 3f0b3e74, sgx_render.c sgx_render_layout and sgx_render_tadata_layout_in),
# one array of region headers (render_rgn_arrays 1), the maximum's own 1x tail room (no --aa4): the first page past the TA data,
# where the TA's region-header writes of four or five arrays fault (E507, E729, E789: the frozen model of closing2/r2-pixel) --------
def rup(a, m):
    return (a + m - 1) // m * m


def layout(w, h):
    tx, ty = (w + 31) // 32, (h + 15) // 16
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = rup((tx + n - 1) // n, 4), rup((ty + n - 1) // n, 4)
    span, side = max(n * mx, n * my), 1
    while side < span:
        side <<= 1
    rgn_size = 0xc0 * (mx // 4) * (my // 4) * n * n
    control = rup(4 * side * side, 4096)
    rgn = control + 3 * 4096
    size = rgn + rup(rgn_size, 4096) + rup(rgn_size, 4096)
    return {"n": n, "side": side, "rgn_size": rgn_size, "rgn": rgn, "size": size}


def fault_page(w, h):
    """The job's fault page if four and five arrays both pass the TA data's end (E729: f is 4 or 5), else None."""
    L = layout(w, h)
    if L["rgn"] + 4 * L["rgn_size"] <= L["size"]:
        return None
    return 0x20000 + (L["size"] >> 12)


def word(page, cid=1):
    return "0x%08x" % ((page << 12) | 0x060 | cid)


R_PAGE = range(0x20006, 0x20009)          # E901: 0x20006 to 0x20008 time out


# ---- the cells ---------------------------------------------------------------------------------------------------------------
# d: name, size, set; the plan's seven: 0x20006 (288 x 144, control), 0x20006 at a second size, 0x20007, 0x20008 (320 x 400) twice,
# 0x20009, 0x2000a (640 x 480, control).  0x20007 has no size under the layout (README "Deviations" 1): 384 x 384 (0x20008, E729's
# kept fault) takes its place.  The controls first: a stage stop on d0 leaves nothing half read.
D_CELLS = [
    ("d0-640x480", (640, 480), "control"),
    ("d1-288x144", (288, 144), "control"),
    ("d2-320x400", (320, 400), "heldout"),
    ("d3-256x288", (256, 288), "heldout"),
    ("d4-128x528", (128, 528), "heldout"),
    ("d5-384x384", (384, 384), "heldout"),
    ("d6-320x400", (320, 400), "heldout"),
]
# m: name, manipulation (none, clr, long), set: M0 M1 M2 M2 M1 M0, all 288 x 144
M_CELLS = [
    ("m0a-none", "none", "control"),
    ("m1a-clr", "clr", "heldout"),
    ("m2a-long", "long", "heldout"),
    ("m2b-long", "long", "heldout"),
    ("m1b-clr", "clr", "heldout"),
    ("m0b-none", "none", "control"),
]
# L: name, set, then the rows per model (class, count)
L_ROWS = [
    ("l0-lock-release", "control", {"L-CTL": ("ok", "512")}),
    ("l1-lock0-lock1", "control", {"L-CTL": ("ok", "512")}),
    ("l2-lock-lock-rel-rel", "heldout", {"H-SELF": ("hang", "0"), "H-REFLAG": ("ok", "512"), "H-RECOUNT": ("ok", "512")}),
    ("l3-lock-lock-rel", "heldout", {"H-SELF": ("hang", "0"), "H-REFLAG": ("ok", "512"), "H-RECOUNT": ("hang", "1")}),
    ("l4-lock-norel", "replicate", {"L-REP": ("hang", "1")}),
]
L_SRC = {"L-CTL": "E088: lock #0 / release #0 serialises the 512 quads (0xd0000200)", "L-REP": "E088 case 3: the job hung, 0xd0000001",
         "H-SELF": "[infer] a second lock of a held mutex blocks its holder", "H-REFLAG": "[infer] a re-lock passes, one release frees it",
         "H-RECOUNT": "[infer] a re-lock passes, the locks are counted"}
L_SRC_L1 = "[infer] two mutexes: a second lock as such does not hang"

S0_ROWS = [
    "n0-clr-idle|control|safe|gate|-|-",
    "c1-tri|control|safe|expectdiff|-|tri --keep-going",
]


def l_rows():
    return ['%s|%s|risky|probe|-|probe --temps 32 --pixels "$S/%s.bin"' % (n, s, n) for n, s, _ in L_ROWS]


def d_rows():
    out = []
    for name, (w, h), sset in D_CELLS:
        knobs = "held rgn:1 expectdiff hypo:d:7 cell:health" + (" ctl640" if (w, h) == (640, 480) else "")
        out.append("%s|%s|risky|%s|-|%s" % (name, sset, knobs, job(w, h)))
    return out


def m_rows():
    out = []
    for name, man, sset in M_CELLS:
        knobs = "held rgn:1 expectdiff hypo:m:6 cell:health" + {"none": "", "clr": " clr", "long": " long"}[man]
        out.append("%s|%s|risky|%s|-|%s" % (name, sset, knobs, job(288, 144)))
    return out


# ---- predictions -------------------------------------------------------------------------------------------------------------
HEADER = "case\tquantity\tvalue\tmodel\tset\tsource"


def s0_preds():
    return [
        "n0-clr-idle\tset_rc\t0\tGATE\tcontrol\tfork 3f0b3e74: kregnow's BIF rows are taken with no job unfinished (E826 n0)",
        "n0-clr-idle\tset_reads\t0x00000010\tGATE\tcontrol\tE826 n0: BIF_CTRL reads 0x10 after the set",
        "n0-clr-idle\tset_int\t0x00080000\tGATE\tcontrol\tE826 n0: BIF_INT_STAT idle (0x80000) with the bit set",
        "n0-clr-idle\tback_reads\t0x00000000\tGATE\tcontrol\tE826 n0: BIF_CTRL back to 0",
        "c1-tri\tclass\tok\tHEALTH\tcontrol\tthe 64 x 64 health triangle, exact",
    ]


def l_preds():
    rows = []
    for name, sset, models in L_ROWS:
        for m, (cls, cnt) in models.items():
            src = L_SRC_L1 if name.startswith("l1") else L_SRC[m]
            rows.append("\t".join([name, "class", cls, m, sset, src]))
            rows.append("\t".join([name, "count", cnt, m, sset, src]))
    return rows


def boot_word(timeout):
    return "timeout" if timeout else "up"


def d_preds():
    rows = []
    add = lambda *r: rows.append("\t".join(r))  # noqa: E731
    for name, (w, h), sset in D_CELLS:
        pg = fault_page(w, h)
        kept = {(640, 480): "E848 h2", (288, 144): "E848 h1/h4", (320, 400): "E789 a6", (256, 288): "E729", (384, 384): "E729"}
        src = "%s page 0x%05x" % (kept.get((w, h), "[infer] the fork's layout"), pg)
        add(name, "job_class", "fault", "H-JOB", "control", "E848: the held 4x job faults (rgn:1, E828)")
        add(name, "job_int", "0x00090004", "H-JOB", "control", "E789, E848: a TA write fault")
        add(name, "job_word", word(pg), "H-JOB", "control", src + "; list 1 after the job's own reset")
        page_t, size_t = pg in R_PAGE, (w, h) == (288, 144)
        if sset == "control":
            add(name, "boot_held", boot_word(page_t), "D-CTL", "control", "E901: 0x2000a 0 of 15, 0x20006 10 of 11 (both rules agree)")
        else:
            add(name, "boot_held", boot_word(page_t), "H-PAGE", "heldout", "E901 R-PAGE: 0x20006 to 0x20008 time out")
            add(name, "boot_held", boot_word(size_t), "H-SIZE", "heldout", "E892: the timeouts followed the 288 x 144 cells")
            add(name, "boot_replay1", boot_word(page_t), "H-PAGE", "heldout", "E901 R-PAGE: every first boot after such a fault")
        add(name, "passes_within", "3", "H-END", "control", "E848, E891: a draw within three triangles")
    return rows


def m_preds():
    rows = []
    add = lambda *r: rows.append("\t".join(r))  # noqa: E731
    pg = fault_page(288, 144)
    for name, man, sset in M_CELLS:
        add(name, "job_class", "fault", "H-JOB", "control", "E848: the held 4x job faults (rgn:1, E828)")
        add(name, "job_int", "0x00090004", "H-JOB", "control", "E789, E848: a TA write fault")
        add(name, "job_word", word(pg), "H-JOB", "control", "E848 h1/h4 page 0x20006; list 1 after the job's own reset")
        if man == "none":
            add(name, "boot_held", "timeout", "M-CTL", "control", "E901: 0x20006 10 of 11; 6 of 6 held resets of r6-held and E848")
        else:
            if man == "clr":
                add(name, "clr_hidden", "yes", "M-CLR", "control", "E826 f2: with the bit set the kernel read 0 and 0")
                add(name, "clr_back", "yes", "M-CLR", "control", "E826: clearing it returned the fault's words (4 of 4)")
            model = {"clr": "H-CLR", "long": "H-TIME"}[man]
            add(name, "boot_held", "up", model, "heldout", {"clr": "[infer] E826 f2 (cleared, up) vs E789 a6 (timed out)",
                                                              "long": "[infer] E826 f2 held 9.1 s, up"}[man])
            add(name, "boot_held", "timeout", "H-NULL", "heldout", "E901 R-PAGE: page 0x20006 times out")
        add(name, "passes_within", "3", "H-END", "control", "E848, E891: a draw within three triangles")
    return rows


# ---- what each control reads, and what each row's job can produce (scorekit.refuse_unreadable) ---------------------------------
def knobs_of(table_line):
    return set(table_line.split("|")[3].split())


def producible(line):
    """The reading keys the row's job can produce, from its knobs and command alone."""
    k = knobs_of(line)
    args = line.split("|")[5]
    if "gate" in k:
        return {"set_rc", "set_reads", "set_int", "back_reads"}
    if "probe" in k:
        return {"class", "count"}
    if "held" in k:
        keys = {"job_class", "job_int", "job_word", "boot_held", "boot_replay1", "passes_within", "dpm_hold"}
        if "clr" in k:
            keys |= {"clr_hidden", "clr_back"}
        return keys
    if args.startswith("tri ") or args == "fill":
        return {"class"}
    return set()


def controls(tables, preds):
    """{name: (keys, table line)}: one control per (case, model) of the control rows."""
    lines = {}
    for t in tables.values():
        for ln in t.splitlines():
            if ln and not ln.startswith("#"):
                lines[ln.split("|")[0]] = ln
    out = {}
    for p in preds.values():
        for ln in p.splitlines()[1:]:
            case, q, _v, model, sset, _s = ln.split("\t")
            if sset != "control":
                continue
            key = "%s:%s" % (case, model)
            keys, _ = out.get(key, ((), None))
            out[key] = (tuple(keys) + (q,), lines.get(case, "?|?|?||?|"))
    return out


def files():
    heads = {
        "s0": ["#stage s0", "#limit 0",
               "# s0: the premise controls: n0 flips CR_BIF_CTRL.CLEAR_FAULT through debugfs kregnow (0x0c00^=0x10, set then cleared)",
               "# with nothing held (taken, BIF_CTRL 0x10 then 0, BIF_INT_STAT idle: E826 n0), c1 the 64 x 64 health triangle."],
        "l": ["#stage l", "#limit 3",
              "# l: Q111, `lock #0` twice in a pixel program: E088's counter probe (a 64 x 32 fill, every instance adds 1 to scratch",
              "# dword 0), five programs (bins/, gen/asm_l.py).  A hang is a reading; the third hang with rows left stops the stage."],
        "d": ["#stage d", "#limit 21",
              "# d: Q003's fault-page dose: E848's held job (hold_recovery Y, render_rgn_arrays 1) at seven sizes, the debugfs reset",
              "# while held, then triangles until one draws (three at most).  A -110 is a reading; d0 (640 x 480) timing out stops d."],
        "m": ["#stage m", "#limit 18",
              "# m: Q003's manipulations at 288 x 144 before the held reset: none, CLEAR_FAULT set then cleared (kregnow), a 9 s hold;",
              "# order M0 M1 M2 M2 M1 M0."],
    }
    tables = {"s0": "\n".join(heads["s0"] + S0_ROWS) + "\n", "l": "\n".join(heads["l"] + l_rows()) + "\n",
              "d": "\n".join(heads["d"] + d_rows()) + "\n", "m": "\n".join(heads["m"] + m_rows()) + "\n"}
    preds = {"s0": "\n".join([HEADER] + s0_preds()) + "\n", "l": "\n".join([HEADER] + l_preds()) + "\n",
             "d": "\n".join([HEADER] + d_preds()) + "\n", "m": "\n".join([HEADER] + m_preds()) + "\n"}
    scorekit.refuse_unreadable(controls(tables, preds), producible)
    out = {}
    for st in ("s0", "l", "d", "m"):
        out["tables/%s.txt" % st] = tables[st]
        out["predictions/%s.tsv" % st] = preds[st]
    # stage alarms (seconds, the driver's bound of one stage's ssh): s0 a minute of work; l five fills and up to three hang
    # recoveries; d seven cells, m six, each at most 2 x 60 s of held job and waits, three steps, health (r6-held: 2400 for six)
    out["stages.txt"] = "s0 600\nl 1200\nd 2800\nm 2600\n"
    out["gen/data/sources.lst"] = "\n".join(sorted([
        E848 + "/cases.tsv",
        R6H + "/cases.tsv",
        E826 + "/n0-idle.dmesg.gz",
        E826 + "/f2-ta-write.dmesg.gz",
        E088 + "/raw.txt",
        E088 + "/bins/usse-quad-lock-counter__1.bin",
        E088 + "/bins/usse-quad-lock-counter__3.bin",
    ])) + "\n"
    out["TABLES.md"] = tables_md()
    return out


def tables_md():
    L = ["# r7-faults tables (written by gen/fgen.py; do not edit)", "",
         "Order: s0, l, d, m (one driver call; `run/f.sh`).  Rows by model: predictions/*.tsv (case, quantity, value, model, set,",
         "source).", "", "## l: `lock #0` twice (E088's counter probe; count = quads that added)", "",
         "| row | program | set | H-SELF | H-REFLAG | H-RECOUNT |", "|---|---|---|---|---|---|"]
    progs = {"l0": "lock #0, add, release #0", "l1": "lock #0, lock #1, add, release #1, release #0",
             "l2": "lock #0, lock #0, add, release #0, release #0", "l3": "lock #0, lock #0, add, release #0", "l4": "lock #0, add"}
    for name, sset, models in L_ROWS:
        g = lambda m: "%s %s" % models.get(m, models.get("L-CTL", models.get("L-REP")))  # noqa: E731
        L.append("| %s | %s | %s | %s | %s | %s |" % (name, progs[name[:2]], sset, g("H-SELF"), g("H-REFLAG"), g("H-RECOUNT")))
    L += ["", "## d: the fault-page dose (E848's held job, one array; the boot after the held reset)", "",
          "| cell | size | fault page (layout) | set | H-PAGE (E901 R-PAGE) | H-SIZE (E892 literal) |", "|---|---|---|---|---|---|"]
    for name, (w, h), sset in D_CELLS:
        pg = fault_page(w, h)
        L.append("| %s | %d x %d | 0x%05x | %s | %s | %s |" % (name, w, h, pg, sset, boot_word(pg in R_PAGE),
                                                            boot_word((w, h) == (288, 144))))
    L += ["", "## m: manipulations at 288 x 144 (page 0x20006)", "", "| cell | before the reset | set | prediction |", "|---|---|---|---|"]
    for name, man, sset in M_CELLS:
        what = {"none": "nothing", "clr": "kregnow 0x0c00^=0x10 twice (CLEAR_FAULT set, cleared)", "long": "a 9 s hold"}[man]
        pred = {"none": "timeout (control)", "clr": "H-CLR up / H-NULL timeout", "long": "H-TIME up / H-NULL timeout"}[man]
        L.append("| %s | %s | %s | %s |" % (name, what, sset, pred))
    L.append("")
    return "\n".join(L)


def main(argv):
    check = "--check" in argv
    bad = 0
    for rel, text in files().items():
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p).read() != text:
                print("differs: %s" % rel)
                bad = 1
            continue
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
    if not check:
        print("written: %s" % ", ".join(sorted(files())))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv))
