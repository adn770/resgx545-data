# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current and its inputs are pinned.

- gen/lgen.py run again into a scratch directory writes the session's tables, predictions,
  programs, mock/progs.tsv and gen/pins.txt byte for byte (needs debug/asm's usse-asm, which
  tests/run_all.sh builds from `git archive` of the pinned resgx545 commit);
- every byte copy (gen/, score/, templates/, tests/kept.py) is its pinned blob (r8-lgeo's
  published files), and session.toml [freeze] pins hold every file the generator and the replays
  read;
- every program disassembles (debug/asm's usse-dis) to what mock/progs.tsv says it samples: the
  T0 and T1 words (type, format, size), the linear axis's constants (the offsets) or the map
  axis, no stored dword;
- the linear axis with no offset is texcatalog.swin's, bit for bit (E940's 24 and 40 wide rows);
- the tool's tag fill covers its whole scratch, 16 pages by default (t4's source at 4623753,
  TOOLSRC.sha256): the premise of every tx6 row's frozen 64 KiB, and no rival reads past it;
- the job counts are the plan's: tx6 14, q139b 4 (18)."""
import filecmp
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tomllib

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, HERE)
import kitscore as K  # noqa: E402
import kept as KD  # noqa: E402
import texcatalog as TC  # noqa: E402

ASM = os.path.join(KP, "debug/asm/tools/usse-asm/usse-asm")
DIS = os.path.join(KP, "debug/asm/tools/usse-dis/usse-dis")
MAIN = "/Users/jtorra/src/resgx545"
STAGES = ("tx6", "q139b")
R8 = "render/closing-r8-lgeo/"
COPIES = {f: R8 + f for f in ("gen/texmodel.py", "gen/texcatalog.py", "gen/texbuild.py", "gen/q139model.py",
                              "gen/q139_fit.py", "templates/tx_map.s", "score/lib_dump.py", "score/pbdump_dump.py",
                              "score/region_tiles_dump.py", "tests/kept.py")}


def toml():
    with open(os.path.join(KP, "session.toml"), "rb") as f:
        return tomllib.load(f)


def test_job_counts_are_the_plans():
    n = {s: len(K.table(KP, s)) for s in STAGES}
    assert n == {"tx6": 14, "q139b": 4}
    assert list(toml()["stages"]) == list(STAGES)


@pytest.mark.skipif(not os.path.exists(ASM), reason="SKIPPED, NOT PASSED: no debug/asm usse-asm (tests/run_all.sh builds it)")
def test_generator_is_current(tmp_path):
    out = tmp_path / "out"
    for d in ("gen", "mock", "bins", "tables", "predictions"):
        (out / d).mkdir(parents=True)
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/lgen.py"), str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for d in ("tables", "predictions", "predictions/q139b", "bins"):
        a, b = sorted(os.listdir(out / d)), sorted(os.listdir(os.path.join(KP, d)))
        assert a == b, d
        files = [f for f in a if os.path.isfile(out / d / f)]
        _, mism, err = filecmp.cmpfiles(out / d, os.path.join(KP, d), files, shallow=False)
        assert not mism and not err, (d, mism[:5], err[:5])
    for f in ("mock/progs.tsv", "gen/pins.txt"):
        assert filecmp.cmp(out / f, os.path.join(KP, f), shallow=False), f


def test_byte_copies_are_their_pins():
    for mine, theirs in COPIES.items():
        assert open(os.path.join(KP, mine), "rb").read() == KD.blob(theirs), mine


def test_every_input_is_pinned():
    pins = set(toml()["freeze"]["pins"])
    need = {ln.strip() for ln in open(os.path.join(KP, "gen/pins.txt")) if ln.strip()}
    need |= {"data:" + p for p in COPIES.values()}
    assert not need - pins, sorted(need - pins)


def test_linear_axis_without_offsets_is_swins():
    import lgen
    for w, h in ((24, 8), (40, 8), (32, 16), (48, 64), (80, 64), (96, 32)):
        assert lgen.lwin(w, h) == TC.swin(w, h), (w, h)


def f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits))[0]


@pytest.mark.skipif(not os.path.exists(DIS), reason="SKIPPED, NOT PASSED: no debug/asm usse-dis (tests/run_all.sh builds it)")
def test_programs_disassemble_to_their_specs():
    progs = {}
    for ln in open(os.path.join(KP, "mock/progs.tsv")):
        if ln.strip() and not ln.startswith("#"):
            sha, meta = ln.rstrip("\n").split("\t", 1)
            progs[sha] = json.loads(meta)
    seen = 0
    for b in sorted(os.listdir(os.path.join(KP, "bins"))):
        if not b.endswith(".bin"):
            continue
        p = os.path.join(KP, "bins", b)
        m = progs[hashlib.sha256(open(p, "rb").read()).hexdigest()]
        dis = subprocess.run([DIS, p], capture_output=True, text=True, check=True).stdout
        t0 = int(re.search(r"\bmov r20, #(0x[0-9A-Fa-f]+)", dis).group(1), 16)
        t1 = int(re.search(r"\bmov r21, #(0x[0-9A-Fa-f]+)", dis).group(1), 16)
        assert t0 == m["t0"] == TC.T0_REP, b
        assert (t1 >> 29, (t1 >> 24) & 31, ((t1 >> 12) & 0xFFF) + 1, (t1 & 0xFFF) + 1) == (m["ty"], m["fmt"], m["w"], m["h"]), b
        assert not re.findall(r"\bstad\b", dis) and not m["stored"], b
        assert ("fmad" in dis) == m["linear"], b
        if m["linear"]:
            # u = (x + xo + 1/2) / w and v = (y + yo + 1/2) / h from r1 = 1 + x / 64 (or 1 + y / 32)
            k = [f32(int(x, 16)) for x in re.findall(r"\bmov\.skipinv r2, #(0x[0-9A-Fa-f]+)", dis)]
            c = [f32(int(x, 16)) for x in re.findall(r"\bmov\.skipinv r3, #(0x[0-9A-Fa-f]+)", dis)]
            assert len(k) == len(c) == 2, b
            for (kk, cc), n, off, step in ((((k[0], c[0])), m["w"], m["xo"], 64), ((k[1], c[1]), m["h"], m["yo"], 32)):
                assert abs(kk - step / n) < 1e-6 and abs(kk + cc - (off + 0.5) / n) < 1e-6, (b, kk, cc)
                for t in range(step):
                    pos = ((1 + t / step) * kk + cc) * n
                    assert int(pos % n) == (t + off) % n and abs(pos % 1 - 0.5) < 1e-3, (b, t)
        else:
            ors = [int(x, 16) for x in re.findall(r"\bor\.skipinv r1, r1, #(0x[0-9A-Fa-f]+)", dis)]
            assert [x for x in ors if x not in (1, 0x3F800000)] == [], b
        seen += 1
    assert seen == len(progs) == 14


def test_tag_fill_covers_the_scratch():
    """t4 (sgxfive-test-rgn4, e6951558...) is built from resgx545 4623753's sgxfive-test.c
    (TOOLSRC.sha256): a probe fills every dword of its SCRATCH_PAGES pages with 0xD0000000 | i,
    16 pages by default (16384 dwords); no tx6 row asks for another size, and the largest dword any
    rival reads is 7151 (80 x 64 under H-P2)."""
    src = subprocess.run(["git", "-C", MAIN, "show", "4623753:userspace/libsgxfive/tools/sgxfive-test.c"],
                         capture_output=True, check=True).stdout
    want = open(os.path.join(KP, "TOOLSRC.sha256")).read().split()[0]
    assert hashlib.sha256(src).hexdigest() == want
    s = src.decode()
    assert "static uint32_t scratch_pages = 16;" in s
    assert "#define SCRATCH_FILL(i)\t(0xD0000000u | (i))" in s
    assert s.count("for (uint32_t i = 0; i < SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4; i++)\n\t\t\tsp[i] = SCRATCH_FILL(i);") >= 1
    import tx6model as X
    top = 0
    for t in K.table(KP, "tx6"):
        assert "--scratch-pages" not in t["args"], t["name"]
    for w, h in ((48, 64), (80, 64), (96, 32)):
        for hy in X.TYPE4:
            top = max(top, max(X.type4_offset(hy, x, y, w, h) for y in range(h) for x in range(w)))
    assert top == 7151 < 16 * 4096 // 4
