# SPDX-License-Identifier: MIT
"""r19-k0: the generated tables and predictions are gen/plan.py's; each k0 row is its kept twin's
argv (r13-dpm pr2, r10-dpm a0-cal-2048 on t10 for rgn4, r13-zls zb-c-ctl); the f0 rows are the
plan's cells (rank-round19.md 2b, f0-down at N 0x30, README.md); the mock's constants are the
plan's."""
import shlex
import shutil

from common import KP, pin, table
import plan as PL


def test_generated_current(tmp_path):
    for d in ("tables", "predictions"):
        (tmp_path / d).mkdir()
    PL.write(str(tmp_path))
    for st in PL.STAGES:
        for d, ext in (("tables", "txt"), ("predictions", "tsv")):
            assert (tmp_path / d / f"{st}.{ext}").read_text() == (KP / d / f"{st}.{ext}").read_text()


def test_mock_constants():
    import world
    assert (world.RT, world.D_OFF, world.RAISE) == (PL.RT, PL.D_OFF, PL.RAISE)


def twin(path, name):
    for ln in pin(path).decode().splitlines():
        if ln.startswith(name + "|"):
            return ln.split("|", 5)
    raise AssertionError(name)


def after_tool(args):
    a = shlex.split(args)
    i = next(k for k, x in enumerate(a) if x.startswith("$HOME/sgxfive-test"))
    return a[i + 1:]


def test_k0_twins():
    k0 = {**table("k0"), **table("kg")}
    assert len(table("k0")) == 6 and len(table("kg")) == 4
    pr = twin("render/closing-r13-dpm/tables/pr2.txt", "pr2-c1-1")
    pr4 = twin("render/closing-r13-dpm/tables/pr2.txt", "pr2-c4-1")
    a0 = twin("render/closing-r10-dpm/tables/s6rep.txt", "a0-cal-2048")
    z = twin("render/closing-r13-zls/tables/zbase.txt", "zb-c-ctl")
    for n in ("k0-pr1-1", "k0-pr1-2"):
        assert after_tool(k0[n]["args"]) == after_tool(pr[5])
        assert "dbg:render_pb_pages=0x2b6" in k0[n]["knobs"] and "0x2b6" in pr[3]
    assert after_tool(k0["k0-pr4"]["args"]) == after_tool(pr4[5])
    assert "dbg:render_pb_pages=0xe2" in k0["k0-pr4"]["knobs"] and "0xe2" in pr4[3]
    assert after_tool(k0["k0-a0"]["args"]) == after_tool(a0[5])
    assert "dbg:render_pb_pages=0x162" in k0["k0-a0"]["knobs"] and "0x162" in a0[3]
    for n in ("k0-z-t10", "k0-z-t18b"):
        assert shlex.split(k0[n]["args"]) == shlex.split(z[5])
    # the timeline registers: r13-dpm's set and 0x0620, 0x0668 more
    def offs(spec):
        out = set()
        for part in spec.split(","):
            lo, _, hi = part.partition("-")
            out |= set(range(int(lo, 0), int(hi or lo, 0) + 4, 4))
        return out
    assert offs(PL.RT) - offs(shlex.split(pr[5])[2]) == {0x620, 0x668}
    assert offs(shlex.split(pr[5])[2]) <= offs(PL.RT)
    for n, r in k0.items():
        assert "--final-pb-pages" not in r["args"]
        assert r["tool"] in ("rt", "t10", "t18b")
        if "-t18b" in r["args"] or r["tool"] == "t18b":
            assert n.startswith(("k0-geo-t18b", "k0-z-t18b"))


def test_f0_cells():
    f0 = table("f0")
    assert len(f0) == 12
    want = {"f0-same": (0x422, 0x200), "f0-up": (0x28, 0x100), "f0-up-h1": (0x30, 0x60),
            "f0-up-h2": (0x24, 0x422), "f0-back": (0x28, 0x100), "f0-down": (0x100, 0x30)}
    for n, r in f0.items():
        p, nn = want[n.rsplit("-", 1)[0]]
        a = shlex.split(r["args"])
        assert f"dbg:render_pb_pages={p:#x}" in r["knobs"].split()
        assert a[a.index("--final-pb-pages") + 1] == f"{nn:#x}"
        assert a[a.index("--geometry") + 1] == "1"
        assert a[a.index("-n") + 1] == ("3" if n.startswith("f0-back") else "2")
        assert "$HOME/sgxfive-test-t18b" in a and r["tool"] == "rt"
        for o in ("--keep-going", "--keep-overflow", "--dump-each", "--words", "--regs"):
            assert o in a
        assert "expectdiff" in r["knobs"].split()
    names = list(f0)
    assert names[-2:] == ["f0-down-1", "f0-down-2"]
    for n in names[-2:]:
        assert {"soft", "stop:jobfail"} <= set(f0[n]["knobs"].split()) and f0[n]["risk"] == "medium"
    assert all(f0[n]["risk"] == "safe" for n in names[:-2])
    assert [n for n in names if f0[n]["set"] == "control"] == ["f0-same-1", "f0-up-1", "f0-same-2",
                                                               "f0-up-2"]


def test_fixtures_are_the_pins():
    for f in ("param", "tadata"):
        assert (KP / f"mock/fixtures/a0-cal-2048.p1139-green.{f}.bin.gz").read_bytes() == \
            pin(f"render/closing-r10-dpm/out/20261113-102513/s6rep/a0-cal-2048.p1139-green.{f}.bin.gz",
                raw=True)


def test_recipe_copy():
    """lead/build_tool18b.sh is round 18's recipe byte for byte (its first publication)."""
    src = KP.parent.parent.parent / "closing18" / "k18" / "build_tool18b.sh"
    if src.exists():
        assert (KP / "lead" / "build_tool18b.sh").read_bytes() == src.read_bytes()
    assert shutil.which("bash")
