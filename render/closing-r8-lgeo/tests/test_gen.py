# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current and its inputs are pinned.

- gen/lgen.py run again into a scratch directory writes the session's tables, predictions,
  programs, mock/progs.tsv and gen/pins.txt byte for byte (needs debug/asm's usse-asm, which
  tests/run_all.sh builds from `git archive` of the pinned resgx545 commit);
- every byte copy (gen/, score/, templates/) is its pinned blob, and session.toml [freeze] pins
  hold every file the generator and the replays read;
- every program disassembles (debug/asm's usse-dis) to what mock/progs.tsv says it samples: the
  T0 and T1 words, the window offsets and the stored dwords;
- the tool's tag fill covers its whole scratch (t4's source at 4623753, TOOLSRC.sha256): the
  premise of tx4's 128 x 128 rows (16384 dwords at 16 pages) and of --scratch-pages 64;
- the job counts are the plan's: tx3 10, tx4 23, tx5 28, zs2 165, q139 20 (246)."""
import filecmp
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, HERE)
import kitscore as K  # noqa: E402
import kept as KD  # noqa: E402

ASM = os.path.join(KP, "debug/asm/tools/usse-asm/usse-asm")
DIS = os.path.join(KP, "debug/asm/tools/usse-dis/usse-dis")
MAIN = "/Users/jtorra/src/resgx545"
STAGES = ("tx3", "tx4", "tx5", "zs2", "q139")
COPIES = {"gen/texbuild.py": "render/closing-r7-geo/gen/texbuild.py",
          "gen/texcatalog.py": "render/closing-r7-geo/gen/texcatalog.py",
          "templates/tx_map.s": "render/closing-r7-geo/templates/tx_map.s",
          "gen/q139_fit.py": "render/closing-r7-rp/fold/q139_fit.py",
          "score/lib_dump.py": "render/closing-r7-rp/score/lib_dump.py",
          "score/pbdump_dump.py": "render/closing-r7-rp/score/pbdump_dump.py",
          "score/region_tiles_dump.py": "render/closing-r7-rp/score/region_tiles_dump.py"}
R7G = "render/closing-r7-geo/out/20261112-211113"
R7R = "render/closing-r7-rp/out/20261112-205431/q139"
REPLAYS = ["%s/tx/%s.txt.gz" % (R7G, n) for n in ("tx-ty3-64x8", "tx-ty4-128x8", "tx-ty5-16x16-ones")] + \
    ["%s/%s%s" % (R7R, n, s) for n in ("q139-c-256x256-ctl", "q139-c-640x480-ctl", "q139-h-256x256-stride-4",
                                       "q139-h-256x256-stride-24") for s in (".txt.gz", ".tri.param.bin.gz", ".tri.tadata.bin.gz")]


def toml():
    with open(os.path.join(KP, "session.toml"), "rb") as f:
        return tomllib.load(f)


def test_job_counts_are_the_plans():
    n = {s: len(K.table(KP, s)) for s in STAGES}
    assert n == {"tx3": 10, "tx4": 23, "tx5": 28, "zs2": 165, "q139": 20}
    assert sum(n.values()) == 246
    assert list(toml()["stages"]) == list(STAGES)


@pytest.mark.skipif(not os.path.exists(ASM), reason="SKIPPED, NOT PASSED: no debug/asm usse-asm (tests/run_all.sh builds it)")
def test_generator_is_current(tmp_path):
    out = tmp_path / "out"
    for d in ("gen", "mock", "bins", "tables", "predictions"):
        (out / d).mkdir(parents=True)
    r = subprocess.run([sys.executable, os.path.join(KP, "gen/lgen.py"), str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for d in ("tables", "predictions", "predictions/zs2", "predictions/q139", "bins"):
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
    need |= {"data:" + p for p in COPIES.values()} | {"data:" + p for p in REPLAYS}
    need |= {"data:texture/p1141/stage-bins/p1141-types__2.bin"}
    assert not need - pins, sorted(need - pins)


def test_e725_control_program_is_r7_geos():
    """tx3's 32 x 16 control is E725's program: r7-geo's copy equals the p1141 stage bin."""
    a = KD.blob("render/closing-r7-geo/bins/r7g-ty3-32x16.bin")
    assert a == KD.blob("texture/p1141/stage-bins/p1141-types__2.bin")
    assert open(os.path.join(KP, "bins/r8l-ty3-32x16.bin"), "rb").read() == a


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
        assert t0 == m["t0"], b
        assert (t1 >> 29, (t1 >> 24) & 31, ((t1 >> 12) & 0xFFF) + 1, (t1 & 0xFFF) + 1) == (m["ty"], m["fmt"], m["w"], m["h"]), b
        ors = [int(x, 16) for x in re.findall(r"\bor\.skipinv r1, r1, #(0x[0-9A-Fa-f]+)", dis)]
        offs = [x for x in ors if x not in (1, 0x3F800000)]
        assert offs == [x for x in (m["xo"], m["yo"]) if x], (b, offs)
        assert len(re.findall(r"\bstad\b", dis)) == len(m["stored"]), b
        assert ("fmad" in dis) == m["linear"], b
        seen += 1
    assert seen == len(progs) == 61


def test_tag_fill_covers_the_scratch():
    """t4 (sgxfive-test-rgn4, e6951558...) is built from resgx545 4623753's sgxfive-test.c
    (TOOLSRC.sha256): a probe fills every dword of its SCRATCH_PAGES pages with 0xD0000000 | i,
    16 pages by default (16384 dwords: a 128 x 128 32-bit texture), --scratch-pages 16 to 64."""
    src = subprocess.run(["git", "-C", MAIN, "show", "4623753:userspace/libsgxfive/tools/sgxfive-test.c"],
                         capture_output=True, check=True).stdout
    want = open(os.path.join(KP, "TOOLSRC.sha256")).read().split()[0]
    assert hashlib.sha256(src).hexdigest() == want
    s = src.decode()
    assert "static uint32_t scratch_pages = 16;" in s
    assert "#define SCRATCH_FILL(i)\t(0xD0000000u | (i))" in s
    assert s.count("for (uint32_t i = 0; i < SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4; i++)\n\t\t\tsp[i] = SCRATCH_FILL(i);") >= 1
    assert "if (*end || v < 16 || v > 64)" in s
    assert 16 * 4096 // 4 == 128 * 128
