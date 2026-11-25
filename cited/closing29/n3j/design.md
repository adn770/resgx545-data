# N3j: which client event lands in attribute 1, second reads, and what land's page follows
(design note, not built, not run)

Status: a design for the lead to bring to the user as **flagged decisions** (§8). Nothing here is
built, committed, staged or run; no laptop, cachix or fork was touched. Tags: **[HW]** measured,
with its E number, or a kept stage's kernel log named by session and stage (round 44 is folded as
E1188-E1200); **[infer]** everything else, including every hypothesis named H-*.

Paths: `R` = `/Users/jtorra/src/resgx545` (main 1c8dc10e, records to E1200), `F` = fork
`/Volumes/linux/linux-sgx-r42` at r42-kernel ec6511d5de87, `drivers/gpu/drm/gma500/sgxfive/`,
`C` = `/Users/jtorra/src/scratch/resgx545/closing29`. The laptop runs module srcversion
079DD0D13F231EEAC52FE0F (r42-kernel): forms incl. fw14, sbc43; images v1, crumb, halt, crumb3,
land, mark, landv (`F/sgx_own_pds.h`). Round 44's logs: `C/r44-n3i-logs/runone-N1..N3.out` and the
kept stages `C/r44-n3i-n1|n2|n3/out/*/STAGE/kernel.log`.

**The short version.** One offline finding first (§0.2): every attribute-1 word read so far that is
not a plant is the pa1 of one known event entry, with the count byte K equal to the CCB commands
since the last firmware load (E768), and the kernel's own `ccb_sent` lines confirm the counts in
all 14 kept stages (H-KC). The open question is no longer *what* the words mean but *which* entry
lands and why fills mostly leave the word alone. No fork change, no build, no boot; one scorer-side
kit change (K9: the count from `ccb_sent`, printed and used as a control). N1 (quiet, crumb3) gives
the second reads the sim's two-read rule needs (FF2, T2, TF2), a third read of one fill (F3), a
second unplanted read (F2b), and one new list, tri,tri (TT), that splits "the last triangle
writes" from "the first triangle after a load writes". N2 and N3 run land: LF2 repeats LF (sa0 2,
page 0), LT reads what a triangle alone leaves in sa0-sa2 and where land then stops.

## 0. What round 44 left

- **Six plants held** [HW, E1188, E1190, E1192, E1194, E1197, E1199]: W's mark image put M1
  0x005d1000 in sa1 (and M13 in sa13 and pa1) with no fault, its 3rd-8th runs.
- **The reads after a plant** [HW]: FT (fill,tri) 0x04400000 (E1189); FF (fill,fill) M1 kept
  (E1191); T (tri) 0x02400000 (E1193); TF (tri,fill) 0x02400000 (E1195); LF (fill, then land) M1
  kept (E1200). With no plant: F2 (fill, after TF's default end draws) 0x05400000 (E1196). Earlier:
  one fill after a plant 0x01000000 (F, E1187); fill,tri with no plant 0x04400000 six times and
  0x04000010 once (X) (n3i §0.1). H-N, H-LAST and H-ACC are falsified; H-K's "last entry" too
  (FF, TF, F2) [HW against the frozen predictions].
- **land's stop** [HW]: LM (no draws since the plant): post sa0 = V0 0x32004000, sa1 = M1, sa2 = V2
  0x32002000, the stop at M1's page (BIF_FAULT 0x005d100f) (E1198). LF (one fill): post sa0
  0x00000002, sa1 = M1, sa2 0x01049b60, the stop at page 0 (0x0000000f) (E1200). H-IMG fails.
  LC and LC2 (fill,tri, no plant, r40-r41 modules): post sa0 0, sa1 0x04400000 (LC2), sa2
  0x0104b95b and 0x01030b00, page 0 (E1176, E1178). The Corrections of 2026-11-24 on E1176, E1178,
  E1182, E1183 and E1187 state these; H-SA0 (the tick pass reads sa0, then sa1) is [infer].
- **The sim** (`R/crates/sgx-sim/src/sgx.rs`, `State::attr1_now`): attribute 1 is known only with
  no draws since the plant; every sequence read once (FF, T, TF) stays unknown until a second read
  agrees; one fill and fill,tri disagree across reads and stay unknown (the user's rule, 1c8dc10e).

### 0.1 What differs between the rows besides the draw list [HW, the logs]

Read from `runone-N1..N3.out` (ROW, JOB, SURVEY, EVENTS) and each stage's `kernel.log` (marks
`row begin`, `health begin try N LIST`, `owntask-arm`, the kernel's `loaded ... ccb_sent N` line at
each firmware load):

| row | E | draws | events at the arm | ccb_sent begin to arm | post sa0 | post sa1 | post sa2 |
|---|---|---|---|---|---|---|---|
| FT | E1189 | fill,tri | 3 | 276 to 286 (10) | V0 (image) | 0x04400000 | V2 (image) |
| FF | E1191 | fill,fill | 2 | 314 to 320 (6) | V0 (image) | M1 | V2 (image) |
| T | E1193 | tri | 2 | 348 to 356 (8) | V0 (image) | 0x02400000 | V2 (image) |
| TF | E1195 | tri,fill | 3 | 384 to 394 (10) | V0 (image) | 0x02400000 | V2 (image) |
| F2 | E1196 | fill (no plant) | 1 | 407 to 411 (4) | V0 (image) | 0x05400000 | V2 (image) |
| LM | E1198 | none | 0 | 447 to 449 (2) | V0 | M1 | V2 |
| LF | E1200 | fill | 1 | 484 to 488 (4) | 0x00000002 | M1 | 0x01049b60 |
| F | E1187 | fill | 1 | 235 to 239 (4) | V0 (image) | 0x01000000 | V2 (image) |

- **The same in every row** [HW]: sa3-sa31 and the started entry's pa0-pa15 equal word for word in
  all 13 stages of round 44 (plants included); attributes 3-12 the same floats and pointers; the
  pre survey the same (sa0-sa2 = V0, V1 0x32005000, V2); every draw exact at try 1 (fill job time
  389-419 us, triangle 5557-5615 us); job 1 saw 8-10 ticks; the begin window (reset to the draws)
  about 6 s in every stage (RESET_WAIT 3 + HEALTH_WAIT 3); the plant stage right before each read
  ended with `end_draws = "none"` (the register health only).
- **"events seen"** counts 1 per fill and 2 per triangle [HW, the table]. It does not follow the
  write: T (2) wrote, FF (2) kept; TF (3) and FT (3) both wrote, different words.
- **`ccb_sent`** at each load rises by exactly 2 + 2 per fill + 6 per triangle from the begin load
  to the arm's load, in all 14 stages (13 of round 44 and F) [HW]: the begin boot's GETMISCINFO,
  the draws' kicks (E747: a fill's two slot-0 entries, a 64x64 triangle's six), the arm's power-off
  ("SGX power-off after N us"). From the disarm's load to the exit's: 2 + the end draws' kicks
  (the disarm's boot and `fwtask_run.py reset`'s own `miscinfo()`), with no power-off line [HW].
- **F against LF** (the one pair with the same history: plant, a 6 s begin window, one exact fill,
  the arm) read different sa1 words [HW]. The only differences are the image (crumb3 stops the tick
  with `tim` and writes V0 and V2; land writes attributes 24 and 26 and leaves the tick running)
  and the session (round 43 against 44). crumb3 does not write sa1 (FF, E1191) [HW].

### 0.2 H-KC: each word is one entry's pa1, with K = commands since the load [infer, offline]

E768: an event's pa1 bits 31:24 are the CCB commands since the last firmware load, a kick entry
carrying the count before its own; E746: ticks are pa0 2, pa1 bits 23:0 0, pa2 0x01061a70; E747: a
fill gives (0:8, 3:4, 0:8), a 64x64 triangle (0:8, 1:9, 3:4, 3:22, 0:8 x5) [HW]. With the
§0.1 counts, K is 1 when the begin draws start (the debugfs reset's boot) and 2 when the end
draws start (the disarm's boot and the runner's read) [HW counts; infer that they are E768's K]:

| row | the entry | its K | pa1 | read |
|---|---|---|---|---|
| FT, six rows | the triangle's 3:22, after one fill | 1 + 2 + 1 = 4 | 0x04400000 | yes |
| X (E1174) | the triangle's 3:4, after one fill | 4 | 0x04000010 | yes |
| T, TF | the triangle's 3:22, first draw | 1 + 1 = 2 | 0x02400000 | yes |
| F2 | TF's **end-draw** triangle's 3:22 (after the end fill) | 2 + 2 + 1 = 5 | 0x05400000 | yes |
| F | a tick before the first kick of a load | 1 | 0x01000000 | yes |
| FF | the 2nd fill's 3:4 | 4 | 0x04000010 | no (M1) |
| TF | the fill's 3:4, after the triangle | 7 + 1 = 8 | 0x08000010 | no |
| F2, LF | the fill's 3:4 | 2 | 0x02000010 | no |

So F2's fill wrote nothing: its word is the one TF's end triangle left across the begin reset, as
attribute 1 keeps a word across resets (E1185) [infer]. All twelve non-plant words fit; no fill's
own entry (3:4 at bit 4 with a fill's K) has ever been read [HW values, infer reading]. What H-KC
does not say: why a triangle's slot-3 entry lands and a fill's does not, and why F's tick landed
once. LF's sa0 2 is a tick's pa0 (E746), but its sa2 0x01049b60 is not the tick's grid word and
attribute 1 kept M1: no single entry of E746/E747 has that shape with attribute 1 unwritten.

### 0.3 Readings of which entry lands [infer]

All fit every read so far under H-KC; they differ on the rows of §3.

- **H-TRI (the last triangle's slot-3 entry).** Only a triangle's slot-3 entries write the bank
  (3:22 as a rule, the 3:4 when their order varies, X); a fill's entries never do; F's tick was a
  stray. The last triangle since the plant decides the word, at its own K.
- **H-FIRST (the first triangle after a load).** As H-TRI, but only the first triangle after each
  firmware load writes; a later one in the same load does not. T, TF, FT and F2 all had one
  triangle per load, so nothing so far splits it from H-TRI.
- **H-RACE (any entry, by a race).** Any event entry (ticks included) may land; which one, or none,
  is decided by timing we do not control. The same list then gives different words across reads:
  F against LF (0x01000000, M1), X against the other FT rows [HW]. It predicts that some repeats
  disagree; H-TRI and H-FIRST predict that repeats agree except a rare tick.

Falsified and not carried: H-N, H-LAST, H-ACC (round 44); H-K as "the last entry" (FF, TF, F2).

### 0.4 What land's stop page follows [infer]

LM's page is sa1's with sa0 = V0, a mapped page; LF's and LC's are page 0 with sa0 2 or 0 [HW].

- **H-SA0.** The tick pass reads through sa0, then sa1; the first unmapped one faults. Rule: page 0
  when post sa0 < 0x1000; sa1's page when post sa0 = V0.
- **H-HIST.** The page follows the draw history, not the bank: page 0 whenever a client draw ran
  since the plant, sa1's page with none. It fits LM, LF and LC as well. It parts from H-SA0 only in
  a row with draws that leaves sa0 = V0; whether any list does is unread, since crumb3 writes V0
  over sa0 and land is the only image on the module that does not (`F/sgx_own_pds.h`).
- **Order rivals.** "sa1 first, the BIF keeps the last fault" and "the lowest faulting page" give
  H-SA0's pages for every bank reachable without a rebuild, since sa0 is only ever V0 (mapped) or
  a word below one page. They are split only by planting chosen unmapped words in sa0 and sa1 (§4).
- **LC's page 0.** Under H-KC with LC's triple (0, 0x04400000, 0x0104b95b), sa0 and sa2 are the
  triangle's 3:22 entry's pa0 (0) and pa2 (an EVENT_TIMER sample), and the page is that pa0's
  under H-SA0. Row LT (a triangle alone, then land) reads that triple directly on this module.

## 1. Rows, one line each

| row | session | question | image | draws before the read |
|---|---|---|---|---|
| WA-WE | N1 | plant M1 (W of E1184 byte for byte) | mark | default |
| FF2 | N1 | second read of fill,fill: M1 kept | crumb3 | fill,fill |
| T2 | N1 | second read of tri: 0x02400000 | crumb3 | tri |
| TF2 | N1 | second read of tri,fill: 0x02400000 | crumb3 | tri,fill |
| TT | N1 | two triangles: last (0x08400000) or first (0x02400000) | crumb3 | tri,tri |
| F3 | N1 | third read of one fill after a plant: M1 (LF) or 0x01000000 (F) | crumb3 | fill |
| F2b | N1 | second unplanted fill after a fill,tri end: 0x05400000 | crumb3 | fill |
| WG | N2 | plant M1 | mark | default |
| LF2 | N2 | second read of LF: sa0 2, sa1 M1, page 0 | land | fill |
| WH | N3 | plant M1 | mark | default |
| LT | N3 | a triangle's sa0-sa2 and land's page | land | tri |
| (WI, LFF) | N4 | optional (decision D): fill,fill's sa0 and the page | land | fill,fill |

Every row: blob `emitsb_sbc43s`, `form=sbc43` (sideband 0xc43, bit 10), `pdsat=fw14`. Every blob,
image and form is on the running module and ran on it in round 44 (mark, crumb3, land: E1188-E1200).
No new firmware bytes. Draw lists are K8's (`tri,tri` is a list of 2 known items: `session.py`
`draws_ok` takes it).

## 2. Kit change K9 (scorer-side, no rebuild; tests first)

**K9, the command count** (`R/tools/closing/kit/kitscore.py`, the per-stage `kernel.log` the kit
already keeps; no change to `run_stage.sh`, `lib_kit.sh` or the laptop's tools):

- Parse every `loaded ... ccb_sent N` line of the stage's `kernel.log` between the marks `row
  begin` and `owntask-arm`, and between `owntask-disarm` and the exit. Print `KC STAGE: begin N0,
  arm N1, delta D, expected 2 + 2 x fills + 6 x tris = E` and the same for the end draws.
- **DK** (row-scoped control for read rows): D = E for the begin draws. When DK fails, every
  outcome that names a K reads cannot tell (a command we did not count ran between the load and
  the read); the row's word is printed.
- Print, never score, H-KC's word for each entry of the declared list (§0.2's arithmetic), so the
  fold reads the word against its entry without hand work.
- Tests, red first: the round 44 kept stages as fixtures (FF 6, T 8, TF 10, F2 4, LM 2, LF 4, FT
  10; the end 10 after `fill,tri`, 2 after `none`); a kernel log missing a `loaded` line gives DK
  cannot tell, not pass; a `health ... try 2` mark (a retry) gives DK failed.

Carried unchanged: K1-K8 (job lists, `sleep_ms`, `gate_order`, devcoredumps, hooks, the gate's
failure a scored end, the per-job BIF words, kick-only jobs, the per-stage draws, the draw lists).

## 3. Rows, frozen predictions

Common, as n3i §3: arm `slots=0x1 entry=0 pds=<img> pdsat=fw14 form=sbc43`, blob `emitsb_sbc43s`,
`#limit 0`, flagged, on_stop "end". Job 1 = command 1, slots and dwords filled with 0xdeadc0de
first, `"ticks": true`, 200 ms, no kick. U0 = 0x080401ef; V0 0x32004000, V2 0x32002000 [HW, every
round 44 snap0]; the builder confirms them at the freeze.

Controls, all of which can fail: row-scoped PG, T0, B, **DR** (the declared list ran at try 1,
each draw exact, nothing else between the begin reset and the arm), **DK** (§2); job-scoped E0, J1
and K5 words read in the job's own record (the H3 rule, E1176); **PLANT** (every read but F2b: W-SA1
of the plant stage right before it in the same attempt).

Printed, never scored: the arm line; Δtick; K5's words; the survey (pre, post, where they differ);
post sa0, sa2, sa3-sa13; every fault page against post sa0, sa1, sa2, sa13; "events seen"; KC.

### 3.1 Plant stages WA-WE (N1), WG (N2), WH (N3), WI (N4)

Row W of E1184 byte for byte (n3i §3.1's 21 words): image **mark**, one job, default begin draws,
`own_gate = "none"`, `end_draws = "none"`.

| outcome | rule | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 | **held** [HW, 8 runs: E1184, E1186, E1188-E1199] |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 | **held** [HW, same] |
| W-QUIET | snap9 BIF_FAULT 0 | **held** [HW, same] |
| W-FAULT | a BIF fault after job 1 | failed |

**Cannot tell.** J1 not DONE: stop the session. W-SA1 failing: the next read reads cannot tell (it
runs, printed). W-FAULT: stop for the user.

### 3.2 Read stages FF2, T2, TF2, TT, F3 (N1, each right after its plant)

Image **crumb3**, n3i §3.2's 19 words byte for byte, one job, `own_gate = "none"`, `end_draws`
default (fill,tri). Common: X-QUIET (snap9 BIF_FAULT 0) **held** [HW, E1189-E1196]. All words are
job 1's post sa1. A second read is "the same word as the first read" (the sim's rule).

**FF2** (`begin_draws = "fill,fill"`):

| outcome | rule | prediction |
|---|---|---|
| FF2-KEEP | M1 (FF's read, E1191) | **held** [HW once; H-TRI, H-FIRST] |
| FF2-FILL | 0x04000010 (the 2nd fill's 3:4 at K 4) or 0x02000010 (the 1st's at K 2) | failed |
| FF2-TICK | bits 23:0 = 0, top byte 1-4 (a tick) | failed [held only under H-RACE] |
| FF2-OTHER | any other | printed |

**T2** (`begin_draws = "tri"`):

| outcome | rule | prediction |
|---|---|---|
| T2-SAME | 0x02400000 (T's read, E1193; the 3:22 at K 2) | **held** [HW once; H-TRI, H-FIRST] |
| T2-34 | 0x02000010 (the triangle's 3:4, X's variant) | failed [infer; H-RACE allows it] |
| T2-KEEP | M1 | failed |
| T2-OTHER | any other | printed |

**TF2** (`begin_draws = "tri,fill"`):

| outcome | rule | prediction |
|---|---|---|
| TF2-SAME | 0x02400000 (TF's read, E1195) | **held** [HW once; H-TRI, H-FIRST] |
| TF2-FILL | 0x08000010 (the fill's 3:4 at K 8) | failed [infer; H-RACE allows it] |
| TF2-KEEP | M1 | failed |
| TF2-OTHER | any other | printed |

**TT** (`begin_draws = "tri,tri"`; new; K: 1, the first triangle to 7, the second's 3:22 at 8):

| outcome | rule | prediction |
|---|---|---|
| TT-LAST | 0x08400000 (or its 3:4 variant 0x08000010) | **held** [infer, H-TRI] |
| TT-FIRST | 0x02400000 (or 0x02000010) | failed [infer; held under H-FIRST] |
| TT-KEEP | M1 | failed |
| TT-OTHER | any other | printed |

**F3** (`begin_draws = "fill"`; F's and LF's list, the third read):

| outcome | rule | prediction |
|---|---|---|
| F3-KEEP | M1 (as LF, E1200, and FF) | **held** [infer, H-TRI] |
| F3-TICK | 0x01000000 (as F, E1187) | failed [infer; H-RACE allows it] |
| F3-FILL | 0x02000010 (the fill's 3:4 at K 2) | failed |
| F3-OTHER | any other | printed |

**What N1's reads settle.** FF2-KEEP, T2-SAME, TF2-SAME together: the sim's rule is met for FF, T
and TF, and fills leave the word on a second read. TT-LAST against TT-FIRST: the last triangle
since the plant writes, or only the first after a load. F3-KEEP: one fill keeps the plant 2 of 3
(F the stray); F3-TICK: 2 of 3 the other way, and the one-fill list stays unknown. Any repeat
failing with a word H-KC names (T2-34, TF2-FILL, FF2-FILL, F3-TICK): H-RACE, printed with K; the
sim keeps those lists unknown.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop N1. PLANT failed: the row's outcomes read cannot
tell (the row runs, printed). DR failed (a retry adds a reset and draws): cannot tell. DK failed:
the K-naming outcomes (FF2-FILL, T2-34, TF2-FILL, TT-*, F3-TICK, F3-FILL) cannot tell; the -KEEP
and -SAME outcomes still stand. B failing: stop for the user.

**Risk.** As FF, T, TF, F (E1187, E1191, E1193, E1195): quiet, no kick, no gate [HW]. New: two
triangles in one health call, both stock client draws; a triangle after a triangle runs in every
recovery's retry already [HW].

### 3.3 Read stage F2b (N1, last, no plant)

crumb3 as §3.2, one job, `begin_draws = "fill"`, right after F3, whose end draws are the default
(fill,tri after the disarm, K from 2). F2's history again: under H-KC the word before F2b's fill is
F3's end triangle's 3:22 at K 5.

| outcome | rule | prediction |
|---|---|---|
| F2b-SAME | 0x05400000 (F2's read, E1196) | **held** [HW once; H-KC, H-TRI] |
| F2b-TICK | 0x01000000 | failed [infer; H-RACE] |
| F2b-FILL | 0x02000010 | failed |
| F2b-OTHER | any other | printed |
| F2b-QUIET | snap9 BIF_FAULT 0 | **held** |

**Cannot tell.** J1 not DONE. DR or DK failed. F3's end health not exact at try 1, or F3's end KC
not 10 (the end triangle's K is then not 5): F2b-SAME cannot tell.

### 3.4 Session N2, stage LF2: land after one fill (LF again; last in N2)

Image **land**, its 16 words (n3i §3.4) byte for byte; `begin_draws = "fill"`; jobs as LF (job 1
the emit, the tick running; job 2 command 6, no kick). land writes none of attributes 0-2.

| outcome | rule | prediction |
|---|---|---|
| LF2-SA1 | post sa1 = M1 | **held** [HW once, E1200; H-TRI] |
| LF2-SA0 | post sa0 = 0x00000002 | **held** [HW once, E1200] |
| LF2-SA2 | post sa2 top byte 0x01, bits 23:0 < 400000, != 0x061a70 | **held** [HW once, E1200] |
| LF2-TICK | post sa1 = 0x01000000 (F's word) | failed [infer; H-RACE] |
| LF2-AOTHER | any other sa0, sa2 | printed |
| LF2-PAGE | job 2 not done; K5 BIF_FAULT CID 15 at the H-SA0 rule's page (§0.4) | **held** |
| LF2-EARLY0 | the same at page 0 | **held** [HW once; H-SA0 with LF2-SA0, H-HIST] |
| LF2-EARLY1 | the same at post sa1's page | failed |
| LF2-SERVE | job 2 done | failed [HW against: E1176, E1178, E1183, E1185, E1198, E1200] |

**What LF2 settles.** With LF2-SA1, -SA0 and -SA2: LF's triple meets the two-read rule, and the sim
can know that one fill before land leaves (2, M1, a timer word) and a page-0 stop. LF2-TICK with
F3-KEEP: the one-fill list is a race.

**Cannot tell.** J1 not DONE: stop. PLANT failed: LF2-SA1 and the page outcomes cannot tell. DR or
DK failed: cannot tell for the -SA outcomes.

**Risk.** LF's, LM's, LC's (E1176, E1178, E1198, E1200): the runner's stop (rc 4), the kit's reset
and strict health recovered it every time [HW]. It ends in the stop, so it is last in N2.

### 3.5 Session N3, stage LT: land after a triangle alone (last in N3)

land as §3.4; `begin_draws = "tri"` (T's list). Under H-KC and LC's triple, the triangle's 3:22
entry writes (pa0 0, pa1 0x02400000, pa2 a timer sample).

| outcome | rule | prediction |
|---|---|---|
| LT-SA1 | post sa1 = 0x02400000 | **held** [HW once, T E1193; H-TRI] |
| LT-TRIPLE | post sa0 = 0; sa2 top byte 0x01, bits 23:0 < 400000 | **held** [infer, LC's triple] |
| LT-ONE | post sa0 = V0 and sa2 = V2 (the triangle writes attribute 1 alone) | failed [infer] |
| LT-AOTHER | any other sa0, sa2 | printed |
| LT-PAGE | job 2 not done; K5 BIF_FAULT CID 15 at the H-SA0 rule's page (§0.4) | **held** |
| LT-HIST | the same at page 0 while post sa0 = V0 | failed [infer; held under H-HIST] |
| LT-SERVE | job 2 done | failed |

**What LT settles.** LT-TRIPLE: a triangle writes attributes 0-2 as one entry's (pa0, pa1, pa2),
and LC's page 0 was the triangle's pa0 under H-SA0 [infer]; H-SA0 and H-HIST agree there (page 0).
LT-ONE: only attribute 1 is written, so LC's sa0 = 0 came from LC's fill; then LT-PAGE (page
0x02400000) against LT-HIST (page 0) is the one no-rebuild split of H-SA0 from H-HIST.

**Cannot tell.** As §3.4. LT-ONE with 0x02400000 mapped (no fault at that page): LT-PAGE and
LT-HIST cannot tell; the fault page is printed against post sa13.

**Risk.** As LF2; a triangle before land is LC's sequence without the fill [HW, E1176, E1178].

### 3.6 Session N4, stage LFF (optional, decision D; last in N4)

land as §3.4; `begin_draws = "fill,fill"`. LFF-SA1 M1 **held** [HW once, FF]; LFF-SA0 sa0 = 2
**held** [infer, LF: the last fill's write]; LFF-V0 sa0 = V0 failed [infer]; LFF-PAGE (the H-SA0
rule) **held**; LFF-HIST (page 0 with sa0 = V0) failed [held under H-HIST]. It is a second chance
for the H-SA0/H-HIST split (if two fills leave sa0 = V0) and reads fill,fill's sa0 and sa2.

## 4. The rebuild alternative (decision E (b) or (c))

Two images, each a fork commit on r42-kernel with KUnit red then green, the Mac shim, a cachix
build (about 45 min unattended), install, a one-shot boot with the user's OK, the srcversion check
and a build control (W again):

- **crumbz**: crumb3 without its two `douta` of V0 and V2 (`tim` kept). Every quiet read row then
  reads sa0 and sa2 as the draws left them, with no stop: N1's six reads would answer LT's and
  LFF's sa0/sa2 questions too, and test H-KC's triple on every list.
- **landq**: land plus `douta` of 0x005d2000 to attribute 0 and M1 to attribute 1 (no draws, no
  plant): both unmapped, sa0 above sa1. "sa0 first" (H-SA0) predicts page 0x005d2000, "the BIF
  keeps the last" and "the lowest page" predict 0x005d1000. Only this splits the order rivals of
  §0.4.

Not recommended this round: N1-N3 need no boot, and LT-ONE (if it happens) splits H-SA0 from
H-HIST without one. crumbz is the better first rebuild if the user wants one: it turns every
later read row into a reader of attributes 0-2.

## 5. Offline first (no laptop)

- **O1 (records).** Round 44 is folded (E1188-E1200 on main 7a0abcd4). §0.1's table and §0.2's
  H-KC arithmetic go into this round's fold notes and Q128's next paragraph as [infer]; no new
  record from them (no new measurement).
- **O2 (sim in sync).** `attr1_now` stays as the user set it until N1's second reads are folded.
  Two notes for that fold: (i) the draws list is cleared at a reset today, but F2 reads a word the
  end draws left across the begin reset (§0.2), so a list's effect must be keyed by the draws since
  the last *write*, with resets in between; (ii) the same list gives a different K at the begin
  (from 1) and the end (from 2), so a known word belongs to (list, K base), not to the list alone.
  Model nothing H-KC only infers; model a list's word only where two reads agree.
- **O3.** K9 with its tests and the scorer for each row, on round 44's kept stages as fixtures;
  the kit's mock: `tri,tri`, an unplanted read after a non-default end, LT's stop at the page of
  sa0 or sa1. No fork change, no shim run.

## 6. Build needs, run order, laptop time

**Build.** None on the fork or cachix, no boot. resgx545 branch `r45-n3j` off main 1c8dc10e: K9
with tests (red, then green) first; scorers for the plant, read, F2b, LF2, LT (and LFF) rows (the
PLANT pairing, DR and DK included); sessions N1 (`r45j1`: wa, ff2, wb, t2, wc, tf2, wd, tt, we,
f3, f2b), N2 (`r45j2`: wg, lf2), N3 (`r45j3`: wh, lt), optional N4 (`r45j4`: wi, lff), frozen with
srcversion 079DD0D13F231EEAC52FE0F and the data pin at resgx545-data ebfeaa775 or later (round
44's kept stages as the scorer's test attempts); `run_all`; check. Firmware-page writes: mark,
crumb3 and land, all round 44's bytes on this module; each needs the user's OK before the run.

**Recovery.** Every planned stop so far was recovered by the runner's stop and the kit's reset
(round 44: LM, LF; round 43: V, F) [HW]. A failed reset (rc 13 or 5) means the user's ordinary
reboot to the default entry.

**Stop conditions.** J1 not DONE: CANNOT TELL, stop that session. W-FAULT, or B failing in a read
row: stop for the user. Any fault other than the land rows' planned stop: stop for the user.

**Run order.** Offline: K9 (tests red, then green), scorers, sessions, mock, `run_all`, check. Then:

1. N1 (quiet; ends with rc 0 after f2b's end draws);
2. N2 (ends in LF2's planned stop);
3. N3 (ends in LT's planned stop);
4. N4, if decision D (b).

N1 first: no planned stop, and F3's outcome frames LF2's sa1 reading.

**Laptop time.** Round 44's N1 ran 9 stages in 3 min 20 s (00:56:24 to 00:59:44), N2 and N3 about
45 s each, stop and recovery included [HW, kernel log stamps]. N1 here (11 stages) about 4-5 min;
N2 and N3 about 1 min each (N4 one more); with staging, scoring and the health draw after each
session, about 20 min attended (25 with N4), no build time.

## 7. Rejected alternatives

- **More FT reads.** Eight reads already agree on the word up to X's variant [HW]; another adds
  nothing to the rule's count that the rows above do not.
- **Lists with three triangles or tri,fill,tri.** TT alone splits H-TRI from H-FIRST; a third
  triangle only repeats that split at a higher K.
- **land after every N1 list** (to read sa0 and sa2 each time). Each would end in a stop; LT and
  LF2 (and LFF) read the two lists that matter for land's page. crumbz (§4) is the clean way.
- **An unplanted repeat of F (no plant, one fill, after a `none` end).** The word before it would
  be the previous read's own word, not M1, so a kept word could not be told from a rewrite; F2b
  asks the unplanted question where the word before is known under H-KC.
- **Reading K from our own task (a ring_e1 event log)** alongside the read. It needs another
  image and blob on the module: a rebuild for a number the kernel already prints (K9).
- **A kick or a gate in the read rows.** The kick pass faults at sa13, then the EDM stalls
  [HW, E1187]: a stop with nothing read about attribute 1.

## 8. User decisions (one at a time)

- **A. Row 1's reads (N1):** (a) FF2, T2, TF2, TT, F3 and F2b (recommended: the three second reads
  the sim's rule needs, TT the one split of H-TRI from H-FIRST, F3 the tie-break of F against LF,
  F2b the check of H-KC's carried word, all quiet, about 5 min); (b) the second reads only, FF2,
  T2 and TF2; (c) the second reads and TT.
- **B. K9 (the command count from `ccb_sent`, the DK control):** (a) include, tests first
  (recommended: it ties each word to its entry in the scorer, and a miscounted K reads cannot tell
  instead of a false verdict); (b) skip; H-KC is checked by hand at the fold from the kernel logs.
- **C. Row 2's land rows:** (a) LF2 and LT, each in its own session (recommended: LF2 meets the
  two-read rule for LF's triple and page; LT reads a triangle's triple, checks LC's page 0 on this
  module, and is the one no-rebuild split of H-SA0 from H-HIST if a triangle leaves sa0 = V0);
  (b) LF2 only; (c) LT only; (d) skip row 2.
- **D. Row LFF** (land after fill,fill, its own session N4): (a) skip (recommended: LF2 and LT
  answer the page question unless both leave sa0 below a page); (b) include, last.
- **E. A rebuild:** (a) none this round (recommended: every row above runs on the installed
  module); (b) crumbz only (§4: every quiet read also reads sa0 and sa2); (c) crumbz and landq
  (landq splits the order rivals of land's page).
- **F. Order:** (a) N1, then N2, then N3 (then N4) (recommended: the quiet session first, and F3
  frames LF2); (b) the land sessions first, then N1.

## 9. Addendum: the rebuild rows (decision E (c))

Status: written 2026-11-24 after the user's decisions E (c) (build crumbz and landq, §4) and F (a)
(N1-N4 run on the installed module while cachix builds; then a one-shot boot, a W control row and
the crumbz and landq sessions). §0-§8 are unchanged. The predictions below are frozen as written,
before N1-N4 run; every reading is **[infer]** unless an E number or a kept stage is named. Paths:
`F45` = fork worktree `/Volumes/linux/linux-sgx-r45`, branch r45-kernel (r42-kernel plus the two
images; r45-red its stub twin), `drivers/gpu/drm/gma500/sgxfive/`.

### 9.0 The two images (our own PDS programs, assembled with pds-asm; no firmware bytes)

- **crumbz** (17 dwords, `F45/sgx_own_pds.h`): crumb3's 12 data dwords unchanged (3 rows, control
  word 0x01800100, the arm fills U0, V0 and V2, _FILLV 1, so its data rows are crumb3's word for
  word) and crumb3's program without its two `douta` (V0 to attribute 0, V2 to attribute 2): T1
  `tim` 0x000, T2 `tim` 0x200, the `doutu`, T3 `tim` 0x005a3305, `halt`. It writes no attribute:
  sa0-sa2 after the emit are what the bank held before it. V0 and V2 sit in its data unread.
- **landq** (18 dwords): land's 12 data dwords with its unused third row holding Q0 0x005d2000
  (ds0[4]), M1 0x005d1000 (ds0[5]) and the `douta` controls of attributes 0 (ds1[4] = 0) and 1
  (ds1[5] = 0x100); land's two marker `douta` (Ma to 24, Mb to 26), then Q0 to attribute 0 and M1
  to attribute 1, then land's `doutu` and `halt`. No `tim`: the tick keeps running, as land's. The
  arm fills U0 only (_FILLV 0, dwords 4 and 5 are Ma and Mb). Q0's page 0x5d2 is next to mark's
  0x5d1 and 0x5d3, below 0x10000000 where no REV1 heap lies, as mark's markers [infer]; M1's page
  faulted in LM and V (E1198, E1185) [HW].

### 9.1 Rows, one line each

| row | session | question | image | draws before the read |
|---|---|---|---|---|
| WJ | N5 | build control on the new module, and the plant before ZN | mark | default |
| ZN | N5 | crumbz writes none of sa0-sa2: (V0, M1, V2) | crumbz | none |
| WK | N5 | plant M1 | mark | default |
| ZT | N5 | a triangle's triple (LT's question without the stop) | crumbz | tri |
| WL | N5 | plant M1 | mark | default |
| ZFT | N5 | fill,tri's triple (LC's, E1176, E1178) on this module | crumbz | fill,tri |
| WM | N5 | plant M1 | mark | default |
| ZF | N5 | one fill: does the fill or land's tick give LF's sa0 2 and sa2? | crumbz | fill |
| WN | N5 | plant M1 | mark | default |
| ZFF | N5 | fill,fill's sa0 and sa2 (LFF's question without the stop) | crumbz | fill,fill |
| WO | N5 | plant M1 | mark | default |
| ZTF | N5 | tri,fill: does the fill rewrite sa0 and sa2 and keep sa1? | crumbz | tri,fill |
| WP | N5 | plant M1 | mark | default |
| ZTT | N5 | tri,tri's triple at K 8 (H-TRI) or 2 (H-FIRST) | crumbz | tri,tri |
| Q | N6 | landq: which of two unmapped words, sa0 above sa1, faults | landq | none |

Every row: blob `emitsb_sbc43s`, `form=sbc43`, `pdsat=fw14`, as §1. The W stages are §3.1's row W
byte for byte. crumbz and landq are new bytes on the firmware page (each needs the user's OK).

### 9.2 Common rules

As §3: arm `slots=0x1 entry=0 pds=<img> pdsat=fw14 form=sbc43`, `#limit 0`, flagged, on_stop
"end"; job 1 = command 1, slots and dwords filled with 0xdeadc0de first, `"ticks": true`, 200 ms,
no kick. U0 = 0x080401ef; V0 0x32004000, V2 0x32002000, the builder confirms them at the freeze.
Controls as §3 (PG, T0, B, DR, DK, E0, J1, K5, PLANT for every Z row) and two more:

- **SV** (session N5, scored once at the freeze and at the run): the loaded module's srcversion is
  the r45-kernel build's (§9.6), installed and loaded alike. SV failing: N5 and N6 do not run.
- **ZN** (session-scoped for N5's Z rows): ZN-SAME held. When ZN fails, every sa0/sa2 outcome of
  ZT-ZTT reads cannot tell (crumbz itself writes them); the sa1 outcomes still stand.

Words: post sa0, sa1, sa2 of job 1's record. "timer" = top byte 0x01, bits 23:0 < 400000 and
!= 0x061a70 (LT-TRIPLE's and LF2-SA2's rule). The H-KC triple of an entry = (its pa0, its pa1 at
the §0.2 K, a timer word) in (sa0, sa1, sa2). Two readings of LF's (2, M1, 0x01049b60) (E1200),
which §0.2 leaves open:

- **R-DRAW.** The fill's events rewrite sa0 and sa2 (to a tick-like pa0 2 and a timer word) and
  leave sa1; land's own running tick adds nothing. crumbz then reads LF's shape after a fill.
- **R-TICK.** land's tick, still running after the emit (land has no `tim`), wrote sa0 and sa2;
  the fill wrote nothing. crumbz stops the tick at T1, so it reads the plant's V0 and V2.

§3.6 froze LFF-SA0 under R-DRAW ("the last fill's write"); the Z rows predict R-DRAW too, and
R-TICK is the alternative each fill row names.

### 9.3 Plant stages WJ-WP (N5) and the build control

§3.1's table and rules unchanged (W-SA1, W-SA13, W-QUIET **held**, W-FAULT failed), on the new
module. WJ is also the **build control**: its 21 words of mark are round 42's bytes (the rebuild
touches no other image), so every W outcome is predicted as in E1184-E1199 [HW, 8 runs on
079DD0D1]. WJ failing any outcome: stop N5 for the user (the rebuild changed the arm path or the
mark bytes), no Z row runs.

### 9.4 Read stages ZN-ZTT (N5, crumbz, each right after its plant)

Image **crumbz**, one job, `own_gate = "none"`, `end_draws` default (fill,tri). Common: Z-QUIET
(snap9 BIF_FAULT 0) **held** [infer: crumbz keeps crumb3's three `tim`, and every crumb3 row was
quiet with the same pre-emit bank, E1189-E1196 HW]; Z-FAULT (a BIF fault after job 1) failed.

**ZN** (`begin_draws = "none"`; LM's and V's history, E1198, E1185):

| outcome | rule | prediction |
|---|---|---|
| ZN-SAME | post sa0 = V0, sa1 = M1, sa2 = V2 | **held** [HW for land, landv: E1198, E1185] |
| ZN-OTHER | any other | failed: control ZN fails (§9.2) |

**ZT** (`begin_draws = "tri"`; the triangle's 3:22 at K 2):

| outcome | rule | prediction |
|---|---|---|
| ZT-SA1 | sa1 = 0x02400000 | **held** [HW T E1193; H-TRI, H-FIRST] |
| ZT-TRIPLE | sa0 = 0, sa2 timer | **held** [infer, H-KC's triple, LC's] |
| ZT-ONE | sa0 = V0, sa2 = V2 (a triangle writes attribute 1 alone) | failed [infer] |
| ZT-AOTHER | any other sa0, sa2 | printed |

**ZFT** (`begin_draws = "fill,tri"`; the triangle's 3:22 at K 4):

| outcome | rule | prediction |
|---|---|---|
| ZFT-SA1 | sa1 = 0x04400000 (or X's 0x04000010) | **held** [HW, eight reads, E1189 and n3i §0.1] |
| ZFT-TRIPLE | sa0 = 0, sa2 timer | **held** [HW under land twice: LC, LC2, E1176, E1178] |
| ZFT-ONE | sa0 = V0, sa2 = V2 | failed [infer] |
| ZFT-AOTHER | any other sa0, sa2 | printed |

**ZF** (`begin_draws = "fill"`; F's, LF's and F3's list):

| outcome | rule | prediction |
|---|---|---|
| ZF-SA1 | sa1 = M1 | **held** [HW LF E1200; H-TRI] |
| ZF-TICK1 | sa1 = 0x01000000 (F, E1187) | failed [infer; H-RACE allows it] |
| ZF-DRAW | sa0 = 0x00000002, sa2 timer (LF's shape) | **held** [infer, R-DRAW] |
| ZF-PLANT | sa0 = V0, sa2 = V2 | failed [infer; held under R-TICK] |
| ZF-AOTHER | any other sa0, sa2 | printed |

**ZFF** (`begin_draws = "fill,fill"`):

| outcome | rule | prediction |
|---|---|---|
| ZFF-SA1 | sa1 = M1 | **held** [HW FF E1191; H-TRI] |
| ZFF-DRAW | sa0 = 0x00000002, sa2 timer | **held** [infer, R-DRAW; §3.6's LFF-SA0] |
| ZFF-PLANT | sa0 = V0, sa2 = V2 | failed [infer; held under R-TICK; LFF-V0's shape] |
| ZFF-AOTHER | any other sa0, sa2 | printed |

**ZTF** (`begin_draws = "tri,fill"`; the triangle's 3:22 at K 2, then the fill):

| outcome | rule | prediction |
|---|---|---|
| ZTF-SA1 | sa1 = 0x02400000 | **held** [HW TF E1195; H-TRI, H-FIRST] |
| ZTF-DRAW | sa0 = 2, sa2 timer (the fill rewrites sa0 and sa2 only) | **held** [infer, R-DRAW] |
| ZTF-TRIPLE | sa0 = 0, sa2 timer (the triangle's triple kept) | failed [infer; held under R-TICK] |
| ZTF-AOTHER | any other sa0, sa2 | printed |

**ZTT** (`begin_draws = "tri,tri"`; K: the second triangle's 3:22 at 8, as TT):

| outcome | rule | prediction |
|---|---|---|
| ZTT-LAST | sa1 = 0x08400000 (or 0x08000010) | **held** [infer, H-TRI] |
| ZTT-FIRST | sa1 = 0x02400000 (or 0x02000010) | failed [infer; held under H-FIRST] |
| ZTT-TRIPLE | sa0 = 0, sa2 timer | **held** [infer, H-KC's triple] |
| ZTT-ONE | sa0 = V0, sa2 = V2 | failed [infer] |
| ZTT-AOTHER | any other sa0, sa2 | printed |

**What N5 settles.** ZN-SAME: crumbz reads the bank unwritten, so every Z row's sa0 and sa2 are the
draws'. ZT-TRIPLE and ZFT-TRIPLE: a triangle's event writes attributes 0-2 as one entry's (pa0,
pa1, pa2), H-KC's triple, on this module; ZT-ONE or ZFT-ONE: attribute 1 alone. ZF-DRAW against
ZF-PLANT splits R-DRAW from R-TICK (with ZFF and ZTF as second and third chances); ZF-PLANT also
answers §3.6's H-SA0/H-HIST question for land: under R-TICK a fill leaves sa0 = V0, and LF's
page-0 stop came from land's own tick, not from the draws. ZTT-LAST against ZTT-FIRST repeats N1's
TT split with the triple read beside it. Each Z row is a second read of its N1-N4 twin (T, FT,
F, FF, TF, TT) for sa1 under the sim's two-read rule [infer: the image differs, the bank does not].

**Cannot tell.** As §3.2 (J1 not DONE: stop N5; PLANT failed: the row reads cannot tell; DR
failed: cannot tell; DK failed: the K-naming outcomes ZT-SA1, ZFT-SA1, ZTF-SA1, ZTT-LAST,
ZTT-FIRST, ZF-TICK1 cannot tell; B failing: stop for the user). ZN failed: the sa0/sa2 outcomes
of every Z row cannot tell. A timer-shaped sa2 with sa0 neither 0 nor 2 nor V0: -AOTHER, printed
with the entry H-KC names for it.

**Stop conditions.** Z-FAULT (any BIF fault in a Z row): the row's read stands (job 1's record is
written before the tick pass), the session stops for the user. WJ failing: stop before ZN.

**Risk.** crumb3's (E1189-E1196): quiet, no kick, no gate [HW]. New: after the emit sa0 may hold 0
or 2 (unmapped) with the tick stopped by T1-T3; before the emit the same banks were quiet under
crumb3 (FT, T, TF) [HW], and LC's stop needed land's running tick [infer].

### 9.5 Session N6, stage Q: landq, no draws, no plant (one stage)

Image **landq**; `begin_draws = "none"`; jobs as LM (job 1 the emit, the tick running; job 2
command 6, no kick). landq writes Q0 0x005d2000 to attribute 0 and M1 0x005d1000 to attribute 1
in the emit itself, before its `doutu`; nothing else writes them before job 1's read.

Under §0.4's rules, with both words unmapped and sa0 above sa1 [infer for each]:

- **H-SA0** (the tick pass reads sa0, then sa1; the first unmapped one faults): page 0x005d2000.
- **"sa1 first, the BIF keeps the last fault"** (§0.4's order rival): sa1 faults, then sa0, the
  last kept: page 0x005d2000, the same as H-SA0. Q does not split this rival from H-SA0.
- **"the lowest faulting page"** (§0.4): page 0x005d1000.
- **"sa0 first, the BIF keeps the last"**: page 0x005d1000 here; already falsified by LF (it gives
  M1's page there, LF stopped at page 0, E1200) [HW against].

| outcome | rule | prediction |
|---|---|---|
| Q-WRITE | job 1 done; post sa0 = 0x005d2000, sa1 = 0x005d1000 | **held** [infer; LV E1183] |
| Q-SA0 | job 2 not done; K5 BIF_FAULT CID 15 at 0x005d2000 (0x005d200f) | **held** [infer, H-SA0] |
| Q-LOW | the same at page 0x005d1000 (0x005d100f) | failed [infer; held under "lowest page"] |
| Q-OTHER | a fault at any other page (sa2's, sa13's, page 0) | printed |
| Q-SERVE | job 2 done, no fault | failed [HW against: E1176-E1200's land stops] |

**What Q settles.** Q-SA0: when both words fault, sa0's page is the one the BIF keeps (H-SA0 or
"sa1 first, the last kept"; one fault register cannot split those two). Q-LOW: the lowest page,
and H-SA0's LF and LC readings need another reason for page 0 (page 0 is the lowest of every pair
read so far). Q-OTHER: a third attribute is read before sa0 and sa1, printed against post sa2 and
sa13.

**Cannot tell.** J1 not DONE, or Q-WRITE failed (landq's words not in sa0 and sa1): every page
outcome cannot tell. 0x005d2000 mapped (a fault at 0x005d1000 with Q-WRITE held cannot tell
"lowest" from "sa0 mapped"): printed; Q-LOW then reads cannot tell unless a later row plants Q0
alone. DR or DK failed: not scored here (no draws), printed.

**Risk.** LM's and V's (E1185, E1198): the runner's stop (rc 4), the kit's reset and strict health
recovered every land stop so far [HW]. It ends in the stop, so it is N6's only stage.

### 9.6 Build, run order, laptop time

**Build** (done before N1-N4 end, unattended): fork r45-red (stubs) and r45-kernel (the images) off
r42-kernel, KUnit red then green on the Mac shim, the cachix series check and module build
(`kernel39c/deliver-cachix.sh` send, start, wait, fetch). The kit needs `pds=crumbz|landq` in its
arm lines (as round 42's ff6e5c3d did for mark and landv) and the Z and Q scorers; the sessions
are frozen with the new srcversion (SV).

**Run order** (decision F (a)):

1. N1-N4 on the installed module 079DD0D13F231EEAC52FE0F (§6), while cachix builds;
2. install the r45-kernel module, the one-shot boot (the user's OK), the srcversion check
   (`boot-test-kernel.sh`, `test-session.sh`, gma500 srcversion against the installed one);
3. N5 (`r45j5`: wj, zn, wk, zt, wl, zft, wm, zf, wn, zff, wo, ztf, wp, ztt; quiet, ends rc 0);
4. N6 (`r45j6`: q; ends in the planned stop).

N5 before N6: N5 has no planned stop, and ZF/ZFF frame how Q's page compares with LF's.

**Laptop time.** Install and boot about 10 min with the check. N5 (14 stages) about 6 min at round
44's rate (§6: 9 stages in 3 min 20 s); N6 about 1 min. With staging, scoring and the health draw
after each session, about 20 min attended after the boot.
