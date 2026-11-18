# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing29/plan/rank-round35.md 3.1, as
README.md "Deviations" adapts it): one safe stage `o` of 32 t10 jobs; every probe row E417's
argv form (--temps 32 --pixels --tri pixel, a 128 x 128 context) at 64 or 128; A' rows with the
pixpds (12 data dwords) and vtxuse slots and --vtx-coords 2 and nothing else does; the first row
an A' (D4: never a reader); every P row after its group's A' (h5: after the fill) with noreset but
h4's (a reset); the group order of replicate b reversed; no forbidden option, no knob, no kreg."""
import os
import shlex
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import make as M  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
HEAD = ["probe", "--temps", "32", "--pixels", "--tri", "pixel"]


def rows():
    out = []
    for ln in open(os.path.join(KP, "tables", "o.txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, risk, knobs, tool, args = ln.rstrip("\n").split("|", 5)
            out.append(dict(name=name, set=st, risk=risk, knobs=knobs.split(), tool=tool,
                            args=args, a=shlex.split(args)))
    return out


def test_session():
    assert list(CFG["stages"]) == ["o"]
    assert CFG["stages"]["o"].get("on_stop") == "end"
    assert CFG["stages"]["o"].get("class", "safe") == "safe"
    assert CFG["tools"].keys() == {"t10"} and CFG["health_tool"] == "t10"
    assert CFG["tools"]["t10"]["sha256"].startswith("9bedc2d6")
    assert CFG["tools"]["t10"]["source"].startswith("a581c06bb24d")
    assert CFG["prefix"] == "r35q" and CFG["name"] == "r35-o0b"
    assert CFG["srcversion"] == "7CE8E38EDB97FC5EA4F6C90" and CFG["host_key_alias"] == "cedar"
    assert not CFG["knobs"] and not CFG["kregs"]
    assert CFG["freeze"]["resgx545"].startswith("204501aac415")
    assert CFG["freeze"]["data"].startswith("1e400772bca8")
    head = open(os.path.join(KP, "tables", "o.txt")).read().splitlines()[:2]
    assert head == ["#stage o", "#limit 0"]


def test_rows_and_counts():
    r = rows()
    assert len(r) == 32
    kinds = [x["a"][-1].split("/")[-1] if x["a"][0] == "probe" else "fill" for x in r]
    assert kinds.count("a.bin") == 14 and kinds.count("p.bin") == 14
    assert kinds.count("k.bin") == 2 and kinds.count("fill") == 2
    assert r[0]["name"] == "c0a-a64" and kinds[0] == "a.bin" and "noreset" not in r[0]["knobs"]
    for x in r:
        assert x["tool"] == "t10" and x["risk"] == "safe", x
        assert not [k for k in x["knobs"] if k.startswith(("dbg:", "kreg:", "expect", "idle:"))]
        assert not set(x["a"]) & set(CFG["forbid_options"]), x
        if x["a"] == ["fill"]:
            assert x["set"] == "between" and x["knobs"] == ["noreset"]
            continue
        a = x["a"]
        assert a[:len(HEAD)] == HEAD, x
        n = a[a.index("--width") + 1]
        assert n in ("64", "128") and a[a.index("--height") + 1] == n
        assert a[a.index("--max-width") + 1] == "128" and a[a.index("--max-height") + 1] == "128"
        if a[-1].endswith("/a.bin"):
            assert a[a.index("--vtx-coords") + 1] == "2"
            assert [a[i + 1] for i, t in enumerate(a) if t == "--slot"] == [
                "pixpds=$S/bins/pds_iter_xy.bin:12", "vtxuse=$S/bins/vtx_coords.bin"]
            assert x["set"] == "control" and x["knobs"] == ["reads:pixels"]
        else:
            assert "--slot" not in a and "--vtx-coords" not in a
        if x["set"] == "control":
            assert "reads:pixels" in x["knobs"]


def test_groups_follow_the_plan():
    r = rows()
    names = [x["name"] for x in r]
    groups = []
    for n in names:
        g = n.split("-")[0]
        if not groups or groups[-1] != g:
            groups.append(g)
    assert groups == ["c0a", "c1a", "h1a", "h2a", "h3a", "h4a", "h5a",
                      "h5b", "h4b", "h3b", "h2b", "h1b", "c1b", "h1c", "h1d"]
    size = {"h1": (64, 64), "h2": (128, 64), "h3": (64, 128), "h4": (64, 64), "h5": (64, 64)}
    for i, x in enumerate(r):
        g = x["name"][:2]
        if not x["a"][-1].endswith("/p.bin"):
            continue
        a_row = r[i - 2] if g == "h5" else r[i - 1]
        assert a_row["a"][-1].endswith("/a.bin" if g != "c1" else "/k.bin"), x["name"]
        assert a_row["name"].split("-")[0] == x["name"].split("-")[0]
        if g == "h5":
            assert r[i - 1]["a"] == ["fill"]
        if g in size:
            w_a = int(a_row["a"][a_row["a"].index("--width") + 1])
            w_p = int(x["a"][x["a"].index("--width") + 1])
            assert (w_a, w_p) == size[g], x["name"]
        assert x["knobs"][0] == ("-" if g == "h4" else "noreset"), x["name"]
        want = "control" if g == "c1" else "heldout"
        assert x["set"] == want, x["name"]
    assert not [x["name"] for x in r if x["set"] == "fit"]          # the fit is r35-o0 (E1143)


def test_bins():
    for b in ("a", "k", "p", "pds_iter_xy", "vtx_coords"):
        assert os.path.getsize(os.path.join(KP, "bins", b + ".bin")) % 8 == 0
    assert CFG["files"]["laptop"] == ["bins/*.bin"]
    assert sorted(os.listdir(os.path.join(KP, "bins"))) == [
        "a.bin", "k.bin", "p.bin", "pds_iter_xy.bin", "vtx_coords.bin"]
    assert M.A_BODY[-1] == "mov.skipinv.end o0, r0"
