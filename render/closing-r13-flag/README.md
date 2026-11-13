# r13-flag (round 13: the flagged stages, Q078 bit 14 twiddled, Q046 bit 11, Q163 hangs)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 0493e36a4691 (kit/ is that commit's blobs: the kit
words `noreset` and `idle:S`) and resgx545-data 75d01ee20311. Plan
`closing13/plan/rank-round13.md` sections 2 and 3 (F1, F2, F3); decisions
`closing13/DECISIONS-R13.md`: R13-3 (a) F1 and F2 after every safe session, R13-4 (a) F3 the very
last stage. **FLAGGED (outside the safe class)**: the user OK'd exactly these rows, planned faults
and hangs the kernel recovers only; no reboot, no clock-gate write, no held reset. Built offline;
nothing here touched the laptop, cachix or a git repository. Records E1033 (f1), E1034 (f2) and
E1035 (f3) are reserved for its fold (the builder folds it).

## What runs, in order: 27 jobs, about 15 minutes

Laptop: module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is
written (only `reset`). Tool t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), bound by source to
resgx545 a581c06 `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., TOOLSRC.sha256),
recipe `data:render/closing-r10-st1/lead/build_tool10.sh`; t10p is the same file under a second
name (deviation 1). Files under `~/scratch/r13f/`.

| # | stage | jobs | planned (#limit) | predicted | what | controls |
|---|---|---|---|---|---|---|
| 1 | f1 | 4 | 2 | 1 fault (H-TWX, H-E566) | T3 bit 14 on a twiddled 32 x 32: E566's own pair (A) and u = x / 4096 (B) | each pair's bit-clear reference, first |
| 2 | f2 | 4 | 3 | 3 faults | sideband 0x0a00 \| mode, modes 0, 4, 8 (E383's form) | E383's bit-12 mode 0 job, first |
| 3 | f3 | 19 | 8 | 5 hangs + the control's | VDM_STATE1 bits 11:9 sequences under E700's counter | E413's v = 7 pair, first (its second job must hang) |

Planned rows are the `expectfault` rows that are not controls; `#limit` is their count (E946's
slip designed out: a control's expected fault or hang is its reading and is not counted), and in
every stage the last planned row is the stage's last row, so the count never stops a stage with a
row left. Time: about 6 s a job with its reset (27 jobs: 3 minutes), about 40 s for each fault or
hang with its reset and strict health (10 predicted: 7 minutes), f3's 60 s idle, staging and
preflight (3 minutes): about 15 minutes, 20 at the most if every planned row faults or hangs.
Alarms: f1 and f2 15 minutes, f3 40.

### f1 (Q078, E1033): T3 bit 14 on a twiddled texture

E566's tx_map form (scratch dword i = 0xD0000000 | i), a twiddled 32 x 32 32-bit texture (T1
0x0C01F01F) at the scratch's first dword, the default 16-page scratch. The bit-clear index is
E561's tile law (gen/law.py, r10-tex's addr.py: 2048 of 2048 on E566's kept tw32-ctl; texmodel's
plain Morton misses 1024). E1003: on a strided texture bit 14 moves the read by m = floor(4096
clamp(u, 0, 1)) texels. Frozen (gen/f1.py, predictions/f1.tsv and predictions/f1/):

- H-TWIDX (the plan's H-TWMOVE): the move added to the twiddled index;
- H-TWX: added to the texel column, then the tile law unwrapped (at m = 4096: + 65536 dwords, a
  fault at the scratch's page + 0x40000) [infer, formed after E566's fault];
- H-TWX-WRAP: added to the column, then the wrap address mode;
- H-FAULTANY (the plan's rival): bit 14 faults any twiddled read; H-E566: E566's fault again.

Rows: f1-ref-a (control: E566's tw32-ctl program byte for byte, its kept image), f1-tw32
(E566's tw32-t3b14, u in (1, 2), m = 4096: H-TWIDX reads at most dword 5119, inside the 16 pages,
so it predicts no fault where E566 faulted: the replicate parts it from H-TWX and H-FAULTANY),
f1-ref-b (control: u = x / 4096 with bit 14 clear, the tile law's column 0), f1-small (held out:
the same with bit 14, m = x = 0 to 63; the three move models read inside the scratch and part on
2016 of 2048 pixels; H-FAULTANY faults). Each pair is gated by its reference.

### f2 (Q046, E1034): sideband bit 11

E383's form (probe --tri pixel, eot_plain, colour 0xc0804020; its published bins), sideband 0x0a00
| mode (bit 11 with E383's bit 9) in modes 0, 4 and 8. E383 faulted all nine modes, its kernel log
keeping `BIF fault 0x91000 at 0x37001xxx` for each (mode 0 0x3700103b, 4 0x37001003, 8 0x37001013
in the table's order [infer: no per-case markers]). Exploration: H-E383 (each faults), H-E383-PAGE
(0x91000 at page 0x37001000 [infer: B60AB0B4's heaps as E383's module laid them out]), H-NOFAULT.
The readings are the kernel line's status, address and page, and the runner's latched
BIF_INT_STAT and fault word (cases.tsv); the scorer prints each row's sideband word beside them.
Control (first): sideband 0x1200 (bit 12, mode 0): completes and at least 4055 of its 4096 pixels
are words of E383's mode 0 set (r13-tex sb12's H-FIXED; E383's two runs: 4096 and 4096).

### f3 (Q163, E1035): hang sequences

Two forms (gen/f3.py): E700's two-block stream (bits 11:9 of block 1 by `--vdm 1^=`, of block 2 by
`--vdm 9^=`, block 2's bits 7:0 at 5, the grid's completing value) and E413's one-triangle job
(`tri --poke vdm:1^=0xa00`, v = 7). E700's counter (M1, held out by E1021 for v 3 to 7): c = 0
after a reset or a hang, a job adds g(v) = v - 2 a block (g(1) = -1), it hangs iff c + add > 8.
Every sequence opens with a normal (reset) row; its later rows carry `noreset`.

| rows | clause | frozen (favoured first) |
|---|---|---|
| f3-c-a, f3-c-b | control: E413's v = 7 pair | the second hangs (E413 55 of 55) |
| f3-v1c0 | block-2 v = 1 at c = 0 | M3 (E701: hangs) against M1 (completes) |
| f3-v1c2-p, f3-v1c2 | at c = 2 (after (4, 2)) | completes under all |
| f3-v1c5-p, f3-v1c5 | at c = 5 (after (7, 2)) | M3 completes, H-C05 (c decides) hangs |
| f3-shape-a, -b | v = 7 twice, 128 x 128 | M1 hangs, H-SHAPE completes |
| f3-idle-a, -b | the same pair, `idle:60` before the second | M1 hangs, H-DECAY completes |
| f3-fill-a, -m, -b | a fill job between (noreset) | M1 hangs, H-FILLCLR completes |
| f3-rst-a, -m, -b | a plain triangle with the kit's reset between | M1 completes, H-RESETKEEP hangs |
| f3-hl-a, -b | the kit's strict health (`after`) between | M1 hangs, H-HEALTHCLR completes |

M3 (M1 with E701's block-2 v = 1 hang at c = 0) is scored on all eight held-out rows and predicts
5 hangs plus the control's; M1 predicts 4 plus the control's. f3-hl's pair is the plan's `noreset`
health-only sequence: the health fill and triangle add nothing under E700 [infer], and E413's
alternation ran across the unpoked triangle.

## Stops

- An undeclared fault or hang (a control of f1 or f2, any opening, fill or plain row of f3): the
  session stops (4).
- Strict health after every fault and hang (the kit), and after f3-hl-a (`after`): a health draw
  that fails at its first try stops the session (16), or aborts it (5) when the retry fails too.
- hook_fault (24) after every planned or control fault or hang: any `SGX recovery failed` line in
  the row's kernel slice (the plan's stop at the first failed recovery: no reboot, the user
  decides); in f1 and f2 an end that is not a fault, or a fault without its kernel `BIF fault S at
  A` line (the readings the scorer needs); in f3 an end that is not a hang, or a hang without the
  kernel's `job N hung, recovering`.
- A runner status 24 lets the driver go on to the next stage; f2 and f3 are `gate = true`, and
  score.py's gate is closed when any kept file of an earlier stage of this session has `SGX
  recovery failed`: after a failed recovery no later flagged stage runs (SKIPPED).
- hook_check (24): an f1 or f2 row that read ok without its pixel rows; in f3 the control f3-c-b
  completing (the counter is not there to read) or any ok row with a `failed:` line.
- A control without its reading stops the session (25); a noreset row after a row that did not
  end ok or as a hang is skipped by the runner (never run).

## The mock's worlds (mock/world.py, kit/session.py mock)

The fake tool answers from the argv and the fake kernel's state (the resets the runner wrote; f3's
counter runs on them): model (H-TWX, H-E383-PAGE, M3: every stage 0), alt (H-TWIDX, H-NOFAULT,
H-C05 with H-FILLCLR: 0), faultany (both f1 bit-14 rows fault, the limit's last row: 0), ctlnopix
(f1 24), f1hang (f1 24), recovfail (f1's fault logs -110, the health draws: f1 24, f2 and f3
skipped by the gate), unplanned (f2's control faults: 4), nobifline (f2 24), hang1st (f3's opening
row hangs: 4), nocounter (f3's control completes: 24), nojobline (f3's control without a reading:
25), f3fault (f3 24), recovfail3 (f3 24), wedge (the first health after a -110 fails: 16).

## Replay vectors

f1, f2, f3: `refused` (the plan, section 3: faults and hangs). f1-small's image would be a table
for sgx-sim's texture address (kind `tex`) if a move model holds on it; the fold builds it from the
kept files (predictions/f1/ and the tile law are here) or names the refusal. Nothing to pin.

## Layout

gen/make.py writes tables/, predictions/ and bins/ (gen/f1.py, f2.py, f3.py; gen/law.py the tile
law; gen/pins.py and gen/tex.py r10-tex's, pinned and compared); score/score.py; run/hooks.sh;
mock/world.py; tests/ (test_gen.py, test_twin.py, test_score.py, test_libmock.py); PREFLIGHT.md;
FOLD-NOTES.md. Publishable: everything (our own programs, tables, scorer and mock; no
firmware-derived file). **Nothing is marked for data-private.** `debug/` is scratch.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the guard, the session's tests, the library mock, the mock of
  every world, the verify once frozen); `python3 gen/make.py --check` (the generator current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/run-r13f.log`).
- Score again on a kept attempt: `python3 score/score.py STAGE out/ATT/STAGE`.

## Deviations from the plan (the lead may object before staging)

1. **Two names for t10** (r13-tex's deviation 1): the kit's library-mock replay fails every probe
   fill of our programs (libsgxfive's mock runs only its own copy shader), so f1's four rows name
   t10p, the same binary with a `no_source` reason; tests/test_libmock.py replays them on t10's
   library mock and requires exactly that end. f2's and f3's 23 rows pass the kit's replay.
2. **F1's frozen hypothesis is not the plan's alone.** H-TWMOVE (H-TWIDX here) reads at most 20
   KiB on E566's own tw32-t3b14 (u past 1, m = 4096) and predicts no fault inside the 64 KiB
   scratch, where E566 faulted: the plan's "fault with the mapping below the reach" row would
   fault under every hypothesis and part nothing. So pair A replicates E566's fault (H-TWIDX
   against H-TWX and H-FAULTANY) and pair B is the no-fault row, u small, where the move models
   part on images; the references run before their bit-14 rows (a control before the rows it
   gates), so the second planned row is the stage's last.
3. **F2 has its control first** and 4 jobs as planned; the scorer's H-E383-PAGE rests on [infer]
   (the same heap layout on B60AB0B4).
4. **F3's shape row is E413's one-block job at 128 x 128** (one block, the plan's "one-block
   stream"; E413's own 64 x 64 job was the counter's fit, in sample): the time, fill, reset and
   health pairs use E413's 64 x 64 job, whose alternation is 55 of 55, so those clauses do not
   rest on the new shape. The reset pair has a plain triangle (its own reset) between, the plan's
   "ordinary reset row". 19 jobs (the plan: about 18).
5. **Gates on f2 and f3** skip them after a failed recovery in an earlier stage (the kit's driver
   goes on after a stage's rc 24).
