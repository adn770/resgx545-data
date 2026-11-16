# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current and reads only pinned files; the bins are the
published programs byte for byte; the frozen masks and readings hold on the kept records they
come from (E268: bit 25 xor 0xff000000 in mode 0, bit 11 nothing, E268's image = E031's; E385:
bit 25 xor 0x80008000, 0xf000f000 and 0 in modes 4, 5 and 8 on the ramp, its five thresholds read
the same under H-GE and H-GT); H-GE's two fit points (E031's mode 4: alpha 0x80 at 0x80 sets the
bit; E385's background: alpha 0xff at 0xff sets it) and H-GT failing them; every equality row has
pixels at its low byte and its two models differ."""
import collections
import hashlib
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import q044 as Q  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
B = pins.blob


def k385(p, c):
    return Q.kept(B, Q.E385 % p, f"pbe-reg-0400-alpha-{p}__{c}")


def k268(c):
    return Q.kept(B, Q.E268, f"pbe-reg-0400-modes-0__{c}")


def k031(m):
    return Q.kept(B, Q.E031 % m, f"pbe-pack-modes-packmode-{m:02d}__0")


def test_generated_current_and_pins():
    r = subprocess.run([sys.executable, os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    import make as MK
    pins.READ.clear()
    MK.build()
    assert pins.READ == set(CFG["freeze"]["pins"])


def test_bins_are_the_published_programs():
    for n, pin in Q.BINS.items():
        b = open(os.path.join(KP, "bins", n), "rb").read()
        assert hashlib.sha256(b).digest() == hashlib.sha256(B(pin)).digest(), n


def test_masks_on_the_kept_pairs():
    assert Q.xor_of(k268(0), k268(1)) == (f"0x{Q.INV25[0]:08x}", 4096)
    assert Q.xor_of(k268(0), k268(13))[0] == "0x00000000"
    assert k268(0) == k031(0)
    for m in (4, 5, 8):
        got, n = Q.xor_of(k385(f"bit25-mode{m}", 0), k385(f"bit25-mode{m}", 1))
        assert got == f"0x{Q.INV25[m]:08x}" and n > 0, m
    assert k385("bit25-mode4", 0) == k385("mode4", 0)


def test_thresholds_on_e385():
    al = Q.alpha_map(B)
    assert sum(a is not None for a in al) == 1062
    for c, low in enumerate((0x80, 0, 0x40, 0xC0, 0xFF)):
        got = Q.thr_of(al, k385("mode4", c))
        assert got == Q.thr_model(al, low, True) == Q.thr_model(al, low, False), (low, got)


def test_h_ge_fit_points():
    m4 = k031(4)
    tri = [v for v in m4 if v != Q.SENT and v & 0xFFFF == 0xFE08]
    assert tri and all(v >> 15 & 1 for v in tri)              # alpha 0x80 at 0x80: set (H-GE)
    bg = k385("mode4", 4)                                       # low byte 0xff
    al = Q.alpha_map(B)
    halves = [h for v in bg for h in (v & 0xFFFF, v >> 16)]
    back = [h for a, h in zip(al, halves[:4096]) if a is None]
    assert back and set(back) == {0x90C8}                       # alpha 0xff at 0xff: set


def test_equality_rows():
    al = Q.alpha_map(B)
    n = collections.Counter(a for a in al if a is not None)
    for low in Q.EQ:
        assert n[low] >= 2, low
        assert Q.thr_model(al, low, True) != Q.thr_model(al, low, False)


def test_classes():
    assert set(Q.INV25) >= (set(Q.P1_MODES) | set(Q.PAST)) - set(Q.Q012)
    assert not set(Q.Q012) & set(Q.INV25)
    for m in Q.P1_MODES:
        if m not in Q.Q012:
            assert len(k031(m)) == 4096
