#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r20-own's tables (tables/ow.txt, owt.txt, owp.txt) and frozen predictions
(predictions/STAGE.tsv): closing20/plan/rank-round20.md section 4 (S2), stages ow and owt (Q191,
E1091) and owp (Q192, E1092).

  make.py [--check]   write them (or exit 1 when the files differ from what it would write)

Every row is E1087's form on t18b (`tri --ctx2 --close-first-early --kept-copy --words
--kpoke-render 1:ta:7^=0xc`, render_keep armed, 1024x768, P by render_pb_pages for both contexts)
under regtimeline (rt, read only). `--move 1:DX,DY` moves only the owner's triangle (t18b at ec50498
moves render i of the first context; tri2_submit draws the library default). The moves are
gen/cover.py's: -112,-80 (the plan's -128,-96 puts vertices on macrotile edges, where the pixel and
the conservative covers differ: a deviation) and 64,64 (the plan's).

The reference pages are read from the data repository at DATA_COMMIT (pinned in the freeze):
E1087's o1-big-a after copy (pages 4 to 6) and E1084's o2-p30 after copy (page 6)."""
import gzip
import os
import struct
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import cover as C  # noqa: E402

DATA = os.environ.get("RESGX545_DATA_REPO", "/Users/jtorra/src/resgx545-data")
DATA_COMMIT = "ba3990f01eb2b2a29fce03c9f48dd071d89b34e6"
E1087 = "render/closing-r19-own1b/out/20261114-230658/own1/o1-big-a.kept.1.bin.gz"
E1084 = "render/closing-r19-own/out/20261114-223625/own2/o2-p30.kept.1.bin.gz"
PAGE = 4096

T18B = '"$HOME/sgxfive-test-t18b"'
RT_LONG = "0x0620-0x0634,0x0658,0x065c,0x0674,0x0694,0x0698,0x0700-0x0728"
RT_SHORT = "0x062c,0x0634,0x0694,0x0698"
FORM = ("tri --width 1024 --height 768 -n 1 --keep-overflow --wait-ms 20000 --ctx2 "
        "--close-first-early --kept-copy \"$W\" --words \"$W\" --kpoke-render 1:ta:7^=0xc")
M1, M2 = (-112, -80), (64, 64)

# name, set, P, move, rt registers
OW = [("ow-c", "control", "0x422", None, RT_LONG),
      ("ow-m1-a", "fit", "0x422", M1, RT_LONG),
      ("ow-m1-b", "fit", "0x422", M1, RT_LONG),
      ("ow-m2", "heldout", "0x422", M2, RT_LONG)]
OWT = [("owt-a", "control", "0x422", None, RT_SHORT),
       ("owt-b", "heldout", "0x422", None, RT_SHORT)]
OWP = [("owp-30-a", "control", "0x30", None, RT_LONG),
       ("owp-30-b", "fit", "0x30", None, RT_LONG),
       ("owp-30m", "heldout", "0x30", M1, RT_LONG),
       ("owp-2c", "heldout", "0x2c", None, RT_LONG),
       ("owp-34", "heldout", "0x34", None, RT_LONG)]
STAGES = {"ow": OW, "owt": OWT, "owp": OWP}

HEAD = {
    "ow": [
        "# r20-own ow (E1091, Q191 whose scene): a kept 1024x768 owner at P 0x422 (no partial "
        "render), the second context drawing the default scene; are the lists of the owner's state "
        "page after the second render the second context's scene or the owner's?",
        "# Frozen: H-SECOND (pages 4 to 6 of kept.1.bin equal E1087's o1-big-a dword for dword "
        "whatever the owner's move) against H-OWNER (the non-zero lists 0 to 15 of page 6 are "
        "the moved owner's cover, gen/cover.py: -112,-80 {0,1,2,3,4,5,6,8,9,12}; 64,64 "
        "{0,1,4,5,6,7,9,10,11,13,14}).",
        "# Control ow-c (unmoved; reads ovf,kept,size): no overflow (0), 2 copies, 69632 bytes, "
        "and its pages 4 to 6 E1087's exactly (the scorer). An empty copy right after the close "
        "makes its row cannot tell; hook_check stops the stage after two in a row (24).",
    ],
    "owt": [
        "# r20-own owt (E1091, Q191 which kick, a reading [infer]): regtimeline on 0x062c, 0x0634, "
        "0x0694, 0x0698 only. H-TA: 0x062c takes the owner's state base (words.101 rtds:11) with a "
        "task write (0x0694 or 0x0698 changing) after the second context's first other state base "
        "and before its last task write; H-END: after its last task write; none seen: cannot tell.",
        "# Control owt-a (also a fit row; reads ovf,kept,size): 0, 2, 69632, pages 4 to 6 E1087's.",
    ],
    "owp": [
        "# r20-own owp (E1092, Q192): the owner's state page after the second render by the "
        "owner's regime (raised iff ta3d.101.bin dword 38 is non-zero, E625, read per row).",
        "# Frozen H-REGIME: zero when raised; not raised, non-zero lists in E627's format, and at "
        "P 0x30 unmoved E1084's o2-p30 10 dwords exactly (a repeat). owp-30m (owner moved "
        "-112,-80): H-SECOND (o2-p30's dwords) against H-OWNER (other lists, within the moved "
        "cover).",
        "# Control owp-30-a (also a fit row; reads ovf,kept,size): 1, 2, 69632 and its page 6 "
        "E1084's o2-p30 exactly.",
    ],
}


def row(stage, name, sset, p, move, regs):
    knobs = f"dbg:render_keep=1 dbg:render_pb_pages={p}"
    if sset == "control":
        knobs += " reads:ovf,kept,size"
    args = FORM + (f" --move 1:{move[0]},{move[1]}" if move else "")
    return f"{name}|{sset}|safe|{knobs}|rt|0 0.3 {regs} -- {T18B} {args}"


def tables():
    out = {}
    for stage, rows in STAGES.items():
        lines = [f"#stage {stage}", "#limit 0"] + HEAD[stage]
        lines += [row(stage, *r) for r in rows]
        out[f"tables/{stage}.txt"] = "\n".join(lines) + "\n"
    return out


def _data(path):
    b = subprocess.run(["git", "-C", DATA, "show", f"{DATA_COMMIT}:{path}"], check=True,
                       capture_output=True).stdout
    return gzip.decompress(b)


def pages(b, which):
    """'pN:i=0x...,i=0x...;pM:...': the non-zero dwords of the pages, dword for dword (a page
    without one is 'pN:')"""
    out = []
    for p in which:
        ws = struct.unpack_from("<1024I", b, p * PAGE)
        out.append(f"p{p}:" + ",".join(f"{i}=0x{x:08x}" for i, x in enumerate(ws) if x))
    return ";".join(out)


def cov(move):
    return ",".join(str(m) for m in C.cover(*move))


def ctl(name, ovf, after, closed, src):
    """a control's frozen readings: the premise words, then its pages (after; closed if given)"""
    out = [f"{name}\tovf\t{ovf}\tCTL\tcontrol\tE1087, E1084 (the owner's overflow at its P)",
           f"{name}\tkept\t2\tCTL\tcontrol\tt18b --kept-copy with --close-first-early",
           f"{name}\tsize\t69632\tCTL\tcontrol\tE1087, E1084 (the 1024x768 TA data, 0x11000)"]
    if closed is not None:
        out.append(f"{name}\tclosed_pages\t{closed}\tCTL\tcontrol\tE1087 (zero after the close)")
    out.append(f"{name}\tafter_{'pages' if closed is not None else 'state'}\t{after}\tCTL\t"
               f"control\t{src}")
    return out


def predictions():
    hdr = "case\tquantity\tvalue\tmodel\tset\tsource"
    ref87 = pages(_data(E1087), (4, 5, 6))
    ref84 = pages(_data(E1084), (6,))
    out = {}
    p = [hdr]
    for name, sset, P, move, _ in OW:
        if sset == "control":
            p += ctl(name, "0", ref87, "p4:;p5:;p6:", "E1087 o1-big-a kept.1.bin")
            continue
        p += [f"{name}\tafter_pages\t{ref87}\tH-SECOND\t{sset}\tE1087 o1-big-a (both draw the "
              "second context's scene) [infer]",
              f"{name}\tlists\t{cov(move)}\tH-OWNER\t{sset}\tgen/cover.py (the owner's moved "
              "cover; the owner's DPM state stored at the slot change) [infer]"]
    out["predictions/ow.tsv"] = "\n".join(p) + "\n"
    p = [hdr]
    for name, sset, *_ in OWT:
        if sset == "control":
            p += ctl(name, "0", ref87, "p4:;p5:;p6:", "E1087 o1-big-a kept.1.bin")
        p += [f"{name}\tkick\tta\tH-TA\t{sset}\tplan S2 owt [infer]",
              f"{name}\tkick\tend\tH-END\t{sset}\tplan S2 owt [infer]"]
    out["predictions/owt.tsv"] = "\n".join(p) + "\n"
    p = [hdr]
    for name, sset, P, move, _ in OWP:
        if sset == "control":
            p += ctl(name, "1", ref84, None, "E1084 o2-p30 kept.1.bin (a repeat)")
        p += [f"{name}\traised_state\tp6:\tH-REGIME\t{sset}\tE1084 (0x28, 0x24 raised: zero)"]
        if move is None and P == "0x30":
            p.append(f"{name}\tplain_state\t{ref84}\tH-REGIME\t{sset}\tE1084 o2-p30 (a repeat)")
        else:
            p.append(f"{name}\tplain_state\tlists\tH-REGIME\t{sset}\tE627's format, non-zero")
        if move is not None:
            p += [f"{name}\twhose\t{ref84}\tH-SECOND\t{sset}\tE1084 o2-p30 (the second context's "
                  "lists) [infer]",
                  f"{name}\twhose\tother-within:{cov(move)}\tH-OWNER\t{sset}\tgen/cover.py "
                  "(the moved owner's lists) [infer]"]
    out["predictions/owp.tsv"] = "\n".join(p) + "\n"
    return out


def main(argv):
    files = {**tables(), **predictions()}
    bad = []
    for rel, body in files.items():
        path = os.path.join(KP, rel)
        cur = open(path).read() if os.path.exists(path) else None
        if "--check" in argv:
            if cur != body:
                bad.append(rel)
        elif cur != body:
            with open(path, "w") as f:
                f.write(body)
    for b in bad:
        print(f"{b}: not what gen/make.py writes")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
