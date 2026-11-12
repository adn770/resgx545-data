#!/usr/bin/env python3
"""hgen.py: r6-held part H (Q003's replay clause on the new kernel), the one source of the tables, the predictions, TABLES.md,
stages.txt and gen/data/sources.lst.  Written and run before the freeze; tests/test_gen.py checks that the files are what this makes.

  PY gen/hgen.py            write the files
  PY gen/hgen.py --check    exit 1 if any file differs from what it would write (nothing written)

Plan: rank-round6.md section 1 R6-5 and section 2 session B, DECISIONS-R6.md R6-4 (a), R6-5 (a).  Base: round 4's stage h
(closing4/r4-render4x, E848) and round 6's runner (closing6/r6-render4x).  Records: E848 (the replay; h4's list 2), E826 (BIF_INT_STAT
writes and BIF_CTRL bit 4), E767 (the halt), E789 (the TA write fault word), E828 (rgn:1 forces the fault), E360 (BIF_FAULT bits 3:0
name the directory list).

Hypotheses (frozen in predictions/q.tsv; [infer] where ours):
  H-LIST  [infer, E848 h4 post hoc]: the replayed TA write goes through the directory list current when the TA next runs: its BIF_FAULT
          word is the failed job's page and SB 6 with the list the next TA job's context holds (1 when the first job after the reset
          is a triangle, 2 when a fill took list 1 first, as in h4).
  H-WORD  (E848's frozen word test): the replay reads the failed job's whole word, its list (1) included.
  H-PEND  : the replay happens with the flush as without it (the BIF invalidate between the hold and the reset changes nothing).
  H-FLUSH [infer]: the pending write lives in the BIF's caches; the invalidate (debugfs bif_flush, fork 3f0b3e74) drops it, so after a
          flushed cell the first triangle passes (no replay).
  H-BOOT  [infer, E848's -110 dumps: a TA write fault inside the boot]: with the flush no "SGX recovery failed: -110" follows the held
          reset.
  H-KEEP  (the fork's code, sgx_seq_bif_flush: INVALDC set, cleared, the other bits kept): the kernel's bif_flush line reads BIF_CTRL
          the same before and after.  A control of the flush.
  H-LATCH (E826: a held fault stays latched until the reset): right after the flush BIF_INT_STAT still reads 0x90004 and BIF_FAULT the
          job's word.
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = "/Users/jtorra/src/resgx545-data"
E848 = DATA + "/render/closing-r4-render4x/out/20261111-211649/h"

POKES = "--poke cmd:1=0xe0000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26"


def job(w, h):
    """E848's cell job byte for byte: the 4x full triangle with E824's words, without --aa4 (a 1x context: the new kernel's tail room
    leaves its layout as before, fork 56f8b932), on a context made for its own size, render_rgn_arrays forced to 1."""
    return ("tri --tri-full --keep-going --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d %s"
            % (w, h, w, h, POKES))


PAGE = {(640, 480): 0x2000a, (288, 144): 0x20006}     # E848 h2 and h1/h3/h4 (E507, E729, E828 j2)

# the cells, in run order (a and b alternate, so a stop leaves both kinds): name, size, follow-up, flush
CELLS = [
    ("a0-640-health", (640, 480), "health", False),
    ("b0-640-flush-health", (640, 480), "health", True),
    ("a1-640-fill", (640, 480), "fill", False),
    ("b1-640-flush-fill", (640, 480), "fill", True),
    ("a2-288-fill", (288, 144), "fill", False),
    ("b2-288-flush-health", (288, 144), "health", True),
]

S0_ROWS = [
    # name|set|risk|knobs|rt|args
    "n0-gate|control|safe|gate|-|-",
    "c1-tri|control|safe|expectdiff|-|tri --keep-going",
]


def q_rows():
    out = []
    for name, (w, h), follow, flush in CELLS:
        knobs = "held rgn:1 expectdiff hypo:q:6 cell:%s%s" % (follow, " flush" if flush else "")
        out.append("%s|heldout|risky|%s|-|%s" % (name, knobs, job(w, h)))
    return out


def word(page, cid):
    return "0x%08x" % ((page << 12) | 0x060 | cid)


def q_preds():
    """case quantity value model set source"""
    rows = []
    add = lambda *r: rows.append("\t".join(r))  # noqa: E731
    for name, size, follow, flush in CELLS:
        pg = PAGE[size]
        src = "E848 %s; E507/E729 page 0x%05x" % ("h2" if size == (640, 480) else "h1/h4", pg)
        add(name, "job_class", "fault", "H-JOB", "control", src)
        add(name, "job_int", "0x00090004", "H-JOB", "control", "E789, E848: a TA write fault")
        add(name, "job_word", word(pg, 1), "H-JOB", "control", src + "; list 1 after the job's own reset")
        cid_next = 2 if follow == "fill" else 1
        if follow == "fill":
            add(name, "fill_class", "ok", "H-FILL", "control", "E848 h4: the fill passed (a transfer: no TA)")
        if not flush:
            add(name, "first_tri", "fault", "H-REPLAY", "control" if name.startswith("a0") else "heldout",
                "E848: 4 of 4 faults replayed (h1, h2, h4; K2 E826 correction)")
            if follow == "health":
                # nothing ran between the reset and the triangle: both readings give list 1 (E848 h1, h2): the replay's control
                add(name, "first_word", word(pg, 1), "H-REPLAY", "control", "E848 h2: the job's word, a page never seen in health")
            else:
                add(name, "first_word", word(pg, cid_next), "H-LIST", "heldout" if name != "a2-288-fill" else "replicate",
                    "E848 h4 post hoc: the list current at the next TA run")
                add(name, "first_word", word(pg, 1), "H-WORD", "heldout" if name != "a2-288-fill" else "replicate",
                    "E848's frozen word test")
        else:
            add(name, "flush_rc", "0", "H-KEEP", "control", "fork 3f0b3e74: a recovery is held, so the write is taken")
            add(name, "flush_ctrl_same", "yes", "H-KEEP", "control", "fork 3f0b3e74 sgx_seq_bif_flush keeps the other bits")
            add(name, "flush_int", "0x00090004", "H-LATCH", "heldout", "E826: only the reset cleared a held fault")
            add(name, "flush_word", word(pg, 1), "H-LATCH", "heldout", "E826: only the reset cleared a held fault")
            add(name, "first_tri", "ok", "H-FLUSH", "heldout", "[infer] the invalidate drops the pending write")
            add(name, "first_tri", "fault", "H-PEND", "heldout", "the replay as without the flush (E848)")
            add(name, "first_word", word(pg, cid_next), "H-PEND", "heldout", "H-PEND with H-LIST's list")
            add(name, "minus110_reset", "0", "H-BOOT", "heldout", "[infer] E848's -110 dumps: a TA write fault in the boot")
        add(name, "passes_within", "3", "H-END", "control", "E848: the third triangle at the latest passed (h2)")
    return rows


S0_PREDS = [
    "n0-gate\tflush_refused\tbusy\tK2-GATE\tcontrol\tfork 3f0b3e74: -EBUSY with nothing held",
    "n0-gate\tflush_ctrl_same\tyes\tK2-GATE\tcontrol\tfork 3f0b3e74: nothing written when refused (BIF_CTRL in the regs before and after)",
    "n0-gate\tpeek_format\treg 0x0694\tK1-PEEK\tcontrol\tfork db7faabc: 'reg 0x0694 0x%08x'",
    "c1-tri\tclass\tok\tHEALTH\tcontrol\tthe 64 x 64 health triangle, exact",
]

HEADER = "case\tquantity\tvalue\tmodel\tset\tsource"


def files():
    q_head = ["#stage q", "#limit 15",
              "# q: Q003's replay clause on the new kernel (module 41E2F5C7..., fork r6-kernel 3f0b3e74).  Each cell: E848's job held",
              "# (hold_recovery Y, render_rgn_arrays 1), the fault read, [flush: debugfs bif_flush 1 while held], the debugfs reset, the",
              "# follow-up (fill: one fill), then health triangles one by one until one draws, three at most.  Order a0 b0 a1 b1 a2 b2."]
    s0_head = ["#stage s0", "#limit 0",
               "# s0: the controls: n0 writes debugfs bif_flush 1 with nothing held (refused: -EBUSY; BIF_CTRL unchanged; peek read idle),",
               "# c1 the 64 x 64 health triangle.  No job faults here."]
    out = {
        "tables/s0.txt": "\n".join(s0_head + S0_ROWS) + "\n",
        "tables/q.txt": "\n".join(q_head + q_rows()) + "\n",
        "predictions/s0.tsv": "\n".join([HEADER] + S0_PREDS) + "\n",
        "predictions/q.tsv": "\n".join([HEADER] + q_preds()) + "\n",
        "stages.txt": "s0 600\nq 2400\n",
        "gen/data/sources.lst": "\n".join(sorted([
            E848 + "/cases.tsv",
            E848 + "/h2-640x480-health.h1.dmesg.gz",
            E848 + "/h4-288x144-fill.h1.dmesg.gz",
        ])) + "\n",
    }
    out["TABLES.md"] = tables_md()
    return out


def tables_md():
    lines = ["# r6-held part H tables (written by gen/hgen.py; do not edit)", "",
             "Stage s0 (controls) then stage q (6 cells).  Each q cell: E848's job held, the fault read at 2.8 s and 1 s later,",
             "[flush: `echo 1 > bif_flush` while held, the registers read], the debugfs reset, the follow-up, then triangles until one",
             "draws (three at most), then the health pair.", "",
             "| cell | size | follow-up | flush | job word | first triangle: H-LIST / H-WORD | H-FLUSH / H-PEND |",
             "|---|---|---|---|---|---|---|"]
    for name, size, follow, flush in CELLS:
        pg = PAGE[size]
        cid = 2 if follow == "fill" else 1
        if flush:
            a = "-"
            b = "ok / fault at %s" % word(pg, cid)
        else:
            a = ("fault at %s / %s" % (word(pg, cid), word(pg, 1))) if follow == "fill" else "fault at %s (both)" % word(pg, 1)
            b = "-"
        lines.append("| %s | %d x %d | %s | %s | %s | %s | %s |" % (name, size[0], size[1], follow, "yes" if flush else "no",
                                                                     word(pg, 1), a, b))
    lines += ["", "Rows by model: predictions/q.tsv and predictions/s0.tsv (case, quantity, value, model, set, source).", ""]
    return "\n".join(lines)


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
