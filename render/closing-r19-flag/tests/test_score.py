# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer on kept directories built in a tmp directory from the
frozen predictions (the control's readings as the runner's hook_reading writes them): it holds
each of the four models on its own outcome and fails on the others, shuts on a failed or absent
control, and says "no model" on a mixed pair (a fit row and its held-out replicate that disagree)."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402

COLS = K.COLUMNS
BIF = "[1.0] sgxfive: BIF fault 0x90200 at 0x30011a40 (PD 0x1) stalls job 7, recovering\n"
HUNG = "[1.0] sgxfive: job 12 hung, recovering\n"
CTL = {"job": "ok", "ovf": "1", "thr": "0xde", "lists": "yes"}


def out(h, diff=0):
    return f"job: ok\ntarget: 1024x768 hash {h}\ndiff: {diff} of 786432 pixels\n"


def kept(root, ends, ctl=None, ctl_hash="0x00000000000000aa", hashes=None, dm=None, reading=True):
    """ends: {row: ok|fault|hang} for the junk rows; the control always ok unless ctl_end given."""
    d = os.path.join(root, "fl")
    os.makedirs(d, exist_ok=True)
    tab = {r["name"]: r for r in K.table(KP, "fl")}
    rows = {"fl-ctl": "ok", **ends}
    with open(os.path.join(d, "cases.tsv"), "w") as f:
        f.write("\t".join(COLS) + "\n")
        for n, cls in rows.items():
            r = tab[n]
            rc = 1 if cls != "ok" or "expectdiff" in r["knobs"] else 0
            f.write("\t".join([n, "fl", r["set"], r["risk"], " ".join(r["knobs"]), r["tool"], r["args"], str(rc),
                               cls, "-", "-", "1000"]) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(COLS) + "\n")
    rd = CTL if ctl is None else ctl
    with open(os.path.join(d, "readings.tsv"), "w") as f:
        f.write("name\treads\treading\n")
        if reading:
            f.write("fl-ctl\t-\t" + " ".join(f"{k}={v}" for k, v in rd.items()) + "\n")
    for n, cls in rows.items():
        h = (hashes or {}).get(n, ctl_hash)
        text = out(h, 0 if h == ctl_hash else 1000) if cls == "ok" else "job: failed: x\n"
        open(os.path.join(d, n + ".txt"), "w").write(text)
        k = {"fault": BIF, "hang": HUNG}.get(cls, "") if n != "fl-ctl" else ""
        open(os.path.join(d, n + ".dmesg"), "w").write((dm or {}).get(n, k))
    return d


def run(tmp, name, *a, **k):
    d = kept(str(tmp / name), *a, **k)
    controls, models, lines = score.verdicts("fl", d)
    return controls, models, lines, score.summary(controls, models)


def test_each_model_holds_on_its_own_outcome_and_only_there(tmp_path):
    both = lambda e: {"fl-junk-a": e, "fl-junk-b": e}  # noqa: E731
    cases = {"H-NOLOAD": (both("ok"), None), "H-LOAD-FAULT": (both("fault"), None),
             "H-LOAD-HANG": (both("hang"), None),
             "H-LOAD-CORRUPT": (both("ok"), {"fl-junk-a": "0x00000000000000bb", "fl-junk-b": "0x00000000000000bb"})}
    for model, (ends, hashes) in cases.items():
        ctl, models, _, summ = run(tmp_path, model, ends, hashes=hashes)
        assert ctl == {"fl-ctl": True}
        held = [m for m, ss in models.items() if all(s is True for s in ss)]
        assert held == [model], (model, models)
        assert summ.startswith(model + ":") and "(2 of 2 rows decided)" in summ, summ


def test_failed_control_shuts_the_headline(tmp_path):
    bad = dict(CTL, thr="0x6")                       # H-IGN: the update did not happen
    ctl, _, lines, summ = run(tmp_path, "thr", {"fl-junk-a": "ok", "fl-junk-b": "ok"}, ctl=bad)
    assert ctl == {"fl-ctl": False} and "FAILED" in lines[0] and "controls FAILED" in summ


def test_absent_reading_cannot_tell_and_premise_stops(tmp_path):
    d = kept(str(tmp_path / "nr"), {}, reading=False)
    ctl, models, _ = score.verdicts("fl", d)
    assert ctl == {"fl-ctl": None}
    assert K.premise(KP, "fl", d) and "STOP" in K.premise(KP, "fl", d)[0]
    assert not K.premise(KP, "fl", kept(str(tmp_path / "r"), {}))


def test_mixed_pair_is_no_model(tmp_path):
    _, models, _, summ = run(tmp_path, "mixed", {"fl-junk-a": "ok", "fl-junk-b": "fault"})
    assert "no frozen model holds on both" in summ
    assert models["H-NOLOAD"] == [True, False]


def test_a_junk_row_that_did_not_end_ok_fault_or_hang_cannot_tell(tmp_path):
    d = kept(str(tmp_path / "f"), {"fl-junk-a": "ok", "fl-junk-b": "ok"})
    # a junk row of class fail (the runner stops, but the kept record may still be scored)
    cases = open(os.path.join(d, "cases.tsv")).read().replace("\tok\t-\t-\t1000", "\tfail\t-\t-\t1000")
    open(os.path.join(d, "cases.tsv"), "w").write(cases)
    controls, models, _ = score.verdicts("fl", d)
    assert controls == {"fl-ctl": None}              # the control did not complete either
