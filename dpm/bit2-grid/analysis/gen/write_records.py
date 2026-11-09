#!/usr/bin/env python3
"""Writes the 11.34 draft records (evidence, questions, datasets) from the text below; every number in them is read from
analysis/out/recompute-*.txt (see the plan) and re-checked by hand against the kept dumps."""
import pathlib, textwrap, re
P = pathlib.Path(__file__).resolve().parent.parent / "draft"
def wrap(text):
    out = []
    for para in text.strip("\n").split("\n\n"):
        if para.startswith("|") or para.startswith("- "): out.append(para)
        else: out.append(textwrap.fill(" ".join(para.split()), 98))
    return "\n\n".join(out) + "\n"
def rec(path, front, body):
    (P / path).parent.mkdir(parents=True, exist_ok=True)
    (P / path).write_text("+++\n" + front.strip("\n") + "\n+++\n\n" + wrap(body))

COMMON_METHOD = ("on the laptop (direct cable), kernel 7.3.0-resgx545, module srcversion 5AD04F33F6BCDA7B880E238 (installed equal "
 "to loaded at the start of every script, never reloaded), stock firmware (own_arm off), tool sgxfive-test-1126 (sha256 751f7223c8c731a08d75cfc3920a5d1050488ca3bdc426be45b7c431e600f82e, "
 "unchanged), no kernel or module change, no reboot, no clock-gate register written")

rec("evidence/usse/E570-the-output-registers-o1-to-o3-of-a-pixel-task-land-in-the-region-before-the-one-that-ran-it.md", f'''
id = "E570"
claim = "In the triangle's pixel task, with the eight-register tagged shader at 13 target shapes (64x64 to 256x128) and PDS_SIZE bits 17:16 at 0 to 3, 5551 of the 6329 destination pixels that carry o1's tag and whose source is read (88 percent) lie in the region that precedes the source's region in the order of the TA data's region headers (regions with a stream), at the same place in the tile, 309 two regions back and 449 in a region with no stream; at the 64-wide targets the raster tile index gives the same rule exactly (497 of 497 pairs at 64x64 size 3) and at wider ones it does not; o2 and o3 land one, two or three regions back (o2: 743 one, 318 two, 91 three of 2099; o3: 268, 150, 24 of 532) with no setting tried fixing the offset; two identical jobs show different pixel counts"
unit = "usse"
method = "script tables o23-tiles (26 jobs), o23-order (26 jobs, with --dump-render) and o23-size (16 jobs, with --dump-render), {COMMON_METHOD}: the shader of E406 (o0 to o7 each the pixel's own x or y float, pa0 or pa1, with the low 16 bits the job's marker * 16 + the register number + 1; a distinct program a job), the PDS iteration of pds_iter_xy and the 2-coordinate vertex program, state block word 4 = 0x00000001 | size << 16, every pixel read back; each table in an x job and a y job, from which a destination pixel's source (x, y) is read; the recompute (recompute/recompute_p1134.py) is independent of the run scripts and reads the region headers of the first written TA data page itself"
tiers = ["HW", "infer"]
date = "2026-11-09"
data = ["output-room-tiles"]
terms = ["PDS_SIZE.BITS17_16", "PB_REGION_HDR"]
''', '''
**What ran.** 68 jobs, all completed (no job failed or hung). The 8 jobs of usse-output-room-size
(E081, E139, E406: 64x64 only) were first read offline: for each destination pixel the x job gives
the source column and the y job the source row of the write that reached it (the pixel's own
place gives the tag's high half, (px + 0.5 - W/2) / (W/2)), and o1's writes landed in a tile that
the raster index of two tile columns puts one back, o2's two back, at the same place in the tile.
That reading (H23-T) is fitted to those jobs; the 64x64 jobs here (size 3 and 0) are its fit.

**The raster rule fails beyond 64 wide, the header order holds.** [HW] H23-T, declared before the
first run with the tile index ty * ceil(W / 32) + tx, was right for o1 in 497 of 497 pairs at 64x64
size 3 and 452 of 452 at size 0 and wrong at the wider shapes: at 256x128 the tiles of column 4 land
in column 7 of the row above (a block of four tile columns), at 64x128 the rows 0-7 of a tile land one
tile back and the rows 8-15 two back (o23-tiles: 6 of 54 held-out scores). The region headers of the
TA data (the first written page, 3 dwords each, entries with a stream, in index order) are laid out
in blocks of 4 x 8 tiles; read in that order (follow-up 1, declared after the first run and built
from its tag 2 data) o1 lands in the region one position back in 5551 of 6329 pairs found in the list
(446 of 446 at 64x64 size 0, 481 of 482 at size 3, 262 of 362 at 256x128), in
the region two back in 309 and in a region that has no stream in 449; 20 pairs differ in the place.
The declared "every pixel" (H23-O) was therefore a miss in 68 of 72 scores.

**o2 and o3.** [HW] Tag 3 (o2): 743 pairs one region back, 318 two, 91 three, 1 other, 692 with the
x and y jobs reading another place (the two jobs of a pair are separate runs, and a destination pixel's
last writer can differ), 248 in a region with no stream. Tag 4 (o3): 268, 150, 24, 90 of 532. The
128x128 jobs show o2 mostly two back at sizes 0 to 2 (101 two, 64 one, at size 0) and one back at size 3
(165 one of 298); follow-up 2 (o23-size, 16 jobs at shapes not used before) gave 30 of 44 scores for
that reading (H23-S, built from the 128x128 and 64-wide jobs): o1's dominant offset is 1 in 8 of 8
configs, o2's is 2 at sizes 0 to 2 in 3 of the 4 configs that show it (1 at 192x96 size 0) and at size 3 is 1 at 192x96 and 2 at 64x96, o3's is 1
in 6 of the 7 configs that show it (2 was declared at sizes 0 and 1). With the counts this small the dependence on the size field is
not established.

**Not deterministic.** [HW] The same table at 128x128 size 3 twice (o23-tiles and its repeat) shows 705
and 463 pairs of tag 2 and 324 and 237 of tag 3: which writes survive to the readback depends on the
run, so a count of pixels is not a measure of the rule.

**What it suggests.** [infer] The output registers o1 to o3 are written into the output area of a
region one to three positions earlier in the region list, at the place of the pixel: a tile-sized
output area a register, laid in the order the tiles are processed. The size field's part is not
shown. **Not shown.** Why some writes land two regions back and why the rows 8-15 of a tile do in the
64x128 job; whether the dependence on the region list is on the regions the TA lists or on the ones
the 3D runs; o4 (tag 5: 189 of 192 pairs in the source's own tile at 128x128 size 3, 3 one back) and o5 to o7; the E406 four-output setup at 128x128 (2 jobs: o2 14 pairs and o4 172 pairs, all in the source's own tile, o23-tiles).
''')

rec("evidence/usse/E571-in-a-vertex-task-the-global-registers-read-0-1-1-0xf-and-the-masks-and-the-lane-numbers-of-a-task-of-4-6-or-8-vertices.md", f'''
id = "E571"
claim = "In the vertex task of the triangle job (126 vertices at 4, 6 and 8 vertices a task, 12 jobs), g16, g19, g26-g31 and g40 read 0 and g20 1 on every decoded vertex (119 of 126, the other 7 are not readable), g42 reads 0x3f800000, g41 0xf and g43 0xdf000000 where the pixel task has 1 and 0xff000000, and g17, g22, g24, g25 and g39 follow the vertex's task and lane (g25 = lane mod 4, g22 = lane div 4 mod 2, g39 = 4 * g22, g24 = 8 * (task mod 2), g17 = task mod 4) in 118 to 119 of 119 vertices in the 12 jobs, the four of 4 and 6 vertices a task a held-out test that the fixed grouping of 8 fails (23 to 65 of 119); the last task of 2 vertices reads g41 0x3 and g43 0x20000000"
unit = "usse"
method = "script tables q053-vtx (6 jobs: groups A g16-g23, B g24-g31, C g39-g43 with g17-g19, twice, VDM_TASK0 MAX_VERTICES 7 = 8 a task) and q053-vtx2 (6 jobs, declared after the first, at fields 3 and 5 = 4 and 6 a task), {COMMON_METHOD}: the vertex program (own assembly) moves 8 global registers into the vertex outputs o6 to o13 and a job marker constant into o14, 126 vertices (--vertices 126, --vtx-coords 11), the vertex words read from the parameter buffer dump (recompute: own decoder of the control stream and the objects, 12 dwords a vertex)"
tiers = ["HW", "infer"]
date = "2026-11-09"
data = ["globals-vertex-eot"]
terms = []
''', '''
**What ran.** 12 jobs, all completed, each with its own marker constant in o14 (right on 119 of
the 126 vertices of every job; the other 7 vertices, numbers 60 to 66 of the draw, read as zero words
in all 12 jobs and are not counted: an object of 15 vertices whose first 7 the recompute's decoder does
not reach [infer: a decoder limit, not hardware]; vertex 67 beside them reads 0 in the 4 jobs where it
is a lane 1 to 3 value, and is skipped in the vectors).

**Constants.** [HW] In the 6 jobs of 8 vertices a task, on every decoded vertex: g16, g19 (by the mov), g26 to
g31, g40 read 0; g20 reads 1; g42 reads 0x3f800000; g41 reads 0xf and g43 0xdf000000 (the pixel
task's g41 is 1 and g43 0xff000000, E374). g19 here is a mov source as in E372. The same values
read in the 6 jobs of 4 and 6 a task, except the last task of the draw at 4 a task, which holds
2 vertices (126 = 31 * 4 + 2): g41 0x3 and g43 0x20000000 on both its vertices; at 8 a
task the last task holds 6 and every vertex of it reads g41 0xf, g43 0xdf000000.

**Per vertex.** [HW] With v the vertex's number over the objects in address order, V the vertices a
task holds, task = v div V and lane = v mod V: g25 = lane mod 4, g22 = (lane div 4) mod 2, g39 = 4 *
g22, g24 = 8 * (task mod 2), g17 = task mod 4. The model fitted to the 6 jobs of 8 a task (E-fit) was
tested on the 6 jobs of 4 and 6 a task, declared before they ran (H53-Q, against H53-F, the same
registers by a fixed grouping of 4 and 8 whatever V): 119 of 119 decoded vertices at 7 of the 12 scores,
118 of 119 at the other 5 (the vertex 67 above); H53-F gave 23 to 65 of 119 (0 of 12 scores). g18, g21
and g23 vary by task as well (g18 0x10 to 0x16 even, g21 0x1c to 0x1f, g23 0 or 0x10; g21 and g18 do not
differ by a constant) and are not fitted.

**Not shown.** What sets g18, g21 and g23; whether g41 and g43 depend on the vertices a task holds as the
two partial tasks suggest (2 and 6) or on their quads [infer]; the global registers of a vertex task
of another program or a task that reads more than the first set of inputs.
''')

rec("evidence/usse/E572-in-the-end-of-tile-task-a-store-of-a-global-register-lands-and-the-job-then-faults-the-registers-read-as-in-a-pixel-task.md", f'''
id = "E572"
claim = "In the end-of-tile task of the triangle job a stad of a global register to the scratch lands the register's value in 37 of 37 jobs and the job then faults (BIF fault 0xd0400 at 0x340042 or 0x340043; the health triangle drew exactly after every recovery: no health failure line in any of the 5 scripts), a program of 7 to 10 instructions without a store completes 5 of 5, and the registers read as in a pixel task (g16, g26-g31, g40 = 0, g20 and g41 = 1, g42 = 0x3f800000, g43 = 0xff000000; 12 of the 13 declared constants), with g19 reading 0x1a through a store; g17 reads 0, g18 0x16 at 32x16, 64x64 and 128x128, g21 0x12, 0x16, 0x15 and g23 0, 0x10, 0x10 by target size"
unit = "usse"
method = "script tables q053-eot (4 jobs, r8 as the address: 4 of 4 faulted at 0x42, kept as q053-eot-first), q053-eot (4 jobs, r1 as the address between the two emits: 4 of 4 faulted at 0x340042), q053-eotcap (4 jobs: 0 to 3 extra nops), q053-eotst (4 jobs: a mov alone, a store of r2, of g43 with and without the fence) and q053-eot2 (37 jobs, one register a job, declared after those; the address 0x5CAF0000 + 16 * job number is the marker), {COMMON_METHOD}: the end-of-tile slot (--slot eot) holds the plain program of the tool with the stores added; the scratch is read after the job as the tool prints it"
tiers = ["HW", "infer"]
date = "2026-11-09"
data = ["globals-vertex-eot"]
terms = []
''', '''
**What ran.** 53 jobs in 6 tables (q053-eot twice). The first form of the program (4 jobs) used r8 as the store address
and every job faulted at 0x42; the second (4 jobs, r1 between the emits) at 0x340042. A program of the
plain end-of-tile task with 0, 1, 2 and 3 extra nops completed in 4 of 4 jobs (and the `mov` alone of q053-eotst: 5 of 5), so the slot is not limited
to 8 instructions. q053-eotst: `mov r1` alone completed; `stad [r1,+#0], r2` (stored 0x001f8000), `stad [r1,+#0], g43`
with and without `idf`/`wdf` (stored 0xff000000 both) each stored the value and the job then faulted
(3 of 3). The recoveries (a debugfs reset and a drawing triangle) never failed.

**Values.** [HW] In q053-eot2 (37 jobs, 37 with a store and 37 faults after it, one register a job, the scratch
dword at the job's own offset holds the register): g16 0, g20 1, g26 to g31 0, g40 0, g41 1, g42 0x3f800000,
g43 0xff000000 at 64x64, the same as the pixel task (E374); g19 reads 0x1a through the store (it reads 0
through a mov in the pixel task, E372: the instruction's read decides). g17 0, g18 0x16, g21 0x16, g22 0, g23
0x10, g24 0, g25 0, g39 0 at 64x64; at 32x16 and 128x128 g21 0x12 and 0x15, g22 1 and 0, g23 0 and 0x10, g24 0
and 8, the others as at 64x64: the value of whichever tile stored last, so it differs with the target. Declared
before the run: H53-pix (the pixel task's constants) 11 of 12 held-out values and the fit g43, the miss g19; H53-vtx (the vertex
task's values) 10 of 12 held out, missing g19 and g41, and the fit g43.

**Not shown.** [infer] Why a store in the end-of-tile task faults the job after the value has landed (the
fault address 0x340042 looks like a code or table address, not the scratch); the g values per tile (only the last
tile's store survives); whether the fault is the store's or the next emit's.
''')

rec("evidence/bif/E573-with-any-one-of-the-buffers-1-to-5-and-12-to-15-left-out-of-the-client-directory-s-alias-the-renders-are-exact-with-buffer-0-the-first-job-faults.md", f'''
id = "E573"
claim = "With the read-only alias of the EDM's buffer left out of the client directory one buffer at a time, the renders are exact for each of the buffers 1, 2, 3, 4, 5, 12, 13, 14 and 15 (2 of 2 runs each, 2 renders a run) and for the pairs 6+7, 8+10, 10+11 and the five 6, 7, 8, 10, 11 together (2 of 2 each); with buffer 0 (0x30000000) left out the first job faults (2 of 2: BIF fault status 0x91000 at 0x3000b022) and the context is lost; the debugfs layout's pd_phys equals CR_BIF_DIR_LIST_BASE15 (0x28b0c000, the EDM's own directory) in 30 of 30 runs"
unit = "bif"
method = "script bif-alias, {COMMON_METHOD}: debugfs alias_skip written to the mask after a reset and a drawing health triangle, then tri -n 2 --keep-going --wait-ms 6000 under regtimeline (0 s, lead 0.3 s, registers 0x0c00-0x0c8c), the debugfs layout read 2.5 s into the run, the mask put back to 0 and the GPU reset after each case; 15 cases twice, the risky ones (buffers 0 to 5) after the others"
tiers = ["HW", "infer"]
date = "2026-11-09"
data = ["alias-skip"]
terms = ["CR_BIF_DIR_LIST_BASE1", "CR_BIF_BANK0", "ta3d_ctl"]
''', '''
**What ran.** 30 case runs (15 cases x 2): the control (mask 0), buffers 12, 13, 14 and 15, the pairs 6+7
(0xc0), 8+10 (0x500), 10+11 (0xc00), the five 6, 7, 8, 10, 11 (0xdc0), and buffers 0, 1, 2, 3, 4, 5, the last six
in a script of their own, one case at a time with a reset and a health triangle between. The
kernel's alias made at the VM's first render context leaves a buffer out when its bit is set (E457).

**Results.** [HW] 28 of 30 case runs: `tri: 2 renders ok`; the regtimeline shows the first kick of the
VM write its page directory into list 2 (BASE2, 0x0c3c; the health triangle before it took list 1; E360) in each.
Buffer 0 (the first of the heap 0x30000000: the EDM's code heap in the layout): `tri: FAILED after 0
renders`, `job faulted, context lost`, the bus interface's fault status 0x91000 at 0x3000b022 (inside buffer
0) in the 2 of 2 runs, with BASE1 as the list the first kick wrote (the VM's first kick after the reset). H76-A
(declared: the buffers 0 to 5 each fault, 12 to 15 not) was right in 20 of 30 case runs (the 18 safe ones and the 2 of buffer 0) and wrong in the 10 of buffers 1 to 5; the null (every single buffer exact) is right in 28 of 30. The declared H76-N rows of the risky cases were written by a generator error as a copy of H76-A's and are not used.
CR_BIF_BANK0 (0x0c78) took the values 0x101f, 0x1022, 0x102f, 0x2022, 0x202f over the renders (and 0, 0xf
before the faulting kick), not only 1 (E457): the low byte differs with the sampling instant [infer].

**The directory.** [HW] The debugfs layout's pd_phys read 0x28b0c000 in every run and that is the value of
CR_BIF_DIR_LIST_BASE15 (0x0c70), the EDM's own directory (E360); the client's directory is the list the kick
writes, and no existing debugfs file shows it, so "list 1 holds the client's directory" was not compared (H76-D
unscored, 28 of 28 explore).

**Not shown.** Which buffers beyond 0 and 9 the TA, the 3D and the PB load use together (a pair of the buffers
1 to 5 was not run); the larger scenes and the partial render under a mask; what buffer 0's page 0xb000 holds. The
dmesg lines the script printed after each case were not scoped to the case (the run's journal in kernel.log
is: 2 BIF fault lines).
''')

rec("evidence/dpm/E574-the-dpm-status-registers-through-36-overflowing-and-complete-scenes-status2-s-high-halves-and-register-0x0740-read-0-and-0x0748-bit-2-clears-in-5-of-36-runs.md", f'''
id = "E574"
claim = "Through 36 jobs of triangles of 3 to 900 vertices at 4096x4096 in 0x100 to 0x422 parameter-buffer pages (3 runs of 12 cells, 6 completing and 30 overflowing into partial renders, none hung), in all 36 jobs and 30 to 1066 samples each the high halves of STATUS2 (0x0710, 0x071c) and the register 0x0740 read 0; 0x0748 bit 2 cleared in 5 of the 36 jobs (300 vertices in 0x100 pages 1 of 3, 150 in 0x100 1 of 3, 450 in 0x100 1 of 3, 600 in 0x100 2 of 3, none of the other cells), against 3 of 3 for 300 in 0x100 in E443, so the clearing is not a function of the scene; 450 and 600 vertices in 0x100 pages complete where 900 hangs (E443)"
unit = "dpm"
method = "script dpm-bit2 (safe 30 jobs, risky 6), {COMMON_METHOD}: probe --tri pixel with the plain green shader, 4096x4096, --vertices N, debugfs render_pb_pages set before each job and put back at the end, regtimeline 10 s, 0.2 s lead over 0x0600-0x0750 (a line at every change), 3 runs of each of 12 cells; the script reset the GPU after every job whose text named a failure, which the tool prints for an overflowing scene (30 of 36 jobs), so each of those jobs started after a reset"
tiers = ["HW", "infer"]
date = "2026-11-09"
data = ["bit2-grid"]
terms = ["CR_DPM_TASK_STATE", "CR_DPM_3D_PAGE_COUNTS"]
''', '''
**What ran.** 36 jobs, declared in 12 cells before the first run (plan.md section 1): (vertices, pages) (3, 0x422), (300,
0x100), (900, 0x422) as fit cells (E443's), and (150, 0x100), (225, 0x100), (300, 0x180), (300, 0x200), (450, 0x200),
(600, 0x300), (600, 0x422), (450, 0x100), (600, 0x100) held out, the last two as the risky script. 6 jobs
(3 at 0x422 and 600 at 0x422) completed; 30 overflowed the buffer, which the tool reports as failed with the
partial renders done ("context kept"), and none hung or faulted: the kernel journal holds no fault line.

**Results.** [HW] The high halves of 0x0710 and 0x071c: 0 in every sample of all 36 jobs (H36-Z: 36 of 36 scores).
0x0740: 0 in every sample (36 of 36 jobs; E256 and E312 read it the same). 0x0748: the values seen are 0x6,
0x7, 0xb, 0xd, 0xe, 0xf, 0x1b, 0x1d and 0x1f; the value with bit 2 clear (0xb or 0x1b) appears in 5 jobs: (300,
0x100) run 2, (150, 0x100) run 3, (450, 0x100) run 2, (600, 0x100) runs 1 and 3. H36-DET (the same scene gives
the same outcome in all three runs, with (300, 0x100) clearing in 3 of 3 as E443 saw) was a miss: 1 of 3 here,
and the 3 runs of (900, 0x422) 0 of 3 (E443 saw 1 of 3). Both E443's 4 of 12 and these 5 of 36 are runs of the same
sparse event: it appears only at the 0x100-page cells here (5 of 15 jobs there against 0 of 21 at the other cells).
The clearing lasts for a sample or two (the timelines hold one line for it) [infer: a short pulse that the 0.2
ms sampling catches by chance].

**Not shown.** What makes the pulse (the sampling is a few microseconds apart and misses events shorter than
that); STATUS2's high half after a scene of more than five global-list pages (none run: 900 vertices hang
at 0x100, as E443 saw).
''')

# questions
def q(unit, qid, question, kind, value, phase, evidence, terms, body, name):
    rec(f"questions/{unit}/{qid}-{name}.md", f'''
id = "{qid}"
question = "{question}"
unit = "{unit}"
kind = "{kind}"
value = "{value}"
phase = {phase}
evidence = {evidence}
terms = {terms}
''', body)

q("usse", "Q182", "what sets the global registers g18, g21 and g23 in a vertex task, and what are the g registers of each tile's end-of-tile task (the stores of one tile survive)?", "hw", "medium", 11,
  '["E571", "E572"]', '[]',
  '''
Carried from Q053 (retired by E571 and E572). In a vertex task of 126 vertices g18 reads 0x10 to 0x16 (even)
and g21 0x1c to 0x1f, both changing with the task, g23 0 or 0x10 (E571); in the end-of-tile task the last tile
stores g18 0x16 and g21 0x12 to 0x16 (E572). What sets them, and the value each tile's end-of-tile task
reads, is not shown: only the last store of a job survives and a store faults the job.

To settle it: a vertex program that writes g18, g21 and g23 with a counter that fixes the task number; an
end-of-tile program that stores to an address built from g17 or g18 once a store that does not fault is found
(Q183).
''', "g18-g21-g23-in-vertex-and-eot-tasks")
q("usse", "Q183", "why does the job fault after a stad in the end-of-tile task has landed its value (BIF fault 0xd0400 at 0x340042 or 0x340043), and what store form would not?", "hw", "medium", 11,
  '["E572"]', '[]',
  '''
In 44 of 44 jobs with a store between the end-of-tile task's two emits (at 0x340042 or 0x340043) the value reached the scratch and the job
faulted after it; a program of the same length without a store completed (5 of 5). The fault address is not the
scratch. Not shown: whether the store, the missing wait on its completion, the emit that follows or the task's
end is what faults.

To settle it: stores in other positions of the program, a store only (no emit), a store with the end flag, and a
second store, in the end-of-tile slot; the kernel log's fault status and address per variant.
''', "store-in-the-end-of-tile-task-faults-the-job")

rec("questions/usse/Q053-global-bank-outside-a-fill.md", '''
id = "Q053"
question = "what do the global registers g18 to g20 and g39 to g43 hold in a triangle's pixel task, a vertex task and the end-of-tile task?"
unit = "usse"
kind = "hw"
value = "high"
phase = 11
evidence = ["E085", "E086", "E372", "E374", "E571", "E572"]
terms = []
''', '''
In a 64x32 fill g23 is the pixel's x in its 32x16 tile, g24 its y, g25 its place in the 2x2 quad, g17 the
tile quarter and g18 a per-tile number (E086); in the triangle's pixel program the constants and the varying
registers are as in the fill (E374).

Answered in 11.34 (E571, E572): in a vertex task of the triangle job g16, g19, g26-g31 and g40 read 0, g20 1,
g42 1.0, g41 0xf and g43 0xdf000000, and g17, g22, g24, g25 and g39 follow the task and the lane (g25 = lane mod 4,
g22 = lane div 4 mod 2, g39 = 4 * g22, g24 = 8 * (task mod 2), g17 = task mod 4; 4, 6 and 8 vertices a task); in the
end-of-tile task the constants are the pixel task's (g41 1, g43 0xff000000). The part that stays open, g18, g21 and
g23 in a vertex task and each tile's values in the end-of-tile task, is Q182; the store that faults is Q183.

Retired by E571 and E572.
''', ) if False else None

# ---- narrowed questions: the landed text plus a paragraph, the evidence list extended
LANDED = pathlib.Path.home() / "src/resgx545/questions"
def narrow(unit, fname, add_ev, para):
    t = (LANDED / unit / fname).read_text()
    m = re.search(r"^evidence = \[(.*)\]$", t, re.M)
    ev = [e.strip() for e in m.group(1).split(",")] + [f'"{e}"' for e in add_ev]
    t = t.replace(m.group(0), "evidence = [" + ", ".join(ev) + "]")
    (P / "questions" / unit).mkdir(parents=True, exist_ok=True)
    (P / "questions" / unit / fname).write_text(t.rstrip("\n") + "\n\n" + wrap(para))

narrow("pds", "Q023-pds-size-bits-17-16.md", ["E570"], '''
Narrowed in 11.34 (E570, 68 jobs at 13 target shapes from 32x96 to 256x128, PDS_SIZE 0 to 3, x and y runs): o1's
writes land at the pixel's own place in the region that comes one position earlier in the order of the TA data's
region headers (5551 of 6329 pairs; the raster tile index of the target's own columns gives the same rule at 64 wide
and fails at 96, 128, 160 and 256 wide), o2 and o3 one to three positions back with no setting that fixes it
(743 one, 318 two, 91 three of 2099 for o2); identical jobs show different pixel counts. Not shown: what decides
the offset of o2 and o3, the part of the size field, o4 to o7, and why the rows 8-15 of a tile at 64x128 land two
back. Status: narrowed, not answered.
''')
narrow("dpm", "Q045-reg-0740-store-and-load-tasks.md", ["E574"], '''
Narrowed in 11.34 (E574): 0x0740 read 0 in every sample of 36 more jobs (triangles of 3 to 900 vertices at 4096x4096
in 0x100 to 0x422 pages, 30 of them overflowing into partial renders). The state page's reader and the page 0x20003000
part are not run: they need a kernel switch (the first context's memory kept, a poke at the final render's kick).
''')
narrow("vdm", "Q036-dpm-status-register-count.md", ["E574"], '''
Narrowed in 11.34 (E574, 36 jobs, three runs of 12 cells of vertices and PB pages at 4096x4096): the high halves
of STATUS2 (0x0710, 0x071c) read 0 in every sample again (global lists of up to five pages; 15 to 1066 samples a
job), and 0x0748 bit 2 cleared in 5 of the 36 jobs, only at the 0x100-page cells (5 of 15 jobs; 0 of 21 elsewhere),
1 of 3 runs at (300, 0x100) where E443 saw 3 of 3 and 0 of 3 at (900, 0x422) where it saw 1 of 3: the clearing is a short
pulse the sampling catches by chance [infer], not a function of the scene. 450 and 600 vertices in 0x100 pages
complete (overflowing, 6 of 6) where 900 hangs. Status: narrowed, not answered.
''')
narrow("bif", "Q076-render-requestor-directories.md", ["E573"], '''
Narrowed in 11.34 (E573, 30 case runs): the buffers 1, 2, 3, 4, 5, 12, 13, 14 and 15 each left out of the client
directory's alias alone leave the renders exact (2 of 2 runs each), and so do the pairs 6+7, 8+10, 10+11 and the five
6, 7, 8, 10, 11 (2 of 2 each); buffer 0 (0x30000000) left out faults the first job (2 of 2, bus status 0x91000 at
0x3000b022). The debugfs layout's pd_phys is the EDM's own directory, CR_BIF_DIR_LIST_BASE15 (30 of 30), so the client's
directory in list 1 or 2 is still not compared with the client's own. Not run: pairs of the buffers 1 to 5 and 12 to
15, larger scenes and a partial render under a mask, the lists given to another context while a job runs.
''')

# ---- datasets and the rest
def ds(name, unit, desc, scripts):
    (P / "datasets").mkdir(exist_ok=True)
    (P / "datasets" / f"{unit}-{name}.toml").write_text(f'''title = "script tables {scripts}"
repo = "data"
paths = ["{unit}/{name}/"]
method = "script tables {scripts}, run by hand over ssh on the laptop with the 11.26 tool (not by the campaign runner), so this manifest was written by hand: the whole raw output of every job (gzip, dumps/<script>/), the case table, output/<script>.out, kernel.log (journalctl -k), the recompute (analysis/recompute/) and its output (analysis/recompute-<script>.txt), the declared files (analysis/declared*.tsv, predictions*.tsv, hashes.txt, plan.md) and the run scripts (scripts/). {desc} output prints rc 0 for every job, also for a failed one: a failed job is read from the failed line of its kept txt."
date = "2026-11-09"
files = 0
size = 0
sha256 = "FILLED-BY-THE-INTEGRATOR"
recipe = ""
needs = ["render", "kpoke", "reset"]
''')
ds("output-room-tiles", "usse", "The pixel readbacks of the 68 jobs, the parameter buffer and TA data dumps of 42.", "o23-tiles, o23-order, o23-size")
ds("globals-vertex-eot", "usse", "The parameter buffer and TA data dumps of the 12 vertex jobs, the scratch lines of the end-of-tile jobs.", "q053-vtx, q053-vtx2, q053-eot (two forms), q053-eotcap, q053-eotst, q053-eot2")
ds("alias-skip", "bif", "The regtimeline of the BIF registers 0x0c00-0x0c8c and the debugfs layout of every case.", "bif-alias-safe, bif-alias-risky")
ds("bit2-grid", "dpm", "The regtimeline of 0x0600-0x0750 of every job.", "dpm-bit2-safe, dpm-bit2-risky")
(P / "removed.txt").write_text("questions/usse/Q053-global-bank-outside-a-fill.md\t# retired: answered for the vertex task and the end-of-tile task by E571 and E572; the remainder (g18, g21, g23 in a vertex task, each tile's g in the end-of-tile task) is Q182, the store that faults the job Q183 (tools/records/questions.py RETIRED gets \"Q053\": \"answered by E571, E572; remainder Q182, Q183\")\n")
