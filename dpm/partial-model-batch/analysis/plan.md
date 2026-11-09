# Phase 11.37 laptop batch (p1139): the DPM and partial renders, for sub-phase 12.7

Scratch, gitignored, written 2026-11-09 10:4x before any run and without laptop access. Nothing
staged or committed, nothing written under `~/src/resgx545`, `~/src/resgx545-fw`, `tools/rewrite/`,
p1137, p1138, p12 or any fork; only `p1139/`. Read: `p12/plan.md` (12.7), Q038, Q107, Q045, Q036,
Q103, Q191, Q192 (the newest DPM questions; Q081, Q084, Q088 only as context), E201, E204, E309 to
E312, E358, E438, E442, E443, E456, E461 to E468, E489, E462, E574, E591, `doc/specs/3d.md`
sections 4.4 and 6, the triage (ranks 4 and 5) and the capture-tool audit (D2, D5, D7, D9, D12).
Tool: the newest source, `overlay/11.35` (`sgxfive-test.c` sha256 f5cdccb1...), built as
`~/sgxfive-test-1135`. Kernel: as installed, no change asked. Record ids from E625 and question
ids from Q210 are reserved for this batch's records; none is written here.

## 0. What is here

| file | what |
|------|------|
| `plan.md` | this plan |
| `gen/gen_p1139.py` | writes `tables/`, `declared.tsv`, `predictions-declared.tsv`, `hashes.txt` |
| `tables/{free,trig,state,depth,wide,owner}.txt` | 204 jobs, one line each (section 4) |
| `lib1139.sh`, `run_table.sh`, `run-all-1139.sh` | shared library, the one runner, the order |
| `recompute/recompute_p1139.py` | scores the predictions from the kept raw files (own decoders) |
| `tool-tests/test_cli_p1139.py`, `tool-changes/*.diff`, `tool-new/` | section 4: tool changes |
| `analysis/off_*.py`, `.out` | two offline readings of landed dumps (sections 1 and 2) |
| `mock/` | the mock harness the scripts were run through here (section 4) |
| `stage1139.sh`, `deploy1139.sh` | copy to the laptop, build the changed tool (both unrun) |

Totals: Part A 191 jobs on the unmodified tool (free 26, trig 29, state 26, depth 74, wide 28,
owner 8), Part B 13 jobs that need the changed tool (owner), about 2 to 3 hours with resets and
health triangles. 15 jobs are risky (trig 4, wide 7, owner 4); they run last, one script at a
time. The 4096x4096 depth jobs are safe but long (64 MiB buffers, 80 MB of dumps each).

## 1. What a DPM and partial-render model must predict, and what is known

The model's inputs are the job's memory: the PB descriptor (page count P, the four thresholds, the
page table), the TA stream (what the vertex and object programs emit, per macrotile and region),
the render details (CR_ISP_ZLSCTL and the bases, flag bits) and the target size (macrotile grid).
Its outputs, with the tier of what we have: [HW] measured and recorded, [infer] read from
firmware or fitted, [unknown].

1. Pages allocated. [HW] The free list is a chain in the page table, entry i at base + 4 i
   (previous << 16 | next), the walk covers all P pages after every job and STATUS1/2 follow the
   walk (E309); the first job on a fresh table takes pages 1, 2, ... (64x64: 1 to 2, 256x256: 1 to
   5); a second render takes the head the first left (E309: pages 3, 4); a whole-buffer job uses 2,
   3, 5, 0x13 and 0x11f pages at 64x64, 128x128, 256x256, 1024x768 and 4096x4096 (E310, E358).
   [infer] which object or region takes which page, how many macrotile pages a triangle needs.
   [unknown] the page order inside a job; the order a final render frees its pages in.
2. When an overflow starts a partial render. [HW] The ZLS threshold register reads P - 0x22 at
   every size (E201); the first abort comes at page status = that threshold (0xe at 0x30 pages,
   1 at 0x23, 0xde at 4096x4096 0x100: E312); TA3DCtl dword 35 reads status - 2 in all seven rows
   of E310 ((0xc, 5) 0x30, (4, 0) 0x28, (0, 0) 0x24, (0xffff, 0x1f) 0x23 at 1024x768; (0xdc, 5)
   0x100, (0x3c, 6) 0x40, (0x1f, 6) 0x23 at 4096x4096); the partial-render counts 1, 1, 10 at
   1024x768 0x30, 4096x4096 0x100 and 0x23 (E204, E312, 0x0658 stretches of 1 to 28 ms).
   [infer] the threshold is raised by 0x20 after the first partial render (firmware reading,
   3d.md 6.4; E312's later aborts at status 0x21; E310's 0x3e at 4096x4096 0x40). [unknown] the
   count at other P, where overflow stops (the pages U a scene needs), the 0x28 puzzle of P3.
3. What a partial render stores and loads. [HW] It renders and frees every macrotile's pages, in
   macrotile order, and stores the TA's lists in the RT data's state page: 17 lists of two dwords
   (count << 16 | head, tail), the global list last (E310, E312); the final render paints the
   background over regions the partial renders drew (E311) unless the background object reloads
   the target (E442: 4422528 of 4422528 pixels); the ZLS store of an overflowed job is the whole
   buffer at E465's address rule with a prefix of zero dwords (15104 at 1024x768 and 80640 or 48000
   at 4096x4096, a contiguous prefix of the buffer in the E489 dumps: `analysis/off_zero_slots.py`)
   and, at some P, the sign bit set (E461, E468). Offline, with this batch's decoders over the
   same E489 dumps: the overflowed 4096x4096 ramp stores (G = 1 and 0, P = 0x2000) have 0 signed of
   246016 and of 148096 stored non-zero dwords (`analysis/off_sign4096.out`), so overflow alone
   does not set the sign. [infer] the final render loads the partial renders' depth (E461's
   load-only job storing the negated fill; E467: a load clears the sign). [unknown] whether it
   does, what sets the sign, why 0x30 pages negate in E468 and not in E461, the tile store order,
   the depth test across partial renders, the colour reload with a depth buffer.
4. State and owner registers. [HW] `CR_DPM_STATE_CONTEXT_ID` reads 2 through a partial render,
   0x0658 reads 1 in its stretches, 0x0730/0x0738/0x0748 as E312, the owner words after a render
   with bit 3 (E462), 0x0740 and STATUS2's high halves 0 in every sample (E456, E438, E443, E574),
   a kept owner's pages 1 to 3 holding 0x00200047, 0x04000417 and 0x00020001, 2 after the next
   context's render (E591). [infer] those words are page lists and thresholds of the owner
   (`0x00020001, 2` is a list of 2 pages, head 1, tail 2: the 64x64 job's pages). [unknown] what
   stores them and when, what a partial owner leaves (Q192), whether a load task reads the state
   page (Q045), what makes 0x0748 bit 2 clear (a 29 us pulse in 5 of 36 jobs, E574).
5. End of frame. [HW] The free list after the job (E309), TA3DCtl dwords 35, 36, 39, 40 (E310,
   E438: dword 36 reads 0 to 3), the page counts (0x0660, 0x072c), `CR_DPM_STATE_CONTEXT_ID` back
   to 0 at the final render of a one-partial job and still 2 after the ten of 0x23 (E312).
   [unknown] the order of the final render's frees, dword 36's rule.

## 2. Open points: hypotheses, experiments, outcomes

All jobs reset the GPU first (debugfs, except where a case says `noreset`), set `render_pb_pages`,
and keep the tool's whole output, the PB and TA data dumps after every render (`--dump-each`), the
TA/3D control block (`--words`), the DPM registers 0x0700 to 0x074c after each render (`--regs`)
and, for jobs that count partial renders, a `regtimeline` of 0x0654-0x0660, 0x0700-0x0710,
0x0720-0x0724 and 0x0748 (read-only; the stretches of 0x0658 are the partial renders). Fill
markers are per job (`0xdeadNNNN`), so a stale buffer or the dump of another job cannot match.

### P1. Page order and addresses (script `free`, 26 jobs; Q045, Q036)

H-walk: the walk covers all P pages after every render of every job. H-first: render 1 on a fresh
table takes pages 1..U ascending. H-head: render k + 1 takes the head of the list render k left,
in list order. H-free-O: at a partial render the 3D appends the pages of the macrotile lists in
macrotile order, each list head to tail, the global list's page last (E312's sampled tail
sequence 2, 5, 0xd, 3, 0xb, 0xe, 4, 0xc, 8 fits it).
Cases: `tri -n 3` on a whole buffer at 64x64 and 256x256 (fit: E309), 128x128, 192x128, 512x384
and 1024x768 (held out), the first and last repeated; `tri -n 2` at 1024x768 for P = 0x23, 0x24,
0x26, 0x28, 0x2a, 0x2c, 0x30, 0x34, 0x36, 0x38 (fit at 0x23, 0x24, 0x28, 0x30) and at 4096x4096
for P = 0x23, 0x40, 0x60, 0x80, 0xc0, 0x100; 0x30 repeated after a reset and without one.
Kept: `tri.N.param.bin` (page table at 0x423000, the pages) and `tri.N.tadata.bin` after each
render. The recompute walks the table, finds the pages whose content changed between consecutive
dumps and tests H-head (the changed pages are the head prefix of the previous walk) and H-free-O
(the state page's list heads appear in the walk in macrotile order).
Outcomes. H-head true everywhere: the pool is a FIFO and `dpm.rs` needs only the free order.
False with a valid walk: the pool is not FIFO, the walks are the data. H-free-O false: the freed
order is only a table of observed orders for the recorded cases (phase 12 vectors) and the other
cases refuse. `job1_pages` (non-zero pages after render 1) assumes zeroed pages before the job;
the walk tests do not.

### P2. When the overflow starts, and how many partial renders (script `trig`, 29 jobs; Q103)

H-trig: the first abort comes when pages in use (the page status) reach thr0 = P - 0x22, and the
job overflows (-ENOSPC) iff thr0 < U, U the pages the scene needs. R1: after the first partial
render the threshold is thr0 + 0x20 and the count is 1 + floor((U - thr0) / (thr0 + 0x1f)); the
last abort's status is thr0 (count 1) or thr0 + 0x20, and dword 35 = that - 2. R1 fits all seven
rows of E310 and E204's three counts when U(4096x4096) = 289 (E310's whole-buffer count is 287;
the 2 is fitted to ten partial renders at 0x23), so 4096x4096 0x23 and 0x100 are `fit`; U(1024x768)
= 21 is the same +2 on 0x13, an assumption. R3: the threshold is never raised (but 1 to 0x21): it
is refuted at 4096x4096 by E310's (0x3c) row at 0x40, and kept as the null at 1024x768 where the
lists of E464 at 0x28 look like several partial renders (P3).
Predictions (R1 / R3 where they differ): 4096x4096 count 10 at 0x23, 5 / 9 at 0x40, 3 / 4 at
0x60, 2 / 3 at 0x80, 1 at 0xc0 and 0x100; 1024x768 count 1 / 20 at 0x24, 1 / 4 at 0x28, 1 / 2 at
0x2c, 1 at 0x23 and 0x30; overflow boundary at P = 0x142 (0x143 completes) and at 1024x768 at 0x36
(0x37 completes), cases 0x13e to 0x144 and 0x33 to 0x38 (the boundary gives U to the page).
Poke: `--kpoke-render 1:pb:11=V` (descriptor dword 11, the ZLS threshold) at P = 0x422, 4096x4096,
V = 0x20, 0x40, 0x80, 0x100 predicted 5, 3, 2, 1 partial renders (H-poke), against H-poke-null (the
poke is not honoured: the job completes); V = 0x400 (the default) is the control. Risky: last.
Outcomes. R1 on all held-out counts: the trigger rule, the raise and U(scene) go to `dpm.rs`; a
miss by one at the boundary says what the global page counts (the +2); counts as R3 at 1024x768
mean the raise needs a condition (the first partial's page count); a poke that works decouples P
from the threshold (the closed driver's 0x400 at 0x422, E327) and gives every later question a
knob.

### P3. The state page across a partial render (script `state`, 26 jobs; Q045, Q191)

The records disagree. E310 (0x30 pages; 4096x4096 0x100): the sum of the lists' counts is the pages
taken at the abort less one (13, 221). E464 (0x28, 1024x768): 9 lists, 18 non-zero dwords, pages
9 to 0x14 and at least 12 pages, where the abort at status 6 (dword 35 = 4) holds at most 5.
H-state-abort: the page holds the lists at the last abort (sum thr_last - 1). H-state-end: it
holds the lists of the TA's end, the pages taken after the last partial render (sum about
U - thr_last). H-state-last (many partial renders): only the last partial's lists remain, against
accumulated lists. H-global: entry 16 is one page, page 1. Structure H-state: lists are disjoint
and only macrotiles the triangle covers (the recompute gets them from the vertices on the 4 x 4
grid E311 and E310 use) have one.
Cases: 1024x768 at 0x2a, 0x2c, 0x34, 0x36; the default triangle moved by (0,0), (256,0), (0,192),
(-128,96), (384,288) at 0x30 and 0x28 (fit: the first of each); 4096x4096 at 0x40 and 0x23
(many partial renders); two triangles in one scene (`--geometry 1 --move 2:+-96,0`) at 0x38, 0x3c,
0x40, 0x48; the 0x30 job repeated after a reset and without one (the pages differ, the counts per
list do not: H-repeat).
Outcomes. H-state-abort true at all P: the state page is the abort's, E464's lists were a later
partial's (and P2's count at 0x28 is above 1). H-state-end true: the store is made at the TA's end
and `dpm.rs` stores twice. Neither: the E464 job differs in a variable the tools do not show (a
second job of the context; the E464 tool run had `-n 2` in two of its cases) and the repeats say
which. The macrotile set and counts per scene become `dpm-state` vectors.

### P4. The final render's depth after partial renders (script `depth`, Q038)

H-load-yes: the final render loads the stored depth of the macrotiles the partial renders drew.
Test: `--depth-fill index` in a load buffer (dword i holds i) and a separate store buffer (marker
fill), control 0x0017510e (bits 1 and 14: depth load, E467) against 0x0017110c (no load), scene
z = 0.5 or the full-screen ramp, P = 0x422 (E467's identity: fit), 0x28 and 0x30. A stored dword
equal to its index (sign ignored) at tile rows 12 and below is a loaded one; H-load-yes predicts
yes with the load control and no without, at both overflow P. Case names `dl-*` (12 jobs).
H-dload-yes / H-dload-no (the depth test across partial renders, overlapping triangles whose order
the depth decides): two default triangles tilted by `--tri-z 0.25,0.75,0.25`, A in a geometry kick,
B in the final render, moved by -96 (B farther in the overlap) or +96 pixels (B nearer: the
tilt makes the order follow the move), depth test less (`blk:1`), P = 0x38, 0x3c, 0x40, 0x48 (the
overflow comes while B is tiled: U(A) 21 < thr0 + 1) and 0x422 (control), the final render's
control with or without the load bits (`--depth-ctl-next`). H-min: the stored |depth| at overlap
pixels is min(zA, zB): B for the nearer move, A with the whole buffer. H-dload-yes predicts A for
B farther at every overflow P, H-dload-no `mixed` (B where A was drawn by a partial render). Cases
`ov-*` (18 jobs). The recompute classifies every overlap pixel from its rule address.
Outcomes. Yes: the model keeps depth per macrotile across partial renders as stored (sign: P5) and
the final render's test starts from it; no: macrotiles tiled before the last partial render restart
their depth, a visible error the simulator must reproduce. The colour reload with a depth buffer is
not reachable with this tool (T1, section 4): left open and said so.

### P5. The sign bit and the E461 / E468 disagreement (script `depth`; Q107, Q038)

Facts: E461 (z = 0.5, G = 1) positive at 0x30, signed at 0x28, 0x24, 0x23 and at 4096x4096 0x40 and
0x23, positive at 0x100; E468 (ramp, G = 33) signed at 0x30, 0x28, 0x23; the E489 4096x4096 ramp
jobs positive. Hypotheses: H-sign-P (nearest neighbour: the z = 0.5 scene is signed iff P < 0x2c;
the ramp whenever it overflows), H-sign-N (signed iff at least two partial renders: tied to P2 -
under R1 the 0x28 job has one, so H-sign-N needs R3 there), H-sign-S (the scene), H-sign-G (the
pitch: G = 1 against 33). Cases: the z = 0.5 scene at P = 0x23, 0x24, 0x26, 0x28, 0x2a, 0x2c, 0x30,
0x34, 0x38 at G = 1 and at 0x23, 0x28, 0x30 at G = 33; the ramp at G = 33 at 0x23, 0x28, 0x30, 0x60,
0x100 and at G = 1 at 0x28, 0x30; every case twice, under `regtimeline` so that the number of
partial renders is measured beside the sign; the 0x30 pair of scenes at both G separates scene
from pitch. 38 jobs, 19 cells.
Output: one table (case, partials, zero dwords, window, signed / non-zero). Outcomes. A rule in
(partials, P) that fits the 19 cells: that rule is what the simulator applies when storing; a
mixed table (same partials, different sign): scene or pitch matters, the next batch bisects it;
a sign that follows nothing measured and repeats: it is recorded as a table lookup per cell
(refusing elsewhere); a sign that does not repeat: P11.

### P6. The zero region and the 4096x4096 window (script `depth`, 6 jobs and all `dp-*`)

H-zero-M1: the zero dwords of an overflowed store are the first macrotile's tiles, at pitch G + 1
(offline fit: 1024x768 G = 1 has a zero prefix of 29.5 slots, 2 * 11 + 7 slots for 8 x 12 tiles,
a half tile each side; 4096x4096 G = 1 157.5 slots for 32 x 64 tiles, G = 0 93.75 against 95, so
close, not exact). It predicts 15104 zero dwords at every overflowing P of the G = 1 jobs (fit at
0x28, 0x23, E461), 184320 at G = 33 for the ramp (E468: 336 whole tiles; fit), and at 4096x4096
G = 127 (no two tiles at one address, control 0x001713fc, 64 MiB buffer = the whole target) 0.9
to 1.1 million zero dwords. H-zero-row (E468's reading, tile rows 0 to 11 are the first row of
macrotiles): 4.0 to 4.2 million at G = 127. Cases `w4096-*` (G = 1 and 0: fit E465; G = 127, two
runs each; P = 0x2000 as E465) and the zero counts of all `dp-*` jobs.
Outcomes. One of the two bands: the zero region is a macrotile or a macrotile row, fitted to the
macrotile rule (Q100), and the store order follows (first macrotile last, E468); neither: the
tile order of the store is open (the 512 dwords E468 left) and the G = 127 dump (no aliasing) is
the data for it. The window sizes (326656, 196096, 16777216) are E465's rule and must match.

### P7. Free-list and PB counters (scripts `trig`, `wide`; Q036)

Per job: TA3DCtl dwords 35, 36, 39, 40 after each render, 0x0700 to 0x0750 after each render and
the timeline: STATUS1 head and tail through the job, 0x0660 and 0x072c (page counts), 0x0720 (abort
macrotile). `wd-glist-*`: 900 to 1500 vertices (step 150) at 4096x4096 in 0x422 pages: global list
4 and 5 pages and dword 36 = 2 and 3 at 900 and 1500 (fit, E438), 1050, 1200, 1350 held out (`?`:
the rule of dword 36 is unknown; a monotone 4 to 5 or a step is the answer); STATUS2's high halves
0 in every line (H36-Z; E574: 36 of 36). A global list above five pages is not reachable here
(1500 vertices is the rig's limit): said, not run. `wd-bit2-*`: 16 jobs, 300 and 450 vertices at
0x100 pages, eight runs each, alternating a reset before the job and none (E574's second variable),
range 0x0600-0x0750: the fraction of runs in which 0x0748 reads bit 2 clear (E574: 5 of 36, 1 of 3
and 3 of 3 for the same cell). Outcome: a rate by (cell, reset) with the run count; not a vector,
section 5.

### P8. Owner and context behaviour (script `owner`; Q191, Q192, Q045)

Part A (8 jobs, unmodified tool, `render_keep`): the 64x64 job of E591 (fit: pages 1, 2, 3 words
0x00200047, 0x04000417, 0x00020001, 2) and the first context varied: two and three renders, 64x32,
32x32 (H191-L: the state words are the list of the owner's pages, (U << 16) | 1 and U), and the PB
size P = 0x300, 0x200, 0x100 (H191-P: the OTPM word's high half is P - 0x22; the low half `?`).
Part B (13 jobs, changed tool): `ow-part-*`: the first context renders 1024x768 on 0x28 pages,
flags 0x4 or 0xc, keep on or off, then the second context (T2) against `ow-part-solo`: H192-R, the
second context's store replaces the kept partial owner's state page with flag bit 3 and leaves it
with bit 2 alone (E591); without keep the closes are risky. `ow-kcopy-*` (T4): the kept pages copied
after the second render and before any close, against the pages after the tool exits: store made by
the job's end, or at close. `ow-fill-*` (T3): a geometry kick that overflows (`--geometry 1`), the
state page (page 6 of a 1024x768 context) zeroed or filled with a ramp just before the final
render's kick, at 0x30 and 0x28, against a control: H45-R (the final render does not read the
page: same page-table walk, same image) against H45-L (it does: the walk differs or a fault); the
ramp is risky and last.
Outcomes. H191-L: the kept words are generated from the owner's free-list state and a model can
write them. H192-R true: the slot step stores for any owner; false: the kept page survives.
H45-R: no load task reads the state page; H45-L: `dpm.rs` must read it back and the junk shows
how. T4's answer cuts the Q191 question in two; the TA-kick against render-end half needs the
optional kernel switch K1 (section 4).

### P9. Hangs with wide scenes (script `wide`, risky; Q103)

E438: 300 vertices hang at 4096x4096 0x40 and 0x23, 900 and 1500 at 0x100. New: `hold_recovery`
on the first three cases (300 at 0x40 and 0x23, 900 at 0x100): after the tool's timeout the script
copies `regs`, the control block and the render memory before the reset (E354: the held job's
memory is as the GPU left it); and 600, 750, 800, 850 vertices at 0x100 to put the boundary
between 600 (overflows, E574) and 900 (hangs). Held state: STATUS1 head/tail (pages exhausted:
head = tail + 1), 0x0658 (a partial render under way), 0x0720. Outcomes: pages exhausted with
0x0658 = 0: the TA ran out before a partial render could free any (the DPM has no spare page:
a rule `dpm.rs` can state); 0x0658 = 1: the partial render hangs (a hardware path to refuse); the
boundary: the scene size in pages that hangs at a given P. A hang is an outcome (`hang`), not an
error; three failed recoveries stop the script.

### P10. Repeatability and non-repeatable results

Every claim sits on two runs after a reset (`-r1`, `-r2`, the two `st-repeat` jobs, the two
`fr-*-rep` jobs, the `wd-bit2` runs). The recompute prints R (kept observables identical: status,
partials, dwords 35 to 39, zero dwords) or NR with the observables that differ. An NR case is not
a prediction target and is not scored: it enters section 5 as an outcome set.

## 3. Declared sets, predictions, discipline

Sets (`declared.tsv`, 204 cases: 33 fit, 123 heldout, 48 control): fit = a case whose outcome a
record or the offline reading used (the E310 rows, E461 and E468 cells, E465's windows, E591's
words); heldout = a cell or size no model used; control = a repeat; `explore` predictions (`?`)
cannot fail and are reported as exploration. `predictions-declared.tsv` (558 rows: case, quantity,
value, model) is computed by `gen/gen_p1139.py` from the models; alternative models are separate
rows and one of them is expected to miss. Frozen by hash before any run (section 6): the two
files, the six tables, the generator, the library, the runner, the order and the recompute.
Nothing in a held-out case is adjusted after a run; a model fitted afterwards is declared in a
later file with its own hash (follow-up style of p1134) and its jobs are its fit.
Raw: every output, dump, control block, depth buffer, kept page and timeline is gzipped whole
(`gzip -n`) with its raw sha256 in `raw.sha256`; the kernel journal with one `resgx545 case`
marker per job is `kernel.log` (audit D3); no pixel row is spliced with the tool's messages
because no job prints pixels (D2); `probe` exits 3 on a failed job (D5). The loaded module's
srcversion is read from `/sys/module` and compared with the installed one in every script's
preflight, both printed; the tool's, regtimeline's and the firmware's sha256 are printed (D9).
Recompute: `python3 -B recompute/recompute_p1139.py DIR` reads `cases.tsv`, the gz files and the
two declared files only; it shares no code with the runner (which keeps raw files and prints no
reduction). It prints every prediction with its observation, tallies by model and set, the table of
P5, the held registers of P9, and R / NR by case group. `--selftest` builds a toy run and checks
every decoder; run over the landed E489 dumps the decoders give E465's 326656, 80640, 246016,
196096, 48000 and 148096.
Every case that claims something can fail: 193 of 204 cases carry a prediction that is not `?`;
the other 11 are references scored through their partners (`ow-part-solo`, the two
`ow-fill-control`) and exploration (the ramp at 0x60 and 0x100, which produce P5's table, the two
`ow-kcopy`, the two `ow-part-*-n` closes). Per-job markers: the fill dword, the kernel log line,
the case name in `cases.tsv`, the tool's own colour pair.
Order and stops: safe tables first, Part B after Part A, risky tables last, one script at a time;
a failed job (fault, hang, rejected) is followed by a debugfs reset, `render_pb_pages` back to the
installed value and the health triangle (64x64 exact; a reset and two retries 3 s to 5 s apart);
three failed recoveries stop the script (`## abort`), and the batch with it: read `journalctl -k`
before another run. No `kreg`, no `kregnow` and no clock-gate register (never CR_CLKGATECTL2),
no trc_hazard, no `/dev/mem` write, no reboot, no recursive delete.

## 4. Scripts, tables, tool changes, kernel, validation

`run_table.sh TABLE safe|risky|all`: one job a line of `tables/TABLE.txt` (name, set, risk, P,
knobs, timeline registers, tool arguments). Knobs: `keep` (render_keep and render_kept), `hold`
(hold_recovery and the held copies), `noreset`, `new` (the changed tool). `run-all-1139.sh` is the
order: `free`, `trig`, `state`, `depth`, `wide`, `owner` safe (Part B cases skipped with a line
when `~/sgxfive-test-1139` is absent), then `trig risky`, `owner risky`, `wide risky`.

Tool changes, none made in the repository. `tool-new/` is a scratch copy of the 11.35 source with
T2, T3, T4 applied (`tool-changes/p1139-sgxfive-test.diff`, 183 lines, source sha256 70b09d58...);
`tool-tests/test_cli_p1139.py` has the failing tests:

- T2: `tri --keep-overflow --ctx2 [--close-first-early]`: an overflow of the first render no longer
  skips the second context, and an overflow of the second is counted (1 test: fails on the unchanged
  tool, passes on `tool-new`).
- T3: `tri --tadata-fill-render N:PAGE:VALUE[:ramp]`: debugfs `tadata_fill` written before render N
  (2 tests: fail, pass).
- T4: `tri --ctx2 --kept-copy DIR`: debugfs `render_kept` copied to `DIR/kept.N.bin` after the
  second context's render N (2 tests: fail, pass).
- T1: `probe --tri ... --depth-scratch [--depth-ctl V]`: the probe's scratch buffer is the ZLS
  buffer (the pokes of `tri --depth`), so `--vertices`, `--copy-depth`, `--obj2` and the reload
  background (bgpixel, bgpds) meet a depth buffer; windows up to 16384 dwords (64 KiB;
  `--scratch-pages 64` for 256x256). 1 test, fails on both: not implemented, only specified.

The unchanged tool fails 6 of 7 and the changed copy 1 of 7 (T1). The existing `tests/test_cli.py`
gives 163 passed and 45 errors (a helper module the copy lacks) for both builds. Part A needs none
of them; the batch is useful without T1 to T4 (191 of 204 jobs).
Kernel: none needed. T3 replaces the kernel switch that "a poke at the final render's kick" would
have needed: the geometry kick and the final render are two kicks, so the poke goes between them.
Optional, separate, not part of the batch: K1, debugfs `render_kept_snap` (one-shot): the kernel
copies the kept context's TA data pages (control, OTPM, state) at the second context's TA kick and
at its 3D kick, before the firmware is told, to a readable file; it answers Q191's "at which kick"
(T4 only separates job end from close). Not reachable by any host switch: a poke between a partial
render and the final render inside one kick (the firmware does it; only a firmware task of our own
could).
Validated here: `bash -n` on every script; the six tables run end to end through `mock/run-
mock.sh` (the real 11.35 mock tool, a fake debugfs directory, shims for sudo, modinfo and
regtimeline): 204 jobs, dumps and gz files kept, the health stop worked (a harness mistake, a
missing kpoke path in the fake debugfs, aborted a run after three failed recoveries), flow and
file formats only (the mock has no kpoke, no partial renders and no registers); `recompute` runs
over those dumps without a decoder error and its selftest passes; the generator is deterministic.
Not validated: every outcome, the run time, whether the kernel takes `pb:11`, whether
`render_pb_pages` 0x2000 still works with a 64 MiB depth buffer (E465 did), the timeline sampling
interval with 12 registers (E574: 29 us for 85).

## 5. Run order and what becomes phase 12 vectors

Order: `./run-all-1139.sh` after `stage1139.sh` and (Part B) `deploy1139.sh`; then
`python3 -B recompute/recompute_p1139.py ~/p1139-dumps-copy` on the Mac.
Vectors (12.7, `doc/specs/vectors.md` style, each naming its records and questions, the dumps by
sha256 as the data repository does):
- `dpm-trigger`: input (P, thresholds, U or the scene's page need), output (partial count,
  last abort status, dword 35, overflow yes/no): the P2 table, fit and held out marked.
- `dpm-pool`: input (P, a sequence of jobs with their page needs), output (the free-list walk after
  each job, the pages each took): P1; walks are exact vectors.
- `dpm-state`: input (scene geometry, P), output (the 17 lists, dword 35, 39): P3, only where the
  rule held; the cases that did not hold stay as recorded observations.
- `zls-overflow`: input (scene, ZLS control, P), output (window, zero prefix, sign, loaded or not):
  P4 to P6, from the recomputed counts, not the dumps themselves (the 3 to 64 MiB buffers stay in
  the data repository).
- `dpm-owner`: the kept words (P8) for the cases that repeat.
- A model with no vector refuses at run time: sizes or P not in a vector refuse.
Non-repeatable outcomes: not a vector with one value; an `observed-set` record: the case, the
condition (reset or none, tool, module), `n` runs, the value counts, the observable (for example
`0x0748 bit 2 clear: 2 of 8, after reset 2 of 4, without 0 of 4`); the simulator's model for it is
an explicit `unmodelled` flag (it does not choose a value), and a model prediction counts as met
if its value lies in the observed set. A hang is an outcome class (`hang`, with the held state if
read), not an error, and a case that hangs once and completes once is NR by the same rule.

## 6. Hashes and disclosures

Written 2026-11-09 10:4x, before the first run (`hashes.txt`):

```
27ce16862f515083dbbcdc6b7a5a04533218ce7c580a16976b462f80343a0955  declared.tsv
b7c65c34e0d2b42d85317cec5a223f45dd0b40539f91de944e92298c572fcbc3  predictions-declared.tsv
01f90229eb85e32f471e0ca180e8a335c9784f3d70748d01d210fb4682f278ea  tables/free.txt
2f7f6fb4aba0fe51bdb8a9cdfe1dfd9b1c709ec41aa63aec9287a127c91a4caa  tables/trig.txt
9cccca533ac20a9dff11044153cb2ae37473811d3b07265d36fa760f55ae9de3  tables/state.txt
1cf6f86c5d975081db5935104248e71c0415ccbcb3b53ce5ff2fbb995730e036  tables/depth.txt
81ba89a8dae99f5c84e73277e540a951fb108dcbe5257bfc631c9ad5cd3c9d9a  tables/wide.txt
759e71687cf48038b20bba65891e5825c6b772f6b98f9acd47cc7807b7d0c0e2  tables/owner.txt
006a9b5f16ae809868bb52de7fee11f9f9ae87b331bf30c60b91cb2454c55a2c  gen/gen_p1139.py
f5e7e115ae8aa33a82d465a26291f5f5bce1ed829f8f68d01196f082d813dd00  lib1139.sh
fa3d7d2a6f8c8c076a0497eb72fdb1a606b448d6c9a0ce03da59f871cc46f3bd  run_table.sh
6667e026e6bd5ccb12a869d9fd30b6baa5b9b5c96164f0d680cc1b6befbd2003  run-all-1139.sh
0645361443e4319b8abd538d31887578adc41c6184f4119b040aa75beb2da227  recompute/recompute_p1139.py
```

Disclosures written before the runs. (1) Two offline readings of landed dumps preceded the
predictions: the zero prefix (`analysis/off_zero_slots.py`) and the sign of the overflowed 4096x4096
stores (`analysis/off_sign4096.py`); the G = 1 and G = 0 zero counts and the positive sign of those
jobs are their `fit`, the G = 127 band and the sign table are not. (2) R1 and U(4096x4096) = 289 are
fitted to E204's ten partial renders and E310's rows; U(1024x768) = 21 and H-sign-P's boundary at
0x2c are assumptions, declared as such. (3) The E464 and E310 disagreement (P3) was found while
reading the records, not in a run. (4) Three commands of the
planning session that contained a recursive or glob removal of scratch files were refused by the
harness and not retried (the first, which also carried the library's first form, was written again
without it); the scripts delete non-recursively only. (5) The mock run does not exercise
`hold_recovery`, the pokes or the timelines' sampling. (6) A change to a frozen file after
`hashes.txt` is disclosed in the records with its new hash.
