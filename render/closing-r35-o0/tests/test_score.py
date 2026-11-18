# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer on synthetic kept directories (the mock's images, simulated
row by row in table order: mock/world.py simulate) and on edits of them.

D2 (rank-round35.md section 1): every hypothesis name frozen in predictions/*.tsv is printed by
the scorer as `held` in at least one synthetic table and as `FAILED` in at least one
(test_every_frozen_name_is_produced; a name in no test fails it), and the controls' H-REF prints
PASS and FAILED. D1: a control that fails (A' off by one bit, K, the c1 P) makes every row it gates
cannot tell, and the rule NARROW. The retire rule reads RETIRE-CAPABLE in the samepix world and
NARROW where a clause cannot be decided."""
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
        m = re.match(r"^ROW \S+ \(\w+\) (H-[A-Z]+): frozen \S+: (held|FAILED|cannot tell)", ln)
        if m:
            SEEN.setdefault(m.group(1), set()).add(m.group(2))
        m = re.match(r"^CONTROL \S+: .*: (PASS|FAILED|cannot tell)$", ln)
        if m:
            SEEN.setdefault("H-REF", set()).add(m.group(1))
    return per, ctl, "\n".join(text)


def states(per, model, names):
    return [per[model][n] for n in names]


H1 = ["h1b-p", "h1c-p"]
SIZE = ["h2a-p", "h2b-p", "h3a-p", "h3b-p"]


def test_samepix_retires(tmp_path):
    per, ctl, text = run(tmp_path, "samepix")
    assert all(v is True for v in ctl.values()), text
    assert states(per, "H-SAMEPIX", H1 + SIZE) == [True] * 6, text
    assert all(v is False for v in states(per, "H-OTHER", H1 + SIZE)), text
    assert all(v is None for v in states(per, "H-SLOTMAP", H1 + SIZE)), text   # identity fit
    assert False in states(per, "H-TILESLOT", SIZE), text
    assert per["H-RESETKEEP"]["h4a-p"] is True and per["H-RESETCLEAR"]["h4a-p"] is False
    assert per["H-FILLREPLACE"]["h5a-p"] is True and per["H-TRIONLY"]["h5a-p"] is False
    assert "Q073 RULE (a) same size: " in text and ": DECIDED, H-SAMEPIX" in text
    assert "Q073 RULE: RETIRE-CAPABLE" in text, text
    assert "Q073 ANSWER [HW]: at the start of an opaque pass's pixel shader o0 holds the o0 the " \
           "previous job's shader wrote at the same pixel" in text
    assert "FIT h1a-p: the identity on 450 pixels" in text


def test_model_world_is_samepix(tmp_path):
    _, _, a = run(tmp_path / "m", "model")
    _, _, b = run(tmp_path / "s", "samepix")
    assert a == b


def test_slotmap(tmp_path):
    per, ctl, text = run(tmp_path, "slotmap")
    assert all(v is True for v in ctl.values()), text
    assert states(per, "H-SLOTMAP", H1) == [True, True], text
    assert per["H-SLOTMAP"]["h1a-p"] is True                     # the fit row itself
    assert states(per, "H-SAMEPIX", H1) == [False, False]
    assert states(per, "H-OTHER", H1) == [False, False]
    assert ": DECIDED, H-SLOTMAP" in text, text
    assert re.search(r"FIT h1a-p: a map on \d+ pixels, \d+ moved", text)


def test_tileslot_on_the_size_rows(tmp_path):
    per, ctl, text = run(tmp_path, "tileslot")
    assert all(v is True for v in ctl.values()), text
    dec = [n for n in SIZE if per["H-TILESLOT"][n] is not None]
    assert dec and all(per["H-TILESLOT"][n] is True for n in dec), text
    assert False in [per["H-SAMEPIX"][n] for n in dec], text
    assert "Q073 RULE (b) other size" in text
    # same size: the tile map is the identity, so H-SAMEPIX holds on h1
    assert states(per, "H-SAMEPIX", H1) == [True, True]


def test_other(tmp_path):
    per, ctl, text = run(tmp_path, "other")
    assert all(v is True for v in ctl.values()), text
    assert states(per, "H-OTHER", H1 + SIZE) == [True] * 6, text
    assert states(per, "H-SAMEPIX", H1) == [False, False]
    assert "FIT h1a-p: no map" in text
    assert "Q073 RULE: NARROW" in text


def test_resetclear(tmp_path):
    per, _, text = run(tmp_path, "resetclear")
    assert per["H-RESETCLEAR"]["h4a-p"] is True and per["H-RESETKEEP"]["h4a-p"] is False, text
    assert per["H-RESETCLEAR"]["h4b-p"] is True


def test_trionly(tmp_path):
    per, _, text = run(tmp_path, "trionly")
    assert per["H-TRIONLY"]["h5a-p"] is True and per["H-FILLREPLACE"]["h5a-p"] is False, text


def flip_a(out, name="c0a-a64"):
    """One A' pixel off by one bit (the decoder's known value broken)."""
    t = out[name]
    m = re.search(r"^(probe a: row 20: )(.*)$", t, re.M)
    vals = m.group(2).split()
    i = next(i for i, v in enumerate(vals) if v != "ff203040")
    vals[i] = "%08x" % (int(vals[i], 16) ^ 1)
    out[name] = t[:m.start(2)] + " ".join(vals) + t[m.end(2):]


def test_a_control_failure_voids_every_row(tmp_path):
    per, ctl, text = run(tmp_path, "samepix", edit=flip_a)
    assert ctl["c0a-a64"] is False, text
    for m in per:
        assert all(v is None for n, v in per[m].items()), (m, per[m])
    assert "Q073 RULE: NARROW" in text and "c0a-a64 FAILED" in text


def test_group_a_control_failure_voids_its_group(tmp_path):
    per, ctl, text = run(tmp_path, "samepix", edit=lambda o: flip_a(o, "h2a-a"))
    assert ctl["h2a-a"] is False
    assert per["H-SAMEPIX"]["h2a-p"] is None and per["H-SAMEPIX"]["h2b-p"] is True


def test_c1_p_failure(tmp_path):
    def edit(out):
        out["c1a-p"] = re.sub(r"(: row \d+: [^\n]*?)ff00ff00", r"\1ff00ff01", out["c1a-p"], count=1)
    per, ctl, text = run(tmp_path, "samepix", edit=edit)
    assert ctl["c1a-p"] is False and ctl["c1a-k"] is True, text
    assert all(v is None for v in per["H-SAMEPIX"].values())


def test_k_failure(tmp_path):
    def edit(out):
        out["c1b-k"] = re.sub(r"(: row \d+: [^\n]*?)ff00ff00", r"\1ff00ff10", out["c1b-k"], count=1)
    per, ctl, text = run(tmp_path, "samepix", edit=edit)
    assert ctl["c1b-k"] is False


def test_no_image_is_cannot_tell(tmp_path):
    def edit(out):
        out["h1c-p"] = "\n".join(ln for ln in out["h1c-p"].splitlines() if ": row 63:" not in ln)
    per, ctl, text = run(tmp_path, "samepix", edit=edit)
    assert per["H-SAMEPIX"]["h1c-p"] is None
    assert "not decided (a held-out h1 row is not decided)" in text
    assert "Q073 RULE: NARROW" in text


def test_missing_control_is_cannot_tell(tmp_path):
    per, ctl, text = run(tmp_path, "samepix", skip=("c0a-a128",))
    assert ctl["c0a-a128"] is None
    assert all(v is None for v in per["H-SAMEPIX"].values())


def test_empty_size_rows_do_not_decide(tmp_path):
    def edit(out):
        for n in ("h3a-p", "h3b-p"):
            out[n] = re.sub(r"(: row \d+: )(.*)", lambda m: m.group(1) + " ".join(
                "ff203040" for _ in m.group(2).split()), out[n])
    per, ctl, text = run(tmp_path, "samepix", edit=edit)
    assert per["H-SAMEPIX"]["h3a-p"] is None
    assert "no decided row in h2 or in h3" in text and "Q073 RULE: NARROW" in text


def test_every_frozen_name_is_produced(tmp_path):
    """D2: run every world, then every model of predictions/*.tsv was printed held and FAILED."""
    for w in ("samepix", "slotmap", "tileslot", "other", "resetclear", "trionly"):
        run(tmp_path / w, w)
    run(tmp_path / "bad", "samepix", edit=flip_a)
    frozen = set()
    for f in os.listdir(os.path.join(KP, "predictions")):
        if f.endswith(".tsv"):
            for ln in open(os.path.join(KP, "predictions", f)).read().splitlines()[1:]:
                frozen.add(ln.split("\t")[3])
    assert frozen == {"H-REF", "H-SAMEPIX", "H-SLOTMAP", "H-OTHER", "H-TILESLOT", "H-RESETKEEP",
                      "H-RESETCLEAR", "H-FILLREPLACE", "H-TRIONLY"}
    for m in frozen:
        want = {"PASS", "FAILED"} if m == "H-REF" else {"held", "FAILED"}
        assert want <= SEEN.get(m, set()), (m, SEEN.get(m))


def test_scorer_commands(tmp_path, capsys):
    d = kept_dir(tmp_path, "samepix")
    assert SC.main(["score.py", "o", d]) == 0
    out = capsys.readouterr().out
    assert "SUMMARY: o: H-SAMEPIX: " in out
    assert SC.main(["score.py", "q073", os.path.dirname(d)]) == 0
    assert "Q073 RULE: RETIRE-CAPABLE" in capsys.readouterr().out
    assert SC.main(["score.py", "premise", "o", d]) == 0
    assert SC.main(["score.py", "gate", "o", d]) == 0
