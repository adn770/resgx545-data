# N3g: where sa13's page comes from, bit 10 with bits 1:0 = 2, and `land` with V0/V2
(design note, not built, not run)

Status: a design for the lead to bring to the user as **flagged decisions** (§8). Nothing here is
built, committed, staged or run; no laptop, cachix or fork was touched. Tags: **[HW]** measured,
with its E number (a reading taken from a kept page of that record's session, printed and not
scored, says so); **[infer]** everything else, including our reading of the firmware dataflow
spec and of the fork's source.

Paths: `R` = `/Users/jtorra/src/resgx545` (main e6201508, records to E1178), `F` = fork
`/Volumes/linux/linux-sgx-r40` at r40-kernel 423b436e7f80, `drivers/gpu/drm/gma500/sgxfive/`
(read with `git show r40-kernel:`), `C` = `/Users/jtorra/src/scratch/resgx545/closing29`. The
laptop runs module srcversion 83FBFD860D4E0D4CE691F48 (fork 423b436e7f80), with the 18-word
`form=` list and the images v1, crumb, halt, crumb3 and land (`F/sgx_own_regs.h`,
`F/sgxfive_owntask.c:600-614`). `0x402` is **not** in the list.

## 0. Where Q128's bit 10 stands

- Bits 1:0 of the sideband decide the start from our task: 0 never starts, 1 faults at #14's
  page + 0x10, 2 or 3 run it to done; bits 6 and 11 are not needed (E1171, over E1158 and
  E1162-E1172) [HW].
- With bit 10, alone (0x403, E1175) or in 0xc43 (E1174), a later job of our own entry 0 reads
  the EDM's own sa0-sa31 equal to the started entry's post words: sa12-sa27 = its pa0-pa15, sa1
  and words of sa3-sa10 changed, sa0 and sa2 = V0/V2 with crumb3 [HW]. With 0x843 nothing changes
  and the gate passes (E1173) [HW].
- The next fill (E1172, E1174, E1175) and the next triangle (E1177) fault through the EDM's list
  (CID 15) at page 0x00043000, the post sa13, until a reset [HW]. In X and Y control B already
  read the fault in snap9, before the gate (E1174, E1175) [HW]; B11 and T, one job and no kick,
  read BIF_FAULT 0 there (E1172, E1177) [HW]. Which pass of X's faulted is not read.
- `land` + 0xc43 (no V0/V2, tick running): LC-EARLY, BIF_FAULT 0x0000000f (page 0) after job 1,
  the tick stopped, job 2 never served (E1178, E1176) [HW]. Post sa0 0, sa2 0x01030b00 (H3:
  0x0104b95b) [HW, E1178, E1176].
- That sa13's 0x43000 comes from pa1 is [infer] (E1178 "What it does not show"): the post pa may
  be stale across resets (E1177: land's markers from H3 in T's pa12 and pa14) [HW].

### 0.1 What the kept pages already show about staleness [HW, printed, kept pages]

Read offline from the kept `*.own_res.json.gz` of L (E1163), B8 (E1168), B11 (E1172), X and C
(E1173, E1174), Y (E1175), H3 (E1176), T (E1177) and LC2 (E1178), dwords 160-223:

- **The odd pa never changed** from L (2026-11-19 23:04) to LC2 (2026-11-21 07:38): pa1
  0x00043000, pa3 0x01555620, pa5 0, pa7 0x03c3cdac, pa9 0xdc531a54, pa11 0x5d50716f, pa13
  0x82e151b5, pa15 0x11b5d77a, in all nine rows, across every reset between them.
- **The even pa follow what our rows wrote**: L's pa0/pa2/pa4/pa6 (0, 0x3727c5ac, 0, 0xd0030000)
  became V0/V2 every fourth word after B1 and B8 (0x003, 0x002, E1164, E1168) and stayed so in
  B11 attempt 1; H3's Ma/Mb stayed in pa12/pa14 through T and LC2; Y's V0 in sa4 and sa8 stayed
  into H3, T and LC2. Some writer we did not run also put 0x3 in pa0 and 0x32411000 in pa2 or pa4
  (B11 attempt 2, X, H3, LC2).
- **With bit 10 the bank's low words follow the same store**: LC2's post sa4 = V0, sa6 = V2,
  sa8 = V0, sa10 = V2 are Y's replicated values, though land writes no V0 or V2; X (before Y)
  read floats there.

[infer] from these: one attribute store holds the emitted program's output; the started entry's
pa k is its attribute 12 + k (E1163's two points, now nine rows of the same pattern); bit 10
makes the issuer's sa n read attribute n of the same block (n3f's H-REBASE, now **H-BLOCK**);
words nobody writes keep their value across resets. Then sa13 = attribute 13 = pa1 =
0x43000, a word no row of ours wrote, and the fault page follows it. The rival, **H-COPY**: bit
10 copies only the started entry's pa0-pa15 into sa12-sa27, and sa1 and sa3-sa11 come from
somewhere else. The kept pages cannot tell these apart: no row wrote an odd attribute. Row M can.

## 1. Rows, one line each

| row | question | blob | image | form | build |
|---|---|---|---|---|---|
| C | control: the build reproduces E1173 | `emitsb14s` | crumb3 | fw14 | yes (boot) |
| M | sa13's source: markers in attr. 13, 1 | `emitsb_sbc43s` | **mark** (new) | sbc43 | yes |
| S | M's marker kept in pa1? (C again) | `emitsb14s` | crumb3 | fw14 | runs on it |
| Q | sb402: bit 10 with bits 1:0 = 2 | **`emitsb_sb402s`** (new) | crumb3 | **sb402** (new) | yes |
| LV | `land` + V0/V2: early stop, heal | `emitsb_sbc43s` | **landv** (new) | sbc43 | yes |

Rows 1-3 of the brief: Q is row 1, LV row 2, M with S row 3. Row 4 of the brief is S plus kit
change K5 (§4).

## 2. What the build holds (one fork build, one one-shot boot)

Rows Q, M and LV each need the module: a new `form=` word (Q) or a new image (M, LV). One build
carries all three; C and S need nothing new but run on it.

**Fork branch `r42-kernel` off r40-kernel 423b436e7f80** (`F/sgx_own_regs.h`,
`F/sgx_own_pds.h`, `F/sgxfive_owntask.c`, the KUnit suite):

1. `form=` list + **sb402** = 0xfb20b08000808184 (sideband 0x402; sb403's word 0xfb20b08000c08184
   with bit 22 clear, the field placement of n3e §0). Optional, decision F: **sb400** =
   0xfb20b08000008184 (word only, no row).
2. Image **mark**: crumb3 plus two `douta` from crumb3's unused third row. Data dwords 0-7
   crumb3's (U0, U1 0, U2 0, ctl 0, V0, V2, ctl 0x200, T3 0x005a3305; FILLV 1, so the kernel fills
   V0 and V2 at dwords 4 and 5 as crumb3); dword 8 = ds0[4] = **M13 0x005d3000**, dword 9 = ds0[5]
   = **M1 0x005d1000**, dword 10 = ds1[4] = 0x00000d00 (douta control, attribute 13), dword 11 =
   ds1[5] = 0x00000100 (attribute 1). Program: crumb3's T1, its two `douta`, then `movs douta,
   ds0[4], ds1[4], ds0[4], ds0[4]` (M13 to attribute 13) and `movs douta, ds0[5], ds1[5], ds0[5],
   ds0[5]` (M1 to attribute 1), then crumb3's T2, `doutu`, T3, `halt`: 12 + 9 = 21 dwords at
   [0x100, 0x154). Three rows and control 0x01800100, #14's own, as every DONE row [HW, E1162,
   E1172]. The tick stops at T3 as in X, Y and T [HW, E1174, E1175, E1177].
   - Marker values: pages below 0x10000000, where no REV1 heap lies (`R/doc/specs/
     boot_sequence.md` §4: the lowest is 3D parameters at 0x10000000, per context) [infer], so
     unmapped in the EDM's list like 0x43000 and page 0, which faulted [HW, E1174, E1178]; 0x5d
     marks "ours", page 0x5d3 = 13, 0x5d1 = 1; neither appears in any kept page (§0.1).
   - The second marker is decision B: M1 (recommended), 0 into attribute 14, or none.
3. Image **landv**: land with V0/V2. Data dwords 0-3 U0, U1 0, U2 0, ctl 0 (attribute 0); 4-7
   V0, V2 (FILLV 1, kernel-filled at 4 and 5), ctl 0x200, ctl 0x1800 (attribute 24); 8-11 Ma
   0x5a5a3a18, Mb 0x5a5a3a1a, ctl 0x1a00 (attribute 26), 0. Program: `douta` V0 (ds0[2], ds1[1]),
   `douta` V2 (ds0[3], ds1[2]), `douta` Ma (ds0[4], ds1[3]), `douta` Mb (ds0[5], ds1[4]),
   `doutu`, `halt`; no `tim`. 12 + 6 = 18 dwords at [0x100, 0x148), control 0x01800100. Against
   land only V0 and V2 to attributes 0 and 2 are added, so LV differs from LC2 in that alone.
4. KUnit, red first: sb402 (and sb400) accepted only with its `form=`; every other `emitpds`
   still refused; `pds=mark` and `pds=landv` written at #14's + 0x100 with U0, V0 and V2 filled
   and nothing else, the slack zeroed, the room check; the arm log names them.

**resgx545 branch `r42-n3g` off main e6201508:** `asm/fwtask/pds/mark.s`, `landv.s` (the
kernel's words generated from them, as crumb3 and land); `gen_verify.py`'s form table with sb402
(test: fw14's and sbc43's words unchanged); `gen_blobs` `emitsb_sb402s` (the existing
`gen_emitsb_after` for form sb402; test: equal to `emitsb_sbc43s` but the word); the kit's arm
grammar takes `pds=mark`, `pds=landv`, `form=sb402`; K5 (§4); scorers; sessions G1-G3.

**Delivery** as round 40: cachix build (`C/kernel39c/deliver-cachix.sh`, module only, the fresh
seed), the fork's KUnit on the Mac shim first (O3), install and one one-shot boot on the laptop
with the user's OK, srcversion loaded = installed (boot-test-kernel.sh, test-session.sh). The
sessions are frozen with a placeholder srcversion and refrozen once cachix names it.

**Firmware-page writes (each needs the user's OK; the README shows every dword before the
run).** C, S and Q: crumb3's 19 dwords [0x100, 0x14c), R4's bytes, approved and run since round
38 [HW, E1154, E1162-E1175]. **M: new bytes**, 21 dwords [0x100, 0x154), the two markers and two
`douta` more than crumb3. **LV: new bytes**, 18 dwords [0x100, 0x148). U0 = 0x080401ef for every
`*s` blob (entry 1 at index 0x4000 + 30, as H1-H4 and LC2) [HW, E1174-E1178]; the builder
confirms it for `emitsb_sb402s`. What is new in M is that two EDM secondaries (sa1 and sa13) take
values we chose, through bit 10, until a reset [infer, H-BLOCK]; under X they took stale values
(0x04000010, 0x00043000) with the same kind of effect [HW, E1174].

## 3. Rows, frozen predictions

Common to every row: the arm `slots=0x1 entry=0 pds=<img> pdsat=fw14 form=<f>`, `#limit 0`,
flagged, on_stop "end"; job 1 = command 1 (the emit, `"ticks": true`, 200 ms, no kick, slots 2-5
and dwords 128-223 filled with 0xdeadc0de first, as B11); command 6 = the after-read (dwords
224-255 filled first). Controls, all can fail:

- **row-scoped**, read on the page or registers after the row: PG (page dword 0), T0 (snap0's
  timer running), B (BIF_FAULT 0 in snap9; a fault is read by the outcomes that name it, the
  rule frozen in X and LC2);
- **job-scoped, read in that job's record and never on the row-end page** (the H3 slip, E1176):
  E0 from `j1rec` (slot 1 = M1 and run id 1, `cmd_after` 0); J1 job 1 DONE (X0, S1, M4 with its
  run id, its record `done`), else CANNOT TELL and stop the ladder; J2 from `j2rec` (done, slot 6
  = M6 0x5a5a3306 and run id 2); each after-read from its own job's record (`slots`), not the
  page's dwords 224-255, which a later job rewrites.

Printed, never scored: the arm line, each job's Δtick, kick reply and **K5's BIF words before
and after it**, the survey (pre, post, each after-read and where they differ), the gate's tools,
the devcoredumps, every fault page against job 1's post words.

### 3.1 Session G1, stage c: row C, the build control (first after the boot)

Row C of H1 (E1173) byte for byte: `emitsb14s`, crumb3, `form=fw14`; job 2 command 6 on a
GETMISCINFO kick; the gate fill then tri.

| outcome | rule | prediction |
|---|---|---|
| C-SAME | job 2's after sa0-31 = job 1's pre | **held** (E1173) |
| C-GATE | fill and tri exact | **held** (E1173) |
| C-DIFF, C-NOKICK | as H1 | failed |

Printed: **R-BOOT**, job 1's post pa0-pa15 against §0.1's words. Do the store's words survive the
reboot (pa1 0x43000 and the odd words as before), or does the boot clear or rewrite them? Not
scored: no prediction is honest here. C failing in any way stops the round: the build, the boot
or the kit is suspect.

### 3.2 Session G1, stage m: row M, the marker in attribute 13 (last in G1)

`emitsb_sbc43s` (X's blob), image **mark**, `form=sbc43`. Job 1 the emit; job 2 command 6 on a
GETMISCINFO kick (X's after-read pass, the tick stopped by T3); then the gate, **fill first** (X's
order, so the fault is a transfer's as in X and Y).

| outcome | rule | prediction |
|---|---|---|
| M-PA | job 1's post pa1 = M13 0x005d3000 | **held** [infer: attribute 13 -> pa 13 - 12] |
| M-SA13 | job 2's after sa13 = M13 | **held** (H-BLOCK and H-COPY alike) |
| M-SA1 | job 2's after sa1 = M1 0x005d1000 | **held** (H-BLOCK); failed under H-COPY |
| M-REBASE | job 2's after = job 1's post in all 32 | **held** (E1174) |
| M-FILL | the gate's fill faults, CID 15, at page 0x005d3000 (= M13) | **held** |
| M-FILL43 | the fill faults at page 0x00043000, sa13 = M13 | failed (the page is not sa13) |
| M-FILLM1 | the fill faults at page 0x005d1000 (= M1) | failed (sa1 is read first) |
| M-FILLOK | the gate's fill exact | failed |
| M-NOKICK | job 2 not done 200 ms after its kick | failed |

**Cannot tell.** J1 not DONE: CANNOT TELL, stop. **M-MISS**: M13 found in no word of post pa0-15
and post sa0-31: the douta did not land where the n - 12 rule says; then M-SA13, M-FILL and
M-FILL43 are scored but say nothing about the source, and the row reads CANNOT TELL for row 3's
question. M-NOKICK: M-PA and the post words stand; the after-read outcomes read cannot tell.

What M settles: M-PA + M-SA13 + M-FILL = sa13 is attribute 13, the word our program wrote, and the
fault page follows it. That settles E1174's and E1178's [infer] and the staleness question at
once: 0x43000 was a stale word in attribute 13. M-SA1 splits H-BLOCK from H-COPY.

### 3.3 Session G2, stage s: row S, does attribute 13 keep M's marker (first in G2)

Row C again (§3.1's blob, image, form, jobs, table and controls), after M's two resets (the
watchdog's and the kit's) and G2's begin reset.

| outcome | rule | prediction |
|---|---|---|
| S-KEEP | job 1's post pa1 = M13, §0.1's other odd pa unchanged | **held** [infer, §0.1] |
| S-BACK | job 1's post pa1 = 0x00043000 | failed (would say: a writer we do not run restores it) |
| S-OTHER | another word in pa1 | printed |
| C-SAME, C-GATE | as §3.1 | **held** |

S-BACK would say the 0x43000 is a stock writer's word, not a leftover, and would name the next
question. If M read M-MISS, S is printed only.

### 3.4 Session G2, stage q: row Q, sb402 (last in G2)

`emitsb_sb402s` (new: `emitsb_sbc43s` with the word 0xfb20b08000808184), crumb3, `form=sb402`.
Y's two jobs (E1175) and the gate, fill first.

| outcome | rule | prediction |
|---|---|---|
| Q-REBASE | job 2's after = job 1's post in all 32, != pre | **held** [infer] |
| Q-REP | post sa4 = sa8 = sa12 = V0, sa6 = sa10 = sa14 = V2 | **held** [infer: E1168, E1175] |
| Q-FILL | the gate's fill faults, CID 15, at the page of job 1's post sa13 | **held** |
| Q-NONE | after = pre and the gate exact | failed (would say: bit 10 acts only with bits 1:0 = 3) |
| Q-OTHER | any other after | printed with indices |

Q-REBASE's reason: bits 1:0 decide the start and bit 10 the rewrite, each alone so far (E1171,
E1175) [infer that they do not interact]. Q-REP's: 0x002 put V0 and V2 in every fourth pa (E1168)
and 0x403 put them in every fourth sa (E1175) [HW]; that 0x402 does both is [infer].
Post sa13 is predicted M13 under S-KEEP and 0x43000 under S-BACK; Q-FILL reads "the page of post
sa13" and so holds or fails on its own reading (as LC2's @post13). With M and S, Q is the third row
where sa13 holds our marker. **Cannot tell:** J1 not DONE (B8's 0x002 ran, E1168, so DONE is
expected); a fault at #14's page + 0x10 is the FAULT outcome of round 40 (E1171), its own reading.

### 3.5 Session G3, stage lv: row LV, `land` with V0/V2 (its own session, last)

`emitsb_sbc43s`, image **landv**, `form=sbc43`. LC2's three jobs (E1178): job 1 the emit, job 2
command 6 on the next tick pass (no kick), job 3 command 6 after `"sleep_ms": 2000` (the heal
read, about 2000 stock passes); then the gate, fill first. Against LC2 only attributes 0 and 2
change (V0, V2).

| outcome | rule | prediction |
|---|---|---|
| LV-V | job 1's post sa0 = V0 and sa2 = V2 | **held** (H-BLOCK; LC2 read 0 and 0x01030b00) |
| LV-EARLY0 | a stop, BIF_FAULT page 0 (CID 15), after job 1, before job 2 | **failed** [infer] |
| LV-EARLY | any other stop or CID-15 fault before job 2 is served | failed [infer, weak] |
| LV-REBASE | job 2's after = job 1's post | **held** (as X, now with the tick running) |
| LV-HEAL | job 3's after sa13 = pre sa13 (0) | **failed** [infer, §0.1] |
| LV-FILL | the gate's fill faults, CID 15, at the page of job 1's post sa13 | **held if reached** |
| LV-FILLOK | the gate's fill exact | failed (would say: the stopped tick of crumb3 is needed) |

The reasons: LV-EARLY0 fails if, as H-BLOCK says, sa0 and sa2 are attributes 0 and 2, which landv
writes with V0 and V2, so the pointer LC's page-0 fault came through is valid again [infer];
LV-HEAL fails because no writer we do not run touched an odd attribute in nine rows (§0.1)
[HW, printed], so nothing rewrites attribute 13 [infer].
LV-EARLY is weak: in X a CID-15 fault at sa13's page came before the gate, with only a kick pass
(E1174), and the EDM still served job 2 [HW]; with the tick running, every stock pass may meet
sa13. K5's per-job BIF words read when it comes. **Cannot tell:** J1 not DONE; LV-EARLY of
either kind: LV-REBASE, LV-HEAL and LV-FILL "not reached" (as LC2). LV-EARLY0 would say sa0 and
sa2 are not attributes 0 and 2 under bit 10 (against H-BLOCK and M-SA1).

If LV-EARLY holds, the heal question has no clean form left without the tick (a crumb3 row stops
the tick, so no stock pass runs). Then Q128's bit-10 thread is closed as far as our task can read
it; the user decides whether to ask it again.

## 4. Kit change K5 (no rebuild): the BIF words in each job's record

`R/tools/fwtask/fwtask_run.py` `one_cmd` (:340-395) keeps `regs()`' 0x0c04 (BIF_INT_STAT) and
0x0c08 (BIF_FAULT) twice: just before the cmd write (with `tk0`) and after the poll, as
`rec["bif"] = {"pre": [...], "post": [...]}`. Two reads of the debugfs `regs` file the runner
already reads per job, nothing written. Tests first: the fake runner's records carry it (mock
world: a fault raised between job 1 and job 2's kick shows in j2rec's `pre` or `post`). It
answers what E1174 and E1175 left: which pass faulted before the gate (after job 1, or with job
2's kick) [HW once run]. Printed only; no outcome depends on it. This is the cheap, decisive
fourth item: it costs no laptop time.

Also carried, no change: K1-K4 of round 41 (job lists, `sleep_ms`, `gate_order`, devcoredumps,
hooks print and never stop, the gate's failure a scored end).

## 5. Offline first (no laptop)

- **O1 (records).** Nothing new to fold: E1178 is on main. §0.1's kept-page readings go into a
  fold note for M's record, not a new record.
- **O2 (sim in sync).** sgx-sim refuses sb402 (bit 10 with bits 1:0 = 2 is unmeasured), and
  bit 10's douta landing stays refused (596cc74b). The sessions' replay is `refused` with that
  reason. After the fold, model only what M, S, Q and LV measure.
- **O3 (shim).** The fork's KUnit suite on the Mac shim (as `C/r41-n3f-logs/shim-r41.log`),
  plus the negative suite (a wrong `form=` fails), before cachix.

## 6. Risk, recovery, run order, time

**Recovery.** Every own-task stop and every gate fault so far was recovered by the watchdog or
the kit's reset (round 40: 7 of 7; round 41: X, Y, H3, T, LC2) [HW, E1165, E1167, E1171-E1178]; a
failed reset (rc 13 or 5) is the user's ordinary reboot to the default entry.

- **Build and boot.** No clock-gate path touched; one-shot boot, a bad boot falls back to the
  default entry.
- **C, S.** E1173's emit and read-only command: none new.
- **M.** X's emit, kick and gate (E1174), with sa1 and sa13 our unmapped pages instead of stale
  unmapped ones [infer]. The stray append into `[sa14 + 0xb0]`
  (`R/doc/specs/edm_dataflow.md:685-705`) stays as in X: sa14 holds a stale word, 0x32411000 or
  V2 (§0.1), an EDM-mapped page the reset rebuilds [infer]; decision B (b) would remove it. If a
  marker page were mapped (against §2's reading of the map), the faults would become stray reads
  or stores in that buffer; the reset rebuilds the firmware's buffers.
- **Q.** Y's risk (E1175), with bits 1:0 = 2 (E1168 ran).
- **LV: the highest, lower than LC.** Stock passes every ~1 ms on the rewritten bank until a stop
  or the gate, now with sa0/sa2 valid but sa1, sa13, sa14 and sa22 not (X's and LC2's post sa22 is
  not the pre 0x32000000) [HW, E1174, E1178]: stores through stale pointers into EDM-mapped pages
  are possible [infer]; the reset rebuilds firmware buffers and context images. Its own session,
  last.

**Stop conditions.** C not C-SAME or its gate failing: stop the round. J1 not DONE in any row:
CANNOT TELL, stop the ladder. Any fault outside the gate other than the ones M, Q and LV name:
stop for the user. M-MISS: run S as a printed row, keep Q and LV as planned. LV-EARLY: no further
LV form. A failed reset: the user's reboot, end of the day.

**Run order.**

1. Offline: O3, resgx545 r42-n3g (blobs, images, K5, scorers, sessions, tests red then green),
   `run_all`, check.
2. cachix build (unattended), then install, one-shot boot, srcversion, post-boot draws.
3. G1: c, then m (ends at the gate's fault, rc 16, scored).
4. G2: s, then q (ends at the gate's fault).
5. G3: lv (ends at a stop or the gate).

M before S, Q and LV on purpose: if S-KEEP holds, Q and LV run with M13 in sa13, so the fault page
of three rows names our marker (decision C).

**Laptop time.** Build about 45 min unattended plus 15 min install, boot and checks. G1 about 20
min (two stages), G2 about 20 min, G3 about 10-15 min. About 1 h 10 attended, about 2 h with the
build.

## 7. Rejected alternatives

- **Entry 0 writes markers into its own pa, no rebuild.** The verifier lets a `mov` write pa2-pa4
  only (`F/sgxfive_owntask.c:56-57, 379-383`): pa1, the word that matters, cannot be written, and
  whether the issuer's pa are the started entry's is unknown. Not decisive.
- **"Clear pa first".** Nothing clears the store but a `douta`. M writes fresh words instead, and
  R-BOOT (§3.1) prints what a reboot does to it.
- **A four-row image to carry more markers.** That changes #14's control word (3 rows), which
  every DONE row used [HW, E1162-E1178].
- **M with 0x403.** 0x003-family sidebands put each `douta` in every fourth attribute (E1164,
  E1168, Y's sa) [HW]; M1 and M13 would collide (1 + 12). 0xc43 has no such copies (X).
- **V1 in landv.** It needs a new kernel fill. X served a kick and a command with sa1 stale
  [HW, E1174]; LC differs from X in sa0 and sa2, and those are what LV restores.
- **sb401.** It faults at #14's page + 0x10 before any program runs (E1165, E1171) [HW].
- **Modelling the rows in the sim first.** The sim refuses the unmeasured.

## 8. User decisions (one at a time)

- **A. The build** (one fork build, one one-shot boot): (a) sb402 + images mark and landv + K5,
  sessions G1-G3 (recommended: rows 1-3 in one boot); (b) only n3f's queue (sb402, landv), no M;
  row 3 stays [infer]; (c) no build: K5 only, the round waits for another build.
- **B. Mark's second marker** (crumb3's third row holds two `douta`): (a) M1 0x005d1000 into
  attribute 1 (recommended: M-SA1 splits H-BLOCK from H-COPY); (b) 0 into attribute 14, so sa14 = 0
  and the transfer handler makes no `[sa14 + 0xb0]` store (safer, asks nothing new); (c) M13
  alone.
- **C. Run order**: (a) M first, then S, Q and LV, so their sa13 carries M13 (recommended: three
  rows test the fault page, and S reads persistence for free); (b) Q and LV first on today's
  0x43000, then M; S dropped.
- **D. Row LV** (stock passes on a rewritten bank, the tick running): (a) run, its own session,
  last (recommended); (b) run only if M reads M-SA1 and M-FILL (the bank is attribute-mapped as
  H-BLOCK says); (c) skip.
- **E. Kit change K5** (per-job BIF words, no laptop cost): (a) add (recommended); (b) skip.
- **F. sb400 in the form list** (bit 10 with bits 1:0 = 0): (a) add the word, no row
  (recommended: a free follow-up, no boot later); (b) add it and run it last in G2 (NEVER expected,
  the tick stops, so the bank is not read); (c) leave it out.
