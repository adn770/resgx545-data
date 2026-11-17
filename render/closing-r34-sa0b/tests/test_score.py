# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer replayed on kept records it must hold on and must fail on.
Kept: E496's usse-pa-dest table (published, read at the frozen data commit): its first job's pa0
mixture (`o0 mixed 0xff00ff00 x1536 0xff203040 x512`) and its jobs 7 and 8 (the sa0 writer whose
colour was its marker, 0x79, and the reader that read 0x79). Attempts are built in a tmp directory
in t30's own probe format (E496's lines are that format), the controls' readings as the runner's
hook_reading writes them; the t10 rows' texts are r34-q010's kept health pair (mock/kept)."""
import os
import re
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
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
RAW = subprocess.run(["git", "-C", DATA, "show",
                      f"{CFG['freeze']['data']}:usse/pa-dest/usse-pa-dest-persist/raw.txt"],
                     check=True, capture_output=True).stdout.decode()
T = K.table(KP, "s")
P = K.predictions(KP, "s")
C = score.C
K1, K2, K3, K4 = (int(C[k], 16) for k in ("K1", "K2", "K3", "K4"))
FILL = int(C["FILL"], 16)
FILLTXT = open(os.path.join(KP, "mock", "kept", "fill.txt")).read()
TRITXT = open(os.path.join(KP, "mock", "kept", "tri.txt")).read()
COLS = K.COLUMNS


def kept_o0(job):
    return re.search(rf"^probe usse-pa-dest-persist__{job}: o0 (.*)$", RAW, re.M).group(1)


def ms_of(o0):
    ms, oth = score.o0_multiset(f"probe x: o0 {o0}\n")
    assert oth == 0
    return ms


MIX = ms_of(kept_o0(0))                     # E496's first pa0 reading


def line(name, ms):
    items = sorted(ms.items(), key=lambda kv: -kv[1])
    if len(items) == 1:
        return "probe %s: o0 0x%08x (%d of 2048)" % (name, items[0][0], items[0][1])
    return "probe %s: o0 mixed " % name + " ".join("0x%08x x%d" % kv for kv in items)


def marker_of(t):
    return int(P[t + "-w"]["sa"]["H-REF"], 16)


def attempt(root, a_model="H-ONEJOB", pa=None, sa_over=None, ctl_over=None, drop=()):
    """Every row's text under one sa0 model (H-ONEJOB, H-PERSIST, H-COLOUR) and a pa0 rule
    (pa(prev multiset or 'tri') -> decoded multiset; default H-PREV); sa_over {row: decoded
    multiset} replaces a reader's sa0; ctl_over {row: (sa, top)}."""
    d = os.path.join(root, "s")
    os.makedirs(d, exist_ok=True)
    pa = pa or (lambda prev: dict(MIX) if prev == "tri" else dict(prev))
    last, since, sa0 = None, 99, None
    with open(os.path.join(d, "cases.tsv"), "w") as f, open(os.path.join(d, "readings.tsv"), "w") as g:
        f.write("\t".join(COLS) + "\n")
        g.write("name\treads\treading\n")
        for r in T:
            n, a = r["name"], r["args"]
            if n in drop:
                continue
            f.write("\t".join([n, "s", r["set"], r["risk"], " ".join(r["knobs"]), r["tool"], a,
                               "0", "ok", "-", "-", "1000"]) + "\n")
            if a == "fill":
                txt, last = FILLTXT, {FILL: 2048}
                since += 1
            elif a == "tri":
                txt, last = TRITXT, "tri"
                since += 1
            elif "/bins/w-" in a:
                m = marker_of(n.split("-")[0])
                sa, top = ctl_over.get(n, (m, K1)) if ctl_over else (m, K1)
                out = {top: 2048}
                txt = line("w", out) + "\nprobe w: scratch +0x000 0x%08x\n" % sa
                g.write(f"{n}\tsa,top\tsa=0x{sa:08x} top=0x{top:08x}\n")
                last, since, sa0 = out, 0, m
            elif "/bins/k." in a:
                sa, top = ctl_over.get(n, (K3, K3)) if ctl_over else (K3, K3)
                txt = line("k", {top: 2048}) + "\nprobe k: scratch +0x000 0x%08x\n" % sa
                g.write(f"{n}\tsa,top\tsa=0x{sa:08x} top=0x{top:08x}\n")
                last = {top: 2048}
                since += 1
            elif "/bins/r." in a:
                prev = dict(MIX) if last == "tri" else last
                if a_model == "H-PERSIST" or (a_model == "H-ONEJOB" and since == 0):
                    dm = {sa0: 2048}
                else:
                    dm = dict(prev)
                if sa_over and n in sa_over:
                    dm = sa_over[n]
                out = {v ^ K2: c for v, c in dm.items()}
                txt = line("r", out) + "\nprobe r: scratch +0x000 0x%08x\n" % max(out, key=out.get)
                last = out
                since += 1
            else:
                dm = pa(last)
                out = {v ^ K4: c for v, c in dm.items()}
                txt = line("p", out) + "\nprobe p: scratch +0x000 0x%08x\n" % max(out, key=out.get)
                last = out
                since += 1
            open(os.path.join(d, n + ".txt"), "w").write(txt)
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(COLS) + "\n")
    return root


def rule(root):
    _, per, ctl, cats = score.score(os.path.join(root, "s"))
    return score.rule(per, ctl, cats)


def test_kept_e496_lines_parse():
    assert MIX == {0xFF00FF00: 1536, 0xFF203040: 512}
    assert ms_of(kept_o0(7)) == {0x79: 2048} and ms_of(kept_o0(8)) == {0x79: 2048}
    assert C["E496_FIRST"] == kept_o0(0) and C["E496_BEFORE"] == "diff: 0 of 4096 pixels"


def test_each_sa0_model_decides_a_on_its_own_pattern(tmp_path):
    for m in score.FULL_A:
        root = attempt(str(tmp_path / m), a_model=m)
        out = rule(root)
        assert out[0].endswith(f"DECIDED, {m}"), out
        assert out[1].endswith("DECIDED, H-PREV"), out
        assert out[2] == "Q136 RULE: RETIRE-CAPABLE (both clauses decided)"
        lines, per, _, _ = score.score(os.path.join(root, "s"))
        for o in score.FULL_A:
            if o != m:
                assert any(v is False for v in per[o].values()), (m, o)
        assert any(ln.startswith(f"SUMMARY: s: {m}: ") and "(16 of 16 rows decided)" in ln
                   for ln in lines)


def test_e496_confound_is_separated(tmp_path):
    """E496 jobs 7 and 8: the writer's colour was its marker, so job 8's 0x79 fitted both. Here the
    writer's colour is K1: a reader after W reads M (H-ONEJOB/H-PERSIST) or K1 (H-COLOUR), and a
    writer whose top is its marker (E496's form) fails its control: its readers cannot tell."""
    root = attempt(str(tmp_path / "c"), a_model="H-ONEJOB",
                   ctl_over={"nra-w": (marker_of("nra"), marker_of("nra"))})
    lines, per, ctl, _ = score.score(os.path.join(root, "s"))
    assert ctl["nra-w"] is False
    assert per["H-ONEJOB"]["nra-r"] is None and per["H-COLOUR"]["nra-r"] is None
    out = score.rule(per, ctl, {})
    assert "not decided (a control did not pass)" in out[0]


def test_e496_mixture_on_the_pa0_rows(tmp_path):
    """E496's first reading placed on every P row (H-FIXED): the fits hold, (b) fails."""
    root = attempt(str(tmp_path / "f"), pa=lambda prev: dict(MIX))
    out = rule(root)
    assert "ptr fits read TRI: yes" in out[1] and out[1].endswith("not decided")
    assert "H-PREV 0 held, 4 FAILED" in out[1] and "H-FIXED 4 held, 0 FAILED" in out[1]
    assert out[2] == "Q136 RULE: NARROW: clause (a) decided, clause (b) open"


def test_mixed_and_odd_readings_do_not_decide(tmp_path):
    # one replicate of k3 reads M (H-PERSIST), the other the colour job's colour (H-ONEJOB)
    root = attempt(str(tmp_path / "m"), a_model="H-ONEJOB",
                   sa_over={"k3a-r": {marker_of("k3a"): 2048}})
    out = rule(root)
    assert out[0].endswith("not decided (no single pattern holds on every R row)"), out[0]
    # a reader of a value no model names (zeros after a reset) is cannot tell, H-RESET held
    root = attempt(str(tmp_path / "z"), a_model="H-ONEJOB", sa_over={"rsa-r": {0: 2048}})
    lines, per, ctl, cats = score.score(os.path.join(root, "s"))
    assert per["H-ONEJOB"]["rsa-r"] is None and per["H-RESET"]["rsa-r"] is True
    assert score.rule(per, ctl, cats)[0].endswith("not decided (a held-out R row is not decided)")
    # a value no model names is no category; the marker as the most frequent value is M
    root = attempt(str(tmp_path / "x"), sa_over={"nra-r": {0x12345678: 2048},
                                                 "nrb-r": {marker_of("nrb"): 2044, K1: 4}})
    _, per, _, _ = score.score(os.path.join(root, "s"))
    assert per["H-PERSIST"]["nra-r"] is None and per["H-COLOUR"]["nra-r"] is None
    assert per["H-PERSIST"]["nrb-r"] is True and per["H-COLOUR"]["nrb-r"] is False


def test_reader_form_premise(tmp_path):
    """E1139: a reader whose dword 0 is not one of its o0 values (r34-sa0's keyed readers: dword 0
    0x693f0a01 with o0 0x5a0c0a01 x1904) is cannot tell, whatever its pixels."""
    root = attempt(str(tmp_path / "f"))
    f = os.path.join(root, "s", "nra-r.txt")
    t = open(f).read()
    open(f, "w").write(re.sub(r"scratch \+0x000 0x[0-9a-f]{8}", "scratch +0x000 0x693f0a01", t))
    _, per, _, _ = score.score(os.path.join(root, "s"))
    assert all(per[m]["nra-r"] is None for m in score.FULL_A)


def test_a_reader_that_did_not_run_and_a_kept_dir_without_rows(tmp_path):
    root = attempt(str(tmp_path / "d"), drop=("tra-r",))
    out = rule(root)
    assert "R rows decided 15 of 16" in out[0] and "not decided" in out[0]
    os.makedirs(str(tmp_path / "e" / "s"))
    out = rule(str(tmp_path / "e"))
    assert out[2] == "Q136 RULE: NARROW: neither clause decided"


def test_premise_and_gate_commands(tmp_path):
    root = attempt(str(tmp_path / "p"))
    d = os.path.join(root, "s")
    assert not K.premise(KP, "s", d)
    lines = open(os.path.join(d, "readings.tsv")).read().splitlines()
    open(os.path.join(d, "readings.tsv"), "w").write(
        "\n".join(ln for ln in lines if not ln.startswith("nra-w")) + "\n")
    assert K.premise(KP, "s", d)
    assert score.main(["score.py", "gate", "s", root]) == 0
