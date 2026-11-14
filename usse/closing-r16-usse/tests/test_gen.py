# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current (every table, prediction and program is what
gen/make.py writes now from the pinned inputs), it reads only pinned files, every program's
results stay inside the default 16 scratch pages and within the 32 dwords the tool prints, every
text test word is the raw word of its field (OQ137: the assembler's two-condition names, testtoz,
testnoz, testnaz, testpanz and the rest, write the fields E529/E530 ran as raw words, byte for
byte), and the bins are the pinned assembler's words of their .s."""
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import progs  # noqa: E402
import rule as R  # noqa: E402
import sim  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def preds(stage):
    out = {}
    for ln in open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        f = ln.split("\t")
        out.setdefault(f[0], []).append({int(k, 16): int(v, 16) for k, v in
                                         (p.split("=") for p in f[2].split(","))})
    return out


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True, timeout=1200)
    assert r.returncode == 0, r.stdout + r.stderr


def test_reads_only_pinned_files():
    for n in progs.TROWS:
        progs.utest_job(n)
    for n in progs.UROWS + progs.RROWS:
        progs.uadd_job(n)
    for p in progs.REPLAYS:
        pins.blob(p)
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_results_inside_the_scratch_and_printed():
    for st in ("uadd", "utest", "urpt"):
        for name, ps in preds(st).items():
            offs = {k for p in ps for k in p}
            assert max(offs) < 16 * 4096 and all(k % 4 == 0 for k in offs)
            assert len(offs) <= 32, (name, len(offs))      # probe_scratch prints 32
            for p in ps:
                # a value equal to its fill would not be printed: none is, so every stored dword shows
                assert all(v != 0xD0000000 | k // 4 for k, v in p.items()), name


def test_programs_store_only_their_dwords():
    for f in sorted(os.listdir(os.path.join(KP, "bins"))):
        if not f.endswith(".s"):
            continue
        name = f[:-2]
        text = open(os.path.join(KP, "bins", f)).read()
        slots = {4 * int(m) for m in re.findall(r"stad \[r29,\+#(\d+)\]", text)}
        allp = {**preds("uadd"), **preds("utest"), **preds("urpt")}
        named = {k for p in allp[name] for k in p}
        assert slots == named, name
        # the scratch base is the only limm of 0x5caf; nothing loads or stores elsewhere
        assert text.count("#0x5CAF0000") == 1 and not re.search(r"\blda|\bldad|\bsta[bw]", text)
        assert sim.assemble(text) == open(os.path.join(KP, "bins", name + ".bin"), "rb").read()


def test_text_words_are_the_raw_fields():
    """OQ137: each name the assembler writes for a field, on every form and channel the session
    runs, is the word with that field, join and chan in enc[43:36] (E529/E530's raw words)."""
    seen = set()
    forms = [(op, s2) for op, s2, _ in progs.TFORMS.values()] + [("and", "r2")] + \
            [(op, s2) for op, s2, _ in progs.LFORMS.values()]
    for op, s2 in forms:
        base = progs.base_word(op, s2)
        for join in "ao":
            for f in range(16):
                for c in (range(8) if op in ("iadd8", "iadd16", "and") else [0]):
                    name = R.text_name(f, join)
                    if name is None:
                        continue
                    t = f"{op}.{name}.{R.CHAN_NAME[c]} !c0, p0, r1, {s2}"
                    assert sim.word(t) == R.word(base, f, join, c), t
                    seen.add(name)
    assert {"testtoz", "testnoz", "testnaz", "testpanz", "testtaz", "testtat", "testtot"} <= seen
    # E529's and E530's words: and.testtaz.chan0 with enc[39] cleared, and the chan field
    and_w = 0x48081181000C0082
    assert R.word(and_w, 5, "o", 0) == sim.word("and.testnoz.chan0 !c0, p0, r1, r2")
    assert R.word(and_w, 1, "o", 0) == sim.word("and.testtoz.chan0 !c0, p0, r1, r2")
    assert R.word(and_w, 0xA, "a", 0) == sim.word("and.testpanz.chan0 !c0, p0, r1, r2")
    assert R.word(and_w, 5, "a", 0) == sim.word("and.testnaz.chan0 !c0, p0, r1, r2")
