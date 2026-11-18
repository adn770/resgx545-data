# SPDX-License-Identifier: MIT
"""tests/test_score.py: r35-o0b's scorer on synthetic kept directories (the mock's images, simulated
row by row in table order: mock/world.py simulate) and on edits of them.

D2 (rank-round35.md section 1): every hypothesis name frozen in predictions/*.tsv is printed by
the scorer as `held` in at least one synthetic table and as `FAILED` in at least one
(test_every_frozen_name_is_produced; a name in no test fails it), and the controls' H-REF prints
PASS and FAILED. D1: a control that fails (A' 64 off by one bit, K, the c1 P) makes the rows it
gates cannot tell, and only those (E1143: r35-o0 gated every row on c0a-a128); the 128 x 128
A' control passes with E1143's share of misplaced pixels and fails beyond 2 %. The retire rule
reads RETIRE-CAPABLE in the offsets world and NARROW where a clause cannot be decided."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "mock")]
sys.dont_write_bytecode = True
import score as SC  # noqa: E402
import world as WD  # noqa: E402

COLS = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n"
TAB = SC.K.table(KP, "o")
SEEN = {}


def kept_dir(tmp, world, edit=None, skip=()):
    out = WD.simulate(TAB, world)
    if edit:
        edit(out)
    d = os.path.join(str(tmp), world, "o")
    os.makedirs(d, exist_ok=True)
    cases, reads = [COLS], ["name\tstage\treading\n"]
    for r in TAB:
        n = r["name"]
        if n in skip:
            continue
        cases.append("\t".join([n, "o", r["set"], r["risk"], " ".join(r["knobs"]), r["tool"],
                                r["args"], "0", "ok", "", "", "999999"]) + "\n")
        with open(os.path.join(d, n + ".txt"), "w") as f:
            f.write(out[n])
        if r["set"] == "control":
            k = len(re.findall(r": row \d+: ", out[n]))
            reads.append(f"{n}\to\tpixels={k}\n")
    for f, t in (("cases.tsv", cases), ("readings.tsv", reads), ("void.tsv", [COLS])):
        with open(os.path.join(d, f), "w") as fh:
            fh.write("".join(t))
    return d


def run(tmp, world, **kw):
    d = kept_dir(tmp, world, **kw)
    lines, per, ctl, counts = SC.score(d)
    text = lines + SC.rule(per, ctl, counts)
    for ln in text:
        m = re.match(r"^ROW \S+ \(\w+\) (H-[A-Z0-9]+): frozen \S+: (held|FAILED|cannot tell)", ln)
        if m:
            SEEN.setdefault(m.group(1), set()).add(m.group(2))
        m = re.match(r"^CONTROL \S+: .*: (PASS|FAILED|cannot tell)$", ln)
        if m:
            SEEN.setdefault("H-REF", set()).add(m.group(1))
    return per, ctl, "\n".join(text)


def st(per, model, names):
    return [per[model][n] for n in names]


H1 = sorted({"h1a-p", "h1b-p", "h1c-p"})
H2 = ["h2a-p", "h2b-p"]
H3 = ["h3a-p", "h3b-p"]


def test_offsets_retires(tmp_path):
    per, ctl, text = run(tmp_path, "offsets")
    assert all(v is True for v in ctl.values()), text
    assert all(v is True for v in per["H-OFFSETS"].values()), text
    assert False in per["H-SAMEPIX"].values() and not any(per["H-OTHER"].values())
    assert st(per, "H-SIZENONE", H2) == [True, True] and st(per, "H-SIZEKEEP", H2) == [False, False]
    assert all(per["H-OFFSETS128"][n] is True for n in H3), text
    assert all(v is True for v in per["H-RESETKEEP"].values())
    assert all(v is True for v in per["H-FILLREPLACE"].values())
    assert all(v is False for v in per["H-TRIONLY"].values())
    assert ": DECIDED, H-OFFSETS" in text and "Q073 RULE: RETIRE-CAPABLE" in text, text
    assert "Q073 ANSWER [HW]: at the start of an opaque pass's pixel shader o0 holds the o0 an " \
           "earlier job's shader wrote" in text


def test_model_world_is_offsets(tmp_path):
    _, _, a = run(tmp_path / "m", "model")
    _, _, b = run(tmp_path / "o", "offsets")
    assert a == b


def test_samepix(tmp_path):
    per, ctl, text = run(tmp_path, "samepix")
    assert all(v is True for v in per["H-SAMEPIX"].values()), text
    assert all(v is True for v in per["H-OFFSETS"].values())    # (0, 0) is one of the offsets
    assert ": DECIDED, H-SAMEPIX" in text and "Q073 RULE: RETIRE-CAPABLE" in text


def test_shift(tmp_path):
    per, ctl, text = run(tmp_path, "shift")
    assert all(v is False for v in per["H-OFFSETS"].values()), text
    assert all(v is True for v in per["H-OTHER"].values())
    assert False in per["H-OFFSETS128"].values()
    assert "Q073 RULE: NARROW" in text


def test_other(tmp_path):
    per, ctl, text = run(tmp_path, "other")
    assert all(v is False for v in per["H-OFFSETS"].values()), text
    assert all(v is True for v in per["H-OTHER"].values())
    assert all(v is None for v in per["H-OFFSETS128"].values())   # no pixel reads A
    assert "Q073 RULE: NARROW" in text


def test_sizekeep(tmp_path):
    per, _, text = run(tmp_path, "sizekeep")
    assert st(per, "H-SIZEKEEP", H2) == [True, True] and st(per, "H-SIZENONE", H2) == [False, False]


def test_resetclear(tmp_path):
    per, _, text = run(tmp_path, "resetclear")
    assert all(v is True for v in per["H-RESETCLEAR"].values()), text
    assert all(v is False for v in per["H-RESETKEEP"].values())


def test_trionly(tmp_path):
    per, _, text = run(tmp_path, "trionly")
    assert all(v is True for v in per["H-TRIONLY"].values()), text
    assert all(v is False for v in per["H-FILLREPLACE"].values())


def flip_a(out, name="c0a-a64", rows=(20,), count=1):
    """count A' pixels per row off by one bit."""
    t = out[name]
    for y in rows:
        m = re.search(r"^(probe a: row %d: )(.*)$" % y, t, re.M)
        vals = m.group(2).split()
        idx = [i for i, v in enumerate(vals) if v != "ff203040"][:count]
        for i in idx:
            vals[i] = "%08x" % (int(vals[i], 16) ^ 1)
        t = t[:m.start(2)] + " ".join(vals) + t[m.end(2):]
    out[name] = t


def test_a64_control_failure_gates_its_size(tmp_path):
    per, ctl, text = run(tmp_path, "offsets", edit=flip_a)
    assert ctl["c0a-a64"] is False, text
    assert all(v is None for v in per["H-OFFSETS"].values())
    assert all(v is None for v in per["H-OFFSETS128"].values())     # h3's A' is 64 x 64
    assert all(v is not None for v in per["H-SIZENONE"].values())   # h2's A' is 128: not gated
    assert "Q073 RULE: NARROW" in text


def test_a128_share(tmp_path):
    # E1143's worst row: 30 of 4284 misplaced passes; 2 % and more fails
    per, ctl, text = run(tmp_path / "ok", "offsets",
                         edit=lambda o: flip_a(o, "c0a-a128", rows=range(40, 70), count=1))
    assert ctl["c0a-a128"] is True, text
    per, ctl, text = run(tmp_path / "bad", "offsets",
                         edit=lambda o: flip_a(o, "h2a-a", rows=range(20, 110), count=1))
    assert ctl["h2a-a"] is False
    assert per["H-SIZENONE"]["h2a-p"] is None and per["H-SIZENONE"]["h2b-p"] is True
    assert all(per["H-OFFSETS"][n] is True for n in H1)            # 64 x 64 rows not gated


def test_group_control_failure_gates_its_group_only(tmp_path):
    per, ctl, text = run(tmp_path, "offsets", edit=lambda o: flip_a(o, "h1b-a"))
    assert ctl["h1b-a"] is False
    assert per["H-OFFSETS"]["h1b-p"] is None and per["H-OFFSETS"]["h1a-p"] is True
    assert "Q073 RULE (a) same size: controls not all passed" in text


def test_c1_p_failure(tmp_path):
    def edit(out):
        out["c1a-p"] = re.sub(r"(: row \d+: [^\n]*?)ff00ff00", r"\1ff00ff01", out["c1a-p"], count=1)
    per, ctl, text = run(tmp_path, "offsets", edit=edit)
    assert ctl["c1a-p"] is False and ctl["c1a-k"] is True, text
    assert all(v is None for m in per for v in per[m].values())


def test_k_failure(tmp_path):
    def edit(out):
        out["c1b-k"] = re.sub(r"(: row \d+: [^\n]*?)ff00ff00", r"\1ff00ff10", out["c1b-k"], count=1)
    per, ctl, text = run(tmp_path, "offsets", edit=edit)
    assert ctl["c1b-k"] is False


def test_no_image_is_cannot_tell(tmp_path):
    def edit(out):
        out["h1c-p"] = "\n".join(ln for ln in out["h1c-p"].splitlines() if ": row 63:" not in ln)
    per, ctl, text = run(tmp_path, "offsets", edit=edit)
    assert per["H-OFFSETS"]["h1c-p"] is None
    assert "Q073 RULE: RETIRE-CAPABLE" in text            # 3 of 4 h1 rows decided


def test_two_h1_rows_missing_do_not_decide(tmp_path):
    per, ctl, text = run(tmp_path, "offsets", skip=("h1c-p", "h1b-p"))
    assert "Q073 RULE: NARROW" in text


def test_missing_control_is_cannot_tell(tmp_path):
    per, ctl, text = run(tmp_path, "offsets", skip=("c0a-a128",))
    assert ctl["c0a-a128"] is None
    assert all(v is None for v in per["H-SIZENONE"].values())
    assert all(v is True for v in per["H-OFFSETS"].values())


def test_every_frozen_name_is_produced(tmp_path):
    """D2: run every world, then every model of predictions/*.tsv was printed held and FAILED."""
    for w in ("offsets", "samepix", "shift", "other", "sizekeep", "resetclear", "trionly"):
        run(tmp_path / w, w)
    run(tmp_path / "bad", "offsets", edit=flip_a)
    frozen = set()
    for f in os.listdir(os.path.join(KP, "predictions")):
        if f.endswith(".tsv"):
            for ln in open(os.path.join(KP, "predictions", f)).read().splitlines()[1:]:
                frozen.add(ln.split("\t")[3])
    assert frozen == {"H-REF", "H-OFFSETS", "H-SAMEPIX", "H-OTHER", "H-SIZENONE", "H-SIZEKEEP",
                      "H-OFFSETS128", "H-RESETKEEP", "H-RESETCLEAR", "H-FILLREPLACE",
                      "H-TRIONLY"}
    for m in frozen:
        want = {"PASS", "FAILED"} if m == "H-REF" else {"held", "FAILED"}
        assert want <= SEEN.get(m, set()), (m, SEEN.get(m))


def test_scorer_commands(tmp_path, capsys):
    d = kept_dir(tmp_path, "offsets")
    assert SC.main(["score.py", "o", d]) == 0
    out = capsys.readouterr().out
    assert "SUMMARY: o: H-OFFSETS: " in out
    assert SC.main(["score.py", "q073", os.path.dirname(d)]) == 0
    assert "Q073 RULE: RETIRE-CAPABLE" in capsys.readouterr().out
    assert SC.main(["score.py", "premise", "o", d]) == 0
    assert SC.main(["score.py", "gate", "o", d]) == 0
