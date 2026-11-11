# Round 4 proposal, area EVENTS: what E817..E830 settle, and the rows left (Fable, 2026-11-11)

Planning only, read-only. Nothing here touched the laptop, a repo or the guard; no build. Scratch
of this proposal: `closing4/events/offline/` (four scripts and their outputs, section 0). Bases:
`closing3/r3k-events/` (K0, K1: E815 to E823), `closing3/r3x-events/` (E811 to E814),
`closing3/r3x-c3/` (E809, E810), `closing3/r4-reruns/b-q152/` (E830), and the round 3 plan
`closing3/events/exp-events-r3.md`. The disassembly listing `closing3/events/readings/ukernel.dis`
was not opened; only the reviewed notes `readings-r3.md` (R-1 to R-4) were read.

Limits held by every proposed row: no kernel change (the laptop's rgn4 module, srcversion
99CD90DA, already has `kicker`, `kick_no_bump`, `kregnow`, `hold_recovery` and the `cont4` patch
kind: read in the fork at a2788bd8, and E830 ran `cont4` on it); no clock-gate register; no
`trc_hazard`; no reboot, GRUB or build on the laptop; debugfs via `sudo -n`; kmsg via
`os.open(O_WRONLY | O_APPEND)`; **no firmware `str` at all in the recommended set** (the brief
allows 0x0814 and 0x0a78 only; HACKING.md check 5 lists three more since R3-K1 and R3-K10: the
difference is decision 6).

## 0. Offline readings made for this proposal (kept data only; to record as dated notes)

Scripts import the frozen `r3k-events/score/scorelib.py` read-only; outputs beside them.

0a. **E819's Q3 ring ends at the kick, not 7 ticks after it [data + infer]** (`kick_latency.out`,
`kb_ring.out`). The stamps of E819 are taken before the `miscinfo` call starts. In the one kept
job of the same op with a logged kick entry (K0's G0, E816) the entry came 6.70 ms after that
stamp. Q3's calls started at 14.30, 14.36 and 14.42 ms and its rings ended (16 rungs full) at
22.00, 22.16 and 21.38 ms, so the `CR_EVENT_KICK` write fell at about 21.0 to 21.1 ms [infer, one
latency sample] and the ring holds 2, 1 and 0 to 1 ticks after it, not the 8, 8 and 7 "after the
call began". E819's post hoc reading "the count stayed 2, which does not fit H-HWC" and the
absence of a kick entry therefore rest on at most 3 ticks and about 1 ms. No correction of the
claim line is needed (it says "void by the frozen reader"); the post hoc paragraph and Q290's last
note need an appended note. Refuted by: a Q3 job whose ring covers 5 ms after the write (row Q3').

0b. **Those last ticks carry E751's "latched while busy" mark [data]** (`pa2_74.out`). Of 635
tick entries in the kept rings of r3k-events (f, t, kb, k0h) and R4-B, `pa2` reads 0x01061a70 in
628, and 0x01061a74 in 6 (plus one mid-period sample): the three ticks of the post-hold burst of
K0's H1 (as E749, E751, E752 and r3x-events H1 x3: 12 of 12 burst entries), and **the last 2, 1
and 0 entries of q3, q3-r2 and q3-r3** (at 21.0 and 22.0 ms; at 22.16 ms; none), all on the
25000 grid. E751 reads 0x74 as a tick latched on arrival while the EDM is not idle (12 clocks
after the reload against 16). [infer] From about the time of the unbumped kick's write the EDM
was not idle when ticks arrived, with no kick entry logged: the unbumped kick left an event
pending or in service that never reached our slot 0 task. E819 named the 0x74 as unexplained;
this is a candidate reading, post hoc, 3 entries in 2 of 3 jobs.

0c. **The grid is exact and a stored timer word moves it for good [data]** (`grid.out`,
`t_ring.out`). 702 consecutive plain-tick gaps of the kept rings average 25000.2 `CR_TIMER`
units (431 of 513 in the first set exactly 25000, the rest within 4): 400000 timer clocks a tick
at 16.000 clocks a unit. After FC4, FB, FPH (E817, E830) the next gap is 24994 or 24995 and the
one after 25006 or 25005: the old grid is kept (the short gap is the logging path of the pass
after an acted one). After T1 (E818) the gaps are 25114 then 25000, 25000, ... in both jobs: the
grid moved by 114 to 120 units and stayed there. E818 recorded the 25114; that the shift is
permanent is new.

0d. **The event timer reloads with nobody serving it [data]** (the stop signatures of E814,
E813, E817, E818, E823, E830: 9 stops, 2 samples each). `CR_EVENT_TIMER` bits 23:0 read below
400000 in 18 of 18 samples of a stalled EDM, seconds after the last served pass (a counter that
ran through 24 bits would be below 400000 in 2.4% of samples). With E751 (ticks latched during a
hold 12 clocks after a reload) the timer is periodic by itself; no handler store is needed to
re-arm it.

0e. **Call counts over the kept stops [data].** 13 stops in the records (E533, E537, E793 x2,
E813, E814 x2, E817, E818, E823, E830 x3): every one read the busy signature where it was
sampled, every one was recovered by one debugfs reset, and P3 (one `miscinfo` into the stop) was
answered in 0 of 8 (E814 2, E817, E818, E823, E830 3).

## 1. What the records settle (knowledge, by topic)

Tier per line; records in brackets. "Refuter" is what would contradict it; "held out" says if the
supporting rows were frozen held-out rows or need one.

**Timer and tick.**

- T1 [HW]. The tick is `CR_EVENT_TIMER` (0x0acc): bit 24 set, bits 23:0 counting down 400000
  clocks, reloading by itself (0d; E751). One tick is 25000 `CR_TIMER` units, exact to 1 in 10^5
  (0c). `pa2` of an event is the timer sampled for it: 0x01061a70 for a tick served at once,
  0x01061a74 for a tick latched while the EDM is not idle (E746, E751; 0b). Refuter: a plain
  tick with another `pa2` in an idle EDM. Held out: E751's rows were.
- T2 [HW + infer]. A task's `str` of the reload word 0x01061a80 to the timer, followed by the
  closed task, keeps the tick and moves the grid by 114 to 120 units for good (E818 T1, 2 of 2;
  0c). [infer] The store restarts the countdown where it executes. The closed tick handler's own
  store (E155 [RE]) does not move the grid on ordinary passes (0c), so either it is not made on
  every tick or an equal store late in the pass is not a restart: not separated. The store does
  not replace the phase end (E818 T2, 1 stop). Refuter: a store placed D units later in the pass
  that does not move the grid by D more (rows T3, T4 of decision 6).
- T3 [HW]. A pass with the tick bit of `sa64` clear leaves `pclink` at 6, does not advance
  HostCtl dword 12 and keeps the tick (E792, E812 C5: 50 passes, 2 of 2). A tick pass handed to
  the slot 2 closed task keeps the tick and does not advance dword 12 (E813 X1, X20). So dword
  12 counts passes of the closed tick handler, not ticks.

**The end of a pass (Q152's first half, answered).**

- P1 [HW, held out, replicated]. A plain tick pass of ours keeps the tick if and only if it
  executes `phas #0, #0, pixel, end, parallel` before its `nop.end`: with the `phas` 13 of 13
  jobs kept (FB 2 + 6, FPH 2 + fk 3; E817, E830), without it 7 of 7 stopped (`idf, wdf,
  nop.end` E793 x2 and E818 T2; with `cfi.global` E817 FCF and E830 x3). `cfi.global` is neither
  needed (FPH) nor enough (FCF). The closed exit reached by `cont4` keeps it (8 of 8), and so
  does any closed path that reaches it (slot 0 always; slot 2, E813 X1 and X20).
- P2 [infer, strong]. This is E118's program-shape rule ("the last phase must be closed by a
  `phas` that declares the end; otherwise the job hangs", `usse_isa.md` 3.6) seen in an EDM
  task: a task that never declares its end stays in service. It fits E811 and E816 (a pass
  still running reads the same signature as a stop, 6 of 6 hold jobs), E813 B3 (a kick pass
  ended without it stops too) and E823 (a slot 3 pass). Unlike a client program the EDM task
  need not start with a `phas` (FPH has one only at its end). Refuter: row KP (a kick pass
  ended with the `phas` that stops) or B1P (slot 3).
- P3 [HW]. What a stop is: `CR_CLKGATESTATUS` 0x000ccfa0, `USE0_SERV_EVENT` bit 16 clear and its
  count frozen, the timer counting, `CR_EVENT_STATUS` 0x20000000 (bit 29 is set in every read,
  healthy or not: 234 of 234, round 3 reading 0b), no later event, a host command not answered,
  one debugfs reset recovers (0e). The signature cannot tell a stop from a long task (E811).

**The kick.**

- K1 [HW]. A kick is: command at the CCB write offset, kicker word W bumped (mod 256),
  `CR_EVENT_KICK` written. It is one event in the general slot, `pa0` = 0, `pa1` = K << 24 |
  0x100 with K the count before the bump; the ticks after carry K + 1 = `ccbctl[0]` (E746, E768,
  E816 G0). Kicks arriving during a hold are queued one by one with the count at arrival (E794).
- K2 [HW, held out]. Writing W alone (0x42, no kick) raises no event and leaves the count of the
  ticks at 2 (E819 Q1, 3 of 3): the hardware does not read W per event. H-KW is refuted.
- K3 [HW]. A kick without the bump is not consumed: read offset stays, no answer in 504 ms, the
  tick goes on (E819 Q3, 3 of 3). [infer, 0a, 0b] No kick entry reached our task within about
  1 ms and the ticks after it carry the "not idle" mark. So the event needs W to change, and
  the count byte follows W as latched at a served kick or the commands consumed: Q2 of E819
  could not separate these (its ring was full 11 ms before the kick).
- K4 [HW + RE]. A phantom kick bit (`sa65` bit 8 with read = write) makes the closed reader take
  an empty command, branch to index 0 and record 0xad002600 in HostCtl dword 14, read = write +
  1 (E814 D2, E537; R-3). E537's word without bit 8 stops it with no mark (E814 D1); bits 2, 3,
  6, 14, 15, 16, 19, 23 and the count byte alone are harmless (E812).

**Status latches and clears (Q166, Q111).**

- S1 [HW, held out]. `CR_EVENT_HOST_CLEAR2`: the bits written are the bits cleared, by the host
  (E821) and by a task's `str` (E822), 3 of 3 rounds each; the latch can be set again.
- S2 [HW, 1 job, post hoc]. `CR_EVENT_STATUS` bit 18 is a level until acknowledged: 48 ms set
  with the slot 3 handler skipped; a host write of bit 18 to `CR_EVENT_HOST_CLEAR` clears it, of
  bit 15 does not (E823). The 4 to 6 us pulses of E547 are the firmware's acknowledgement.
- S3 [HW]. A latched bus fault is not cleared by writing its bits to `CR_BIF_INT_STAT` (4 of 4);
  `CR_BIF_CTRL` bit 4 hides it while set and it returns when cleared; the reset clears it
  (E826, frozen verdict "cannot tell": the three readings agree across rows, post hoc).

**Task state (Q098, Q124, Q158).** [HW] `mov` to pa3 is sa67 (kept to the next pass), to pa2 is
sa66 for the pass only (rewritten per event [infer]), to pa4 is lost (E820, 3 of 3 each). p1, p2,
p3 at the next entry are what our task left; p0 reads 1; after a fill, reload or reset p0 p1 = 1
1, `pclink` 0x98, p2 0 and p3 as left (E809, E810). i0, i1 survive a reload and a reset, sa63
and r20 do not, r21 does (E810).

## 2. Where it should land (all offline; no hardware needed)

| # | place | change | rests on |
|---|---|---|---|
| L1 | `doc/specs/hw_spec.md` 12.2 "The EDM tick" | rewrite its last two paragraphs as four short ones: timer (T1 to T3), end of a pass (P1 to P3), the kick (K1 to K4), state between passes; today it stops at E794 and says "what the EDM needs is open" | E811 to E819, E830 |
| L2 | `hw_spec.md` 6.4 "Event bits" | S1, S2 with their tiers; drop "for how long a bit is set is open" for bit 18 and STATUS2 bit 6 | E821 to E823 |
| L3 | `hw_spec.md` 5.4, 5.5 | S3: what `CLEAR_FAULT` does and does not on a held fault | E826 |
| L4 | `doc/specs/usse_isa.md` 3.6 and line 622; `usse_guide.md` line 515 | P1, P2: the `phas ... end` rule for an EDM task, the canonical own end `idf; wdf; phas #0, #0, pixel, end, parallel; nop.end`; E820's pa rules beside E748's | E817, E820, E830 |
| L5 | `doc/specs/edm_dataflow.md` section 4 | register rows: `CR_EVENT_TIMER` (periodic, a store restarts [infer]), `CR_EVENT_KICK` and the kicker word (K1 to K3), HOST_CLEAR and CLEAR2 (S1, S2) | as above |
| L6 | `crates/sgx-sim/src/edm_pass.rs` | `PassEnd::OwnEnd { cfi, phas }` and `PassEnd::Exit` (cont4): `phas` true on a tick pass is Kept with the next entry 24994 to 24995 then back on the grid; `phas` false is Stalled (read = write, dword 14 0); on a kick or slot 3 pass with `phas` true refused until KP and B1P run. A `timer_store: Option<u32>`: 0x01061a80 then `Closed{0}` Kept with the grid moved 114 to 120; then own end without `phas` Stalled; any other word refused. Tests name the records | E817, E818, E830 |
| L7 | `crates/sgx-sim/src/sgx.rs` (`event_count`, `EVENT_KICK`) | a kicker word in the model: an `EVENT_KICK` write with W unchanged raises no kick event, leaves the count and the read offset, and the command is refused as unanswered (today every write counts and raises bit 8, which E819 Q3 contradicts); a W write alone changes nothing; W set then a bumped kick is refused until Q2' runs | E819 |
| L8 | `crates/sgx-sim/src/usse.rs` (`set_pa`, EDM task) | replace the blanket refusal of a pa write: pa3 writes sa67, pa2 writes sa66 (the next event rewrites it), pa4 is dropped, pa0, pa1 and pa5 up stay refused | E820 |
| L9 | sgx-sim register file | `HOST_CLEAR2` write clears the written bits of STATUS2 bit 6 (latched by the measured loops only); `HOST_CLEAR` bit 18 refused until B1P (1 job, post hoc) | E821, E822 |
| L10 | vectors (`vectors/nokernel/usse/fwtask-*`) | one vector per acted end from the kept pages of `edm-closing-r3k-events:out/f`, `out/t` and `edm/closing-r4-q152`, by the pattern of `tests/sim_r3.py` | E817, E818, E830 |
| L11 | `tools/fwtask` | an `own_end` macro in the assembler front end and a lint warning for a `.end` not preceded by the exit `phas` (decision 7); resgx545-fw's tasks end the same way | P1 |
| L12 | notes, appended and dated | E819 and Q290: 0a, 0b; E818 and Q152: 0c (the shift is permanent); Q002: 0c's 16.000 clocks a unit (one clock times `CR_TIMER` and the event timer; the USSE clause stays open) | section 0 |
| L13 | question text | Q152 (decisions 4, 5); Q290 reworded to "W latched at a served kick, or commands consumed" with H-KW out; Q166 and Q111 after B1P; Q098's EDM clause marked answered for pa2 to pa4 | section 1 |

L6 to L9 follow "refuse the unmeasured": every row names its record and everything else returns
`Unsupported`. None needs a held-out check beyond the frozen rows it copies, except the two
[infer] items (T2's restart, K3's "needs W to change"), which land as text marked [infer] and as
refusals in the simulator, not as behaviour.

## 3. What remains, and its hypotheses

About Q290 (the count byte and the unbumped kick):

- **H-LATCH**: the count is W as latched when a kick is served. Q2': ticks after the kick 0x43.
- **H-CNT**: the count is a count of served kicks (or consumed commands). Q2': 3.
- **H-HWC**: a count of `CR_EVENT_KICK` writes. Q2': 3; Q3': ticks after the write 3.
- **H-PEND**: an unbumped kick leaves an event pending that is not delivered. Q3': no kick entry
  in 5 ms, every tick after the write `pa2` 0x01061a74, `USE0_SERV_EVENT` bit 16 clear.
- **H-NOEVENT**: it raises nothing. Q3': no kick entry, ticks 0x01061a70, bit 16 set.
- **H-LATE**: it is delivered late. Q3': a kick entry inside the ring.

About Q152 and Q166 (does P1 hold for other passes):

- **H-PHAS-ANY**: any pass that ends with the `phas` end is finished for the EDM. KP: tick kept,
  the kick's command not read (read = write - 1, no answer: the closed reader never ran). B1P:
  tick kept, the fill not completed, bit 18 held.
- **H-KICK-MORE** / **H-SLOT3-MORE**: a kick pass, or the slot 3 pass, needs more than the phase
  end. KP, or B1P, stops with the busy signature.

Not proposed, and why: which of bits 4, 7, 10 of `sa65` stops the closed task with no job
(decision 4: it measures the closed code's reaction to an event that did not happen, of no use
to the simulator's refusal or to our own firmware); the D instrument of E811 (whether a stopped
pass was counted: P2 gives the mechanism, and the row costs a session of its own); other `sa64`
words; `cfi`/`phas` word order.

## 4. Stages (one session, laptop directory `~/r4ev`, tool `~/sgxfive-test-s1b` pinned)

Order kb2, kp, e3p. Each stage gated on the previous stage's kept `stage.json`. The runner loads
the firmware by the health fill and triangle before the first EDM stage (rule of 2026-11-11),
slices kmsg by marker, and checks srcversion loaded = installed = 99CD90DA and
`render_rgn_arrays` at its default before and after.

### Stage kb2: Q290 with the ring over the kick (ring_hold.blob byte for byte, 0 stops expected)

The only change against E819's stage kb is the order: `kick_no_bump` and `kicker =0x42` are
written **before** the window opens, and the `miscinfo` call starts 1 ms after it (`ticks_ms` 0).
By G0's kept timing the kick's write then falls about 8 ms after the first ring entry, with
about 7 ticks before it and 6 after. "After the kick" is frozen as: entries stamped later than
the kick entry, or, with no kick entry, later than the call's start stamp + 8.0 ms.

| row | action | x | frozen prediction | label |
|---|---|---|---|---|
| G0' | one ordinary `miscinfo` | 2 | 1 kick entry with K 2; ticks before 2, after 3; `pa2` of the ticks 0x01061a70; file `kicker 3 ccbctl 3 3 kicks 3`; answered | control (E768, E816; fixes E816's void row) |
| Q2' | W = 0x42 before the window, then one `miscinfo` | 3 | all: 1 kick entry, K 2, ticks before 2, answered, file `kicker 67 ccbctl 3 3 kicks 3`. Ticks after: H-LATCH 0x43; H-CNT and H-HWC 3 | held out, 2 replicates |
| Q3' | `kick_no_bump` before the window, then one `miscinfo` | 3 | all: not answered in 504 ms, file `kicker 2 ccbctl 3 2 kicks 3`, tick alive after (fit, E819). Kick entries: H-PEND and H-NOEVENT 0, H-LATE 1. Ticks after, K: 2 (H-LATCH, H-CNT), 3 (H-HWC). Ticks after, `pa2`: H-PEND 0x74 in all, H-NOEVENT 0x70 in all. Signature x2 after the timeout: bit 16 clear (H-PEND), set (H-NOEVENT) | held out, 2 replicates |
| Q4 | Q3', then after its timeout a second window and one ordinary `miscinfo` | 2 | recorded against two frozen readings: H-PEND 2 kick entries and `ccbctl 4 4`; H-NOEVENT 1 entry and `ccbctl 4 3` | held out (decision 3) |

Controls that can fail: G0' (if its kick entry is not in the ring with at least 3 ticks after
it, Q2' and Q3' are void and the stage stops: the timing design is wrong again); the kicker file
reading what was written; `kick_no_bump` reading back N; the tick alive after each job. Cannot
tell: fewer than 3 ticks after the kick. Stop condition: any tick stop ends the stage (none has
occurred in 13 kicker jobs). Each job starts with reset + arm, as E819.

### Stage kp: a kick pass ended with the phase end (new blob ring_exit2, 0 or 1 stop, cap 1)

ring_exit2.s = ring_exit.s plus KIND 2 (ring_end.s's kick-pass test, `pa0` = 0 and `pa1[23:0]`
= 0x100, E813), same ACT 4 (`idf, wdf, phas end, nop.end`). No new instruction form: the `phas`
row is in the landed verifier since 7aaa017.

| row | KIND, ACT | trigger | x | H-PHAS-ANY | H-KICK-MORE | label |
|---|---|---|---|---|---|---|
| E0 | none | none | 1 | 14 +- 2 entries on the grid | same | control |
| FK | tick, 4 | none | 1 | kept, next gap 24994 or 24995, then the grid | same | control (E830 fk, 3 of 3) |
| KP | kick, 4 | one `miscinfo` | 2 | kept: at least 4 tick entries on the grid after the kick entry (flag 3); not answered; `ccbctl` read = write - 1; dword 14 0; signature idle | stop: nothing after the kick entry, busy, P3 not answered | held out, 1 replicate only if kept |

Controls that can fail: E0, FK, ACT_SEEN 4 and ACTED 1 in the page. A stopped row is not
replicated; the stop is signed (signature x2, P3, dumps) before the reset. KP's unread command
is left to the reset that ends the job (no second kick: K3 says what an unread command does).

### Stage e3p: the slot 3 pass ended with the phase end, and HOST_CLEAR (new blob, cap 1)

ring_skip3p.s = ring_skip3.s with the skipped end-of-render pass ended `idf, wdf, phas end,
nop.end` instead of `idf, wdf, nop.end`. `hold_recovery` Y during B1P, restored by trap. The
status watch starts when the page shows the slot 3 entry logged (E823's first read came before
the render's end and voided its frozen rows).

| row | skip | x | frozen prediction | label |
|---|---|---|---|---|
| B0 | 0 | 1 | fill completes, one slot 3 entry, bit 18 never read, tick alive | control (E823 B0, 3 of 3) |
| B1P | 1 | 3 | H-PHAS-ANY: tick alive through the 50 ms watch; H-SLOT3-MORE: stop. Both: the fill does not complete (job held); bit 18 set in 9 of 9 watch reads (H-LEVEL); after `kregnow 0x0134` = bit 15: set at 1 and 3 ms; after bit 18: clear at 1, 3 and 20 ms (H-W; H-ALL clears at bit 15, H-NONE never) | held out, 2 replicates; fit for the clears (E823, 1 job) |

Each B1P ends with the debugfs reset, the gate and health (the job is held by design: 3
recoveries). If B1P stops the tick the stage ends at its first stop and the row still gives the
clears' readings on a stopped EDM once more, with the watch fixed. No `str #77` row (decision 6).

### Cost, risk, order

kb2 8 to 10 jobs, kp 4, e3p 4: **16 to 18 jobs**, about 4 minutes of jobs, 12 minutes wall with
the resets. Tick stops predicted 0, at most 2 (kp 1, e3p 1); held jobs 3 (e3p). Risk: kb2 low
(E819 ran the same writes 12 times; health ok); kp medium-low (B3's shape plus a word that kept
13 of 13 tick passes); e3p medium (a held job and a recovery each, as E823, last in the
session). If only one stage runs, kb2 (decision 2).

## 5. Reuse and new work

Reused unchanged: `r3k-events/bins/ring_hold.blob`; the runner core `run/r3_run.py`,
`r3common.py`, `ops_kicker.py`'s file readers, `ops_e3.py`'s watch and `kregnow` steps,
`health_remote.sh`, `stage_r3.sh`, `freeze_r3.sh`, the guards; `score/scorelib.py` (ring reader,
signature, marks, tally, `sc_ring.py`'s kicker scorer, `sc_e3.py`); the mock (`tests/mockfw`,
`kmock.py`, `shims`, `fake_tool.py`); R4-B's block gate and `FROZEN.commits`; `scorekit.py` for
the new scorer. Session copy in `closing4/events/r4-events/`, never an edit of a kept session.

| new item | what | size |
|---|---|---|
| `ops_kicker` order | writes before `ring_open`, `ticks_ms` 0 in the allow-list, the second window of Q4, signature x2 after a timeout | about 50 lines |
| `asm/ring_exit2.s` (gen) | KIND 2 test beside KIND 1 | about 15 generator lines |
| `asm/ring_skip3p.s` (gen) | one `phas` word in the skipped end | about 5 generator lines |
| tables, predictions | kb2, kp, e3p | generator about 120 lines |
| scorer | "after the kick" rule, `pa2` class of ticks, kick-entry count, Q4, KP, watch from the slot 3 entry | about 180 lines |
| tests | scorer worlds, one per hypothesis (H-LATCH, H-CNT, H-HWC, H-PEND, H-NOEVENT, H-LATE, H-PHAS-ANY, H-KICK-MORE, H-SLOT3-MORE); a world where G0' has no kick entry (the stage must stop); guard breaks; mock end to end; sim of both blobs to their ends | about 350 lines |

Controls are frozen from jobs of the stage's own shape (rule of E825): G0' is frozen on the
count and the entry kinds, which do not depend on the timing, and on nothing E816 read at
another timing. Not provable offline: the 6.7 ms call latency (one sample); G0' is its control.

## 6. How the simulator takes the results

- Q2': `event_count` becomes W at a served kick (H-LATCH) or stays a count of served kicks
  (H-CNT); the refusal of L7 for "W set, then a bumped kick" is replaced by the measured row.
- Q3', Q4: an unbumped kick is `pending` (ticks latched with the 0x74 sample, delivered or not
  by the next kick) or a no-op; until then L7's refusal stands.
- KP, B1P: `OwnEnd { phas: true }` on a kick pass and a slot 3 pass becomes Kept with the
  command unread, or Stalled; L6's refusal is replaced either way.
- B1P: STATUS bit 18 as a level cleared by its own bit in `HOST_CLEAR` (L9's refusal replaced).

## User decisions

1. **Land section 2 offline, before any run.** (a) recommended: one fold with L1 to L13
   (docs, sim refusals and rows, vectors, appended notes), tests first, check.sh on main after
   the merge; (b) docs and notes now (L1 to L5, L12, L13), sim and vectors (L6 to L10) after the
   session so they land once; (c) nothing until the session ran.
2. **Session shape.** (a) recommended: kb2, kp, e3p in that order (16 to 18 jobs, 0 tick stops
   predicted, 2 at most, 3 held jobs); (b) kb2 and kp (12 to 14 jobs, no held job); (c) kb2
   only (no stop by design; closes Q290's main clause); (d) no laptop work for events in round 4.
3. **Row Q4** (an ordinary kick after the unanswered one, two frozen readings). (a) recommended:
   yes, x2, last in kb2; (b) no: Q3' alone reads H-PEND from `pa2` and bit 16.
4. **Bits 4, 7 and 10 of `sa65`** (Q152's remaining first clause). (a) recommended: no run;
   split them and the `sa64` tick-bit clause into one new low-value question that cites E812 and
   E814; (b) run three single-bit rows (reset + arm each, up to 3 stops) after the lead makes
   reading R-5 (what each handler does with no job in flight, E154's method); (c) run them
   without the reading.
5. **Q152 after stage kp.** (a) recommended: if KP keeps the tick 2 of 2, retire Q152 as
   answered by that record (with E817 and E830; the question's title is the phase end), the rest
   moved by decision 4 (a); (b) retire now as answered by E830, KP's row going to the new
   question; (c) keep Q152 open and narrowed.
6. **Firmware `str` rows.** The round 4 brief allows 0x0814 and 0x0a78 only; HACKING.md check 5
   has had 0x0114, 0x0134 and 0x0acc since R3-K1 and R3-K10. (a) recommended: keep the brief's
   limit this round, so no `str` row; T2's "a store restarts the timer" stays [infer] and
   Q166's `str #77` clause is dropped as not needed (E822 showed the route does not matter for
   CLEAR2); (b) allow the two verified rows as they ran: stage t2 (ring_timer with the pinned
   word placed before and after a delay of D units: T3, T4 x2 each, the grid moving by D or
   not, 5 jobs, no stop predicted) and B2P (`str #77` of bit 18, 1 job); (c) t2 only.
7. **fwtask own end** (L11). (a) recommended: an `own_end` macro and a lint warning in
   `tools/fwtask` (tests first), no verifier change, so experiments that end otherwise stay
   possible; (b) the verifier refuses a `.end` without the exit `phas` (tool and kernel, a fork
   commit); (c) text in the docs only.
8. **Notes of section 0** (0a, 0b on E819 and Q290; 0c on E818, Q152 and Q002; 0d, 0e in the
   spec text). (a) recommended: appended before the session's freeze, since 0a and 0b change
   what Q3' predicts; (b) with the session's fold.
9. **Q166 after stage e3p.** (a) recommended: retire it if B1P's clears hold 3 of 3 (CLEAR and
   CLEAR2 both "the bits written"), and reword Q111 to what is left (the order of the rises, the
   level or pulse of the other bits); (b) keep Q166 open for the `str #77` route.
