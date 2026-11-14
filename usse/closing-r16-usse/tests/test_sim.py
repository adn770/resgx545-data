# SPDX-License-Identifier: MIT
"""tests/test_sim.py: the frozen predictor, replayed on the kept readbacks before the freeze (the
plan's premise check for r16-usse).

1. sgx-sim of the pinned commit replays every kept vector file the session leans on (E521's
   iaddu32 values, E498's iaddu32 tests, E499's rawcond and rawcond2, E529's rawjoin-o tables,
   E530's rawchan-1 to -7): every case matches, none unsupported.
2. gen/rule.py's H-RULE (the predictions' rule) gives every kept raw test case of those tables
   (the test word's field, join and chan on the sim's channel classes of the pair): 1152 of 1152
   (90 + 450 + 90 + 270 + 7 x 36).
3. Each row's program, with every raw field written as the field of the same two parts, runs on
   the sim to exactly H-RULE's tests and H-SIM's values (the a join rows, the controls and or #7
   with the o join); the o join on the other forms and the write masks are what the sim refuses as
   not run, and nothing else stops it: the frozen prediction there is the sim's rule carried over.
4. The uadd rows run on the sim to H-ZX (H-E521 and H-E498 on the controls).
5. Every held-out row tells H-RULE (H-ZX) from each of its rivals in at least one dword, and the
   controls' kept tables equal H-RULE."""
import os
import sys

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import progs  # noqa: E402
import rule as R  # noqa: E402
import sim  # noqa: E402


@pytest.mark.parametrize("pin", progs.REPLAYS)
def test_sim_replays_the_kept_vectors(pin):
    match, unsupported, mismatch = sim.replay(pin)
    assert (unsupported, mismatch) == (0, 0) and match > 0, (pin, match, unsupported, mismatch)


def _form(pin):
    base = os.path.basename(pin)
    src2 = "#7" if ("-imm" in base or "and7" in base) else "r2"
    for op in ("and", "or", "xor", "rol"):
        if f"-{op}-" in base or base.endswith(f"-{op}.vec.json") or f"-{op}7-" in base:
            return op, src2
    return "and", src2


def test_rule_on_the_kept_tests():
    n = hit = 0
    for pin in progs.REPLAYS:
        if "/raw" not in pin:
            continue
        op, src2 = _form(pin)
        for w, a, b, o0 in progs.kept_cases(pin):
            f, join, c = R.fields_of(w)
            cls = sim.classes(op, src2, a, b)
            n += 1
            hit += R.predicate(f, join, c, cls) == bool(o0)
    assert (hit, n) == (1152, 1152)


@pytest.mark.parametrize("name", progs.TROWS)
def test_utest_twin_on_the_sim(name):
    j = progs.utest_job(name)
    r = sim.run(progs.utest_job(name, canonical=True)["text"])
    if not r.ok:
        assert j["join"] == "o" and j["op"] not in ("and", "or", "xor"), (name, r.why)
        assert "with the join o (not run, E529)" in r.why, r.why
        return
    want = dict(j["preds"]["tests"]["H-RULE"])
    want.update(j["preds"]["values"]["H-SIM"])
    assert r.scratch == want


@pytest.mark.parametrize("name", progs.UROWS + progs.RROWS)
def test_uadd_on_the_sim(name):
    j = progs.uadd_job(name)
    r = sim.run(j["text"])
    p = j["preds"]["dwords"]
    if name.startswith("u-rpt"):
        assert not r.ok and "write mask" in r.why and "on test" in r.why, r.why
        return
    assert r.ok, r.why
    assert r.scratch == p[next(m for m in ("H-E521", "H-E498", "H-ZX") if m in p)]


def test_rivals_separate():
    for n in progs.TROWS:
        t = progs.utest_job(n)["preds"]["tests"]
        if n.startswith("t-ctl"):
            assert t["H-RULE"] == t["H-E499" if n.endswith("-a") else "H-E529"], n
            continue
        for m, p in t.items():
            if m != "H-RULE":
                assert p != t["H-RULE"], (n, m)
    for n in progs.UROWS[2:] + progs.RROWS[1:]:
        d = progs.uadd_job(n)["preds"]["dwords"]
        zx = d.get("H-ZX", d.get("H-ZX-ADV"))
        for m, p in d.items():
            if p is not zx:
                assert sum(p[k] != zx[k] for k in zx) >= 3, (n, m)
