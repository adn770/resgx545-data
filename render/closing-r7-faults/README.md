# r7-faults: Q003's -110 by fault page and by manipulation, Q111's `lock #0` twice

Prepared 2026-11-12, offline, NOT run. Nothing here touched the laptop, cachix or a git repository; the repo guard was not run.
Plan: `closing7/c/exp-faults-r7.md` (sections 1.3 to 1.5, 2.2), decisions `closing7/DECISIONS-R7.md` R7-2 (a) and the plan's own
decisions 2 (a) and 3 (a): stages L, d and m; a -110 is a reading; stop on a failed second boot, a failed health or an unexpected
word; budget 16 timed-out boots. **No Q294 rows** (O4 failed its controls, E902). Frozen against resgx545 main **1c64f3a** and
resgx545-data **830641e6** (`FROZEN.commits`, `FREEZE.txt`). Read `PREFLIGHT.md` before staging (its "End state" is what the lead
does if the boot is left unusable).

Module **41E2F5C756F96D20F7109A4** (fork `r6-kernel` 3f0b3e74: peek, bif_flush, kregnow), tool `~/sgxfive-test-rgn4`
(e6951558...), frozen in `run/f.env`. It runs **last** of round 7's sessions on that module. Laptop prefix **`~/scratch/r7f/`**
(`stage/` the staged tree, `out/` the kept stages, `run/` the -110 ledger); work directories `~/scratch/tmp/r7f.XXXXXX`.

## What runs (`stages.txt`, one driver call: `run/f.sh`)

| stage | rows | what | predicted |
|---|---|---|---|
| s0 | 2 | n0: `kregnow 0x0c00^=0x10` twice with nothing held (CLEAR_FAULT set and cleared: taken, BIF_CTRL 0x10 then 0, BIF_INT_STAT idle; E826 n0); c1: the 64 x 64 health triangle | 5 controls PASS |
| l | 5 fills | E088's counter probe (64 x 32 fill, each instance adds 1 to a scratch dword), five programs (`bins/`): l0 lock/release, l1 lock #0 + lock #1, l2 lock lock rel rel, l3 lock lock rel, l4 lock, no release (E088's hang) | l0, l1 512; H-SELF: l2, l3 hang with 0; l4 hang with 1 |
| d | 7 cells | E848's held job (one array, `render_rgn_arrays` 1) at 640 x 480, 288 x 144, 320 x 400, 256 x 288, 128 x 528, 384 x 384, 320 x 400; held reset, triangles until one draws | E901's R-PAGE: the boot after the held reset times out at pages 0x20006 to 0x20008 (d1, d2, d3, d5, d6), comes up at 0x2000a (d0) and 0x20009 (d4); H-SIZE (E892's wording) refuted |
| m | 6 cells | 288 x 144 (page 0x20006) with a manipulation before the held reset: none, CLEAR_FAULT set then cleared (kregnow, E826's write), a 9 s hold; order M0 M1 M2 M2 M1 M0 | H-NULL (R-PAGE): all time out; rivals H-CLR (M1 up), H-TIME (M2 up) |

Each held cell: reset, registers, `hold_recovery` Y, the job, registers at 2.8 s and 1 s later, [clr: the two kregnow writes
with registers after each; long: 5.2 s more], the debugfs reset with the hold still Y, `hold_recovery` N, registers, then
triangles one by one until one draws (three at most), then strict health; the row's whole kernel-log slice is kept and its
timed-out boots go to the ledger. Rows by model: `predictions/*.tsv` (106 rows), tables `TABLES.md`.

**Controls that can fail** (each declares its readings; `scorekit.refuse_unreadable` checked them in the generator): s0's five;
l0 and l1 (512, ok) gate l2, l3, l4; d0 (640 x 480 up) and d1 (288 x 144 timeout) gate every d row, and d0 timing out stops d;
m0a and m0b (timeout) gate every m row; each cell's H-JOB (the held fault, 0x90004, the layout's page word) and H-END (a draw
within three); each clr cell's M-CLR (the kernel's reads with the bit set: 0 and 0; cleared: the fault's words, E826 4 of 4).

**Fit vs held out.** R-PAGE is E901's fit (770 of 771, SEMI on r6-held); d1, d0, m0a, m0b are its fit sizes (controls); d2 to d6
and m1/m2 are held out. Stage L: l2, l3 held out; l4 replicates E088.

**Job count.** s0 2; l 5 probe fills (+ up to 3 strict health pairs after hangs); d 7 held jobs + 7 to 21 triangles + 7 health
pairs; m 6 held jobs + 6 to 18 triangles + 6 health pairs; begin/end health per stage. **About 60 tool calls on the laptop
side, 4 driver stages.** Time: L about 2 min, a held cell 25 to 35 s (r6-held), d about 4 min, m about 4 min (+ 10 s for the two
long cells); with staging, copies, scoring and health **about 30 minutes; plan 60**.

**Timed-out boots: expect the budget to end the session in m.** r6-held's 288 x 144 cells timed out two boots each (the held
reset's and a replay's: a2 TU + TU, b2 TU + U + TU), so R-PAGE predicts about 2 a timing-out cell: d about 10 (five cells),
m about 12. The budget of 16 (decision 3 (a)) then ends the session after m's third cell (rc 25, after its health): m's first pass
(M0, M1, M2) runs, its second (M2, M1, M0) does not. The plan's estimate (9 to 14) counted one a cell. If the lead wants both m
passes inside 16, `run/f.sh --only s0 l m d` runs m before d (d then stops after about its third cell); no refreeze needed.

## Stops (plan 1.5; decision 3 (a))

- **Session, no resume (rc 26):** two failed boots in a row (the second boot of one recovery), or "SGX boot: BIF fault during
  reset": at once, no further reset, knobs restored. Strict health failing after a cell or a hang (rc 16); a cell's third
  triangle (rc 17); a fatal kernel message (rc 3), a job that did not return (rc 6), E317's stall (rc 18).
- **Stage (rc 24, after the row's health; the driver goes on):** a fault word other than 0x90004, a timed-out boot's dump with
  `BIF_INT_STAT` other than 0x000d0004 or `BIF_FAULT` outside pages 0x10000-0x10fff and 0x20000-0x20fff, a fault through list 15;
  d0 (640 x 480) timing out; a held fault of another shape; a probe that faults; the third hang of L with rows left.
- **Budget (rc 25):** the 16th timed-out boot of the session (the ledger, every attempt) ends it after the cell's health; a spent
  ledger stops the preflight.
- Standing: free space per job (300 MiB), files under `~/scratch/r7f/` only, kmsg sliced by marker, every scorer input checked
  kept by the driver (`score/sessioncheck.py kept`, rc 43), the premise of every stage that ran to its end (`score_f.py premise`,
  rc 44), the staged tree run under `env -i` in the mock.

## Round 4's to 6's slips: impossible by construction

- **The mock answers by argv** (`tests/worlds.py`): a held job faults only with `--tri-full`, `cmd:1=0xe0000000`, maximum =
  size, no `--aa4` and `render_rgn_arrays` 1 as written through the shim; the page from the size (typed by hand from the kept
  faults); a probe runs the lock and release words of the program file its argv names (found by assembling them in the mock),
  never a case name. Its start-up is waited for (the regs read during a hold waits for the fake's answer; a world runs it 3 s late).
- **The argv twin** (`tests/test_twin.py`): every row against the plan rows typed by hand; every d/m job E848's byte for byte
  (the size aside); every L program's locks and releases from the assembler's listing.
- **Replays before the freeze** (`tests/test_replay.py`): holds on E826 n0 (s0), E088 cases 1 and 3 (l0, l4), r6-held a0, a2,
  b2 (d0, d1, d3; m0a, m2a), E826 f2 (m1a's M-CLR); must fail on a2 as d0, a0 as d1, f2's page as m1a, E088 case 0 and 3 as l0,
  a refused kregnow set, an s0 with no kregnow line (premise STOP).
- **Round 7 gates:** `score/scorekit.py` and `score/sessioncheck.py` byte for byte main's (1c64f3a); controls declare their
  readings (`gen/fgen.py` refuses an unreadable one); `tests/run_all.sh` runs sessioncheck staged, envi and kept.

## Layout and commands

`gen/fgen.py` writes `tables/`, `predictions/`, `TABLES.md`, `stages.txt`, `gen/data/sources.lst`; `gen/asm_l.py` assembles
`bins/` (resgx545's usse-asm, `probes/usse/templates/counter.s`); `score/score_f.py` the scorer (`REQUIRED`, `premise`); `run/`:
`run_f.sh`, `lib_f.sh`, `f.env` run on the laptop, `f.sh` the driver, `stage_f.sh`, `freeze_f.sh`, `guard_f.sh` (the session's
own static guard), `lib_check.sh` (Mac).

```
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHONDONTWRITEBYTECODE=1
export PY=/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
cd /Users/jtorra/src/scratch/resgx545/closing7/r7-faults
bash tests/run_all.sh                 # offline: RUN_ALL PASSED
run/guard_f.sh && run/freeze_f.sh verify
SGX_DRY_RUN=1 run/stage_f.sh && SGX_DRY_RUN=1 run/f.sh
run/stage_f.sh                        # copies to ~/scratch/r7f/stage, compares, checks the tool hash
run/f.sh                              # s0, l, d, m (gate, kept check, score, premise, health)
$PY score/score_f.py verdict out/ATT  # the SUMMARY lines (several ATT after a --from)
```

## Deviations from the plan

1. **0x20007 has no size.** Under the fork's layout (one array, the 1x tail room) the fault page is 4 + 2k (side 16 or 32) or
   7 + 2k (side 64) pages above 0x20000, k >= 1 (`tests/test_gen.py` scans every size): 0x20007 cannot be reached. Its cell is
   384 x 384 (page 0x20008, E729's kept fault), so 0x20008 has three cells at two sizes. 0x20009 is reached only at side 64
   (n = 2, height 513 to 528 for widths up to 256): 128 x 528, a tall target never run [infer: its page from the layout; the 4x
   tail entries of its doubled grid stay below 0x4400, inside the TA data]. Its H-JOB control fails if the fault lands elsewhere.
2. **H-DONE is not frozen.** Its number per size (plan F2: the pages a completed four-array job allocates) was not compiled by
   the fold (E901) and no kept file reads it (every kept `CR_DPM_PAGE_STATUS` is a held reading). The cells print the page count
   at the hold (0x0724, explore) for a later fold. The rival frozen against R-PAGE is H-SIZE (E892's wording, literal).
3. **s0's n0 is a kregnow gate**, not r6-held's bif_flush row (this session writes CLEAR_FAULT, never bif_flush); peek is read
   once in the preflight as the module's identity (the 0x0694 peek is exhausted, plan 2.1), never per cell.
4. **The premise runs Mac-side** (`score_f.py premise`, scorekit.premise_stops) after every stage that ran to its end; the laptop
   runner stays python-free, so `scorekit.py` and `sessioncheck.py` are copied and frozen in `score/` but not staged to the laptop.
5. **Stage L's health:** strict after each hang, and a failed one stops the session (rc 16), not only the stage.
6. **The budget is counted per row** from the row's whole slice (its pre-job reset, the job, the steps, the health), written to
   `~/scratch/r7f/run/minus110.ledger` so that a `--from` attempt keeps counting.
7. **300 MiB** free-space floor (HACKING's is 200).

## Data-private

Nothing here is firmware-derived: the programs are our own (`counter.s` and the plan's lock lines), the oracle O4 is not used.
The whole directory is publishable.
