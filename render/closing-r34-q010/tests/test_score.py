# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer replayed on kept records it must hold on and must fail on.
Kept attempts are built in a tmp directory from the published r29-flag2 copies (E1112, read at the
frozen data commit): q010-pre and q010-ld2 (E037's BT.601 hash: KEPT) and q010-af and q010-p1 (black
after the health pair and after a recovered hang: CLEARED), placed on this session's rows as each
hypothesis says; the controls' readings as the runner's hook_reading writes them."""
import gzip
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
DATA = "/Users/jtorra/src/resgx545-data"
H1 = "render/closing-r29-flag2/out/20261116-073242/h1"
COLS = K.COLUMNS


def gtext(path):
    b = subprocess.run(["git", "-C", DATA, "show", f"{CFG['freeze']['data']}:{path}"], check=True,
                       capture_output=True).stdout
    return gzip.decompress(b).decode()


TEXT = {"KEPT": gtext(f"{H1}/q010-pre.txt.gz"), "CLEARED": gtext(f"{H1}/q010-af.txt.gz"),
        "LOAD": gtext(f"{H1}/q010-ld2.txt.gz"), "CLEARED2": gtext(f"{H1}/q010-p1.txt.gz")}
P = K.predictions(KP, "c")
T = K.table(KP, "c")


def attempt(root, pattern, change=None, drop=(), other=None, cleared_text="CLEARED"):
    """pattern: {held-out row: KEPT/CLEARED}; the controls read their frozen values unless
    change = (row, hash); drop: rows that did not run; other: a row whose text has another hash."""
    d = os.path.join(root, "c")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cases.tsv"), "w") as f, open(os.path.join(d, "readings.tsv"), "w") as g:
        f.write("\t".join(COLS) + "\n")
        g.write("name\treads\treading\n")
        for r in T:
            n = r["name"]
            if n in drop:
                continue
            rc = 1 if "expectdiff" in r["knobs"] and r["tool"] == "t30" and r["set"] != "between" else 0
            f.write("\t".join([n, "c", r["set"], r["risk"], " ".join(r["knobs"]), r["tool"], r["args"],
                               str(rc), "ok", "-", "-", "1000"]) + "\n")
            if r["set"] == "control":
                h = P[n]["hash"]["H-REF"]
                if change and change[0] == n:
                    h = change[1]
                g.write(f"{n}\tjob,hash\tjob=ok hash={h}\n")
                txt = TEXT["KEPT"] if h == score.KEPT_HASH else TEXT["CLEARED"]
            elif r["set"] == "heldout":
                txt = TEXT[pattern[n] if pattern[n] == "KEPT" else cleared_text]
                if other == n:
                    txt = txt.replace(score.CLEARED_HASH, "0x0123456789abcdef").replace(score.KEPT_HASH, "0x0123456789abcdef")
            else:
                txt = "job: ok\n"
            open(os.path.join(d, n + ".txt"), "w").write(txt)
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(COLS) + "\n")
    return root


def pattern_of(model):
    out = {}
    for r in T:
        if r["set"] == "heldout":
            out[r["name"]] = score.WORD[P[r["name"]]["hash"][model]]
    return out


def rule(root):
    _, per, ctl = score.score(os.path.join(root, "c"))
    return score.rule(per, ctl)


def test_kept_texts_read_as_frozen():
    for k, want in (("KEPT", score.KEPT_HASH), ("LOAD", score.KEPT_HASH), ("CLEARED", score.CLEARED_HASH),
                    ("CLEARED2", score.CLEARED_HASH)):
        assert f"hash {want}" in TEXT[k], k


def test_each_job_hypothesis_retires_on_its_own_pattern(tmp_path):
    for m in score.JOBS:
        for ct in ("CLEARED", "CLEARED2"):             # after the health pair, or after a recovered hang
            root = attempt(str(tmp_path / f"{m}{ct}"), pattern_of(m), cleared_text=ct)
            out = rule(root)
            assert out[0].endswith(f"one job hypothesis, {m}: RETIRE-CAPABLE"), out
            lines, per, _ = score.score(os.path.join(root, "c"))
            assert all(v is True for v in per[m].values()) and len(per[m]) == 9
            for o in score.FULL:
                if o != m:
                    assert any(v is False for v in per[o].values()), o
            assert any(ln.startswith(f"SUMMARY: c: {m}: ") and "(9 of 9 rows decided)" in ln for ln in lines)


def test_none_and_side_hypotheses_narrow(tmp_path):
    out = rule(attempt(str(tmp_path / "n"), pattern_of("H-NONE")))
    assert out[0].endswith("narrow only (the stage boundary itself, or a longer idle [infer])")
    pat = pattern_of("H-FILL")
    pat.update({"t4-rd": "CLEARED", "t5-rd": "CLEARED"})                   # H-IDLE
    out = rule(attempt(str(tmp_path / "i"), pat))
    assert "H-IDLE 2 held" in out[0] and out[0].endswith("no single job hypothesis holds on every row: narrow only")
    pat = pattern_of("H-TRI")
    pat.update({"t3a-rd": "CLEARED", "t3b-rd": "CLEARED"})                 # H-COPYNL
    out = rule(attempt(str(tmp_path / "c"), pat))
    assert "H-COPYNL 2 held" in out[0] and out[0].endswith("narrow only")


def test_replicates_that_disagree_narrow(tmp_path):
    pat = pattern_of("H-FILL")
    pat["t1b-rd"] = "KEPT"
    out = rule(attempt(str(tmp_path / "r"), pat))
    assert out[0].endswith("no single job hypothesis holds on every row: narrow only")


def test_a_failed_control_makes_every_row_cannot_tell(tmp_path):
    # the module's debugfs reset clears the set (T0's R reads black): the reading the rule rests on
    root = attempt(str(tmp_path / "t0"), pattern_of("H-FILL"), change=("t0b-rd", score.CLEARED_HASH))
    out = rule(root)
    assert "controls 14 of 15 passed" in out[0] and out[0].endswith("a control did not pass: narrow only")
    _, per, _ = score.score(os.path.join(root, "c"))
    assert all(v is None for v in per["H-FILL"].values())
    # one triple's L failing gates its own R only
    root = attempt(str(tmp_path / "l"), pattern_of("H-FILL"), change=("t2a-ld", score.CLEARED_HASH))
    _, per, ctl = score.score(os.path.join(root, "c"))
    assert per["H-FILL"]["t2a-rd"] is None and per["H-FILL"]["t2b-rd"] is True
    assert rule(root)[0].endswith("a control did not pass: narrow only")


def test_missing_or_other_readings_do_not_decide(tmp_path):
    out = rule(attempt(str(tmp_path / "d"), pattern_of("H-TRI"), drop=("t5-rd",)))
    assert "decided 8 of 9" in out[0] and out[0].endswith("a held-out row is not decided: narrow only")
    root = attempt(str(tmp_path / "o"), pattern_of("H-TRI"), other="t6-rd")
    _, per, _ = score.score(os.path.join(root, "c"))
    assert per["H-TRI"]["t6-rd"] is None
    assert rule(root)[0].endswith("a held-out row is not decided: narrow only")
    out = rule(attempt(str(tmp_path / "z"), pattern_of("H-TRI"), drop=("z0-rd",)))
    assert out[0].endswith("a control did not pass: narrow only")


def test_premise_stops_on_a_control_without_its_hash(tmp_path):
    root = attempt(str(tmp_path / "p"), pattern_of("H-FILL"))
    d = os.path.join(root, "c")
    assert score.main(["score.py", "premise", "c", d]) == 0
    t = open(os.path.join(d, "readings.tsv")).read().replace("t3a-ld\tjob,hash\tjob=ok hash=" + score.KEPT_HASH,
                                                             "t3a-ld\tjob,hash\tjob=ok")
    open(os.path.join(d, "readings.tsv"), "w").write(t)
    assert score.main(["score.py", "premise", "c", d]) == 1
