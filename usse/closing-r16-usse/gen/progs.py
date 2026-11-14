# SPDX-License-Identifier: MIT
"""progs.py: the probe programs of r16-usse and their frozen predictions (client fills as E597 and
E599 ran, `probe --temps 32 FILE`: one program a job, its results stored to scratch dwords that
the tool prints, at most 32 of them, PROBE_MAX_WORDS 256 words a program).

uadd (Q126): iaddu32 over eight (r1, source 2) pairs a program, each result stored to its own
dword k (scratch +4k). r1 of 0x8000 to 0xffff in the low half (seven of eight pairs: H-ZX and
H-SX differ there; 0x7fff is the side where they agree).

utest (Q137): one form and one join a program; for each input pair j the value of OP (written by
the field-0 test `OP.testtat.chan0 r3, ...`) at dword 2j and, at dword 2j + 1, 0x5A5A0000 with bit
f set when the test word of field f set p0 (`p0 or r10, r10, r(12 + f)`, r12 + f holding 1 << f),
fields 0 to 15 (the controls 1 to 15, E499's and E529's tables). The lane rows: one pair, the value
at dword 0 and the chan field c's dword at 1 + c (chan0 to or02), the nine fields the assembler
names (0, 1, 2, 4, 5, 6, 8, 9, 0xa). A test word the assembler names is written as text, any other
as `.long` (the text word's enc[43:36] replaced); tests/test_gen.py checks that every text word
is that raw word (OQ137)."""
import pins
import rule as R
import sim

PHAS = "phas #0, #0, pixel, end, parallel"
MARK = 0x5A5A0000
BITREG = 12                         # r12 + f holds 1 << f
FIELDS16 = tuple(range(16))
FIELDS15 = tuple(range(1, 16))
FIELDS9 = (0, 1, 2, 4, 5, 6, 8, 9, 10)
UMARK = [0xA0A1A2A3 + 0x04040404 * k for k in range(4)]

# ---- the kept tables the controls replicate (the sim replays each, tests/test_sim.py) -------------
RAWCOND = "data:vectors/nokernel/usse/rawcond/usse-rawcond-and-codes.vec.json"          # E499
RAWJOIN = "data:vectors/nokernel/usse/rawjoin-o/usse-rawjoin-o-and.vec.json"            # E529
E521_VEC = ("data:vectors/usse/decoder-vectors/usse-decoder-vectors-iaddu32-taz.vec.json",
            "data:vectors/usse/integer/usse-integer-iaddu32-value.vec.json")
E498_VEC = "data:vectors/nokernel/usse/iaddu32-pairs/usse-iaddu32-pairs-iaddu32-%s.vec.json"
REPLAYS = (RAWCOND, RAWJOIN, *E521_VEC,
           *(E498_VEC % t for t in ("testtaz", "testtanz", "testnat", "testpat")),
           "data:vectors/nokernel/usse/rawcond2/usse-rawcond2-and-imm.vec.json",
           "data:vectors/nokernel/usse/rawcond2/usse-rawcond2-or-reg.vec.json",
           "data:vectors/nokernel/usse/rawcond2/usse-rawcond2-rol-reg.vec.json",
           "data:vectors/nokernel/usse/rawcond2/usse-rawcond2-xor-imm.vec.json",
           "data:vectors/nokernel/usse/rawcond2/usse-rawcond2-xor-reg.vec.json",
           "data:vectors/nokernel/usse/rawjoin-o2-and7/usse-rawjoin-o2-and7-fields.vec.json",
           "data:vectors/nokernel/usse/rawjoin-o2-or/usse-rawjoin-o2-or-fields.vec.json",
           "data:vectors/nokernel/usse/rawjoin-o2-xor/usse-rawjoin-o2-xor-fields.vec.json",
           *(f"data:vectors/nokernel/usse/rawchan-{c}/usse-rawchan-{c}-and.vec.json"
             for c in range(1, 8)))


def h(v):
    return "0x%08x" % (v & R.M)


def kept_cases(pin):
    """[(word of the test (or None), a, b, o0)] of a kept vector file: the inputs A and B, the
    readback o0 (the program's OUT register), the first class 9 word of the program."""
    out = []
    for v in pins.vectors(pin)["vectors"]:
        p = v["provenance"]["inputs"]
        ws = [int(w, 16) for w in v["program"]["words"]]
        t = next((w for w in ws if w >> 59 == 9), None)
        out.append((t, int(p["A"], 16), int(p.get("B", "0"), 16), int(v["readback"]["o0"], 16)))
    return out


# ---- utest --------------------------------------------------------------------------------------
U = R.M
TFORMS = {
    # name: (op, source 2, pairs (r1, r2); r2 unused with an immediate)
    "shl": ("shl", "r2", [(0, 5), (0x80000000, 1), (1, 4), (0x60000000, 1), (0x7FFFFFFF, 1),
                          (0x12345678, 0)]),
    "shr": ("shr", "r2", [(0, 3), (1, 1), (0x80000000, 0), (U, 0), (0x80000000, 31),
                          (0xF0000000, 4)]),
    "asr": ("asr", "r2", [(0, 7), (1, 1), (0x80000000, 31), (0x80000000, 4), (0x7FFFFFFF, 30),
                          (0x40000000, 2)]),
    "or7": ("or", "#7", [(0, 0), (8, 0), (0x7FFFFFF8, 0), (0x80000000, 0), (0xFFFFFFF8, 0),
                         (0x12345670, 0)]),
    "rol7": ("rol", "#7", [(0, 0), (1, 0), (0x01000000, 0), (0x80000000, 0), (U, 0),
                           (0x02000000, 0)]),
    "iadd32": ("iadd32", "r2", [(0, 0), (1, U), (0x8000, 0x8000), (5, 3), (0xFFFF, 0),
                                (0x7FFF, 0x7FFFFFFF)]),
    "iaddu32": ("iaddu32", "r2", [(0, 0), (0xFFFF, 1), (1, U), (0x8000, 0x8000), (0, 0x80000000),
                                  (0xABCD, 0x12345678)]),
}
LFORMS = {
    # bytes 0, 3, 0xf1, 8 (zero, positive, negative, positive) / halves 0 and -15 (lanes 0, 2)
    "iadd8": ("iadd8", "r2", (0x05F00100, 0x03010200)),
    "iadd16": ("iadd16", "r2", (0xFFF00005, 0x0001FFFB)),
}
TROWS = (["t-ctl-and-a", "t-ctl-and-o"]
         + [f"t-{f}-{j}" for f in TFORMS for j in "ao"]
         + [f"t-{f}-a" for f in LFORMS] + [f"t-{f}-o" for f in LFORMS])
T_MODELS_A = ("H-RULE", "H-SETAND")
T_MODELS_O = ("H-RULE", "H-AJOIN", "H-ORFALSE", "H-SETOR")


def base_word(op, src2):
    return sim.word(f"{op}.testtaz.chan0 !c0, p0, r1, {src2}")


def test_line(op, src2, field, join, chan, base, canonical=False):
    """The text of one test (or its .long), and its word."""
    w = R.word(base, field, join, chan)
    if canonical:
        s, z = R.parts(field)
        field = {"t": 0, "n": 4, "p": 8}[s] | {"t": 0, "z": 1, "nz": 2}[z]
    name = R.text_name(field, join)
    if name is None:
        return ".long 0x%016X" % w, w
    return f"{op}.{name}.{R.CHAN_NAME[chan]} !c0, p0, r1, {src2}", w


def prologue(title):
    lines = [f"; r16-usse {title} (gen/progs.py)", PHAS, "mov.skipinv r29, #0x5CAF0000",
             "mov.skipinv r28, #0x%08X" % MARK]
    lines += ["mov.skipinv r%d, #0x%08X" % (BITREG + f, 1 << f) for f in range(16)]
    return lines


EPILOGUE = ["idf drc0, bif", "wdf drc0", "mov.skipinv.end o0, r10"]


def value_lines(op, src2, a, b, slot):
    out = ["mov.skipinv r1, #0x%08X" % a]
    if src2 == "r2":
        out.append("mov.skipinv r2, #0x%08X" % b)
    return out + [f"{op}.testtat.chan0 r3, p0, r1, {src2}", f"stad [r29,+#{slot}], r3"]


def sim_value(op, src2, a, b):
    r = sim.run("\n".join([PHAS] + value_lines(op, src2, a, b, 0)[:-1]
                          + ["mov.skipinv.end o0, r3"]) + "\n")
    if not r.ok:
        raise SystemExit(f"sgx-sim refuses the value of {op} {src2} {a:#x} {b:#x}: {r.why}")
    return r.regs["r3"]


def utest_job(name, canonical=False):
    """dict(name, set, text, preds {quantity: {model: {offset: value}}}, why) of a utest row;
    canonical=True writes every raw field as the field of the same two parts (the sim's twin)."""
    kind, join = name.rsplit("-", 1)[0][2:], name[-1]
    preds = {"tests": {}, "values": {"H-SIM": {}}}
    if kind == "ctl-and":
        op, src2, fields, st = "and", "r2", FIELDS15, "control"
        model = "H-E499" if join == "a" else "H-E529"
        kept = kept_cases(RAWCOND if join == "a" else RAWJOIN)
        pairs = []
        for _, a, b, _ in kept:
            if (a, b) not in pairs:
                pairs.append((a, b))
        preds["tests"][model] = {}
        for j, (a, b) in enumerate(pairs):
            bits = 0
            for (w, ka, kb, o0) in kept:
                f, kj, kc = R.fields_of(w)
                assert kj == join and kc == 0
                if (ka, kb) == (a, b) and o0:
                    bits |= 1 << f
            preds["tests"][model][4 * (2 * j + 1)] = MARK | bits
        why = (f"E{'499' if join == 'a' else '529'}'s kept table "
               f"({'usse-rawcond-and-codes' if join == 'a' else 'usse-rawjoin-o-and'}), replicated")
        models = ("H-RULE",)
    elif kind in TFORMS:
        op, src2, pairs = TFORMS[kind]
        fields, st = FIELDS16, "heldout"
        models = T_MODELS_A if join == "a" else T_MODELS_O
        why = f"{op} {src2}, the {join} join, fields 0-15 over six pairs (sgx-sim's rule)"
    else:
        op, src2, pair = LFORMS[kind]
        pairs, fields, st = [pair], FIELDS9, "heldout"
        # H-SETAND reads as H-RULE on the nine named fields (it differs on two-bit parts only)
        models = (("H-RULE",) if join == "a" else T_MODELS_O) + ("H-CHAN0",)
        why = f"{op} lanes, the {join} join, chan0-or02 by the nine named fields"
    base = base_word(op, src2)
    lines = prologue(f"{name}: {why}")
    lane = kind in LFORMS
    for m in models:
        preds["tests"].setdefault(m, {})
    for j, (a, b) in enumerate(pairs):
        vslot = 0 if lane else 2 * j
        lines += value_lines(op, src2, a, b, vslot)
        preds["values"]["H-SIM"][4 * vslot] = sim_value(op, src2, a, b)
        cls = sim.classes(op, src2, a, b)
        for c in (range(8) if lane else [0]):
            slot = 1 + c if lane else 2 * j + 1
            lines.append("mov.skipinv r10, r28")
            for f in fields:
                lines.append(test_line(op, src2, f, join, c, base, canonical)[0])
                lines.append("p0 or r10, r10, r%d" % (BITREG + f))
            lines.append(f"stad [r29,+#{slot}], r10")
            for m in models:
                bits = sum(1 << f for f in fields if R.predicate(f, join, c, cls, m))
                preds["tests"][m][4 * slot] = MARK | bits
    lines += EPILOGUE
    return dict(name=name, set=st, text="\n".join(lines) + "\n", preds=preds, why=why,
                op=op, src2=src2, join=join, pairs=pairs)


# ---- uadd ---------------------------------------------------------------------------------------
R1S = [0x8000, 0x8001, 0xABCD, 0xFFFF, 0x7FFF, 0xFFFF8000, 0x1234FEDC, 0xFFFFFFFF]
R2S = [0x8000, 0x7FFF0000, 0x1, U, 0x8001, 0x12345678, 0x80000000, 0x00010000]
E521_PAIRS = [(0x8000, 0x8000), (0xFFFF, 1), (U, 1), (0x7FFFFFFF, 1), (U, 2),
              (0x7C23A2BD, 0x47B003F0), (0xB99EDE85, 0x87261F80), (0x12345678, 0x11111111)]
E498_PAIRS = [(0, 0), (0x8000, 0x8000)]
TESTS4 = ("testtaz", "testtanz", "testnat", "testpat")
UROWS = ("u-ctl-e521", "u-ctl-e498", "u-imm1", "u-imm127", "u-c56", "u-i0", "u-sa0")
# the write masks on the test (a field no job has run on a class 9 word): a stage of their own,
# the session's last, with E521's control again first
RROWS = ("u-ctl-rpt", "u-rpt2", "u-rpt4")


def uadd_job(name):
    lines = [f"; r16-usse {name} (gen/progs.py)", PHAS, "mov.skipinv r29, #0x5CAF0000"]
    preds, st, models = {}, "heldout", ("H-ZX", "H-SX")
    if name in ("u-ctl-e521", "u-ctl-rpt"):
        st, why = "control", "E521's register pairs (r10, then stored), replicated"
        kept = {}
        for pin in E521_VEC:
            for _, a, b, o0 in kept_cases(pin):
                kept.setdefault((a, b), set()).add(o0)
        vals = {}
        for k, (a, b) in enumerate(E521_PAIRS):
            assert len(kept[(a, b)]) == 1, (a, b)
            lines += ["mov.skipinv r1, #0x%08X" % a, "mov.skipinv r2, #0x%08X" % b,
                      "iaddu32.testtaz.chan0 r10, p0, r1, r2", f"stad [r29,+#{k}], r10"]
            vals[4 * k] = kept[(a, b)].pop()
        preds = {"H-E521": vals}
    elif name == "u-ctl-e498":
        st, why = "control", "E498's iaddu32 tests (p0 into r10, stored) over two pairs, replicated"
        kept = {t: {(a, b): o0 for _, a, b, o0 in kept_cases(E498_VEC % t)} for t in TESTS4}
        vals = {}
        k = 0
        for a, b in E498_PAIRS:
            lines += ["mov.skipinv r1, #0x%08X" % a, "mov.skipinv r2, #0x%08X" % b]
            for t in TESTS4:
                lines += [f"iaddu32.{t}.chan0 !c0, p0, r1, r2", "mov r10, #0", "p0 mov r10, #1",
                          f"stad [r29,+#{k}], r10"]
                vals[4 * k] = kept[t][(a, b)]
                k += 1
        preds = {"H-E498": vals}
    elif name in ("u-imm1", "u-imm127", "u-c56"):
        src2 = {"u-imm1": "#1", "u-imm127": "#127", "u-c56": "c56"}[name]
        b = {"#1": 1, "#127": 127, "c56": 0xFFFFFFFF}[src2]
        why = f"iaddu32 r10 = r1 + {src2} (source 2 {'an immediate' if src2[0] == '#' else 'c56 = 0xffffffff'})"
        preds = {m: {} for m in models}
        for k, a in enumerate(R1S):
            lines += ["mov.skipinv r1, #0x%08X" % a, f"iaddu32.testtaz.chan0 r10, p0, r1, {src2}",
                      f"stad [r29,+#{k}], r10"]
            for m in models:
                preds[m][4 * k] = R.iaddu32(a, b, m)
    elif name in ("u-i0", "u-sa0"):
        d = name[2:]
        why = f"iaddu32 to {d} (read back by mov r3, {d})"
        preds = {m: {} for m in models}
        for k, (a, b) in enumerate(zip(R1S, R2S)):
            lines += ["mov.skipinv r1, #0x%08X" % a, "mov.skipinv r2, #0x%08X" % b,
                      f"iaddu32.testtaz.chan0 {d}, p0, r1, r2", f"mov r3, {d}",
                      f"stad [r29,+#{k}], r3"]
            for m in models:
                preds[m][4 * k] = R.iaddu32(a, b, m)
    else:
        n = 2 if name == "u-rpt2" else 4
        mask = ".xy" if n == 2 else ".xyzw"
        why = (f"iaddu32 r10{mask} (the write mask, {n} components: d + k from r1 + k and r5 + k), "
               f"r10-r13 preset to markers")
        models = ("H-ZX-ADV", "H-SX", "H-NOREP", "H-NOADV")
        preds = {m: {} for m in models}
        for g in range(8 // n):
            grp = list(zip(R1S, R2S))[g * n:(g + 1) * n]
            lines += ["mov.skipinv r%d, #0x%08X" % (10 + k, UMARK[k]) for k in range(4)]
            lines += ["mov.skipinv r%d, #0x%08X" % (1 + k, a) for k, (a, _) in enumerate(grp)]
            lines += ["mov.skipinv r%d, #0x%08X" % (5 + k, b) for k, (_, b) in enumerate(grp)]
            lines.append(f"iaddu32.testtaz.chan0 r10{mask}, p0, r1, r5")
            for k in range(n):
                slot = g * n + k
                lines.append(f"stad [r29,+#{slot}], r{10 + k}")
                a, b = grp[k]
                a0, b0 = grp[0]
                preds["H-ZX-ADV"][4 * slot] = R.iaddu32(a, b, "H-ZX")
                preds["H-SX"][4 * slot] = R.iaddu32(a, b, "H-SX")
                preds["H-NOREP"][4 * slot] = R.iaddu32(a0, b0, "H-ZX") if k == 0 else UMARK[k]
                preds["H-NOADV"][4 * slot] = R.iaddu32(a0, b0, "H-ZX")
    out = "r3" if name in ("u-i0", "u-sa0") else "r10"
    lines += ["idf drc0, bif", "wdf drc0", f"mov.skipinv.end o0, {out}"]
    return dict(name=name, set=st, text="\n".join(lines) + "\n", preds={"dwords": preds},
                why=why)
