#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r19-own's tables (tables/own2.txt, own1.txt) and frozen predictions
(predictions/own2.tsv, own1.tsv) from closing19/plan/rank-round19.md section 4 (S3).

  make.py [--check]   write them (or exit 1 when the files differ from what it would write)

Every row is E631's form on t18b: `tri --ctx2 --close-first-early` with debugfs render_keep armed
(dbg:render_keep=1, so the first context's early close keeps its TA data) and the first render's
flag poked (`--kpoke-render 1:ta:7^=0xc`, or 0x4), the kept TA data copied by the tool right after
the close and before the second context's render (`kept.closed.1.bin`) and after that render,
before any other close (`kept.1.bin`), `--words` snapshots before (101) and after (201) the close.
P is debugfs render_pb_pages (both contexts). No row writes render_final_pb_pages (declared at 0).
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FORM = ('tri --width {w} --height {h} -n 1 --keep-overflow --wait-ms 20000 --ctx2 '
        '--close-first-early --kept-copy "$W" --words "$W" --kpoke-render 1:ta:7^={flag}')

# name, set, w, h, P, flag
OWN2 = [
    ("o2-c-a", "control", 1024, 768, "0x28", "0xc"),
    ("o2-c-b", "fit", 1024, 768, "0x28", "0xc"),
    ("o2-4", "fit", 1024, 768, "0x28", "0x4"),
    ("o2-p30", "heldout", 1024, 768, "0x30", "0xc"),
    ("o2-p24", "heldout", 1024, 768, "0x24", "0xc"),
    ("o2-2k", "heldout", 2048, 1536, "0x28", "0xc"),
]
OWN1 = [
    ("o1-4", "control", 64, 64, "0x422", "0x4"),
    ("o1-c-a", "fit", 64, 64, "0x422", "0xc"),
    ("o1-c-b", "fit", 64, 64, "0x422", "0xc"),
    ("o1-big-a", "heldout", 1024, 768, "0x422", "0xc"),
    ("o1-big-b", "heldout", 1024, 768, "0x422", "0xc"),
    ("o1-p200", "heldout", 64, 64, "0x200", "0xc"),
]

HEAD = {
    "own2": [
        "#stage own2",
        "#limit 0",
        "# r19-own own2, Q192 (E1084): does the store that follows the second context's render "
        "replace the state page a partial-render owner left, and what does it write? A 1024x768 "
        "owner on P pages (partial renders), kept, closed early; the TA data copied after the close "
        "(kept.closed.1.bin) and after the second context's render (kept.1.bin).",
        "# Frozen: H-RSTORE (closed copy: the owner's lists, 18 non-zero dwords at 0x28 (E464, E631's "
        "solo); after copy: 0) against H-EARLY (the closed copy already 0: the close or the second "
        "context's creation) and H-LATE (both copies hold the lists: the zero of E631 comes after "
        "the second render, at its close). Held out: P 0x30, 0x24, 2048x1536 (state page 0x12000).",
        "# Control o2-c-a (reads ovf,kept,size): the first render overflowed (1), both copies made "
        "(2), 69632 bytes each (the 1024x768 TA data); hook_check stops the stage (24) on any row "
        "whose copies were not both made. Safe: render_keep reads back Y before each row (rc 19).",
    ],
    "own1": [
        "#stage own1",
        "#limit 0",
        "# r19-own own1, Q191 (E1085): are the kept owner words (control 0x00200047, OTPM "
        "0x04000417, state 0x00020001 and 2) stored by the second context's render or at the "
        "first context's close, and do the state words count the owner's pages?",
        "# Frozen: (a) H-RENDER (64x64, 0xc: none in kept.closed.1.bin, all four in kept.1.bin) "
        "against H-CLOSE (all four already in the closed copy); (b) 1024x768 at P 0x422 (no "
        "partial render): H-COUNT (state words (U << 16 | head), tail with U the owner's pages, "
        "0x11 to 0x15) against H-CONST (0x00020001, 2) and H-NONE (0, 0); (c) P 0x200 held out.",
        "# Control o1-4 (reads ovf,kept,size; flag 0x4: E631's no-word case): no overflow (0), both "
        "copies (2), 24576 bytes; the scorer fails it if any owner word shows in either copy.",
    ],
}


def row(name, sset, w, h, p, flag, control):
    knobs = f"dbg:render_keep=1 dbg:render_pb_pages={p}"
    if control:
        knobs += " reads:ovf,kept,size"
    return f"{name}|{sset}|safe|{knobs}|t18b|" + FORM.format(w=w, h=h, flag=flag)


def tables():
    out = {}
    for stage, rows in (("own2", OWN2), ("own1", OWN1)):
        lines = list(HEAD[stage])
        for name, sset, w, h, p, flag in rows:
            lines.append(row(name, sset, w, h, p, flag, sset == "control"))
        out[f"tables/{stage}.txt"] = "\n".join(lines) + "\n"
    return out


W4 = "0x00200047,0x04000417,0x00020001,0x00000002"   # E591, E631: the 64x64 owner's words


def predictions():
    hdr = "case\tquantity\tvalue\tmodel\tset\tsource"
    p2 = [hdr]
    for name, sset, w, h, p, flag in OWN2:
        if sset == "control":
            for q, v, s in (("ovf", "1", "E631 ow-part-c-k (the first render overflowed)"),
                            ("kept", "2", "t18b --kept-copy with --close-first-early"),
                            ("size", "69632", "E631 (the 1024x768 TA data, 0x11000)")):
                p2.append(f"{name}\t{q}\t{v}\tCTL\t{sset}\t{s}")
        lists = "18" if p == "0x28" and w == 1024 else ">0"
        src = "E464, E591, E631 solo (18 at 0x28)" if lists == "18" else \
            "E627 (lists at any P of a partial render) [infer]"
        sset2 = "fit" if sset == "control" else sset
        p2 += [f"{name}\tclosed_state_nz\t{lists}\tH-RSTORE\t{sset2}\t{src}",
               f"{name}\tafter_state_nz\t0\tH-RSTORE\t{sset2}\tE631 (0 after the run, 4 of 4)",
               f"{name}\tclosed_state_nz\t0\tH-EARLY\t{sset2}\tplan S3 H-CLOSE/H-CREATE",
               f"{name}\tafter_state_nz\t0\tH-EARLY\t{sset2}\tE631",
               f"{name}\tclosed_state_nz\t{lists}\tH-LATE\t{sset2}\t{src}",
               f"{name}\tafter_state_nz\t{lists}\tH-LATE\t{sset2}\tthe zero after kept.1"]
    p1 = [hdr]
    for name, sset, w, h, p, flag in OWN1:
        if sset == "control":
            for q, v, s in (("ovf", "0", "E631 (64x64 never overflows at 0x422)"),
                            ("kept", "2", "t18b --kept-copy with --close-first-early"),
                            ("size", "24576", "E631 ow-kcopy (the 64x64 TA data, 0x6000)"),
                            ("closed_words", "none", "E631 ow-kcopy-4 (flag 0x4: no word)"),
                            ("after_words", "none", "E631 ow-kcopy-4")):
                p1.append(f"{name}\t{q}\t{v}\tCTL\t{sset}\t{s}")
            continue
        if w == 64:
            p1 += [f"{name}\tclosed_words\tnone\tH-RENDER\t{sset}\tE631 (by the render's end)",
                   f"{name}\tafter_words\t{W4}\tH-RENDER\t{sset}\tE591, E631 (8 of 8)",
                   f"{name}\tclosed_words\t{W4}\tH-CLOSE\t{sset}\tplan S3 H-CLOSE",
                   f"{name}\tafter_words\t{W4}\tH-CLOSE\t{sset}\tE631"]
        else:
            p1 += [f"{name}\tafter_state01\tcount:0x11-0x15\tH-COUNT\t{sset}\t"
                   "E631 H191-L; plan S3 (19 pages at P 0x422) [infer]",
                   f"{name}\tafter_state01\t0x00020001,0x00000002\tH-CONST\t{sset}\tE631 (U = 2 in 8 of 8)",
                   f"{name}\tafter_state01\t0x00000000,0x00000000\tH-NONE\t{sset}\tE631's partial owner"]
    return {"predictions/own2.tsv": "\n".join(p2) + "\n",
            "predictions/own1.tsv": "\n".join(p1) + "\n"}


def main(argv):
    files = {**tables(), **predictions()}
    bad = []
    for rel, body in files.items():
        p = os.path.join(KP, rel)
        cur = open(p).read() if os.path.exists(p) else None
        if "--check" in argv:
            if cur != body:
                bad.append(rel)
        elif cur != body:
            with open(p, "w") as f:
                f.write(body)
    for b in bad:
        print(f"{b}: not what gen/make.py writes")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
