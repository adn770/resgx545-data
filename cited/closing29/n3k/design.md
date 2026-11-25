# N3k: which page land's stop keeps, whether two fills write attribute 1, and B5/B6
(design note, not built, not run)

Status: a design for the lead to bring to the user as **flagged decisions** (§9). Nothing here is
built, committed, staged or run; no laptop, cachix or fork was touched. Tags: **[HW]** measured,
with its E number; **[infer]** everything else, including every hypothesis named R-* or H-*.

Paths: `R` = `/Users/jtorra/src/resgx545` (main 7399bf3c pushed, local 908b7e96; records to
E1233), `F` = the fork `/Volumes/linux/linux-sgx`, branch `resgx545` = r45-kernel b1089172b2e7,
`drivers/gpu/drm/gma500/sgxfive/` (read with `git show`, nothing checked out), `C` =
`/Users/jtorra/src/scratch/resgx545/closing29`. The laptop runs 7.3.0-resgx545 with module
srcversion EC553F41FD8324BB6BF1764 (r45-kernel): images v1, crumb, halt, crumb3, land, mark,
landv, crumbz, landq (`F/sgx_own_pds.h`); forms incl. fw14, sb043, sb803, sbc43
(`F/sgx_own_regs.h`). Round 45's logs: `C/r45-n3j-logs`, `C/r45-n3j-z-logs`; its kept stages
under `C/r45-n3j-n1..n6/out/`.

**The short version.** Every early stop of land read so far fits two readings of which page the
BIF keeps: R-LOW (the lowest faulting page of the words the pass reads) and R-SA0 (sa0 is read
first, and 0x005d2000 is mapped) (§0.2). No row on the installed module can split them: no image
or draw on it puts in sa0 a word on a page known unmapped and above sa1's (§1). One fork commit
adds two images of 18 dwords, each a two-word change of an image already run (landq, landv):
**landr** (sa0 0x04400000, sa1 M1: both pages faulted before, sa0's higher) and **landp** (sa0 V0,
mapped; sa1 0x005d2000: reads directly whether that page is mapped). R-LOW predicts the stop at
M1's page in R and at 0x005d2000 in P; R-SA0 at 0x04400000 in R and no stop at 0x005d2000 in P.
Before the boot, on the installed module: B5 (0x043) and B6 (0x803) from the re-pinned copies,
frozen as they are (§4.6); LFF twice more with land after two fills, a crumbz read of the same
list in the same session, and land after three fills (whether 0x04000010 comes back, and whether it
is the second fill's entry or the last's, §0.4); and a second read of Q.

## 0. What round 45 left

### 0.1 Where land stops [HW]

Every land-family row ended in the planned early stop. Job 2's K5 pre already held the fault, list
15, so the fault came on a tick pass between the emit and job 2:

| row | E | image | post sa0 | post sa1 | fault page |
|---|---|---|---|---|---|
| LC, LC2 | E1176, E1178 | land | 0 | 0x04400000 (LC2) | 0 |
| LV | E1183 | landv | V0 0x32004000 | 0x04400000 | 0x04400000 |
| V | E1185 | landv | V0 | M1 0x005d1000 | 0x005d1000 |
| LM | E1198 | land | V0 | M1 | 0x005d1000 |
| LF, LF2 | E1200, E1213 | land | 0x00000002 | M1 | 0 |
| LT | E1215 | land | 0 | 0x02400000 | 0 |
| LFF | E1217 | land | 0 | 0x04000010 | 0 |
| Q | E1233 | landq | Q0 0x005d2000 | M1 | 0x005d1000 |

In every row after a plant, post sa13 = M13 0x005d3000 and was never the fault page [HW, E1198,
E1200, E1213, E1215, E1217, E1233].

### 0.2 The two readings [infer]

- **R-LOW.** The pass reads (at least) sa0 and sa1; when more than one is unmapped, the BIF keeps
  the lowest faulting page. Page 0 whenever sa0 is below one page; sa1's page when sa0 = V0
  (mapped); M1's in Q because 0x005d1000 < 0x005d2000, both unmapped.
- **R-SA0.** The pass reads sa0 first and stops at the first unmapped word (round 45's H-SA0), and
  0x005d2000 is mapped, so Q's first unmapped word was sa1's.
- **"sa1 first, the BIF keeps the last fault"** gives R-SA0's pages in every row read and in every
  row of §2 (the last fault is sa0's whenever sa0 is unmapped), and needs 0x005d2000 mapped as well
  (E1233). It is carried with R-SA0 and named R-SA0' where a row could part them; none here does.
- Falsified and not carried [HW against]: "sa1 first, the first fault kept" (LF, LF2: page 0 with
  sa1 = M1 unmapped); "sa13 first" (Q: M13 unmapped in sa13, the stop at M1's page); "sa0 first"
  with 0x005d2000 unmapped (Q-SA0 failed, E1233).

### 0.3 What makes a page "known unmapped"

A page is **known unmapped** when (i) a kept stage read BIF_FAULT with that page, list 15 (the
list of every land stop), while the word stood in a bank our rows read [HW], and (ii) no page
directory our kernel builds has a table for its 4 MiB directory slot [infer, a code read]:

| page | slot | (i) the fault read [HW] |
|---|---|---|
| 0x00000000 | 0 | LC, LC2, LF, LF2, LT, LFF (E1176, E1178, E1200, E1213, E1215, E1217) |
| 0x005d1000 (M1) | 1 | V, LM, Q (E1185, E1198, E1233) |
| 0x005d3000 (M13) | 1 | M's next fill and F's kick pass, 0x005d300f, list 15 (E1180, E1187) |
| 0x04400000 | 17 | LV, 0x0440000f, list 15 (E1183) |
| 0x005d2000 (Q0) | 1 | **none**: Q stopped at the lower page (E1233) |

(ii) from the fork at b1089172: the kernel's heaps start at 0x2e000000 (`F/sgxfive.c`,
`sgx_heap_base[]`), the user heaps at 0x10000000 (`F/sgxfive_drv.c`, `sgxfive_rev1_heaps[]`), and
a client VM_MAP below them only inside the first MiB, page 0 excepted, through debugfs `vm_low`
(`F/sgxfive_vm.c`, `sgxfive_vm_check_low`), which no row of ours writes. So slots 1-63 have no
table in any directory we build, and every page in them faults on a PDE miss [infer]. Q0 sits in
slot 1 with M1 and M13, so (ii) says it is unmapped as well: R-SA0's premise is already against
our own code [infer]. But (ii) is a reading of our driver, not of the BIF: a fault read is the
rule this project scores by, and Q0 has none. Row P reads it.

V0 0x32004000 and V2 0x32002000 are **known mapped**: in the kernel data heap (0x32000000), and
LV, V and LM ran with sa0 = V0 and faulted at sa1's page, not V0's [HW, E1183, E1185, E1198].

### 0.4 LFF and attribute 1 after two fills

Post sa1 after a plant and fill,fill [HW]: M1 with crumb3 (FF E1191, FF2 E1202), M1 with crumbz
(ZFF E1227, sa0 2, sa2 timer), **0x04000010** with land (LFF E1217, sa0 0, sa2 timer). Land after
one fill kept M1 twice (LF E1200, LF2 E1213). KC begin delta 6 in LFF (DK passed) [HW].

Under H-KC [infer], an event entry's pa1 carries K, the CCB commands since the load, in bits
31:24; a fill kicks two commands, the n-th fill's slot-3 entry (3:4) carries K = 2n and the word
0x0n000010 for fill n: 0x02000010, 0x04000010, 0x06000010. So LFF's 0x04000010 is the **second
fill's** 3:4 entry, and its triple (0, 0x04000010, timer) is one entry's (pa0, pa1, pa2), where
ZFF's (2, M1, timer) is a slot-0 entry's with attribute 1 unwritten. X (E1174, crumb3, fill,tri,
no plant) read the same 0x04000010: the triangle's 3:4 at K 4, the second draw's first slot-3
entry again. Readings [infer]:

- **H-TRI** (carried): a fill's entries never write attribute 1; LFF and X were strays of the
  second draw's 3:4 entry. Repeats of fill,fill read M1 with any image.
- **H-FL** (land lets the fill's 3:4 land): with land's tick running (no `tim`, the only
  difference between land and crumbz besides the markers to 24 and 26), a fill's slot-3 entry
  writes attributes 0-2. LF and LF2 kept M1 after one fill, so H-FL needs two fills: either the
  **second** draw's entry lands (H-FL2: three fills read 0x04000010) or the **last** fill's does
  (H-FLL: three fills read 0x06000010).
- **H-RACE**: which entry lands is timing we do not control; repeats of one list disagree.

### 0.5 B5 and B6

Round 40 ran 11 sidebands from our task: bits 1:0 decide the start, 2 or 3 run the program to
done, 0 never starts it, 1 faults (E1162-E1172) [HW]. 0x043 (bit 6 with 3) and 0x803 (bit 11
with 3) were built as B5 and B6 and never run, because their condition (B1 0x003 NEVER) did not
happen; RUN for them follows from the rule only [infer]. `C/r40-n3e-b5` and `-b6` are the frozen
originals (module 83FBFD86); `C/r40-n3e-b5-r45` and `-b6-r45` are copies whose session.toml
names EC553F41, unfrozen; their own tests, guard, mock (10 worlds) and verify pass
(`C/r40-n3e-b56-logs/runall-b5-prefreeze.log`, `-b6-`). Against the originals only
`session.toml`, `run/session.env` and `tests/test_twin.py` differ: **the predictions are round
40's bytes**. Their kit is resgx545 b8528c0c (on main), the data pin 9fce0b99 (on data main).

## 1. Why the installed module cannot split R-LOW from R-SA0

What puts a word in attributes 0 and 1 on EC553F41 [HW, the records of §0.1 and E1201-E1232]:

| source | attribute 0 | attribute 1 |
|---|---|---|
| mark (plant) | V0 | M1 |
| crumb3, landv | V0 | (none) |
| land, crumbz | (none) | (none) |
| landq | Q0 0x005d2000 | M1 |
| a triangle last | 0 | its 3:22 word (0x02400000 ... 0x08400000) |
| a fill last | 2 | (none; once 0x04000010 with land, with sa0 0) |

R-LOW and R-SA0 part only when sa0 holds an unmapped page above sa1's unmapped page: then R-LOW
names sa1's page and R-SA0 sa0's. sa0 is above one page only as V0 (mapped: both name sa1's) or
Q0 (whose mapping is the open premise). Draws always rewrite sa0 below one page (page 0 under
both). So every reachable bank gives both readings the same page, or the one Q gave [infer].
Checked and refused as no-rebuild routes:

- **kpoke** writes only render, transfer and context words (`F/sgxfive_kpoke.h`), not the PDS
  image our arm copies.
- **The arm** fills U0, and V0 and V2 in _FILLV images, from the kernel's own values
  (`F/sgxfive_owntask.c`, `sgx_own_pds_put`); no arm word carries a data dword.
- **Our blob** may load and store only at the results page (verifier `SGX_OWN_WHY_BASE`), so it
  cannot rewrite the image on the firmware page; whether its own `mov` to a secondary reaches the
  attribute the tick pass reads is unread (§8).
- **Mapping 0x005d2000 through a client VM** (to test the premise the other way): VM_MAP takes
  only user heaps or the first MiB (`sgxfive_vm_check_range`, `sgxfive_vm_check_low`), and which
  directory the tick pass uses is unread.

So the split needs new image words: one fork commit (§3.2).

## 2. Rows, one line each

Module EC553F41, before the boot (no rebuild):

| row | session | question | image / form | draws before the read |
|---|---|---|---|---|
| B5 | B5 (r40 copy) | does 0x043 (bit 6 with 3) run the program | crumb3 / sb043 | kit r40 |
| B6 | B6 (r40 copy) | does 0x803 (bit 11 with 3) run the program | crumb3 / sb803 | kit r40 |
| WA | N1 | plant M1 (row W, byte for byte) | mark | default |
| ZFF2 | N1 | fill,fill with the tick stopped: M1 (4th read) | crumbz | fill,fill |
| WB | N1 | plant M1 | mark | default |
| LFF2 | N1 | LFF again: M1 (H-TRI) or 0x04000010 (H-FL) | land | fill,fill |
| WC | N2 | plant M1 | mark | default |
| LFF3 | N2 | LFF a third time | land | fill,fill |
| WD | N3 | plant M1 | mark | default |
| LF3F | N3 | three fills: M1, 0x04000010 (H-FL2) or 0x06000010 (H-FLL) | land | fill,fill,fill |
| WE | N4 | plant M1 | mark | default |
| Q2 | N4 | Q again: the stop at M1's page | landq | none |

Module of fork r46-kernel (one build, one one-shot boot):

| row | session | question | image | draws |
|---|---|---|---|---|
| WF | N5 | build control on the new module, plant | mark | default |
| R | N5 | sa0 0x04400000 over sa1 M1, both known unmapped: whose page | landr | none |
| WG | N6 | plant | mark | default |
| P | N6 | sa0 V0 (mapped), sa1 0x005d2000: is that page mapped | landp | none |
| (WH, R2) | N7 | decision E: R's second read | landr | none |
| (WI, P2) | N8 | decision E: P's second read | landp | none |

Every N row: blob `emitsb_sbc43s`, `form=sbc43` (sideband 0xc43, bit 10), `pdsat=fw14`, as round
45. Draw lists are K8's (1-3 fill/tri items; `fill,fill,fill` is a list of 3). Each session's
first stage is a plant with the default begin draws (the kit refuses `begin_draws = "none"` on a
first stage). Each land-family read ends in the planned stop, so it is the last stage of its
session.

## 3. Changes

### 3.1 Kit (resgx545, branch `r46-n3k` off main; tests first)

- **K10, the arm words** `pds=landr` and `pds=landp` (as ff6e5c3d did for mark and landv and
  cf20aa87 for crumbz and landq), with the tests: the guard accepts them in an arm line, refuses
  an unknown name, and the scorer's FILLV table names landp 1 and landr 0.
- **Scorers** for ZFF2, LFF2, LFF3, LF3F, Q2, R, P (and R2, P2), with the PLANT pairing, DR, DK
  and SV controls of round 45 (§4.1), and two new kinds of rule: a job 2 fault page from a list of
  candidates (R, P), and an `@faultnotin` printed outcome for each. Red then green on round 45's
  kept stages as fixtures: LFF (E1217) must score LFF2-FILL2 held and LFF2-KEEP failed; LF2
  (E1213) LFF2-KEEP's sa1 rule held; Q (E1233) Q2-SAME held; a doctored copy of Q with the fault
  at 0x005d200f must score Q2-SAME failed.
- No change to `run_stage.sh`, `lib_kit.sh` or the laptop tools.

### 3.2 The fork commit: images landr and landp (only if decision A (a), (b) or (c))

Two `.s` files under `R/asm/fwtask/pds/`, assembled with pds-asm, the header regenerated by
`tools/fwtask/gen_verify.py`; no firmware bytes. Each is a two-dword change of an image already
run on this hardware, program words byte for byte:

**landr** (18 dwords, _FILLV 0): landq (E1233) with dword 8 (ds0[4], the word to attribute 0)
0x005d2000 -> **0x04400000**. Data: U0, 0, 0, 0x1800, Ma 0x5a5a3a18, Mb 0x5a5a3a1a, 0x1a00, 0,
0x04400000, M1 0x005d1000, 0 (attribute 0's control), 0x100 (attribute 1's); program landq's:
`douta` Ma to 24, Mb to 26, ds0[4] to 0, ds0[5] to 1, `doutu`, `halt` (0x07040606, 0x07042ca6,
0x07084406, 0x07084ea6, 0x07000305, 0xaf000000). No `tim`: the tick runs, as land's.

**landp** (18 dwords, _FILLV 1): landv (E1183, E1185) with dword 9 (ds0[5]) Mb -> **Q0
0x005d2000** and dword 10 (ds1[4]) 0x1a00 -> **0x100**. Data: U0, 0, 0, 0 (attribute 0's
control), V0, V2 (the kernel's), 0x200, 0x1800, Ma, Q0, 0x100, 0; program landv's: V0 to 0, V2
to 2, Ma to 24, ds0[5] to attribute 1, `doutu`, `halt` (0x07040606, 0x07042ca6, 0x07082606,
0x07084ca6, 0x07000305, 0xaf000000).

Why 0x04400000 and not M13 for landr's sa0: every plant leaves M13 in sa13 (§0.1), so a fault at
0x005d3000 could be sa0's or sa13's; 0x04400000 is known unmapped (§0.3) and stands in no other
attribute after a plant with no draws (post sa3-sa31 equal the plant's, E1233).

The commit: worktree `/Volumes/linux/linux-sgx-r46`, branch `r46-kernel` off `resgx545`
b1089172b2e7, its stub twin `r46-red`; the message ends with **"Assisted-by: LLM"**, never
Co-Authored-By. KUnit red first on the Mac shim (r46-red: the two names in the table with zero
words; the word tests fail), then green (round 45: 48 of 48 green, 45 of 48 red). Tests: each
image's words equal the assembled `.s`; the arm parse takes `pds=landr` and `pds=landp`; landp's
dwords 4 and 5 are the arm's V0 and V2, landr's stay Ma and Mb. Then the cachix series check and
the module build (`C/kernel39c/deliver-cachix.sh` with TIPB=r46-kernel REDB=r46-red; about 45
min unattended), install, the one-shot boot with the user's OK, the srcversion check. No other
image or form changes: WF reproduces row W as the build control (as WJ did, E1218).

## 4. Rows, frozen predictions

### 4.1 Common (N1-N8)

As n3j §3 and §9.2: arm `slots=0x1 entry=0 pds=<img> pdsat=fw14 form=sbc43`, blob
`emitsb_sbc43s`, `#limit 0`, flagged, on_stop "end"; job 1 = command 1, slots and dwords filled
with 0xdeadc0de first, `"ticks": true`, 200 ms, no kick; the land-family reads add job 2 =
command 6 on the next tick pass, no kick. U0 = 0x080401ef; V0 0x32004000, V2 0x32002000, M1
0x005d1000, M13 0x005d3000, Q0 0x005d2000, L4 0x04400000. "timer" = top byte 0x01, bits 23:0 <
400000 and != 0x061a70.

Controls, all of which can fail: row-scoped PG, T0, B, E0, J1, **DR** (the declared list ran at
try 1, each draw exact, nothing else between the begin reset and the arm), **DK** (KC begin delta
= 2 + 2 x fills + 6 x tris), **PLANT** (W-SA1 of the plant stage right before, same attempt),
**SV** (the loaded srcversion is the session's; N5-N8: the r46-kernel build's). B and J2 fail in
every planned stop; the outcomes that name the stop read them.

Printed, never scored: the arm line; Δtick; K5's words; the survey; post sa0-sa31; every fault
page against post sa0, sa1, sa2, sa13; "events seen"; KC and HKC (H-KC's word for each entry of
the declared list).

### 4.2 Plant stages WA-WI

Row W of E1184 byte for byte: W-SA1, W-SA13, W-QUIET **held** [HW, 24 runs: E1184-E1232's
plants], W-FAULT failed. W-SA1 failing: the read after it reads cannot tell. WF is also the build
control on the new module: any outcome failing stops N5 before R.

### 4.3 ZFF2 (N1, crumbz, fill,fill, quiet)

| outcome | rule | prediction |
|---|---|---|
| ZFF2-KEEP | sa1 = M1, sa0 = 2, sa2 timer | **held** [HW 3 reads: E1191, E1202, E1227; H-TRI] |
| ZFF2-FILL2 | sa1 = 0x04000010, sa0 = 0, sa2 timer | failed [held under H-RACE] |
| ZFF2-OTHER | any other | printed |
| ZFF2-QUIET | snap9 BIF_FAULT 0 | **held** [HW, E1227] |

**Settles.** With LFF2 in the same session, module and plant procedure: an image effect (ZFF2-KEEP
with LFF2-FILL2) or none.

### 4.4 LFF2 (N1, last), LFF3 (N2): land after fill,fill

land, 16 dwords, as LFF (E1217); `begin_draws = "fill,fill"`; DK: KC begin delta 6.

| outcome | rule | prediction |
|---|---|---|
| LFFn-KEEP | sa1 = M1 | **held** [infer, H-TRI; crumb3/crumbz 3 of 3, land after one fill 2 of 2] |
| LFFn-FILL2 | sa1 = 0x04000010 (the 2nd fill's 3:4 at K 4) | failed [held under H-FL; LFF E1217] |
| LFFn-FILL1 | sa1 = 0x02000010 (the 1st fill's 3:4 at K 2) | failed |
| LFFn-OTHER | any other sa1 | printed |
| LFFn-SA0 | sa0 = 2, sa2 timer (a slot-0 entry, as ZFF, LF) | **held** [infer, with -KEEP] |
| LFFn-TRIPLE | sa0 = 0, sa2 timer (the 3:4 entry's triple, as LFF) | failed [held under H-FL] |
| LFFn-PAGE0 | job 2 not done; BIF_FAULT list 15 at page 0 | **held** [HW 6 of 6 with sa0 < page] |
| LFFn-SERVE | job 2 done | failed [HW against: every land row] |

**Settles.** KEEP in both: LFF was a stray (H-TRI with one exception, or H-RACE at a low rate);
the sim keeps fill,fill unknown (1 of 6 reads disagrees). FILL2 in both: two fills before land
write the 2nd fill's entry (H-FL; LFF 3 of 3), and ZFF2-KEEP then makes it an image effect, so
the sim keys fill,fill's word by image (tick running or stopped), two reads agreeing on each.
One of each: H-RACE. The page is the same under R-LOW and R-SA0 (sa0 < page); it adds to their
common pattern only.

**Cannot tell.** PLANT failed: -KEEP and -FILL* cannot tell. DK failed: -FILL* cannot tell (K
not 4). DR failed: all cannot tell.

### 4.5 LF3F (N3, last): land after fill,fill,fill

As §4.4 with `begin_draws = "fill,fill,fill"`; DK: KC begin delta 8; under H-KC the fills' 3:4
entries carry K 2, 4, 6.

| outcome | rule | prediction |
|---|---|---|
| LF3F-KEEP | sa1 = M1 | **held** [infer, H-TRI] |
| LF3F-SECOND | sa1 = 0x04000010 (the 2nd draw's 3:4, as LFF and X) | failed [held under H-FL2] |
| LF3F-LAST | sa1 = 0x06000010 (the 3rd fill's 3:4 at K 6) | failed [held under H-FLL] |
| LF3F-FIRST | sa1 = 0x02000010 | failed |
| LF3F-OTHER | any other sa1 | printed |
| LF3F-PAGE0 | job 2 not done; page 0 | **held** [infer: every fill leaves sa0 below a page] |
| LF3F-SERVE | job 2 done | failed |

**Settles.** Why 0x04000010, if it comes: LF3F-LAST says the last fill's entry writes (its K
tracks the list); LF3F-SECOND says the second draw's entry is special (X's and LFF's word at K 4
whatever follows); with H-KC's K arithmetic confirmed by KC in each case [HW counts]. KEEP with
LFF2/LFF3 KEEP: nothing to explain beyond one stray. One read: the sim learns nothing from it
alone.

### 4.6 B5 and B6: the re-pinned copies, frozen as they are

Each its own session (`C/r40-n3e-b5-r45`, prefix r40b5; `-b6-r45`, r40b6): stage **own** (crumb3
at fw14, `form=sb043` or `sb803`, blob `emitsb_sb043` or `emitsb_sb803` = emitsb14d with only the
emit word changed, one job, tick pass, no kick, on_stop "end") and stage **post** (t30's triangle
and fill after the disarm). Outcomes, as frozen in round 40 (`predictions/own.tsv`): the start
table (NEVER, T1, T2, T3, E1, DONE; RUN = T1..DONE), one H-DM line (predicted RUN) and one H-ALL
line (predicted NEVER); controls PG, E0, T0, B.

| row | expected | H-DM column (frozen) | H-ALL column (frozen) | today's rule [infer] |
|---|---|---|---|---|
| B5 0x043 | DONE | RUN | NEVER | RUN: bits 1:0 = 3 (E1164, E1162) |
| B6 0x803 | DONE | RUN | NEVER | RUN: bits 1:0 = 3 |

H-DM was falsified as "bits 1:0 needed as the data master" by 0x842 and 0x002 (E1166, E1168),
but its column's RUN for bits 1:0 = 3 is the same as today's rule; the fold reads the H-DM line
as "RUN predicted, held or FAILED" and names today's rule beside it, not H-DM.

**Choice: freeze as they are (decision B (a)).** Reasons: (1) their predictions are round 40's
bytes, frozen before B1, B2-B4 and B7-B11 ran; a rebuild would write new predictions after
knowing ten neighbouring sidebands; (2) every file but the srcversion is the reviewed round 40
session, and its tests, guard, mock and verify already pass on EC553F41 (§0.5); (3) the question
they ask (does the program start, and the landing lines) needs neither K5, K8 nor K9; (4) no
builder time. What a rebuild on today's kit (decision B (b)) would add: an after-read (blobs
`emitsb_sb043s`, `emitsb_sb803s` with command 6, no rebuild of the module: both words are on the
verifier's list) and post sa0-sa31, so B5/B6 would also say whether bits 6 and 11 change the
bank rewrite; that is a new question, not the frozen one, and fits a later round if they RUN.

**Freeze.** In the user's terminal (the lead's freeze was denied by the classifier): `cd` into
each copy, `python3 kit/session.py freeze .`, then `bash tests/run_all.sh`; check that
`PREDICTIONS.sha256` equals the original's (`C/r40-n3e-b5/PREDICTIONS.sha256`, `-b6`), which
shows the predictions did not move. **Stage only after cleanup-r45.sh has run**: its laptop step
moves `~/scratch/r4[0-5]*` into the archive (except r40n3e), r40b5 and r40b6 included.

**Risk.** RUN: the row ends ok and the kit's gate fill runs; bit 10 is not set, and only bit 10
was read breaking the gate fill (0xc43, E1172) [HW for 0xc43; infer for these]. NEVER: the tick
stops, rc 4, the kit's reset (every own-task stop recovered so far). A fault (bits 1:0 = 1 only
so far): stop for the user.

**Settles.** RUN for both: bits 6 and 11 do not decide the start with bits 1:0 = 3 [HW], closing
the two combinations Q128 left [infer]. NEVER for either: the rule "bits 1:0 decide" is wrong for
that combination; stop the round's B rows and bring it to the user. The landing lines (V0 and V2
in every fourth pa, or nowhere, as 0x003 against 0x843) are printed and folded as what bits 6 and
11 change in what is seen.

### 4.7 Q2 (N4, last): landq again, no draws

Q's stage byte for byte (E1233): landq, `begin_draws = "none"`, after the plant WE.

| outcome | rule | prediction |
|---|---|---|
| Q2-WRITE | job 1 done; sa0 = Q0, sa1 = M1 | **held** [HW, E1233] |
| Q2-SAME | job 2 not done; BIF_FAULT list 15 at 0x005d1000 | **held** [HW once, E1233] |
| Q2-SA0 | the same at 0x005d2000 | failed |
| Q2-OTHER | any other page | printed |
| Q2-SERVE | job 2 done | failed |

**Settles.** Q's stop meets the two-read rule; the sim can then hold landq's stop page (§5). It
splits nothing by itself.

### 4.8 R (N5, last; R2 in N7): landr, sa0 0x04400000 over sa1 M1

landr; `begin_draws = "none"` after the plant (WF, WH); jobs as Q. Both pages known unmapped
(§0.3), sa0's the higher, no other post sa holds either.

| outcome | rule | prediction |
|---|---|---|
| R-WRITE | job 1 done; sa0 = 0x04400000, sa1 = M1 | **held** [infer: Q-WRITE's `douta`, E1233] |
| R-LOW | job 2 not done; BIF_FAULT 0x005d100f (list 15, M1's page) | **held** [infer, R-LOW] |
| R-SA0 | the same at 0x0440000f (sa0's page) | failed [held under R-SA0 and R-SA0'] |
| R-OTHER | a fault at any other page (sa2's, sa13's, page 0) | printed |
| R-SERVE | job 2 done | failed [HW against: every land row] |

**Cannot tell.** J1 not DONE, or R-WRITE failed: every page outcome. SV or WF failed: the session
does not run past WF.

### 4.9 P (N6, last; P2 in N8): landp, sa0 V0 (mapped), sa1 0x005d2000

landp; `begin_draws = "none"` after the plant (WG, WI); jobs as Q. With sa0 = V0 every land row
so far stopped at sa1's page (LV, V, LM) [HW].

| outcome | rule | prediction |
|---|---|---|
| P-WRITE | job 1 done; sa0 = V0, sa1 = Q0, sa2 = V2 | **held** [infer: landv's, landq's `douta`] |
| P-UNMAP | job 2 not done; BIF_FAULT 0x005d200f (list 15) | **held** [infer, §0.3 (ii); R-LOW] |
| P-MAPPED | no fault at 0x005d2000: job 2 done, or a fault elsewhere | failed [held under R-SA0] |
| P-OTHER | a fault at another page (printed with P-MAPPED) | printed |

**Cannot tell.** J1 not DONE, or P-WRITE failed: every page outcome.

### 4.10 What R and P settle together

- **R-LOW with P-UNMAP**: 0x005d2000 is unmapped, so Q had two unmapped words and kept the lower;
  R shows the same across slots 1 and 17. R-LOW stands; R-SA0 and R-SA0' are falsified [HW
  against, with E1233].
- **R-SA0 with P-MAPPED**: R-SA0 (or R-SA0') stands: sa0 first, 0x005d2000 mapped. §0.3 (ii) is
  then wrong about our own tables, a finding of its own.
- **R-SA0 with P-UNMAP**: neither reading: Q kept the lower page with sa0 unmapped, R the higher.
  The rule is not an order of sa0 and sa1 (by slot or by word, unread); stop for the user.
- **R-LOW with P-MAPPED**: R-LOW holds for R, and Q then fits R-SA0 too; slot 1 would be mapped
  page by page, against (ii). Printed; Q2 and P2 decide whether to read on.

R alone splits the readings with two known-unmapped pages; P alone answers the premise; they
are independent checks of one rule. Each settles only with its own row's controls held.

## 5. The sim (`R/crates/sgx-sim/src/sgx.rs`)

The sim models attributes 0-2 after draws (`State::attr_now`, the user's rule: a list's word only
where more than one read agreed and none disagreed) and the kick pass's fault at sa13's page
(E1187); land's tick-pass stop page is not modelled. Per row:

- **ZFF2, LFF2, LFF3**: fill,fill stays refused while any read disagrees. If LFF2 and LFF3 both
  read 0x04000010 and ZFF2 M1, the sim may key the list's word by image (the tick running at the
  emit or stopped): two or more reads agree on each and none disagrees. Model nothing H-KC only
  infers.
- **LF3F**: one read; nothing modelled.
- **Q2**: with Q, two reads of (Q0, M1, no draws) -> page 0x005d1000; the sim may then answer
  that one bank shape (and, with LV, V, LM agreeing on sa1's page with sa0 = V0, and LC, LC2, LF,
  LF2, LT, LFF on page 0 with sa0 below a page, those two shapes), each by its own reads. A
  general rule (R-LOW) only after R and P are read twice (decision E).
- **R, P**: one read each; with R2 and P2 agreeing, each bank shape meets the rule.
- **B5, B6**: the start rule table (bits 1:0) gains 0x043 and 0x803 as read, not inferred.

## 6. Risks, recovery, stop conditions

- **The boot.** The first one-shot boot onto EC553F41 hung the laptop hard after login with
  nothing logged; the second ran clean; no cause is claimed (render-closing-r45-n3j-n5's fold
  notes). For the r46 boot: start the Mac listener (`netconsole-listen.py`) first; the Mac's LAN
  address is now **192.168.12.137**; right after login run `sudo ./test-session.sh
  192.168.12.137 6666` on the laptop (netconsole and the panic sysctls) before any session, then
  the srcversion check (`boot-test-kernel.sh` flow; gma500 srcversion loaded = installed). A
  hang: power cycle; the default entry is the stock kernel (one-shot), nothing to undo; then a
  second one-shot boot with the user's OK. If the laptop is rebooted before N1-N4, they need a
  one-shot boot onto 7.3.0-resgx545 again (EC553F41 is installed; the next default boot is
  stock).
- **Land-family stops** (LFF2, LFF3, LF3F, Q2, R, P): the runner's stop (rc 4), the kit's reset
  and strict health recovered every land stop so far (LC, LC2, LV, V, LM, LF, LF2, LT, LFF, Q)
  [HW]. A failed reset (rc 13 or 5): the user's ordinary reboot (stock).
- **New pages.** R's and P's faults are at pages the BIF has faulted at before (0x005d1000,
  0x04400000) or, under R-SA0, a page our code says is unmapped; P-MAPPED would mean the pass
  read a mapped page and went on, as LM's job 1 did through V0 [infer: no new risk class].
- **Stop conditions.** J1 not DONE: CANNOT TELL, stop that session. W-FAULT, or B failing in a
  quiet read (ZFF2): stop for the user. WF failing: stop before R. Any fault at a page no outcome
  names in a quiet stage: stop. B5/B6 FAULT: stop the B rows.

## 7. Build needs, run order, laptop time

**Build.** resgx545 branch `r46-n3k` off main (names start `r46-`, which cleanup-r45.sh's KEEP
spares): K10 and the scorers with tests (red, then green); the sessions N1-N4 frozen with
srcversion EC553F41FD8324BB6BF1764; the asm sources, header and N5-N8 sessions after the fork
build, frozen with the r46 srcversion (SV). Fork commit per §3.2, cachix, install. B5/B6: the
user's freeze (§4.6). Firmware-page writes: mark, crumbz, land, landq (run before) and landr,
landp (new); each needs the user's OK.

**Run script** (`C/r46-n3k-logs/runone.sh`, from round 45's): check the loaded srcversion
against the session's, `session.py stage`, `session.py run`, then for each stage `python3
score/score.py STAGE out/ATT/STAGE 2>&1 | tee ...`: **the scorer's output whole, every
PREDICTION line, never filtered**; then the health fill and triangle on t30. For B5/B6 the
copies' README commands (`session.py stage`, `run`, then `score.py own` and `score.py post`),
also teed whole. `SGX_TARGET_HOST=jtorra@192.168.12.234` (the laptop, unchanged); laptop files
only under `~/scratch/<prefix>/` (prefixes r46k1-r46k8, r40b5, r40b6), never /tmp.

**Run order** (decision F (a)):

0. The user runs cleanup-r45.sh (no session running); the Mac listener up; `test-session.sh
   192.168.12.137` on the laptop.
1. B5, then B6 (quiet expected);
2. N1 (WA, ZFF2, WB, LFF2; ends in LFF2's stop), N2 (WC, LFF3), N3 (WD, LF3F), N4 (WE, Q2);
   cachix builds r46-kernel meanwhile;
3. install, the one-shot boot (the user's OK), netconsole, the srcversion check;
4. N5 (WF, R), N6 (WG, P), then N7 (WH, R2) and N8 (WI, P2) with decision E (a).

B first: quiet, and a NEVER or fault there is the one result that would change the rest of the
round's reading of the sideband. N1 before the boot: LFF2 then runs on the module LFF's twin ran
on (images only added since, WJ E1218).

**Laptop time.** Round 45: one plant plus one land read about 1 min a session; N5 (14 stages)
about 6 min [HW, kernel log stamps]. Here: B5, B6 about 2 min each; N1 about 2 min; N2-N4 about
1 min each; boot and checks about 10 min; N5-N8 about 1 min each. With staging, scoring and the
health draws, about 40 min attended; the build about 45 min unattended, overlapping step 2.

## 8. Rejected alternatives

- **landq with M13 in sa0** (instead of 0x04400000): M13 also stands in sa13 after every plant,
  so a fault at 0x005d3000 needs Q's argument against "sa13 first" to be read as sa0's.
- **landr without a plant**: the kit refuses `begin_draws = "none"` on a first stage, and the
  plant gives the PLANT control and a known sa2 and sa13.
- **Only P** (decision A (c)): it answers the premise but does not show the order with two
  pages known unmapped; R costs nothing more in the same commit.
- **A blob that writes sa0 itself** (no module rebuild): whether the verifier's mov forms admit a
  secondary destination, and whether an issuer's secondary reaches the attribute the tick pass
  reads, are both unread; it would add a mechanism to the reading, where landr and landp reuse
  `douta` to attributes 0 and 1 (Q-WRITE, E1233; landv, E1183).
- **Reading the directory with a debugfs dump**: there is none for the kernel's directory
  (`peek` reads registers only), and a software read of our own tables is (ii), not the BIF.
- **More one-fill reads for F's 0x01000000**: not this round's question; LF and LF2 and F3 and
  ZF already read M1 four times against F's once.
- **B5/B6 rebuilt on today's kit**: §4.6 (decision B (b)).
- **Folding LFF2 and LFF3 into one session**: each ends in a stop, and on_stop "end" ends the
  session; one read a session, as round 45.

## 9. User decisions (one at a time)

- **A. The split of land's stop page (a rebuild):** (a) **recommended**: one fork commit with
  landr and landp, rows R and P after one one-shot boot (R splits R-LOW from R-SA0 with two pages
  known unmapped; P reads directly whether 0x005d2000 is mapped; two independent checks in one
  build); (b) landr only; (c) landp only; (d) no rebuild: record §0.3 (ii) in Q128 as [infer] and
  leave both readings open.
- **B. B5 and B6:** (a) **recommended**: freeze the re-pinned copies as they are, in the user's
  terminal, and stage them after cleanup-r45.sh (round 40's predictions unchanged, tests already
  pass, no builder time); (b) rebuild both on today's kit with an after-read (K5, K9, post
  sa0-sa31; new predictions); (c) skip them again.
- **C. The LFF rows:** (a) **recommended**: ZFF2 and LFF2 in N1, LFF3 in N2, LF3F in N3 (two
  repeats for the two-read rule, the image comparison in one session, and three fills for which
  fill's entry); (b) ZFF2, LFF2 and LFF3 only; (c) LFF2 only.
- **D. Q2** (Q's second read, no rebuild): (a) **recommended**: include (the sim's rule for
  landq's stop page; one more minute); (b) skip.
- **E. Second reads of R and P** (N7, N8 after the boot): (a) **recommended**: include (each
  verdict then rests on two reads and the sim may model the shapes; two more planned stops,
  every land stop recovered so far); (b) skip; repeat in a later round only if R or P disagrees
  with its prediction.
- **F. Order:** (a) **recommended**: B5, B6 and N1-N4 on EC553F41 while cachix builds, then the
  boot and N5-N8 (B5/B6 stay valid on the module they are pinned to); (b) the boot first and
  every session on the new module (B5/B6 then re-pinned and frozen again).

## 10. Addendum: the user's decisions and the build (round 46 builder, 2026-11-25)

The user's decisions (final): **A (a)** one fork commit with landr and landp; **B (b)** B5 and B6
rebuilt on today's kit with an after-read, new frozen predictions; **C (a)** ZFF2 and LFF2 in N1,
LFF3 in N2, LF3F in N3; **D (a)** Q2 in N4; **E (a)** R2 in N7, P2 in N8; **F (b)** the boot
first: every session (B5, B6, N1-N8) runs on the r46-kernel module. This section replaces §4.6's
"freeze the copies" plan and §7's run order; §2's "Module EC553F41, before the boot" no longer
holds: every row below runs on the new module. The copies `C/r40-n3e-b5-r45`, `-b6-r45` and round
40's frozen sessions are not used; their rows' intent (n3e §3.3: does bits 6 or 11 with bits 1:0
= 3 start the program) is kept, their predictions are not.

### 10.1 B5 and B6, rebuilt (sessions r46-n3k-b5, r46-n3k-b6)

One stage each (`b5`, `b6`), crumb3 at fw14, blob `emitsb_sb043s` / `emitsb_sb803s` (new in
resgx545 r46-n3k: `emitsb_sbc43s` but the emit word, entry 1 at index 30, U0 0x080401ef; no kernel
change, both words on the module's list since round 40), arm `slots=0x1 entry=0 pds=crumb3
pdsat=fw14 form=sb043` (`sb803`), the kit's default begin and end draws, `on_gate_fail = "score"`.
Row: job 1 = command 1 as every N row (the 0xdeadc0de fill, ticks, 200 ms, no kick); job 2 =
command 6 on a GETMISCINFO kick (round 41's row C, E1173: crumb3's T3 stops the tick, so the
after-read needs a kick pass); then the gate (fill, triangle). New against round 40's B5/B6: K5's
BIF words per job, K9's command counts (KC, printed), job 1's post sa0-sa31 and pa0-pa15, and job
2's after-read of the EDM's own sa0-sa31.

| outcome | rule | prediction |
|---|---|---|
| Bn-DONE | start DONE (S1, M4 with its run id, state 2) | **held** [infer: 1:0 = 3, E1162, E1164] |
| Bn-RUN | start any of T1, T2, T3, E1, DONE | **held** [infer] |
| Bn-NEVER, -T1, -T2, -T3, -E1 | that start | failed |
| Bn-HID | post sa0-sa31 = pre sa0-sa31 | **held** [HW for 0x843 and 0x003, E1162, E1164] |
| Bn-SAME | job 2 done; after = pre | **held** [HW for 0x843, C E1173; infer: no bit 10] |
| Bn-REBASE | job 2 done; after = post, post != pre | failed [held with bit 10: E1174, E1175] |
| Bn-AOTHER | job 2 done; after neither | printed |
| Bn-NOKICK | job 2 not done after its kick | failed |
| Bn-GATE | the gate's fill and triangle exact | **held** [HW: 0x843 E1173, 0x003 E1164] |
| Bn-FILL | the gate's fill not exact | failed [held with bit 10: X-FILL, Y-FILL] |
| Bn-QUIET | snap9 BIF_FAULT 0 | **held** |
| Bn-LAND4 | V0 at pa0, 4, 8, 12 and V2 at pa2, 6, 10, 14 (as 0x003) | printed |
| Bn-LANDNONE | no V0 or V2 in pa0-pa15 (as 0x843) | printed |

Controls: PG, E0, T0, SV decide the RULE; B is read by the outcomes; J1 is printed (the start is
the reading: NEVER is an outcome, not a cannot-tell); J2, DR and DK printed. **Cannot tell**: a
start other than DONE makes HID, SAME, REBASE, AOTHER, NOKICK and the landing outcomes cannot tell.
**Settles**: DONE and SAME with GATE for both: bits 6 and 11 change neither the start nor the bank
rewrite with bits 1:0 = 3 [HW then]; REBASE or FILL for either: that bit acts as bit 10 does, a
finding of its own. NEVER or a fault: stop the B rows for the user. **Risk**: §4.6's, plus the kick
(served on every crumb3 DONE gate fill so far).

### 10.2 What was built (offline)

- resgx545 branch `r46-n3k` on main 908b7e96: the landr and landp images (`asm/fwtask/pds/`, the
  header by gen_verify), the after-read blobs `emitsb_sb043s` and `emitsb_sb803s`, the fork pin at
  r46-kernel, K10 (`pds=landr|landp` in the kit's lint and runner).
- Fork `r46-kernel` (one commit on resgx545 b1089172b2e7) and its stub twin `r46-red`; the cachix
  series check and module build (`C/kernel39c/deliver/<tip12>/`).
- Sessions `C/r46-n3k-b5`, `-b6`, `-n1` ... `-n8` (prefixes r46k5b, r46k6b, r46k1-r46k8), frozen
  with the r46 module's srcversion (SV); generator `C/r46-n3k-logs/sessgen`; run script
  `C/r46-n3k-logs/runone.sh`.
- The page rows print PLANT (their images write sa0 and sa1 themselves); ZFF2 and the land rows
  after fills read it for their attribute-1 outcomes.

### 10.3 Run order (replaces §7's, decision F (b))

0. The user runs cleanup-r45.sh (no session running); the Mac listener up (`netconsole-listen.py`,
   the Mac at 192.168.12.137); install the r46 module (`sudo ~/install-module.sh KO 7.3.0-resgx545
   linux-resgx545 SHA`, the user's OK); the one-shot boot (the user's OK); right after login
   `sudo ./test-session.sh 192.168.12.137 6666`; the srcversion check (loaded = installed = the r46
   build's).
1. B5, then B6 (quiet expected; a NEVER or a fault stops the B rows for the user).
2. N1 (WA, ZFF2, WB, LFF2; ends in LFF2's stop), N2 (WC, LFF3), N3 (WD, LF3F), N4 (WE, Q2), N5
   (WF, R), N6 (WG, P), N7 (WH, R2), N8 (WI, P2), each ending in its land read's planned stop.

**The build control** moves from WF to **WA**, the first plant on the new module: WA failing any
outcome stops the round's N rows for the user (B5 and B6 before it read their own start and
controls). If the laptop is rebooted mid-round, the remaining sessions need a one-shot boot onto
7.3.0-resgx545 again (the r46 module installed; the next default boot is stock). **Laptop time**:
B5, B6 about 2 min each, N1 about 2 min, N2-N8 about 1 min each, the boot and checks about 10 min;
with staging, scoring and the health draws about 45 min attended. Every session: `bash
C/r46-n3k-logs/runone.sh STEP STAGE...` (the srcversion check, stage, run, every stage scored in
whole, the health fill and triangle).

## 11. Addendum: after N1-N4, which candidate decides the stop page (2026-11-25, design only)

Status: written after B5, B6 and N1-N4 ran on module 10BBF3BFBD51D559106589F (fork r46-kernel
c5094783eb88, installed and loaded; the laptop still on that boot) and before N5-N8. Nothing here
is built, frozen or run. A fold of B5, B6, N1-N4 is in progress on resgx545 `r46-fold-n3k`
(records from E1234); this section cites round 46's reads by session and attempt, not by record:
`n1` = `C/r46-n3k-n1/out/20261125-160752`, `n2` = `-n2/.../20261125-160955`, `n3` =
`-n3/.../20261125-161049`, `n4` = `-n4/.../20261125-161145`, `b5` = `-b5/.../20261125-150329`,
`b6` = `-b6/.../20261125-150427`; the scorer output is `C/r46-n3k-logs/score-r46-n3k-*.txt`.

### 11.0 What N1-N4 read [HW]

- **LFF2 (n1), LFF3 (n2), LF3F (n3)**: post sa0 2, sa1 M1, sa2 a timer word (0x01015e75,
  0x0102298f, 0x01043ca1); job 2 not done; BIF_FAULT **0x005d100f** (list 15, M1's page) in job
  2's pre and post and in snap9. KEEP and SA0 held, FILL1/FILL2/TRIPLE (LF3F: FIRST/SECOND/LAST)
  failed as predicted; **PAGE0 failed 3 of 3**, against the frozen "held". DR and DK passed (KC
  begin deltas 6, 6, 8). LFF's 0x04000010 (E1217) came back 0 of 3.
- **ZFF2 (n1)**: sa1 M1 kept, sa0 **0x00040000** (ZF and ZFF read 2, E1225, E1227), sa2
  0x010204c4; ZFF2-KEEP failed on sa0 alone; QUIET held. Its sa3-sa12 are not its own: WA, the plant
  right before it, read the same words [HW, `score-r46-n3k-n1-wa.txt`].
- **Q2 (n4)**: WRITE and SAME held: (Q0, M1), stop at 0x005d1000, as Q (E1233).
- **Plants WA-WE**: W-SA1, W-SA13, W-QUIET held 5 of 5; the build control passed.
- **B5, B6**: every prediction held; quiet. B5 printed LANDNONE (post pa0 0x4b1f374b), B6 printed
  LAND4: post pa0, 4, 8, 12 = V0 and pa2, 6, 10, 14 = V2.

### 11.1 Every land stop read so far

"sa12" is post sa12, which every land row read equal to the started entry's pa0 (E1178, E1184);
"K" is the KC arm count (CCB commands since the module load; printed from round 45 on, K9).

| row | where | module | draws after the plant | K | sa0 | sa1 | sa12 | page |
|---|---|---|---|---|---|---|---|---|
| LC | E1176 | 83FBFD86 | (no plant) fill,tri | - | 0 | 0x04400000 | not read here | 0 |
| LC2 | E1178 | 83FBFD86 | (no plant) fill,tri | - | 0 | 0x04400000 | 3 | 0 |
| LV | E1183 | 079DD0D1 | (no plant) fill,tri | - | V0 | 0x04400000 | not read here | 0x04400000 |
| V | E1185 | 079DD0D1 | none | - | V0 | M1 | 3 (E1184) | M1 |
| LM | E1198 | 079DD0D1 | none | - | V0 | M1 | 3 | M1 |
| LF | E1200 | 079DD0D1 | fill | - | 2 | M1 | 3 | 0 |
| LF2 | E1213 | 079DD0D1 | fill | 734 | 2 | M1 | 0 | 0 |
| LT | E1215 | 079DD0D1 | tri | 777 | 0 | 0x02400000 | 0 | 0 |
| LFF | E1217 | 079DD0D1 | fill,fill | 818 | 0 | 0x04000010 | 0 | 0 |
| Q | E1233 | EC553F41 | none | 284 | Q0 | M1 | 0x4b1f374b | M1 |
| LFF2 | n1 | 10BBF3BF | fill,fill | 144 | 2 | M1 | V0 | M1 |
| LFF3 | n2 | 10BBF3BF | fill,fill | 185 | 2 | M1 | V0 | M1 |
| LF3F | n3 | 10BBF3BF | fill,fill,fill | 228 | 2 | M1 | V0 | M1 |
| Q2 | n4 | 10BBF3BF | none | 265 | Q0 | M1 | V0 | M1 |

(Modules from the records' claims; LF, LF2, LT and LFF ran on 079DD0D1, not EC553F41: no land row
with sa0 below a page has ever run on EC553F41.) Two facts stand out [HW]:

1. Every stop at page 0 had sa0 below a page **and** sa12 below a page (3 or 0); the only rows with
   sa0 below a page and sa12 above one are round 46's three, and all three stopped at sa1's page.
2. sa12 on this boot is B6's landing: B5 (the boot's first own row) read pa0 0x4b1f374b, the word
   EC553F41's boot also held (E1219-E1233's sa12); after B6 (sideband 0x803) pa0 = V0, and every
   N row after it read sa12 = V0 (WA-WE, ZFF2, LFF2, LFF3, LF3F, Q2: 10 reads). The words B6 left
   at sa12-sa27 are bank C's (sa15 0x4d2817d1, sa17 0xcc48604d, ...) word for word.

The module diff since 079DD0D1 (ec6511d5de87) is two commits, b1089172 (crumbz, landq) and
c5094783 (landr, landp): `sgx_own_pds.h`, the arm's image table (4 lines each), the header's enum
and KUnit; no page-table, heap or VM change (`git show --stat`, read-only) [infer from the diff:
a module effect on page 0's mapping would have to come through the images alone].

### 11.2 The candidates, restated to cover all 14 reads

Let **A0** be the address the pass forms from attribute 0. R-LOW and R-SA0 (§0.2) survive only with
A0 not plain sa0, or with page 0 not faulting here: with A0 = sa0 = 2 and page 0 unmapped, both
named page 0 for LFF2, LFF3, LF3F and both failed. Candidates for what changed [all infer]:

- **C-FILL** (the draw list): two or more fills before land leave sa0's 2 out of what faults. Plain
  form **against [HW]**: LFF (two fills, E1217) stopped at page 0 (with sa0 0, sa1 0x04000010).
  Survives only as "sa0 = 2 written by the second or later fill's slot-0 entry is not read".
  Predicts page 0 for land after **one** fill on any module.
- **C-K** (K or the boot's age): the page-0 rows ran late in their boot (K 734-818; rounds 41-44
  unread), round 46's early (K 144-228). Predicts page 0 again once K passes some value in
  (228, 734]; at K above 818 it must.
- **C-E0** (the started entry's pa0, read as sa12): page 0 is hit only when sa0 and sa12 are both
  below a page. Fits all 14 reads. A sub-form, **C-E0+**, makes A0 = sa0 + sa12: page 0 for (2, 3),
  (0, 3), (2, 0), (0, 0); V0 + 2 for round 46's three (V0's page, mapped: E1183-E1198); and with
  R-LOW kept, Q and Q2 at M1 whatever Q0 + sa12 maps to. Under C-E0+ R's A0 is 0x04400000 + V0 =
  **0x36404000** and P's V0 + V0 = **0x64008000**, both of unread mapping (§0.3's (ii) covers
  slots 1-63 only).
- **C-MOD** (the module): something in 10BBF3BF (or EC553F41) maps page 0 for the tick pass or
  stops it being read. A priori weak (§11.1's diff), and, on this module, never separable from
  C-E0 without a low sa12 (no image or emit we have writes one, §11.6).
- **C-BOOT** (other state from earlier rows of this boot, e.g. B5's 0x043 or B6's 0x803 beyond
  pa0): the same predictions as C-E0 for every row below; carried with it.
- **C-SA2** (sa2's timer word): **against [HW]**: no threshold parts the reads (LC2's 0x01030b00
  stopped at page 0, LF3F's 0x01043ca1 at M1, LF2's 0x0105bab1 at page 0, LFF2's 0x01015e75 at M1).
  Dropped.
- **H-RACE** (timing): repeats of one shape agree 14 of 14 (LF, LF2; LFF2, LFF3, LF3F; Q, Q2; LC,
  LC2; V, LM). Carried only as the reason for second reads.

Which row splits which (on this boot, sa12 = V0 unless a reboot):

| row | C-FILL | C-K | C-E0 / C-E0+ / C-BOOT | C-MOD |
|---|---|---|---|---|
| LFK (one fill) | page 0 | unsure (K ~300) | M1 | M1 |
| LTK (one triangle) | page 0 | unsure | 0x02400000 | 0x02400000 |
| LFKP (one fill, K > 830) | page 0 | page 0 | M1 | M1 |
| R (landr) | (no page 0) | - | C-E0+: 0x36404000 or M1 | R-LOW / R-SA0 |

LFK splits C-FILL from the rest; LFKP splits C-K from C-E0 and C-MOD; C-E0 against C-MOD needs a
low sa12 on this module or a high one on 079DD0D1 (§11.6, decision K).

### 11.3 Rows, one line each (module 10BBF3BF, this boot, no rebuild)

| row | session | question | image | draws before the read |
|---|---|---|---|---|
| W9 | N9 | plant | mark | default |
| LFK | N9 | land after **one** fill on this module: page 0 (C-FILL) or M1 | land | fill |
| W10 | N10 | plant | mark | default |
| LTK | N10 | land after one triangle: page 0 or sa1's 0x02400000 | land | tri |
| W11 | N11 | plant | mark | default |
| LFK2 | N11 | LFK's second read | land | fill |
| W13, R | N13 | landr as N5's R, plus E12 and the C-E0+ pages (I) | mark, landr | default, none |
| W14, P | N14 | landp, as N6's P, the same additions | mark, landp | default, none |
| (W15, R2; W16, P2) | N15, N16 | second reads (decision J) | as N13, N14 | as N13, N14 |
| W12 | N12 | plant, after the K pad (decision H) | mark | default |
| LFKP | N12 | LFK with K above 818 (LFF's): page 0 (C-K) or M1 | land | fill |

No LM-like row (land, no draws after a plant): every candidate names M1 for it, and Q2 already
read that sa0-above-a-page shape on this module. Each land-family read ends its session (on_stop
"end"), one read a session, as rounds 45 and 46. Order: N9, N10, N11, N13, N14, (N15, N16), then
N12 last: its pad raises K for everything after it.

### 11.4 Rows, frozen predictions

**Common.** As §4.1: arm `slots=0x1 entry=0 pds=<img> pdsat=fw14 form=sbc43`, blob
`emitsb_sbc43s`, job 1 = command 1, job 2 = command 6 on the next tick pass, no kick. Controls
PG, T0, B, E0, J1, DR, DK, PLANT (the plant right before, same attempt), SV (10BBF3BF, loaded =
installed = the session's); B and J2 fail in every planned stop. Printed, never scored: as §4.1
plus post pa0-pa15. **New outcome in every read, `-E12`**: post sa12 = V0 (B6's pa0 still there),
predicted **held** [HW, 10 reads on this boot]; E12 failed makes the C-E0 column of that row
cannot tell (the outcomes are still scored). Plants W9-W16: row W of §4.2 byte for byte (W-SA1,
W-SA13, W-QUIET held, W-FAULT failed; 29 of 29 so far).

**LFK (N9, last), LFK2 (N11, last)**: land, 16 dwords; `begin_draws = "fill"`; DK: KC begin
delta 4. The stage of LF2 (`C/r45-n3j-n2`, stage lf2) byte for byte but its names and srcversion.

| outcome | rule | prediction |
|---|---|---|
| LFK-SA | sa0 = 2, sa1 = M1, sa2 timer | **held** [HW: LF, LF2, ZF, and with 2-3 fills n1-n3] |
| LFK-E12 | sa12 = V0 | **held** [HW, this boot] |
| LFK-PAGE0 | job 2 not done; BIF_FAULT list 15 at page 0 | failed [held under C-FILL] |
| LFK-M1 | the same at 0x005d1000 | **held** [C-E0, C-BOOT, C-MOD; C-K if K is below its value] |
| LFK-OTHER | a fault at any other page | printed |
| LFK-SERVE | job 2 done | failed [HW against: 14 of 14 land rows] |

**Settles.** M1 in both reads: the number of fills is not what changed (C-FILL out [HW, two
reads]); the stop follows sa12, the boot, the module or K. Page 0 in both: one fill keeps page 0
on this module and boot with sa12 = V0, so C-E0, C-BOOT and C-MOD are out and the draw list
decides [HW]; R-LOW and R-SA0 stand with "after two or more fills sa0's 2 is not read". One of
each: H-RACE, stop for the user. **Cannot tell**: PLANT failed (-SA cannot tell); DK failed (the
list did not run as one fill); DR or J1 failed: all.

**LTK (N10, last)**: land; `begin_draws = "tri"`; DK: KC begin delta 8; the stage of LT
(`C/r45-n3j-n3`, stage lt) byte for byte but its names and srcversion. 0x02400000 is the
triangle's 3:22 word at K 2 [HW: LT E1215, ZT E1221]; slot 9 has no table in any directory we
build (§0.3 (ii)) [infer]; the BIF has never been read faulting there.

| outcome | rule | prediction |
|---|---|---|
| LTK-SA | sa0 = 0, sa1 = 0x02400000, sa2 timer | **held** [HW: LT, ZT] |
| LTK-E12 | sa12 = V0 | **held** |
| LTK-PAGE0 | job 2 not done; BIF_FAULT list 15 at page 0 | failed [held under C-FILL] |
| LTK-SA1 | the same at 0x02400000 (0x0240000f) | **held** [C-E0, C-E0+, C-MOD; (ii)] |
| LTK-PAST | no fault at page 0 or 0x02400000 (done, or elsewhere) | failed [held if it is mapped] |
| LTK-SERVE | job 2 done | failed |

**Settles.** SA1: sa0 = 0 (not only 2) misses page 0 on this boot, and 0x02400000 becomes a known
unmapped page [HW] (a third one for R-like rows). PAGE0 with LFK at M1: the draw kind or sa0's
value (0 against 2) matters, a new candidate to bring to the user. PAST: the pass read through
sa1; its printed page (sa13's M13 the next known-unmapped word) says how far.

**LFKP (N12, last; decision H)**: LFK's stage byte for byte, run after a pad of client fills that
lifts K. The pad runs **outside the session**, before `session.py stage` (as the health draws do,
so DR's "nothing between the begin reset and the arm" is untouched): `~/scratch/r46k12/pad.sh`,
250 x `sgxfive-test-t30 fill` (each 2 CCB commands, DK's arithmetic), stopping at the first fill
that is not "fill: ok", its output teed whole to `C/r46-n3k-logs/pad-n12.log`. New control **PAD**:
KC begin N0 of the read stage >= 830 (above LFF's 818) [a kit change, §11.5]; PAD failed makes
LFKP's C-K column cannot tell.

| outcome | rule | prediction |
|---|---|---|
| LFKP-SA, -E12 | as LFK's | **held** |
| LFKP-PAGE0 | job 2 not done; page 0 | failed [held under C-K, and under C-FILL] |
| LFKP-M1 | the same at 0x005d1000 | **held** [C-E0, C-BOOT, C-MOD] |
| LFKP-OTHER, -SERVE | as LFK's | printed, failed |

**Settles.** With LFK and LFK2 at M1: LFKP at M1 drops C-K (at least for K up to its read); at
page 0, K (or the boot's age) decides and C-E0 is not needed for any read so far. With LFK at
page 0, LFKP adds nothing (C-FILL already names page 0): run it only if decision H says so
regardless.

**R (N13, last) and P (N14, last); decision I (a).** New sessions, not edits of N5 and N6: the
same stages byte for byte (plant W13/W14 with the default draws, then landr / landp with
`begin_draws = "none"`), the same outcomes and predictions as §4.8 and §4.9, plus:

| outcome | rule | prediction |
|---|---|---|
| R-E12, P-E12 | sa12 = V0 | **held** |
| R-SUM | job 2 not done; list 15 at 0x36404000 (sa0 + sa12) | failed [C-E0+, A0 first, unmapped] |
| P-SUM | the same at 0x64008000 (V0 + V0) | failed [C-E0+, A0 first, unmapped] |

R-OTHER's and P-OTHER's `@faultnotin` lists gain the SUM pages. Reading them together, now:

- **R at M1**: R-LOW with plain sa0, or C-E0+ with A0 mapped or kept above M1: no longer a clean
  R-LOW verdict on this boot. **R at 0x04400000**: R-SA0 with plain sa0 read first (C-E0+ out for
  R). **R at 0x36404000**: C-E0+ [HW for that bank], A0 first.
- **P at 0x005d2000 (P-UNMAP)**: Q0's page is unmapped [HW], whatever forms A0. **P-SUM**: C-E0+.
  **P served or elsewhere**: as §4.9's P-MAPPED.
- §4.10's four-way table holds only for A0 = plain sa0; §11.2's candidates decide whether that is
  the case. P's premise test (is 0x005d2000 mapped) stands on its own under every candidate.

**R2, P2 (N15, N16; decision J)**: N13, N14 byte for byte but their names; for the two-read rule.

### 11.5 Changes (builder; nothing here touches the fold's branch)

- resgx545 branch **`r46-n3k-b`** off `r46-n3k` eaee04a4 (not off `r46-fold-n3k`, which the fold
  owns), tests first: (1) the `-E12` rule needs no new kind (`postsa12`, the scorer's
  `(postsa|postpa)N` quantity); (2) **PAD**: a control on KC begin N0 >= a value (kit/kitscore.py,
  K9's kc), red then green on n1's lff2 stage (KC begin 138: PAD at 830 must fail) and a doctored
  copy (begin 900: must pass); (3) the scorers of LFK, LFK2, LTK, LFKP, and R/P/R2/P2 with the SUM
  outcomes, red then green on kept stages as fixtures: n1's lff2 must score LFK-M1's page rule held
  and -PAGE0 failed; round 45's lf2 (E1213) -PAGE0 held and -E12 failed; LT (E1215) LTK-PAGE0 held
  and LTK-SA held; Q2 (n4) R-OTHER-like `@faultnotin` with the SUM pages held.
- Sessions `C/r46-n3k-n9` ... `-n16` by `C/r46-n3k-logs/sessgen`, srcversion 10BBF3BF, prefixes
  r46k9 ... r46k16 (laptop files only under `~/scratch/r46k9/` ...). Frozen before any runs.
  `C/r46-n3k-n5` ... `-n8` stay as built, frozen and not run (named as such in the plan log).
- `C/r46-n3k-logs/runone.sh` accepts N9-N16 (its `case` list); for N12 it runs `pad.sh` on the
  laptop first and prints its tail whole. Every scorer output whole, every PREDICTION line, never
  filtered (as now). The pad script is new and goes under `C/r46-n3k-logs/` and
  `~/scratch/r46k12/` only.
- No fork commit, no cachix, no install, no boot.

### 11.6 What this round leaves open, and the follow-up for C-E0 against C-MOD

On 10BBF3BF no image or emit we have writes a word below a page into pa0: B5's 0x043 left it, B6's
0x803 wrote V0, a fresh boot gives 0x4b1f374b (twice: EC553F41's and this one), and mark writes
attribute 13 (pa1), not 12. Two routes, both later rounds:

- **Swap to 079DD0D1** (`C/kernel39c/deliver/ec6511d5de87/`, delivered; no rebuild): one boot,
  sessions pinned to that srcversion: LF with the boot's own sa12 (3 or 0 so far: page 0 under all
  candidates, a reproduction), then a B6-like emit (sideband 0x803, `emitsb_sb803s`, on the
  module's verifier list since round 40) and LF again with sa12 = V0: C-E0 names M1, C-MOD page 0.
  Needs an install, a one-shot boot and the user's OK; then a return to 10BBF3BF.
- **A rebuild**: a plant image like mark with a third word, 0 or 3, sent to attribute 12; then LF
  on 10BBF3BF with sa12 low: C-E0 names page 0, C-MOD M1.

### 11.7 The sim

Unchanged this round. The (2, M1) bank after a plant stopped at page 0 twice with sa12 low on
079DD0D1 (LF, LF2) and at M1 three times with sa12 = V0 on 10BBF3BF (LFF2, LFF3, LF3F): the sim may
hold each shape as read, keyed by everything that differs between them (sa12, module, draw list)
and no rule; no candidate of §11.2 is modelled until a row splits it with two reads agreeing. Q2
and Q now meet the two-read rule for the (Q0, M1) shape, M1's page (on two modules).

### 11.8 Risks and stop conditions

- **The boot is the state.** Every row here reads on this boot, with sa12 = V0. If the laptop
  reboots, sa12 goes back to the boot's word: re-run B6's session (`C/r46-n3k-b6`, a new attempt;
  its LAND4 put V0 there once, one read) before any remaining row, and the rows' E12 checks it; if
  E12 still fails, stop for the user. A reboot needs a one-shot boot onto 7.3.0-resgx545 (the next
  default boot is stock) with the user's OK.
- **Land stops**: 14 of 14 recovered by the runner's stop, the kit's reset and strict health. LTK
  may fault at 0x02400000, a page the BIF has not been read faulting at; R's C-E0+ page
  0x36404000 and P's 0x64008000 are new too. A list-15 fault at a new page is the class LV
  (0x04400000) and Q2 already recovered from [HW]; a failed reset (rc 13 or 5): the user's
  ordinary reboot (then the bullet above).
- **The pad**: 250 client fills on t30 (the health tool), each checked; one not ok stops the pad
  and N12 for the user. Run last so that no other row reads after it.
- **Stop conditions**: J1 not DONE: cannot tell, stop that session. W-FAULT or a plant's W-SA1
  failing: stop. E12 failing in a row with no reboot before it: stop (pa0 moved under us). LFK and
  LFK2 disagreeing: stop the N12-N16 rows for the user (H-RACE). A fault at a page no outcome names
  in a quiet stage: stop.

**Laptop time.** N9-N11 about 1 min each, N13-N16 about 1 min each, N12 the pad (about 250 fills,
a few minutes) plus 1 min; with staging, scoring and health about 25 min attended, no build.

### 11.9 User decisions (one at a time)

- **G. The fill-count rows on this boot:** (a) **recommended**: LFK (N9), LTK (N10) and LFK2
  (N11): fill count against everything else, two reads, and sa0 = 0 with a new page; (b) LFK and
  LFK2 only; (c) LFK only (one read: the sim learns nothing from it).
- **H. The K pad row LFKP (N12):** (a) **recommended**: include, last on this boot (the only row
  that splits C-K from C-E0 and C-MOD without a reboot; costs a few minutes of fills); (b) skip:
  C-K stays open.
- **I. R and P (built, frozen, not run, N5-N8):** (a) **recommended**: run them as new frozen
  sessions N13 (R) and N14 (P), the stages byte for byte plus E12 and the C-E0+ pages as scored
  outcomes, after N9-N11 on this boot; N5-N8 stay frozen and unrun; (b) run N5 and N6 as frozen
  and read C-E0+'s pages from the printed FAULT lines only (no new prediction is scored); (c) drop
  R and P this round: their reading leans on A0, which the rows of G and H decide first.
- **J. Second reads of R and P:** (a) **recommended**: N15 (R2) and N16 (P2) right after N13 and
  N14 on the same boot (same sa12; the two-read rule; two more planned stops); (b) skip, and repeat
  only if R or P reads a page no frozen prediction named held.
- **K. C-E0 against C-MOD:** (a) **recommended**: decide after this round: if LFK, LFK2 and LFKP
  all stop at M1, the next round swaps in 079DD0D1 for one boot (§11.6, no rebuild); (b) the
  next round rebuilds with a plant image that writes a low word to attribute 12; (c) leave both
  open and record §11.1's two facts in Q128 as [HW] with the candidates as [infer].
