#!/usr/bin/env python3
"""test_replay.py: the frozen scorer replayed before the freeze on E848's kept stage-h files (resgx545-data
render/closing-r4-render4x out/20261111-211649/h, data e5cdaf0a), mapped to this session's cells, and on the files it must fail on.

  holds:  E848 h2 (640 x 480, two replays) read as a0: every a0 control PASS (the job's word 0x2000a061, the first triangle's fault at
          0x2000a061, a draw within three), the replay control open;  E848 h4 (288 x 144, fill) read as a2: H-FILL PASS, H-LIST held
          (0x20006062), H-WORD FAILED; the verdict's list headline names H-LIST's row as decided.
  fails:  E848 h4 read as a1 (a 640 x 480 cell): the H-JOB word control FAILS (page 0x20006, not 0x2000a) and closes the cell's
          rows;  E848 h1 (288 x 144, no flush) read as b2: raw H-FLUSH FAILED, raw H-PEND held, raw H-BOOT FAILED (the -110 after
          its held reset), and with no flush file the H-KEEP controls are NODATA, so every K2 row is cannot tell after the gate;
          E848 h3 (the ctx follow-up, no triangle fault) read as a0: the replay control FAILS;  an s0 whose gate row was taken
          (not refused) closes every row.
Exit 0 if every check holds.
"""
import os
import sys
import tempfile

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "tests"))
os.environ["SCORE_NOFREEZE"] = "1"
import score_h as S  # noqa: E402
import worlds as Wd  # noqa: E402

fails = 0


def check(cond, msg):
    global fails
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        fails += 1


def rows_of(root, maps, s0kw=None):
    q = Wd.e848(os.path.join(root, "q"), maps)
    s0 = Wd.s0_world(os.path.join(root, "s0"), **(s0kw or {}))
    ctl, _ = S.s0_controls(s0)
    rows, got, cctl, rep = S.q_rows(q, ctl)
    return rows, got, rep, q


def find(rows, case, q, model):
    r = [x for x in rows if x["case"] == case and x["q"] == q and x["model"] == model]
    assert len(r) == 1, (case, q, model, len(r))
    return r[0]


with tempfile.TemporaryDirectory(dir=os.path.join(KP, "debug")) as T:
    # holds
    rows, got, rep, q = rows_of(os.path.join(T, "h"), {"h2-640x480-health": "a0-640-health", "h4-288x144-fill": "a2-288-fill"})
    a0 = [x for x in rows if x["case"] == "a0-640-health" and x["set"] == "control"]
    check(a0 and all(x["raw"] is True for x in a0), "E848 h2 as a0: every a0 control PASS (%s)" % ", ".join("%s=%s" % (x["q"], x["got"]) for x in a0))
    check(rep == {"a0:replay": "PASS"}, "  a0's replay control open: %s" % rep)
    check(got["a0-640-health"][0]["replays"] == 2, "  two replays read (E848: h2 twice)")
    x = find(rows, "a2-288-fill", "first_word", "H-LIST")
    check(x["state"] is True and x["got"] == "0x20006062", "E848 h4 as a2: H-LIST held (%s)" % x["got"])
    x = find(rows, "a2-288-fill", "first_word", "H-WORD")
    check(x["state"] is False, "  H-WORD FAILED (the list is 2, not the job's 1)")
    x = find(rows, "a2-288-fill", "fill_class", "H-FILL")
    check(x["raw"] is True, "  H-FILL PASS (the fill drew)")
    s = S.q_stage(q, [T + "/h"])[1]["summary"]
    check(any("Q003 list (q): H-LIST" in l and "rows decided" in l for l in s), "  the list headline decides: %s" % [l for l in s if "list" in l])
    # must fail
    rows, got, rep, q = rows_of(os.path.join(T, "f1"), {"h4-288x144-fill": "a1-640-fill"})
    x = find(rows, "a1-640-fill", "job_word", "H-JOB")
    check(x["raw"] is False, "E848 h4 as a1 (640 x 480): the job-word control FAILS (%s, frozen %s)" % (x["got"], x["want"]))
    check(all(y["state"] is None for y in rows if y["case"] == "a1-640-fill" and y["set"] != "control"),
          "  and every heldout row of a1 is cannot tell (the cell's gate is shut)")
    rows, got, rep, q = rows_of(os.path.join(T, "f2"), {"h1-288x144-health": "b2-288-flush-health", "h3-288x144-ctx": "a0-640-health"})
    b = lambda qq, m: find(rows, "b2-288-flush-health", qq, m)  # noqa: E731
    check(b("first_tri", "H-FLUSH")["raw"] is False and b("first_tri", "H-PEND")["raw"] is True,
          "E848 h1 as b2 (no flush): raw H-FLUSH FAILED, raw H-PEND held")
    check(b("minus110_reset", "H-BOOT")["raw"] is False, "  raw H-BOOT FAILED (E848 h1's held reset was followed by a -110)")
    check(b("flush_rc", "H-KEEP")["raw"] is None and all(y["state"] is None for y in rows if y["model"] in ("H-FLUSH", "H-PEND", "H-BOOT", "H-LATCH")),
          "  no flush file: H-KEEP NODATA, every K2 row cannot tell after the gate")
    check(rep == {"a0:replay": "FAIL"}, "E848 h3 (a ctx follow-up, no triangle fault) as a0: the replay control FAILS (%s)" % rep)
    rows, got, rep, q = rows_of(os.path.join(T, "f3"), {"h4-288x144-fill": "a2-288-fill"}, {"refused": False})
    check(all(y["state"] is None for y in rows if y["set"] != "control"), "an s0 whose bif_flush gate row was taken: every row cannot tell")
    s = S.q_stage(q, [T + "/f3"])[1]["summary"]
    check(any("controls FAILED" in l for l in s if "list" in l), "  the list headline names the FAILED s0 control")
    ctl, _ = S.s0_controls(Wd.s0_world(os.path.join(T, "f4"), peek="reg 0x0690 0x00000000"))
    check(ctl["n0-gate:peek_format"] == "FAIL", "s0: a peek line for another offset FAILS the peek control")

print("replay checks: %s" % ("PASS" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
