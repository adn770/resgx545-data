# N3i: what the client draws write into attribute 1, and land's early stop with a planted sa1
(design note, not built, not run)

Status: a design for the lead to bring to the user as **flagged decisions** (§8). Nothing here is
built, committed, staged or run; no laptop, cachix or fork was touched. Tags: **[HW]** measured,
with its E number (a reading taken from a kept stage's kernel log says which stage); **[infer]**
everything else, including every hypothesis named H-*.

Paths: `R` = `/Users/jtorra/src/resgx545` (main 9076992b, records to E1187), `F` = fork
`/Volumes/linux/linux-sgx-r42` at r42-kernel ec6511d5de87, `drivers/gpu/drm/gma500/sgxfive/`,
`C` = `/Users/jtorra/src/scratch/resgx545/closing29`. The laptop runs module srcversion
079DD0D13F231EEAC52FE0F (r42-kernel): forms incl. fw14, sbc43, sb403, sb402, sb400; images v1,
crumb, halt, crumb3, land, mark, landv (`F/sgx_own_pds.h`, `F/sgx_own_regs.h`).

**The short version.** One kit change (K8: begin draws as a short sequence), no fork change, no
build, no boot. Three sessions. N1 plants M1 four times and reads attribute 1 after the draw
sequences fill-fill, triangle, triangle-fill and fill-triangle (crumb3, one quiet job each), then
once after a fill with no plant. It splits an event count (H-N) from a per-kind constant (H-LAST)
and from the kick count (H-K). N2 runs land on W's planted bank with no draws (row LM). It splits
"the early stop reads sa0, then sa1" (H-SA0) from "land stops at page 0 whatever the bank holds"
(H-IMG). N3 (optional) runs land after one fill (row LF): the fill's words in attributes 0 and 2,
and LC's page 0 again from the other side.

## 0. What round 43 left, and the earlier rows' draws

- **Attribute 1 keeps its word with no draws** [HW, E1185]: across W's disarm and exit resets, V's
  begin reset, the register health, V's arm (firmware reload, GETMISCINFO) and tick passes.
- **One fill rewrites it** [HW, E1187]: M1 became **0x01000000** after one stock fill, against
  F-FILL4's 0x04000010. Attributes 3-12 and 13 (M13) were unchanged; 0 and 2 were crumb3's own V0
  and V2, so what the fill writes there was not read [HW, E1187 survey].
- **landv's early stop faults at sa1's page** [HW, E1183 at 0x04400000, E1185 at M1], with sa0 = V0.
  **land's faulted at page 0** [HW, E1176, E1178], with post sa0 0, sa1 0x04400000 and sa2
  0x0104b95b (H3) or 0x01030b00 (LC2).
- **The bare kick pass faults at sa13's page, and then the EDM serves nothing** [HW, E1187].
- **The kick count** [HW, E746, E768]: pa1 bits 31:24 of every PDS #13 entry count the GETMISCINFO
  writes since the firmware load; a kick entry carries the count before it. Every kit reset ends in
  the boot's own GETMISCINFO (`R/HACKING.md`, "Session kit").
- **The events a draw raises** [HW, E747]: a fill gives (0:8, 3:4, 0:8), one non-kick entry; a
  64x64 triangle gives (0:8, 1:9, 3:4, 3:22, 0:8 x5), three non-kick entries, 3:22 about 5.6 us
  after 3:4. Every entry has pa0 = 0 and pa2 an EVENT_TIMER sample.
- **The arm reloads the firmware** [HW, every stage's kernel.log: "SGX power-off", "SGX stopped, N
  events seen", "SGX firmware DDK ... loaded" at `owntask-arm`]. So the draws that matter are the
  ones after the stage's begin reset, and any state that lives in firmware memory starts afresh at
  that reset.

### 0.1 The draw sequences behind 0x04400000 and 0x04000010 [HW, kernel logs]

Read from each stage's `kernel.log` (marks `row begin`, `health begin try N`, `owntask-arm`):

| row | E | sa1 | before the arm, after the begin reset | row begin | at the arm |
|---|---|---|---|---|---|
| B11 | E1172 | 0x04400000 | fill, tri (try 1) | 3 events seen | 3 events seen |
| X | E1174 | **0x04000010** | fill, tri (try 1) | 0 events seen | 3 events seen |
| Y | E1175 | 0x04400000 | fill, tri (try 1) | 3 events seen | 3 events seen |
| LC (H3) | E1176 | 0x04400000 | fill, tri (try 1) | 3 events seen | 3 events seen |
| LC2 | E1178 | 0x04400000 | fill, tri (try 1) | 3 events seen | 3 events seen |
| Q | E1182 | 0x04400000 | fill, tri (try 1) | 0 events seen | 3 events seen |
| LV | E1183 | 0x04400000 | fill, tri (try 1) | 3 events seen | 3 events seen |
| F | E1187 | **0x01000000** | fill (K7) | 0 events seen | 1 events seen |
| V | E1185 | M1 (kept) | none (K7) | 0 events seen | 0 events seen |

- Seven rows ran the same sequence: begin reset, one fill, one 64x64 triangle, the arm. Six read
  0x04400000, X read 0x04000010 [HW]. What the stage before left ("row begin" 0 or 3 events) did
  not matter: X and Q both followed a stage that ended with no draws since its last reset [HW].
- The top byte was 4 in all seven, 1 after the fill alone [HW]. Bits 23:0 were bit 22 (6 of 7) or
  bit 4 (X) after a triangle last, and 0 after a fill last [HW].
- "events seen" is the kernel's software-event counter (`F/sgxfive.c:436`): fill 1, fill and
  triangle 3 [HW]. It is not the top byte (3 against 4). It is printed in every row, never scored.

### 0.2 Readings of the attribute-1 word [infer]

All four fit F and the seven FT rows; they differ on the sequences no row has run.

- **H-N (event count).** Bits 31:24 count the non-kick client events (E747's slots 1-3) since the
  last firmware load: fill 1, triangle 3, so fill-then-triangle 4. Bits 23:0 follow the last draw:
  0 after a fill, bit 22 (rarely bit 4) after a triangle. That the writer is the event PDS program
  or its task is not claimed.
- **H-LAST (per-kind constant).** The last draw's kind alone sets the word: a fill 0x01000000, a
  triangle 0x04400000 (or 0x04000010). Nothing accumulates.
- **H-K (pa1 verbatim).** Attribute 1 takes the pa1 of the last slot-1-to-3 entry, with E746's kick
  count. With k kicks before the first draw it predicts 0x0(k+1)000010 for a fill and 0x0(k+3)400000
  for fill-then-triangle. F needs k = 0, the FT rows need k = 1: no one k fits both. So H-K already
  fails on F (E1187). It is kept as a check that costs nothing.
- **H-ACC (read-modify-write).** Each event adds 1 to attribute 1's own top byte and rewrites the
  low bits. M1's top byte is 0, so after a plant it predicts as H-N. Q argues against it: Q read 4
  after a stage that ran many draws (S's gate and end draws, Q's begin draws), not 4 more than the
  word before. Only an unplanted read (row F2) tests it directly.

| row | begin draws (after a plant, unless said) | H-N | H-LAST | H-K (k = 1) | H-ACC |
|---|---|---|---|---|---|
| FF | fill, fill | **0x02000000** | 0x01000000 | 0x04000010 | 0x02000000 |
| T | tri | **0x03400000** (or 0x03000010) | 0x04400000 (or ..10) | 0x02400000 | as H-N |
| TF | tri, fill | **0x04000000** | 0x01000000 | 0x08000010 | as H-N |
| FT | fill, tri (control) | 0x04400000 (or ..10) | as H-N | as H-N | as H-N |
| F2 | fill, no plant, after TF | 0x01000000 | 0x01000000 | 0x02000010 | **0x09000000** |

H-K's numbers come from E747's entries: a fill adds 2 kicks, a triangle 6, and the boot 1 (k = 1).
H-ACC's F2: TF's read 0x04, plus TF's end draws (fill, triangle: 4), plus F2's fill (1).

### 0.3 LC's page 0 [infer]

- **H-SA0.** A tick pass on the rebased bank reads through sa0 (TA3DCtl), then sa1 (HostCtl), and
  stops at the first unmapped one (E002 names them; that BIF_FAULT keeps the first fault is not
  settled by any record). LC's sa0 was 0, so page 0. LV's and V's sa0 was V0, so sa1's page. LC's
  sa0 = 0 and sa2 = an EVENT_TIMER sample look like an event entry's pa0 and pa2 (E746). So the
  draws may write attributes 0 and 2 as well as 1.
- **H-IMG.** land itself stops at page 0, whatever sa0 holds. landv differs from land only by two
  `douta` (V0 and V2 to attributes 0 and 2), so landv's own writes would be what moved the stop.
- **What tells them apart.** Give land the bank V had: plant M1 with W, then no draws. If
  attributes 0 and 2 keep W's V0 and V2 the way attribute 1 kept M1 (E1185), land's bank equals
  V's word for word. H-SA0 predicts the stop at M1's page. H-IMG predicts page 0. The row reads
  post sa0 itself, so a sa0 that did not keep V0 is seen, not assumed (§3.6's cannot-tell rule).
  LC's sa1 page was never tested while sa0 was 0; that would need sa0 = 0 with M1 planted, which no
  image on the module writes (§4, the rebuild alternative).

## 1. Rows, one line each

| row | session | question | image | draws before the read |
|---|---|---|---|---|
| WA-WE | N1 | plant M1 (W of E1184 byte for byte), no pass after | mark | default |
| FT | N1 | control: the plant-based read gives the seven rows' word | crumb3 | fill, tri |
| FF | N1 | two fills: count (0x02) or constant (0x01) | crumb3 | fill, fill (K8) |
| T | N1 | a triangle alone: 0x03 or 0x04 | crumb3 | tri |
| TF | N1 | triangle, then fill: the low bits and the count 4 | crumb3 | tri, fill (K8) |
| F2 | N1 | a fill with no plant, after a triangle-ending stage: H-ACC | crumb3 | fill |
| WL | N2 | plant M1 | mark | default |
| LM | N2 | land on W's bank, no draws: page M1 or page 0 | land | none |
| WF | N3 | plant M1 | mark | default |
| LF | N3 | land after one fill: the fill's attributes 0-2 and the page | land | fill |

Every row: blob `emitsb_sbc43s`, `form=sbc43` (sideband 0xc43, bit 10), `pdsat=fw14`. Every blob,
image and form is on the running module. mark and crumb3 ran on it in rounds 42-43 [HW, E1180,
E1182, E1184-E1187]. land ran on the r40 module (E1163, E1176, E1178). The r42-kernel header keeps
its words unchanged: `git diff r40-kernel r42-kernel -- sgx_own_pds.h` only appends after land's
array. No new firmware bytes (§3).

## 2. Kit change K8 (no rebuild; tests first)

**K8, draw sequences** (`R/tools/closing/kit/lib_kit.sh` `health_ok`, `stage_health`;
`run_stage.sh`'s draws check; `session.py` `OWNTASK_DRAWS`; lint; the fake laptop):

- `begin_draws` and `end_draws` take `"none"` or a comma list of 1 to 3 items from `fill` and `tri`,
  run in order. `"fill,tri"`, the default, keeps today's `health` path (retries after a reset).
  Any other list runs once through `health_ok`: every draw must be exact, else a reset, both draws
  (the recovery) and rc 16, as K7's `fill` and `tri` do today. Recovery paths still draw both.
- Each draw's output is kept under its own name (`NAME.fill<HN>.<i>`, `NAME.health<HN>.<i>`). Today
  two fills in one `health_ok` call would overwrite the same name. The health mark names the list
  (`health begin try N fill,fill`).
- Lint and `run_stage.sh` refuse an empty item, an unknown word, more than 3 items, and `none`
  inside a list (exit 7). K7's rule stays: a non-default `begin_draws` only on a stage that is not
  its session's first, and the driver never starts an attempt there (status 46).
- Tests, red first: the fake laptop's marks and kept files show `fill,fill` and `tri,fill` in order,
  under distinct names; a failed second draw recovers and stops (rc 16); the default keeps its
  retry; lint's refusals.

**Scorer support (no kit change):** a read stage reads PLANT from the plant stage right before it
in the same attempt (round 43's rule, now with four plant stages in one session: the test pins the
pairing WA-FT, WB-FF, WC-T, WD-TF). DR is a row-scoped control (§3): the read stage's health mark
names the declared list at try 1, and each kept draw output is exact.

Carried unchanged: K1-K7 (job lists, `sleep_ms`, `gate_order`, devcoredumps, hooks print and never
stop, the gate's failure a scored end, the per-job BIF words with `mid`, kick-only jobs, the draw
keys and `own_gate`).

## 3. Rows, frozen predictions

Common: arm `slots=0x1 entry=0 pds=<img> pdsat=fw14 form=sbc43`, blob `emitsb_sbc43s` (emit word
0xfb20b18800c08184, `emitpds.tasks.taske #0, r2, r3, r4, #0xc43`), `#limit 0`, flagged, on_stop
"end". Job 1 = command 1: slots 2-5 and dwords 128-223 filled with 0xdeadc0de first, `"ticks":
true`, 200 ms, no kick (the emit on the timer pass). A cmd-6 job fills dwords 224-255 first.

U0 = 0x080401ef in every row (TRC 8, CBASE 15, index 0x4000 + 30, `emitsb_sbc43s`'s entry 1)
[HW, E1184-E1187]; the builder confirms it at the freeze. V0 and V2 are the kernel's TA3DCtl dwords
0 and 2 at the arm (0x32004000 and 0x32002000 in every round 42-43 snap0 [HW]).

Controls, all of which can fail:

- **row-scoped** (the row's page and registers): PG (page dword 0); T0 (snap0's timer running); B
  (BIF_FAULT 0 in snap9; where an outcome names a fault, that outcome reads B, the rule frozen in X,
  LC2, LV, V and F); **DR** (read rows: the declared begin draws ran at try 1, each exact, no other
  draw between the begin reset and the arm).
- **job-scoped, read in that job's own record, never on the row-end page** (the H3 slip, E1176):
  E0 (job 1's slot 1 = M1 0x5a5a3301 with run id 1, `cmd_after` 0); J1 (job 1 DONE: X0, S1, M4 with
  its run id, `done`; else CANNOT TELL and stop the session); for each later job, its own `done`,
  slot and run id, and its after-read from its own `slots`; each job's K5 words (`pre`, `mid`,
  `post`) from its own record.
- **PLANT** (read rows but F2): W-SA1 of the plant stage right before it in the same attempt, read
  from that stage's job 1 record.

Printed, never scored: the arm line; each job's Δtick and kick reply; K5's words; the survey (pre,
post, each after-read, where they differ); post sa0, sa2, sa3-sa12 and sa13; every fault page
against job 1's post sa0, sa1, sa2 and sa13; the kernel's "events seen" lines. Expected: FF 2, T 2
[infer], TF 3 [infer], FT 3 [HW, §0.1], F2 1 [HW, E1187].

### 3.1 Plant stages WA, WB, WC, WD (N1), WL (N2), WF (N3)

Row W of E1184 and E1186 byte for byte: image **mark**, one job (job 1 only, no kick, no cmd 6),
default begin draws, `own_gate = "none"`, `end_draws = "none"` (K7). T3 stops the tick, so no pass
runs on the rebased bank before the disarm reset [HW, E1184, E1186].

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | TA3DCtl dword 0 at the arm |
| 0x114 | V2 | TA3DCtl dword 2 at the arm |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 |
| 0x120 | 0x005d3000 | ds0[4]: M13 |
| 0x124 | 0x005d1000 | ds0[5]: M1 |
| 0x128 | 0x00000d00 | ds1[4]: douta control 0xd00 (attribute 13) |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100 (attribute 1) |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07084406 | movs douta, ds0[4], ds1[4] (M13 to attribute 13) |
| 0x140 | 0x07084ea6 | movs douta, ds0[5], ds1[5] (M1 to attribute 1) |
| 0x144 | 0x07003547 | movs tim (T2) |
| 0x148 | 0x07000305 | movs doutu (entry 1) |
| 0x14c | 0x07003fe7 | movs tim (T3) |
| 0x150 | 0xaf000000 | halt |

| outcome | rule | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 | **held** [HW, E1184, E1186] |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 | **held** [HW, E1184, E1186] |
| W-QUIET | snap9 BIF_FAULT 0 | **held** [HW, E1184, E1186] |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) | failed |

**Cannot tell.** J1 not DONE: stop the session. W-SA1 failing: the next read's outcomes read cannot
tell (it runs, printed). W-FAULT: stop the session for the user.

**Risk.** W's, run twice [HW, E1184, E1186]: quiet, no pass after the emit.

### 3.2 Read stages FT, FF, T, TF (N1, each right after its plant)

Image **crumb3**, G2 q's and F's 19 dwords byte for byte. Stage keys: `begin_draws` as the row says
(FT `"fill,tri"`, written out so the stage reads as its siblings do; FF `"fill,fill"`, T `"tri"`,
TF `"tri,fill"`), `own_gate = "none"`, `end_draws` default. **One job**: job 1 only, no kick, no
cmd 6. T3 stops the tick, so the row is as quiet as B11, W and W2 [HW, E1172, E1184, E1186], and
the gate's planned fault at sa13 (M13) does not happen (no gate).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | TA3DCtl dword 0 at the arm |
| 0x114 | V2 | TA3DCtl dword 2 at the arm |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07003547 | movs tim (T2) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0x07003fe7 | movs tim (T3) |
| 0x148 | 0xaf000000 | halt |

Common to the four: X-QUIET (snap9 BIF_FAULT 0) **held** [HW, E1172, E1184, E1186]; X-KEEP (post
sa1 = M1: the draws did not write it) failed [HW for a fill, E1187; infer for a triangle, the seven
FT rows]; X-OTHER (any word no row names) printed. All words below are job 1's post sa1.

**FT (control; first read of N1).**

| outcome | rule | prediction |
|---|---|---|
| FT-SAME | 0x04400000 or 0x04000010 | **held** [HW: the seven rows of §0.1] |

**FF.**

| outcome | rule | prediction |
|---|---|---|
| FF-N | 0x02000000 | **held** [infer, H-N; H-ACC alike] |
| FF-LAST | 0x01000000 | failed [infer, H-LAST] |
| FF-K | 0x04000010 | failed [infer, H-K] |

**T.**

| outcome | rule | prediction |
|---|---|---|
| T-N | 0x03400000 or 0x03000010 | **held** [infer, H-N; H-ACC alike] |
| T-LAST | 0x04400000 or 0x04000010 | failed [infer, H-LAST] |
| T-K | 0x02400000 or 0x02000010 | failed [infer, H-K] |

**TF.**

| outcome | rule | prediction |
|---|---|---|
| TF-N | 0x04000000 | **held** [infer, H-N; H-ACC alike] |
| TF-LAST | 0x01000000 | failed [infer, H-LAST] |
| TF-K | 0x08000010 | failed [infer, H-K] |
| TF-TRI | 0x04400000 or 0x04000010 (the triangle's word survives the fill) | failed [infer] |

**What the four settle.** FF-N, T-N and TF-N together: the top byte counts client events since the
firmware load (fill 1, triangle 3), and the low bits follow the last draw's kind. FF-LAST, T-LAST
and TF-LAST together: a per-kind constant. FF-K, T-K and TF-K together: pa1 verbatim (against F).
A mix is printed with the rows' words: no single reading. TF-TRI says a fill writes attribute 1
only when no triangle ran since the load. FT-SAME ties the plant-based reads to the seven rows.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop N1. PLANT failed: the row's outcomes read cannot
tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a reset and
draws, so it changes the count): cannot tell. FT-SAME failing: comparisons with the seven earlier
rows read cannot tell; FF, T and TF still compare among themselves (one frame). B failing (a fault
with no pass planned): stop the session for the user.

**Risk.** B11's, W's and F's job 1 (E1172, E1184, E1187), with no kick and no gate: quiet in every
run [HW]. New: `fill,fill` and `tri,fill` as begin draws, which are stock client draws. A triangle
right after a reset already runs in every recovery path [HW]. The stray `[sa14 + 0xb0]` append stays
as in X [infer].

### 3.3 Read stage F2 (N1, last, no plant)

crumb3 as §3.2, one job, `begin_draws = "fill"`, `own_gate = "none"`, right after TF, whose end
draws are the default (fill, triangle). So the word before F2's fill is the triangle-ending word of
TF's end draws, not M1. N1's only unplanted read.

| outcome | rule | prediction |
|---|---|---|
| F2-N | 0x01000000 (F again, whatever the word before) | **held** [HW, E1187; infer] |
| F2-ACC | 0x09000000 | failed [infer, H-ACC] |
| F2-K | 0x02000010 | failed [infer, H-K] |
| F2-PRIOR | 0x04400000 or 0x04000010 (the fill did not write it) | failed [HW against: E1187] |
| F2-OTHER | any other | printed |
| F2-QUIET | snap9 BIF_FAULT 0 | **held** |

**Cannot tell.** J1 not DONE. DR failed. TF's end health not ok at try 1 (the word before F2's fill
is then not the one assumed): F2-ACC and F2-PRIOR cannot tell; F2-N still stands.

**Risk.** As §3.2.

### 3.4 Session N2, stage LM: land on W's bank, no draws (last in N2)

Image **land**, the 16 dwords of rows L, H3 and LC2 (round 40-41's bytes; round 42 did not run
land) byte for byte. Stage keys: `begin_draws = "none"` (K7). Between WL's emit and LM's emit run
only WL's disarm and exit resets, LM's begin reset with the register health, and LM's arm. Jobs:
V's two (E1185): job 1 the emit (land has no `tim`: the tick runs); job 2 command 6 with no kick
(the next tick pass). Against V (landv), only the two `douta` of V0 and V2 are gone.

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00001800 | ds1[1]: douta control 0x1800 (attribute 24) |
| 0x110 | 0x5a5a3a18 | ds0[2]: Ma |
| 0x114 | 0x5a5a3a1a | ds0[3]: Mb |
| 0x118 | 0x00001a00 | ds1[2]: douta control 0x1a00 (attribute 26) |
| 0x11c | 0x00000000 | ds1[3]: 0 |
| 0x120 | 0x00000000 | 0 |
| 0x124 | 0x00000000 | 0 |
| 0x128 | 0x00000000 | 0 |
| 0x12c | 0x00000000 | 0 |
| 0x130 | 0x07040606 | movs douta (Ma to attribute 24) |
| 0x134 | 0x07042ca6 | movs douta (Mb to attribute 26) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0xaf000000 | halt |

| outcome | rule | prediction |
|---|---|---|
| LM-V0 | job 1's post sa0 = V0 and sa2 = V2 (kept from WL) | **held** [infer, as E1185] |
| LM-KEEP | post sa1 = M1 | **held** [HW, E1185] |
| LM-EARLY1 | job 2 not done; K5 BIF_FAULT CID 15 at post sa1's page (M1) | **held** [infer] |
| LM-EARLY0 | the same at page 0 | failed [infer; held under H-IMG] |
| LM-EARLY13 | the same at post sa13's page (M13) | failed [HW against: E1185] |
| LM-SERVE | job 2 done | failed [HW against: E1176, E1178, E1183, E1185] |
| LM-OTHER | any other fault page | printed |

LM-V0's and LM-EARLY1's reasons: E1185's kept attribute 1, and §0.3's H-SA0.

**What LM settles.** LM-V0 and LM-EARLY1: land stops exactly as landv when the bank is the same.
The image did not cause LC's page 0; LC's bank did (sa0 = 0 from the draws, under H-SA0) [infer].
LM-V0 and LM-EARLY0: land stops at page 0 with sa0 = V0 and sa1 = M1 (H-IMG); then landv's two
extra `douta` moved V's and LV's stop, and the sa0-then-sa1 reading of §0.3 fails. LM-V0 alone also
says attributes 0 and 2 keep their words across a stage boundary with no draws, as attribute 1 does.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop. PLANT failed: LM-KEEP and the LM-EARLY outcomes
read cannot tell for row 2. LM-V0 failed with post sa0 below 0x1000: page 0 is then sa0's page under
both readings, so LM-EARLY0 cannot split H-SA0 from H-IMG (CANNOT TELL for row 2; the survey says
what rewrote attribute 0 with no draws). LM-V0 failed with another sa0: printed, and the page is
read against post sa0, sa1, sa2 and sa13.

**Risk.** V's and LV's (E1183, E1185): the EDM stops after the emit's pass; the runner's stop (rc
4), then the kit's reset and strict health with both draws recovered it each time [HW]. The bank
equals V's under LM-V0. It ends in the runner's stop, the planned end, so it is last in N2.

### 3.5 Session N3, stage LF: land after one fill (optional, decision D; last in N3)

land as §3.4, the same bytes and jobs. Stage keys: `begin_draws = "fill"` (K7, as F). The plant WF
before it gives attributes 0, 1 and 2 the known words V0, M1 and V2. Then one fill. land writes
none of attributes 0-2, so job 1's post sa0-sa2 are the fill's words or the plant's.

| outcome | rule | prediction |
|---|---|---|
| LF-SA1 | post sa1 = 0x01000000 | **held** [HW once, E1187] |
| LF-EVT | post sa0 = 0; sa2 = 0x01xxxxxx, bits 23:0 < 400000, != 0x061a70 | **held** [infer] |
| LF-TICK | post sa0 = 2 and sa2 = 0x01061a70 (a tick's words, E746) | failed [infer] |
| LF-ONE | post sa0 = V0 and sa2 = V2 (the fill writes attribute 1 alone) | failed [infer] |
| LF-AOTHER | any other sa0, sa2 | printed |
| LF-EARLY0 | job 2 not done; K5 BIF_FAULT CID 15 at page 0 | **held** [infer, H-SA0 with LF-EVT] |
| LF-EARLY1 | the same at page 0x01000000 (post sa1) | failed [infer; held under LF-ONE] |
| LF-SERVE | job 2 done | failed |

LF-EVT's reason: LC's post triple (0, 0x04400000, 0x0104b95b or 0x01030b00) after fill and
triangle has an event entry's pa0 and pa2 shape [HW values, E1176, E1178, E746; infer reading].

**What LF settles.** LF-EVT: a client fill writes attributes 0, 1 and 2 as one triple, with pa0's
and pa2's event shape. So LC's sa0 = 0 came from its draws [infer]. LF-TICK: the fill's triple is a
tick's, so 0x01000000 is a tick's pa1 at count 1 (and H-N's count reading weakens). LF-ONE: only
attribute 1 is written. Then H-SA0 predicts LF-EARLY1, and a page-0 stop would point to H-IMG.
LF-EARLY0 with LF-EVT repeats LC with another sa1 (0x01000000, not 0x04400000): with sa0 and sa1
both unmapped, the stop is at sa0's page.

**Cannot tell.** J1 not DONE. PLANT failed. DR failed. **LM-V0 failed in N2** (attributes 0 and 2
are not kept across a boundary): LF-EVT, LF-TICK and LF-ONE cannot tell whether the fill wrote them.
That is a fold-time rule, since N3's scorer does not read N2.

**Risk.** LC's and LC2's (E1176, E1178): a stop at page 0 through the EDM's list, recovered both
times [HW]. Ends in the runner's stop, so it is last in N3.

## 4. The rebuild alternative for row 2 (decision C (b))

A new image **landz**: land plus `douta` of 0 to attribute 0 and of M1 to attribute 1, V2 to
attribute 2, no `tim` (3 rows, control 0x01800100). Row LZ (no draws, no plant needed): H-SA0
predicts page 0 with sa1 = M1 known, the direct test of "sa0 before sa1". Costs: a fork commit on
r42-kernel (image, KUnit red then green), the Mac shim, a cachix build (about 45 min unattended),
install, a one-shot boot with the user's OK, the srcversion check, a build control (G1 c again).
Not recommended: LM (with LC and LF) gives the same split without a boot, unless LM-V0 fails.

## 5. Offline first (no laptop)

- **O1 (records).** Round 43 is folded (E1184-E1187 on main 9076992b). §0.1's table is read from
  kept kernel logs and goes into this round's fold notes, not a new record.
- **O2 (sim in sync).** sgx-sim keeps attribute 1 and stalls the EDM after a bit-10 kick pass
  (9076992b). Bit 10's douta landing stays refused, so the sessions' replay is `refused` with that
  reason. After the fold, model only what N1-N3 measure (the client draws' attribute-1 word and,
  with LF, attributes 0 and 2).
- **O3.** No fork change, no shim run. The kit's mock: K8's worlds (two draws in order, a failed
  second draw), four plant/read pairs in one session, LM's and LF's stops.

## 6. Build needs, run order, laptop time

**Build.** None on the fork or cachix, no boot. resgx545 branch `r44-n3i` off main 9076992b: K8 with
tests (red, then green) first; scorers for the plant, read, F2, LM and LF rows (the PLANT pairing
and DR included); sessions N1 (`r44i1`: wa, ft, wb, ff, wc, t, wd, tf, f2), N2 (`r44i2`: wl, lm)
and N3 (`r44i3`: wf, lf), frozen with srcversion 079DD0D13F231EEAC52FE0F and data pins at
resgx545-data b3df8fc21 or later (round 43's kept stages as the scorer's test attempts: N1 w,
N1 v, N2 f); `run_all`; check. Firmware-page writes: mark and crumb3 (round 42-43's bytes), land
(round 40-41's bytes, its first run on the r42 module). Each needs the user's OK before the run.

**Recovery.** Every own-task stop and gate fault so far was recovered by the watchdog or the kit's
reset (round 40: 7 of 7; round 41: 5 of 5; round 42: M, Q, LV; round 43: V, F) [HW]. A failed reset
(rc 13 or 5) means the user's ordinary reboot to the default entry.

**Stop conditions.** J1 not DONE in any row: CANNOT TELL, stop that session. W-FAULT, or B failing
in a read row: stop for the user. Any fault other than the ones LM and LF name: stop for the user.
A failed reset: the user's reboot, end of the day.

**Run order.** Offline: K8 (tests red, then green), scorers, sessions, mock, `run_all`, check.
Then:

1. N1 (all quiet, ends with rc 0 after f2's end draws);
2. N2 (ends in LM's planned stop);
3. N3, if decision D (a) (ends in LF's planned stop).

N1 first: it carries no planned stop. N2 before N3, because LM-V0 is the premise of LF's attribute
0 and 2 outcomes.

**Laptop time.** Round 43's two-stage sessions took about 45 s each on the laptop, stop and
recovery included [HW, r43-n3h-logs timestamps]. N1 (9 stages) about 4-5 min, N2 and N3 about 1
min each, plus staging, scoring and the health draw after each session: about 15 min attended in
all, no build time.

## 7. Rejected alternatives

- **land as the reader of every row-1 sequence** (to see attributes 0 and 2 after each). Every row
  would end in an early stop. One land read after a fill (LF) answers the question at one stop's
  cost.
- **Two fills across a stage boundary** (the plant's `end_draws = "fill"` plus the read's
  `begin_draws = "fill"`) instead of K8. A reset and firmware load sit between the fills, so this
  asks "does the count survive a load?", not FF's question. §0.1 already answers no [HW: seven
  rows read 4 whatever the stage before ran].
- **No plant before the reads.** A sequence that does not write attribute 1 would show the previous
  stage's word, not M1, and could not be told from a rewrite. F2 is the one deliberately unplanted
  read.
- **A triangle with `-n 3`, or a copy, as a draw.** These would split "event count" from "draw
  weight" further (E747: three renders give 9 non-kick entries). They need health-tool variants in
  the kit; left for a later round if H-N holds.
- **A kick or a gate in the read rows.** The kick pass faults at sa13 and then the EDM stalls
  [HW, E1187]: it adds a stop and reads nothing about attribute 1.
- **landv for row 2.** It rewrites attributes 0 and 2 itself; land is the image LC ran.

## 8. User decisions (one at a time)

- **A. Row 1's route:** (a) K8 (draw sequences, kit-only, tests first) and reads FT, FF, T, TF
  (recommended: FF, T and TF each split H-N, H-LAST and H-K, and FF is the count's sharpest test);
  (b) no kit change: FT and T only (T alone splits the three readings; FF and TF stay unread);
  (c) T only.
- **B. Row F2** (an unplanted fill after a triangle-ending stage, against H-ACC): (a) include, last
  in N1 (recommended: one quiet stage, and F's word repeated once more); (b) drop (Q already argues
  against H-ACC [infer]).
- **C. Row 2's route:** (a) LM, no rebuild: plant M1 with W, then land with no draws (recommended:
  no boot; it splits H-SA0 from H-IMG unless attribute 0 is not kept); (b) the rebuild of §4 (image
  landz, fork commit, cachix, boot, build control); (c) skip row 2.
- **D. Row LF** (land after one fill: the fill's attributes 0 and 2, and the page with sa0 from a
  draw): (a) include, its own session N3 after N2 (recommended: the only no-boot read of what a
  draw writes into attributes 0 and 2, at one recovered stop's cost); (b) skip.
- **E. Order:** (a) N1, then N2, then N3 (recommended: the quiet session first; LM-V0 is LF's
  premise); (b) N2 first (row 2 before row 1), then N1, then N3.
