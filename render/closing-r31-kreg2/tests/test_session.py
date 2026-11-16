# SPDX-License-Identifier: MIT
"""r31-kreg2's own tests: the generator current, the tables as the README says, the hooks' and the
scorer's readings alike (the median of renders 2-6), and the scorer on kept records: flat (holds,
both loads, Q024 RETIRE), E1114's own renders under the frozen single-control outlier rule (holds
64 of 64 with c11 the one allowed outlier; post hoc, a calibration, said so in the README), E141's
two slow values on both passes (FAILED), and every cannot-tell premise and FAILED control."""
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
IMG = "o0 mixed 0xff203040 x2961 0xff00ff00 x1135"


def test_the_tables_and_predictions_are_what_gen_writes():
    r = subprocess.run([PY, str(KP / "gen/gen.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("st", ["k1", "k2"])
def test_each_flagged_stage_writes_every_value_once_a_pass_with_16_controls(st):
    t = K.table(str(KP), st)
    vals = [(r["set"], r["knobs"][0]) for r in t if r["set"] in ("fit", "held")]
    for sset in ("fit", "held"):
        assert sorted(w for s, w in vals if s == sset) == [f"kreg:0x0a78={v}" for v in gen.VALUES]
    a, b = gen.passes(st)
    assert a != b and sorted(a) == sorted(b) == gen.VALUES
    names = [r["name"] for r in t]
    ctl = [r for r in t if r["set"] == "control" and r["knobs"][0].startswith("kreg:")]
    assert len(ctl) == 16 and all(r["knobs"][0] == "kreg:0x0a78=0x2c" for r in ctl)
    assert all(names[i] == f"c{i // 9 + 1:02d}" for i in range(0, 144, 9)), names
    assert names[-1] == "c-end" and t[-1]["knobs"] == ["reads:diff"] and len(t) == 145
    timed, tool = (gen.TIMED1, "t10") if st == "k1" else (gen.TIMED2, "t30")
    assert all(r["args"] == timed and r["tool"] == tool for r in t[:-1])
    assert t[-1]["args"] == gen.EXACT and t[-1]["tool"] == "t10"
    assert all(r["risk"] == "flagged" for r in t)
    assert not any("expectfault" in r["knobs"] for r in t)


def test_the_two_loads_have_their_own_shuffles():
    assert gen.passes("k1") != gen.passes("k2")


def test_s0_is_safe_and_k1_k2_flagged_gated_and_ending_the_session():
    c = tomllib.loads((KP / "session.toml").read_text())
    assert list(c["stages"]) == ["s0", "k1", "k2"]
    assert c["stages"]["s0"].get("class", "safe") == "safe"
    for st in ("k1", "k2"):
        assert c["stages"][st] == {"alarm": 7200, "gate": True, "class": "flagged",
                                   "on_stop": "end"}
    assert c["kregs"] == {"0x0a78": {"values": gen.VALUES}}
    assert c["srcversion"] == "7CE8E38EDB97FC5EA4F6C90" and c["prefix"] == "r31k"
    assert c["tools"]["t30"]["sha256"] == \
        "b5ea288d273f0da50884bbeec38f784a5d19773b8ed20efc7937dd455c1b87a5"
    assert "kreg" not in "".join(ln for ln in (KP / "tables/s0.txt").read_text().splitlines(True)
                                 if not ln.startswith("#"))
    for st in ("s0", "k1", "k2"):
        assert re.search(r"^#limit 0$", (KP / f"tables/{st}.txt").read_text(), re.M)


def test_the_k2_program_is_the_pinned_one():
    c = tomllib.loads((KP / "session.toml").read_text())
    assert "data:render/closing-s1b/bins/p1139-green.bin" in c["freeze"]["pins"]
    data = pathlib.Path(os.environ.get("RESGX545_DATA", pathlib.Path.home() / "src/resgx545-data"))
    r = subprocess.run(["git", "-C", str(data), "show",
                        f"{c['freeze']['data']}:render/closing-s1b/bins/p1139-green.bin"],
                       capture_output=True)
    if r.returncode:
        pytest.skip(f"the data commit is not in {data}")
    assert r.stdout == (KP / "bins/p1139-green.bin").read_bytes()


# ---- the readings: hooks and scorer alike ---------------------------------------------------
def tri_text(w, h, renders, diff=0):
    s = f"tri: render context for targets up to {w}x{h}\n"
    for i, t in enumerate(renders, 1):
        s += (f"job: ok\ntarget: {w}x{h} hash 0x0\ndiff: {diff} of {w * h} pixels\n"
              f"outside: 0 dwords\ntri {w}x{h} #{i}: 1 triangle, 0 background, 0 other; wrong 0 "
              f"inside, 0 outside, 0 at edges; 0 if flipped; guard 0\ntri {w}x{h} #{i}: {t} us\n")
    return s + f"tri: {len(renders)} renders ok\n"


def probe_text(renders, img=IMG, odd=None):
    s = "programs asm\n"
    for i, t in enumerate(renders):
        s += ("probe p1139-green: scratch at 0x3e00e000 (64 KiB)\n"
              "probe p1139-green: tri 64x64 (1500 vertices), pixel replaced\n"
              f"tri 64x64 #1: {t} us\nprobe p1139-green: {odd if odd and i == 3 else img}\n")
    return s


def hooks(tmp_path, text):
    (tmp_path / "x.out").write_text(text)
    r = subprocess.run(["bash", "-c", f'JW="{tmp_path}"; . "{KP}/run/hooks.sh"; hook_reading x; '
                        'echo "check:$(hook_check x)"'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


@pytest.mark.parametrize("renders", [[73400, 67000, 69000, 66000, 90000, 67500],
                                     [9, 5, 4, 3, 2, 1], [5, 7], [5, 7, 3, 3, 3, 3, 9]])
def test_hooks_and_scorer_read_the_same_median(tmp_path, renders):
    out = hooks(tmp_path, tri_text(256, 256, renders))
    want = S.median_low(renders[1:])
    assert f"us={want}\n" in out and "diff=0\n" in out, out
    assert S.reading(tri_text(256, 256, renders))["us"] == want
    out = hooks(tmp_path, probe_text(renders))
    assert f"us={want}\n" in out and "img=0\n" in out, out
    assert S.reading(probe_text(renders))["us"] == want


def test_the_median_ignores_one_and_two_slow_renders():
    assert S.median_low([67000, 67100, 67200, 74000, 83000]) == 67200
    # E1114's c11 (renders 2 and 3 slow): its mean read +3.04 percent, its median 67271 us
    c11 = [70807, 71090, 74071, 67271, 66885, 66636]
    assert S.reading(tri_text(256, 256, c11))["us"] == 67271


def test_the_hooks_stop_a_wedge_and_a_failed_probe_render_only(tmp_path):
    assert hooks(tmp_path, probe_text([2400] + [2000] * 5)).endswith("check:\n")
    out = hooks(tmp_path, probe_text([2400] * 5))
    assert "timed 5 renders, not 6" in out, out
    out = hooks(tmp_path, probe_text([2400] * 6) + "probe p1139-green: failed: job timed out\n")
    assert "has a failed render" in out, out
    out = hooks(tmp_path, probe_text([2400] * 6, odd="o0 0xff00ff00"))
    assert "img=1\n" in out and out.endswith("check:\n"), out
    out = hooks(tmp_path, tri_text(256, 256, [1] * 6, diff=3))
    assert "drew 18 wrong pixels" in out, out
    r = subprocess.run(["bash", "-c", f'JW="{tmp_path}"; . "{KP}/run/hooks.sh"; '
                        f'printf "%s" "$1" > "$JW/a.out"; printf "%s" "$2" > "$JW/b.out"; '
                        f'printf "%s" "$3" > "$JW/c.out"; hook_check a; hook_check b; '
                        'hook_check c', "_", probe_text([2000] * 6), tri_text(256, 256, [67000] * 6),
                        probe_text([4100] * 6)], capture_output=True, text=True)
    assert "c's render median 4100 us is above twice 2000 us" in r.stdout, r.stdout


# ---- kept records -------------------------------------------------------------------------
def kept(root, stage, times, image=lambda r: IMG):
    """A kept stage directory: every row of the table ok; a timed row's six renders `times(row)`;
    a k2/v row's o0 line `image(row)`; a 64x64 exact row one render."""
    d = root / stage
    d.mkdir(parents=True)
    rows = ""
    for r in K.table(str(KP), stage):
        if r["args"] == gen.TIMED1:
            txt = tri_text(256, 256, times(r))
        elif r["args"] == gen.TIMED2:
            txt = probe_text(times(r), image(r))
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


def flat(r):
    """Every timed row: L1 67400 us, L2 2000 us, s0's v1-v8 with an IQR of 0.2 percent."""
    if r["args"] == gen.TIMED2:
        m = re.fullmatch(r"v(\d)", r["name"])
        x = 2000 + (int(m[1]) % 3 - 1) * 2 if m else 2000
        return [2400] + [x] * 5
    return [73400] + [67400] * 5


def build(root, k1=flat, k2=flat, s0=flat, image=lambda r: IMG):
    kept(root, "s0", s0, image)
    kept(root, "k1", k1)
    kept(root, "k2", k2, image)


def run(*args):
    r = subprocess.run([PY, str(SCORE), *map(str, args)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def summary(out, st):
    return next(ln for ln in out.splitlines() if ln.startswith(f"SUMMARY: {st}: "))


def score(root, st):
    return run(st, root / st, root)


def test_flat_holds_both_loads_and_q024_retires(tmp_path):
    build(tmp_path)
    for st in ("k1", "k2"):
        s = summary(score(tmp_path, st), st)
        assert "(64 of 64 rows decided)" in s and "not supported" not in s, s
    assert "within 1.00 percent" in summary(score(tmp_path, "k2"), "k2")
    assert "s0's references draw and time (17 of 17" in summary(score(tmp_path, "s0"), "s0")
    assert "Q024: RETIRE" in run("q024", tmp_path)
    assert subprocess.run([PY, str(SCORE), "gate", "k2", tmp_path]).returncode == 0


def with_controls(base, devs):
    """times(row) with c-controls NAME moved by devs[NAME] percent (all renders 2-6)."""
    def times(r):
        if r["name"] in devs:
            b = base(r)
            return [b[0]] + [int(x * (1 + devs[r["name"]] / 100)) for x in b[1:]]
        return base(r)
    return times


@pytest.mark.parametrize("st", ["k1", "k2"])
def test_one_control_out_of_band_is_allowed_and_two_fail(tmp_path, st):
    kw = {st: with_controls(flat, {"c07": 3.0})}
    build(tmp_path / "x", **kw)
    out = score(tmp_path / "x", st)
    assert "(64 of 64 rows decided)" in summary(out, st), out
    assert "OUTLIERS: c07 (1 outside" in out and "the one allowed outlier" in out, out
    assert "Q024: RETIRE" in run("q024", tmp_path / "x")
    kw = {st: with_controls(flat, {"c07": 3.0, "c12": -2.0})}
    build(tmp_path / "y", **kw)
    out = score(tmp_path / "y", st)
    assert "controls FAILED" in summary(out, st) and "c07: FAILED" in out, out
    assert "Q024: NARROW" in run("q024", tmp_path / "y")


def test_a_control_that_draws_wrong_is_never_the_allowed_outlier(tmp_path):
    def image(r):
        return "o0 0xff00ff00" if r["name"] == "c05" else IMG
    build(tmp_path, image=image)
    s = summary(score(tmp_path, "k2"), "k2")
    assert s.startswith("SUMMARY: k2: controls FAILED: c05: FAILED"), s


def by_value(base, table):
    """times(row) from {value: (fit percent, held percent)} off base."""
    def times(r):
        v = value_of(r)
        b = base(r)
        if r["set"] in ("fit", "held") and v in table:
            p = table[v][r["set"] == "held"]
            return [b[0]] + [int(x * (1 + p / 100)) for x in b[1:]]
        return b
    return times


@pytest.mark.parametrize("st", ["k1", "k2"])
def test_a_value_out_on_both_passes_fails_and_out_on_its_fit_only_holds(tmp_path, st):
    build(tmp_path / "x", **{st: by_value(flat, {"0x01": (2.2, 2.2)})})
    out = score(tmp_path / "x", st)
    assert "is not supported" in summary(out, st) and re.search(r"ROW 0x01: .*FAILED", out), out
    assert "Q024: FINDING" in run("q024", tmp_path / "x")
    build(tmp_path / "y", **{st: by_value(flat, {"0x01": (2.2, 0.1), "0x02": (-3, 3)})})
    out = score(tmp_path / "y", st)
    assert "(64 of 64 rows decided)" in summary(out, st), out
    assert re.search(r"ROW 0x01: .*held \(fit pass outside", out), out


def test_the_controls_spread_is_a_premise(tmp_path):
    def spread(r):
        if r["set"] == "control" and value_of(r):
            return [73400] + [67400 + (300 if int(r["name"][1:]) % 2 else -300)] * 5
        return flat(r)
    build(tmp_path, k1=spread)
    s = summary(score(tmp_path, "k1"), "k1")
    assert s.startswith("SUMMARY: k1: cannot tell:") and "spread: cannot tell" in s, s


def test_k2_cannot_tell_when_s0_s_l2_references_are_too_noisy(tmp_path):
    def noisy(r):
        m = re.fullmatch(r"v(\d)", r["name"])
        if m:
            return [2400] + [2000 + 40 * (int(m[1]) % 4)] * 5
        return flat(r)
    build(tmp_path, s0=noisy)
    out = score(tmp_path, "k2")
    assert "CONTROL bound2: BOUND2" in out and "bound2: cannot tell" in summary(out, "k2"), out
    assert "Q024: NARROW (decided on k1 only)" in run("q024", tmp_path)


def test_k2_s_bound_widens_with_s0_s_spread_up_to_the_cap(tmp_path):
    def wider(r):
        m = re.fullmatch(r"v(\d)", r["name"])
        if m:
            return [2400] + [2000 + 6 * (int(m[1]) % 4)] * 5
        return flat(r)
    build(tmp_path, s0=wider)
    out = score(tmp_path, "s0")
    b2 = float(re.search(r"BOUND2 ([\d.]+) %", out)[1])
    assert gen.FLOOR2_PCT < b2 <= gen.CAP2_PCT, out
    assert f"within {b2:.2f} percent" in summary(score(tmp_path, "k2"), "k2")


def test_a_k2_value_drawing_another_image_is_cannot_tell_and_named(tmp_path):
    build(tmp_path, image=lambda r: "o0 0xff00ff00" if r["name"] == "b3f" else IMG)
    out = score(tmp_path, "k2")
    assert "IMAGE 0x3f: b3f drew another image" in out and "ROW 0x3f: " in out, out
    assert "63 of 64 rows decided" in summary(out, "k2"), out
    assert "Q024: NARROW" in run("q024", tmp_path)


def test_the_gates_need_their_own_load_s_references(tmp_path):
    build(tmp_path, image=lambda r: "o0 0xff00ff00" if r["name"] == "v4" else IMG)
    assert subprocess.run([PY, str(SCORE), "gate", "k1", tmp_path],
                          capture_output=True).returncode == 0
    assert subprocess.run([PY, str(SCORE), "gate", "k2", tmp_path],
                          capture_output=True).returncode == 1


# ---- E1114 (post hoc calibration: must hold) and E141 (must fail) ----------------------------
def e1114():
    """{r29-kreg row name: six renders} from E1114's fold/posthoc.txt at the pinned data commit."""
    c = tomllib.loads((KP / "session.toml").read_text())
    data = pathlib.Path(os.environ.get("RESGX545_DATA", pathlib.Path.home() / "src/resgx545-data"))
    r = subprocess.run(["git", "-C", str(data), "show",
                        f"{c['freeze']['data']}:render/closing-r29-kreg/fold/posthoc.txt"],
                       capture_output=True, text=True)
    if r.returncode:
        pytest.skip(f"E1114's posthoc.txt is not in {data}")
    out = {}
    for ln in r.stdout.splitlines():
        m = re.match(r"^\s*\d+ (\S+)\s+0x\w+\s+\d+\s+\S+((?: \d+){6})", ln)
        if m:
            out[m[1]] = [int(x) for x in m[2].split()]
        m = re.match(r"^s0 (r\d) \d+ \S+((?: \d+){6})", ln)
        if m:
            out[m[1]] = [int(x) for x in m[2].split()]
    assert len(out) == 152 and out["c11"] == [70807, 71090, 74071, 67271, 66885, 66636]
    return out


def e1114_times(runs):
    def times(r):
        if r["args"] != gen.TIMED1:
            return flat(r)
        if r["set"] in ("fit", "held"):
            return runs[r["name"]]
        return runs[r["name"]]          # c01-c16, r1-r8: E1114's own rows of the same names
    return times


def test_e1114_holds_under_the_frozen_rule_and_its_c11_reads_in_band(tmp_path):
    runs = e1114()
    t = e1114_times(runs)
    build(tmp_path, k1=t, s0=t)
    out = score(tmp_path, "k1")
    assert "(64 of 64 rows decided)" in summary(out, "k1") and "FAILED" not in out, out
    assert "OUTLIERS: none (0 outside" in out and re.search(r"CONTROL c11: .*us 67271.*PASS", out)
    # and the outlier rule alone would have carried E1114 too: c11 at its mean (+3.04 percent)
    runs2 = dict(runs, c11=[73400] + [69190] * 5)
    t2 = e1114_times(runs2)
    build(tmp_path / "m", k1=t2, s0=t2)
    out2 = score(tmp_path / "m", "k1")
    assert "OUTLIERS: c11 (1 outside" in out2 and "(64 of 64 rows decided)" in out2, out2
    far = float(re.search(r"FARTHEST: 0x\w+ ([\d.]+) %", out)[1])
    assert far < 1.0, out


def test_e141_s_slow_values_fail_on_both_passes(tmp_path):
    """E141's means: 0x01 70977 and 0x20 69038 us against 0x2c's 67288 (5.5 and 2.6 percent)."""
    runs = e1114()
    base = e1114_times(runs)
    t = by_value(base, {"0x01": (5.48, 5.48), "0x20": (2.6, 2.6)})
    build(tmp_path, k1=t, s0=base)
    out = score(tmp_path, "k1")
    assert "is not supported" in summary(out, "k1"), out
    assert re.search(r"ROW 0x01: .*FAILED", out) and re.search(r"ROW 0x20: .*FAILED", out), out
