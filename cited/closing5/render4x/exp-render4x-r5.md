# Proposal round 5, RENDER / 4x: Q292's onset and cause, reruns of stages o and t

2026-11-12. Planning only: nothing ran on the laptop, no repo edited, no guard run, no build.
Scratch work, all in `~/src/scratch/resgx545/closing5/render4x/` (read-only against the kept data;
publishable: our own fork's layout formula and published datasets only, nothing firmware-derived):

- `onset_fit.py`, `onset_fit.out`: 15 candidate rules against the 13 four-array 4x cells on
  record, then their predictions at the proposed cells.
- `rgn_check.py`, `rgn_check.out`: the region-header rule of a 4x job, checked on 12 kept dumps.
- `pb_scan_all.py`, `pb_scan_all.out`: scene pages of all 51 kept `--tri-full` rows with a dump.
- `td_scan.py`, `td_scan.out`, `rgn_map.py`, `rgn_dump.py`: page maps and header listings.

Everything in section 1 is a POST HOC reading of data measured before these scripts existed.
Section 3 holds what a run would freeze.

## 0. Summary for the decision

| item | offline result | laptop | jobs | risk |
|---|---|---|---|---|
| Q292 onset | not decidable from kept data (1.1) | stages l, x | 5 + 3 | 2 to 8 faults, 3D side |
| Q292 cause | one candidate fits 13 of 13: H-TPC (1.4) | stage m, row d | 5 + 1 | 1 to 5 faults |
| stage o | the control's need was wrong twice (1.6) | stage o again | 11 | none predicted |
| stage t | the kept dumps score with the name fixed (2.2) | stage t again | 9 | none predicted |
| 11.32 tables | nothing to do (section 5) | none | 0 | - |

- The kept data cannot place the onset: no four-array 4x job has W > 1024 with H <= 768 or the
  reverse, and no faulting job left a dump or an image.
- It does give a candidate cause with a test that needs no kernel change. H-TPC [infer]: at 4x
  the TA's tail pointer cache covers the doubled tile grid, four times what our kernel reserves,
  and its tail end runs over the region headers. The same faulting size on a context made for a
  larger maximum (more room) is then predicted to complete. Every size rule predicts a fault.
- No reboot is needed if the laptop is still on the rgn4 kernel (module 99CD90DA) with
  `~/sgxfive-test-rgn4`. If it has rebooted to stock Arch, the session needs the one-shot boot
  of the rgn4 test kernel, with the user's OK.

## 1. What the kept data decides offline

### 1.1 The onset: not decidable, and the cells E845 names are confounded

`pb_scan_all.out` lists every kept `--tri-full` row with a dump in the 15 published closing
sessions. The four-array 4x cells are E824's nine sizes, E828's two, E845's and E846's: 9 sizes
complete (64 x 64 to 1024 x 768) and 4 fault (1280 x 1024, 2048 x 1536, 4096 x 1152, 4096 x 4096).
None has one dimension past 1024 x 768 and the other inside. So width, height and count stay
tied, as E845 says. Rests on: E824, E828, E845, E846. Nothing to refute; no held-out check.

Two of the four faults also overflow the buffer (4096 x 1152 needs 1153 pages, 4096 x 4096
needs 4097), and both are 256 tiles wide on the doubled grid (1.2), past the 128 columns a
single-sampled 4096-wide target has. They are the only faults with right pixels (756800 and
1048576, first wrong at (1024, 0)). I leave them out of every prediction below: two or three
effects are mixed there. The same holds for Q292's "to settle it" cells 4096 x 960 and
960 x 4096: I propose cells that stay at or below 2048 each way instead.

### 1.2 What the TA writes at 4x: the doubled grid (fit, 12 of 12 dumps)

`rgn_check.py` checks one rule on every kept four-array dump (E824's nine, E845's s0, E846's o3
and o4; 31744 headers): **0 headers off the rule**.

- The TA writes the single-sampled layout's macrotiles with both spans doubled: 2 mx by 2 my
  tiles of 16 x 8 pixels, n by n macrotiles, column-major, each in 4 x 4 blocks.
- Header word 0 is flags, x in 23:16, the macrotile in 15:12, y in 11:0; bit 25 marks a tile
  outside the target (no stream). Word 1 is the stream's offset from the request base. Word 2
  is zero.
- One stream per tile of the doubled grid inside the target: 2 tx x 2 ty streams (6144 at
  1024 x 768). This is why the four arrays are needed and why U4 doubles the page count.
- Bytes 0 to `td.rgn` (tail pointers, DPM control, OTPM, DPM state) are all zero after every
  completed job. o4, the overflow, has a non-zero state page and zero before it.

[infer] A header of three zero words reads as "has a stream, at the request base plus 0". Page 0
of a parameter slot is never mapped, so a 3D that reads a zeroed header faults at page 0x10000:
the word of all four faults and of E511's three. E511's own reading was "the words and the RT
data disagree".

### 1.3 What the closed driver does at 4x (one captured size) [CAP, infer]

E339: for a 64 x 64 4x target the closed driver halves the macrotile words (0x00802002 against
0x01004004) and quarters the stride (4 against 0x10). With 1.2's doubling, its TA then tiles
macrotiles of 4 x 4 doubled tiles, exactly the single-sampled layout of a 128 x 128 target. Ours
keeps the single-sampled words, so our macrotiles are twice as wide and high as needed, and
every buffer size we derive is the single-sampled one. [infer] The closed driver's buffers for a
4x target are those of the doubled target; the RT data words that would show it were not read
for that capture (Q086's open part). One size, so this is a direction, not a rule.

### 1.4 Candidate causes against the 13 cells (`onset_fit.out`)

The kernel reserves `tail_size` = 4 x side x side bytes for the tail pointers, side the power of
two over the single-sampled macrotile span; then one page each of control, OTPM and state; then
the region headers (`sgx_render.c`, fork a2788bd8). At 4x the doubled grid has four times the
tiles.

**H-TPC [infer].** At 4x the hardware keeps 4 bytes a tile of the doubled grid from
`CR_TE_TPC_ADDR` on, and clears or flushes them when the TA ends (the firmware's
`CR_TE_TPCCONTROL` write in 3d.md's TA-finished steps). Where that extent passes `td.rgn`, the
first region headers are zeroed after the TA wrote them, and the 3D faults at the request base
(1.2).

| rule | fault iff | fits |
|---|---|---|
| TPC-d-rgn | 16 tx ty > `td.rgn` (dense rows of 2 tx) | 13 of 13 |
| TPC-d-state | 16 tx ty > the state page's offset | 13 of 13 |
| TPC-rs-rgn | 16 (n mx) ty > `td.rgn` (rows of the macrotile span) | 13 of 13 |
| TPC-rb-rgn | 16 (n mx)(n my) > `td.rgn` | 13 of 13 |
| TPC-rs-state, TPC-rb-state | as above, state page | 12 (640 x 480 completes) |
| TPC-sq (rows of 2 side) | - | 12 and 10 (1024 x 768 completes) |
| K-W, K-H, K-OR, K-AND | W > 1024; H > 768; either; both | 13 of 13 each |
| K-TPM, K-P, K-AREA | tiles a macrotile > 128; U4 > 193; pixels > 786432 | 13 of 13 each |

- At 1024 x 768 the extent is 0x6000 and the state page starts at 0x6000: the largest size that
  completes sits exactly at the limit. At 1280 x 1024 the extent is 0xa000 against `td.rgn`
  0x7000. Neither is a test: both were known when the rule was written.
- Eleven rules fit everything. The kept data cannot choose among them. H-TPC is the only one with a
  mechanism for the fault address, and it alone depends on the context's maximum.
- Not explained by any rule: why 4096-wide faults leave a right block (1.1).

Rests on: E824, E828, E845, E846 (outcomes), E339 (direction), the fork's layout. Refuted by:
section 3's stage m or l. Needs the held-out check; nothing here should land as more than a
dated [infer] note on Q292.

### 1.5 Region headers of a faulting job: not kept

A fault loses the context, so `--dump-render` wrote nothing for all four faults, and no fault
row had `--pixels`. The hold path (`hold_recovery` Y, then debugfs `render_param` and
`render_tadata`) was tried once, on o5, which did not fault: its two files are the 62- and
63-byte error text. So the held dump has never returned data on this module. Row d (3.5) is the
first real use and is scored as exploratory for that reason.

### 1.6 Stage o's control was wrong twice

- E846 found the first slip: o2's row ran the default triangle (19 scene pages in three kept
  dumps: s0, o1, o2) while its need was frozen for the full triangle.
- Second, new here: the frozen need 97 is not the full triangle's need at 1x either. The one
  kept 1x `--tri-full` dump with a size (r2-pixel `a4-ctl-320x400-te20`) has 10 scene pages; the
  formula behind 97 gives 17. Streams at 1x are one a 32 x 16 tile and pages are taken a
  macrotile (E773's HU1): 4 + 3 + 1 + 1 + 1 = 10 there. For 1024 x 768 that is 16 x 3 + 1 = 49
  [model, 1 of 1 fit, post hoc].
- So had o2 run the full triangle at P 0x82 (96 usable) it would have completed all the same.

If stage o's 1x full pair measures 49, E846 needs an appended correction to its sentence "the
frozen need 97 is the model of the full triangle" (the model was wrong for 1x). Before that,
nothing lands.

## 2. Reruns of o and t: what changes, and the dry run that proves each fix

Both reuse `closing4/r4-render4x` (generator, runner, scorer, tests) in a new session directory
`closing5/r5-render4x`. The r4 mock could not see either slip: `tests/worlds.py` answers by the
case NAME from the kmsg marker and writes every dump as `tri.*`, so a row's argv never reached
the test.

### 2.1 Stage o (11 jobs, no fault predicted)

The question changed: E846 read, post hoc, that a 4x overflow ends in -ENOSPC. The rerun freezes
that as H-ENOSPC4 and tests it on sizes not run.

| row | job | P | need (source) | frozen | set |
|---|---|---|---|---|---|
| o1 | 1x default, 1024 x 768 | 0x35 | 19 (3 kept dumps, E773) | complete | control |
| o2 | the same | 0x34 | 19 | -ENOSPC, no fault | control |
| o3 | 4x full, 1024 x 768 | 0xe3 | 193 (4 dumps) | complete | control |
| o4 | the same | 0xe2 | 193 | -ENOSPC, no fault | replicate |
| o5 | 4x full, 288 x 144, `--pixels` | 0x23 | 12 | -ENOSPC, no fault | replicate |
| o6, o7 | 4x full, 640 x 480 | 0x6e, 0x6d | 76 (E824 h6) | complete, -ENOSPC | held out |
| o8, o9 | 4x full, 512 x 384 | 0x53, 0x52 | 49 (E824 h5) | complete, -ENOSPC | held out |
| o10, o11 | 1x full, 1024 x 768 | 0x53, 0x52 | 49 [model, 1.6] | complete, -ENOSPC | explore |

- Changes against r4: o1 and o2 keep the argv that ran and move the boundary to its measured
  need. r4's o6 (dead condition), o7 (belongs to Q292) and o8 (ran, nothing new) are dropped. o5
  is plain, not held. o10 and o11 are the pair r4 meant to run; they gate nothing.
- Control that can fail: o1 and o2 (the page rule one page apart, on a measured need).
- Verdict: H-ENOSPC4 held if o7 and o9 end in -ENOSPC with no BIF line and o6 and o8 complete
  with 0 wrong. Refuted by a fault in o4, o5, o7 or o9. o4 and o5 are labelled replicates: their
  outcome is known, so they are not counted as held out.
- Stop: the first fault-class event ends the stage (limit 1; none is predicted).

Dry runs, before the laptop:

1. **Scene twin test (would have caught o2).** For every row with a frozen need, the generator
   looks up a kept row with the same argv (knobs and paths stripped) in the published
   `cases.tsv` files and takes the need from that row's dump. A control with no twin, or with a
   need marked [model], fails the build. Run on r4's own o table it must fail at o2 (19 against
   97): that failing case is kept as a regression test.
2. **Argv-driven mock.** The fake tool decides from argv and the fake `render_pb_pages`: scene
   pages from the twin table (or the stated model for o10 and o11), overflow iff P - 0x22 is
   below them. It no longer reads predictions. The tool's own `--mock` output (built from the
   pinned source, as `tests/mock_all.py` does) supplies the triangle line, and a test compares
   that line with the scene the need was frozen for.
3. **Replay on real files.** The new scorer on r4's kept `out/20261111-211649/o` for the rows
   whose argv and P did not change (o3, o4, o5): PASS, held, held.
4. **Gate across attempts.** r4's stage summaries read s0 as NODATA after `--from`. The gate
   file now names the attempt that holds s0 and the stage scorer reads it there. Tested in the
   mock with a two-attempt run, and on r4's two real attempt directories.

### 2.2 Stage t (9 jobs, no fault predicted)

| row | job | frozen | set |
|---|---|---|---|
| t6 | E827's pb-e40-m2-64a | its words and hash | control |
| t3b, t4b | the 11.31 line and point, no poke | their kept heads (11.31, r4's dumps) | control |
| t1, t2 | 0x40, 0x80 on a 4x context | dword 11 zero, format word at 12, empty | replicate |
| t3, t4 | line, point with 0x40 | zero dword inserted at 9, at 11 | replicate |
| t3c, t4c | line, point with 0x80 | zero dword inserted at 9, at 11 | held out |

- Changes against r4: the scorer derives the dump name from the row's verb (`tri` gives
  `NAME.tri.param.bin.gz`; `probe ... PROG.bin` gives `NAME.PROG.param.bin.gz`). A row that
  asked for a dump and has none is a READER-MISS error, not NODATA, and `insertion()` refuses to
  run with a side missing (r4 printed "no single insertion" on no data).
- t3 and t4 ran and were read post hoc (E847), so they are replicates. t3c and t4c are new: the
  poke 0x80 was never run on a line or a point. H-PAD predicts a zero dword at the same place;
  H-FIELD a non-zero one. The empty image is predicted [infer] and reported.
- Stop: the first fault or unexplained failure (limit 1).

Dry runs:

1. **Replay on real files (would have caught it).** The fixed scorer on r4's kept
   `out/20261111-211649/t`: t3b and t4b PASS, t3 held at 9, t4 held at 11, a decided summary.
   `closing4/fold-render4x/scratch/posthoc_t.py` already shows these values with the frozen
   `insertion()`; the dry run makes it the scorer's own output.
2. **Name census.** The mock writes dumps under the names the real tool uses, taken from the
   kept real directories (r4's t, 11.31's line and point sessions) and, if the pinned tool's
   `--mock` writes dump files, from its own output. A test asserts that every row of every stage
   resolves to exactly one dump name and that the mock's file set matches the kept pattern.
3. **Regression.** r4's scorer against the correctly named mock must print NODATA for t3b and
   t4b; the test keeps that as the failing case.
4. In the all-hypotheses-held world, any NODATA, READER-MISS or "cannot tell" fails the suite.

## 3. Q292: the proposed stages

Common to every row: `tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width W
--height H --max-width MW --max-height MH --aa4` with E824's words, `--dump-render`,
`--regs 0x0700-0x072c`; a debugfs reset before each; `render_rgn_arrays` 0 and `render_pb_pages`
0x422 read back. Every scene fits the buffer (U4 at most 769). Every size is at most 2048 each
way. All on the rgn4 module as it is.

Frozen per row: outcome (complete with 0 wrong, or fault with BIF_INT_STAT bits 15:0 0x0100 and
page 0x10000); for a completing row also the scene pages (U4), the TA data size of the maximum's
layout and 0 headers off 1.2's rule.

### 3.1 s0, controls (3 jobs)

r4's three, unchanged, with their kept hashes. A miss voids the session.

### 3.2 m: the same size with more room (5 jobs; the decisive stage)

| row | target | context maximum | tail room | H-TPC (all four) | every K rule |
|---|---|---|---|---|---|
| m0 | 1024 x 768 | 2048 x 2048 | 0x10000 | complete | complete |
| m1 | 1280 x 1024 | 1280 x 1040 | 0x10000 | **complete** | fault |
| m2 | 1280 x 1024 | 2048 x 2048 | 0x10000 | **complete** | fault |
| m3 | 1280 x 1024 | 2048 x 1024 | 0x4000 | fault | fault |
| m4 | 2048 x 1536 | 4096 x 4096 | 0x40000 | **complete** | fault |

- The target's words are the same as in E845's faulting jobs; only the buffers' room changes
  (the kernel sizes the TA data for the maximum and checks the words against the target).
- m1 is the sharpest row: 16 more pixels of maximum height move the tail side from 64 to 128.
- m3 is the control that separates "tail room" from "any larger maximum": its region buffer is
  a third larger than the target's own and its tail room is the same 0x4000.
- m0 is the control that can fail (a larger maximum must not break a size that works). A fault
  in m0 stops the stage.
- H-TPC held: m1, m2 and m4 complete with 0 wrong, m3 faults. Refuted: m1 and m2 fault. A
  split (m1 against m2) is reported as it is and decides nothing.
- Fault limit 4.

### 3.3 l: width, height and count apart (5 jobs)

| row | size | H-TPC (all four) | K-W | K-H | K-OR | K-AND | K-TPM, K-P, K-AREA |
|---|---|---|---|---|---|---|---|
| l1 | 2048 x 240 | complete | fault | complete | fault | complete | complete |
| l2 | 256 x 1536 | complete | complete | fault | fault | complete | complete |
| l3 | 768 x 2048 | complete | complete | fault | fault | complete | fault |
| l4 | 1280 x 768 | fault | fault | complete | fault | complete | no threshold |
| l5 | 1024 x 1024 | fault | complete | fault | fault | complete | no threshold (K-TPM: complete) |

- Every rule has its own column of outcomes, so five jobs name the survivor whatever happens.
  This stage answers the onset question even if H-TPC fails in stage m.
- l3 is larger than 1280 x 1024 in pixels, pages (385) and height, and H-TPC says it completes.
- Control that can fail: s0's 1024 x 768 and E845's own cell, rerun as row d.
- Fault limit 5 (K-OR predicts five; 3D-side faults left health ok in 6 of 6 so far).

### 3.4 x: which H-TPC variant (3 jobs, exploratory; only if m held)

| row | size | d-rgn | d-state | rs-rgn | rb-rgn |
|---|---|---|---|---|---|
| x1 | 1024 x 512 | complete | fault | complete | complete |
| x2 | 1184 x 768 | complete | fault | fault | fault |
| x3 | 1024 x 800 | complete | fault | complete | fault |

Four variants, four distinct columns. x1 is the surprising one: under d-state a size smaller
than 1024 x 768 faults. These rows place the onset to one tile column or row.

### 3.5 d: a held fault with its dumps (1 held job, exploratory, last)

E845's 1280 x 1024 on its own maximum, `hold_recovery` Y, registers at 2.8 s, debugfs
`render_param` and `render_tadata` read in the hold, then the kernel's reset.

- Frozen for every rule: it faults with E845's word (the replication; a completion here voids
  l and m).
- Frozen under H-TPC: the parameter dump holds 321 scene pages (the TA finished). In the TA
  data, the headers off 1.2's rule all lie below offset 0xa000 (d) or 0xc000 (rs, rb), header 0
  is among them, and every header past that offset is on the rule.
- A dump shorter than a page is "held dump not read" (o5's kept files are the test fixture) and
  the dump lines then read cannot tell. They gate nothing.

### 3.6 Dry runs for the new stages

- Argv-driven worlds: one fake world a rule (`onset_fit.py`'s rules computed from argv, the
  maximum included). In each world the verdict must name that rule and no other.
- Reader census on real files: a fault row on r4's kept p-1280x1024 (fault, no dump: must score
  as a fault with its word); a completing row on s0's kept 1024 x 768; the header rule on the 12
  kept dumps (`rgn_check.py`'s 0 off).
- Every argv through the pinned tool's `--mock` (accepts `--max-height 1040`, no odd size).
- The layout of every maximum against the 4 MiB slot (largest: m4, 0x223000 bytes).

### 3.7 Order, counts, time, stops

Order: s0, t, o, m, l, x, d. The reruns go first, before any fault. 37 tool jobs (3 + 9 + 11 + 5
+ 5 + 3 + 1) plus the health pair at each stage's ends and after each fault. About 20 minutes on
the laptop; the offline build of the session is the larger part.

Fault-class events, all 3D side: 4 if H-TPC d-rgn holds (m3, l4, l5, d); 13 at worst.

Stops: strict health after every fault (a failing fill or triangle ends the session); any fault
word other than 0x10000011, any TA-side fault, any -110, a hang or a fatal kernel line ends the
stage; knobs read back at every exit. After a stop: no reboot, no unload, no register write.

## 4. If H-TPC holds: what it would change (not this session)

- Kernel: size the tail pointers for the doubled grid on a 4x context (four times, side
  doubled), KUnit first, built on cachix, one-shot boot with the user's OK. At 4096 x 4096 the
  TA data grows from 0x223000 to 0x2e3000 bytes, still inside the 4 MiB slot.
- Records by appended correction: E828 and E824 ("the four-array layout fits" lacks the tail
  room), `render_uapi.md` line 174 and hw_spec's 4x paragraph, Q292 narrowed to the 4096-wide
  residue, a datum for Q086 (the tail cache under 4x).
- sgx-pipe: nothing until the variant is known (stage x).

## 5. The 11.32 probe tables that cite Q113 and Q114

`probes/texture/tx-types.toml`, `tx-types-risky.toml`, their two templates and the 11.32
generator and recompute scripts (`tools/texture/p1132/`) carry "Q113,Q114" in headers and in each
table's `question` line. Nothing needs doing. They are the tables as run in 11.32 (504972b), the
question they were written for; Q114 is still open, and Q113 resolves through
`tools/records/questions.py` ("answered by E844"), which scans records and not probes, so no
check trips. Rewording them would make the files differ from what ran. One thing to remember,
not to do now: if `gen_p1132.py` is ever run again for a new Q114 batch, drop Q113 from its
`QUESTIONS` map at that point, in the generator, so new tables do not cite a retired question.

## 6. User decisions

1. **Session scope.** a) One session `r5-render4x` on the rgn4 module as it is: s0, t, o, m, l,
   x, d; 37 jobs, about 20 minutes, 4 to 13 3D-side faults (recommended). b) Without x and d: 33
   jobs, the cause and the onset rule but not the variant. c) s0, m and the two reruns only: 28
   jobs, at most 4 faults. d) The reruns only (t, o): 23 jobs, no fault predicted, Q292 waits.
2. **What stage l and m freeze.** a) H-TPC's four variants against the seven size rules, as
   tabled (recommended: stage m separates H-TPC from all of them in one row). b) Only the
   neutral ladder Q292 names (4096 x 960, 960 x 4096, then steps): I advise against it, those
   cells mix in the 256-column grid (1.1).
3. **Row d, the held fault with dumps.** a) Run it last, exploratory (recommended: the first
   look at a faulting job's region headers; one held 3D-side fault). b) Skip it.
4. **Stage o's shape.** a) 11 jobs as in 2.1: the default-triangle control at its measured need,
   two replicates, two new 4x boundary pairs, the 1x full pair as exploratory (recommended).
   b) The five rows o1 to o5 only. c) Do not rerun; E846's post hoc reading stays as it is.
5. **Stage t's shape.** a) 9 jobs: r4's seven plus the line and the point at 0x80, held out
   (recommended). b) r4's seven only (all replicates now). c) Do not rerun.
6. **Fault budget.** a) Limits m 4, l 5, x 3, d 1, o 1, t 1, strict health after each
   (recommended). b) Stop each stage at the first fault H-TPC did not predict (fewer faults;
   stage l may then not finish its table).
7. **If H-TPC holds.** a) Plan the kernel change (tail room for 4x contexts) as its own item
   for the next boot; no kernel work in this session (recommended). b) Build it now on cachix
   and add own-maximum rows after a one-shot boot, with your OK for the reboot. c) Text only.
8. **The closed driver's 4x sizes (Q086's capture batch).** a) Not now (recommended: it needs
   the other OS, so a reboot). b) Schedule it after this session: it would show the closed
   driver's tail cache size at 4x directly.
9. **11.32 tables.** a) Leave as run (recommended). b) Also note the generator's map now.
10. **Laptop state.** a) Run only if the rgn4 module is still loaded; otherwise ask you for the
    one-shot boot first (recommended). b) Wait for the next planned boot.
