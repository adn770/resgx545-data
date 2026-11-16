# Round 34 plan: safe-class sessions that can retire or decisively narrow

Planner (2026-11-16, offline, read only; this file is the only output). Class: SAFE only (no
planned fault, no hang, no `kreg`, no new kernel); tools t10 (a581c06) and t30 (sha256 b5ea288d,
source 42c4de7), regtimeline, the kit's words incl. `pre:miscinfo`, `noreset`, `idle:S`; module
7CE8E38E, or the coming N3 module (one own-task `emitpds` form, `closing29/kernel33/design.md`).

Basis: resgx545 main 5745c8d (132 open, 122 hw; records to E1133, E1132 never built per
`closing29/r33-tim/FOLD-NOTES.md`, so new records from E1134 unless the lead reuses E1132),
`doc/state_digest.md`, the r32 handover, `resgx545-question-closing.md` rounds 29-33, the rank
files of rounds 22 and 27, HACKING "Session kit" and its slips list, `kit/run_stage.sh`'s knob
header, `kit/lib_kit.sh` (health), the last notes of every question named below and the claims of
E031, E268, E377, E383, E385, E1103, E1112.

## 0. Summary

- **Two questions are retire-capable in one safe session each, both low value:**
  **Q010** (which job clears colour-space set 0; ~30 jobs, ~15 min) and **Q044** (CR_REG_0400
  bits 11:0 and bit 25 over the pack modes; ~170 jobs, ~40 min). Both run on today's module with
  t10 + t30 and no tool change. Q010 is the strongest: its line was reworded in round 29 to one
  clause, and E1112 left exactly two candidate jobs (the health fill or the health triangle).
- **Decisive narrowing, not retirement:** **Q111** (high: DPM bits in an overflowing render, the
  events of a copy and a large copy), **Q036** (medium: 0x0748's other bits and
  CR_DPM_3D_PAGE_COUNTS' high half in overflowing renders), **Q082** (medium: bit 6 in a triangle,
  after an offline fit forms a hypothesis), **Q136** (low: sa0's lifetime across jobs). Q111 keeps
  a host-write clause (CR_EVENT_HOST_CLEAR) no safe row reaches, so it cannot retire safe.
- **N3** decides fwsim's emitted-`douta` landing (a sim question); it narrows no open hw question
  more than marginally (Q128 by contrast [infer]). Rank it on fwsim value, after the two safe
  sessions (R34-3).
- **One cheap tool change** makes every timeline session (Q111, Q036, Q082) void-proof against the
  r30-evst and r33-tim slips: control premises read from the row's own `snap0.regs` and from the
  job window of kept timelines of the same register set (T1, kit + scorekit, ~2 h, tests first).
- Not safe and not planned here: Q024 (needs `kreg`, flagged only), Q001/Q043/Q048/Q290 (register
  or clock-gate writes), Q163/Q040/Q112/Q241/Q046/Q139/Q108 residuals (planned hangs or faults).

## 1. Discipline every sketch below follows (what voided r30-evst and r33-tim)

- **L1. Idle values from `snap0.regs` of the same module, never from a mid-session timeline.**
  r30-evst froze CR_CACHE_CTRL 0x1000ffff (E258, after earlier jobs) and the post-reset value is
  0x0000ffff: three stages void (E1116). Here: every control on a register value cites a kept
  7CE8E38E `snap0.regs` (r30-evst2, r31-cc, r32-misc, r33-tim2) and is also checked per row against
  that row's own `snap0.regs` (a premise failure is "cannot tell", not a verdict).
- **L2. Sample-interval premises from the job window of a kept timeline of the SAME register set,
  never from idle spacing or an extrapolation.** r33-tim froze ~1.2 us / 540 ns from idle spacing;
  the job read 4897 ns and 3696 ns with 0x0acc (E1131). E1044 extrapolated 460 ns for 0x0748 alone
  and read 1682 ns. Register cost is per register (0x012c alone ~541 ns, E1115/E1121; 0x0748 alone
  ~1.68 us, E1057; 0x0acc ~3.7 us, E1131). So: no 0x0acc in a fine timeline; a new register set
  first runs a calibration stage (2-3 jobs, readings only) whose measured job-window interval
  gates the later stages (`gate = true`), as r32-kreg3's s0 did.
- **L3. Job outputs frozen from kept job outputs** (hashes of kept copies and images), which are
  premises the hardware already gave under the same tool; and a control that can fail in each
  stage.
- **L4. Held out = rows of a form no record ran, or a second replicate in reversed order frozen
  before the first is read.** Every hypothesis has its rival frozen beside it (r29-flag2's Q010
  rule "not one hypothesis: narrow only" is the model).
- **L5. Stage boundaries run the kit's health pair** (`lib_kit.sh` `health begin/end`: t10 `fill`
  then t10 `tri`), and every row but a `noreset` one runs a debugfs reset first. A sketch whose
  reading depends on what runs between two rows keeps them in one stage, no `after` word.

## 2. Ranking

Value: high 3, medium 2, low 1; x1 retire-capable, x0.5 decisive narrow, x0.2 narrow.

| # | Q | value | class | session | retire? | jobs / wall | tool change | score |
|---|---|---|---|---|---|---|---|---|
| 1 | Q010 | low | safe | r34-csc (t30 copies, t10 fill/tri, `idle:S`) | yes | ~30 / 15 min | none | 1.0 |
| 2 | Q044 | low | safe | r34-pbe (t10 `probe --tri`, `--cmd`, `--sideband`) | yes, R34-4 | ~170 / 40 min | none | 1.0 |
| 3 | Q111 | high | safe | r34-ev (regtimeline, t30 overflow, copies) | no (host-clear clause) | ~40 / 25 min | T1 first | 1.5 |
| 4 | Q036 | medium | safe | r34-ev stage d (0x0748 + page counts) | no (builder-fault clause) | ~20 / 15 min | T1 first | 1.0 |
| 5 | Q082 | medium | safe | r34-b6 (STATUS2 + CLKGATESTATUS, loop triangles) | no | ~30 / 20 min | offline fit first | 0.4-1.0 |
| 6 | Q136 | low | safe | r34-sa0 (iaddu32 to sa0, `noreset`, `idle:S`) | maybe | ~30 / 15 min | none | 0.5 |
| - | Q002 | low | safe | loop fills at 512/2048/8192 instances | no (k x 399 MHz stays) | ~40 | none | 0.2 |
| - | Q128 | medium | N3 | own-task emitpds (`emitsa`) | no | ~10 | N3 boot | 0.2 + fwsim |
| - | Q177 | low | safe | size round W H + 7 W + 52 | no ("what the half is") | ~20 | none | 0.2 |
| - | Q193 | low | safe | unwritten temps across another context | no (power cycle, reload) | ~20 | none | 0.2 |
| - | Q161 | low | safe | point sizes 49-62, edges | no (closed point shader) | ~25 | none | 0.2 |
| - | Q075 | low | safe? | HWPerf group-0 reads under regtimeline | no | ~30 | group select word? | 0.2 |

Score order puts Q111 first, but it cannot retire and needs T1; the two retirements need nothing.
So the run order recommended is Q010, Q044, then T1, then Q111 + Q036 in one session (R34-1,
R34-2). Every other medium/high question keeps a "why" clause or a fault/hang clause (rounds 16,
26 and 27 sweeps still hold for them).

## 3. The top six

### 3.1 Q010 (texture, low): which job clears colour-space set 0 (RETIRE-capable)

**Clauses (line, reworded by E1112):** which job clears set 0 between jobs, given (a) a copy
without the load converts with the last loaded words across a debugfs reset (E1097, E1103,
E1112), (b) with zeros after the kit's health fill and triangle with no fault or hang and after a
recovered hang followed by them (E1112), (c) the first job of a session after hung jobs converts
with zeros (E271). Body extras (not in the line): a recovery without a health job, the power-on
state, set 1 and the luma-key words.

**Premises already measured.** Neither t10 `fill` nor library transfers set
`DRM_SGXFIVE_TRANSFER_LOAD_YUV` (`libsgxfive/src/xfer.c` `sgxfive_transfer_cmd`, kernel
`sgxfive_cmd.c` CMD_LOAD_YUV only from the flag), and a probe fill without the flag keeps the
set (E1103). So the t10 health `fill` is not expected to load; the rivals are real.

**Session r34-csc (one stage `c`, all rows in it, no `after`, safe).** Copies on t30 with
E1103/E1112's forms (`copy --every-value --pixels --poke tex:1=0x7d03f01f --poke tex:0^=0x90`,
a load adds `--poke xfer:17^=0x1` and BT.601 in xfer:18-22). Triples `L, X, R`: L = load BT.601
(control: frozen 0xb6067a95fa98de2d, E037/E1112), X = the job under test, R = copy without the
load (the reading: BT.601 hash = kept, 0xd3522437a14b6325 = cleared, anything else = cannot tell).

| triple | X | replicates |
|---|---|---|
| T0 (control that can fail) | none (R right after L: E1112 q010-pre) | 2 |
| T1 | t10 `fill` (the health fill's exact argv) | 2 |
| T2 | t10 `tri` (the health triangle's exact argv) | 2 |
| T3 | t30 `copy` without the load (a transfer that is not a fill) | 2 |
| T4 | `idle:60` on R | 1 |
| T5 | `idle:120` on R | 1 |
| T6 | t10 `fill` then t10 `tri` (the pair, as health runs it) | 1 |

First row of the stage is an L (the stage-begin health pair may have cleared the set). Second
replicates run in reversed triple order, frozen before the first is read (L4). ~32 jobs.

**Frozen hypotheses.** H-FILL (the fill clears: T1, T6 cleared; T2-T5 kept), H-TRI (the triangle
clears: T2, T6 cleared; others kept), H-BOTH (T1, T2, T6 cleared), H-IDLE (T4 and/or T5 cleared:
the stage gap or a power state, not a job [infer]), H-NONE (all kept; then the stage boundary
itself, a second stage `c2` of one R row would test it, only if R34-1 b). Control: T0 must read
BT.601 in both; every L must read its hash; a premise failure stops (rc 25 via `reads:`).

**Retire rule (against the line).** Controls pass and exactly one of H-FILL / H-TRI / H-BOTH holds
in every decided row with both replicates decided, and H-IDLE fails: then "which job clears" is
answered and (b) and (c) follow (each recovery ran the pair). The body extras go to a new low
question or the body as not asked (lead confirms; R34-4 style). Any other outcome narrows.

**What could void it, and how it is avoided.** The stage-begin pair clears the set before the
first L: the stage starts with L (L5). A set loaded by the copy's own path when the flag is clear
(H-COPYNL): T3 measures it. An idle power-down between rows: T4/T5 separate it (the kit's
`idle:S` waits after the reset, right before R). The copies' hashes come from kept job outputs
(L3), no register value is frozen (L1/L2 do not arise). t30's copy path equals t22's for these
argv [check at build: the mock's argv twin and s0-style references in T0].

### 3.2 Q044 (pbe, low): CR_REG_0400 bits 11:0 and bit 25 (RETIRE-capable, R34-4)

**Clauses (line):** (a) what bits 11:0 do (0x80 as built), no value changing a stored pixel in
pack modes 0-3; (b) does bit 25 act on the other pack modes. Known: 7:0 = threshold of ARGB1555's
one-bit alpha (mode 4), 11:8 nothing in modes 0 and 4, bit 25 inverts alpha in modes 0, 1, 2, 4,
5, nothing in 3 and 8 (E268, E385). Open by the body: alpha equal to the low byte; the low byte in
other modes with alpha bits; bit 25 in the modes not run; 11:8 elsewhere.

**Session r34-pbe (t10 `probe --tri pixel` with E385's alpha-ramp shader and `eot_plain`,
`--cmd 11=V` for the word that loads CR_REG_0400 [builder checks the index against `render.c`'s
`pixelbe`], `--sideband M`, every pixel kept).** The shader is assembled from our own sources
(E385's pds_iter_xy.s and the alpha ramp); the ramp is changed so that alpha takes every multiple
of 4 including 0x40, 0x80, 0xc0 exactly (the equality clause).

- s0 (controls, gate): mode 0 at 0x80 and 0x80|0xf00 identical (E268); mode 4 at 0x80 reproduces
  E385's split (clear to 120, set from 132; frozen from E385's kept image); mode 4 bit 25 inverts
  (E385). Each control can fail.
- p1 (bit 25): every pack mode M in 4..63 except 14 (faults in both runs, E031), at 0x80 and
  0x02000080, plus a repeat of the 0x80 reference for 22, 26 and 34 (E031: 22 and 34 do not
  repeat). ~124 jobs. Frozen H-INV25: the stored image differs exactly in the alpha field the
  mode stores (E031's classes: the 41 ARGB8888-like modes their bits 31:24, 4/5 as E385, 8 and
  modes with no alpha (3-like, 15, 18, 24, 25, 28: green/blue only, E383) unchanged); rival
  H-SUBSET (only modes 0-2, 4, 5). Held out: every mode but 0-5 and 8.
- p2 (low byte): modes with an alpha field narrower than 8 bits (4, 5, 7 at sideband 0, and any
  E031 class with one) at 0x00, 0x40, 0x80, 0xc0, 0xff. Frozen H-THR1 (a threshold only where
  alpha is one bit; equality goes to the side H-GT or H-GE says, both frozen) against H-THRN.
- p3 (bits 11:8): 0xf80 vs 0x80 in one mode of each E031 class. Frozen H-NULL.

**Retire rule.** Controls pass; H-INV25, H-THR1 with one of H-GT/H-GE, and H-NULL hold on every
decided row; modes 22, 26, 34 are decided only where their reference repeats (else "cannot
tell"); mode 14 is named from E031 (faults, nothing stored). Retire if at most those named modes
are undecided and the lead accepts that (R34-4 a); else narrow.

**Voiding risks.** E031's classes are from two runs on an old module: p1's prediction per mode is
frozen from E031's kept stored values, and s0 repeats three of them first (L3). Sideband bits 8:6
fixed at 0 (alpha channel in 7/8, E383). No register value, no timeline: L1/L2 do not arise.
Safety: E031 ran all 64 modes; only 14 faulted; sideband bit 11 (faults, E383) is never set.

### 3.3 Q111 (platform, high): DPM bits of an overflow, a copy's events (decisive narrow)

**Clauses:** which event sets each bit in a TA, 3D, DPM or transfer job; pulse or level; how long;
their order; what a host CR_EVENT_HOST_CLEAR write of other bits clears (host write: not safe, so
no retirement this way). Open per its notes: the DPM bits in an out-of-memory overflow (E547
partial renders show 13, 12, 5, 1, 0; E771 no bit 3), the events of transfers other than the fill.

**Session r34-ev (needs T1).** Stage e0 (calibration, readings, gate): 2 overflow jobs and 1 copy
under regtimeline on CR_EVENT_STATUS alone; it measures the job-window interval that e1/e2 gate on
(L2). e1: CR_EVENT_STATUS alone (~541 ns), t30 `probe --tri --vertices 1500 --keep-overflow` at
the PB sizes of r32-kreg3's calibration (`expect:rc0-overflow`), 4 sizes x 2; t30 `copy` and
`--large-copy`, 3 each. e2: STATUS + STATUS2 on the same rows (one replicate). ~40 jobs.
Frozen from E547/E1120 (job outputs): H-OOM-SET (an overflowing render shows bits 1 or 2 and 4/5
around each partial render, each pulse at most 6.1 us, E547's width bound), rival H-OOM-NONE (the
firmware acknowledges within a sample); H-COPY (a copy shows only 14 with 31 and bit 26 after
CR_CACHE_CTRL's change, E1123), rival H-COPY-END (18 as in a fill).
Controls: snap0's 0x20000000 as the row's first sample (L1); one plain t10 triangle per stage
whose kept E1121 order (26 then 18/0) must repeat.
**Narrow rule:** each hypothesis decided on held-out sizes; record the bit sets and widths. Not
retire: the host-clear and order clauses stay. **Void guard:** T1 checks every frozen idle value
against the row's snap0 and the interval against e0's measured window; no 0x0acc, no 0x0748 in
e1/e2 (slow registers, L2).

### 3.4 Q036 (vdm, medium): 0x0748 bit by bit, CR_DPM_3D_PAGE_COUNTS' high half (narrow)

**Clauses:** 0x0748 bit by bit, PAGE_COUNTS' high half, owner words 0x0700-0x0728, CR_DMS_CTRL
2:0, signature and settle registers, the builder-fault state (fault: not safe). **Stage d of
r34-ev:** d0 calibration (0x0748 + PAGE_COUNTS, 2 jobs, measured interval ~2-3.5 us, gate), d1 the
e1 overflow rows again with those two, 8 jobs. Frozen: E1057's bit 2 clear pulses ~4 us at partial
renders (H-B2PR), PAGE_COUNTS' high half = the 3D's page count at each render (H-HI3D, from E1032's
table) against H-HICONST. Controls: snap0's 0x0748 idle value (L1); the PR-0 row reads no clear
(E1057's control, it can fail). Narrow only (builder clause).

### 3.5 Q082 (edm, medium): what bit 6 follows in a triangle (narrow; offline fit first)

**Clause reached:** "what bit 6 follows in a triangle"; the after-a-fault-word clause is a fault
(not safe). E841 refuted H-SEG, H-N and the discrete reading. **Offline step first (planner or
builder, ~2 h, numpy in scratch only):** fit on E841's kept timelines a per-task form (bit 6 sets
when one pixel task's run reaches ~125 us, the task length = iterations x instructions x E377's
per-instance cost x the instances sharing the pipes [infer]) against E841's first set points;
freeze by hash, or stop if no form fits all five sizes. **Session r34-b6 (only if a form fits):**
t10 `probe --tri` with E841's loop shader at three new sizes and two new loop lengths, each
bracketing the predicted set point (2 below, 2 above), STATUS2 + CR_CLKGATESTATUS (E839's pair,
interval from E839's kept job windows, L2). Controls: a no-loop triangle keeps bit 6 clear; E805's
fill loop sets it near 125 us (both can fail). ~30 jobs. Narrow rule: the frozen form holds on
every held-out bracket.

### 3.6 Q136 (usse, low): how long an sa0 write lasts across jobs (narrow, maybe retire)

**Clauses:** (a) how long an sa0 write lasts across jobs, (b) is pa0's 0xff00ff00/0xff203040
mixture the colour the job before left. E1106 gives a single writer (iaddu32, zero-extended) and
t24/t30's `probe --scratch-show`. **Sketch r34-sa0 (one stage, as r34-csc):** W (writes a marker
to sa0, outputs colour K1), X (none / t10 fill / t10 tri / `idle:60`), R (reads sa0 without
writing it, outputs a fixed colour K2), each twice, reversed order; plus for (b) a K3-colour job
right before a pa0 reader. Frozen H-PERSIST-X per X, rival H-CLEARED. Retire only if both clauses
decide; the "other registers of the banks" in the body make retirement doubtful (lead). Void
guard: hashes and markers from job outputs only (L3); the first row after the stage-begin health
is a W.

## 4. Tool changes that unlock cheaply

- **T1 (kit + scorekit, ~2 h, tests first; recommended before any timeline session).**
  `kitscore.snap0_value(row, reg)` and a sessioncheck lint: a frozen register value in a control
  must cite a kept `snap0.regs` of the module (path + row), and the scorer compares it with the
  row's own snap0 (mismatch = premise failure, rc 25 path, not a verdict). `kitscore.job_interval
  (timeline, job window)` replaces frozen spacing constants: stages gate on a calibration stage's
  measured value (L2). Unlocks Q111, Q036, Q082 without the two slips that voided five stages.
- **T2 (N3 image b, module change, only after N3's first session shows H-PA).** A second image
  that also moves `ir0` and `tim` by `douta` to attributes 1 and 3 (pa1, pa3 then hold them):
  Q128's "what s0-s2 of the started program become" and Q057's `tim` input, and fwsim's PDS #14
  inputs. Unsafe before H-PA (an `sa` landing would overwrite sa1/sa3 the firmware holds; design
  §2 item 4), so it waits.
- **T3 (sgxfive-test, ~1 h, not recommended now).** Odd target widths for `tri` (Q240's odd-width
  clause): narrows only, since Q240 keeps the depth-bound clause (Q200).
- **T4 (kit word, not recommended).** A HWPerf group word for Q075 (low, narrow only).

## 5. Order

1. r34-csc and r34-pbe built in parallel (own dirs, own CARGO_TARGET_DIR), run r34-csc first
   (short), then r34-pbe. Records E1134 (Q010), E1135-E1136 (Q044 p1, p2/p3).
2. T1 agent in parallel with the builds (kit change, its own branch); r34-ev (Q111 + Q036, records
   E1137-E1138) built on T1 after it merges.
3. Offline Q082 fit; r34-b6 only if a form fits. Q136 if the laptop has time.
4. N3 install + boot (asked) and its own-task session after the safe sessions (R34-3).

## 6. R34 decisions

1. **R34-1 The two retirement sessions.**
   - a) Build and run r34-csc (Q010) and r34-pbe (Q044) on 7CE8E38E now (recommended: both
     safe, no tool change, the only two retirements reachable).
   - b) r34-csc only, plus a one-row second stage testing the stage boundary itself.
   - c) Neither; go to the timeline sessions.
2. **R34-2 Timeline sessions (Q111, Q036, Q082).**
   - a) T1 first, then r34-ev; Q082 only after its offline fit freezes a form (recommended: the
     two voided rounds came from hand-frozen premises).
   - b) r34-ev now with hand-frozen premises from kept snap0/job windows (no kit change).
   - c) Skip timeline work this round.
3. **R34-3 N3 (one own-task emitpds form).**
   - a) Install and boot after r34's safe sessions; its session decides fwsim's landing; T2 only
     if H-PA (recommended: fwsim value, no hw question retires from it).
   - b) Before r34's sessions (fwsim first).
   - c) Defer N3.
4. **R34-4 Q044's retirement with modes that cannot be decided safe (14 faults; 22, 34 do not
   repeat).**
   - a) Retire if every other mode decides, naming 14 from E031 and 22/34 as decided only on
     repeat-stable pixels or split into Q012 (recommended: the line asks what bit 25 does where a
     mode stores, and those modes' own formats are Q012's).
   - b) Narrow only, keep Q044 open for 14, 22, 34.
   - c) Add a flagged stage for mode 14 later (one planned fault a row).
