# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current, reads only pinned files, and its rows can part
their rivals: dcmp's frozen counts are the plan's table (closing10/rank/dcmp_table.out, the rows it
keeps), zov's plane gives every pixel of every tile area its own float32 and the overlap rivals
part, zbits/isp0x's frozen hashes and lines are E977's kept outputs, sb's and win0's rivals part on
every held-out row, the controls' kept images are whole."""
import gzip
import os
import struct
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import probes as P  # noqa: E402
import z as Z  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def preds(stage):
    out = {}
    for ln in open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        f = ln.split("\t")
        out.setdefault(f[0], {}).setdefault(f[1], {})[f[3]] = f[2]
    return out


def test_generator_current_and_pins_declared():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run([sys.executable, "-B", "-c",
                        "import sys; sys.path.insert(0, 'gen'); import make, pins; make.build(); "
                        "print('\\n'.join(sorted(pins.READ)))"], capture_output=True, text=True, cwd=KP)
    assert r.returncode == 0, r.stderr
    assert set(r.stdout.split()) <= set(CFG["freeze"]["pins"])


def test_dcmp_counts_are_the_plan_table():
    plan = {}
    for ln in """eq-m0 0;eq-m1 0;eq-m2 2048;eq-m3 2048;eq-m4 0;eq-m5 0;eq-m6 2048;eq-m7 2048;
up1-m2 0;up1-m3 2048;up1-m5 2048;up1-m6 0;dn1-m2 0;dn1-m3 0;dn1-m5 2048;dn1-m6 2048""".split(";"):
        n, v = ln.split()
        plan[n] = {"H-GL": v}
    # dcmp_table.out: H-UBITS | H-ABS | H-IEEE | H-CLAMP0
    for ln in """nan-m2 0 0 0 0;nan-m3 2048 2048 0 0;nan-m5 2048 2048 2048 2048;nan-m6 0 0 0 0;
neg25-m1 2048 0 0 0;neg25-m4 0 2048 2048 2048;neg75-m1 2048 2048 0 0;neg75-m4 0 0 2048 2048;
z0-neg25-m1 2048 2048 0 0;z0-neg25-m2 0 0 0 2048;z0-neg25-m4 0 0 2048 0;z0-negz-m1 2048 0 0 0;
z0-negz-m2 0 2048 2048 2048;z0-negz-m4 0 0 0 0""".split(";"):
        n, *v = ln.split()
        plan[n] = dict(zip(("H-UBITS", "H-ABS", "H-IEEE", "H-CLAMP0"), v))
    plan["z243-ctl"] = {"H-E467": "2048"}
    got = {n: q["drawn"] for n, q in preds("dcmp").items()}
    assert got == plan


def plane_f32(w, h):
    """float32 of the zov plane at every pixel centre of the target (whole tiles)."""
    sx, sy = Z.zx(h) / (2 * w), 1 / (2 * h)
    f = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]
    return {(x, y): f(sx * (x + 0.5) + sy * (y + 0.5)) for y in range(h) for x in range(w)}


def test_zov_plane_distinct_and_rivals_part():
    for w, h, g in Z.ZOV:
        p = plane_f32(w, h)
        assert len(set(p.values())) == w * h and max(p.values()) < 1
        # the rivals part on every overlapping job: some slot has two tiles
        o = {m: Z.owners(w, h, g, m) for m in Z.ZOV_MODELS}
        assert o["H-LATE/HDR"] != o["H-EARLY/HDR"] and o["H-LATE/RASTER"] != o["H-EARLY/RASTER"]
        if (w, h) in ((160, 48), (256, 64)):        # a second macrotile column: the orders part
            assert o["H-LATE/HDR"] != o["H-LATE/RASTER"]
        else:
            assert o["H-LATE/HDR"] == o["H-LATE/RASTER"]
    # the header order: macrotile columns outer (sgx-pipe ta.rs headers: at(m, i) = (m / n) * fx)
    assert Z.header_rank(160, 48)[(4, 0)] > Z.header_rank(160, 48)[(0, 2)]
    assert "(m / t.n) * fx + i % fx" in pins.blob("resgx545:crates/sgx-pipe/src/ta.rs").decode()


def test_zov_predict_on_a_synthetic_dump():
    w, h, g = 160, 48, 2
    tx, ty = Z.tiles(w, h)
    full = [0x3E000000 + i for i in range(512 * tx * ty)]
    for m in Z.ZOV_MODELS:
        pred = Z.zov_predict(full, w, h, g, m)
        assert len(pred) == 512 * len(Z.owners(w, h, g, m))
        assert max(pred) < 512 * ((ty - 1) * (g + 1) + tx)


def test_bits_frozen_values_are_e977():
    for job, hsh in (("z242-c-f0", Z.HASH_C), ("z242-c-f1", Z.HASH_C), ("z242-c-f2", Z.HASH_C),
                     ("z243-ctl", Z.HASH_L)):
        text = gzip.decompress(pins.blob(f"data:{Z.KEPT}/{job}.txt.gz")).decode()
        assert f"hash {hsh}" in text
    p = preds("zbits")
    assert p["zb-all-load"]["store_line"]["H-INERT"].startswith(
        "depth store #1: 18432 dwords, 2048 changed, 2 distinct")
    assert p["zb-b0-f0"]["drawn"] == {"H-E665": "0", "H-INERT": "3200"}
    assert p["zb-ctl-f0"]["depth.1.bin"]["H-INERT"] == preds("isp0x")["x-ctl"]["depth.1.bin"]["H-NULL"]


def image(stage, name, model):
    return open(os.path.join(KP, "predictions", stage, f"{name}.{model}.txt")).read().split()


def test_probe_rivals_part_and_controls_whole():
    for stage, models in (("sb", ("H-LOW16", "H-M7")), ("win0", P.WIN_MODELS)):
        for n, q in preds(stage).items():
            if n.startswith(("sb-ctl", "w0-ctl")):
                (m,) = q["pixels"]
                assert len(set(image(stage, n, m))) > 1
                continue
            ims = [tuple(image(stage, n, m)) for m in models]
            if stage == "sb" and "-f0-" not in n:
                assert ims[0] == ims[1]               # mode 7's field 1 is the low half: a tie
            elif stage == "sb":
                assert ims[0] != ims[1], n
    # win0: the x and y jobs of one configuration together part H-IDENT from H-WIN (b31 moves x,
    # b30 y), and H-IDENT from H-IDFULL wherever the region model leaves holes (none at 64 x 64
    # under 0x60000000 and 0xa0000000: E953's tri-full holes are the seam's)
    p = preds("win0")
    for n in p:
        if n.startswith("w0-ctl") or not n.endswith("-x"):
            continue
        y = n[:-1] + "y"
        im = {m: (tuple(image("win0", n, m)), tuple(image("win0", y, m))) for m in P.WIN_MODELS}
        assert im["H-IDENT"] != im["H-WIN"], n
        holes = sum(v == "%08x" % P.BG for v in im["H-IDENT"][0])
        assert (im["H-IDENT"] != im["H-IDFULL"]) == (holes > 0), n
        assert holes > 0 or n in ("w0-te60-64x64-x", "w0-tea0-64x64-x")
    for name in ("A-m1-tee0-64x64-x", "A-m0-te20-64x64-x"):
        im = P.case_images(gzip.decompress(pins.blob(f"data:{P.E502}/{name}.txt.gz")).decode())
        assert [len(v) for v in im.values()] == [4096]


def test_win0_model_is_e953s_on_the_control_geometry():
    """H-IDENT's mode-1 image of the E502 control's geometry holds E502's kept image (the region
    model's holes and E502's offsets, mode 1's doubling): the decode the win0 rows rely on."""
    M = pins.module("data:texture/p1141/recompute/msaa_model.py")
    kept = P.case_images(gzip.decompress(pins.blob(f"data:{P.E502}/A-m1-tee0-64x64-x.txt.gz")).decode())
    (im,) = kept.values()
    drawn = M.predict(M.tri_full(64, 64), 64, 64, 1, 0xE0000000)
    want = [P.f32bits(drawn[(x, y)][0] + 0.375) if (x, y) in drawn else P.BG
            for y in range(64) for x in range(64)]
    assert sum(a == b for a, b in zip(im, want)) == 4096
