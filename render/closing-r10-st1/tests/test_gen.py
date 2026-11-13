# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r10-st1's generator is current; every row carries the flags its premise
needs (E934: --isp2 only with --depth --stencil --stencil-store, tool t10) and the ISP word 2
fields of the plan; the tool puts --isp2 in the state block with ISP word 0's bit 8 and reference
0 (render.c, pinned); the rivals part on the rows; the q071 rows differ from their base rows only
by the control's inert bits; the edge rows' pages hold every buffer; t10's recipe is bound."""
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import st1 as S  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def rows():
    return [ln.rstrip("\n").split("|", 5) for ln in open(os.path.join(KP, "tables/st1.txt"))
            if ln.strip() and not ln.startswith("#")]


def opts(args):
    a = args.split()
    o = {}
    for i, x in enumerate(a):
        if x.startswith("--"):
            o[x] = a[i + 1] if i + 1 < len(a) and not a[i + 1].startswith("--") else True
    return o


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_rows_premises():
    rs = rows()
    assert len(rs) == 18 and list(CFG["stages"]) == ["st1"]
    head = open(os.path.join(KP, "tables/st1.txt")).read().splitlines()[:2]
    assert head == ["#stage st1", "#limit 0"]
    for name, st, risk, knobs, tool, args in rs:
        o = opts(args)
        w, h, fill, mode, m, base, ctl = S.ROWS[name]
        assert tool == "t10" and risk == "safe" and "expectdiff" in knobs.split()
        assert (st == "control") == ("reads:drawn" in knobs) == (name in S.CONTROL_DRAWN)
        assert o["--depth"] is True and o["--stencil"] is True and o["--stencil-store"] is True
        assert o["--pixels"] is True and o["--depth-dump"] == '"$W"' and o["--tri-full"] is True
        assert o["--stencil-fill"] == fill and int(o["--width"]) == w and int(o["--height"]) == h
        c = int(o["--depth-ctl"], 16)
        assert c & 0x6002 == 0x2002 and c >> 24 & 7 == 0 and (c >> 3 & 0x1FF) == 1   # load, f0, G 1
        assert c == (S.CTL if base is None else (S.CTL & ~S.CLR_BITS) | S.SET_BITS)
        if mode is None:
            assert "--isp2" not in o
        else:
            v = int(o["--isp2"], 16)
            assert v >> 25 & 7 == mode and v >> 22 & 7 == 0 and v >> 16 & 7 == 5   # SOP1 keep, SOP3 invert
            assert v >> 8 & 0xFF == m and v & 0xFF == 0xFF and v >> 28 == 0
        if (w, h) != (64, 32):
            tx, ty = S.tiles(w, h)
            assert int(o["--depth-pages"]) * 4096 >= 2048 * tx * ty      # every tile, each buffer
        else:
            assert "--depth-pages" not in o
        for bad in ("--kpoke-render", "--poke", "--kpoke"):
            assert bad not in o


def test_q071_rows_are_their_base_rows_with_the_inert_bits():
    t = {r[0]: r[5] for r in rows()}
    for n in ("q071-b0", "q071-l1"):
        base = S.ROWS[n][5]
        ctl = S.ROWS[n][6]
        assert t[n] == t[base].replace(f"--depth-ctl {S.CTL:#010x}", f"--depth-ctl {ctl:#010x}")
        assert ctl ^ S.CTL == 0xF8F19000 and not ctl & 0x00111000     # 15, 21-23, 27-31 set; 12, 16, 20 clear


def test_render_puts_isp2_with_bit_8_and_reference_0():
    src = pins.blob("resgx545:userspace/libsgxfive/src/render.c").decode()
    assert "blk[i++] = 0x01d00200;\t\t/* isp0 */" in src and "blk[1] |= 1u << 8;" in src
    assert "blk[3] = p->isp2;" in src
    tool = pins.blob("resgx545:userspace/libsgxfive/tools/sgxfive-test.c")
    import hashlib
    assert hashlib.sha256(tool).hexdigest() == CFG["tools"]["t10"]["source_sha256"]


def test_rivals_part():
    names = [n for n in S.ROWS if n not in S.CONTROL_DRAWN and not S.ROWS[n][5]]
    for i, a in enumerate(S.MODELS):
        for b in S.MODELS[i + 1:]:
            assert any(S.predict(n, a)[0] != S.predict(n, b)[0] for n in names), (a, b)
    # the bytes rows read each of j's eight low bits: H-DEPTHORD's j mod 256 is decoded per pixel
    for x in range(32):
        for y in range(16):
            bits = sum((x, y) not in S.predict(f"st1-b{k}", "H-DEPTHORD")[0] and 1 << k for k in range(8))
            assert bits == S.in_tile_index(x, y) & 0xFF


def test_in_tile_order_is_zls_rs():
    rs = pins.blob("resgx545:crates/sgx-pipe/src/zls.rs").decode()
    assert "fn in_tile_order_is_y0_x0_y1_x1_y2_x2_y3_x3_x4" in rs
    assert sorted(S.in_tile_index(x, y) for y in range(16) for x in range(32)) == list(range(512))


def test_control_word_is_e978s():
    e978 = pins.blob("data:render/closing-r9-x/tables/zst.txt").decode()
    assert f"--depth-ctl {S.CTL:#010x}" in e978


def test_recipe_is_bound():
    t = CFG["tools"]["t10"]
    assert t["recipe"] == "data:render/closing-r10-st1/lead/build_tool10.sh"
    assert t["sha256"] == "9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb"
    src = open(os.path.join(KP, "lead/build_tool10.sh")).read()
    assert f"SRCSHA={t['built_sha256']}" in src
    assert "COMMIT=a581c06bb24d2f77e03d9b64f7ca1b2d5487b59f" in src
    assert t["built_from"] == "a581c06bb24d2f77e03d9b64f7ca1b2d5487b59f:userspace/libsgxfive/tools/sgxfive-test.c"
