# r18-flag (round 18: the flagged rows deferred "later, with the user")

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 2c0fe18e46d0 (kit/ is that commit's blobs) and
resgx545-data 45423fbc317b. Plan `closing18/plan/rank-round18.md` sections 2 and 3; decisions
`closing18/DECISIONS-R18.md` (the user present: R18 decisions (a)). **FLAGGED (outside the safe
class)**: the user approved 8 planned faults and 3 recovered hangs, the `#limit`s counting only
planned rows and capping at 15; no kernel change, no boot, no clock-gate write, no held reset.
Built offline; nothing here touched the laptop, cachix or a git repository. Records E1070 to E1076
are reserved for its fold (the builder folds it). Laptop prefix `r18f`.

## Tools

- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), bound by source to resgx545 a581c06
  `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76...), recipe
  `data:render/closing-r10-st1/lead/build_tool10.sh` (r16-zls's binding).
- t14 = `~/sgxfive-test-t14` (sha256 aa550b94...), source resgx545 c58f9f9 (sha256 9cef7a20...),
  recipe `data:render/closing-r14-flag/lead/build_tool14.sh` (r16-tw's binding; a byte copy of
  closing14/k14's recipe and built line in `lead/`).

## What runs, in order: 26 jobs, about 15 minutes (20 at most)

| # | stage | jobs | `#limit` | planned | tool | what | gate (s0 references) |
|---|---|---|---|---|---|---|---|
| 1 | s0 | 7 | 0 | 0 | t10, t14 | the safe references, one or two per later stage | none |
| 2 | f1 | 2 | 2 | 1 fault | t10 | Q299 (E1070): E411's G 3 and G 5 stores, 16-page buffer | zv-c-g3, zv-g5-24 |
| 3 | f2 | 4 | 4 | 2 faults | t14 | Q108 (E1071): EDMPROTECT, WRITEONLY alone on a load and a texture read | rf-c-depth, f1-ref-a |
| 4 | f3 | 2 | 2 | 2 faults | t10 | Q139 (E1074): two words never run at 384 x 256, O18-1's kinds (E1073) | f2-ctl-256 |
| 5 | f4 | 2 | 2 | 2 faults | t10 | Q241 bit 18 (E1072): the library triangle and E977's ramp | x-ctl |
| 6 | h1 | 1 | 1 | 1 hang | t10 | Q112 (E1075): bit 24 alone over a 32-bit index list | ix32-n |
| 7 | h2 | 8 | 4 | 2 hangs | t10 | Q163 (E1076): M1 on two new stream shapes, v = 6 | its own h2-c-b |
| | total | 26 | 15 | 7 faults, 3 hangs | | | |

Planned rows are those a frozen hypothesis says fault or hang; every row a rival says faults or
hangs is `expectfault`, and a stage's `#limit` counts exactly its `expectfault` rows that are not
controls (E946), so a rival's outcome is a reading, not a stop; in every flagged stage the last
row is one of them. The user's approval covers 8 faults: f1 now plans 1 (deviation 1), so 7.
Time: s0 about 2 minutes; 10 planned events at about 45 s each with the reset and strict health
(r14-flag's estimate), 16 other jobs about 3 minutes, staging and seven preflights about 4: about
15 minutes; all 15 allowed events about 20. Alarms: s0 15 minutes, each flagged stage 10, h2 15.

### s0: the references (safe class)

`zv-c-g3` and `zv-g5-24` (E1051's zv- form: E1041's and E1051's kept stores byte for byte, the
depth buffer at 0x3e001000 and the colour buffer right after it: 0x3e015000 at 20 pages,
0x3e019000 at 24, the premise of f1); `rf-c-depth` (r14-bif's control: E1046's kept store, the depth
buffer at 0x3e001000, f2's knob address); `f1-ref-a` (r14-flag's: E1047's kept image, the scratch at
0x3e003000, f2's other knob address); `f2-ctl-256` (E1048's baseline: its kept hash, TA data 24576
bytes, f3's layout); `x-ctl` (E998's control on t10: E977's kept dump and hash); `ix32-n` (E756's
bit-clear 32-bit list: every pixel the background, the probe's 32-bit echo). Each control reads
its keys through `hook_reading` (readings.tsv; the dumps' sha256 on the laptop); a reading that
differs from the frozen one closes only its stage's gate (`score.py gate`); a control without a
reading stops the session (25); any fault or hang stops it (4).

### f1, Q299 (E1070)

E411's G 3 (ctl 0x0017101c) and G 5 (0x0017102c) in E1051's form with `--depth-pages 16`. The
stores' pages are E1041's and E1051's (G 3: buffer pages 12, 14, 16, 18; G 5: 12, 15, 18, 21).
Read from the kept outputs (deviation 1): t10's colour buffer (5 pages with its guard,
`render.c fb_size`) is the GENERAL heap's next allocation, at the end of the depth buffer, so at 16
pages it covers buffer pages 16 to 20. Frozen, on the ends: **H-PAST-FAULT** (a store faults at
an unmapped page and lands on a mapped one: G 3 completes, its pages 16 and 18 in the colour
buffer; G 5 faults at page 21), **H-PAST-ANY** (any store past the buffer faults: both),
**H-DROP** (both complete). The fault word and page are scored apart: H-PAST-FAULT-PAGE (G 5:
0x90200 at 0x3e016000) and H-PAST-ANY-PAGE (0x3e011000, 0x3e013000). Retire Q299 (R18-6 a) when
both rows read as one end hypothesis with the s0 references passing: H-PAST-FAULT reads E411's
table literally (G 3 stored past its buffer without a fault, G 5 faulted) [infer].

### f2, Q108 (E1071)

Knobs `dbg:vm_pte_addr`, `dbg:vm_pte_flags` (r14-bif's), restored after every job. Rows in order:
`q108-edm-load` (EDMPROTECT 0x10 on the depth buffer, rf-c-depth's argv: the load reads it, the
store goes to the separate `--depth-store`), `q108-edm-tex` (0x10 on the scratch, f1-ref-a's argv:
E566's tx_map reads it as a texture; the program's PRE is empty, it writes only o0), `q108-wo-load`
and `q108-wo-tex` (WRITEONLY 0x2). Frozen: **H-WO-ALL** (0x80200 at 0x3e001000, 0x80002 at
0x3e003000) with **H-EDM-READ** (both edm rows complete; the texture row with E1047's image);
rivals H-WO-LOAD-OK, H-EDM-ZLS (0xa0200), H-EDM-TEX (0xa0002). The load rows' stores are read
after the run: `python3 score/score.py dumps f2 out/ATT/f2` (deviation 5).

### f3, Q139 (E1073 offline, E1074)

O18-1 (`fit/o18_1.py`, output `fit/o18_1.out`, form file sha256 in its last line) read E509's 329
cases and the first kernel fault line of each of the 162 that faulted: 155 0x90100 at the
parameter heap's first page, 7 0x90004 on TA data pages. **H-KIND** (0x90004 iff an axis has every
bound 0, or the stride puts the last macrotile at or past slot 3072; else 0x90100) fits 162 of 162
post hoc; **H-ONE-KIND** (every faulting word 0x90100) 155 of 162 (95.7 %, deviation 2). The rule
"a form fits at least 95 %" holds, so f3 is built. Rows (t10, E1048's form, never run: 384 x 256 is
no size of E509's, B1 and B3 values none of its n = 2 words had): `f3-k4` (0x00c00005, B2 = 0:
H-KIND 0x90004, H-ONE-KIND 0x90100) and `f3-k100` (0x00406001, fx 6, a second macrotile inside the
target: 0x90100 under both). The page is scored apart: H-PAGE-END (k4 at TA data page 0x20006, the
first page past the kernel's 0x6000 bytes at 384 x 256, fork 2a650d74's layout; k100 at 0x10000)
[infer]; E509's pages (0x20008, 0x2000a, 0x20010) came from a module whose layout is not kept.

### f4, Q241 bit 18 (E1072)

`b18-lib` (E065's job: `tri --poke blk:1^=0x00040000`) and `b18-ramp` (E998's isp0x form,
E977's 80 x 40 ramp with its depth buffer, `blk:1=0x00440200`). Frozen: **H-FAULT-ANY** (both
fault through one requestor: equal fault words) against **H-NEEDS-BUF** (the ramp draws, the
library row faults) [infer, weak]. The fault word names the requestor (hw_spec 5.5).

### h1, Q112 (E1075)

`b24-w32`: E756's form, `--index-width 32 --vdm 2^=0x03000000` (bit 25 cleared, 24 set). Frozen:
**H-B24-HANG** (hangs, E737) against **H-B24-W32** (E414's object: ix-c's o0 line).

### h2, Q163 (E1076)

E700's M1 (a job adds the sum of v - 2 over its blocks; it hangs iff c + add > 8; a reset clears
c), block 1 at v = 6 (`--vdm 1^=0x00000800`: add 4): ok, ok (c = 8), hang. Control first (no
`expectfault`): E700's two-block shape, the triple's first two rows (`h2-c-a`, then `h2-c-b`
`noreset`, reads o0): a hang there stops the session (4). Shape A (`h2-a1..3`): 24 vertices, one
object, 8 temporaries, 64 x 64; shape B (`h2-b1..3`): 48 vertices, two objects of 24, 16
temporaries, 128 x 64. Frozen: **M1-SHAPE** (each third row hangs) against **H-ALT** (E413's
alternation) and **H-SCALE** (the threshold scales with the stream: no hang) [infer].

## Stops

- s0: any fault or hang (4) and a control without its reading (25) stop the session; a reading
  that differs closes only its stage's gate (that stage is skipped).
- Every flagged stage is gated (`score.py gate`): its s0 references passed, and no kept file of an
  earlier stage of the attempt holds `SGX recovery failed`.
- An unplanned fault or hang (a row without `expectfault`, h2's control included): rc 4, the
  session stops.
- Strict health after every fault and hang (the kit): a first health draw that fails stops the
  session (16), or aborts it (5) when the retry fails too.
- hook_fault (24, and `on_stop = "end"` ends the session) after every expected fault or hang: any
  `SGX recovery failed` line in its kernel slice; in f1 to f4 an end other than a fault or a fault
  without its kernel `BIF fault S at A` line; in h1 and h2 an end other than a hang or a hang
  without `job N hung, recovering`.
- hook_check (24): a tri row that read ok without `job: ok`; a probe row without its pixels.
- A stage's `#limit` reached with rows left (24, the session ends).

## The mock's worlds (mock/world.py, `python3 kit/session.py mock .`)

model (every frozen hypothesis: 0 everywhere), alt (the rivals: 0), faultmax (every expectfault
row of f1 to f4 faults: each limit used up on its last row: 0), s0diff (x-ctl's hash differs: f4
skipped, 0), s0fault (a reference faults: 4), s0noread (ix32-n without its background reading:
25), recovline (an `SGX recovery failed` line in an ok s0 row: every flagged gate closes, 0),
recovfail (q299-g5 with `SGX recovery failed: -110`: 24, the session ends), f2hang (an f2 row
hangs: 24), nobifline (an f3 fault without its BIF line: 24), h1fault (the h1 row faults: 24),
h2ctlhang (E413's alternation: h2's control hangs: 4), wedge (the health fails once after f4's
first fault: 16). The kit's library-mock replay runs all 26 rows on t10's and t14's pinned sources
(f1-ref-a and f2's texture rows as "program not simulated"; the h2 noreset rows from a fresh mock).

## Replay vectors

Every stage's measured rows are faults, hangs or controls that replicate kept records, so each is
`refused` as a vectors table for now: f1 (a fault, and G 3's store into the colour buffer, which
sgx-pipe's `zls` refuses as past its buffer: the fold turns the refusal into the measured outcome,
no table), f2 (page-table flags: no sgx-sim model, SIM_UNMODELLED), f3 and f4 (faulting words),
h1 and h2 (hangs: the counter is not in sgx-sim). The s0 references are kept records already
replayed by their own sessions' tables. The fold builds a `closing_tables.py` table only where a
row drew (f2's edm rows: a `zls` load table of E1046's store; h1 under H-B24-W32: a `vdm` index
table), from the kept files alone; what it reads is pinned.

## Layout

gen/make.py writes tables/, predictions/, bins/ and mock/kept/ (byte copies of pinned kept
files: the s0 references' dumps and E1047's text, which the mock answers with); fit/o18_1.py and
fit/o18_1.out (O18-1, E1073); score/score.py; run/hooks.sh; mock/world.py; tests/
(test_twin.py, test_gen.py, test_score.py); lead/ (t14's recipe and built line, byte copies of
closing14/k14); PREFLIGHT.md; FOLD-NOTES.md. Publishable: everything (our own programs, tables,
scorer, mock and fit; no firmware-derived file). **Nothing is marked for data-private.** `debug/`
is scratch.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the guard, the session's tests, the library mock, the mock of
  every world, the verify once frozen); `python3 gen/make.py --check`; `python3 fit/o18_1.py`.
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/r18-flag-run.log`).
- Score again on a kept attempt: `python3 score/score.py STAGE out/ATT/STAGE out/ATT`; f2's stores:
  `python3 score/score.py dumps f2 out/ATT/f2`.

## Deviations from the plan (the lead may object before staging)

1. **f1's premise does not hold** (the plan asked the builder to check it): the colour buffer is
   allocated right after the depth buffer (E1041's and E1051's kept `layout: fb` lines, t10's
   `fb_reserve`), so at 16 pages G 3's pages 16 and 18 land in it and only G 5 reaches an
   unmapped page (21, not 18). The argv are the plan's; the frozen hypotheses are re-derived
   (H-PAST-FAULT: G 3 completes, G 5 faults at 0x3e016000), so f1 plans 1 fault, not 2 (7 faults
   in all, not 8); `#limit 2` stays (G 3 is `expectfault` for H-PAST-ANY). Every outcome still
   answers Q299's clause.
2. **O18-1's rival also clears 95 %**: H-ONE-KIND fits 155 of 162 (95.7 %), H-KIND 162 of 162, so
   the 95 % rule says only that a form fits; f3 parts the two on f3-k4. The page could not be
   fitted (E509's module layout is not kept): it is a separate model (H-PAGE-END), not part of
   the kind's verdict.
3. **f3 at 384 x 256 (n = 2)**: E509's three 0x90004 faults at 640 x 480 each failed its health
   triangle twice before it drew (kept output: "health: recovered on the retry"), which the kit's
   strict health would stop on; its four at 256 x 256 recovered at the first try. Both rows are at
   a new n = 2 size.
4. **h1's and ix32-n's argv drop `--dump-render`** (E756 had it): the library mock refuses it (no
   debugfs render files in the mock), and nothing is read from that dump.
5. **f2's stores are read outside the kit's scorer** (r14-flag's deviation 6): a faulted row has
   no dump and the kit checks REQUIRED on every row, so `score.py dumps f2` reads them.
6. **x-ctl runs on t10** (E998 ran it on t4): the same library; its frozen dump and hash are
   E977's, so a t10 difference fails the reference and skips f4 only.
7. **s0 ends with the default `on_stop`**: a stop in s0 (hook_check) skips only the stages whose
   references did not read; h2 has its own control.
