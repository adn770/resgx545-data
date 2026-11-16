# r29-flag (round 29: the flagged rows, user present)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 c0571816c4ff (kit/ is that commit's blobs) and
resgx545-data 73e058d51b5e. Plan `closing29/plan/rank-round29.md` sections 1 and 3; decisions
`closing29/DECISIONS-R29.md` (R29-1 to R29-6 (a), the user present). **FLAGGED (outside the safe
class)**: planned faults and recovered hangs only, in flagged stages after the safe stage s0; the
`#limit`s count only planned rows (rows a frozen hypothesis or a rival says fault or hang, never a
control: E946), 9 in all (the user's cap is 14); no kernel change, no boot, no clock-gate write,
no held reset, no firmware `str`, no trc_hazard. Built offline; nothing here touched the laptop,
cachix or a git repository. Records E1108 to E1113 are reserved for its fold (the builder folds
it). Laptop prefix `r29f`. Module srcversion E0CC40275493F8AEAD8180B (fork 456404fcffe5), loaded =
installed. It runs on the road over the travel cable (plans/resgx545-travel-runbook.md,
`host_key_alias = "cedar"`); nothing in it assumes cachix.

## Tools (none is built for this session)

- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), bound by source to resgx545 a581c06
  `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76...), recipe
  `data:render/closing-r10-st1/lead/build_tool10.sh` (round 10's binding). f2, h1's hangs, h2,
  and the kit's health fill and triangle.
- t14 = `~/sgxfive-test-t14` (sha256 aa550b94...), source resgx545 c58f9f9 (sha256 9cef7a20...),
  recipe `data:render/closing-r14-flag/lead/build_tool14.sh`; `lead/` holds closing14/k14's recipe
  and built line (byte copies). rf-c-depth, f1-ref-a and f1.
- t22 = `~/sgxfive-test-t22` (sha256 9b62d315...), source resgx545 3c68e8d (sha256 396252bd...),
  recipe `data:render/closing-r23-pk/lead/build_tool22_laptop.sh` (r23-pk's binding; `lead/`
  holds its recipe and built line). Every copy (before t22 the copy's poke set was a dangling
  pointer, HACKING).

## What runs, in order: 28 jobs, about 16 minutes (20 at most)

| # | stage | jobs | `#limit` | planned | tool | what | gate |
|---|---|---|---|---|---|---|---|
| 1 | s0 | 8 | 0 | 0 | t14, t10, t22 | the safe references | none |
| 2 | f1 | 2 | 2 | 2 faults | t14 | Q108 (E1108): both PTE flags on a read | rf-c-depth, f1-ref-a |
| 3 | f2 | 2 | 2 | 2 faults | t10 | Q139 (E1109): the page of the TA's empty-axis write | f2-ctl-256, c-512 |
| 4 | h1 | 6 | 2 | 2 hangs | t22, t10 | Q010 (E1112): the colour-space set across recoveries | the four c10- copies |
| 5 | h2 | 10 | 3 | 2 hangs | t22, t10 | Q010's last copy, then Q163 (E1113): block-2 v = 1 | its own h2-c-b |
| | total | 28 | 9 | 4 faults, 4 hangs | | at most 9 events | |

Time: 19 jobs without an event at about 12 s (4 minutes), 8 planned events at about 50 s with the
reset and strict health (7 minutes), staging and five preflights (4 minutes): about 16 minutes;
with the ninth allowed event (h2-a3) and a health retry about 20. Alarms: s0 15 minutes, f1, f2,
h1 10, h2 15. The records E1110 (f3) and E1111 (f4) are not used (deviations 1 and 2).

### s0: the references (safe class)

`rf-c-depth` (r14-bif's control: E1046's kept store, the depth buffer at 0x3e001000, f1's knob
address); `f1-ref-a` (r14-flag's: E1047's kept image, the scratch at 0x3e003000, f1's other knob
address); `f2-ctl-256` (E1048's hash, TA data 24576 bytes); `c-512` (the 512 x 512 job unpoked:
job ok and TA data 32768 bytes, the kernel's layout (fork 456404fc `sgx_render_tadata_layout_in`)
and H-SIZE's premise [infer]); `c10-zc`, `c10-zn`, `c10-bc`, `c10-bn` (E1103's and E1097's copy
forms on t22: a load of set 0 with zeros then a copy without the load read black
0xd3522437a14b6325, a load of BT.601 then a copy without the load read E037's 0xb6067a95fa98de2d:
both of Q010's readings shown reachable, each a control that can fail). Each control reads its keys
through `hook_reading` (readings.tsv); a reading that differs from the frozen one closes only its
stage's gate (`score.py gate`); a control without a reading stops the session (25); any fault or
hang stops it (4).

### f1, Q108 (E1108)

Knobs `dbg:vm_pte_addr`, `dbg:vm_pte_flags=0x12` (WRITEONLY 0x2 and EDMPROTECT 0x10 together; the
fork takes their sum), restored after every job. `q108-both-load` (rf-c-depth's argv, 0x12 on the
depth buffer: the ZLS load reads it) and `q108-both-tex` (f1-ref-a's argv, 0x12 on the scratch:
E566's texture read). Frozen: **H-WO-READ** (the read faults as WRITEONLY alone, E1071: 0x80200 at
0x3e001000, 0x80002 at 0x3e003000) [infer: EDMPROTECT never stops a read, E1071] against
**H-EDM-TYPE** (EDMPROTECT's type takes over as on writes, E965: 0xa0200, 0xa0002) and **H-PASS**
(both complete, E1046's store and E1047's image). Decides: narrow (the flags together on a read).

### f2, Q139 (E1109)

E1074's form (t10 `tri --tri-full --pixels ... --kpoke-render 1:ta:N=V --dump-render "$W"`) at
512 x 512 (n = 2 by the kernel's rule, area below 640 x 480; TA data 0x8000 bytes, region headers
at 0x4000 as at 256 x 256 and 384 x 256), with the size's own macrotile word and its B2 field
cleared, so the axis's every bound is 0 (E509's m1-B2-0 and m2-B2-0 form, never run at this size):
`f2-x512` CR_TE_MTILE1 0x02000008, `f2-y512` CR_TE_MTILE2 0x04000010. The kind is E1073's
**H-KIND** (0x90004, the TA's header write) on both, a third and fourth held-out word. The page:
**H-AXIS** (fixed by the axis at n = 2: x 0x20008, y 0x20010; E509, E1074) against **H-SIZE** (it
moves with the TA data's end: x end + 2 pages 0x2000a, y end + 10 pages 0x20012) [infer, weak].
All four pages are past the 0x8000 bytes, so every form predicts a fault. H-AXIS cannot be parted
from "the region headers' base + 0x4000 / + 0xc000" at any n = 2 size whose tail room is one page
(deviation 3).

### h1 and h2's first row, Q010 (E1112)

The fork read (rank-round29.md, Q010): debugfs `reset`, a hang's and a fault's recovery all run
`sgxfive_reset` (halt, `sgx_fw_build`, boot); E1097 and E1103 kept the set across the debugfs
reset. Rows (t22 copies in E1103's form; no load = `copy --every-value --pixels --poke
tex:1=0x7d03f01f --poke tex:0^=0x90`): `q010-af` (no load: the first copy after f1's and f2's
recovered faults; the last load is s0's c10-bc), `q010-ld2` (load BT.601, control), `q010-pre`
(no load after the kit's reset, control: E037's hash), `q010-h1` (E737's bit-24 hang on t10:
`probe --tri pixel --vertices 15 --copy-depth --pixels --vdm 2^=0x01000000`), `q010-p1` (no load),
`q010-h2` (the hang again, h1's last row), and h2's first row `q010-p2` (no load). Frozen:
**H-KEEP** (each held-out copy reads 0xb6067a95fa98de2d) against **H-RECOV-CLR**
(0xd3522437a14b6325). A copy is scored only after its recovery (q010-af: a fault in f1 or f2;
p1, p2: their hang). Retire rule (R29-3 a, `python3 score/score.py q010 out/ATT`): the four c10-
controls and h1's two pass and the three held-out copies read one hypothesis; under H-KEEP the
answer is "no job, idle, reset, fault or hang recovery clears the set; E271's zeros were a set not
loaded since the module loaded [infer]".

### h2, Q163 (E1113)

O29-2 (`fit/o29_2.py`, `fit/o29_2.out`): on the 15 kept block-2 v = 1 jobs of E545 and E701 (fit)
and E1035's three (held out), c alone (D-C) and the job before's non-zero add (D-PREVADD) fit the
fit set 15 of 15 but E1035 2 and 1 of 3; the grid's bits 7:0 (D-BITS) 13 of 15; **H-PREV16** (it
completes iff the job right before it, no reset between, completed with a block at v 1 or 6) fits
15 of 15 and 3 of 3 and E701's c = 8 completion. H-PREV16 was formed after E1035 was read: it is
post hoc on all 18 jobs, held out by this stage only. Rows, E700's stream on t10 (`--vdm 1^=`,
`--vdm 9^=`, the kit's `noreset` inside each triple), three triples from a reset:
(6,2) (6,2) (2,1) (`h2-c-a`, `h2-c-b` the control: c = 8 under M1, completes, a hang stops the
stage, 4; `h2-a3` E701's c = 8 completion held out), (2,2) (5,2) (2,1) and (2,2) (3,2) (2,1) (a v
5 and a v 3 job right before, never run before a block-2 v = 1).

| row | c (M1) | job before | H-PREV16 | D-PREVADD | D-C | H-ALWAYS |
|---|---|---|---|---|---|---|
| h2-a3 | 8 | (6,2) | ok | ok | ok | hang |
| h2-b3 | 3 | (5,2) | hang | ok | ok | hang |
| h2-c3 | 1 | (3,2) | hang | ok | ok | hang |

`#limit 3` = the three (2,1) rows (expectfault); 2 planned (H-PREV16), 3 if H-ALWAYS. Every other
row completes under M1 (c + add at most 8); a hang there is unplanned (4).

## Stops

- s0: any fault or hang (4) and a control without its reading (25) stop the session; a reading
  that differs closes only its stage's gate (that stage is skipped).
- Every flagged stage is gated (`score.py gate`): its s0 references passed, and no kept file of an
  earlier stage of the attempt holds `SGX recovery failed`. h2's own control gates its scoring.
- An unplanned fault or hang (a row without `expectfault`, h2-c-b included): rc 4, the session
  stops.
- Strict health after every fault and hang (the kit): a first health draw that fails stops the
  session (16), or aborts it (5) when the retry fails too.
- hook_fault (24, and `on_stop = "end"` ends the session) after every expected fault or hang: any
  `SGX recovery failed` line in its kernel slice; in f1 and f2 an end other than a fault or a fault
  without its kernel `BIF fault S at A` line; in h1 and h2 an end other than a hang or a hang
  without `job N hung, recovering`.
- hook_check (24): a tri or copy row that read ok without `job: ok` or its `target:` hash; a probe
  row without its pixels.
- A stage's `#limit` reached with rows left (24, the session ends): the last row of every flagged
  stage is a planned row, which is why Q010's copy after h1's second hang is h2's first row.
- Stop budget: zero unplanned events. Any stop other than a clean finish ends the session and is
  reported to the user: never retried, never rebooted.

## The mock's worlds (mock/world.py, `python3 kit/session.py mock .`)

model (every frozen hypothesis: 0 everywhere; the scorer's Q010 rule reads RETIRE H-KEEP), alt
(the rivals: H-EDM-TYPE, H-SIZE, H-RECOV-CLR, D-PREVADD: 0), pass (H-PASS: 0), always (H-ALWAYS:
h2's `#limit 3` used on its last row: 0), s0diff (c10-bn reads black: h1 skipped, 0), s0fault
(a reference faults: 4), s0noread (f1-ref-a without its scratch line: 25), recovline (an `SGX
recovery failed` line in an ok s0 row: every flagged gate closes, 0), recovfail (q108-both-load
with `SGX recovery failed: -110`: 24, the session ends), nobifline (an f2 fault without its BIF
line: 24), f2hang (an f2 row hangs: 24), h1fault (q010-h1 faults: 24), h2ctlhang (h2's control
hangs: 4), wedge (the health fails once after f2's first fault: 16). The kit's library-mock replay
runs all 28 rows on t10's, t14's and t22's pinned sources, none refused (f1-ref-a and
q108-both-tex as "program not simulated"; the noreset rows from a fresh mock).

## Replay vectors

Every stage's measured rows are faults, hangs or controls that replicate kept records, so each is
`refused` as a vectors table for now: f1 (page-table flags: no sgx-sim model, SIM_UNMODELLED), f2
(faulting macrotile words), h1 and h2 (hangs: the VDM counter is not in sgx-sim; the colour-space
set across a recovery is not modelled: the sim stops on colour-space load jobs, E568's note). The
s0 references are kept records already replayed by their own sessions' tables. The fold builds a
`closing_tables.py` table only where a row drew: f1 under H-PASS (a `zls` load table of E1046's
store, as r18-flag's f2), and the Q010 copies' hashes in run order (`sgx545-tables`, `refused`
until sgx-sim models a kept set across jobs), from the kept files alone; what they read is pinned.

## Layout

gen/make.py writes tables/, predictions/, bins/ and mock/kept/ (byte copies of pinned kept files:
E1046's store and E1047's text, which the mock answers with); fit/o29_1.py and fit/o29_1.out
(O29-1), fit/o29_2.py and fit/o29_2.out (O29-2); score/score.py; run/hooks.sh; mock/world.py;
tests/ (test_twin.py, test_gen.py, test_score.py); lead/ (t14's and t22's recipes and built
lines); PREFLIGHT.md; FOLD-NOTES.md. Publishable: everything (our own programs, tables, scorer,
mock and fits; no firmware-derived file). **Nothing is marked for data-private.** `debug/` is
scratch.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the guard, the session's tests, the library mock, the mock of
  every world, the verify once frozen); `python3 gen/make.py --check`; `python3 fit/o29_1.py`;
  `python3 fit/o29_2.py`.
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/r29-flag-run.log`).
- Score again on a kept attempt: `python3 score/score.py STAGE out/ATT/STAGE out/ATT`; Q010's
  rule: `python3 score/score.py q010 out/ATT`.

## Deviations from the plan (the lead may object before staging)

1. **f3 (Q241) is not built** (R29-2 a): O29-1 (`fit/o29_1.out`) finds no candidate word. The
   state block's zero words (12 wrap, 16 coordsize, 17 coordfmt) have no address role; the render
   command has no zero word; the PDS pointers are offsets from PDS_EXEC_BASE (0x2e000000), so a
   zero field would fetch the heap's base, not page 0; the ZLS words (rd:1, 12, 13) are set in
   E1072's ramp, which faulted at page 0 alike, and rd:14, 15 belong to the ZLS requestor (bit 9),
   not bit 10's. E363 shows bit 10's requestor fetching low memory (0x1f000) from no word of the
   job [infer]. c-lib-wA, c-lib-wB and x-ctl are dropped with it: 2 faults fewer, record E1110
   unused.
2. **f4 (Q112) is not built**: its control's premise contradicts Q042 (E307, E308): the low bits
   of the index list's word 4 (VDM_INDEX2) are an offset of the list's first index, so c-ix-w4
   (word 4 = 0xf0a5a000, bit 25 clear) would read indices about 0xa5a000 entries past the list,
   an unplanned TA read fault in s0 (a stop, 4) or a changed image (f4's gate closed): no marker
   value parts H-W4-S4 from H-W4-S0 with a control that can pass. 2 faults fewer, record E1111
   unused. Q112's 0xd0008 clause needs a form whose control moves no index (the 16 0xd0008 lines
   of usse/output-room-vdm's kernel log, at other addresses, are an offline lead).
3. **f2 at 512 x 512, not 512 x 256 and 384 x 256**: by the kernel's layout 512 x 256 and 384 x
   256 have 256 x 256's TA data (0x6000 bytes), so the plan's rows could not part H-AXIS from
   H-SIZE; at 512 x 512 (n = 2, 0x8000 bytes) they do. Both rows use the size's own word with B2
   cleared (E509's form) rather than E1074's 0x00c00005. c-512 is the 512 x 512 baseline.
4. **Q010's rows are moved**: the kit stops a stage whose `#limit` is reached with rows left, so
   a copy cannot follow a stage's last planned event. q010-ld (f1's control) is dropped (s0's
   c10-bc is the last load before q010-af), q010-af opens h1 (after f1's and f2's four planned
   faults, not f1's two), and q010-p2 opens h2.
5. **h2 has 9 Q163 rows and plans 2 hangs, not 11 rows and 3**: O29-2's best form and rivals part
   on the three (2,1) rows; the control pair is the first triple's first two rows (as r18-flag's
   h2). H-ALWAYS makes the third (2,1) row expectfault: `#limit 3`.
6. **h1's hang runs E737's 16-bit form** (`--index-width` is in `forbid_options`) and drops
   `--dump-render` (E737 had it; the library mock refuses it, r18-flag deviation 4).
7. **s0 ends with the default `on_stop`**: a stop in s0 (hook_check) skips only the stages whose
   references did not read; h2 has its own control.
