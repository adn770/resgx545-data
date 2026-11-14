# SPDX-License-Identifier: MIT
"""fold/records.py: fill the drafts tools/records/new_record.py wrote for E1068 and E1069
(fold/drafts/) with the fold's text and write them into the fold worktree's evidence/zls/. Run once
by the fold (not frozen).

  python3 fold/records.py DRAFTS EVIDENCE_DIR"""
import os
import re
import sys

LAPTOP = ("on the laptop (host cedar, kernel 7.3.0-resgx545, module srcversion "
          "B60AB0B475DD1E8972419B5 (linux fork 2a650d74, installed and loaded alike), stock firmware, "
          "tool ~/sgxfive-test-t10 (t10, sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb, "
          "built from resgx545 a581c06), every job one process of the kit runner (kit/run_stage.sh), a "
          "debugfs reset and the health fill and triangle between jobs, every output and dump kept "
          "gzipped; the rows are tables/STAGE.txt, a row's name prefix naming its record (zo2- E1068, "
          "zb20- E1069), the frozen predictions predictions/STAGE.tsv (gen/z17.py))")
ROUND = ("round 17, decisions R17-1 (a), R17-5 (a) and R17-6 (a): session r17-zls of the round 17 "
         "plan, safe class only")
ATT = "20261114-104614"
START = {"zovp2": "10:46:14", "zovs2": "10:46:58", "zb20": "10:47:33"}

R = {}
R["E1068"] = dict(
    file="E1068-r17-zls-a-load-pass-over-overlapping-tiles-with-edge-tiles-keeps-the-tile-visited-last-and-the-stencil-test-reaches-the-pixels-inside-the-band.md",
    stages=("zovp2", "zovs2"),
    terms='["CR_ISP_ZLSCTL"]',
    claim=("r17-zls rows zo2- (Q299, 8 jobs in stages zovp2 and zovs2, t10): the depth load pass "
           "over overlapping tiles with edge tiles (65 x 33 G 1 and 63 x 31 G 0, E996's plane over a "
           "0.2 load) loads each tile's slot, passes each tile on its own over the whole 32 x 16 tile "
           "and leaves in a shared slot the tile visited last (frozen H-OVL-PASS-EDGE 2 of 2 rows, 3584 "
           "of 3584 and 1536 of 1536 dwords and the drawn counts; the first tile failed 2 of 2, an edge "
           "tile without its load 2 of 2, a load reaching only the pixels inside the extent 2 of 2); the "
           "stencil pass at the same shapes held on 63 x 31 (1536 of 1536 bytes) and failed on 65 x 33 "
           "by 363 bytes beyond the extent, which keep their load past E831's band (x + 0.5 < 1.25 W, "
           "y + 0.5 < 1.25 H) while the frozen model tested them: fitted post hoc, 3584 of 3584 and "
           "1536 of 1536 bytes; all four controls passed"),
    ran=("E1064's load pass with edge tiles: the depth (E996's plane z 0, ZX, 1 at (0,0), (2W,0), "
         "(0,2H) over a buffer filled 0.2f, 0x00175006 at 63 x 31 G 0 and 0x0017500e at 65 x 33 G 1, "
         "depth less, `--depth-pages 20`) and the stencil (E988's st1 form, `bytes` load, 0x00173006 "
         "and 0x0017300e, `--depth-pages 20`) at 65 x 33 G 1 (3 x 3 tiles, slots 2 and 4 shared, the "
         "last tile column and row one pixel wide and high) and 63 x 31 G 0 (2 x 2 tiles, slot 1 "
         "shared by the two edge tiles). The plane of each depth pixel is the kept full-pitch "
         "reference's (E1041's zo-65-f0 and zo-63-f0, H-PASS-TWIN [infer], E1059). Controls: zo2-c-160 "
         "(E1064's zo-p-160 rerun, its kept store byte for byte), zo2-c-65 and zo2-c-63 (the no-load "
         "stores of the two shapes, E996's owner rule on the kept reference; the first also E1041's "
         "zo-65-ov, its first 3584 dwords) and zo2-c-s160 (E1064's zo-s-160 rerun, its kept stencil "
         "store byte for byte). Frozen (gen/z17.py): H-OVL-PASS-EDGE (every tile loads its slot and "
         "passes over its whole tile, the tile visited last owns a shared slot), H-OVL-FIRST, "
         "H-EDGE-SKIP (an edge tile takes no load), H-EDGE-EXT (the load reaches the pixels inside "
         "the extent only) and, on the stencil, H-EDGE-CLIP (the pixels beyond the extent untested). "
         "README deviation 1: 63 x 31 G 0 replaces the plan's 161 x 49 G 2 (no kept plane reference)."),
    results=("Controls: zo2-c-160 3040 drawn and 5632 dwords changed, byte for byte its kept store; "
             "zo2-c-65 3584 of 3584 dwords, 2145 drawn, its first 3584 dwords E1041's zo-65-ov; "
             "zo2-c-63 1536 of 1536, 1953 drawn; zo2-c-s160 3840 drawn, 1408 changed, byte for byte. "
             "zo2-p-65: H-OVL-PASS-EDGE 3584 of 3584 dwords and 845 drawn; H-OVL-FIRST 3363 (221 off "
             "inside the extent), H-EDGE-SKIP 2048 and 929 drawn predicted, H-EDGE-EXT 2113 (1471 off "
             "beyond it). zo2-p-63: 1536 of 1536 and 756 drawn; FIRST 1152, SKIP 512 and 1825 drawn "
             "predicted, EXT 1457. Stencil, zo2-s-63: H-OVL-PASS-EDGE 1536 of 1536 bytes, 1008 drawn. "
             "zo2-s-65: 3221 of 3584 and 1105 drawn (H-EDGE-SKIP 2060 and 1121 drawn predicted, "
             "H-EDGE-EXT 2120, H-EDGE-CLIP 3244): the 363 bytes off the frozen model are all beyond the "
             "extent, in the owner tiles of the last tile row and column (fold/look.out). Post hoc: "
             "the beyond-extent bytes the test could change (a loaded byte with bit 0 clear, even "
             "rows) were tested at x 65 to 80 and y 33 to 40 and not at x 81 to 95 and y 42 to 46, "
             "exactly E831's band (sgx-pipe `zls::in_band`: x + 0.5 < 1.25 W, y + 0.5 < 1.25 H, so x "
             "< 81.25 and y < 41.25), and H-OVL-PASS-EDGE with the pixels beyond the band keeping "
             "their load fits 3584 of 3584 bytes at 65 x 33 and 1536 of 1536 at 63 x 31 (fold/look.py "
             "post). The frozen scorer re-run on the kept files is byte for byte the run's "
             "(fold/reproduce.out). sgx-pipe's `zls::pass_plane` now passes overlapping tiles with "
             "edge tiles and tests/closing_r17_zls.rs replays the four depth rows and both stencil "
             "rows."),
    shows=("The load pass over overlapping tiles keeps its two rules with edge tiles: each tile "
           "reads its slot's loaded dwords over its whole 32 x 16 tile and passes on its own, and the "
           "tile the 3D visits last owns a shared slot (E996, E1041, E1064) [infer: the planes of "
           "the depth rows are the no-load references']. The stencil test over an edge tile reaches "
           "the pixels beyond the extent only as far as the depth pass does, E831's band, as E988 saw "
           "at 40 x 20 (post hoc: the frozen model tested the whole tile)."),
    not_shows=("A store past its buffer (E411's G 5 row in a 16-page buffer: a planned fault, "
               "Q299's remaining clause); the pass at 161 x 49 and over edge tiles in more than one "
               "macrotile column (both shapes here have raster header order); formats 1 and 2 or "
               "bit 19 over overlapping edge tiles; whether the depth pass beyond the band differs "
               "(the plane there is above the 0.2 load at both shapes: the depth rows cannot part it)."),
)
R["E1069"] = dict(
    file="E1069-r17-zls-bit-20-cleared-packs-the-format-6-and-7-records-from-dword-2048-at-96-x-48-and-128-x-64-as-at-64-x-32-3-of-4-and-the-fourth-by-the-twin-s-tenth-slot.md",
    stages=("zb20",),
    terms='["CR_ISP_ZLSCTL"]',
    claim=("r17-zls rows zb20- (Q071, 9 jobs in stage zb20, t10): with bit 20 cleared, formats 6 and 7 "
           "at 96 x 48 G 2 and 128 x 64 G 3 store their per-tile records one after another from dword "
           "2048 whatever the size, as E1063 saw at 64 x 32 G 1 (frozen H-PACK2048 held on 3 of 4 "
           "rows, 108, 704 and 192 dwords of 108, 704 and 192 with the stencil store the twin's and the "
           "drawn count the target's; H-PACK-AFTER (4608, 8192) and H-PACK-SCALE (3072, 4096) failed 4 "
           "of 4); the fourth row (format 6 at 96 x 48) wrote 396 dwords where the frozen rule took "
           "352 of its twin's records: post hoc, its twin (bit 20 set) stored its nine tile records at "
           "slots 0 to 6, 8 and 10 and the frozen rule gathered slots 0 to 8, so H-PACK2048 holds there "
           "too on every dword of the twin in address order (396 of 396); the control passed"),
    ran=("E1031's zf-flat-f6 and zf-7k-3f rows (`--tri-full`, `--depth-fill 0xdeadbeef`, the "
         "`index` and 0x3f3f3f3f stencil loads, format 6 0x06173016 at G 2 and 0x0617301e at "
         "G 3, format 7 0x07173016 and 0x0717301e) at 96 x 48 G 2 and 128 x 64 G 3 (G = tiles across - 1, no "
         "overlap, `--depth-pages 32`), each bit-20-cleared row (zb20-b-F-S) right after its "
         "bit-20-set twin (zb20-t-F-S, the records of the row's expected content). Control: zb20-c-f6 "
         "(E1063's zb4-c-f6, E1031's zf-flat-f6 rerun, its kept depth dump and stencil store byte for "
         "byte, 176 dwords changed). Frozen (gen/z17.py): H-PACK2048 (the twin's tile records, each "
         "slot's dwords other than the fill, in slot order from dword 2048), H-PACK-AFTER (from 512 x "
         "rows x (G + 1): 4608 and 8192) and H-PACK-SCALE (from 1024 x (G + 1): 3072 and 4096); the "
         "three agree at E1063's 64 x 32 G 1. The 128 x 64 pair ran last, a size and a 32-page "
         "buffer never run."),
    results=("Control: zb20-c-f6 176 dwords changed, depth dump and stencil store byte for byte the "
             "kept zf-flat-f6. Twins (bit 20 set): format 6 at 128 x 64 a 44-dword record at every one "
             "of the 16 slot starts; format 6 at 96 x 48 44 dwords at slots 0 to 6, 8 and 10 (none "
             "at slot 7); format 7 (two runs of 12 dwords, at +0 and +256) 24-dword "
             "records in slots 0 to 2 and 12-dword ones in slots 3 to 5 at 96 x 48 and 24-dword records "
             "in slots 0 to 7 at 128 x 64, none after. "
             "Rows: zb20-b-6-128 wrote "
             "dwords 2048 to 2751 (704, contiguous), zb20-b-7-128 2048 to 2239 (192), zb20-b-7-96 2048 to "
             "2155 (108), zb20-b-6-96 2048 to 2443 (396): each the twin's non-fill dwords in address "
             "order, and every other dword of the depth dump the fill; the stencil stores the twins' "
             "and 4608 or 8192 pixels drawn. Frozen H-PACK2048 matched 704 of 704, 192 of 192 and 108 "
             "of 108 and 352 of 352 with 44 other at zb20-b-6-96 (the frozen rule took slots 0 to 8 "
             "of the twin: its slot 10 held the ninth record); H-PACK-AFTER and H-PACK-SCALE matched 0 "
             "everywhere. The frozen scorer re-run on the kept files is byte for byte the run's "
             "(fold/reproduce.out)."),
    shows=("Bit 20 cleared packs the format 6 and 7 per-tile records from dword 2048, one after "
           "another in the twin's address order, at three sizes (64 x 32, 96 x 48, 128 x 64) and "
           "two pitches: not from the end of the last slot and not at an offset scaling with the "
           "pitch [post hoc at 64 x 32, held out at the other two, the fourth row by a record "
           "gathering the frozen rule got wrong]. With bit 20 set the records sit at the slots' "
           "starts, except at 96 x 48 G 2 where the last two tiles' records are at slots 8 and 10 "
           "[post hoc]."),
    not_shows=("Why the last two tiles of 96 x 48 store at slots 8 and 10; bit 20 cleared in formats "
               "3 to 5, with other stencil loads or an overlapping pitch; where bit 23's bytes come "
               "from and the ISP's use of the control (Q071's remaining clauses)."),
)


def fill(name, d, drafts, out):
    s = open(os.path.join(drafts, name + ".md")).read()
    att = f"{ATT}"
    st = d["stages"]
    t = "attempt out/%s" % att
    stamps = ", ".join(f"{s_} {START[s_]}" for s_ in st)
    s = s.replace("(TODO-FILL: round, decisions, plan)", f"({ROUND})")
    s = s.replace("(TODO-FILL: host, kernel, module srcversion, firmware, tool, the job commands and rows)", LAPTOP)
    s = s.replace(f"attempt out/{att} (scores", f"attempt out/{att} ({stamps} Mac time; driver log run.log; its freeze FROZEN.sha256 3cecf5e25b1cfa6cdf7e174884e45f1c43958ca788c082a9ddb87a400a3d78ea; scores")
    s = s.replace('claim = "TODO-FILL: the claim, with the frozen verdict quoted"', 'claim = "%s"' % d["claim"])
    s = s.replace("terms = []", "terms = %s" % d["terms"])
    sums = []
    for stg in st:
        for ln in open(os.path.join(os.path.dirname(drafts), "..", "out", att, f"score-{stg}.txt")):
            if ln.startswith("SUMMARY:"):
                sums.append(f"attempt {att}, stage {stg} (run.log): `{ln.strip()}`")
    verdict = "; ".join(sums) + "."
    parts = {"What ran": d["ran"], "Frozen verdict (as printed)": verdict, "Results [HW]": d["results"],
             "What it shows": d["shows"], "What it does not show": d["not_shows"]}
    body = s.split("+++\n", 2)
    head = body[0] + "+++\n" + body[1] + "+++\n"
    text = "\n\n".join(f"**{k}.** {v}" for k, v in parts.items()) + "\n"
    open(os.path.join(out, d["file"]), "w").write(head + text)


if __name__ == "__main__":
    drafts, out = sys.argv[1], sys.argv[2]
    for name, d in R.items():
        fill(name, d, drafts, out)
