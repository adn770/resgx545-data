#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r29-flag's tables, predictions and bins (closing29/plan/rank-round29.md sections 1
and 3; closing29/DECISIONS-R29.md: the user approved this flagged session, R29-1 to R29-6 (a), the
#limits counting only planned rows and capped at 14). Standard library only. Every input is read
at the data commit of session.toml [freeze] (`git show`, never the working tree) and pinned there.

  python3 gen/make.py          write tables/STAGE.txt, predictions/STAGE.tsv, bins/, mock/kept/
  python3 gen/make.py --check  exit 1 when a written file is not what the generator writes

Stages in run order (README.md): s0 the safe references (each gates its own stage, score.py
GATES), then f1 Q108 (both flags on a read), f2 Q139 (the page of the TA's empty-axis write), h1
Q010 (the colour-space set across recovered hangs; its first copy reads the set after f1's and
f2's recovered faults), h2 Q163 (O29-2's H-PREV16, fit/o29_2.out; its first row is h1's last
Q010 copy, which the kit cannot run after h1's last planned hang). f3 (Q241) and f4 (Q112) are
not built (README.md deviations 1 and 2). A planned row is an `expectfault` row that is not a
control; #limit counts exactly those (E946); the last row of every flagged stage is one."""
import gzip
import hashlib
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
DATA_COMMIT = CFG["freeze"]["data"]
DATA = os.environ.get("RESGX545_DATA_REPO", "/Users/jtorra/src/resgx545-data")

# ---- the kept records the controls are frozen on (pinned in session.toml) -------------------
BIF = "render/closing-r14-bif/out/20261114-055414/refill"      # E1046's rf-c-depth
FLAG = "render/closing-r14-flag/out/20261114-060824"           # E1047's f1-ref-a, E1048's f2-ctl-256
CSC = "render/closing-r25-csc/out/20261115-213805/csc"         # E1103's copies (zeros, BT.601)
PK = "render/closing-r23-pk/out/20261115-202948/q181"          # E1097's c-copy-none after c-copy-csc
BINS = {"f1-ref-a.bin": "render/closing-r14-flag/bins/f1-ref-a.bin",            # E566's tx_map
        "p1139-green.bin": "render/closing-s1b/bins/p1139-green.bin",           # E414's, E737's program
        "p1131-green__0.bin": "render/closing-r13-flag/bins/p1131-green__0.bin",  # E700's stream
        "p1131-blue__0.bin": "render/closing-r13-flag/bins/p1131-blue__0.bin"}
MOCK = {"rf-c-depth.depth-store.1.bin.gz": f"{BIF}/rf-c-depth.depth-store.1.bin.gz",
        "f1-ref-a.txt.gz": f"{FLAG}/f1/f1-ref-a.txt.gz"}
KEPT = [f"{BIF}/rf-c-depth.depth-store.1.bin.gz", f"{BIF}/rf-c-depth.txt.gz", f"{FLAG}/f1/f1-ref-a.txt.gz",
        f"{FLAG}/f2/f2-ctl-256.txt.gz", f"{CSC}/y28-zc.txt.gz", f"{CSC}/y28-bc.txt.gz",
        f"{PK}/c-copy-csc.txt.gz", f"{PK}/c-copy-none.txt.gz"]


def data(path):
    return subprocess.run(["git", "-C", DATA, "show", f"{DATA_COMMIT}:{path}"], check=True,
                          capture_output=True).stdout


def gunz(path):
    return gzip.decompress(data(path))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def line_of(text, start):
    return next(ln for ln in text.splitlines() if ln.startswith(start))


def image_sha(text):
    """The sha256 of a probe's `row Y:` tokens (8 hex digits each, raster order, one space)."""
    toks = []
    for ln in text.splitlines():
        if ": row " in ln or ln.startswith("row "):
            toks += [t.lower().zfill(8) for t in ln.split(": ", 2)[-1].split()]
    return sha(" ".join(toks).encode())


# ---- the kernel's TA data layout (fork 456404fc sgx_render.c: sgx_render_layout and
# sgx_render_tadata_layout_in, one region-header array, the 1x tail room) ---------------------
def cdiv(a, b):
    return -(-a // b)


def rup(a, b):
    return cdiv(a, b) * b


def layout(w, h):
    tx, ty = cdiv(w, 32), cdiv(h, 16)
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = rup(cdiv(tx, n), 4), rup(cdiv(ty, n), 4)
    span, side = max(n * mx, n * my), 1
    while side < span:
        side <<= 1
    bpm = (mx // 4) * (my // 4)
    rgn_size = 0xC0 * bpm * n * n
    tail = rup(4 * side * side, 0x1000)
    rgn = tail + 3 * 0x1000
    size = rgn + rup(rgn_size, 0x1000) + rup(rgn_size, 0x1000)
    m1 = (mx << 22) | (mx << 12) | mx if n == 2 else None
    m2 = (my << 22) | (my << 12) | my if n == 2 else None
    return dict(n=n, mx=mx, my=my, rgn=rgn, size=size, m1=m1, m2=m2)


TA_BASE = 0x20000000
L256, L384, L512 = layout(256, 256), layout(384, 256), layout(512, 512)
assert L256["size"] == L384["size"] == 0x6000 and L512["size"] == 0x8000 and L512["n"] == 2
assert L256["rgn"] == L384["rgn"] == L512["rgn"] == 0x4000
# f2's words: the size's own CR_TE_MTILE1 / MTILE2 with B2 (bits 21:12) cleared, the axis's every
# bound 0 at n = 2 (E509's q100-256x256-m1-B2-0 and -m2-B2-0 form; E1073's H-KIND: 0x90004)
X512 = L512["m1"] & ~(0x3FF << 12)
Y512 = L512["m2"] & ~(0x3FF << 12)
assert (X512, Y512) == (0x02000008, 0x04000010)

# ---- the job forms ---------------------------------------------------------------------------
RF = ('tri -n 2 --keep-going --wait-ms 20000 --width 64 --height 32 --max-width 64 --max-height 32 '
      '--tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl 0x0017500e --depth-fill index --depth-store '
      '--depth-store-fill 0x3e800000 --depth-pages 20 --depth-dump "$W" --poke blk:1=0x00000200')
TEX = 'probe --temps 32 --coords --pixels --scratch-pages 256 "$S/bins/f1-ref-a.bin"'
TRI = ('tri --tri-full --pixels --width {w} --height {h} --max-width {w} --max-height {h}{poke} '
       '--wait-ms 20000 --keep-going --dump-render "$W"')
B24 = 'probe --tri pixel --vertices 15 --copy-depth --pixels --vdm 2^=0x01000000 "$S/bins/p1139-green.bin"'
COPY = 'copy --every-value --pixels --poke tex:1=0x7d03f01f --poke tex:0^=0x90'
BT601 = (0x00950095, 0x00000095, 0x010203CE, 0x039800CC, 0)


def load(words):
    return COPY + " --poke xfer:17^=0x1" + "".join(f" --poke xfer:{18 + i}={w:#x}" if w else
                                                   f" --poke xfer:{18 + i}=0" for i, w in enumerate(words))


LOAD0, LOADBT = load((0,) * 5), load(BT601)
E700 = ('probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 '
        '--obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/bins/p1131-green__0.bin"')
BLUE = ' "$S/bins/p1131-blue__0.bin"'


def e700(v1=2, v2=2):
    """E700's two-block stream with block 1 at v1 and block 2 at v2 (bits 11:9, base 2)."""
    vdm = (f" --vdm 1^={(2 ^ v1) << 9:#010x}" if v1 != 2 else "") + \
          (f" --vdm 9^={(2 ^ v2) << 9:#010x}" if v2 != 2 else "")
    return E700 + vdm + BLUE


WOEDM = "0x12"
DEPTH_AT, SCRATCH_AT = "0x3e001000", "0x3e003000"


def knob(addr):
    return f"dbg:vm_pte_addr={addr} dbg:vm_pte_flags={WOEDM}"


# h2 (O29-2, fit/o29_2.out): (name, set, risk, knobs, v1, v2); the triples' c by M1 and the job
# before each block-2 v = 1 row are what the frozen deciders read
H2_ROWS = [("h2-c-a", "prime", "safe", "-", 6, 2), ("h2-c-b", "control", "safe", "noreset reads:o0", 6, 2),
           ("h2-a3", "heldout", "risky", "noreset expectfault", 2, 1),
           ("h2-b1", "prime", "safe", "-", 2, 2), ("h2-b2", "prime", "safe", "noreset", 5, 2),
           ("h2-b3", "heldout", "risky", "noreset expectfault", 2, 1),
           ("h2-c1", "prime", "safe", "-", 2, 2), ("h2-c2", "prime", "safe", "noreset", 3, 2),
           ("h2-c3", "heldout", "risky", "noreset expectfault", 2, 1)]


# (name, set, risk, knobs, tool, args): the rows of each stage in run order
def stages():
    s0 = [
        ("rf-c-depth", "control", "safe", "expectdiff reads:job,zstore,depthat", "t14", RF),
        ("f1-ref-a", "control", "safe", "reads:pixels,scratchat", "t14", TEX),
        ("f2-ctl-256", "control", "safe", "expectdiff reads:job,hash,tadata", "t10", TRI.format(w=256, h=256, poke="")),
        ("c-512", "control", "safe", "expectdiff reads:job,tadata", "t10", TRI.format(w=512, h=512, poke="")),
        ("c10-zc", "control", "safe", "expectdiff reads:job,hash", "t22", LOAD0),
        ("c10-zn", "control", "safe", "expectdiff reads:job,hash", "t22", COPY),
        ("c10-bc", "control", "safe", "expectdiff reads:job,hash", "t22", LOADBT),
        ("c10-bn", "control", "safe", "expectdiff reads:job,hash", "t22", COPY),
    ]
    f1 = [("q108-both-load", "heldout", "risky", f"{knob(DEPTH_AT)} expectfault expectdiff", "t14", RF),
          ("q108-both-tex", "heldout", "risky", f"{knob(SCRATCH_AT)} expectfault", "t14", TEX)]
    f2 = [("f2-x512", "heldout", "risky", "expectfault expectdiff", "t10",
           TRI.format(w=512, h=512, poke=f" --kpoke-render 1:ta:143={X512:#010x}")),
          ("f2-y512", "heldout", "risky", "expectfault expectdiff", "t10",
           TRI.format(w=512, h=512, poke=f" --kpoke-render 1:ta:144={Y512:#010x}"))]
    h1 = [("q010-af", "heldout", "safe", "expectdiff", "t22", COPY),
          ("q010-ld2", "control", "safe", "expectdiff reads:job,hash", "t22", LOADBT),
          ("q010-pre", "control", "safe", "expectdiff reads:job,hash", "t22", COPY),
          ("q010-h1", "heldout", "risky", "expectfault", "t10", B24),
          ("q010-p1", "heldout", "safe", "expectdiff", "t22", COPY),
          ("q010-h2", "heldout", "risky", "expectfault", "t10", B24)]
    h2 = [("q010-p2", "heldout", "safe", "expectdiff", "t22", COPY)]
    h2 += [(n, st, risk, k, "t10", e700(v1, v2)) for n, st, risk, k, v1, v2 in H2_ROWS]
    return {"s0": s0, "f1": f1, "f2": f2, "h1": h1, "h2": h2}


HEAD = {
    "s0": ["r29-flag s0: the safe references (rank-round29.md section 3), each gating only its own stage (score.py "
           "GATES): rf-c-depth (E1046's kept store, the depth buffer at 0x3e001000) and f1-ref-a (E1047's kept image, "
           "the scratch at 0x3e003000) gate f1; f2-ctl-256 (E1048's hash, TA data 24576 bytes) and c-512 (512 x 512 "
           "unpoked: job ok, TA data 32768 bytes, the kernel's layout, the premise of f2's H-SIZE) gate f2; the four "
           "copies c10-zc, c10-zn, c10-bc, c10-bn (E1103's and E1097's forms on t22: a load of zeros then no load read "
           "black 0xd3522437a14b6325, a load of BT.601 then no load read E037's 0xb6067a95fa98de2d) gate h1.",
           "Safe class: no expectfault, #limit 0; any fault or hang stops the session (4). A control without its reading "
           "stops it (25); a reading that differs closes its stage's gate only."],
    "f1": ["r29-flag f1, Q108 (E1108): WRITEONLY and EDMPROTECT together (vm_pte_flags 0x12) on a mapping only read: "
           "r14-bif's ZLS load of the depth buffer (0x3e001000) and E566's texture read of the probe's scratch "
           "(0x3e003000), both t14. PLANNED FAULTS (user OK, DECISIONS-R29).",
           "Frozen: H-WO-READ (as WRITEONLY alone, E1071: 0x80200 at 0x3e001000, 0x80002 at 0x3e003000) against "
           "H-EDM-TYPE (EDMPROTECT's type takes over as on writes, E965: 0xa0200, 0xa0002) and H-PASS (both complete, "
           "E1046's store, E1047's image). #limit 2 = both rows (expectfault); hook_fault stops on a hang, a fault "
           "without its BIF line or SGX recovery failed (24, on_stop end)."],
    "f2": ["r29-flag f2, Q139 (E1109): an empty-axis CR_TE_MTILE1 (x) and CR_TE_MTILE2 (y) word at 512 x 512 (n = 2, "
           "TA data 0x8000 bytes by the kernel's layout; 256 x 256 and 384 x 256 have 0x6000), E1074's form on t10, "
           "words never run. PLANNED FAULTS (user OK).",
           "Kind: E1073's H-KIND 0x90004 on both (third and fourth held-out words). Page: H-AXIS (fixed by the axis at "
           "n = 2: x 0x20008, y 0x20010, E509 E1074) against H-SIZE (it moves with the TA data's end: x end + 2 pages "
           "0x2000a, y end + 10 pages 0x20012) [infer]. #limit 2."],
    "h1": ["r29-flag h1, Q010 (E1112): does a recovered fault or hang clear colour-space set 0? E1103's copies on t22 "
           "(no load: the set last loaded). q010-af is the first copy after f1's and f2's recovered faults (the last "
           "load c10-bc in s0); q010-ld2 loads BT.601 (control), q010-pre reads it back (control); then E737's bit-24 "
           "hang (t10, PLANNED HANG, user OK) and a copy after it, twice (the second copy is h2's first row).",
           "Frozen: H-KEEP (each held-out copy reads 0xb6067a95fa98de2d) against H-RECOV-CLR (0xd3522437a14b6325). "
           "#limit 2 = the two hangs (expectfault, the last row); a fault instead stops the stage (24, on_stop end)."],
    "h2": ["r29-flag h2: q010-p2 (Q010, the copy after h1's second hang), then Q163 (E1113): what decides a block-2 "
           "v = 1 job (VDM_STATE1 bits 11:9 = 1 in block 2, E700's stream on t10). O29-2 (fit/o29_2.out) froze "
           "H-PREV16 (it completes iff the job right before, no reset between, completed with a block at v 1 or 6; "
           "post hoc on all 18 kept jobs) against D-PREVADD (a non-zero add before; the fit set's own form, 15 of 15, "
           "E1035 1 of 3), D-C (c alone) and H-ALWAYS (every such job hangs on this module family). PLANNED HANGS "
           "(user OK). Kit word noreset.",
           "Triples from a reset: (6,2) (6,2) (2,1) (control h2-c-b: c = 8 under M1, completes; the third is E701's "
           "c = 8 completion held out), (2,2) (5,2) (2,1) and (2,2) (3,2) (2,1) (a v 5 and a v 3 job before, never "
           "run before a block-2 v = 1). H-PREV16: ok, hang, hang; D-PREVADD and D-C: ok, ok, ok; H-ALWAYS: hang x 3. "
           "#limit 3 = the three (2,1) rows (expectfault); 2 planned, the last row is one."],
}


# ---- the frozen predictions ------------------------------------------------------------------
# (case, quantity, value, model, set, source); quantities: end (ok, fault, hang), fstat (the
# kernel's first `BIF fault S at A` S), fpage (A & ~0xfff), image (the probe image's sha256), hash
# (a copy's `target:` hash), o0 (presence), and the controls' reading keys (readings.tsv)
def predictions():
    t = {k: [] for k in stages()}
    zc = line_of(gunz(f"{CSC}/y28-zc.txt.gz").decode(), "target: ").split()[3]
    bc = line_of(gunz(f"{CSC}/y28-bc.txt.gz").decode(), "target: ").split()[3]
    none = line_of(gunz(f"{PK}/c-copy-none.txt.gz").decode(), "target: ").split()[3]
    assert line_of(gunz(f"{PK}/c-copy-csc.txt.gz").decode(), "target: ").split()[3] == bc == none
    ref = {
        "rf-c-depth": {"job": "ok", "zstore": sha(gunz(f"{BIF}/rf-c-depth.depth-store.1.bin.gz")),
                       "depthat": line_of(gunz(f"{BIF}/rf-c-depth.txt.gz").decode(), "depth: 0x").split()[1]},
        "f1-ref-a": {"pixels": "32", "scratchat": SCRATCH_AT,
                     "image": image_sha(gunz(f"{FLAG}/f1/f1-ref-a.txt.gz").decode())},
        "f2-ctl-256": {"job": "ok", "hash": line_of(gunz(f"{FLAG}/f2/f2-ctl-256.txt.gz").decode(),
                                                    "target: ").split()[3], "tadata": str(L256["size"])},
        "c-512": {"job": "ok", "tadata": str(L512["size"])},
        "c10-zc": {"job": "ok", "hash": zc}, "c10-zn": {"job": "ok", "hash": zc},
        "c10-bc": {"job": "ok", "hash": bc}, "c10-bn": {"job": "ok", "hash": bc},
    }
    src = {"rf-c-depth": "E1046 (r14-bif refill kept)", "f1-ref-a": "E1047 (r14-flag f1 kept), E566",
           "f2-ctl-256": "E1048 (r14-flag f2 kept; TA data 24576 bytes, E1007)",
           "c-512": "the kernel's TA data layout at 512 x 512 (fork 456404fc sgx_render.c) [infer]",
           "c10-zc": "E1103 (r25-csc kept y28-zc)", "c10-zn": "E1103 (a copy without the load keeps the set)",
           "c10-bc": "E1103 (r25-csc kept y28-bc), E037", "c10-bn": "E1097 (r23-pk kept c-copy-none after c-copy-csc)"}
    assert ref["f1-ref-a"]["scratchat"] in gunz(f"{FLAG}/f1/f1-ref-a.txt.gz").decode()
    assert ref["rf-c-depth"]["depthat"] == DEPTH_AT
    assert "24576 bytes" in gunz(f"{FLAG}/f2/f2-ctl-256.txt.gz").decode()
    for n, q in ref.items():
        for k, v in q.items():
            t["s0"].append((n, k, v, "H-REF", "control", src[n]))
    # f1: the ends and fault words of the two rows
    img = ref["f1-ref-a"]["image"]
    for n, m, end, stat, addr in (
            ("q108-both-load", "H-WO-READ", "fault", "0x80200", DEPTH_AT),
            ("q108-both-tex", "H-WO-READ", "fault", "0x80002", SCRATCH_AT),
            ("q108-both-load", "H-EDM-TYPE", "fault", "0xa0200", DEPTH_AT),
            ("q108-both-tex", "H-EDM-TYPE", "fault", "0xa0002", SCRATCH_AT),
            ("q108-both-load", "H-PASS", "ok", None, None), ("q108-both-tex", "H-PASS", "ok", None, None)):
        s = "E1071 (WRITEONLY alone on these reads), E965 (both flags on a write: EDMPROTECT's type)"
        t["f1"].append((n, "end", end, m, "heldout", s))
        if stat:
            t["f1"].append((n, "fstat", stat, m, "heldout", s))
            t["f1"].append((n, "fpage", addr, m, "heldout", s))
        if n == "q108-both-tex" and end == "ok":
            t["f1"].append((n, "image", img, m, "heldout", "E1047's kept f1-ref-a image"))
    # f2: the kind (H-KIND) and the page (H-AXIS, H-SIZE), scored as separate models
    end512 = TA_BASE + L512["size"]
    for n in ("f2-x512", "f2-y512"):
        s = "E1073 (fit/o18_1.out, H-KIND 162 of 162), E1074"
        t["f2"] += [(n, "end", "fault", "H-KIND", "heldout", s), (n, "fstat", "0x90004", "H-KIND", "heldout", s)]
    for n, m, page, s in (
            ("f2-x512", "H-AXIS", 0x20008000, "E509 (256 x 256), E1074 (384 x 256): x side 0x20008"),
            ("f2-y512", "H-AXIS", 0x20010000, "E509 (256 x 256, 640 x 480): y side 0x20010"),
            ("f2-x512", "H-SIZE", end512 + 0x2000, "E1074: 0x20008 = the end of 0x6000 bytes + 2 pages [infer]"),
            ("f2-y512", "H-SIZE", end512 + 0xA000, "E509: 0x20010 = the end of 0x6000 bytes + 10 pages, its layout "
                                                   "assumed the kernel's [infer]")):
        t["f2"] += [(n, "end", "fault", m, "heldout", s), (n, "fpage", f"{page:#x}", m, "heldout", s)]
    # h1 and h2's q010-p2: the copies after a recovery
    for n, st in (("q010-af", "heldout"), ("q010-p1", "heldout"), ("q010-p2", "heldout")):
        t["h1" if n != "q010-p2" else "h2"] += [
            (n, "end", "ok", "H-KEEP", st, "a copy completes (E1097, E1103)"),
            (n, "hash", bc, "H-KEEP", st, "E1097 E1103 (the set survives a debugfs reset and the health), E399; "
                                         "fork 456404fc: a recovery runs the reset a debugfs reset runs [infer]"),
            (n, "end", "ok", "H-RECOV-CLR", st, "a copy completes (E1097, E1103)"),
            (n, "hash", zc, "H-RECOV-CLR", st, "E271 (zeros after hung jobs) [infer]")]
    for n in ("q010-ld2", "q010-pre"):
        t["h1"] += [(n, "job", "ok", "H-REF", "control", "E1103"), (n, "hash", bc, "H-REF", "control", "E1103 E1097")]
    for n in ("q010-h1", "q010-h2"):
        t["h1"].append((n, "end", "hang", "H-B24-HANG", "heldout", "E737 (bit 24 hung 2 of 2), E1075 (1 of 1)"))
    # h2: the ends of the triples under each decider (fit/o29_2.out)
    ends = {"H-PREV16": ("ok", "ok", "ok", "ok", "ok", "hang", "ok", "ok", "hang"),
            "D-PREVADD": ("ok",) * 9, "D-C": ("ok",) * 9,
            "H-ALWAYS": ("ok", "ok", "hang", "ok", "ok", "hang", "ok", "ok", "hang")}
    for m, e in ends.items():
        for (n, st, *_), v in zip(H2_ROWS, e):
            t["h2"].append((n, "end", v, m, st, "fit/o29_2.out (O29-2: E545, E701 fit; E1035) [post hoc]; "
                                                "E700's M1 for the other rows"))
    t["h2"].append(("h2-c-b", "o0", "present", "H-REF", "control", "E700's shape completes at c = 8 under M1 (E1076)"))
    return t


def outputs():
    out = {}
    for st, rows in stages().items():
        planned = [r for r in rows if "expectfault" in r[3].split() and r[1] != "control"]
        body = [f"#stage {st}", f"#limit {len(planned)}"] + [f"# {ln}" for ln in HEAD[st]]
        body += ["|".join(r) for r in rows]
        out[f"tables/{st}.txt"] = ("\n".join(body) + "\n").encode()
    for st, rows in predictions().items():
        body = ["case\tquantity\tvalue\tmodel\tset\tsource"] + ["\t".join(r) for r in rows]
        out[f"predictions/{st}.tsv"] = ("\n".join(body) + "\n").encode()
    for b, p in BINS.items():
        out[f"bins/{b}"] = data(p)
    for b, p in MOCK.items():
        out[f"mock/kept/{b}"] = data(p)
    return out


def main(argv):
    out = outputs()
    bad = []
    for rel, b in sorted(out.items()):
        p = os.path.join(KP, rel)
        if "--check" in argv:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                bad.append(rel)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b)
    if "--check" in argv:
        print("gen: current" if not bad else "gen: NOT current: " + ", ".join(bad))
        return 1 if bad else 0
    print("gen: wrote " + ", ".join(sorted(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
