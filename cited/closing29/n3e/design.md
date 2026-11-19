# N3e: what the emit's sideband says, and where an emitted `douta` lands (design note, not built,
not run)

Status: a design for the lead to bring to the user as **flagged decisions** (§6). Nothing here is
built, committed, staged or run; no laptop, cachix or fork was touched. Tags: **[HW]** measured,
**[RE]** our reading of the firmware as the records give it, **[sim]** fwsim/sgx-sim, **[infer]**
reasoning, **[post hoc]** read after a run, not frozen, **[unfolded]** measured in a kept session
that no E-record carries yet.

Paths: `R` = `/Users/jtorra/src/resgx545` (main a8724ca; records up to E1156 on branch
r39-fold-kz, read at `C/r39-kz-fold`), `F` = fork `/Volumes/linux/linux-sgx-r39` at r39-kernel
f9453424bf71, `drivers/gpu/drm/gma500/sgxfive/` (read with `git show r39-kernel:`), `C` =
`/Users/jtorra/src/scratch/resgx545/closing29`, `W` = `C/r40-s` (resgx545 branch r40-s c3f9f67).
Module on the laptop: srcversion 0CDFCDB73D76F39FE9E593C (fork f9453424bf71), arm words
`slots/entry/trc/pds=v1|crumb|halt|crumb3/pdsat=own|fw14/pds2=0|req/form=own|fw14`.
The verifier takes exactly two `emitpds` words: `OWN_EMIT_WORD` 0xfb20b00000008184 and
`OWN_EMIT_FW14` 0xfb20b10800c08184, and arms an emitting blob only when `form=` names the word
it holds (`F/sgxfive_owntask.c:61-62, 124-137, 755-758`).

## 0. Where Q128 stands

Every row: crumb3 (`W/asm/fwtask/pds/crumb3.s`, 3 rows, control 0x01800100) at `pdsat=fw14`
(0x30011100), one job, controls passed unless said.

| row | session (attempt) | sideband | `s2` | pass | result |
|---|---|---|---|---|---|
| M (R4) | r38-n3c-s3 | 0 | 0 | tick | never started, tick stopped (E1154) [HW] |
| K | `C/r39-n3d-k` (152848) | 0 | 0 | kick | K-NEVER readings, Δtick 7: CANNOT TELL (E1155) |
| Z | `C/r39-n3d-z` (153429) | 0x843 | req | kick | Z-DONE (E1156) [HW] |
| SB | `C/r40-s-sb` (170536) | 0x843 | 0 | kick | SB-DONE [HW, unfolded] |
| S2 | `C/r40-s-s2` (170645) | 0 | req | kick | stop (hang class, rc 4), recovered [HW, unfolded] |
| SP | `C/r40-s-pass` (170734) | 0x843 | req | tick | SP-DONE [HW, unfolded] |
| ST | `C/r40-s-sbt` (174746) | 0x843 | 0 | tick | ST-DONE [HW, unfolded] |

So: with #14's sideband the program runs to done from either pass and with either `s2` (4 of 4);
with sideband 0 it never starts and the tick stops (E1148-E1150, E1153-E1155, S2). **The
sideband decides; `s2` and the kick pass do not** [HW]. The firmware's values (data-private
`firmware/fwsim/n3d-o1/facts.txt` at main 5f15828, facts only): #11 0x0c43, #12 and #14 0x0843.
Field placement: value bits 5:0 at word 27:22, 11:6 at 40:35, 13:12 at 55:54 (usse-dis #149).

Every DONE row printed the same LANDING line: entry 1's pa0-pa3 = 0x00000000 0x00043000
0x3727c5ac 0x01555620 (4 of 4, identical), sa0-sa3 = V0-V3 (TA3DCtl dwords 0-3); "pa0 = V0 no,
pa2 = V2 no" (`C/r40-s-sbt/score/score.py:274-284`, `landing()`).

## 1. What the records allow us to say

### 1.1 The sideband

What is measured:

- From an EDM task of ours, 0x000 never starts the program and 0x843 always does (§0) [HW].
- From a **client** fill shader, sidebands 0x000, 0x001, 0x200 and 0x2000 all started the
  program (one probe each), and every such job then faulted; the fault page was 0xd2000 in 22
  of 24 and **0x92000 once, with sideband 0x1** (E488, `R/doc/isa/content/usse/groups/emit.md:
  41-45`) [HW]. A one-probe difference; it says the sideband reaches something on the bus side
  [infer, weak].
- #11 is the program that copies TA3DCtl into the EDM's secondary attributes (`R/doc/specs/
  hw_spec.md` §11.1 step 2; E002, E003) [RE]; it alone of the three carries bit 10 [RE, O1].

Candidate readings, each [infer], none from a source that names the `emitpds` sideband (the
cited Mesa csbgen rows, C0206-C0208 and C0712, are the PBE sideband of `emitpix2`: pack mode
5:0, bit 9, dither 10, memlayout 13; a different emit, not transferable):

- **H-DM: bits 1:0 name the data master the started program runs for.** The SGX545 DDK's own
  2-bit DM field of `CR_USE_CODE_BASE_n` (C0013, `sgx545defs.h:638`; C0012, EMGD `psb_regs.h:
  424`; glossary G0007: vertex, pixel, reserved, event) has the same width, and 3 (event) is
  what an EDM-started program would carry; 0 would be the vertex DM, which has no work on our
  laptop's idle passes. A client pixel shader's sideband 0 or 1 still running fits a DM that
  is busy anyway. Predicts: bits 1:0 = 3 is needed and enough for the start, bits 6 and 11 do
  not decide it.
- **H-SA: bit 10 marks a program that (re)loads the issuer's secondary attributes** (#11's
  job). Predicts nothing about the start; it is the reason 0xc43 is a risk row (§4).
- **H-ALL: the 0x843 value is needed as a whole** (no bit alone; e.g. a fixed EDM-to-PDS
  routing code). Predicts: every single-bit removal from 0x843 never starts.
- **Bits 6 and 11** have no candidate from a cited source. One weak thought: SGX545 is the only
  core with two PDS pipes (`R/doc/specs/pds_isa.md` §8.11, :1461-1473), so a pipe or
  pipe-mask bit is possible [infer, unsupported].

H-DM is the working hypothesis; the rows below are chosen so it can fail in both directions
(a DM-3 row that never starts, a non-3 row that starts).

### 1.2 The landing

- `douta` writes its first word to the **secondary** attribute named by control bits 19:8; from
  a fill's secondary program the values reach `sa0`-`sa15` of its tasks; from a primary program
  nothing reached the USE task (`R/doc/specs/pds_isa.md` §3 `douta`; E391, E1096, E1104) [HW].
  So pa0/pa2 were not where to look [infer from that rule].
- crumb3's V0 and V2 are filled by the kernel with **what sa0 and sa2 already hold**: TA3DCtl
  dwords 0 and 2 (`F/sgxfive_debug.c:2205-2208`, "the values sa0 and sa2 hold"), by design, so
  that a `douta` into the EDM's own secondaries changes nothing. A landing at sa0/sa2 is
  therefore invisible: the LANDING line's sa0/sa2 = V0/V2 says nothing (E1156 "What it does
  not show").
- Entry 1's sa1 = V1 and sa3 = V3 as well, which no `douta` wrote: the doutu-started task sees
  the EDM's secondaries [infer: shared, or copied].
- The firmware reads `sa0`-`sa19`, `sa22` and `sa43` (`R/doc/specs/edm_dataflow.md` §0-§2, all
  6637 instructions analysed; secondary attributes seen: 20) [RE]. `sa20`, `sa21` and `sa23`-
  `sa31` are read by no firmware instruction [RE, static; indexed access not excluded].
- pa0-pa3 of entry 1 are the same in 4 of 4 runs; what they are is not asked here (printed).

## 2. Offline first (no laptop)

- **O1 (records, this note's lead).** Fold SB, S2, SP and ST (§0) into E-records before any row
  here is frozen; correct E1156's LANDING reading: sa0/sa2 = V0/V2 is by construction
  (`F/sgxfive_debug.c:2205-2208`), and `douta` targets `sa`, not `pa` (§1.2).
- **O2 (sim in sync).** sgx-sim refuses every own-task emit (`R/crates/sgx-sim/src/sgx.rs:
  777-787`). After O1: sideband 0x843 from our task runs (E1156 + folds), 0 does not start;
  every other value stays refused until a row below measures it.
- **O3 (shim).** Every new blob through the fork's KUnit suite on the Mac shim
  (`C/r40-s-shim`, as `C/r40-s-logs/shim-emitsb14.log`) before its session is frozen.

No new data-private read is needed: the three firmware values are known (§0).

## 3. Rows, cheapest first, frozen predictions

Base for every row: **ST** (`emitsb14`, a tick pass, no kick, `pds2=0`, crumb3 at `pdsat=fw14`),
the cheapest DONE combination (no host-command pass in the job). Each row changes **one** thing
against ST, or against D0 for L. One owntask stage per row, `#limit 0`, flagged; a runner stop
ends the session (rc 4), an ok end disarms (its reset restarts `tim` and zeroes #14's slack) and
the next owntask stage arms afresh. The kit takes several owntask stages per session
(`owntask_stages()` returns a table, `C/r40-s-sbt/kit/session.py:290`); **predicted-RUN stages
first, at most one predicted-NEVER stage, last**.

The common table (ST's, `C/r40-s-sbt/README.md` "Outcomes"; T is 0x0acc in snap9 and the stop
dump; no tick band):

| outcome | T | S1 (dw 84) | M4 (dw 80), state |
|---|---|---|---|
| NEVER | running | fill | fill, 0 |
| T1: started, stopped at a `douta` | 0x00000000 | fill | fill, 0 |
| T2: stopped at the `doutu` | 0x00000200 | fill | fill, 0 |
| T3: `doutu` issued, entry 1 never stored | 0x005a3305 | fill | fill, 0 |
| E1: entry 1 started, stopped after S1 | 0x005a3305 | 0x5a5a3304 | fill, 0 |
| DONE | 0x005a3305 | 0x5a5a3304 | M4 + run id, 2 |

RUN = any of T1..DONE. Controls as ST: PG, E0 (slot 1 = M1 + run id, cmd 0), T0, B (else FAULT,
its own outcome). Cannot tell as ST. X0 printed.

### 3.1 No rebuild, no boot (module 0CDFCDB7): row D0, the landing survey

**Blob `emitsb14d`** = `emitsb14` plus stores, nothing else changed (same word 0x843, same emit
path, entry 0 and entry 1 code order kept up to the new stores):

- entry 0, after the M1/run-id stores and before the fence that precedes the emit: `mov rN,
  saK; stad` for K = 0..31 into page dwords 128+K (**pre**);
- entry 1, after S1 and before M4: pa0-pa15 into dwords 192+K and sa0-sa31 into dwords 160+K
  (**post**); the existing pa0-pa3/sa0-sa3 slots (72-79) kept, so ST's scorer lines still read.
- The verifier at f9453424bf71 classifies `mov rN, paK` and `mov rN, saK` (K <= 31) as
  `mov-reg` with no refusal (`C/r40-s-logs/d-row-note.md`); confirm with O3 before freezing.
- The host fills dwords 128-223 with 0xdeadc0de first (as slots 2-5 today).

Arm `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=fw14` (ST's). Firmware-page write: ST's, byte
for byte except U0 if entry 1 moves (`emitsb14d`'s entry 1 index; U0 = TRC 8, CBASE 15, index
0x4000 + entry 1); stated in the session README as R4's.

Readings and outcomes (frozen; DONE of the common table is a precondition, else CANNOT TELL):

| outcome | rule | prediction |
|---|---|---|
| D0-HID | post sa4-31 = pre; no V0 or V2 in pa0-15 | **held** [infer, §1.2: sa0/sa2 own values] |
| D0-PA | V0 at pa k and V2 at pa k+2 for some k | failed |
| D0-SHIFT | post sa j = V0 and sa j+2 = V2 where pre differed, j >= 4 | failed |
| D0-STIR | any other pre/post difference in sa4-31 | printed with its indices |

Extra controls (can fail): **P0** every pre dword overwritten (no 0xdeadc0de left in 128-159);
**P1** pre sa0-sa3 = V0-V3 (the EDM's own secondaries, as E002). Printed, never scored: pre and
post sa20-sa31 (the quiet-attribute survey L needs: equal pre and post, and no firmware read,
§1.2), pa0-pa15.

D0 alone cannot see a landing at sa0/sa2 (that is L's job); it rules out pa and a shifted sa,
tests sharing (pre = post in sa4-31) and picks L's target attributes. **Risk: none new** (ST's
emit, word, image and page; only more stores in our own results page). About 10 min.

### 3.2 One module build and one one-shot boot: the sideband list and the `land` image

**The fork change (one build, everything batched).**

1. **The emit words.** `form=` becomes a closed list (decision A, §6). Recommended set: the 16
   subsets of 0x843's set bits {0, 1, 6, 11}, plus #11's 0xc43 and 0x403 (bit 10 without 6 and
   11), each with every other field of our word:

   | form | sideband | word | H-DM predicts |
   |---|---|---|---|
   | own | 0x000 | 0xfb20b00000008184 | NEVER (measured) |
   | sb001 | 0x001 | 0xfb20b00000408184 | NEVER |
   | sb002 | 0x002 | 0xfb20b00000808184 | NEVER |
   | sb003 | 0x003 | 0xfb20b00000c08184 | RUN |
   | sb040 | 0x040 | 0xfb20b00800008184 | NEVER |
   | sb041 | 0x041 | 0xfb20b00800408184 | NEVER |
   | sb042 | 0x042 | 0xfb20b00800808184 | NEVER |
   | sb043 | 0x043 | 0xfb20b00800c08184 | RUN |
   | sb800 | 0x800 | 0xfb20b10000008184 | NEVER |
   | sb801 | 0x801 | 0xfb20b10000408184 | NEVER |
   | sb802 | 0x802 | 0xfb20b10000808184 | NEVER |
   | sb803 | 0x803 | 0xfb20b10000c08184 | RUN |
   | sb840 | 0x840 | 0xfb20b10800008184 | NEVER |
   | sb841 | 0x841 | 0xfb20b10800408184 | NEVER |
   | sb842 | 0x842 | 0xfb20b10800808184 | NEVER |
   | fw14 | 0x843 | 0xfb20b10800c08184 | RUN (measured) |
   | sbc43 | 0xc43 | 0xfb20b18800c08184 | RUN (H-SA: risk) |
   | sb403 | 0x403 | 0xfb20b08000c08184 | RUN |

   (Words computed from 0xfb20b00000008184 with the field placement of §0; `gen_verify.py`
   generates the table, a test asserts fw14's word unchanged.) One blob per word, `emitsb_sbXXX`
   = `emitsb14d` with only the word changed (`gen_blobs` variant, a test per blob as
   `test_emitsk14_is_emitsk_with_the_fw14_word_and_nothing_else`), so every row also carries D0's
   pre/post landing readings for free.
2. **The `land` image** (`pds=land`, decision C): crumb3's layout and control word 0x01800100
   (3 rows, so `pdsat=fw14` and #14's control as every DONE row), **no `tim`**:
   data dwords U0, U1 0, U2 0, 0x00001800 (douta control, attribute 24), Ma 0x5a5a3a18, Mb
   0x5a5a3a1a, 0x00001a00 (attribute 26), 0, four zero dwords; program `movs douta, Ma, ctl24`,
   `movs douta, Mb, ctl26`, `movs doutu, U0, U1, U2`, `halt` (operands as crumb3's, its two
   `tim` lines and T3's dword gone). Markers are constants of the image, not kernel fills.
   Attributes 24 and 26 are the default; **if D0 shows either one stirred**, the build takes the
   first pair j, j+2 in 20..31, outside {22}, that D0 shows quiet.

KUnit (red first): each listed word accepted only with its `form=`, every other `emitpds` still
refused; `form=` names refused for a blob without an emit; `land` written at #14's +0x100 with
U0 filled and nothing else (as `fw14_disarm` and the crumb3 tests); `own_arm` and the log name
`form=` and `pds=land`. Delivery as round 39: `C/kernel39c/deliver-cachix.sh`, one one-shot boot,
srcversion check (`feedback_laptop_test_boot`).

**Firmware-page writes of this build (each needs the user's OK).** Every row writes its image
at #14's buffer + 0x100 after zeroing [0x68, 0x1000), #14's own 0x68 bytes, PTE and flags
untouched, the disarm reset rebuilding #14's bytes:

- crumb3 rows: R4's 19 dwords [0x100, 0x14c), approved and run 7 times; only U0 follows the
  blob's entry 1.
- `land` (new bytes): 16 dwords [0x100, 0x140): U0, 0, 0, 0x00001800, 0x5a5a3a18, 0x5a5a3a1a,
  0x00001a00, 0, 0, 0, 0, 0, then the four instruction words.
- `land` also **writes two EDM secondary attributes** (24 and 26, or D0's pair) that stay set
  for every later EDM pass until the disarm reset; no firmware instruction reads them (§1.2).

### 3.3 The sideband rows (after the build, boot-free, one change against ST each)

Image crumb3, `pds2=0`, tick pass, arm `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=<f>`,
blob `emitsb_<f>`. Frozen per row: the common table, the H-DM column above, D0's landing lines
printed.

| row | form | why | H-DM | H-ALL | stage order |
|---|---|---|---|---|---|
| B0 | fw14 (`emitsb14d`, new build) | control: the build reproduces ST | RUN | RUN | E1, 1st |
| B1 | sb003 | DM bits alone | RUN | NEVER | E1, 3rd |
| B2 | sb841 | DM 1 with 6 and 11 | NEVER | NEVER | E1, last |
| B3 | sb842 | DM 2 with 6 and 11 | NEVER | NEVER | E2 |
| B4 | sb840 | 6 and 11 without DM bits | NEVER | NEVER | E3 |

Conditional (each its own row, same table):

- **If B1 NEVER** (H-DM falsified as "enough"): B5 sb043, B6 sb803 (RUN stages first in one
  session if either is predicted RUN by the revised rule). Both NEVER: 0x843 is minimal on
  these bits; stop.
- **If B2, B3 or B4 RUN** (H-DM falsified as "needed"): B7 sb001, B8 sb002, B9 sb040, B10 sb800
  to find the rule, then the remaining subsets only if the four singles leave it ambiguous.
- **If B0..B4 read as H-DM** (B1 RUN, B2-B4 NEVER): stop the start ladder; bits 6 and 11 do not
  decide the start. B5/B6 are then optional (they would say whether 6 and 11 change what is
  **seen**: the T markers, the landing lines), at the lead's choice.
- **B11 sbc43** (bit 10): last, its own session, only with decision D (§4 risk).

Row L (Q2): **E1, 2nd stage**, `emitsb14d`, `form=fw14`, `pds=land` (changes only the image
against B0). Outcomes (frozen; a no-`tim` image leaves T running, so DONE is S1 + M4 + state 2
with T running):

| outcome | rule | prediction |
|---|---|---|
| L-SA | post sa24 = Ma and sa26 = Mb, pre not | **held** [§1.2: `douta` to `sa` attribute] |
| L-SHIFT | Ma at sa j, Mb at sa j+2, j != 24 | failed |
| L-PA | Ma, Mb in pa0-15 | failed |
| L-ONE | only one marker found | failed |
| L-NONE | DONE but neither marker found | failed |
| L-NEVER | S1 fill, T running, the tick stopped | failed (`land` did not start: CANNOT TELL) |

Extra: **L-TICK** (printed, not scored): whether T is still counting after a DONE with no `tim`
in the image. If it is, the tick stops of the DONE rows were crumb3's `tim` markers alone [HW
then; infer now].

### 3.4 What needs what

| row | session | new blob | kit change | rebuild + boot |
|---|---|---|---|---|
| D0 | D (today's module) | `emitsb14d` | fill 128-223, scorer pre/post | no |
| B0, L, B1, B2 | E1 | `emitsb_<f>`, one per form | owntask stages, `pds=land` | **yes, one** |
| B3 | E2 | as E1 | as E1 | same build |
| B4 | E3 | as E1 | as E1 | same build |
| B5-B10 | cond. | as E1 | as E1 | same build |
| B11 | cond. | as E1 | as E1 | same build |

## 4. Risk, recovery, stop conditions, work list, time

**Recovery.** Every own-task emit stop so far was recovered by the kit's debugfs reset: E1148,
E1149, E1150, R5 (E1153), R4 (E1154), K (E1155), S2: 7 of 7 [HW]; a failed reset (rc 13 or 5)
means the user's ordinary reboot to the default entry.

- **D0.** ST's emit; more stores in our results page only. Risk as ST (ran ok).
- **B0, B1, B5, B6, B9, B10 and the RUN cases** (DM bits 3, or bits 1:0 = 0): as ST and S2, a
  NEVER stops the tick and ends the session.
- **B2, B3, B7, B8 (bits 1:0 = 1 or 2): a new class.** Under H-DM the started program or its
  task would belong to the pixel or reserved DM [infer]: a pixel-DM task might raise a pixel
  event the firmware then services with no render, or fault the bus (the client's 0x92000 with
  0x1, E488). Each in its own last stage; a BIF fault is the row's FAULT and stops the ladder
  for the user.
- **B11 (0xc43): the highest.** Under H-SA a program that reloads the secondaries could leave
  the EDM's sa0-sa43 changed: sa1 (HostCtl) and sa22 (kernel CCB) are written through, so later
  passes could store through a wrong pointer before the reset [infer]. Only with decision D, its
  own session, D0's pre/post sa read giving the evidence of what it touched.
- **L.** Two EDM secondaries no firmware instruction reads hold markers until the disarm
  reset (§3.2); if D0 shows them stirred, the build picks another pair.
- **Build.** No clock-gate path touched; one-shot boot as `C/kernel33/deliver-laptop.sh:17-20`,
  only with the user's OK; a bad boot falls back to the default entry.

**Stop conditions (whole plan).** B0 not DONE: stop everything (the build or the new blob is
suspect; D0 reran first). Any FAULT: stop the ladder, user decision. A failed reset: the user's
reboot, end of the day. H-DM read as in §3.3: stop the start ladder. L-NEVER: do not retry L with
another image in this build.

**Work list (tests first, red then green).**

resgx545 (branch off main, no rebuild):

1. `tools/fwtask/gen_blobs.py` `gen_emitsb14d()`: tests beside `tools/fwtask/test_emitpds.py`:
   the emit word, path and markers equal `emitsb14`'s; 32 pre `sa` reads/stores on entry 0
   before the fence, 16 `pa` and 32 `sa` post reads/stores on entry 1 before M4; offsets
   128/160/192; `fwtask.refusal(...) is None`; lint clean.
2. O3 shim run of `emitsb14d` against f9453424bf71.
3. Scorer: D0's table, P0/P1, the pre/post survey lines; tests on ST's kept attempt (with the
   new slots fabricated as D0-HID) and a fabricated D0-SHIFT.
4. Session `r40-n3e-d0`, predictions frozen.

Fork + resgx545 (one build, after D0 and decisions A-C):

5. KUnit as §3.2; `gen_verify.py` emits the form list; the kit's arm grammar takes the
   `form=` names and `pds=land`.
6. `gen_blobs` variants `emitsb_<f>` (one test per blob: the word alone differs from
   `emitsb14d`).
7. Scorer: B-rows (the common table with each row's frozen H-DM/H-ALL line), L's table; sessions
   E1-E3 with several owntask stages, predictions frozen per stage.

**Laptop time.** D0: about 10 min. Build: about 45 min unattended plus 15 min install, boot and
srcversion checks. E1: about 25 min (4 stages); E2, E3: about 10 min each. Conditional rows:
about 10 min each. Without conditionals: about 1 h 55, about 1 h 10 attended.

## 5. Rejected alternatives

- **Client shader emits** (`sgxfive-test --pds/--use`, no rebuild, any sideband): E488 already
  ran 0, 0x1, 0x200, 0x2000 from a client and every job faulted; it answers a different
  question (a pixel issuer) and is a hang risk by record.
- **A `sb=` arm word that patches the sideband into one accepted blob at the arm** (decision A,
  option b): one blob, but it moves the verifier from "these exact words" to "this word with a
  kernel-written field"; kept as an option, not recommended.
- **Writing distinct values into sa0/sa2 to see crumb3's landing**: sa0-sa2 are the EDM's
  TA3DCtl, HostCtl and CCB pointers (E002); a marker there breaks the firmware's next pass.
- **Reading the landing from pa only** (the d-row-note's first form): `douta` targets `sa`
  (§1.2); kept inside D0 as one outcome, not the whole row.
- **A `tim` marker with bit 24 set in `land`** (to keep T1-T3 granularity without stopping the
  tick): a running count we choose, a new timer risk; L reads S1/M4 instead.
- **Sideband bits 12-13**: no firmware value sets them (§0); not in the list.
- **The 16-subset ladder run blindly**: 14 sessions; the H-DM order (§3.3) answers the same
  question in 3 sessions when H-DM holds, and the list keeps the rest boot-free when it does not.

## 6. User decisions (one at a time)

- **A. The build's emit words.** (a) the 18-word list of §3.2 (recommended: every follow-up
  boot-free); (b) the minimal list 0x003, 0x043, 0x803, 0x840, 0x841, 0x842, 0xc43; (c) a
  `sb=` arm-time patch of one blob instead of a word list.
- **B. Rows with bits 1:0 = 1 or 2** (B2, B3, conditional B7, B8; a new risk class): (a) run
  them as planned, each last in its session; (b) run only B4 (0x840) and skip DM 1/2.
- **C. The `land` image and its two secondary-attribute writes** (row L, a new firmware-page
  write): (a) build and run it (recommended); (b) leave Q2 at D0's answer.
- **D. Row B11 (0xc43, bit 10)**: (a) in the build, run last after the rest, own session;
  (b) in the build, not run until asked; (c) left out.
- **E. D0 now** on today's module (no rebuild, ST's firmware-page write, a new blob): (a) yes,
  before the build is frozen (recommended: it picks L's attributes); (b) fold it into E1.
