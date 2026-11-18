# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer on synthetic kept directories (the mock's images, mock/world.py)
and on kept records. D2 (rank-round35.md section 1): every model name frozen in
predictions/*.tsv is printed held (a SUMMARY line "(N of N rows decided)", or a CONTROL PASS) in
one world and FAILED in another; the model world holds H-RZ, H-AS0, H-WHOLE, H-1136; the rn, rne,
scale worlds hold their rule; the alt world holds the rivals. D1: a FAILED form control makes its
mode's rows "cannot tell: form control" and closes every gate; a reference without its image
makes its rows cannot tell; the narrow rule reads NARROW with each clause decided or not."""
import os
import re
import subprocess
import sys

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "gen"), os.path.join(KP, "mock")]
sys.dont_write_bytecode = True
import pins  # noqa: E402
import pk as Q  # noqa: E402
import score as SC  # noqa: E402
import world as WD  # noqa: E402

COLS = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n"
WORLDS = ("model", "rn", "rne", "scale", "alt")


def out_of(img, scr, case="x"):
    t = "".join("probe %s: row %d: %s\n" % (case, y, " ".join("%08x" % v for v in img[64 * y:64 * y + 64]))
                for y in range(64))
    return t + "".join("probe %s: scratch +0x%03x 0x%08x\n" % (case, 4 * k, v)
                       for k, v in sorted(scr.items()))


def key(r):
    a = r["args"].split()
    form = "ramp" if "--vtx-coords" in a else "colour"
    return form, int(a[a.index("--sideband") + 1], 16) & 0x3F, \
        int(a[a.index("--cmd") + 1].split("=")[1], 16)


def kept_dir(att, stage, world, skip=(), override=None):
    d = os.path.join(att, stage)
    os.makedirs(d, exist_ok=True)
    cases, reads = [COLS], ["name\tstage\treading\n"]
    for r in SC.K.table(KP, stage):
        n = r["name"]
        cases.append("\t".join([n, stage, r["set"], r["risk"], " ".join(r["knobs"]), r["tool"],
                                r["args"], "0", "ok", "", "", "999999"]) + "\n")
        if n in skip:
            img, scr = None, {}
        elif override and n in override:
            img, scr = override[n], {}
        else:
            img, scr = WD.image(*key(r), world)
        with open(os.path.join(d, n + ".txt"), "w") as f:
            f.write("job: ok\n" + ("" if img is None else out_of(img, scr)))
        if r["set"] == "control":
            reads.append(f"{n}\t{stage}\tpixels={0 if img is None else 64}\n")
    for f, t in (("cases.tsv", cases), ("readings.tsv", reads), ("void.tsv", [COLS])):
        with open(os.path.join(d, f), "w") as fh:
            fh.write("".join(t))
    return d


def attempt(att, world, **kw):
    for s in SC.STAGES:
        kept_dir(att, s, world, **kw)
    return att


def printed(att):
    """The scorer's printed lines over every stage, as the runner calls it."""
    out = []
    for s in SC.STAGES:
        r = subprocess.run([sys.executable, os.path.join(KP, "score", "score.py"), s,
                            os.path.join(att, s), att], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        assert r.returncode == 0, r.stderr
        out += r.stdout.splitlines()
    return out


def frozen_names():
    names = set()
    for s in SC.STAGES:
        for ms in SC.K.predictions(KP, s).values():
            for m in ms.values():
                names |= set(m)
    return names


def states(lines):
    """{model: set of 'held'/'FAILED'} from SUMMARY and CONTROL lines."""
    out = {}
    for ln in lines:
        m = re.match(r"^SUMMARY: \w+: (H-[\w-]+)[^:]*?\((\d+) of (\d+) rows decided\)$", ln)
        if m and m.group(2) == m.group(3):
            out.setdefault(m.group(1), set()).add("held")
        m = re.match(r"^SUMMARY: \w+: (H-[\w-]+).* is not supported: .*FAILED", ln)
        if m:
            out.setdefault(m.group(1), set()).add("FAILED")
        m = re.match(r"^CONTROL \S+: (H-[\w-]+) .*: (PASS|FAILED)$", ln)
        if m:
            out.setdefault(m.group(1), set()).add("held" if m.group(2) == "PASS" else "FAILED")
    return out


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    out = {}
    for w in WORLDS + ("s0diff", "ctlfail"):
        att = str(tmp_path_factory.mktemp(w))
        out[w] = (att, printed(attempt(att, w)))
    return out


def test_every_frozen_name_is_produced_held_and_failed(runs):
    seen = {}
    for w, (_, lines) in runs.items():
        for m, st in states(lines).items():
            seen.setdefault(m, set()).update(st)
    names = frozen_names()
    assert names == {"H-RAMP", "H-E031", "H-E1136", "H-RZ", "H-RN", "H-RNE", "H-SCALE", "H-AS0",
                     "H-AS0-PART", "H-WHOLE", "H-NARROW", "H-1136", "H-LOWDEP"}
    for n in names:
        assert seen.get(n) == {"held", "FAILED"}, (n, seen.get(n))


@pytest.mark.parametrize("world,rule", [("model", "H-RZ"), ("rn", "H-RN"), ("rne", "H-RNE"),
                                        ("scale", "H-SCALE")])
def test_each_rule_world_holds_its_rule_only(runs, world, rule):
    att, lines = runs[world]
    for m in Q.NARROW:
        held = [r for r in Q.RULES if any(
            ln.startswith(f"SUMMARY: r1: {r} m{m:02d} (heldout) (2 of 2") for ln in lines)]
        assert held == [rule], (m, held)
    v, clauses, why = SC.narrow(att)
    assert v == "NARROW" and not why
    assert f"(d) RGB565: {rule} on every pixel of 2 rows" in clauses
    assert any(c.startswith("(a) ARGB8888-like: H-AS0 on 42 of 42") for c in clauses), clauses
    assert "(e) bit 25 with low bytes 0x40, 0xc0: H-1136 in modes 0, 4, 5, 6" in clauses


def test_alt_world_holds_the_rivals(runs):
    att, lines = runs["alt"]
    assert any(ln.startswith("SUMMARY: r2: H-AS0-PART (heldout) (40 of 40") for ln in lines)
    assert any(ln.startswith("ROW r2-m40 (heldout)") and ln.endswith("held H-AS0-PART")
               for ln in lines)
    assert any(ln.startswith("SUMMARY: r1: H-NARROW m09 (heldout) (2 of 2") for ln in lines)
    assert any(ln.startswith("SUMMARY: pw: H-NARROW m13 (heldout) (2 of 2") for ln in lines)
    assert any(ln.startswith("SUMMARY: r3: H-LOWDEP m05 (heldout) (4 of 4") for ln in lines)
    _, clauses, _ = SC.narrow(att)
    assert "(a) mode 9: H-NARROW on 2 rows" in clauses
    assert any(c.startswith("(e) bit 25 with low bytes 0x40, 0xc0: not decided") for c in clauses)


def test_failed_form_control_closes_gates(runs):
    att, lines = runs["s0diff"]
    assert any(ln.startswith("CONTROL s0-m04-col:") and ln.endswith("FAILED") for ln in lines)
    assert SC.gate_of("r1", [att])[0] is False
    rows = [ln for ln in lines if ln.startswith("ROW r1-m04-")]
    assert rows and all(ln.endswith("cannot tell: form control s0-m04-col") for ln in rows)
    assert all(not ln.endswith("form control s0-m04-col") for ln in lines
               if ln.startswith("ROW r1-m03-"))
    _, _, why = SC.narrow(att)
    assert any(w.startswith("s0 controls:") for w in why)


def test_reference_without_image_cannot_tell(tmp_path):
    att = attempt(str(tmp_path), "model", skip=("r2-m00-ref",))
    _, _, lines = SC.verdicts("r2", os.path.join(att, "r2"))
    assert any(ln.startswith("CONTROL r2-m00-ref") and ln.endswith("cannot tell") for ln in lines)
    row = [ln for ln in lines if ln.startswith("ROW r2-m16 ")][0]
    assert row.endswith("cannot tell"), row


def test_stage_ref_must_hold_its_construction(tmp_path):
    bad = list(WD.ramp())
    i = next(i for i, v in enumerate(bad) if v != Q.BG)
    bad[i] ^= 1
    att = attempt(str(tmp_path), "model", override={"r1-m00-ref": bad})
    c, _, _ = SC.verdicts("r1", os.path.join(att, "r1"))
    assert c["r1-m00-ref"] is False


def test_rules_on_e031_and_e385_fit():
    """D1 offline: each packer reproduces E031's kept colour images under H-RZ (the layout of
    modes 3 to 7); E385's mode 5 alpha ramp fits H-RZ only (the fit of the frozen rules)."""
    k031 = lambda m: Q.kept(pins.blob, Q.E031 % m, f"pbe-pack-modes-packmode-{m:02d}__0")  # noqa
    src = k031(0)
    for m in (3, 4, 5, 6, 7):
        assert Q.image16(src, m, Q.rz) == k031(m), m
    assert Q.image16(src, 6, Q.rn) != k031(6) and Q.image16(src, 6, Q.scale) == k031(6)
    m0 = Q.kept(pins.blob, Q.E385 % "mode0", "pbe-reg-0400-alpha-mode0__0")
    m5 = Q.kept(pins.blob, Q.E385 % "bit25-mode5", "pbe-reg-0400-alpha-bit25-mode5__0")
    fit = []
    for name, f in Q.RULES.items():
        ok = all(((m5[i // 2] >> (16 * (i % 2))) & 0xFFFF) >> 12 == f(m0[i] >> 24, 4)
                 for i in range(4096))
        fit.append(name) if ok else None
    assert fit == ["H-RZ"]
    for m in (9, 10, 12, 13):
        assert Q.whole(src, k031(m))[0] == "all", m
