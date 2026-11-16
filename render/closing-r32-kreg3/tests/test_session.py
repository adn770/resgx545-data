# SPDX-License-Identifier: MIT
"""r32-kreg3's own tests: the generator current, the tables as the README says, the hooks' and the
scorer's readings alike (the median of renders 2-N), the frozen PICK rule (first qualifying form
in order, 64x64 before 1024x768, none: every gate shut and Q024 NOTHING), E1125's own references
(8.27 percent) qualifying no form, and the scorer on kept records: steady (holds, Q024 RETIRE),
one control out allowed and two failing, a value out on both passes (FINDING), the spread
premise, an image change named, a k stage that ran without its pick (cannot tell)."""
import os
import pathlib
import re
import subprocess
import sys
import tomllib

import pytest

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KP / "gen"))
sys.path.insert(0, str(KP / "kit"))
sys.path.insert(0, str(KP / "score"))
import gen  # noqa: E402
import kitscore as K  # noqa: E402
import score as S  # noqa: E402

PY = sys.executable
SCORE = KP / "score/score.py"
COLS = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n"
IMG = {(64, 64): "o0 mixed 0xff203040 x2961 0xff00ff00 x1135",
       (1024, 768): "o0 mixed 0xff203040 x577967 0xff00ff00 x208465"}
KST = [gen.stage_of(f[0]) for f in gen.FORMS]


def test_the_tables_and_predictions_are_what_gen_writes():
    r = subprocess.run([PY, str(KP / "gen/gen.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_the_forms_are_the_question_s_load_first_then_the_larger_target():
    assert [f[1:] for f in gen.FORMS] == [(64, 64, 10), (64, 64, 20), (64, 64, 40),
                                         (1024, 768, 10), (1024, 768, 20), (1024, 768, 40)]
    assert gen.PICK_PCT == 0.8 and gen.REFS == 8 and gen.OUTLIERS == 1
    # with a pick at most 0.8 percent, BOUND = max(1, 3 x IQR) stays under the cap
    assert max(gen.FLOOR_PCT, gen.K * gen.PICK_PCT) <= gen.CAP_PCT


def test_s0_is_safe_with_eight_references_a_form_in_shuffled_rounds():
    t = K.table(str(KP), "s0")
    assert t[0]["name"] == "c0-tri" and t[0]["args"] == gen.EXACT and len(t) == 49
    assert all(r["risk"] == "safe" and r["set"] == "control" for r in t)
    assert not any(w.startswith("kreg:") for r in t for w in r["knobs"])
    for i in range(gen.REFS):
        rnd = t[1 + 6 * i: 7 + 6 * i]
        assert sorted(r["name"] for r in rnd) == sorted(f"v{f[0]}-{i + 1}" for f in gen.FORMS)
        assert all(r["args"] == gen.timed(r["name"][1:].split("-")[0]) and r["tool"] == "t30"
                   for r in rnd)
    assert len({tuple(r["name"].split("-")[0] for r in t[1 + 6 * i: 7 + 6 * i])
                for i in range(8)}) > 1


@pytest.mark.parametrize("form", [f[0] for f in gen.FORMS])
def test_each_flagged_stage_writes_every_value_once_a_pass_with_16_controls(form):
    st = gen.stage_of(form)
    t = K.table(str(KP), st)
    vals = [(r["set"], r["knobs"][0]) for r in t if r["set"] in ("fit", "held")]
    for sset in ("fit", "held"):
        assert sorted(w for s, w in vals if s == sset) == [f"kreg:0x0a78={v}" for v in gen.VALUES]
    a, b = gen.passes()
    assert a != b and sorted(a) == sorted(b) == gen.VALUES
    names = [r["name"] for r in t]
    ctl = [r for r in t if r["set"] == "control" and r["knobs"][0].startswith("kreg:")]
    assert len(ctl) == 16 and all(r["knobs"][0] == "kreg:0x0a78=0x2c" for r in ctl)
    assert all(names[i] == f"c{i // 9 + 1:02d}" for i in range(0, 144, 9)), names
    assert names[-1] == "c-end" and t[-1]["knobs"] == ["reads:diff"] and len(t) == 145
    assert all(r["args"] == gen.timed(form) and r["tool"] == "t30" for r in t[:-1])
    assert t[-1]["args"] == gen.EXACT and t[-1]["tool"] == "t10"
    assert all(r["risk"] == "flagged" for r in t)
    assert not any("expectfault" in r["knobs"] for r in t)


def test_s0_is_safe_and_every_k_stage_flagged_gated_and_ending_the_session():
    c = tomllib.loads((KP / "session.toml").read_text())
    assert list(c["stages"]) == ["s0"] + KST
    assert c["stages"]["s0"] == {"alarm": 2400, "on_stop": "end"}
    for st in KST:
        assert c["stages"][st] == {"alarm": 3600, "gate": True, "class": "flagged",
                                   "on_stop": "end"}
    assert c["kregs"] == {"0x0a78": {"values": gen.VALUES}}
    assert c["srcversion"] == "7CE8E38EDB97FC5EA4F6C90" and c["prefix"] == "r32k"
    assert c["freeze"]["resgx545"].startswith("bf0ba56")
    for t in ("t10", "t30"):
        assert c["tools"][t]["sha256"] == {
            "t10": "9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb",
            "t30": "b5ea288d273f0da50884bbeec38f784a5d19773b8ed20efc7937dd455c1b87a5"}[t]
    for st in ["s0"] + KST:
        assert re.search(r"^#limit 0$", (KP / f"tables/{st}.txt").read_text(), re.M)


def data_show(path, text=False):
    c = tomllib.loads((KP / "session.toml").read_text())
    data = pathlib.Path(os.environ.get("RESGX545_DATA", pathlib.Path.home() / "src/resgx545-data"))
    r = subprocess.run(["git", "-C", str(data), "show", f"{c['freeze']['data']}:{path}"],
                       capture_output=True, text=text)
    if r.returncode:
        pytest.skip(f"{path} at the data commit is not in {data}")
    assert f"data:{path}" in c["freeze"]["pins"]
    return r.stdout


def test_the_program_is_the_pinned_one():
    assert data_show("render/closing-s1b/bins/p1139-green.bin") == \
        (KP / "bins/p1139-green.bin").read_bytes()


# ---- the readings: hooks and scorer alike ---------------------------------------------------
def tri_text(w, h, renders, diff=0):
    s = f"tri: render context for targets up to {w}x{h}\n"
    for i, t in enumerate(renders, 1):
        s += (f"job: ok\ntarget: {w}x{h} hash 0x0\ndiff: {diff} of {w * h} pixels\n"
              f"outside: 0 dwords\ntri {w}x{h} #{i}: 1 triangle, 0 background, 0 other; wrong 0 "
              f"inside, 0 outside, 0 at edges; 0 if flipped; guard 0\ntri {w}x{h} #{i}: {t} us\n")
    return s + f"tri: {len(renders)} renders ok\n"


def probe_text(renders, img=None, odd=None, wh=(64, 64)):
    img = img or IMG[wh]
    s = "programs asm\n"
    for i, t in enumerate(renders):
        s += ("probe p1139-green: scratch at 0x3e00e000 (64 KiB)\n"
              f"probe p1139-green: tri {wh[0]}x{wh[1]} (1500 vertices), pixel replaced\n"
              f"tri {wh[0]}x{wh[1]} #1: {t} us\n"
              f"probe p1139-green: {odd if odd and i == 3 else img}\n")
    return s


def hooks(tmp_path, text):
    (tmp_path / "x.out").write_text(text)
    r = subprocess.run(["bash", "-c", f'JW="{tmp_path}"; . "{KP}/run/hooks.sh"; hook_reading x; '
                        'echo "check:$(hook_check x)"'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


@pytest.mark.parametrize("renders", [[2400] + [2000 + 13 * (i % 7) for i in range(9)],
                                     [9] + list(range(19, 0, -1)), [5, 7] * 20,
                                     [3000, 700, 690, 2000, 680] + [700] * 15])
def test_hooks_and_scorer_read_the_same_median(tmp_path, renders):
    want = S.median_low(renders[1:])
    out = hooks(tmp_path, probe_text(renders))
    assert f"us={want}\n" in out and "img=0\n" in out, out
    assert S.reading(probe_text(renders))["us"] == want
    out = hooks(tmp_path, probe_text(renders, wh=(1024, 768)))
    assert f"us={want}\n" in out, out
    assert S.reading(tri_text(64, 64, [5585]))["diff"] == 0


def test_the_hooks_stop_a_wedge_and_a_failed_render_only(tmp_path):
    assert hooks(tmp_path, probe_text([2400] + [2000] * 9)).endswith("check:\n")
    assert hooks(tmp_path, probe_text([9000] * 40, wh=(1024, 768))).endswith("check:\n")
    out = hooks(tmp_path, probe_text([2400] * 10).replace("tri 64x64 #1: 2400 us\n", "", 1))
    assert "timed 9 renders, not 10" in out, out
    out = hooks(tmp_path, probe_text([2400] * 6))
    assert "started 6 renders, not 10, 20 or 40" in out, out
    out = hooks(tmp_path, probe_text([2400] * 10) + "probe p1139-green: failed: job timed out\n")
    assert "has a failed render" in out, out
    out = hooks(tmp_path, probe_text([2400] * 10, odd="o0 0xff00ff00"))
    assert "img=1\n" in out and out.endswith("check:\n"), out
    out = hooks(tmp_path, tri_text(64, 64, [1], diff=3))
    assert "drew 3 wrong pixels" in out, out
    # the wedge rule keeps one reference a form: another form's slower median is no wedge
    r = subprocess.run(["bash", "-c", f'JW="{tmp_path}"; . "{KP}/run/hooks.sh"; '
                        'printf "%s" "$1" > "$JW/a.out"; printf "%s" "$2" > "$JW/b.out"; '
                        'printf "%s" "$3" > "$JW/c.out"; printf "%s" "$4" > "$JW/d.out"; '
                        'hook_check a; hook_check b; hook_check c; hook_check d',
                        "_", probe_text([2000] * 10), probe_text([9000] * 10, wh=(1024, 768)),
                        probe_text([9500] * 10, wh=(1024, 768)), probe_text([4100] * 10)],
                       capture_output=True, text=True)
    assert r.stdout == "d's render median 4100 us is above twice 2000 us (64x64/10)\n", r.stdout


# ---- the pick rule --------------------------------------------------------------------------
def forms_of(spreads):
    """{form: dict(drawn, us)}: eight readings around 1000 us whose IQR is spreads[form] percent
    (None: a reference that did not draw)."""
    out = {}
    for f, *_ in gen.FORMS:
        p = spreads.get(f, 5.0)
        if p is None:
            out[f] = dict(drawn=[True] * 7 + [False], us=[1000] * 7)
            continue
        us = [1000 + 10 * p / 3.5 * (i - 3.5) for i in range(8)]     # IQR 3.5 steps = p %
        out[f] = dict(drawn=[True] * 8, us=us)
    return out


@pytest.mark.parametrize("spreads,want", [
    ({"10": 0.5}, "10"), ({"10": 0.9, "20": 0.8}, "20"), ({"20": 0.3, "40": 0.1}, "20"),
    ({"40": 0.7, "l10": 0.1}, "40"), ({"l10": 0.79}, "l10"), ({"l20": 0.6, "l40": 0.2}, "l20"),
    ({"l40": 0.8}, "l40"), ({}, None), ({"10": 0.81, "l40": 0.9}, None),
    ({"10": None, "20": 1.0, "l10": 0.4}, "l10")])
def test_the_pick_is_the_first_qualifying_form_in_order(spreads, want):
    forms = forms_of(spreads)
    for f, x in forms.items():
        if x["drawn"][-1]:
            assert abs(S.iqr_pct(x["us"]) - spreads.get(f, 5.0)) < 1e-9
    assert S.pick(forms) == want


def test_e1125_s_references_qualify_no_form():
    """E1125's s0 v1-v8 (r31-kreg2's posthoc.txt at the pinned data commit): 8.27 percent."""
    txt = data_show("render/closing-r31-kreg2/fold/posthoc.txt", text=True)
    m = re.search(r"^s0 v1-v8 medians of renders 2-6: ((?:\d+ ){8})us; median ([\d.]+), IQR "
                  r"([\d.]+) %", txt, re.M)
    v = [int(x) for x in m[1].split()]
    assert v == [703, 774, 695, 687, 750, 697, 736, 822]
    assert round(S.iqr_pct(v), 2) == float(m[3]) == 8.27
    assert S.pick({f[0]: dict(drawn=[True] * 8, us=v) for f in gen.FORMS}) is None


# ---- kept records -------------------------------------------------------------------------
def form_of(r):
    m = re.search(r"--width (\d+) --height (\d+) ", r["args"])
    if not m or not r["args"].startswith("probe"):
        return None
    return next(f[0] for f in gen.FORMS if r["args"] == gen.timed(f[0]))


def kept(root, stage, times, image=lambda r: None):
    """A kept stage directory: every row of the table ok; a probe row's renders `times(row)` and
    o0 line `image(row)` (None: the target's); a 64x64 exact row one render."""
    d = root / stage
    d.mkdir(parents=True)
    rows = ""
    for r in K.table(str(KP), stage):
        f = form_of(r)
        if f:
            txt = probe_text(times(r), image(r), wh=tuple(gen.FORM[f][1:3]))
        else:
            txt = tri_text(64, 64, [5585])
        (d / f"{r['name']}.txt").write_text(txt)
        rows += f"{r['name']}\t{stage}\t{r['set']}\t{r['risk']}\t{' '.join(r['knobs'])}\t" \
            f"{r['tool']}\t{r['args']}\t0\tok\t0\t0x0\t9999999\n"
    (d / "cases.tsv").write_text(COLS + rows)
    (d / "void.tsv").write_text(COLS)
    (d / "readings.tsv").write_text("name\tkeys\treading\n")
    return d


def value_of(r):
    return next((w.split("=")[1] for w in r["knobs"] if w.startswith("kreg:")), None)


def steady(noisy=()):
    """times(row): base 2000 us (64x64) or 9000 us (1024x768), renders 2-N flat; a reference of a
    form in noisy spreads its eight medians by 5 percent, of the others by 0.2 percent."""
    def times(r):
        f = form_of(r)
        n = gen.FORM[f][3]
        base = 2000 if gen.FORM[f][1] == 64 else 9000
        m = re.fullmatch(r"v\w+-(\d)", r["name"])
        if m:
            k = int(m[1]) % 3 - 1
            base = int(base * (1 + k * (0.05 if f in noisy else 0.002)))
        return [int(base * 1.2)] + [base] * (n - 1)
    return times


def build(root, k=None, form="10", s0=None, image=lambda r: None):
    kept(root, "s0", s0 or steady(), image)
    kept(root, gen.stage_of(form), k or steady(), image)


def run(*args):
    r = subprocess.run([PY, str(SCORE), *map(str, args)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def summary(out, st):
    return next(ln for ln in out.splitlines() if ln.startswith(f"SUMMARY: {st}: "))


def score(root, st):
    return run(st, root / st, root)


def gate(root, st):
    return subprocess.run([PY, str(SCORE), "gate", st, root], capture_output=True).returncode


def test_steady_picks_10_holds_and_q024_retires(tmp_path):
    build(tmp_path)
    out = score(tmp_path, "s0")
    assert "PICK: 10 (" in out and "FORM l40 " in out, out
    assert "s0's references draw; picked form 10 (48 of 48" in summary(out, "s0"), out
    assert [gate(tmp_path, st) for st in KST] == [0, 1, 1, 1, 1, 1]
    s = summary(score(tmp_path, "k10"), "k10")
    assert "(64 of 64 rows decided)" in s and "within 1.00 percent" in s, s
    assert "at 64x64, 10 renders a job" in s
    assert "Q024: RETIRE" in run("q024", tmp_path)


def test_noisy_64x64_falls_back_to_1024x768(tmp_path):
    t = steady(noisy=("10", "20", "40"))
    build(tmp_path, s0=t, k=t, form="l10")
    out = score(tmp_path, "s0")
    assert "PICK: l10 (" in out and "FORM 10 " in out and "does not qualify" in out, out
    assert [gate(tmp_path, st) for st in KST] == [1, 1, 1, 0, 1, 1]
    assert "Q024: RETIRE" in run("q024", tmp_path)


def test_no_form_qualifies_every_gate_shut_and_q024_nothing(tmp_path):
    t = steady(noisy=tuple(f[0] for f in gen.FORMS))
    kept(tmp_path, "s0", t)
    out = score(tmp_path, "s0")
    assert "PICK: none (no form qualified" in out, out
    assert "no form qualified" in summary(out, "s0")
    assert all(gate(tmp_path, st) == 1 for st in KST)
    q = run("q024", tmp_path)
    assert "Q024: NOTHING (STOPPED before any flagged row" in q, q


def test_a_k_stage_without_its_pick_cannot_tell_and_c0_shuts_the_gates(tmp_path):
    build(tmp_path / "x", form="20")
    s = summary(score(tmp_path / "x", "k20"), "k20")
    assert s.startswith("SUMMARY: k20: cannot tell") and "pick: cannot tell" in s, s
    assert "Q024: NOTHING (k10 did not run)" in run("q024", tmp_path / "x")
    kept(tmp_path / "y", "s0", steady())
    (tmp_path / "y/s0/c0-tri.txt").write_text(tri_text(64, 64, [5585], diff=2))
    assert all(gate(tmp_path / "y", st) == 1 for st in KST)


def test_a_reference_that_draws_another_image_disqualifies_its_form(tmp_path):
    kept(tmp_path, "s0", steady(), image=lambda r: "o0 0xff00ff00" if r["name"] == "v10-5" else None)
    out = score(tmp_path, "s0")
    assert "FORM 10 (" in out and "7 of 8 drew" in out and "PICK: 20 (" in out, out


def with_controls(base, devs):
    def times(r):
        b = base(r)
        if r["name"] in devs:
            return [b[0]] + [int(x * (1 + devs[r["name"]] / 100)) for x in b[1:]]
        return b
    return times


def test_one_control_out_of_band_is_allowed_and_two_fail(tmp_path):
    build(tmp_path / "x", k=with_controls(steady(), {"c07": 3.0}))
    out = score(tmp_path / "x", "k10")
    assert "(64 of 64 rows decided)" in summary(out, "k10"), out
    assert "OUTLIERS: c07 (1 outside" in out and "the one allowed outlier" in out, out
    assert "Q024: RETIRE" in run("q024", tmp_path / "x")
    build(tmp_path / "y", k=with_controls(steady(), {"c07": 3.0, "c12": -2.0}))
    out = score(tmp_path / "y", "k10")
    assert "controls FAILED" in summary(out, "k10") and "c07: FAILED" in out, out
    assert "Q024: NOTHING (k10 did not decide 64 of 64)" in run("q024", tmp_path / "y")


def test_a_control_that_draws_wrong_is_never_the_allowed_outlier(tmp_path):
    build(tmp_path, image=lambda r: "o0 0xff00ff00" if r["name"] == "c05" else None)
    s = summary(score(tmp_path, "k10"), "k10")
    assert s.startswith("SUMMARY: k10: controls FAILED: c05: FAILED"), s


def by_value(base, table):
    def times(r):
        v = value_of(r)
        b = base(r)
        if r["set"] in ("fit", "held") and v in table:
            p = table[v][r["set"] == "held"]
            return [b[0]] + [int(x * (1 + p / 100)) for x in b[1:]]
        return b
    return times


def test_a_value_out_on_both_passes_fails_and_out_on_its_fit_only_holds(tmp_path):
    build(tmp_path / "x", k=by_value(steady(), {"0x01": (2.2, 2.2)}))
    out = score(tmp_path / "x", "k10")
    assert "is not supported" in summary(out, "k10") and re.search(r"ROW 0x01: .*FAILED", out)
    assert "Q024: FINDING" in run("q024", tmp_path / "x")
    build(tmp_path / "y", k=by_value(steady(), {"0x01": (2.2, 0.1), "0x02": (-3, 3)}))
    out = score(tmp_path / "y", "k10")
    assert "(64 of 64 rows decided)" in summary(out, "k10"), out
    assert re.search(r"ROW 0x01: .*held \(fit pass outside", out), out


def test_e141_s_excursions_fail_on_both_passes(tmp_path):
    """E141: 0x01 5.5 and 0x20 2.6 percent above 0x2c: both outside a bound of at most 2.4."""
    build(tmp_path, k=by_value(steady(), {"0x01": (5.48, 5.48), "0x20": (2.6, 2.6)}))
    out = score(tmp_path, "k10")
    assert re.search(r"ROW 0x01: .*FAILED", out) and re.search(r"ROW 0x20: .*FAILED", out), out


def test_the_controls_spread_is_a_premise(tmp_path):
    def spread(r):
        b = steady()(r)
        if r["set"] == "control" and value_of(r):
            x = int(b[1] * (1.004 if int(r["name"][1:]) % 2 else 0.996))
            return [b[0]] + [x] * (len(b) - 1)
        return b
    build(tmp_path, k=spread)
    s = summary(score(tmp_path, "k10"), "k10")
    assert s.startswith("SUMMARY: k10: cannot tell:") and "spread: cannot tell" in s, s


def test_the_bound_widens_with_the_pick_s_spread(tmp_path):
    def wider(r):
        b = steady()(r)
        m = re.fullmatch(r"v10-(\d)", r["name"])
        if m:
            x = int(b[1] * (1 + 0.0035 * (int(m[1]) % 4 - 1.5)))
            return [b[0]] + [x] * (len(b) - 1)
        return b
    build(tmp_path, s0=wider)
    out = score(tmp_path, "s0")
    b = float(re.search(r"BOUND ([\d.]+) %", out)[1])
    assert gen.FLOOR_PCT < b <= gen.CAP_PCT, out
    assert f"within {b:.2f} percent" in summary(score(tmp_path, "k10"), "k10")


def test_a_value_drawing_another_image_is_cannot_tell_and_named(tmp_path):
    build(tmp_path, image=lambda r: "o0 0xff00ff00" if r["name"] == "b3f" else None)
    out = score(tmp_path, "k10")
    assert "IMAGE 0x3f: b3f drew another image" in out and "ROW 0x3f: " in out, out
    assert "63 of 64 rows decided" in summary(out, "k10"), out
    assert "Q024: NOTHING (k10 did not decide 64 of 64)" in run("q024", tmp_path)
