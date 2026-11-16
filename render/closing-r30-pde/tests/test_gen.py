# SPDX-License-Identifier: MIT
"""tests/test_gen.py: gen/pde.py against the linux fork's KUnit values (branch r30-kernel
8bc0877e8603, sgx_mmu_large_test.c), every row inside the fork's safety windows, the plan's counts
(closing29/kernel/plan-kernel.md 2.3), the rival models telling each row apart, and the generated
files current."""
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import make as M  # noqa: E402
import pde as P  # noqa: E402

R0, V = 0x3C000000, 1
SZ_64K = 0x10000


def test_generated_files_are_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen", "make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_geometry_is_the_forks():
    order = (3, 4, 6, 8, 10, 10, 10, 10)
    for code in range(P.CODES):
        for lay in range(4):
            ok = (1 <= code <= 4) or (code in (0, 5) and lay <= P.PT4K) or lay == P.DENSE
            g = P.geom(code, lay)
            assert (g is not None) == ok, (code, lay)
            if g:
                assert g["order"] == order[code] and g["region"] == P.SZ_4K << order[code]
                assert g["region"] // g["unit"] <= 15 and g["unit"] // P.SZ_4K <= 1024
                assert P.SZ_4K <= g["trap_off"] < g["region"]
    assert P.geom(8, 0) is None and P.geom(1, 4) is None
    g = P.geom(2, P.DENSE)
    assert (g["size"], g["unit"], g["nblocks"], g["block_off"][0], g["block_off"][2],
            g["trap_off"], g["pt_off"]) == (SZ_64K, SZ_64K, 3, SZ_64K, 3 * SZ_64K, 3 * SZ_64K, 0)
    assert P.geom(2, P.MISALIGN)["nblocks"] == 2 and P.geom(2, P.PTOFF_L)["pt_off"] == 0x400
    g = P.geom(0, P.DENSE)
    assert (g["size"], g["block_off"][0], g["trap_off"]) == (P.SZ_4K, P.SZ_4K, 7 * P.SZ_4K)
    g = P.geom(5, P.DENSE)
    assert (g["nblocks"], g["block_off"][0], g["trap_off"]) == (1, 0, P.SZ_4M - P.SZ_4K)
    assert (P.geom(6, 0)["size"], P.geom(6, 0)["region"]) == (P.SZ_4M, P.SZ_4M)


def test_tables_are_the_forks():
    for code in range(1, 6):
        s = P.page_size(code)
        g = P.geom(code, P.DENSE)
        trap = R0 + g["trap_off"]
        pt = P.table(g, R0)
        assert P.pde(g, R0) == R0 | code << 1 | V
        assert pt == [(R0 + g["block_off"][i] if i < g["nblocks"] else trap) | V for i in range(1024)]
        g = P.geom(code, P.PT4K)
        pt = P.table(g, R0)
        for i in range(1024):
            k = i * P.SZ_4K // s
            assert pt[i] == ((R0 + g["block_off"][k] + i * P.SZ_4K % s) if k < g["nblocks"] else trap) | V
        if code == 5:
            assert P.geom(5, P.MISALIGN) is None and P.geom(5, P.PTOFF_L) is None
            continue
        pt = P.table(P.geom(code, P.MISALIGN), R0)
        assert pt[0] == (R0 + s + P.SZ_4K) | V and pt[1] == (R0 + 2 * s + P.SZ_4K) | V
        assert all(e == trap | V for e in pt[2:])
        g = P.geom(code, P.PTOFF_L)
        pt = P.table(g, R0)
        assert P.pde(g, R0) == R0 | 0x400 | code << 1 | V
        for i in range(1024):
            want = trap
            if i < 3:
                want = R0 + g["block_off"][(i + 1) % 3]
            elif 256 <= i < 259:
                want = R0 + g["block_off"][i - 256]
            assert pt[i] == want | V, (code, i)
    pt = P.table(P.geom(0, P.DENSE), R0)
    assert pt == [(R0 + (i + 1) * P.SZ_4K if i < 3 else R0 + 7 * P.SZ_4K) | V for i in range(1024)]
    g = P.geom(7, P.DENSE)
    pt = P.table(g, R0)
    assert P.pde(g, R0) == R0 | 0xF and pt[0] == (R0 + P.SZ_4K) | V
    assert all(pt[i] == (R0 + i * P.SZ_4K) | V for i in range(1, 1024))


def test_readings_are_the_forks():
    pt = [0] * 1024
    pde = 0x01000000 | 0x400 | 2 << 1 | V
    pt[0], pt[1], pt[2] = 0x02010000 | V, 0x02021000 | V, 0x02030000
    pt[256], pt[257], pt[17] = 0x02050000 | V, 0x02061000 | V, 0x02070000 | V
    f = P.phys
    assert f(P.RD_DENSE, SZ_64K, pde, pt, 0x1234) == 0x02011234
    assert f(P.RD_DENSE, SZ_64K, pde, pt, 0x11234) == 0x02021234
    assert f(P.RD_MASK4K, SZ_64K, pde, pt, 0x11234) == 0x02022234
    assert f(P.RD_4K, SZ_64K, pde, pt, 0x11234) == 0x02070234
    assert f(P.RD_SECTION, SZ_64K, pde, pt, 0x11234) == 0x01011234
    assert f(P.RD_DENSE | P.RD_PTOFF, SZ_64K, pde, pt, 0x11234) == 0x02061234
    assert f(P.RD_MASK4K | P.RD_PTOFF, SZ_64K, pde, pt, 0x11234) == 0x02062234
    assert f(P.RD_4K | P.RD_PTOFF, SZ_64K, pde, pt, 0x234) == 0x02050234
    assert f(P.RD_SECTION | P.RD_PTOFF, SZ_64K, pde, pt, 0x11234) == 0x01011634
    assert f(P.RD_DENSE, SZ_64K, pde, pt, 0x20000) == P.FAULT
    assert f(P.RD_4K | P.RD_PTOFF, SZ_64K, pde, pt, 0x300000) == P.OUTSIDE
    pt[0] = 0x02400000 | V
    assert f(P.RD_DENSE, P.SZ_4M, pde, pt, 0x3FF004) == 0x027FF004
    assert P.tag(3, 0x3FF, 0x3FF) == 0xA33FF3FF


def all_rows():
    return M.rows()


def test_every_row_stays_in_the_forks_safety_windows():
    """The part of a row's window in the large slot (offsets 0 to 4 MiB) lies in a window of the
    fork's KUnit safety case for its code, a fill in a writable one; and under every reading the
    safety case checks, each 4 KiB it reaches is in the region and a write never the table page
    (pde.union never yields x for a fill)."""
    for st, rs in all_rows().items():
        for r in rs:
            if r["g"] is None:
                continue
            a, b = max(r["va"][0], 0), min(r["va"][1], P.SZ_4M)
            if a >= b:
                assert r["name"] == "s0-warm"
                continue
            assert P.inside(r["g"]["code"], a, b, r["kind"] == "fill"), r["name"]
            u = P.union(r["g"], a, b)
            assert not u & {P.OUTSIDE, P.FAULT}, r["name"]
            if r["kind"] == "fill":
                assert "x" not in u, r["name"]


def test_the_plans_counts_and_words():
    rs = all_rows()
    assert {st: len(v) for st, v in rs.items()} == {"s0": 9, "f1": 9, "f2": 6, "f45": 8, "f67": 4}
    assert sum(M.LIMIT.values()) == 20 and M.LIMIT["s0"] == 0
    for st, v in rs.items():
        for r in v:
            w = r["knobs"].split()
            if st == "s0":
                assert "expectfault" not in w
            else:
                assert "expectfault" in w and "expectdiff" in w, r["name"]
            if r["g"] is not None and r["g"]["order"] == 10:
                assert "soft" in w, r["name"]           # an -ENOMEM voids the row, never a stop
    first = rs["s0"][0]
    assert first["name"] == "s0-warm" and first["g"]["order"] == 10    # right after the boot
    assert M.SLOT >= 0x60000000 and M.SLOT % P.SZ_4M == 0
    assert 0x3E000000 <= M.SLOT - P.SZ_4M and M.SLOT + 2 * P.SZ_4M <= 0xB0000000   # the general heap
    assert set(st for st in rs if st != "s0") == {"f1", "f2", "f45", "f67"}


def test_knob_words_are_declared():
    c = tomllib.load(open(os.path.join(KP, "session.toml"), "rb"))
    allowed = {f"dbg:{k}={v}" for k, d in c["knobs"].items() for v in d["values"]}
    for rs in all_rows().values():
        for r in rs:
            for w in r["knobs"].split():
                if w.startswith("dbg:"):
                    assert w in allowed, (r["name"], w)
    assert list(c["stages"]) == list(M.STAGES)
    assert all(c["stages"][s].get("class") == "flagged" and c["stages"][s].get("on_stop") == "end"
               and c["stages"][s].get("gate") for s in M.STAGES[1:])


def test_the_rivals_tell_every_flagged_row_apart():
    """On every flagged row, the frozen hypothesis and each rival predict different readings (so a
    held row decides), H-FAULT apart by its end. Code 5's one block is the region, whose first
    page is the table page, so H-DENSE and H-SECTION name the same 4 MiB there (by the fork's
    design): README.md says code 5 cannot tell them apart."""
    pairs = (("H-DENSE", "H-4K"), ("H-DENSE", "H-SECTION"), ("H-MASK-S", "H-MASK4K"),
             ("H-PTOFF-IGN", "H-PTOFF-USE"), ("H-ALIAS", "H-ALIAS16"))
    seen = set()
    for st, rs in all_rows().items():
        if st == "s0":
            continue
        for r in rs:
            p = r["pred"]
            for a, b in pairs:
                if a in p and b in p and not (r["name"].startswith("c5-") and b == "H-SECTION"):
                    assert p[a] != p[b], (r["name"], a, b)
                    seen.add((a, b))
            assert p["H-FAULT"] == {"end": "fault"}
    assert seen == set(pairs)


def test_tables_name_only_the_forms_the_mock_and_tool_take():
    pat = re.compile(r'^(copy --src-addr|fill --dst-addr) 0x[0-9a-f]+ --height (16|32|64) --large-copy "\$W"$')
    for st in M.STAGES:
        for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
            if ln and not ln.startswith("#"):
                assert pat.match(ln.split("|", 5)[5]), ln


def test_a_freeze_never_names_the_t30_placeholder():
    """t30's sha256 is the laptop build's (lead/finish_freeze.sh); 0 x 64 only before the freeze."""
    c = tomllib.load(open(os.path.join(KP, "session.toml"), "rb"))
    sha = c["tools"]["t30"]["sha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", sha)
    if os.path.exists(os.path.join(KP, "FROZEN.sha256")):
        assert sha != "0" * 64, "frozen with the t30 placeholder: re-scaffold"
        built = open(os.path.join(KP, "lead", "TOOL30.built")).read().split()
        assert built[0] == sha and built[1:3] == ["built", c["freeze"]["resgx545"]]
