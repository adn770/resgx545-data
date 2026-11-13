#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r9-k1's generator. Writes gen/bgmask.txt (the scored pixels, from E590's kept
hardware control), bins/ (the four probe programs, assembled from the pinned templates),
tables/STAGE.txt and predictions/STAGE.tsv, all from session.toml's pinned commits and
gen/bgl_model.py (the frozen model). `python3 gen/make.py` writes them; `python3 gen/make.py
--check` exits 1 when a written file is not what it would write (tests/test_gen.py).

Plan: closing9/k1/exp-k1-r9.md section 3 (stages s0-s4, 94 jobs), decisions K-1..K-6 (a). Two
changes the kit forced, both said in README.md: (1) the kit's guard forbids `--kpoke` (probe's
kernel poke) in every row, so every POKED row reads the layer through texels (L-TEX, `tri
--kpoke-render`), and L-RAW (exact u and v) is read in the unpoked controls only; each L-TEX row
reads u and v at once, so the plan's U/V pairs become one row and the freed rows are more held-out
and fit pokes (44, 20 and 21 rows as planned); (2) a stage's REQUIRED files are per row, so s0 is
two stages, s0t (tri controls, with their dumps and words) and s0p (probe controls); and the
H-NONE confirmation (plan: "s1's 6 one-word U rows, group none") is its own stage s1n, gated on
H-NONE, so 100 rows are tabled and 94 run on the H-ITER path.

The held-out pokes are drawn with random.Random("r9-k1") over 1-3 of the words 3-8 and values
k/8 (k = 0..8), kept when the poke changes the object, H-VM predicts at least 40 % of the scored
pixels (in range and off the texel edges) and differs from H-NOREAD on at least 20 % of the
pixels both predict."""
import os
import random
import subprocess
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
import bgl_model as M  # noqa: E402
import kitscore as K  # noqa: E402
import scorekit  # noqa: E402

REPOS = {"resgx545": "/Users/jtorra/src/resgx545", "data": "/Users/jtorra/src/resgx545-data"}
CONF = tomllib.load(open(os.path.join(KP, "session.toml"), "rb"))
MASK_SRC = "isp/bg-object-pokes/dumps/bg-words-f1/b66f1-control-1.txt.gz"   # E590's control
ASM = os.path.join(KP, "debug/asm/tools/usse-asm")
PROGS = {   # bins/NAME.bin: (template in resgx545, assembler)
    "r9k-raw": ("probes/isp/templates/pds_bgl_raw.s", "pds-asm"),     # L-RAW primary
    "r9k-pos": ("probes/dpm/templates/pds_bg_pos.s", "pds-asm"),      # POS primary (E442)
    "r9k-pa0": ("probes/dpm/templates/pix_pa0.s", "usse-asm"),        # o0 = pa0
    "r9k-pa1": ("probes/dpm/templates/pix_pa1.s", "usse-asm"),        # o0 = pa1
}
STAGES = ("s0t", "s0p", "s1n", "s1", "s2", "s3", "s4")
LAYER = "dbg:render_bg_layer=Y dbg:render_bg_src=0x%08x" % M.SRC
TEX = "tri --bg-layer --pixels --keep-going --dump-render $W"
OFF = "tri --pixels --keep-going --dump-render $W --words $W"
PROBE = "probe --tri bgpds:12 --slot bgpixel=$S/bins/%s.bin%s --pixels $S/bins/%s.bin"
EIGHTHS = [M.bits(k / 8) for k in range(9)]
SEED = "r9-k1"


def git_show(repo, path):
    rev = CONF["freeze"][repo]
    return subprocess.run(["git", "-C", REPOS[repo], "show", "%s:%s" % (rev, path)],
                          check=True, capture_output=True, timeout=60).stdout


def kp(spec):
    """The --kpoke-render options of {word: value}."""
    return "".join(" --kpoke-render 1:bg:%d=0x%08x" % (w, v) for w, v in sorted(spec.items()))


def row(name, sset, knobs, args, tool="t9"):
    return dict(name=name, set=sset, risk="safe", knobs=knobs, tool=tool, args=args)


# ---- the rows --------------------------------------------------------------------------------
def s0t():
    return [
        row("c-off", "control", "expectdiff reads:job,hash,diff", OFF),
        row("c-tex", "control", LAYER + " expectdiff reads:job,diff,inplace,layer",
            TEX + " --words $W"),
        row("c-noop", "control", LAYER + " expectdiff reads:job,diff,inplace,layer",
            TEX + " --words $W" + kp({5: M.ONE})),
    ]


def s0p():
    return [
        row("c-pos-off", "control", "reads:rows", PROBE % ("r9k-pa0", "", "r9k-pos")),
        row("c-pos", "control", LAYER + " reads:rows,layer",
            PROBE % ("r9k-pa0", " --bg-layer", "r9k-pos")),
        row("c-rawu", "control", LAYER + " reads:rows,layer",
            PROBE % ("r9k-pa0", " --bg-layer", "r9k-raw")),
        row("c-rawv", "control", LAYER + " reads:rows,layer",
            PROBE % ("r9k-pa1", " --bg-layer", "r9k-raw")),
    ]


def tex_row(name, sset, pokes, extra=""):
    return row(name, sset, LAYER + " expectdiff", TEX + kp(pokes) + extra), pokes


HALF, QUARTER, THREEQ = M.bits(0.5), M.bits(0.25), M.bits(0.75)


def fit_pokes():
    out = [("f-b%d-h" % w, {w: HALF}) for w in range(3, 9)]
    out += [("f-b%d-q" % w, {w: QUARTER}) for w in range(3, 9)]
    out += [("f-b34-q", {3: QUARTER, 4: QUARTER}), ("f-b58-t", {5: THREEQ, 8: THREEQ})]
    return out


def heldout_pokes(mask, n=30):
    rng = random.Random(SEED)
    seen, out = set(), []
    while len(out) < n:
        k = rng.choice((1, 2, 3))
        words = sorted(rng.sample(range(3, 9), k))
        spec = {w: rng.choice(EIGHTHS) for w in words}
        key = tuple(sorted(spec.items()))
        if key in seen or all(M.CTRL[w] == v for w, v in spec.items()):
            continue
        seen.add(key)
        vm = M.predict_tex("H-VM", spec, mask)
        if len(vm) < 0.4 * len(mask):           # in range and off the texel edges
            continue
        d, both = M.differ(vm, M.predict_tex("H-NOREAD", spec, mask))
        if not both or d < 0.2 * both:
            continue
        out.append(("h%02d" % (len(out) + 1), spec))
    return out


def s1n():
    return [tex_row("n-b%d" % w, "fit", {w: HALF}) for w in range(3, 9)]


def s1(mask):
    return ([tex_row(n, "fit", p) for n, p in fit_pokes()]
            + [tex_row(n, "heldout", p) for n, p in heldout_pokes(mask)])


# s2: the vertex words 15-22: a move of 16 px (outward where one word can) and one bit flip each
# (E590's decoding), then four two-word moves. Words 19 and 22 decode to nothing.
S2 = [
    ("v-b15-m", {15: 0x000ff000}),      # TL y -16
    ("v-b15-x", {15: 0x00000000}),      # TL y bit 20 flipped: -4096
    ("v-b16-m", {16: 0x00000ff0}),      # TL x -16
    ("v-b16-x", {16: 0x00000000}),      # TL x bit 20 flipped: -4096
    ("v-b17-m", {17: 0x10000000}),      # TR y +16 (one word cannot move it up)
    ("v-b17-x", {17: 0x01000000}),      # TR y bit 8 flipped: +1
    ("v-b18-m", {18: 0x10500010}),      # TR x 80
    ("v-b18-x", {18: 0x10c00010}),      # TR x bit 15 flipped: 192
    ("v-b19-m", {19: 0x00001000}),      # no vertex under the decoding
    ("v-b19-x", {19: 0x80000000}),
    ("v-b20-m", {20: 0x00105000}),      # BL y 80
    ("v-b20-x", {20: 0x0010c000}),      # BL y bit 15 flipped: 192
    ("v-b21-m", {21: 0x00000ff0}),      # BL x -16
    ("v-b21-x", {21: 0x00001001}),      # BL x bit 8 flipped: +1
    ("v-b22-m", {22: 0x00001000}),      # no vertex under the decoding
    ("v-b22-x", {22: 0x80000000}),
    ("v-tl", {15: 0x000ff000, 16: 0x00000ff0}),     # TL (-16, -16)
    ("v-box80", {18: 0x10500010, 20: 0x00105000}),  # TR x 80, BL y 80
    ("v-u96", {16: 0x00000ff0, 18: 0x10500010}),    # TL x -16, TR x 80
    ("v-v96", {15: 0x000ff000, 20: 0x00105000}),    # TL y -16, BL y 80
]


def s2():
    return [tex_row(n, "heldout", p) for n, p in S2]


# s3 (explore, Q066): words 9-14 and the format word, then bgobj_words[1] (cmd:24, one attribute
# row today: 0x30001) at 0, 1 and 4 rows; every 0xffffffff last (E209: the format word at
# 0xffffffff made every pixel texel (0, 0) in a copy)
S3 = ([("e-b9-one", {9: M.ONE})]
      + [("e-b10-%x" % v, {10: v}) for v in (0x0, 0x404, 0x101, 0xffff, 0x10000, 0x80000000, 0x202)]
      + [("e-b%d-one" % w, {w: M.ONE}) for w in range(11, 15)])
S3_ROWS = [("e-rows0", 0x30000), ("e-rows1", 0x30001), ("e-rows4", 0x30004)]
S3_LAST = [("e-b9-ff", {9: 0xffffffff})] + [("e-b%d-ff" % w, {w: 0xffffffff})
                                            for w in range(11, 15)] + [("e-b10-ff", {10: 0xffffffff})]


def s3():
    out = [tex_row(n, "explore", p) for n, p in S3]
    out += [(row(n, "explore", LAYER + " expectdiff", TEX + " --poke cmd:24=0x%05x" % v),
             {"cmd24": v}) for n, v in S3_ROWS]
    out += [tex_row(n, "explore", p) for n, p in S3_LAST]
    return out


def s4():
    return [
        row("c-tex2", "control", LAYER + " expectdiff reads:job,diff,inplace,layer",
            TEX + " --words $W"),
        row("c-off2", "control", "expectdiff reads:job,hash,diff", OFF),
    ]


def all_rows(mask):
    """{stage: [(row, pokes or None)]}."""
    return {"s0t": [(r, None) for r in s0t()], "s0p": [(r, None) for r in s0p()],
            "s1n": s1n(), "s1": s1(mask), "s2": s2(), "s3": s3(),
            "s4": [(r, None) for r in s4()]}


# ---- the predictions -------------------------------------------------------------------------
HDR = "case\tquantity\tvalue\tmodel\tset\tsource\n"
SRC_PLAN = "exp-k1-r9.md s3"


def models_for(stage, pokes):
    if stage == "s2":
        return ("H-VM", "H-VPLANE")
    if stage == "s3":
        if pokes == {10: 0xffffffff}:
            return ("H-VM", "H-17")             # H-17's picture: every pixel texel (0, 0) (E209)
        if pokes.get("cmd24") == 0x30000:
            return ("H-VM", "H-NOTEX")
        return ("H-VM",)
    if stage == "s1n":
        return ("H-NONE", "H-VM")
    return ("H-VM", "H-LM", "H-SWAP", "H-NOREAD", "H-NONE", "H-17")


def predictions(stage, rows, mask):
    out = [HDR]
    for r, pokes in rows:
        n, sset = r["name"], r["set"]
        if pokes is None:
            out += control_predictions(n, sset)
            continue
        bgp = {w: v for w, v in pokes.items() if isinstance(w, int)}
        for m in models_for(stage, pokes):
            out.append("%s\ttexmap\t%s\t%s\t%s\t%s\n" % (n, M.map_id(M.predict_tex(m, bgp, mask)),
                                                        m, sset, SRC_PLAN))
        for w, v in sorted(bgp.items()):
            out.append("%s\treadback\tbg:%d=0x%08x\tH-REACH\t%s\tE590 (140 of 140 read back)\n"
                       % (n, w, v, sset))
    return "".join(out)


def control_predictions(n, sset):
    E = "E590"
    obj = ",".join("0x%x" % M.CTRL[w] for w in range(3, 11))
    p = {
        "c-off": [("hash", M.HASH_OFF, "H-CTL", E), ("diff", "0", "H-CTL", E)],
        "c-off2": [("hash", M.HASH_OFF, "H-CTL", E), ("diff", "0", "H-CTL", E)],
        "c-tex": [("layers", "1", "H-BUILT", "fork fafea977"),
                  ("obj3_10", obj, "H-BUILT", "fork fafea977"),
                  ("texmap", "identity>=3000/3034", "H-TEX", "E209, exp-k1-r9.md s2")],
        "c-tex2": [("layers", "1", "H-BUILT", "fork fafea977"),
                   ("obj3_10", obj, "H-BUILT", "fork fafea977"),
                   ("texmap", "identity>=3000/3034", "H-TEX", "E209, exp-k1-r9.md s2")],
        "c-noop": [("readback", "bg:5=0x3f800000", "H-REACH", E),
                   ("texmap", "identity>=3000/3034", "H-TEX", "E209")],
        "c-pos-off": [("pos", "f32(x+0.5)>=3000/3034", "H-POS", "E437, E442")],
        "c-pos": [("pos", "f32(x+0.5)>=3000/3034", "H-POS", "E437, E442")],
        "c-rawu": [("raw", "(x+0.5)/64+-2^-12>=3000/3034", "H-ITER", "E131, E437, E709"),
                   ("raw", "(y+0.5)/64", "H-SWAP", "rival"), ("raw", "(y+0.5)/64", "H-LM", "rival"),
                   ("raw", "one value", "H-NONE", "rival"), ("raw", "0", "H-17", "rival")],
        "c-rawv": [("raw", "(y+0.5)/64+-2^-12>=3000/3034", "H-ITER", "E131, E437, E709"),
                   ("raw", "(x+0.5)/64", "H-SWAP", "rival"), ("raw", "(y+0.5)/64", "H-LM", "rival"),
                   ("raw", "one value", "H-NONE", "rival"), ("raw", "0", "H-17", "rival")],
    }[n]
    return ["%s\t%s\t%s\t%s\t%s\t%s\n" % (n, q, v, m, sset, s) for q, v, m, s in p]


# ---- the files -------------------------------------------------------------------------------
def producible(r):
    a = r["args"].split()
    layer = {"inplace", "layer"} if "--bg-layer" in a else set()
    if a[:1] == ["tri"]:
        return {"job", "hash", "diff"} | layer
    if a[:2] == ["probe", "--tri"] and "--pixels" in a:
        return {"rows"} | ({"layer"} if "--bg-layer" in a else set())
    return set()


def files():
    import gzip
    out = {}
    text = gzip.decompress(git_show("data", MASK_SRC)).decode()
    out["gen/bgmask.txt"] = "\n".join(M.mask_lines_from_rows(M.tri_rows(text))) + "\n"
    mask = [(x, y) for y, ln in enumerate(out["gen/bgmask.txt"].split()) for x, c in enumerate(ln)
            if c == "."]
    rows = all_rows(mask)
    for st in STAGES:
        lines = ["#stage %s\n#limit 0\n" % st]
        lines += ["%s|%s|%s|%s|%s|%s\n" % (r["name"], r["set"], r["risk"], r["knobs"], r["tool"],
                                            r["args"]) for r, _ in rows[st]]
        out["tables/%s.txt" % st] = "".join(lines)
        out["predictions/%s.tsv" % st] = predictions(st, rows[st], mask)
    return out


def assemble():
    """{bins/NAME.bin: bytes} from the pinned templates with debug/asm's assemblers."""
    import tempfile
    out = {}
    with tempfile.TemporaryDirectory(dir=os.path.join(KP, "debug")) as d:
        for name, (tpl, asm) in PROGS.items():
            src = os.path.join(d, name + ".s")
            open(src, "wb").write(git_show("resgx545", tpl))
            dst = os.path.join(d, name + ".bin")
            subprocess.run([os.path.join(ASM, asm), "-o", dst, src], check=True,
                           capture_output=True, timeout=60)
            out["bins/%s.bin" % name] = open(dst, "rb").read()
    return out


def main(argv):
    want = files()
    if os.path.exists(os.path.join(ASM, "pds-asm")):
        want.update(assemble())
    elif "--check" not in argv:
        print("no debug/asm assemblers: run tests/run_all.sh once (it builds them)")
        return 1
    bad = []
    for path, data in sorted(want.items()):
        p = os.path.join(KP, path)
        b = data if isinstance(data, bytes) else data.encode()
        if "--check" in argv:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                bad.append(path)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(b)
    if bad:
        print("not current: " + ", ".join(bad))
        return 1
    # the generator's side of the control rule (scorekit.refuse_unreadable)
    for st in STAGES:
        scorekit.refuse_unreadable(K.controls(KP, st), producible)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
