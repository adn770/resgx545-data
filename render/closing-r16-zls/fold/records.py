# SPDX-License-Identifier: MIT
"""fold/records.py: fill the drafts tools/records/new_record.py wrote for E1059, E1063, E1064 and
E1066 (debug/drafts/) with the fold's text, keep each record's own models in its frozen verdict,
and write them into the fold worktree's evidence/. Run once by the fold (not frozen).

  python3 fold/records.py DRAFTS EVIDENCE_DIR"""
import os
import re
import sys

LAPTOP = ("on the laptop (host cedar, kernel 7.3.0-resgx545, module srcversion "
          "B60AB0B475DD1E8972419B5 (linux fork 2a650d74, installed and loaded alike), stock firmware, "
          "tool ~/sgxfive-test-t10 (t10, sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb, "
          "built from resgx545 a581c06), every job one process of the kit runner (kit/run_stage.sh), a "
          "debugfs reset and the health fill and triangle between jobs, every output and dump kept "
          "gzipped; the rows are tables/STAGE.txt, grouped by the dump their scorer reads, a row's name "
          "prefix naming its record (zp2- E1059, zb4- E1063, zo- E1064, zw2- E1066), the frozen "
          "predictions predictions/STAGE.tsv (gen/z16.py))")
ROUND = ("round 16, decisions R16-1 (a), R16-3 (a), R16-6 (a) and R16-8 (a): session r16-zls of the "
         "round 16 plan, safe class only")

R = {}
R["E1059"] = dict(
    file="zls/E1059-r16-zls-the-zls-load-pass-stores-the-plane-its-no-load-twin-stores-where-it-is-below-the-load-7-of-7-and-the-depth-s-own-float-at-the-one-float-depths-3-of-3.md",
    models=("H-PASS-TWIN", "H-PASS-OWN", "H-PASS-EXACT"),
    terms='["CR_ISP_ZLSCTL", "CR_ISP_ZLOAD_BASE"]',
    claim=("r16-zls rows zp2- (Q297, 15 jobs in stage zpass2, t10): E1050's load pass (64 x 32, the "
           "bit:9 load of 0.25 and 0.75, depth less) at the flat depths 0.125, 0.0625, 0.1, 0.3, 0.375, "
           "0.625 and 0.5 + 2^-20 stores at every dword the float its no-load twin (the same triangle "
           "from the clear 1.0) stores where that float is below the load, else the load (frozen "
           "H-PASS-TWIN 7 of 7, 2048 of 2048 dwords and the drawn count on each); at the one-float depths "
           "0.375, 0.625 and 0.5 + 2^-20 that is the depth's own float (H-PASS-EXACT 3 of 3), while the "
           "twins at 0.125, 0.0625, 0.1 and 0.3 hold 3 to 10 floats up to 9 ulps below the depth, so the "
           "depth's own float failed there (H-PASS-OWN 3 held, 4 FAILED); both controls passed"),
    ran=("E1050's zpass form (`--tri-full` at 64 x 32, `--depth --depth-store`, `--depth-pages 20`, "
         "the depth buffer filled `bit:9`: 0.25f in tile column 0 and 0.75f in column 1 at G 1, the "
         "load and store enables 0x0017500e, the depth test less) at the flat depths 0.125, 0.0625, "
         "0.1, 0.3, 0.375, 0.625 and 0.5 + 2^-20, each pass row followed by its no-load twin "
         "(0x0017100c, the store from the clear 1.0). Controls: zp2-c-z125 (E1050's zp-z125, the 0.125 "
         "pass, its kept store byte for byte; the pair's verdict is printed on its twin zp2-t-z125, held "
         "out) and zp2-c-467 (E1050's zp-c-467: 256 x 128 G 7). Frozen (gen/z16.py): H-PASS-TWIN, "
         "H-PASS-OWN, and H-PASS-EXACT at the three one-float depths of E1054. E1050's H-PASS-LE was "
         "not scored: no depth equals a loaded one (README deviation 5)."),
    results=("Controls: zp2-c-467 16384 drawn and zp2-c-z125 2048 drawn, each store byte for byte its "
             "kept E1050 record. The twins (READING lines): 0.125 nine floats 0x3dfffff7 to 0x3dffffff "
             "(as E1050's zp-z125 stored), 0.0625 ten floats 0x3d7ffff7 to 0x3d800000, 0.1 six floats "
             "0x3dccccc6 to 0x3dcccccb (0.1f is 0x3dcccccd), 0.3 three floats 0x3e999997 to 0x3e999999 "
             "(0.3f is 0x3e99999a), and 0.375, 0.625 and 0.5 + 2^-20 one float each, the depth's "
             "(0x3ec00000, 0x3f200000, 0x3f000010). Every pass row held H-PASS-TWIN at 2048 of 2048 "
             "dwords with 2048 drawn below 0.25 and 1024 from 0.3 up; H-PASS-OWN matched 0, 4, 0 and 1024 "
             "of 2048 dwords at 0.125, 0.0625, 0.1 and 0.3. The frozen scorer re-run on the kept files is "
             "byte for byte the run's (fold/reproduce.out). sgx-pipe's `zls::pass_plane` fed each twin's "
             "floats reproduces every pass store and drawn count (tests/closing_r16_zls.rs)."),
    shows=("What a load pass stores at a flat depth is the plane the same triangle stores without a "
           "load, tested strictly against the loaded float (E995) and kept where it fails: the pass "
           "adds nothing to the plane's own error, which is Q200's (a flat plane stores up to 9 ulps "
           "below a depth whose plane is not one float) [infer: the twin's plane is the pass's]. With "
           "E1050's edge-tile, bit-19 and integer clauses, every clause of Q297's line is decided by "
           "held-out rows with passing controls."),
    not_shows=("Why the planes at 0.125, 0.0625, 0.1 and 0.3 are not one float (Q200); a pass at a "
               "depth equal to the load away from 0.75 (E1050); a sloped plane in a pass beyond "
               "E996's (E1064); the stencil test of a pass other than E988's EQUAL row."),
)
R["E1063"] = dict(
    file="zls/E1063-r16-zls-bit-0-stores-as-without-it-with-a-loaded-stencil-4-of-4-bit-23-s-bytes-follow-no-test-value-3-of-3-and-bit-20-cleared-moves-the-format-6-and-7-records.md",
    models=("H-B0", "H-B0-NOSTORE", "H-INERT20", "H23-FIXED", "H23-REF", "H23-MASK", "H23-BG"),
    terms='["CR_ISP_ZLSCTL", "CR_ISP_BGOBJVALS.STENCIL", "ISP2"]',
    claim=("r16-zls rows zb4- (Q071, 14 jobs in stages zbits4, zovp and zoff, t10): bit 0 under E988's "
           "stencil row, E1030's bit 16 cleared and E1031's flat format-6 and F7K rows writes no colour "
           "pixel and leaves the depth dump and the stencil store byte for byte the kept twin's (frozen "
           "H-B0 4 of 4; nothing stored, H-B0-NOSTORE, failed 4 of 4); bit 23's bytes 0x3f, 0x80 and 0 "
           "by x mod 16 stay with the reference at 0x80, the compare mask at 0xff and the background "
           "stencil (CR_ISP_BGOBJVALS, render details dword 17) at 0x5a (H23-FIXED 3 of 3, each named "
           "source refuted on its own row); bit 20 cleared changed nothing at 640 x 480 in format 0 nor "
           "with bit 12 cleared and a depth load (H-INERT20 2 of 2 there), but in formats 6 and 7 it "
           "moved the stored records (H-INERT20 failed 2 of 2: post hoc, the twin's per-tile records "
           "packed one after another from dword 2048); all controls passed"),
    ran=("E988's st1-b0 form (64 x 32, the stencil loaded from the `bytes` fill and stored, ISP word 2 "
         "0x040501ff) and E1031's zfmt form (the `index` stencil, depth less) with bit 0 set on "
         "st1-b0 (0x0017300f), E1030's zbs-c16 (0x0016300f), zf-flat-f6 (0x0617300f) and zf-7k-3f "
         "(0x0717300f); bit 20 cleared on zf-flat-f6 (0x0607300e), zf-7k-3f (0x0707300e), E1042's zb2-d12 "
         "(0x0007400e, in stage zovp) and E1041's zo-640-f0 (0x0007109c, 640 x 480, in stage zoff); "
         "E1042's zb2-b23 (0x0097300e) with `--poke blk:1^=0x80` (the reference, ISP word 0 bits 7:0), "
         "`--isp2 0x0405ffff` (the compare mask 0xff) and `--kpoke-render 1:rd:17=0x35a` (t10's "
         "background word 0x300 with STENCIL 0x5a, 3d.md 11.3). Each changed row is its kept twin's "
         "argv with one word moved (tests/test_gen.py). Controls: zb4-c-base (st1-b0), zb4-c-b23 "
         "(zb2-b23) and zb4-c-f6 (zf-flat-f6), their kept dumps byte for byte."),
    results=("Controls: 1024 and 1536 drawn and 176 depth dwords changed, each dump byte for byte the "
             "kept twin's. The four bit-0 rows drew 0 and stored the twin's depth dump and stencil store "
             "byte for byte (the format 6 and 7 rows store no stencil: E1031). zb4-23-ref drew 1536 and "
             "zb4-23-bg 1536, zb4-23-msk 1024 (the zero bytes only under the full mask), and on all three "
             "the byte the test read (the stored byte, XOR 0xff where drawn) was 0x3f, 0x80 or 0 by x mod "
             "16 exactly as E1053's, 2048 of 2048; the rd:17 poke line was printed. zb4-20-d12 stored "
             "zb2-d12's store byte for byte (0 drawn), zb4-20-640 zo-640-f0's 307200 dwords. zb4-20-f6 and "
             "zb4-20-f7 drew 2048 and left the stencil store as the twin's, but their depth dumps differ: "
             "the twin's 176 and 48 dwords (44 and 24 a tile record, at each slot's start) are not at the "
             "slots, and the same dwords lie packed in tile order at dwords 2048 to 2223 and 2048 to 2095 "
             "(fold/look.py, fold/look.out, post hoc). The frozen scorer re-run on the kept files is byte "
             "for byte the run's (fold/reproduce.out). sgx-pipe's `zls::Ctl::decode` takes bit 0 with a "
             "loaded stencil and refuses bit 20 cleared with formats 5 to 7 (tests/closing_r16_zls.rs)."),
    shows=("Bit 0 suppresses the colour write and nothing of the depth or stencil path under every "
           "control it ran with (E997's four, these four) [infer: every route]. Bit 23's bytes come "
           "from neither the reference, the compare mask nor the background stencil. Bit 20 is not "
           "inert: in formats 6 and 7 it chooses where the per-tile records go, at their slots (set, as "
           "the closed driver's values) or packed after the four slots (cleared) [post hoc, one size], "
           "and it changed nothing seen in formats 0 and with a linear depth load."),
    not_shows=("Bit 20 cleared at another size or pitch, in formats 3 to 5 or with a stencil but no "
               "format-6/7 depth (the packed records' start: after the slots or at a fixed offset); "
               "where bit 23's bytes come from; bits 27 to 31 on routes other than E1042's; the ISP's "
               "use of the control beyond these."),
)
R["E1064"] = dict(
    file="zls/E1064-r16-zls-a-load-pass-over-overlapping-tiles-keeps-the-tile-visited-last-4-of-4-and-a-kept-nan-stores-the-top-of-the-integer-range-5-of-5.md",
    models=("H-OVL-PASS", "H-OVL-FIRST", "H-OVL-SKIP", "H-NAN-SAT", "H-NAN-ZERO", "H-NAN-LOW"),
    terms='["CR_ISP_ZLSCTL"]',
    claim=("r16-zls rows zo- (Q299, 11 jobs in stages zovp and zbits4, t10): a load pass over "
           "overlapping tiles (64 x 32 G 0 and 160 x 48 G 2) loads each tile's slot by E465, passes "
           "each tile on its own and leaves in a shared slot the tile visited last in region header "
           "order, for the depth load over E996's plane and the stencil load under E988's test (frozen "
           "H-OVL-PASS 4 of 4; the first tile failed 2 of 2, shared slots without a load 4 of 4); a "
           "NaN load (0x7fc00000, 0xffc00000, 0x7f800001) kept under never stores 0x00ffffff in format "
           "1 and 0xffffffff in format 2 (H-NAN-SAT 5 of 5; 0 and the word's low bits failed 5 of 5); "
           "both controls passed"),
    ran=("E996's plane (z 0, ZX, 1 at (0,0), (2W,0), (0,2H)) at 64 x 32 G 0 (0x00175006) and 160 x 48 G "
         "2 (0x00175016), the depth loaded from a buffer filled 0.2f (0x3e4ccccd) and stored, depth "
         "less; E988's st1 row at the same pitches (0x00173006, 0x00173016, the `bytes` stencil, in "
         "stage zbits4); E1050's zpass form under never (blk:1 0x00000200) in formats 1 (0x0117500e) "
         "and 2 (0x0217500e) with the load buffer filled 0x7fc00000, 0xffc00000 (format 1) and "
         "0x7f800001. Controls: zo-c-64 (the 64 x 32 pass row without the load, 0x00171004: E996's "
         "owner rule from the kept full-pitch reference, held on E996's kept zov-64x32-g0 dword for "
         "dword offline) and zo-c-f1 (E1050's zp-f1, its kept store byte for byte). The plane of "
         "each pixel was named by E996's kept zov-64x32-ctl and zov-160x48-ctl (H-PASS-TWIN, E1059)."),
    results=("Controls: zo-c-64 1536 of 1536 dwords and 2048 drawn, zo-c-f1 byte for byte and 1024 "
             "drawn. zo-p-64 1536 of 1536 dwords and 806 drawn, zo-p-160 5632 of 5632 and 3040 under "
             "H-OVL-PASS (H-OVL-FIRST 1146 and 4416, H-OVL-SKIP 1024 and 4288 with 1440 and 5728 "
             "predicted drawn); zo-s-64 1536 of 1536 bytes and 1024 drawn, zo-s-160 5632 of 5632 and "
             "3840. Every NaN row stored one value at every dword of the target: 0x00ffffff (format 1) or "
             "0xffffffff (format 2), 0 drawn. The frozen scorer re-run on the kept files is byte for byte "
             "the run's (fold/reproduce.out). sgx-pipe's `zls::pass_plane` now passes overlapping whole "
             "tiles in visit order and `encode_depth` stores a NaN at the top of the range; "
             "tests/closing_r16_zls.rs replays every zo- row."),
    shows=("The load pass and the overlapping store compose: each tile reads its own slot (the shared "
           "slot's dwords for every tile sharing it) and E996's last-visited tile owns the stored slot "
           "[infer: with E1050's pass, per tile]. A NaN kept from the load reaches the integer "
           "conversion as above every depth, as in the compare (E995), and clamps there (E1051)."),
    not_shows=("A store past its buffer (E411's faults: a planned fault, Q299's remaining clause); "
               "a pass over overlapping tiles with edge tiles; a NaN produced by the plane rather than "
               "the load; infinity loaded into an integer store."),
)
R["E1066"] = dict(
    file="mte/E1066-r16-zls-zoff-below-0-5-the-viewport-z-offset-gives-the-plane-1-6-w-plus-0-4-s-t-held-out-8-of-8-outside-a-fixed-bend-and-not-the-polygon-cut.md",
    models=("H-LIN", "H-LIN-S", "H-POLYCLIP"),
    terms='["VIEWPORT.Z_OFFSET", "VIEWPORT.Z_SCALE"]',
    claim=("r16-zls rows zw2- (Q069, 9 jobs in stage zoff, t10): on E987's ramp (256 x 128, t = x / 512, "
           "format 0) the viewport's z offset w at 0, 1/16, 3/16, 5/16, 3/8 and 7/16 stored (1.6 w + 0.2) "
           "t (frozen H-LIN [fitted on E981's and E987's two rows by the offline gate OQ069] 6 of 6) and "
           "at w 0.25 with the z scale s at 0.25 and 0.75 stored (1.6 w + 0.4 s) t (H-LIN-S 2 of 2), at "
           "every dword outside the 912 pixels by the far edge where the kept rows bend; E1056's polygon "
           "cut at z = 0 failed 7 of 8 (it held only at s 0.25, where no vertex is below 0); the "
           "control passed"),
    ran=("Offline first (OQ069, gen/oq069.py and gen/oq069rs, before the freeze): E987's zw-0125 and "
         "E981's z2-a-f0 through sgx-pipe `isp::depth_cut_image` (E1056) and E987's H-LIN: the cut "
         "covers 8192 and 16384 of the 32768 pixels both rows drew, H-LIN holds at 31856 of 32768 "
         "dwords of each and the other 912 are one set in both (BEND). Then E987's zw form (the triangle "
         "(0,0) (512,0) (0,256) at depths 0, 1, 0, 0x0017103c, depth less) with `--poke blk:10=w` at w "
         "7/16, 3/8, 5/16, 3/16, 1/16 and 0 and with `--poke blk:11=s` at w 0.25 for s 0.25 and 0.75 "
         "(state-block words 10 and 11, the viewport's z offset and scale, 3d.md 9.1). Frozen: H-LIN "
         "[fitted] and H-POLYCLIP (the cut of z = s (2 t - 1) + w at 0, sgx-pipe's coverage) on every "
         "row, H-LIN-S [infer: the two points written with the far and near vertex depths] on the "
         "scale rows, each outside BEND. Control: zw2-c-0125 (E987's zw-0125 on t10, byte for byte)."),
    results=("Control: 32768 drawn and the dump byte for byte E987's. Every row drew all 32768 pixels; "
             "z / t along y = 0 was 0.9, 0.8, 0.7, 0.5, 0.3 and 0.2 for w 7/16 to 0, and 0.5 and 0.7 for "
             "s 0.25 and 0.75 (READING lines), each at 31856 of 31856 dwords outside BEND within 1e-5. "
             "Off the row's own line lay exactly BEND's 912 pixels on every row with a vertex below 0, and "
             "none at s 0.25 (vertex depths 0 and 0.5). H-POLYCLIP held only at s 0.25. The frozen "
             "scorer re-run on the kept files is byte for byte the run's (fold/reproduce.out). sgx-pipe's "
             "`mte::triangle` refuses a viewport depth below 0 (tests/closing_r16_zls.rs)."),
    shows=("Below 0.5 the z offset does not clip the plane at z = 0: on this triangle the near vertices "
           "(at t 0, depth w - s below 0) store 0 and the far one w + s + 0.6 (w - s), the plane through "
           "them, 8 of 8 held out [infer: a rule of the vertex depths, one triangle]; the bend by the far "
           "edge is the same 912 pixels at every offset and scale with a negative vertex."),
    not_shows=("Why 0.6; the bend's values; another triangle or a negative vertex elsewhere than "
               "at t = 0; OUTSEL bit 13 and the presence bits 16 to 31 (they need the tool to grow the "
               "block past bit 7)."),
)


def fill(draft, rec):
    t = open(draft).read()
    t = t.replace('claim = "TODO-FILL: the claim, with the frozen verdict quoted"',
                  f'claim = "{rec["claim"]}"')
    t = t.replace("(TODO-FILL: round, decisions, plan)", f"({ROUND})")
    t = re.sub(r"on the laptop \(TODO-FILL[^)]*\)", lambda m: LAPTOP, t)
    t = t.replace("terms = []", f"terms = {rec['terms']}")
    t = t.replace("**What ran.** TODO-FILL", "**What ran.** " + rec["ran"])
    t = t.replace("**Results [HW].** TODO-FILL", "**Results [HW].** " + rec["results"])
    t = t.replace("**What it shows.** TODO-FILL", "**What it shows.** " + rec["shows"])
    t = t.replace("**What it does not show.** TODO-FILL",
                  "**What it does not show.** " + rec["not_shows"])
    # the frozen verdict: this record's models only
    head, _, rest = t.partition("**Frozen verdict (as printed).** ")
    verdict, _, tail = rest.partition("\n\n")
    parts = [p for p in re.split(r"; (?=attempt )", verdict.rstrip("."))
             if re.search(r"SUMMARY: \w+: (%s)[ :(]" % "|".join(map(re.escape, rec["models"])), p)]
    t = head + "**Frozen verdict (as printed).** " + "; ".join(parts) + ".\n\n" + tail
    assert "TODO" not in t, t[:300]
    return t


def main(drafts, ev):
    for k, rec in R.items():
        p = os.path.join(ev, rec["file"])
        open(p, "w").write(fill(os.path.join(drafts, k + ".md"), rec))
        print(p)


if __name__ == "__main__":
    main(*sys.argv[1:3])
