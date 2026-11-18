# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current and reads only pinned files; the bins are the
published programs byte for byte and bins/ramp_xy.bin is src/ramp_xy.s assembled; the ramp's
premises: E382's kept xy image gives pa0 = x + 0.5 and pa1 = y + 0.5 on each of the 1062
triangle pixels (the triangle every row draws), the ramp's colours are unique and every byte lane
takes all 256 values on them, and sgx-sim runs the program to ramp_word (when built); the frozen
controls are what their sources say (s0-m04-ramp's split 127/128, E031's kept images)."""
import collections
import hashlib
import os
import subprocess
import sys
import tomllib

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import pk as Q  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
B = pins.blob
SIM = os.path.join(pins.MAIN, "target", "release", "sgx-sim")


def test_generated_current_and_pins():
    r = subprocess.run([sys.executable, os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    assert r.returncode == 0, r.stdout + r.stderr
    import make as MK
    pins.READ.clear()
    MK.build()
    fit = {Q.E385 % "mode0" + "/raw.txt", Q.E385 % "bit25-mode5" + "/raw.txt"}
    assert pins.READ | fit == set(CFG["freeze"]["pins"])


def test_bins_are_the_published_programs():
    for n, pin in Q.BINS.items():
        b = open(os.path.join(KP, "bins", n), "rb").read()
        assert hashlib.sha256(b).digest() == hashlib.sha256(B(pin)).digest(), n
    assert len(open(os.path.join(KP, "bins", Q.RAMP_BIN), "rb").read()) == 29 * 8


def test_pa_and_triangle_from_e382():
    xy = Q.xy_image(B)
    tri = Q.triangle(B)
    assert sum(tri) == 1062
    for i, t in enumerate(tri):
        if t:
            x, y = i % 64, i // 64
            assert xy[i] == (Q.single(x + 0.5) & 0xFFFF0000) | (Q.single(y + 0.5) >> 16), (x, y)


def test_ramp_unique_and_every_byte():
    tri = Q.triangle(B)
    ramp = Q.ramp_image(tri)
    on = [v for v, t in zip(ramp, tri) if t]
    assert len(set(on)) == 1062 and Q.BG not in on
    for sh in (0, 8, 16, 24):
        n = collections.Counter((v >> sh) & 0xFF for v in on)
        assert len(n) == 256 and min(n.values()) >= 2, sh


def test_integer_trick_is_exact():
    for v in range(64):
        f = 2.0 ** 22 + v + 0.5
        assert (Q.single(f) >> 1) & 0x3F == v and float(f) == f


@pytest.mark.skipif(not os.path.exists(SIM), reason="sgx-sim not built")
def test_sim_runs_the_ramp():
    for x, y in ((8, 8), (54, 13), (30, 30), (17, 40), (9, 53), (63, 0)):
        r = subprocess.run([SIM, "--task", "pixel", "--set", f"pa0=0x{Q.single(x + .5):08x}",
                            "--set", f"pa1=0x{Q.single(y + .5):08x}",
                            os.path.join(KP, "bins", Q.RAMP_BIN)], capture_output=True, text=True)
        assert f"o0 = 0x{Q.ramp_word(x, y):08x}" in r.stdout, (x, y, r.stdout, r.stderr)


def test_controls():
    tri = Q.triangle(B)
    ramp = Q.ramp_image(tri)
    assert Q.thr_of([v >> 24 for v in ramp], Q.image16(ramp, 4, Q.rz)) == "127,128"
    rows = {r["name"]: r for rows in Q.jobs(B).values() for r in rows}
    assert rows["s0-m00-ref"]["pixels"]["H-RAMP"] == ramp
    for m in Q.COL_CONTROLS:
        assert len(rows[f"s0-m{m:02d}-col"]["pixels"]["H-E031"]) == 4096


def test_rules_differ_on_the_ramp():
    ramp = Q.ramp_image(Q.triangle(B))
    for m in Q.NARROW:
        ims = {n: tuple(Q.image16(ramp, m, f)) for n, f in Q.RULES.items()}
        assert len(set(ims.values())) == 4, m
