# Phase 11.34 laptop batch: PDS/USSE edge cases, DPM state, BIF directories

Scratch, gitignored, written 2026-11-09 03:2x before any run. Nothing staged or committed; nothing
written under `~/src/resgx545` (landed, read-only), `tools/rewrite/`, the worktree's index, or any
fork. Questions in the order asked: Q023, Q053, Q066, Q045 and Q036, Q076. Direction: hardware facts
a simulator needs. No kernel change; tool `~/sgxfive-test-1126` (sha256 751f7223...600f82e),
unchanged, no new option, so no `~/sgxfive-test-1134`.

## 0. What is run, what is skipped (and why)

- Q023 (script o23-tiles, 26 jobs): the landed data (E081, E139, E406: 1797 jobs, all at 64x64)
  hold each pixel's value and a tag naming the register and the source x (or y) of the write. Read
  offline (analysis/o23_pair.py, run before this plan on the 8 jobs of usse-output-room-size)
  the x run and the y run of one table give, for each destination pixel, its source tile and
  in-tile place: o1 (tag 2) lands in the tile one back, o2 (tag 3) two back, in tile index (raster
  order, 2 tiles a row at 64 wide) with the in-tile place unchanged. That reading is H23-T, fitted
  to those 8 jobs, so the 64x64 jobs here are `fit`. No other target size was ever run: the jobs at
  128x128 (4 tile columns), 96x64 (3), 64x128, 160x48 (5), 32x96 (1) and 256x128 (8) are `heldout`
  and separate "tile index in raster order of the target's own tile columns" from "two columns".
  Fixes the E406 four-output setup at 128x128 as exploration.
- Q053 (q053-vtx 6 jobs safe, q053-eot 4 jobs risky): the vertex program reads g16-g31, g39-g43 into
  the vertex outputs (o6 to o13, o14 a distinct marker a job), 126 vertices, read from the
  parameter buffer. The end-of-tile program stores them to the scratch (stad) with a marker, read as
  the scratch dwords changed. EOT g-registers may hang the job: last, one at a time.
- Q066: NOT RUN. E410 flipped every bit of rd:76, rd:77 and rd:69 already; the rest of the object
  lives in render memory the tool builds, and no existing debugfs poke reaches it (rtds/ctx/pb/kw
  spaces do not hold the object's vertex words). Needs a kernel poke into the bg object, or a tool
  option; both are out of scope here.
- Q045 second half (0x20003000, third context holding the VM; state page poked between the partial
  and the final render): NOT RUN. Needs a kernel switch that does not free the closed context's
  memory, or a poke at the final render's internal kick. 0x0740: E456/E464 saw only 0; the timelines
  of dpm-bit2 sample it again (one more look, not a new method).
- Q036 (script dpm-bit2, 36 jobs): what makes 0x0748 bit 2 clear, and STATUS2's high halves, over a
  grid of scene sizes and PB pages at 4096x4096 (three runs each, regtimeline 0x0600-0x0750).
- Q076 (script bif-alias, 30 jobs): `alias_skip` for the ids E457 did not run (0-5, 12-15), pairs and
  five of the ids 6, 7, 8, 10, 11, each twice; CR_BIF_DIR_LIST_BASE1 against the debugfs `layout`
  pd_phys during the render. Fault addresses and lists from the kernel log.
- DPM and BIF fixed-function models wait for phase 12; the sim part is only what Q023 and Q053 add
  to the USSE/PDS side.

## 1. Declared before any run

`declared.tsv` (case, script, set, size) and `predictions-declared.tsv` (case, quantity, value,
model) are written by `gen/gen_p1134.py`; hashes in section 6. Sets: fit = a case whose outcome an
earlier record or the offline reading used; heldout = never used to adjust a model; control =
repeats; explore = no outcome can fail it (`?`), reported as exploration.

Hypotheses:
- H23-T: in a render, every destination pixel that carries tag k+1 (the output register o_k, k = 1,
  2, 3) was written by the tile whose raster index is the destination tile's plus k, from the same
  in-tile place; tile index = ty * ceil(W/32) + tx, tiles 32x16. H23-0 (the plain reading: o_k lands
  on the pixel's own place) is refuted by E081 and is kept as the null: it predicts "not all".
  A job's quantity `disp-tagK-tile-back` is `all` if every destination pixel with the tag, read
  from the x job and the y job of the pair, fits H23-T (and at least one pixel carries it).
- H53-same: in the vertex task (and the end-of-tile task) g16, g19, g26-g31, g40 read 0, g20 and
  g41 1, g42 0x3f800000, g43 0xff000000, the pixel task's values (E374); H53-zero: all read 0.
  The varying registers (g17, g18, g21-g25, g39) are `?` (exploration).
- H36-DET: the same scene gives the same 0x0748 bit 2 outcome in all three runs; (300, 0x100)
  clears it in 3 of 3 as E443 saw (fit), (3, 0x422) never; the other cells are `?`. H36-Z: STATUS2's
  high halves (0x0710, 0x071c bits 31:16) read 0 in every sample (E358, E443).
- H76-A: the client directory needs only what E457 found; ids 12-15 alone, pairs and the five
  are exact; ids 0-5 alone each fault (the EDM's code and data heap, the first list). H76-N: the
  null, every single id is exact. H76-D: CR_DIR_LIST_BASE1 equals the layout's pd_phys (the page
  directory of the client's newest render VM) at the render's end.

## 2. Outcome rules, recompute, faults to avoid

A job completed (rc 0, `diff`/`tri`/`job` line) or failed (rc != 0, failed, faulted, hung); a failed
job is followed by a debugfs reset and the health triangle (64x64 exact, one retry after 5 s, three
failed recoveries abort the script, journalctl -k kept per script). Raw outputs gzipped with raw
sha256; the recompute (`recompute/recompute_p1134.py DIR`) reads only the kept files and the case
tables, with its own decoders (pixel dump rows, parameter buffer, scratch lines, timeline lines).
Faults of r1126, r1127, r1131 avoided: every case has a distinct marker so a stale or dropped
write cannot match; a fit case is never scored as a test; counts in records are taken from the data
by the recompute; "every" and "no" claims state the number of jobs; [infer] is tagged.
Safety: no clock-gate register is written (lib1134.sh refuses all but the two host enables, which
this batch does not use); no trc_hazard; no reboot; reset through debugfs only.

## 6. Hashes (written 2026-11-09 03:2x, before the first run)

declared.tsv sha256 eaf1e85e7137714341771dc8d46795a9dcfe1acbdf7f42622e0ec18a880c321e;
predictions-declared.tsv sha256 7212f17bdee46d6b163f727549fdb21de2d81f765d6abda9b0aff643c06d93be;
tables (hashes.txt): o23-tiles 7af70b95..., q053-vtx 7f339299..., q053-eot 5dd642c3..., bif-alias
739324b6..., dpm-bit2 c6cbdc9a....

## 7. Follow-up 1 (o23-order, 26 jobs), declared after the first o23-tiles run and before it runs

The first run (26 jobs; the numbers are in the records) gave H23-T right for 64-wide targets (497 of 497
pairs of tag 2 at 64x64 size 3, 452 of 452 at size 0) and wrong elsewhere: at 256x128 the tiles of
column 4 land in column 7 of the row above (a 4-column block), at 64x128 the same tile's rows 0-7 land
one tile back and rows 8-15 two tiles back. So the index is not the raster index of the target.
H23-O (built from the tag-2 data of that run, so those jobs are its fit, the tags 3 and 4 are not):
the lands-in order is the order of the region headers of the TA data (the first written page, entries
with a stream, in index order): o_k of a pixel in the region at position p lands in the region at
p - k, same in-tile place. The jobs are the 13 configs again, x and y, with --dump-render and new
markers; `declared-followup1.tsv`, `predictions-followup1.tsv`, `gen/table-o23-order.txt`: hashes in
hashes.txt (written before the run). The recompute reads the region order from the kept
`.tadata.bin.gz`/`.param.bin.gz`.

## 8. Follow-up 2 (o23-size, 16 jobs), declared after follow-up 1 (o23-order) and before it runs

o23-order (26 jobs) read the region order: o1 (tag 2) lands in the previous region with a stream (header
index order) in 85 to 100 percent of its pixels in every config (446 of 446 at 64x64 size 0, 481 of 482 at
size 3); the dest region was one without a stream (the remainder) or two back. H23-O as declared ("all") is
therefore scored as a miss where it is not exact. The same data show o2 and o3 two regions back at sizes 0 to 2
(o2: 101 of 290, 86 of 219, 77 of 175 at 128x128) and one back at size 3 (165 of 298, 112 of 124 for o3): H23-S,
built from that data (fit = the 128x128 and 64-wide jobs), declared for new shapes: 96x96 at sizes 0, 1, 2, 3,
192x96 at 0 and 3, 64x96 at 2 and 3: the most frequent offset of the pairs found in the region list is 1 for o1 in
all, for o2 2 at sizes 0-2 and 1 at size 3, for o3 2 at sizes 0, 1, 1 at size 3, `?` at size 2. Hashes in hashes.txt.

## 9. EOT program revised (declared before its second run)

The first q053-eot run (4 jobs, first form: stores through r8) faulted in 4 of 4 jobs (BIF fault 0xd0400 at
0x42, job lost, health triangle exact after each reset, no failed recovery): the end-of-tile task has the
registers r0-r3 only [infer from the fault]. Kept as dumps/q053-eot-first. Second form: the stores sit between
the two emits, r1 the address (0x5CAF0000 + 256 * job number: the marker is the scratch offset), source the
global register directly. Predictions unchanged (H53-same where the pixel task gave a constant, `?` else).

## 10. Follow-up 3 (q053-eot2, 37 jobs), declared after the eot, eotcap and eotst runs and before it runs

eot (2 forms, 8 jobs): faulted in 8 of 8 (BIF fault 0xd0400 at 0x42 and 0x340042); eotcap (extra nops 0 to 3, 4
jobs): completed 4 of 4, so the EOT slot is not limited to 8 instructions; eotst (4 jobs): a lone `mov r1` completes,
a `stad` of r2, of g43 with the fence and of g43 without it each stores its value in the scratch (0x001f8000, 0xff000000,
0xff000000) and then the job faults (3 of 3, at 0x340042 or 0x340043). So a store lands and the job is lost
afterwards: one register a job. H53-pix: the end-of-tile task reads the pixel task's constants (g16, g19, g26-g31, g40 0, g20
and g41 1, g42 0x3f800000, g43 0xff000000); H53-vtx: the vertex task's (g41 0xf, g43 0xdf000000). g43 at 64x64 is the fit (eotst e2 saw it).
The varying registers (g17, g18, g21-g25, g39) at 32x16, 64x64 and 128x128: `?` (the value of the last tile).
`declared-followup3.tsv`, `predictions-followup3.tsv`, `gen/table-q053-eot2.txt` hashes in hashes.txt.

## 11. Follow-up 4 (q053-vtx2, 6 jobs), declared after q053-vtx (6 jobs) and before it runs

q053-vtx (V = 8 vertices a task, 126 vertices, 6 jobs, 119 distinct clip positions, every vertex's marker correct): the vertex
task's g16, g19, g26-g31, g40 read 0, g20 1, g41 0xf, g42 0x3f800000, g43 0xdf000000 on every vertex, and with v the vertex's
sequence number over the objects (address order) g25 = v mod 4, g22 = (v mod 8) div 4, g39 = 4 * g22, g24 = 8 * ((v div 8) mod 2), g17 =
(v div 8) mod 4 (g18, g21, g23 vary by task; not fitted). So the fit is V = 8 and cannot tell a task's lane (v mod V) from a fixed
grouping of 4 and 8. H53-Q (lane-based: g25 = lane mod 4, g22 = (lane div 4) mod 2, g24 = 8 * (task mod 2), g17 = task mod 4, task = v div V,
lane = v mod V) against H53-F (fixed: g25 = v mod 4, g22 = (v div 4) mod 2, g24 = 8 * ((v div 8) mod 2), g17 = (v div 8) mod 4); g39 = 4 * g22 in
both. Jobs: VDM_TASK0 field 3 (V = 4) and 5 (V = 6), groups A (g16-g23), B (g24-g31), C (g39-g43, g17-g19), new markers. Hashes in hashes.txt.

## 12. What ran (written at the end; sections 1 to 11 are as declared and are not edited)

Laptop clock, 2026-11-09, one run each, the scripts in the order: o23-tiles 03:20 (26 jobs), o23-order 03:23 (26),
o23-size 03:26 (16), q053-vtx 03:27 (6), q053-eot first form 03:28 (4), second form 03:30 (4), q053-eotcap 03:31 (4), q053-eotst
03:32 (4), q053-eot2 03:33 to 03:37 (37), q053-vtx2 03:38 (6), bif-alias safe 03:39 (18 case runs), bif-alias risky 03:43 (12),
dpm-bit2 safe 03:45 (30), risky 03:54 (6): 199 jobs (counts from cases.tsv of each script). Tool: ~/sgxfive-test-1126 (sha256
751f7223c8c731a08d75cfc3920a5d1050488ca3bdc426be45b7c431e600f82e) in every job; no new tool option, so no sgxfive-test-1134.
Health (job, fill, a 64x64 triangle exact, debug switches at their defaults, journal) over the cable before the first script and
at the end (03:56); every script ran the health triangle before and after and after each failed job; no script printed a health
failure line, none retried, none aborted. 4 of the 14 scripts were risky by design (the EOT stores, the alias_skip buffers 0 to 5, the
DPM cells beside the 900-vertex hang): all ran, one at a time as a script, with a debugfs reset and a drawing triangle after each fault.

Disclosures. (1) Four follow-ups (sections 7 to 11) were declared after reading earlier results and before their runs; each has its own
hashed declared and predictions file; their models are built from the earlier jobs, which are their fit. (2) The offline reading of the
64x64 jobs of E081, E139 and E406 (H23-T) preceded the plan and is the fit of the o23-tiles 64x64 jobs. (3) The first EOT program form and the
second faulted in 8 of 8 jobs (section 9); q053-eotst and q053-eot2 were written after seeing that a store lands before the fault: the
q053-eot2 predictions are for registers (a held-out set) and the constants are scored against the pixel task's values. (4) The declared H76-N
rows of the risky bif-alias cases are a generator error (a copy of H76-A's): the intended null (every buffer alone exact) is scored by hand in
E573; recompute prints the declared rows. (5) The script bif-alias printed `dmesg | grep` lines after each case that were not scoped to the case
(they repeat older faults): the journal of the script (kernel.log) is. (6) dpm-bit2 reset the GPU after every job whose text named a failure,
which the tool prints for an overflowing scene (30 of 36 jobs), so those jobs ran after a reset; E443 did not reset. (7) The recompute's vertex decoder
reads 119 of the 126 vertices of the objects (the 7 vertices 60 to 66 read as zero words in all 12 vertex jobs); vertex 67 beside them is skipped
in the vectors. (8) Q066 and the rest of Q045 (the state page's reader, page 0x20003000 with the first context's memory kept) were not run: they need
a kernel poke into the background object or a switch that keeps the closed context's memory (no kernel change was allowed). (9) The
`Q076` comparison of the client directory with CR_BIF_DIR_LIST_BASE1 was not possible: the debugfs layout holds the EDM's own directory (BASE15).
(10) o23 counts are pairs of an x job and a y job that are separate runs; the jobs of one config are not repeated except 128x128 size 3
(twice: 705 and 463 pairs of tag 2).
