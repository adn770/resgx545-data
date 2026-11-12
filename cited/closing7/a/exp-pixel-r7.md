# Round 7 plan, area render/pixel (2026-11-12)

Planner output for `closing7/BRIEF-COMMON.md`. Seeds: handover r6 "Next" item 3 (Q287 odd widths,
Q291, Q276, Q293, Q139, Q086). Nothing here touched the laptop, cachix or a repository; every
file of this plan is under `closing7/a/`. Tags: [data] counted from kept files, [post hoc] read
after the run that made the data, [infer] my inference, [HW] a landed record's measurement.

State the plan starts from: resgx545 main 418467e (records to E892), data 7533ddc0, fork
`resgx545` 3f0b3e74; the laptop runs the test kernel 7.3.0-resgx545 with module 41E2F5C7 until its
next reboot, which returns to the distro kernel (no render node there:
`tools/bringup/boot-test-kernel.sh`).

## 0. Summary table

| seed | offline (done here or in the fold) | laptop rows | tool | faults expected |
|---|---|---|---|---|
| Q293 | DONE here: render 2's own object, 13 of 13 kept dumps, 11 of 11 images | 4 | t4 | 0 |
| Q291 | DONE here: `pix_posstore.s` assembled, sgx-sim 2048 of 2048 pixels | 27 | t6 | 0 |
| Q287 | cells computed here; tool change specified (lead lands it, test first) | 25 | t7 new | 0 |
| Q276 | own-source scorer: fit on R6's kept p6-rd (fold), nothing decidable offline | 48 | t4 | 0 |
| Q139 | nothing decidable offline (E877: no dump kept); selection and scorer | 24 | t4 | 0 |
| Q086 | H-COV's axes are not separated by E886 [data]; boundary rows computed | 11 | t4 | 5 |

One session, `r7-rp`, 143 jobs, about 25 minutes of jobs, 50 minutes planned with staging
and health. Test kernel with module 41E2F5C7 as installed; no kernel change.

## 1. Offline first

### 1.1 Q293: render 2's own object is already in the kept dumps [data, post hoc]

Q293's last open item is "what does the TA write for render 2's own object, and how does the 3D
read it" (E888 left it as the one item its rows did not run). The rows of E829 and E888 are
`tri --tri-full -n 2 --geometry 1`: render 1 tiles its triangle and leaves the scene open, render
2 tiles its own triangle and draws. Their kept `--dump-render` files therefore hold both objects.

Run here (read-only, `closing7/a/q293/`):

- `obj2_scan.py` (output `obj2_scan.out`, `obj2_inserted.out`): every `*param.bin.gz` under
  `resgx545-data/render/closing-*` (1342 dumps), the objects that open as the one-triangle
  scene's does and the place of the format word 0x00040101 in each.
- `obj2_images.py` (`obj2_images.out`): the job's own text for the 13 dumps found.
- `t7_words.py` (`t7_words.out`): the first 96 dwords of E888's t7 and t8 dumps.

Result: 13 kept dumps have two objects under `CR_TE_AA` 0x40000000 (r3k-pixel k-pb0 2,
r3k-regress rg-pb 3, r4-q285 a-pb 5 and a-pb0 2, r6-render4x t7). In 13 of 13 the second object
starts at dword 27, has a zero at its dword 11 (dump dword 38) and its format word at its dword 12
(dump dword 39): the same 27-dword layout with the inserted zero as the first object. In the 11
jobs whose first object was not put in the bit-29-set layout (no poke, or 0, 1, 0xffffffff at
dword 11) the last image has 0 triangle pixels of 4096, although render 2's own triangle covers
the target (`--tri-full`): the 3D drew nothing for it either. The two twin rows (E829's p3a, p3b)
show 4096 triangle pixels and cannot tell which object drew: both triangles are the same and the
pages hold render 2's colour by then.

- Rests on: E728, E829, E888 and the four sessions' kept files (paths in `obj2_inserted.out`).
- Label: post hoc, no frozen prediction; one command shape (64 x 64, 0x40000000, triangle).
- Refuted by: a dump where the second object has its format word at +11, or an image with
  triangle pixels in a job whose first object is displaced.
- Needs a held-out check: yes, section 3.5 (three rows that poke the second object).
- Fold: one offline record (ta), the three scripts and outputs published with it
  (`scratch_cites.py --publish`; nothing is firmware-derived). No landed claim is contradicted:
  Q293's text says render 2's own object was "not drawn in E829's jobs", which this counts.

### 1.2 Q291: the new pixel program, assembled and checked in sgx-sim

R6-misc dropped Q291 because no landed program stores an instance's attribute at a scratch
address formed from its position (r6-misc README, deviation 1). Draft here: `q291/pix_posstore.s`
(listing `pix_posstore.lst`, binary `pix_posstore.bin`, hashes `SHA256.txt`), assembled with the
landed `tools/usse-asm/usse-asm` (16 instructions):

```
phas #0, #0, pixel, end, parallel
shl r1, g24, #5              ; slot = g24 << 5 | g23   (y mod 16, x mod 32: E808)
or r1, r1, g23
and r1, r1, #0x1ff           ; an invalid instance cannot store past 8 KiB
or r1, r1, #0x00100000       ; register offset = high x low = 16 bytes x slot (eot_tile.s rule)
or r2, g25, #0x7E570000      ; the lane, tagged
mov r0, #0x5CAF0000
stad [r0,+r1], pa0           ; dword 0: pa0, every instance that runs (E111)
mov r0, #0x5CAF0004
stad.skipinv [r0,+r1], pa0   ; dword 1: pa0, valid instances
mov r0, #0x5CAF0008
stad.skipinv [r0,+r1], pa1   ; dword 2: pa1, valid instances
mov r0, #0x5CAF000C
stad.skipinv [r0,+r1], r2    ; dword 3: 0x7E570000 | g25, valid instances
idf drc0, bif
wdf drc0
mov.skipinv.end o0, pa0
```

Design choices and their reasons:

- Only g23, g24 and g25 are read: the three registers measured in a triangle's pixel task (E808,
  29 of 29 rows) and the only ones sgx-sim answers there (`usse.rs` `global()`; it refuses g18).
  A per-tile register would let one job read several tiles, but g18's rule is not measured in a
  triangle (E086 is a fill; E374 only says it varies), so the sim could not check the program.
- Consequence: two tiles of one job would share slots. Every Q291 row therefore touches ONE tile:
  either the target fits one 32 x 16 tile, or the triangle is cut to one tile (section 3.3).
- The value and the address are independent: the address comes from the global registers, the
  value from the iterator. With E437's position pair (pa0 = x + 0.5, pa1 = y + 0.5) every stored
  slot checks itself (value = slot position), and dword 3 checks the lane. Controls that can fail.
- `probe --tri` already prints every changed scratch dword (`sgxfive-test.c` `probe_scratch`, no
  cap in the triangle probe) and patches the 0x5CAFnnnn immediates: no tool change is needed.

Sim check (`q291/simcheck/`, a copy of r6-pixel's `debug-src/simcheck` harness; built with
`CARGO_TARGET_DIR` in my directory, removed after the run; output `simcheck.out`): the program run
as a triangle's pixel instance at each of the 2048 pixels of a 64 x 32 area with pa0 = x + 0.5 and
pa1 = y + 0.5: 2048 of 2048 pixels store exactly (base + 16 slot: pa0, pa0, pa1, lane tag) and
leave o0 = pa0. What the sim does not cover [infer, for the hardware control]: one instance at a
time (no lanes, no invalid instances), and the register-offset store rule is measured in the
end-of-tile and vertex tasks (`eot_tile.s`, `vtx_dump_sa.s`), not yet in a triangle's pixel task.

Session builder's part: land nothing; copy the draft into the session (`templates/`), assemble it
there, rerun the sim check as a session test (`tests/test_sim.py` style), pin the binary's hash.
After the fold the program goes to `probes/pds/templates/` with a probe table.

### 1.3 Q287: the odd-width cells and the tool change

Cells (`q287/oddw_cells.py`, output `oddw_cells.out`, from the published model
`closing6/r6-misc/gen/r3_geo.py`): at H 18 rule A and FLOOR differ inside the tile area at W 7,
11, 15, 19, 23, 35, 39, 43, 47, 51 (A stores one column more: 24 against 23 at W 19, 44 against 43
at W 35). W 27 and 55 do not separate (the band passes the tile area); 17, 21 and 33 are the .25
confirmations (A = FLOOR; CEIL one more).

Why the tool refuses odd widths: `sgxfive_pbe()` writes the line stride in 2-pixel units
(`pbe[2] = 0x80 << 8 | (stride / 8 - 1) << 16`, `src/xfer.c`), and the triangle scene passes
`4 * p->width` as the stride (`render.c` `put_eot`, `tri_probe.c`). Nothing else needs an even
width: the screen, tiling and MTE words take W - 1 or the tile count (a6d78db's message).

The change (one resgx545 commit, "libsgxfive: allow odd target widths", test first; the lead or a
build agent lands it on main before the freeze, as a6d78db was for R6):

1. `include/sgxfive_render.h`, `src/render.c`: `sgxfive_tri_stride_px(width)` = `(width + 1) &
   ~1u`, the colour buffer's row pitch in pixels. `put_eot` and `tri_probe.c` pass `4 *
   stride_px` to `sgxfive_pbe` (XMAX stays W - 1); `fb_size`, the guard fill and
   `sgxfive_tri_check` index `fb[y * stride_px + x]`; `sgxfive_tri_scene` drops `p->width % 2`.
2. `tools/sgxfive-test.c`: the probe's size check drops `pt->width % 2`; `print_target` and
   `probe_report` take the stride (struct target already has one).
3. `src/mock.c`: the mock's store honours the PBE line stride if it does not already (the
   builder checks; the mock tests below fail otherwise).
4. Tests, written first: `tests/test_render.c` (stride_px at 1, 19, 20, 4095; a 19 x 18 scene
   accepted with PBE word 1 = 18 | 17 << 16 and stride field 9, `mte_screen` 18 | 17 << 16; for
   every even W of a list the five PBE words byte-identical to the old expression: even widths
   must not change; `sgxfive_tri_check` on a stride-20 buffer); `tests/test_cli.py` and
   `test_cli_tri_probe.py` (mock `tri --width 19 --height 18 --tri-full --pixels` prints 18 rows
   of 19 values; mock probe at 33 x 17; the odd-width usage-error tests become acceptance tests).
5. Costs to name: the IGT vendored copy (`test_vendored`, check.sh with RESGX545_IGT) must be
   re-synced or the full check fails; `sgx-pipe` `zls.rs` keeps refusing odd widths until the
   fold.

Build: `lead/build_tool7.sh` = r6-misc's `lead/build_tool6.sh` with COMMIT = the landing commit,
`TOOL7SRC.sha256` pinning `sgxfive-test.c`, `render.c` and the two git trees, build directory
`~/sgxt-r7` on the build host, output `debug/tool7-i686/sgxfive-test`, slot `TOOL7.sha256` filled
once by `run/freeze_*.sh tool7 S7`. The binary never reaches the laptop except through the stage
script, which checks its hash there.

A second route that needs no tool change (rows in section 3.2, run with the same binary): an
even-width job with the MTE screen word and the viewport poked to an odd width (`--poke
cmd:9=...`, `--poke blk:6=`, `blk:7=`). It also says which word carries W in the band, which no
record separates (E730, E831 and E885 changed every size word together) [data].

### 1.4 Q276: what is offline and what is not

E878's verdict is cannot tell by one frozen number: the class share was taken over all 1062 TRI
pixels, and 113 to 134 of them hold words that other sources' `o1` to `o3` writes displaced there.
Its post hoc reading (H-MOD4: `o1` to `o3` read their own word, `o4` to `o7` the word of `o0` to
`o3`) uses the data the scorer would be fitted on, so no offline step can turn it into a held
result. Offline work is the scorer only: `score_rd7.py`, R6's reader (`score_rd.py`, `rdmodel.py`)
with the share taken over own-source words, replayed on R6's kept p6-rd as its FIT set (it must
reproduce `fold/posthoc_r6.txt` section A: the vector S S S A0 A4 A4 A4, own-source shares 0.903
to 1.000) and frozen before the rerun. The fit set's lowest own-source share is 0.903 (rd-4,
rd-6 y jobs: 85 own-source tag-2 words beside the top label) [data], so a 0.90 bar would repeat
E878's slip; the frozen rule is in section 3.4.

### 1.5 Q139 and Q086

- Q139: E877 already ran the offline test (H-SLOT failed, 39 of 104) and states that neither
  dataset kept a header or stream dump: `find` shows no `*.bin*` file under `ta/mtile-fields` or
  `ta/mtile-fields-risky` (they hold `dumps/NAME.txt.gz` only) [data]. Nothing more is decidable
  offline; the dump rows are section 3.6.
- Q086: the 11 unrun rows are all far from H-COV's boundary (grid 4 x 4 of 12 x 12 up to 32 x 48
  tiles for FX, 8 x 8 or 16 x 24 of 14 x 14 up to 32 x 48 for HS: `r6-misc/predictions/
  q086.tsv`), farther than the three rows that did fault (4 of 10, 8 of 10, 8 of 12). And in
  E886's nine rows the grid is short on BOTH axes in every fault and covers both in every
  completion [data]: "covers on both axes" (H-COV), "covers in x", "covers in y" and "has at least
  as many tiles" all fit 9 of 9. The 11 rows would not separate them either. Section 3.7
  replaces them with four rows that do.

## 2. The session: r7-rp

One session, built offline by one builder against main after the tool commit, frozen
(FROZEN.sha256, PREDICTIONS.sha256, FROZEN.commits), run once. Stage order, safe first:

| # | stage | question | jobs | tool | min | fault limit |
|---|---|---|---|---|---|---|
| 1 | s0 | bridge controls on 41E2F5C7 | 4 | t4, t7 | 1 | 0 |
| 2 | q287 | Q287 odd widths | 25 | t7 (t4, t6 controls) | 4 | 1, none expected |
| 3 | q291 | Q291 attribute band | 27 | t6 | 4 | 1, none expected |
| 4 | p7-rd | Q276 readback | 48 | t4 | 5 | 1, none expected |
| 5 | q293 | Q293 second object | 4 | t4 | 1 | 1, none expected |
| 6 | q139 | Q139 TA dumps | 24 | t4 | 7 | 1, none expected |
| 7 | q086 | Q086 axes | 11 | t4 | 3 | 6 (5 predicted) |

Tools: t4 = `~/sgxfive-test-rgn4` (e6951558..., the binary of every precedent row); t6 = R6's
build of d9b2969 (97df5c0e..., restaged from the Mac copy `r6-misc/debug/tool6-i686/`); t7 = the
new build. Each stage's rows use the tool of the record they replicate, so controls compare token
for token; s0 shows the three tools agree on the default triangle and on E831's 34 x 18 depth row
(924 stored dwords).

### 2.1 Which boot

Every stage needs the test kernel (render node, debugfs kpoke, `render_param`, `--aa4` contexts);
none needs a kernel change. Module 41E2F5C7 as installed is right: it has R6's four-array
contexts and its tail room is automatic at knob 0.

- If the laptop is still up on 41E2F5C7: no reboot; the runner's preflight checks kernel,
  srcversion loaded = installed, knobs at defaults (`render_tail_room` 0, `render_rgn_arrays` 0,
  `hold_recovery` N, `render_pb_pages` 0x422), tools' hashes.
- If it was rebooted: one one-shot boot (`boot-test-kernel.sh`), which needs the user's OK; then
  `test-session.sh` and the srcversion check (memory: laptop test boot).
- What differs from the precedents' boot: R6's pixel, misc and render4x A rows ran on 99CD90DA.
  41E2F5C7 changes the 4x tail room (E889), so Q086's faulting precedent is repeated as a bridge
  row (section 3.7); the 1x paths are covered by s0 and each stage's own controls.

### 2.2 Laptop rules (as R6, HACKING)

Files only under `~/scratch/r7rp/` (run, bin, stage, out) and one `mktemp -d
~/scratch/tmp/r7rp.XXXXXX` per stage, 200 MB free checked before each job (rc 22), job
directories removed once kept, never `/tmp`. Debugfs through `sudo -n`; the runner writes only
`reset 1`; the tool writes its own kpokes (depth recipe, `ta:143/144/146`, `par:N`). Kernel-log
slices by marker (`os.open(O_WRONLY|O_APPEND)` or `sudo -n tee -a /dev/kmsg`). No clock-gate
write, no firmware `str`, no trc_hazard, no reboot, no build on the laptop.

### 2.3 Slips designed out

- R6 dpm a1 (a function not staged): the mock runs the STAGED tree under `env -i`; a test lists
  every function the runner calls and greps its definition in the staged files.
- R6 misc (dumps never written): the runner makes `$JW/depth` and `$JW/dump`; `REQUIRED` in each
  scorer lists every file it reads; the runner stops rc 23 when one is missing or not kept; the
  mock's fake tool needs the directory as the real one does.
- R6 dpm a2 (a control with no reading by construction): every control below names the reading
  that fails it; `tests/test_controls.py` runs each control's scorer on a doctored input that
  must fail.
- R4 (control on the default triangle, scorer reading the wrong dump name): controls are rows of
  the stage's own shape; the replay tests run each scorer on the kept files of its precedent
  under their real names (E831 and E885 dumps, R6's p6-rd, E888's t7, E886's rows).
- R5 (/tmp, 16 ms mock margin): no `/tmp`; no timed flow in this session, every sleep 0 in the
  mock.

## 3. Stages: rows, predictions, controls, stops

### 3.1 s0 (4 jobs)

Default 64 x 64 triangle with t4, t6 and t7 (exact, 0 wrong) and health; E831's `z-ctl-34x18-y`
with t4 (924). A miss stops the session before any stage (rc 30).

### 3.2 q287: Q287 odd widths (25 jobs, t7)

Row shape: E831's and E885's depth row, `tri --keep-overflow --wait-ms 20000 --width W --height
18 --tri-full --tri-z Z --depth --depth-ctl 0x17100c --depth-fill 0xdeadbeef --depth-dump
"$W/depth" --depth-pages N --poke blk:1=0x00400200`; x ramp `--tri-z 0.25,0.75,0.25` by
default, the y ramp as the second reading. The depth dump is tile-major (E465), so the colour
buffer's stride does not enter the reading.

| set | rows | jobs |
|---|---|---|
| gate | `z-dry-33x18` (a .25 cell, first): the module may refuse an odd width | 1 |
| control | 34 x 18 with t4, t6, t7 (924 each), t7 with the y ramp | 4 |
| fit | W 19, two runs | 2 |
| held out | W 7, 11, 23, 35, two runs each; y ramp at W 19, 23, 35; W 43 and 51, one run | 13 |
| confirm | W 17, 21 (.25: A = FLOOR, CEIL one more) | 2 |
| poke twins | W 20: `cmd:9=0x00110012`; `blk:6`, `blk:7` = 0x41180000 (9.5); both | 3 |

Frozen predictions (per row: stored count, set hash, extent, from `r3_geo.band_set`):

- H-A (predicted; Q287's own text, E885 on the y side): x + 0.5 < 1.25 W. H-FLOOR: x <
  floor(1.25 W). ROUND, CEIL, RSTRICT scored as in R6. Counts at H 18: W 19 A 528, FLOOR 506;
  W 35 A 968, FLOOR 946; W 7 198 / 176; W 11 308 / 286; W 23 638 / 616; W 43 1188 / 1166; W 51
  1408 / 1386 (`q287/oddw_cells.out`).
- Poke twins, no favourite, both frozen [infer]: H-SCR (the band's W is `CR_MTE_SCREEN`'s x field
  plus 1) against H-VP (2.5 times the viewport's half width). `cmd:9` alone: H-SCR 24 columns,
  H-VP 25. Viewport alone: H-SCR 25, H-VP 24. Both: 24 under either (the emulated W 19).
  A row that reads neither is reported as such; it does not gate Q287.

Controls that can fail: the three 924s (a t7 that changes an even width fails here); the gate;
replicates must agree (a disagreeing pair is "mixed", never held); `dead` = 0 tile-area dwords
left at the pre-fill inside the stored set.

Verdict: A held iff all held-out cells read A's set; FLOOR held iff all read FLOOR's; else none.
Either retires Q287 (it closes on the depth rule; Q291 is separate). gateodd (rc 21): the module
refused the odd width; the stage ends cleanly, Q287 becomes "odd widths refused by the kernel",
the poke twins still run (they are even widths) and the session goes on.

Stops: rc 4 any fault or hang (none expected: the depth jobs of this shape ran clean in E730,
E831 and E885); rc 23 a dump not kept.

### 3.3 q291: Q291, the attribute band (27 jobs, t6)

Row shape: E606's iteration job with the new shader, `probe --tri pixpds:12 --temps 32 --pixels
--width W --height H GEOM --slot pixel="$S/pix_posstore.bin" "$S/PDS.bin"`, PDS = E437's
position pair (`pds_iter_nofetch.s`, DOUTI0 0x20400000, U1 0x01000004: pa0 = x + 0.5, pa1 = y +
0.5, 1062 of 1062 in E437) for set P, and E606's vertex pair (0x20400800 with `--vtx-coords 2
--slot vtxuse=vtx_attr_zx.bin`: pa0 = clip z, pa1 = clip x iterated) for set V. Read: the changed
scratch dwords, 4 a slot; "valid set" = slots whose dword 1 changed.

| set | rows | jobs |
|---|---|---|
| gate + control | P at 32 x 16 `--tri-full` (target = one tile; all 512 slots known) | 1 |
| control | `pix_pa0` (the landed shader) with the position pair at 20 x 12: the image | 1 |
| control | P at 64 x 16 and 32 x 32 with the cut triangle (tile (1,0); tile (0,1)) | 2 |
| control | V at 32 x 16 | 1 |
| fit | P at 20 x 12, two runs | 2 |
| held out, one tile | P at 18 x 12, 24 x 8, 12 x 12, 20 x 8, 26 x 10, 10 x 6 | 6 |
| held out, cut in x | P at W 34, 36, 44, 50, H 16; triangle (32,0) (128,0) (32,48) | 4 |
| held out, cut in y | P at 32 x 18, 32 x 24; triangle (0,16) (96,16) (0,64) | 2 |
| held out, vertex pair | V at 20 x 12, 18 x 12, 24 x 8 | 3 |
| depth twins | `tri --depth` (3.2's shape) at 20 x 12, 18 x 12, 24 x 8, 12 x 12, 10 x 6 | 5 |

The cut triangles (`--tri-v`, 1/256 pixel) have their right angle on the tile's corner, so by the
ISP's fill rule (E606) no pixel of another tile is covered and no quad straddles the edge (quads
start at even x and y); the targets have one tile row (H 16) or one tile column (W 32), so the
spill past the tile has no tile to land in. That is what keeps slots unique.

Frozen predictions for the valid set of each row, three rivals, exact set equality:

- H-BAND (predicted, Q291's text, [infer: the band is a clip, E730]): the depth band's set, x +
  0.5 < 1.25 W and y + 0.5 < 1.25 H, inside the tile and the triangle (20 x 12: 25 x 15 = 375
  slots; 34 x 16 cut: columns 32 to 41).
- H-TARGET: only pixels inside the target (20 x 12: 240).
- H-TILE: every pixel of the tile the triangle covers (512).
- Values (set P): dword 1 = f32(x + 0.5) and dword 2 = f32(y + 0.5) at every valid slot, past the
  target too (H-LIN); a clamp or any other value is reported per slot. Set V: clip x linear in x
  within E661's 23 units of 2^-23, clip z within 4.
- Secondary, not gating [E111]: dword 0's set is the valid set grown to whole 2 x 2 quads.
- Depth twins: rule A's stored set (E831's rule at sizes never run: all kept depth rows have W
  and H of 18 or more; a miss here is a finding for Q287's rule, reported, and makes the
  attribute rows at that size "no depth reference").

Controls that can fail: the gate row (512 slots, each value its slot's position, each lane tag
(x & 1) | (y & 1) << 1; any miss means the slot rule, the lanes or the position pair is not what
E808 and E437 say, and the stage stops, rc 24); the cut-triangle controls (512 slots with x from
32.5, y from 16.5: a spill or a shared slot shows as a wrong value); `pix_pa0`'s image (exact
x + 0.5 words); in every row the in-target slots must hold their position (a per-row check).

Verdict: H-BAND held iff every held-out P row's valid set equals its set (the 12 rows all
separate it from both rivals); then Q291 is answered "the same band" and, with Q287, Q122's
attribute side closes. H-TARGET or H-TILE on every row answers it the other way. Mixed: narrowed.

Stops: fault limit 1. The risk that is new: a per-instance scratch store in a triangle's pixel
task. The 9-bit mask bounds every store to the first 8 KiB of the 64 KiB buffer; the gate row is
the first job and a fault there ends the stage with strict health (rc 4), the session goes on.

### 3.4 p7-rd: Q276 (48 jobs, t4)

R6's p6-rd rerun with the scorer frozen on own-source words, plus rows with no displaced words.

| set | rows (each an x and a y job) | jobs |
|---|---|---|
| control | R6's 14: c-e709, c-u, c-all4, c-ow, c-rd-0, c-prd-0 at k 1 and 7 | 14 |
| replicate | rd-1 to rd-7 (R6's programs byte for byte, `bins/` hashes pinned) | 14 |
| replicate | n-rd-4, x-rd-4 | 4 |
| held out | x-rd-6, x-rd-7 (tags 15, 16 written to `o6`, `o7`), n-rd-5 | 6 |
| held out, clean | cl-4 to cl-7: only `o0` (word A) and `o_j` (word B) written, then read | 8 |
| held out, clean | cl-p4 at k 0: cl-4 with `p1 or.skipinv o4` under the g25 test | 2 |

Frozen scorer (`score_rd7.py`; fit set: R6's kept p6-rd):

- TRI as R6 (own pixels of c-rd-0 in both jobs). A word is own-source when it decodes to the
  pixel itself. A configuration reads class L when, in both jobs, L holds at least 0.85 of the
  own-source words AND no other model class (S, A0, A4) holds more than 0.02 of them. Fit range
  0.903 to 1.000 with every rival class at 0 [data, `posthoc_r6.txt` A]; 0.85 leaves five points.
- Clean rows write no `o1` to `o3`, so no displaced word can land: they are scored with R6's
  original rule unchanged (one class at 0.90 of ALL TRI pixels in both jobs; c-rd-0, the same
  shape, read 1.000). They do not depend on the new threshold at all.
- Models, as frozen in R6: H-STORE (S at 1 to 7), H-FOUR, H-O0, H-MOD4 (S at 1 to 3, A0 at 4, A4
  at 5 to 7). Predicted: H-MOD4, with x-rd-6 and x-rd-7 reading `o2`'s and `o3`'s words and
  n-rd-5 reading `o1`'s.
- Clean rows, frozen: cl-4 reads word A under H-MOD4 and word B under H-STORE. cl-5 to cl-7 read
  what `o1` to `o3` hold, which no instruction of theirs wrote: the prediction is "not word B"
  (H-MOD4) against "word B" (H-STORE), and the word they do read is reported (E878's n-rd-1 read
  the background word, post hoc). cl-p4: word A on every lane (the predicate cannot show).

Controls that can fail: R6's bridge (c-e709 G-o4, c-u tag-2 fraction at least 0.98, c-ow and
c-rd-0 at least 0.95, c-prd-0 lanes) gates the stage as in R6; the replicate rows must repeat
R6's top labels (a row whose top label differs from R6's is "not replicated" and voids its
entry).

Outcomes: H-MOD4 held (replicates decided, held-out rows as predicted) means no read of `o4` to
`o7` shows a word of their own in this command; with E871 (no pixel) nothing observes such a
write, so by R6-6 (a), carried, the predicate clause is retired as not observable and Q276's line
keeps only "why the lane of the OR's `o3` word depends on the job" (E880). H-STORE at any j of 4
to 7 reopens it: E878's reading is then refuted and needs an appended correction to its post hoc
paragraph (not to its claim, which is the frozen cannot tell).

Stops: fault limit 1 (no fault in R5's p5-o4 or R6's p6-rd, E858, E878); a gate fail ends the
stage.

### 3.5 q293: render 2's own object, held out (4 jobs, t4)

Three renders in one scene, `tri --tri-full --keep-going --wait-ms 20000 --width 64 --height 64
--max-width 64 --max-height 64 -n 3 --geometry 1 --geometry 2 --poke cmd:1=0x40000000 --poke
cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26 --dump-render "$W/dump"`,
knob `render_rgn_arrays` 1 as stage t (`rgn:1`). The kernel poke before render 3 reaches the
object render 2's TA wrote (dump dwords 27 to 53).

| row | poke before render 3 | frozen prediction |
|---|---|---|
| u1 control | none | objects at 0, 27, 54, zero at +11, format at +12; 0 triangle pixels |
| u2 control | E888's t7 again (`-n 2`, `2:par:11=1`) | its kept dump head and image |
| u3 held out | `3:par:38..53` = the twin's 16 words (E829's p3 list, shifted by 27) | 4096 |
| u4 held out | `3:par:38=0xffffffff` | 0 triangle pixels |

u3's prediction: the second object, put in the bit-29-set layout, draws (4096 triangle pixels,
0 wrong against render 3's colours), while objects 1 and 3 stay displaced and draw nothing: the
3D reads render 2's own object as it reads render 1's (E829). Rival: 0 pixels (the second
object is read differently, or not at all). u1 can fail (a different layout with three objects).

Verdict and outcome: u1, u3, u4 as predicted answers Q293's last item held out; with section
1.1's record the question has no bounded item left (what the dword is "for" has no finite test,
R6's rewording). Stops: fault limit 1; `-n 3` with two geometry-only renders is new for this
command (E888 ran `-n 2`), so u1 runs first and a failure of class other than ok ends the stage.

### 3.6 q139: TA dumps at the missed cases (24 jobs, t4)

Row shape: the dataset's own command (`ta/mtile-fields*/cases.tsv`, token for token) plus
`--dump-render "$W/dump"`: `tri --tri-full --pixels --width W --height H --max-width W
--max-height H --kpoke-render 1:ta:14x=V... --dump-render "$W/dump"`. Every chosen case completed
with a whole image in its dataset (wrong tiles, no fault).

| set | cases | jobs |
|---|---|---|
| control | unpoked 256 x 256 and 640 x 480 (exact image; the baseline dumps) | 2 |
| control | 256 x 256 m1-B1-5 (poked; not among E877's misses) | 1 |
| fit, 256 x 256 | m1-B2-8, m1-B2-5, m2-B2-10, stride-8, stride-16, part1-8_8_8 | 6 |
| fit, 640 x 480 | m1-B1-20, m1-B2-20, m2-B1-17, one m2-B2 case at or past B3 (exact) | 4 |
| held out, 256 x 256 | m1-B2-12, m2-B2-12, stride-4, stride-24, part2-10_10_10 | 5 |
| held out, 640 x 480 | m1-B1-28, m1-B2-32, m2-B1-20, a second m2-B2 past B3, bit 31 | 5 |
| replicate | m1-B2-8 again | 1 |

All named cases are rows of `ta/mtile-fields-risky/cases.tsv` and, but for the control, misses of
E877's frozen model (`closing6/fold-misc/q139/q139_score.out`) [data]; the two "m2-B2 at or past
B3" cases and the bit-31 case are picked by the builder from the same file (Q139's text: exact
6 of 6 in CR_TE_MTILE2; bit 31 wrong at 640 x 480).

Protocol (E877's split, in one run): all 24 jobs run; the fit rows' dumps are read first, a
placement model is fitted, hashed and committed to data; only then are the held-out dumps read.
The session freezes before the run what it can:

- Replication (gating): each case's wrong-tile set equals the one its dataset kept (E877's maps).
  A case that does not replicate is dropped from both sets.
- H-MOVED [infer], frozen: a tile is wrong iff its region header is not where the baseline job
  of the same size has it (read with `tools/usse-asm/region_tiles.py` and `pbdump.py` from
  `tri.param.bin` and `tri.tadata.bin`; the baseline is the unpoked control of this stage).
  Rival H-INPLACE: the header is in place and the tile is wrong anyway (then the loss is in the
  streams or on the 3D side, and Q139's "which rule places a region's header" is the wrong
  question). Scored per tile over the fit rows before any model fit; a third outcome (headers
  moved for tiles that drew) is reported.
- Controls that can fail: the baselines draw exactly and their region headers decode for every
  tile of the target (else the reader, not the hardware, is at fault: stage cannot tell); the
  exactly-drawing poked control has every header in place under H-MOVED.

Outcome: H-MOVED held on the fit rows gives the placement data the E877 model lacked (header
address per region per case); the frozen-then-read held-out rows say whether the fitted placement
rule generalises. Either way Q139 narrows; it retires only if the held-out rule holds.

Stops: fault limit 1 (these cases completed before; a fault means the boot differs: stop the
stage, rc 4). Disk: 4.6 MB a raw dump, gzipped before keeping; the 640 x 480 pixel text is about
3.5 MB; the 200 MB check covers it.

### 3.7 q086: the axes of H-COV (11 jobs, t4, last)

Row shape: E886's, `tri --tri-full --keep-going --wait-ms 20000 --pixels --width W --height H
--max-width W --max-height H --aa4` with the four 4x pokes and `--kpoke-render 1:ta:143/144/146`.
U2's words (0x01806006, 0x01806006, 0x24) describe a 12 x 12 grid.

| row | size (1x tiles) | H-COV | H-X | H-Y | H-AREA |
|---|---|---|---|---|---|
| bridge R 1024 x 768 | 32 x 48 | ok | ok | ok | ok |
| bridge U2 320 x 160 | 10 x 10 | ok | ok | ok | ok |
| bridge FX 320 x 160 | 10 x 10, grid 4 x 4 | fault | fault | fault | fault |
| R at each new size (4 controls) | | ok | ok | ok | ok |
| U2 448 x 160 | 14 x 10 | fault | fault | ok | ok (144 of 140) |
| U2 320 x 224 | 10 x 14 | fault | ok | fault | ok |
| U2 416 x 192 | 13 x 12 | fault | fault | ok | fault |
| U2 384 x 208 | 12 x 13 | fault | ok | fault | fault |

Frozen: H-COV (both axes must cover; predicted, E886) against H-X, H-Y and H-AREA; each of the
four rows splits them two against two, the four together name one. Bridge rows repeat E886 on the
new module: if FX 320 x 160 completes here, E886's faults depended on the old tail room and E886
needs an appended correction (its claim would name the module); the stage then stops (rc 19) and
the four rows are not scored. A new-size row counts only if its R control completed with 0 wrong.

Order: bridges, then per size the R control and its poked row. Budget 6 fault-class events (5
predicted: FX and the four rows); every fault must be the 3D-side class (BIF_INT_STAT 0x0100,
BIF_FAULT 0x100000xx), followed by a reset and strict health; a TA-side fault, a -110 or a second
failed health stops (rc 18, 16). Risk medium: E886 recovered 3 such faults, E845 and E848 more;
the stage is last so a stop costs nothing else.

The 11 unrun rows (FX past 320 x 160, HS past 384 x 192) are not run: all are predicted to fault
by every one of the four rules, so they separate nothing (section 1.5). Q086's note gets "not
pursued, by design" for them; the closed driver's rule over sizes still needs the capture batch.

## 4. Stop codes (session)

| rc | meaning |
|---|---|
| 1 | preflight: kernel, srcversion, knob, tool hash, table, FROZEN.sha256 |
| 3, 6 | fatal kernel message; a job that did not return (no reset) |
| 4, 5 | unexpected fault, hang or failure (strict health first); failed recovery |
| 12, 13, 14 | registers unreadable; reset failed; a fault latched before a job |
| 15 | q086: the budget's last fault with rows left |
| 16, 18, 19 | q086: failed health after a fault; wrong fault class or -110; bridge FX completed |
| 21 | q287: odd width refused by the module (clean; the session goes on) |
| 22, 23 | under 200 MB free; a file a scorer reads not written or not kept |
| 24 | q291: the gate row's slots are not the frozen ones (stage ends, session goes on) |
| 30-42 | driver: s0 or health after a stage, no SUMMARY, attempt exists, knob not default |

After any stop: no reboot, no module unload, no register write; the lead decides. A refuting
outcome is a result, not a stop.

## 5. Costs, order, reuse

- Builder: one agent, offline, about 30 minutes; reuses r6-misc (runner, q287 and q086
  generators, `build_tool6.sh`), r6-pixel (p6-rd generator, reader, bins), r6-render4x (stage t
  rows, dump scorer), `scorekit.py`. New: `pix_posstore` rows and their scratch reader, the
  q139 dump reader over `region_tiles.py`, `score_rd7.py`, the staged-tree and control tests.
- Before the builder: the tool commit on main (30 to 45 minutes with tests and the IGT re-sync),
  then `build_tool7.sh` on cachix (about 5 minutes). If the user declines the tool change, the
  session drops q287's odd rows and keeps the poke twins on t6.
- Laptop: 143 jobs, about 25 minutes of jobs, 50 planned. Risk low for stages 1 to 6, medium for
  stage 7 (5 predicted, recoverable faults).
- Against the other areas: run before any session that holds resets or provokes -110 (area c);
  no ordering constraint with area b except that q086 leaves the GPU reset-clean.
- Fold: offline record for 1.1 now; session records one per stage; sgx-pipe: `zls.rs` odd widths
  by the rule that holds (refusal lifted), the attribute band if H-BAND holds, `ta.rs` the second
  object's layout and the both-axes validity rule; the program to `probes/pds/templates/`.
- Corrections this plan may need (appended, none now): E878's post hoc paragraph if H-STORE
  shows; E886 if the bridge FX row completes; Q287's and Q291's question lines on retirement.

## 6. User decisions

1. **Offline fold before the build.**
   (a) Recommended: land the Q293 offline record now (section 1.1: 13 of 13 dumps, 11 of 11 empty
   images, labelled post hoc) and publish `closing7/a/q293/`; keep the Q291 draft and the cells as
   builder inputs. (b) Fold everything with the session. (c) No offline record.
2. **Q287: the tool change.**
   (a) Recommended: land "libsgxfive: allow odd target widths" (row pitch rounded up to even
   pixels, section 1.3) test first on main, re-sync IGT, build t7 on cachix with
   `lead/build_tool7.sh`; q287 runs 25 jobs. (b) No tool change: only the three poke twins on t6
   (Q287 narrowed by an emulated width, [infer], not retired). (c) Defer Q287.
3. **Q291: run the new program.**
   (a) Recommended: all 27 jobs (one-tile cells, cut triangles, vertex pair, depth twins).
   (b) One-tile cells only (19 jobs; no cut triangle, no `--tri-v`). (c) Defer; land the program
   and its sim test only.
4. **Q276: the rerun and its consequence.**
   (a) Recommended: 48 jobs with the own-source scorer and the clean rows; if H-MOD4 holds, retire
   the predicate clause as not observable (R6-6 a carried) and keep only the OR-lane clause.
   (b) Minimal: controls plus rd-4, n-rd-4, x-rd-4 and cl-4 (22 jobs). (c) No run: retire the
   clause by decision on E878's post hoc reading (a "decided in" retirement).
5. **Q293: close it.**
   (a) Recommended: the four rows of 3.5; if they hold, retire Q293 as answered by that record
   (the dword's purpose has no finite test, already set aside in R6). (b) Offline record only,
   narrow, no rows. (c) Rows, but keep Q293 open for the "why".
6. **Q139: the dump rows.**
   (a) Recommended: 24 jobs with E877's fit-then-frozen held-out protocol. (b) The 13 control and
   fit rows only; held-out rows in a later round once a model exists. (c) Defer.
7. **Q086: which rows spend the fault budget.**
   (a) Recommended: the 11 jobs of 3.7 (5 predicted faults, budget 6), which separate four
   coverage rules; mark E886's 11 unrun rows not pursued. (b) Also run those 11 (16 predicted
   faults, budget 17; they separate nothing). (c) Only the 11 unrun rows, budget 11, as the seed
   reads. (d) No Q086 rows.
8. **Boot.**
   (a) Recommended: test kernel with module 41E2F5C7 as installed; no reboot if the laptop is
   still up on it, otherwise one one-shot boot with your OK; no kernel change. (b) Wait and share
   a boot with a round 7 kernel series, if area b or c gets one approved (the session does not
   need it; its preflight would pin the new srcversion).
9. **One session or two.**
   (a) Recommended: one session `r7-rp`, stages in the order of section 2, q086 last.
   (b) Two: `r7-rp-safe` (stages 1 to 5, no fault expected) and `r7-rp-ta` (q139, q086).
10. **Sim and vectors in the fold (tests first).**
    (a) Recommended: `zls.rs` odd widths and the attribute band by what holds, `ta.rs` the second
    object and the coverage rule, `pix_posstore.s` as a landed probe template with its sim test.
    (b) Vectors only. (c) Later.

## 7. Ten-line summary

1. Offline, done: Q293's last item is in kept dumps: render 2's own object has the inserted zero
   in 13 of 13 dumps and drew nothing in 11 of 11 images [post hoc]; record proposed.
2. Offline, done: Q291's program `q291/pix_posstore.s` assembles with our assembler and passes
   sgx-sim at 2048 of 2048 pixels; it needs no tool change, only one-tile rows.
3. Q287: the tool refuses odd widths only for the PBE stride; change = row pitch rounded up to
   even pixels, tests listed, t7 built like R6's t6; a poke route needs no tool change.
4. Q287 rows: W 19 fit; 7, 11, 23, 35, 43, 51 held out; three poke twins say which word is W.
5. Q276: rerun with the share over own-source words (bar 0.85, rivals under 0.02) plus clean
   rows that write no `o1` to `o3` and need no new bar; H-MOD4 held retires the predicate clause.
6. Q139: 24 dump rows at the missed cases, E877's split protocol, H-MOVED against H-INPLACE.
7. Q086: E886's nine rows do not separate "both axes" from x, y or area; four rows do; the 11
   unrun rows separate nothing and are dropped (5 predicted faults instead of 11).
8. One session `r7-rp`: 143 jobs, about 25 minutes of jobs, 50 planned; faults only in q086.
9. Boot: test kernel, module 41E2F5C7 as installed, no kernel change; one-shot boot only if the
   laptop was rebooted.
10. File: `/Users/jtorra/src/scratch/resgx545/closing7/a/exp-pixel-r7.md` (10 user decisions).
