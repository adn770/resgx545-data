#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r18-flag's tables, predictions and bins (closing18/plan/rank-round18.md sections 2
and 3; closing18/DECISIONS-R18.md: the user approved this flagged session, 8 faults and 3 hangs
planned, the #limits capped at 15). Standard library only. Every input is read at the data commit
of session.toml [freeze] (`git show`, never the working tree) and pinned there.

  python3 gen/make.py          write tables/STAGE.txt, predictions/STAGE.tsv, bins/
  python3 gen/make.py --check  exit 1 when a written file is not what the generator writes

Stages in run order (README.md): s0 the safe references (each gates its own stage, score.py
GATES), then f1 Q299, f2 Q108, f3 Q139 (O18-1 fitted, fit/o18_1.out), f4 Q241 bit 18, h1 Q112
bit 24, h2 Q163. A planned row is an `expectfault` row that is not a control; #limit counts exactly
those (E946); the last row of every flagged stage is a planned row."""
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
ZLS = "render/closing-r15-zls/out/20261114-073826/zovl"        # E1051's zv-c-g3 (E1041) and zv-g5
BIF = "render/closing-r14-bif/out/20261114-055414/refill"      # E1046's rf-c-depth
FLAG = "render/closing-r14-flag/out/20261114-060824"           # E1047's f1-ref-a, E1048's f2-ctl-256
ISP = "render/closing-r10-x/out/20261113-101116/isp0x"         # E998's x-ctl (E977's ramp)
IDX = "render/closing-s1b/out/g-e4w"                           # E756's ix32-n, E414's ix-c
BINS = {"f1-ref-a.bin": "render/closing-r14-flag/bins/f1-ref-a.bin",            # E566's tx_map
        "p1139-green.bin": "render/closing-s1b/bins/p1139-green.bin",           # E756's program
        "p1131-green__0.bin": "render/closing-r13-flag/bins/p1131-green__0.bin",  # E1035's
        "p1131-blue__0.bin": "render/closing-r13-flag/bins/p1131-blue__0.bin"}
# the kept files the mock's world answers the s0 controls with (mock/kept/, byte copies)
MOCK = {"zv-c-g3.depth.1.bin.gz": f"{ZLS}/zv-c-g3.depth.1.bin.gz", "zv-g5.depth.1.bin.gz": f"{ZLS}/zv-g5.depth.1.bin.gz",
        "rf-c-depth.depth-store.1.bin.gz": f"{BIF}/rf-c-depth.depth-store.1.bin.gz",
        "x-ctl.depth.1.bin.gz": f"{ISP}/x-ctl.depth.1.bin.gz", "f1-ref-a.txt.gz": f"{FLAG}/f1/f1-ref-a.txt.gz"}
KEPT = [f"{ZLS}/zv-c-g3.depth.1.bin.gz", f"{ZLS}/zv-c-g3.txt.gz", f"{ZLS}/zv-g5.depth.1.bin.gz",
        f"{ZLS}/zv-g5.txt.gz", f"{BIF}/rf-c-depth.depth-store.1.bin.gz", f"{BIF}/rf-c-depth.txt.gz",
        f"{FLAG}/f1/f1-ref-a.txt.gz", f"{FLAG}/f2/f2-ctl-256.txt.gz", f"{ISP}/x-ctl.depth.1.bin.gz",
        f"{ISP}/x-ctl.txt.gz", f"{IDX}/ix32-n-r1.txt.gz", f"{IDX}/ix-c.txt.gz"]


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


# ---- the job forms ---------------------------------------------------------------------------
ZV = ('tri --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 '
      '--tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl {ctl} --depth-fill 0xdeadbeef '
      '--depth-pages {pages} --depth-dump "$W" --poke blk:1=0x00400200 --kpoke-render 1:rd:13=0xd000')
RF = ('tri -n 2 --keep-going --wait-ms 20000 --width 64 --height 32 --max-width 64 --max-height 32 '
      '--tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl 0x0017500e --depth-fill index --depth-store '
      '--depth-store-fill 0x3e800000 --depth-pages 20 --depth-dump "$W" --poke blk:1=0x00000200')
TEX = 'probe --temps 32 --coords --pixels --scratch-pages 256 "$S/bins/f1-ref-a.bin"'
TRI = ('tri --tri-full --pixels --width {w} --height {h} --max-width {w} --max-height {h}{poke} '
       '--wait-ms 20000 --keep-going --dump-render "$W"')
RAMP = ('tri --keep-going --wait-ms 20000 --width 80 --height 40 --max-width 80 --max-height 40 '
        '--tri-v 0,0,40960,0,0,20480 --tri-z 1,0,1 --depth --depth-ctl 0x00171014 '
        '--depth-fill 0xdeadbeef --depth-dump "$W" --poke blk:1={blk}')
IX = ('probe --tri pixel --vertices 15 --copy-depth --pixels --index-width 32 '
      '--vdm 2^={vdm} "$S/bins/p1139-green.bin"')
SHAPE = {   # h2: E700's two-block stream (E1035's f3 form) and the two new shapes (plan h2)
    "e700": ('probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 '
             '--obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/bins/p1131-green__0.bin"'),
    "a": 'probe --tri pixel --temps 8 --pixels --width 64 --height 64 --vertices 24',
    "b": ('probe --tri pixel --temps 16 --pixels --width 128 --height 64 --vertices 48 --obj2 24 '
          '--obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/bins/p1131-green__0.bin"'),
}
V6 = ' --vdm 1^=0x00000800 "$S/bins/p1131-blue__0.bin"'   # block 1 at v = 6 ((6 ^ 2) << 9): add 4
WO, EDM = "0x2", "0x10"
DEPTH_AT, SCRATCH_AT = "0x3e001000", "0x3e003000"


def knob(addr, flags):
    return f"dbg:vm_pte_addr={addr} dbg:vm_pte_flags={flags}"


# (name, set, risk, knobs, tool, args): the rows of each stage in run order
def stages():
    s0 = [
        ("zv-c-g3", "control", "safe", "expectdiff reads:job,zdump,fb,depthat", "t10",
         ZV.format(ctl="0x0017101c", pages=20)),
        ("zv-g5-24", "control", "safe", "expectdiff reads:job,zdump,fb,depthat", "t10",
         ZV.format(ctl="0x0017102c", pages=24)),
        ("rf-c-depth", "control", "safe", "expectdiff reads:job,zstore,depthat", "t14", RF),
        ("f1-ref-a", "control", "safe", "reads:pixels,scratchat", "t14", TEX),
        ("f2-ctl-256", "control", "safe", "expectdiff reads:job,hash,tadata", "t10",
         TRI.format(w=256, h=256, poke="")),
        ("x-ctl", "control", "safe", "expectdiff reads:job,zdump,hash", "t10", RAMP.format(blk="0x00400200")),
        ("ix32-n", "control", "safe", "reads:bg,w32", "t10", IX.format(vdm="0x02000000")),
    ]
    f1 = [("q299-g3", "heldout", "risky", "expectfault expectdiff", "t10", ZV.format(ctl="0x0017101c", pages=16)),
          ("q299-g5", "heldout", "risky", "expectfault expectdiff", "t10", ZV.format(ctl="0x0017102c", pages=16))]
    f2 = [("q108-edm-load", "heldout", "risky", f"{knob(DEPTH_AT, EDM)} expectfault expectdiff", "t14", RF),
          ("q108-edm-tex", "heldout", "risky", f"{knob(SCRATCH_AT, EDM)} expectfault", "t14", TEX),
          ("q108-wo-load", "heldout", "risky", f"{knob(DEPTH_AT, WO)} expectfault expectdiff", "t14", RF),
          ("q108-wo-tex", "heldout", "risky", f"{knob(SCRATCH_AT, WO)} expectfault", "t14", TEX)]
    f3 = [("f3-k4", "heldout", "risky", "expectfault expectdiff", "t10",
           TRI.format(w=384, h=256, poke=" --kpoke-render 1:ta:143=0x00c00005")),
          ("f3-k100", "heldout", "risky", "expectfault expectdiff", "t10",
           TRI.format(w=384, h=256, poke=" --kpoke-render 1:ta:143=0x00406001"))]
    f4 = [("b18-lib", "heldout", "risky", "expectfault expectdiff", "t10", "tri --poke blk:1^=0x00040000"),
          ("b18-ramp", "heldout", "risky", "expectfault expectdiff", "t10", RAMP.format(blk="0x00440200"))]
    h1 = [("b24-w32", "heldout", "risky", "expectfault", "t10", IX.format(vdm="0x03000000"))]
    h2 = [("h2-c-a", "prime", "safe", "-", "t10", SHAPE["e700"] + V6),
          ("h2-c-b", "control", "safe", "noreset reads:o0", "t10", SHAPE["e700"] + V6),
          ("h2-a1", "prime", "safe", "-", "t10", SHAPE["a"] + V6),
          ("h2-a2", "heldout", "risky", "noreset expectfault", "t10", SHAPE["a"] + V6),
          ("h2-a3", "heldout", "risky", "noreset expectfault", "t10", SHAPE["a"] + V6),
          ("h2-b1", "prime", "safe", "-", "t10", SHAPE["b"] + V6),
          ("h2-b2", "heldout", "risky", "noreset expectfault", "t10", SHAPE["b"] + V6),
          ("h2-b3", "heldout", "risky", "noreset expectfault", "t10", SHAPE["b"] + V6)]
    return {"s0": s0, "f1": f1, "f2": f2, "f3": f3, "f4": f4, "h1": h1, "h2": h2}


HEAD = {
    "s0": ["r18-flag s0: the safe references (rank-round18.md section 3), one per flagged stage, each gating only its own stage "
           "(score.py GATES): zv-c-g3 and zv-g5-24 (E1041's and E1051's kept stores, byte for byte, and the colour buffer right "
           "after the depth buffer: f1's premise) gate f1; rf-c-depth (E1046's kept store, the depth buffer at 0x3e001000) and "
           "f1-ref-a (E1047's kept image, the scratch at 0x3e003000) gate f2; f2-ctl-256 (E1048's hash, TA data 24576 bytes) "
           "gates f3; x-ctl (E998's control: E977's kept dump and hash, on t10) gates f4; ix32-n (E756's bit-clear 32-bit "
           "list: every pixel the background, the 32-bit echo) gates h1.",
           "Safe class: no expectfault, #limit 0; any fault or hang stops the session (4). A control without its reading "
           "stops it (25); a reading that differs closes its stage's gate only."],
    "f1": ["r18-flag f1, Q299 (E1070): E411's G 3 and G 5 stores (E1051's zv- form, t10) with a 16-page depth buffer. PLANNED "
           "FAULT (user OK, DECISIONS-R18). Premise read from the kept outputs (README.md deviation 1): the colour buffer "
           "follows the depth buffer (fb = depth + pages, 5 pages with its guard), so G 3's pages 16 and 18 land in it and "
           "G 5's page 21 is the first unmapped one.",
           "Frozen: H-PAST-FAULT (g3 ok, g5 faults at depth + 0x15000), H-PAST-ANY (any store past the buffer faults: g3 at "
           "+0x10000, g5 at +0x12000), H-DROP (both ok). #limit 2 = both rows (expectfault); hook_fault stops on a hang, a "
           "fault without its BIF line or SGX recovery failed (24, on_stop end)."],
    "f2": ["r18-flag f2, Q108 (E1071): WRITEONLY (0x2) and EDMPROTECT (0x10) alone on a mapping only read: the ZLS load "
           "of r14-bif's rf-c-depth (depth buffer 0x3e001000, t14) and E566's texture read of the probe's scratch "
           "(0x3e003000, t14). PLANNED FAULTS (user OK). EDMPROTECT rows first.",
           "Frozen: H-WO-ALL (wo-load 0x80200 at 0x3e001000, wo-tex 0x80002 at 0x3e003000) with H-EDM-READ (both edm rows "
           "complete, the control's store and image); rivals H-WO-LOAD-OK, H-EDM-ZLS (0xa0200), H-EDM-TEX (0xa0002). "
           "#limit 4 = the four rows (expectfault); 2 planned."],
    "f3": ["r18-flag f3, Q139 (E1074): two CR_TE_MTILE1 words never run at 384 x 256 (n = 2, E1048's form, t10), held out "
           "on O18-1's kind form (E1073, fit/o18_1.out: H-KIND 162 of 162 of E509's faulting cases, H-ONE-KIND 155). "
           "PLANNED FAULTS (user OK).",
           "f3-k4 (B2 = 0, an empty x axis): H-KIND 0x90004 (the TA's header write) at TA data page 0x20006 (H-PAGE-END, "
           "the first page past the kernel's 0x6000) against H-ONE-KIND 0x90100 at 0x10000; f3-k100 (fx 6, a second "
           "macrotile inside): 0x90100 at 0x10000 under both. #limit 2."],
    "f4": ["r18-flag f4, Q241 bit 18 (E1072): ISP word 0 bit 18 alone on E065's library triangle and on E977's 80 x 40 "
           "ramp with its depth buffer loaded and stored (E998's isp0x form, t10). PLANNED FAULTS (user OK); the last "
           "fault stage.",
           "Frozen: H-FAULT-ANY (both fault with one FAULT_REQ bit) against H-NEEDS-BUF (the ramp draws, the library row "
           "faults) [infer, weak]. #limit 2."],
    "h1": ["r18-flag h1, Q112 (E1075): VDM index-list header bit 24 alone over E756's 32-bit list (--index-width 32 sets "
           "bit 25, --vdm 2^=0x03000000 clears it and sets 24; t10). PLANNED HANG (user OK).",
           "Frozen: H-B24-HANG (it hangs as over 16 bits, E737) against H-B24-W32 (bit 24 selects 32-bit indices: E414's "
           "object, ix-c's pixels). #limit 1; a fault instead of the hang stops the stage (24, on_stop end)."],
    "h2": ["r18-flag h2, Q163 (E1076): E700's counter M1 (a job adds the sum of v - 2 over its blocks, hangs iff c + add "
           "> 8) on two new stream shapes, block 1 at v = 6 (add 4): ok, ok (c = 8), hang. PLANNED HANGS (user OK). Kit "
           "word noreset.",
           "Control first: E700's shape, the triple's first two rows (both complete under M1; the second has no "
           "expectfault, so a hang there stops the stage, 4). Shape A: 24 vertices, one object, 8 temporaries, 64 x 64; "
           "shape B: 48 vertices, two objects, 16 temporaries, 128 x 64. Frozen: M1-SHAPE (each third row hangs) "
           "against H-ALT (E413's alternation: each second row hangs) and H-SCALE (no row hangs) [infer]. #limit 4 = "
           "rows 2 and 3 of each shape (expectfault); 2 planned, the last row is one."],
}


# ---- the frozen predictions ------------------------------------------------------------------
# (case, quantity, value, model, set, source); quantities: end (ok, fault, hang), fstat (the
# kernel's `BIF fault S at A` S, the row's first), fpage (A & ~0xfff), image (the probe image's
# sha256), o0 (the probe's `o0 ...` line), and the controls' reading keys (readings.tsv)
def predictions():
    t = {k: [] for k in stages()}
    zg3 = gunz(f"{ZLS}/zv-c-g3.txt.gz").decode()
    zg5 = gunz(f"{ZLS}/zv-g5.txt.gz").decode()
    ref = {
        "zv-c-g3": {"job": "ok", "zdump": sha(gunz(f"{ZLS}/zv-c-g3.depth.1.bin.gz")),
                    "fb": line_of(zg3, "layout: fb ").split()[2], "depthat": line_of(zg3, "depth: 0x").split()[1]},
        "zv-g5-24": {"job": "ok", "zdump": sha(gunz(f"{ZLS}/zv-g5.depth.1.bin.gz")),
                     "fb": line_of(zg5, "layout: fb ").split()[2], "depthat": line_of(zg5, "depth: 0x").split()[1]},
        "rf-c-depth": {"job": "ok", "zstore": sha(gunz(f"{BIF}/rf-c-depth.depth-store.1.bin.gz")),
                       "depthat": line_of(gunz(f"{BIF}/rf-c-depth.txt.gz").decode(), "depth: 0x").split()[1]},
        "f1-ref-a": {"pixels": "32", "scratchat": SCRATCH_AT,
                     "image": image_sha(gunz(f"{FLAG}/f1/f1-ref-a.txt.gz").decode())},
        "f2-ctl-256": {"job": "ok", "hash": line_of(gunz(f"{FLAG}/f2/f2-ctl-256.txt.gz").decode(),
                                                    "target: ").split()[3], "tadata": "24576"},
        "x-ctl": {"job": "ok", "zdump": sha(gunz(f"{ISP}/x-ctl.depth.1.bin.gz")),
                  "hash": line_of(gunz(f"{ISP}/x-ctl.txt.gz").decode(), "target: ").split()[3]},
        "ix32-n": {"bg": "4096", "w32": "1"},
    }
    src = {"zv-c-g3": "E1041 E1051 (r15-zls zovl kept zv-c-g3)", "zv-g5-24": "E1051 (r15-zls zovl kept zv-g5)",
           "rf-c-depth": "E1046 (r14-bif refill kept)", "f1-ref-a": "E1047 (r14-flag f1 kept), E566",
           "f2-ctl-256": "E1048 (r14-flag f2 kept; TA data 24576 bytes, E1007)", "x-ctl": "E998 E977 (r10-x isp0x kept)",
           "ix32-n": "E756 (s1b g-e4w kept ix32-n-r1)"}
    assert ref["f1-ref-a"]["scratchat"] in gunz(f"{FLAG}/f1/f1-ref-a.txt.gz").decode()
    assert ref["rf-c-depth"]["depthat"] == DEPTH_AT
    assert "o0 0xff203040 (4096 of 4096)" in gunz(f"{IDX}/ix32-n-r1.txt.gz").decode()
    for n, q in ref.items():
        for k, v in q.items():
            t["s0"].append((n, k, v, "H-REF", "control", src[n]))
    # f1: the ends decide Q299's clause (H-PAST-FAULT, H-PAST-ANY, H-DROP); the fault word and page
    # are a second reading, scored apart (the -PAGE models), never against the ends' verdict
    depth = int(DEPTH_AT, 16)
    s = "E991 E1041 E1051 page rule; fb after the depth buffer (kept zv-c-g3, zv-g5) [infer]"
    for n, m, end in (("q299-g3", "H-PAST-FAULT", "ok"), ("q299-g5", "H-PAST-FAULT", "fault"),
                      ("q299-g3", "H-PAST-ANY", "fault"), ("q299-g5", "H-PAST-ANY", "fault"),
                      ("q299-g3", "H-DROP", "ok"), ("q299-g5", "H-DROP", "ok")):
        t["f1"].append((n, "end", end, m, "heldout", s))
    for n, m, page in (("q299-g5", "H-PAST-FAULT-PAGE", 0x15000), ("q299-g3", "H-PAST-ANY-PAGE", 0x10000),
                       ("q299-g5", "H-PAST-ANY-PAGE", 0x12000)):
        t["f1"].append((n, "end", "fault", m, "heldout", s))
        t["f1"].append((n, "fpage", f"{depth + page:#x}", m, "heldout", s))
        t["f1"].append((n, "fstat", "0x90200", m, "heldout", "FAULT_REQ bit 9 (E965), FAULT_TYPE 1 (hw_spec 5.5) [infer]"))
    img = ref["f1-ref-a"]["image"]
    for n, m, end, stat, addr in (
            ("q108-wo-load", "H-WO-ALL", "fault", "0x80200", DEPTH_AT), ("q108-wo-tex", "H-WO-ALL", "fault", "0x80002", SCRATCH_AT),
            ("q108-wo-load", "H-WO-LOAD-OK", "ok", None, None),
            ("q108-edm-load", "H-EDM-READ", "ok", None, None), ("q108-edm-tex", "H-EDM-READ", "ok", None, None),
            ("q108-edm-load", "H-EDM-ZLS", "fault", "0xa0200", DEPTH_AT),
            ("q108-edm-tex", "H-EDM-TEX", "fault", "0xa0002", SCRATCH_AT)):
        s = "E945 E946 E964 E965"
        t["f2"].append((n, "end", end, m, "heldout", s))
        if stat:
            t["f2"].append((n, "fstat", stat, m, "heldout", s))
            t["f2"].append((n, "fpage", addr, m, "heldout", s))
        if n == "q108-edm-tex" and end == "ok":
            t["f2"].append((n, "image", img, m, "heldout", "E1047's kept f1-ref-a image"))
    # f3: the kind (end, fstat) is O18-1's held-out clause; the page is scored apart (H-PAGE-END)
    for n, m, stat in (("f3-k4", "H-KIND", "0x90004"), ("f3-k4", "H-ONE-KIND", "0x90100"),
                       ("f3-k100", "H-KIND", "0x90100"), ("f3-k100", "H-ONE-KIND", "0x90100")):
        s = "E1073 (fit/o18_1.out, H-KIND 162 of 162, H-ONE-KIND 155 of 162), E509"
        t["f3"].append((n, "end", "fault", m, "heldout", s))
        t["f3"].append((n, "fstat", stat, m, "heldout", s))
    for n, page in (("f3-k4", "0x20006000"), ("f3-k100", "0x10000000")):
        s = "the kernel's TA data of 0x6000 bytes at 384 x 256 (fork 2a650d74, E1048's 24576) [infer]; E509, E869"
        t["f3"].append((n, "end", "fault", "H-PAGE-END", "heldout", s))
        t["f3"].append((n, "fpage", page, "H-PAGE-END", "heldout", s))
    for n, m, end in (("b18-lib", "H-FAULT-ANY", "fault"), ("b18-ramp", "H-FAULT-ANY", "fault"),
                      ("b18-lib", "H-NEEDS-BUF", "fault"), ("b18-ramp", "H-NEEDS-BUF", "ok")):
        t["f4"].append((n, "end", end, m, "heldout", "E065 (bit 18 faulted the library triangle once) [infer]"))
    t["h1"].append(("b24-w32", "end", "hang", "H-B24-HANG", "heldout", "E737 (bit 24 hung over 16 bits, 2 of 2)"))
    t["h1"].append(("b24-w32", "end", "ok", "H-B24-W32", "heldout", "E414 E756"))
    t["h1"].append(("b24-w32", "o0", line_of(gunz(f"{IDX}/ix-c.txt.gz").decode(), "probe p1139-green: o0").split(": o0 ", 1)[1],
                    "H-B24-W32", "heldout", "E756's ix-c (E414's object over 16 bits)"))
    ends = {"M1-SHAPE": ("ok", "ok", "ok", "ok", "hang", "ok", "ok", "hang"),
            "H-ALT": ("ok", "hang", "ok", "hang", "ok", "ok", "hang", "ok"),
            "H-SCALE": ("ok", "ok", "ok", "ok", "ok", "ok", "ok", "ok")}
    names = [r[0] for r in stages()["h2"]]
    for m, e in ends.items():
        for n, v in zip(names, e):
            st = "control" if n == "h2-c-b" else "prime" if n.endswith(("1", "-c-a")) else "heldout"
            t["h2"].append((n, "end", v, m, st, "E700 E1021 E1035 (M1); E413 (H-ALT) [infer]"))
    t["h2"].append(("h2-c-b", "o0", "present", "H-REF", "control", "E700's shape completes at c = 8 under M1"))
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
