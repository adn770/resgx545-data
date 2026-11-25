# r45-n3j-n6

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below, **and the one-shot boot onto the new module first** (the r45-kernel
module, srcversion EC553F41FD8324BB6BF1764; the laptop's installed module is the r42-kernel one
until then: `boot-test-kernel.sh`, `test-session.sh`, then the gma500 srcversion against the
installed one, as round 42 did).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 cf20aa8703f7 (branch r45-n3j-z on
r45-n3j and main 1c8dc10e, not merged: K9, the crumbz and landq images, the fork pin at b1089172b2e7
and the kit's `pds=crumbz|landq`) and resgx545-data ebfeaa7754e4, laptop prefix `r45j6`,
HostKeyAlias `cedar`. Question Q128 (N3j): which client event lands in attribute 1, what crumbz and
landq read, and which unmapped word land's stop faults at. Design: `closing29/n3j/design.md` (§9 the
rebuild rows, §9.6 order and time; §8 the user's decisions A=a, B=a, C=a, D=b, E=c, F=a). Built
offline, frozen, not staged, not run.

**When:** after N5 (decision F (a)): wq plants M1 (the kit's K7 keeps a session's first stage on the
default begin draws), q runs landq with no draws and ends in the runner's planned stop (row Q). The
round's order: N1-N4 (done), the one-shot boot, then N5, then N6 (decision F (a)); the whole session
in one `run`.

**Module.** fork r45-kernel b1089172b2e7 (r42-kernel plus the crumbz and landq images), srcversion
EC553F41FD8324BB6BF1764, loaded = installed after the one-shot boot: control SV. mark, crumbz and
landq are its images, sbc43 its form.

## Stage wq: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wq1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wq

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it, and the rebuild touches no
other image (WJ is the build control)**; V0 and V2 are the kernel's own TA3DCtl words at the arm
(0x32004000, 0x32002000 in every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x005d3000 | ds0[4]: M13 0x005d3000 |
| 0x124 | 0x005d1000 | ds0[5]: M1 0x005d1000 |
| 0x128 | 0x00000d00 | ds1[4]: douta control 0xd00, attribute 13 |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100, attribute 1 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07084406 | movs douta, ds0[4], ds1[4] (M13 to attribute 13) |
| 0x140 | 0x07084ea6 | movs douta, ds0[5], ds1[5] (M1 to attribute 1) |
| 0x144 | 0x07003547 | movs tim (T2) |
| 0x148 | 0x07000305 | movs doutu (entry 1) |
| 0x14c | 0x07003fe7 | movs tim (T3) |
| 0x150 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage wq (predictions/wq.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r45-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3J-WQ RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user. WJ is also the build control (design §9.3): WJ failing any outcome stops
N5 for the user (the rebuild changed the arm path or the mark bytes), no Z row runs.

## Stage q: row Q, 1 row of 2 jobs, flagged, on_stop "end", begin_draws = "none"

landq after no draw (begin_draws "none", no plant): landq writes Q0 0x005d2000 to attribute 0 and M1
0x005d1000 to attribute 1 in the emit itself, so both are unmapped words with sa0 above sa1; which
does the tick pass fault at? Jobs: the emit, then command 6 on the next tick pass. Ends in the
runner's planned stop (job 2 not done: rc 4, reset, strict health with both draws).

**The arm.** `slots=0x1 entry=0 pds=landq pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image landq (`asm/fwtask/pds/landq.s`, 3 rows, control word
0x01800100).

Row q1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass); job 2: command 6 (dwords 224-255
filled with 0xdeadc0de and read as result slots 40-47, ticks, 200 ms), no kick (the next tick pass).
Then the page, snap0/snap9 and the record (each job's K5 BIF words), after an ok end the gate (the
fill then the triangle), the disarm and the end draws.

### The firmware-page write of stage q

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 18 dwords at #14's buffer address + 0x100, [0x100, 0x148) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **NEW bytes (design §9.0): land's 12 data dwords with its third row holding Q0, M1 and their
douta controls, and two douta more after land's two; the fork's sgx_own_pds.h at b1089172b2e7
carries them**; landq has no V0 or V2 words (its fill flag is 0): its words 4 and 5 are Ma and Mb.

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00001800 | ds1[1]: douta control 0x1800 (attribute 24) |
| 0x110 | 0x5a5a3a18 | ds0[2]: Ma 0x5a5a3a18 |
| 0x114 | 0x5a5a3a1a | ds0[3]: Mb 0x5a5a3a1a |
| 0x118 | 0x00001a00 | ds1[2]: douta control 0x1a00 (attribute 26) |
| 0x11c | 0x00000000 | ds1[3]: 0 |
| 0x120 | 0x005d2000 | ds0[4]: Q0 0x005d2000 (new) |
| 0x124 | 0x005d1000 | ds0[5]: M1 0x005d1000 (new) |
| 0x128 | 0x00000000 | ds1[4]: douta control 0x000, attribute 0 (new) |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100, attribute 1 (new) |
| 0x130 | 0x07040606 | movs douta (Ma to attribute 24) |
| 0x134 | 0x07042ca6 | movs douta (Mb to attribute 26) |
| 0x138 | 0x07084406 | movs douta, ds0[4], ds1[4] (Q0 to attribute 0, new) |
| 0x13c | 0x07084ea6 | movs douta, ds0[5], ds1[5] (M1 to attribute 1, new) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage q (predictions/q.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| Q-WRITE | job 1 done; post sa0 = 0x005d2000, sa1 = 0x005d1000 [infer; LV E1183] (j1 = DONE, postsa0 = 0x005d2000, postsa1 = 0x005d1000) | **held** |
| Q-SA0 | job 2 not done; K5 BIF_FAULT CID 15 at 0x005d2000 (0x005d200f) [infer, H-SA0] (j2 = notdone, j2fault = cid15 page 0x005d2000) | **held** |
| Q-LOW | the same at page 0x005d1000 (0x005d100f) [infer; held under "lowest page"] (j2 = notdone, j2fault = cid15 page 0x005d1000) | failed |
| Q-OTHER | a fault at any other page (sa2's, sa13's, page 0) (j2fault = @faultnotin:cid15 page 0x005d2000,cid15 page 0x005d1000) | printed |
| Q-SERVE | job 2 done, no fault [HW against: E1176-E1200's land stops] (j2 = done) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR and DK (printed here, not scored: no draws), SV (the
stage log's installed and loaded srcversion are the r45-kernel build's), and, read in each job's own
record and never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id,
cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the
session), J2 (job 2 done, slot 6 = M6, run id 2; printed). The RULE line `Q128-N3J-Q RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE, or Q-WRITE failed (landq's words not in sa0 and sa1): every page
outcome cannot tell. 0x005d2000 mapped (a fault at 0x005d1000 with Q-WRITE held cannot tell 'lowest'
from 'sa0 mapped'): Q-LOW held reads cannot tell, printed. DR or DK failed: not scored here (no
draws), printed. SV as the Z stages.

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (V0, V2 the kernel's at the arm):

- wq1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- q1-a (landq, 18 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00001800 0x5a5a3a18
  0x5a5a3a1a 0x00001a00 0x00000000 0x005d2000 0x005d1000 0x00000000 0x00000100 0x07040606 0x07042ca6
  0x07084406 0x07084ea6 0x07000305 0xaf000000

## Risk

Stage wq: W's [HW]. Stage q: LM's and V's (E1185, E1198): the runner's stop (rc 4), the kit's reset
and strict health recovered every land stop so far [HW]. It ends in the stop, so it is last in N6.

## Stops

J1 not DONE in any row: CANNOT TELL, stop the session. W-FAULT, or B failing in a Z row: stop for
the user; WJ failing any outcome: stop N5 for the user, no Z row runs. SV failing: N5 and N6 do not
run. Any fault other than the ones the land stage names: stop for the user. A runner stop (a job not
done, any fault outside the gate) ends the session after reset and strict health (rc 4, both draws);
the lead scores it by hand (`python3 score/score.py STAGE out/ATT/STAGE`, or runone.sh). A failed
reset (rc 13 or 5) is the user's ordinary reboot to the default entry, end of the day. A stage with
its own begin draws runs only right after its plant in the same attempt (the driver refuses --from
or --only there: status 46).

## Deviations from the design (builder)

- K9 (round 45): the scorer reads the command count from the kernel log (kit/kitscore.py `kc`): DK
  is a control that can fail, row-scoped, and prints KC and HKC lines; DK failing makes only the
  outcomes that name a K cannot tell (design §9.4: ZT-SA1, ZFT-SA1, ZF-TICK1, ZTF-SA1, ZTT-LAST,
  ZTT-FIRST), DR failing is the RULE's CANNOT TELL.
- SV (design §9.2) is read from the attempt's stage log (STAGE.log beside the kept directory: the
  preflight's `## installed module` and `## loaded module` lines): both must be
  EC553F41FD8324BB6BF1764; a missing log reads cannot tell, and SV decides the RULE with PG, E0, T0,
  J1 and DR. runone.sh checks the loaded srcversion first (exit 7).
- ZN (design §9.2, session-scoped) is read from the stage zn of the same attempt (its kept directory
  beside KEPT_DIR, or in ROOTS): ZN-SAME there (post sa0 V0, sa1 M1, sa2 V2). A missing zn reads
  cannot tell, never a pass. It makes the sa0 and sa2 outcomes of ZT, ZFT, ZF, ZFF, ZTF and ZTT
  cannot tell (the -SA1, -LAST, -FIRST and -TICK1 outcomes stand); ZN itself is a Z row with its
  plant wj.
- The Z rows' outcome kinds: TRIPLE is sa0 = 0 with a timer sa2, LF (the draw's) sa0 = 2 with a
  timer sa2, ONE sa0 = V0 with sa2 = V2; an -AOTHER outcome is any sa0, sa2 the row's other outcomes
  do not name (ZT, ZFT, ZTT: neither TRIPLE nor ONE; ZF, ZFF: neither LF nor ONE; ZTF: neither LF
  nor TRIPLE, so ONE reads -AOTHER there). It is frozen with the prediction `printed`.
- Q-OTHER reads "a fault at any other page" as a fault (not none) at neither 0x005d2000 nor
  0x005d1000; Q-LOW held reads cannot tell on the PREDICTION line (design §9.5: 'lowest page'
  against 'sa0 mapped').
- DR is read from the kernel log (exactly one `health begin try 1 LIST` between `row begin` and
  `owntask-arm`, LIST the stage's declared list; none: the register health) and the kept draw
  outputs (each exact). A begin health at try 2 or more is DK failed too (K9). Q prints DR and DK
  (no draws, design §9.5), it does not score them.
- The plant a Z stage reads is the one right before it in the same attempt (wj-zn, wk-zt, wl-zft,
  wm-zf, wn-zff, wo-ztf, wp-ztt; test_score pins the pairing); q has none.
- The job controls are printed CONTROL lines that can fail but do not decide the RULE (as round 42's
  J2): J2 (job 2 done, M6, run id 2) fails by design when the early stop holds.
- W-FAULT reads snap9's BIF_FAULT and the disarm record's (owntask.reset.json health bif_fault);
  unread (cannot tell) when snap9 is 0 and the disarm record is missing. The hooks stop the session
  on snap9's in a plant or Z stage; a fault at the disarm fails the end's register health (rc 16).
  Z-FAULT is the same reading in a Z row.
- The scorer's test attempts are round 44's kept stages (N1 wa and ff, N2 lm, pinned at
  resgx545-data ebfeaa775) as the tokens edit them (ff for every Z row, lm for q), the kernel log's
  `ccb_sent` lines rewritten to the declared lists' counts; no kept data exists for crumbz or landq.
- N6 has a plant stage wq before q (design §9.5 says q is N6's only stage, no plant): the kit's K7
  refuses `begin_draws` on a session's first stage (session.py lint), and row Q's begin draws are
  `none`. wq is row W as WJ (mark, M1 planted, no end draws) and q follows it as LM followed WL in
  round 44; Q's outcomes do not read wq (landq writes Q0 and M1 itself), the scorer prints no PLANT
  line for q. The alternative, a kit change letting a first stage declare `none`, is the lead's to
  decide.
- No frozen prediction was altered. Doubts about the design are in the builder's report.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses bit 10's douta landing, so the
replay is `refused` with that reason (design O2).

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`
(never --from or --only a stage with its own begin draws), or `bash
closing29/r45-n3j-z-logs/runone.sh N6 wq q` (stage, run, score, health draw); after a stop: `python3
score/score.py wq out/ATT/wq`, `python3 score/score.py q out/ATT/q`.
