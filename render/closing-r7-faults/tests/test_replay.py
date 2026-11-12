#!/usr/bin/env python3
"""test_replay.py: the frozen scorer replayed before the freeze on kept files it must hold on and on files it must fail on (the
round 7 rule), mapped to this session's rows by tests/worlds.py (r6held, e826, e088):

  holds:  E826's n0-idle as s0's gate row (+ its health triangle as c1): the five s0 controls PASS, the premise passes;
          E088's case 1 (lock #0 / release #0) as l0: the L-CTL control PASS (ok, 512); its case 3 (no release) as l4: L-REP held
          (hang, 1);  r6-held a0 (640 x 480) as d0 and a2 (288 x 144) as d1: every D-CTL and H-JOB control PASS (up, timeout);
          r6-held b2 (288 x 144) as d3 (256 x 288, the same page): H-PAGE's boot_held held, H-SIZE FAILED, and H-PAGE's
          boot_replay1 FAILED (b2's first replay came up: E901's one r6-held miss, scored as it falls);  r6-held a2 as m0a: M-CTL PASS;
          b2 as m2a: H-NULL held, H-TIME FAILED;  E826's f2 (CLEAR_FAULT set and cleared while held) as m1a: both M-CLR controls PASS.
  fails:  r6-held a2 as d0: the job-word and the D-CTL controls FAIL, every d held-out row cannot tell;  a0 as d1: D-CTL FAILS;
          E826 f2 as m1a: its job-word control FAILS (page 0x20008, not 0x20006) and its H-CLR row is cannot tell;  E088's case 0 (no
          lock) as l0: count 44, L-CTL FAILS, every l row cannot tell;  case 3 as l0: hang, FAILS;  an s0 whose kregnow set was
          refused: set_rc FAILS, every gate closed;  an s0 with no kregnow line: the premise STOPS (no reading of set_reads).
Exit 0 if every check holds.
"""
import gzip
import os
import sys
import tempfile

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "tests"))
os.environ["SCORE_NOFREEZE"] = "1"
import score_f as S  # noqa: E402
import worlds as Wd  # noqa: E402

fails = 0


def check(cond, msg):
    global fails
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        fails += 1


def find(rows, case, q, model):
    r = [x for x in rows if x["case"] == case and x["q"] == q and x["model"] == model]
    assert len(r) == 1, (case, q, model, len(r))
    return r[0]


def merge(dst, *srcs):
    """one stage directory from several fixtures (their cases.tsv rows joined)."""
    os.makedirs(dst, exist_ok=True)
    rows = [Wd.COLS]
    for s in srcs:
        for n in os.listdir(s):
            if n != "cases.tsv":
                os.replace(os.path.join(s, n), os.path.join(dst, n))
        rows += open(os.path.join(s, "cases.tsv")).read().splitlines()[1:]
    open(os.path.join(dst, "cases.tsv"), "w").write("\n".join(rows) + "\n")
    return dst


with tempfile.TemporaryDirectory(dir=os.path.join(KP, "debug")) as T:
    # ---- holds --------------------------------------------------------------------------------------------------------------
    R = os.path.join(T, "h")
    s0 = Wd.e826(os.path.join(R, "s0"), {"n0-idle": "n0-clr-idle"}, "s0")
    ctl = S.s0_controls(s0)
    check(ctl and all(v == "PASS" for v in ctl.values()) and len(ctl) == 5, "E826 n0 as s0's gate row (+ c1): five controls PASS %s" % ctl)
    check(S.premise("s0", s0) == [], "  the premise of s0 passes")
    l = Wd.e088(os.path.join(R, "l"), {"usse-quad-lock-counter__1": "l0-lock-release", "usse-quad-lock-counter__3": "l4-lock-norel"})
    rows, _, _ = S.stage_rows("l", l, ctl)
    check(find(rows, "l0-lock-release", "count", "L-CTL")["raw"] is True and find(rows, "l0-lock-release", "class", "L-CTL")["raw"] is True,
          "E088 case 1 as l0: L-CTL PASS (ok, %s)" % find(rows, "l0-lock-release", "count", "L-CTL")["got"])
    x = find(rows, "l4-lock-norel", "count", "L-REP")
    check(x["state"] is True and x["got"] == "1" and find(rows, "l4-lock-norel", "class", "L-REP")["state"] is True,
          "E088 case 3 as l4: L-REP held (hang, %s), gated by l0 alone (l1 not run)" % x["got"])
    d = Wd.r6held(os.path.join(R, "d"), {"a0-640-health": "d0-640x480", "a2-288-fill": "d1-288x144", "b2-288-flush-health": "d3-256x288"})
    rows, got, _ = S.stage_rows("d", d, ctl)
    c = [x for x in rows if x["case"] in ("d0-640x480", "d1-288x144") and x["set"] == "control"]
    check(c and all(x["raw"] is True for x in c), "r6-held a0 as d0, a2 as d1: every d0/d1 control PASS (%s)" % ", ".join(
        "%s:%s=%s" % (x["case"][:2], x["q"], x["got"]) for x in c))
    check(find(rows, "d3-256x288", "boot_held", "H-PAGE")["state"] is True and find(rows, "d3-256x288", "boot_held", "H-SIZE")["state"] is False,
          "r6-held b2 as d3: H-PAGE's boot_held held (timeout), H-SIZE FAILED")
    x = find(rows, "d3-256x288", "boot_replay1", "H-PAGE")
    check(x["state"] is False and x["got"] == "up", "  H-PAGE's boot_replay1 FAILED (b2's first replay came up: E901's r6-held miss, as it falls)")
    s = S.stage_score("d", d, [R])[1]["summary"]
    check(any(l.startswith("Q003 page (d): H-PAGE") and "is not supported" in l for l in s), "  the page headline says H-PAGE is not supported (1 FAILED): %s" % [l for l in s if "page" in l])
    m = merge(os.path.join(R, "m"), Wd.r6held(os.path.join(T, "m1"), {"a2-288-fill": "m0a-none", "b2-288-flush-health": "m2a-long"}, "m"),
              Wd.e826(os.path.join(T, "m2"), {"f2-ta-write": "m1a-clr"}, "m"))
    rows, got, _ = S.stage_rows("m", m, ctl)
    check(find(rows, "m0a-none", "boot_held", "M-CTL")["raw"] is True, "r6-held a2 as m0a: M-CTL PASS (timeout)")
    check(find(rows, "m2a-long", "boot_held", "H-NULL")["state"] is True and find(rows, "m2a-long", "boot_held", "H-TIME")["state"] is False,
          "r6-held b2 as m2a: H-NULL held, H-TIME FAILED")
    check(find(rows, "m1a-clr", "clr_hidden", "M-CLR")["raw"] is True and find(rows, "m1a-clr", "clr_back", "M-CLR")["raw"] is True,
          "E826 f2 as m1a: both M-CLR controls PASS (hidden 0/0, back 0x90004/0x20008061)")
    # ---- must fail ----------------------------------------------------------------------------------------------------------
    x = find(rows, "m1a-clr", "job_word", "H-JOB")
    check(x["raw"] is False and find(rows, "m1a-clr", "boot_held", "H-CLR")["state"] is None,
          "E826 f2 as m1a: the job-word control FAILS (%s, frozen %s) and its H-CLR row is cannot tell" % (x["got"], x["want"]))
    F = os.path.join(T, "f")
    d = Wd.r6held(os.path.join(F, "d"), {"a2-288-fill": "d0-640x480", "a0-640-health": "d1-288x144", "b2-288-flush-health": "d3-256x288"})
    rows, _, _ = S.stage_rows("d", d, ctl)
    check(find(rows, "d0-640x480", "job_word", "H-JOB")["raw"] is False and find(rows, "d0-640x480", "boot_held", "D-CTL")["raw"] is False,
          "r6-held a2 as d0: the job-word and D-CTL controls FAIL")
    check(find(rows, "d1-288x144", "boot_held", "D-CTL")["raw"] is False, "r6-held a0 as d1: D-CTL FAILS (up, frozen timeout)")
    check(all(x["state"] is None for x in rows if x["set"] != "control"), "  and every d held-out row is cannot tell")
    s = S.stage_score("d", d, [R])[1]["summary"]
    check(any(l.startswith("Q003 page (d): controls FAILED") for l in s), "  the page headline names the FAILED controls")
    l = Wd.e088(os.path.join(F, "l"), {"usse-quad-lock-counter__0": "l0-lock-release", "usse-quad-lock-counter__3": "l4-lock-norel"})
    rows, _, _ = S.stage_rows("l", l, ctl)
    x = find(rows, "l0-lock-release", "count", "L-CTL")
    check(x["raw"] is False and x["got"] == "44" and find(rows, "l4-lock-norel", "count", "L-REP")["state"] is None,
          "E088 case 0 (no lock) as l0: count %s, L-CTL FAILS, l4 cannot tell" % x["got"])
    l = Wd.e088(os.path.join(F, "l2"), {"usse-quad-lock-counter__3": "l0-lock-release"})
    rows, _, _ = S.stage_rows("l", l, ctl)
    check(find(rows, "l0-lock-release", "class", "L-CTL")["raw"] is False, "E088 case 3 (the hang) as l0: the class control FAILS")
    s0b = Wd.e826(os.path.join(F, "s0"), {"n0-idle": "n0-clr-idle"}, "s0")
    gzip.open(os.path.join(s0b, "n0-clr-idle.txt.gz"), "wt").write("set rc 1\nclear rc 1\n")
    c2 = S.s0_controls(s0b)
    check(c2["n0-clr-idle:set_rc"] == "FAIL" and S.gate("l", [F])[0] == 1, "an s0 whose kregnow set was refused: set_rc FAILS, the gate of l is closed")
    rows, _, _ = S.stage_rows("d", Wd.r6held(os.path.join(F, "d2"), {"a2-288-fill": "d1-288x144"}), c2)
    check(all(x["state"] is None for x in rows if x["set"] != "control"), "  and every d row is cannot tell")
    s0c = Wd.e826(os.path.join(F, "s0c"), {"n0-idle": "n0-clr-idle"}, "s0")
    gzip.open(os.path.join(s0c, "n0-clr-idle.dmesg.gz"), "wt").write("")
    stops = S.premise("s0", s0c)
    check(any("n0-clr-idle:GATE has no reading of set_reads" in x for x in stops), "an s0 with no kregnow line: the premise STOPS (%s)" % stops[:1])

print("replay checks: %s" % ("PASS" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
