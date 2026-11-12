# r6-held: Q003's replay through the directory list, the BIF flush, and Q111's 0x0694 row

Prepared 2026-11-12, offline, NOT run. Nothing here touched the laptop, cachix or a git repository; the
repo guard was not run. Plan: session B of `closing6/rank/rank-round6.md` (R6-5, R6-6, section 2
"Session B", section 4 K1/K2), decisions `closing6/DECISIONS-R6.md` R6-4 (a), R6-5 (a). Frozen against
resgx545 main **d9b2969** and resgx545-data **e5cdaf0a** (`FROZEN.commits`, `FREEZE.txt`). Read
`PREFLIGHT.md` before staging.

The session runs on the **new kernel** only: fork branch `r6-kernel` tip 3f0b3e74 (rgn4 + the 4x tail
room + debugfs `peek` + debugfs `bif_flush`), module **srcversion 41E2F5C756F96D20F7109A4** (the lead's
cachix build: vermagic 7.3.0-resgx545 SMP preempt mod_unload 686, gma500_gfx.ko sha256 8a32dada...),
frozen directly in `run/h.env` (and `p/`'s env). `render_tail_room` stays at its default 0 (checked,
never written).

Two parts, one laptop prefix **`~/scratch/r6h/`**: part H (this directory: `run/`, `tables/`, `score/`)
and part P (`p/`, its own README, freeze and tests). Order: **P first, then H** (P's tick stops are the
known recoverable kind, E855 3 of 3; H holds the -110 risk). Each is its own driver call.

## Part H: what runs (`stages.txt`)

| stage | rows | what | predicted |
|---|---|---|---|
| s0 | 2 | n0: `echo 1 > bif_flush` with nothing held (refused -EBUSY, BIF_CTRL unchanged, `peek` read idle); c1: the 64 x 64 health triangle | 4 controls PASS |
| q | 6 cells | E848's held 4x job (one array, `render_rgn_arrays` 1, TA write fault 0x90004), the debugfs reset, the follow-up, triangles until one draws | 6 held faults, 6 replays (one a cell under H-PEND, three if H-FLUSH holds) |

Cells, in run order (a and b alternate so a stop leaves both kinds; `TABLES.md`):

| cell | job | follow-up | flush | first triangle predicted |
|---|---|---|---|---|
| a0-640-health | 640 x 480 (0x2000a061) | none | no | replay at 0x2000a061 (the CONTROL that a replay happens on this kernel; E848 h2) |
| b0-640-flush-health | 640 x 480 | none | yes | H-FLUSH: draws / H-PEND: 0x2000a061 |
| a1-640-fill | 640 x 480 | fill | no | H-LIST: 0x2000a062 / H-WORD: 0x2000a061 (held out at a new size) |
| b1-640-flush-fill | 640 x 480 | fill | yes | H-FLUSH: draws / H-PEND: 0x2000a062 |
| a2-288-fill | 288 x 144 (0x20006061) | fill | no | H-LIST: 0x20006062 / H-WORD: 0x20006061 (E848 h4's replicate) |
| b2-288-flush-health | 288 x 144 | none | yes | H-FLUSH: draws / H-PEND: 0x20006061 |

Each cell: reset, `render_rgn_arrays` 1 (read back), registers and `peek` before, `hold_recovery` Y,
the job (E848's argv byte for byte: `tri --tri-full ... --max-width = --width`, E824's four pokes, no
`--aa4`, so a 1x context whose layout the tail-room commit leaves byte for byte as before), registers at
2.8 s (+ `peek`) and 1 s later, [b: `echo 1 > bif_flush` while held, its status kept, the kernel's
`bif_flush:` line in the slice, registers again], the debugfs reset with the hold still Y, `hold_recovery`
N, registers (+ `peek`), `render_rgn_arrays` 0, then [a fill], then triangles one by one until one draws
(three at most), then strict health (fill + triangle).

**Rows (`predictions/q.tsv`, 59 rows; `gen/hgen.py`'s docstring).** Controls per cell: H-JOB (class
fault, BIF_INT_STAT 0x90004, the job's word), H-END (a draw within three triangles), H-FILL (the fill
draws), H-KEEP (flush status 0, BIF_CTRL the same before and after: the fork's sequence), H-REPLAY (a0
only: the replay at the job's word; it gates every K2 row). Held out: **H-LIST** vs **H-WORD** (a1; a2
is h4's replicate), **H-FLUSH** vs **H-PEND** (b0, b1, b2), **H-BOOT** [infer] (no -110 after a flushed
held reset), **H-LATCH** (E826: the fault still latched right after the flush). Explore (printed, never
scored): `peek` before, during and after each hold, replays per cell, -110 per cell, the clock status.
Verdicts are scorekit's (byte for byte main's): any non-PASS control shuts the rows it gates.

**Job count.** s0 2 rows; q 6 held jobs + 3 fills + 6 to 9 triangles (6 under H-FLUSH-in-b + H-PEND,
up to 12 with double replays) + 6 strict health pairs + begin/end health. Part P: 3 jobs (B0, B1P x2).
**About 25 to 30 tool calls in all.** Time: part H about 6 minutes of runs (a cell 20 to 30 s), part P
about 4; with staging, copies, scoring and the health checks **about 25 minutes; plan 40**.

## Stops (R6-5 (a); rank-round6.md R6-5: "budget 3 faults, stop on two -110 in a row or a health that does not pass within 3 tries")

- s0: any row not as frozen ends the session (n0's flush taken, or BIF_CTRL changed: rc 23).
- q, per cell: the job's fault must be E848's shape (bits 15:0 0x0004, a 0x2xxxx page, SB 6), every
  step fault the job's page and SB through any list (else rc 18); the **third** failing triangle of a
  cell (rc 17: no further reset, the lead decides); a refused held flush voids the K2 rows (rc 23 after
  the cell's health); **two cells in a row with "SGX recovery failed: -110"** (rc 22, after the second's
  health); fault-class events limited to **15** (6 held + one replay a cell + **3 more**: the plan's
  fault budget of 3 read as replays beyond one a cell, rc 15 with rows left); strict health after every
  cell (rc 16); every usual stop (fatal message rc 3, freeze rc 6, knobs rc 19, free space rc 21).
- Any stop ends the session; after a stop: no reboot, no module unload, no register write. `run/h.sh
  --from STAGE` is a new attempt.

## Round 4's, 5's and 6's slips: impossible by construction

- **The mock answers by argv** (`tests/worlds.py`): the held job faults only with `--tri-full`,
  `cmd:1=0xe0000000`, the maximum equal to the size and `render_rgn_arrays` 1 as written through the
  shim; the page from `--width/--height`; replays from the fake kernel's pending write, lists counted per
  job after a reset. Never a case name.
- **The argv twin** (`tests/test_twin.py`): every row against the plan rows typed by hand, and each job
  against E848's kept argv byte for byte; it fails the default triangle, another maximum, no rgn:1, a b
  cell without flush, an `--aa4`.
- **Replays before the freeze** (`tests/test_replay.py`, on E848's kept files at data e5cdaf0a): h2 as
  a0 passes every control (two replays read); h4 as a2 holds H-LIST (0x20006062) and fails H-WORD; must
  fail: h4 as a1 (the page control FAILS, the cell closes), h1 as b2 (raw H-FLUSH FAILED, raw H-BOOT
  FAILED, no flush file so the K2 rows are cannot tell), h3 as a0 (the replay control FAILS), an s0 whose
  flush was taken (every row cannot tell), a peek of another offset.
- **The staged tree, the laptop's environment only** (`tests/run_mock.sh`): every world stages a frozen
  copy of this tree (h.env's two pins replaced by the fake's, nothing else: checked) into a fake home
  through the fake scp, and the fake ssh runs it with `env -i`, HOME the fake home and a PATH of the
  laptop's commands only (no python, no perl); every log is searched for "not found".
  `tests/test_static.py` reads every line of the runner (stop paths included) for a command word that is
  neither defined, a builtin nor on that PATH (self-tested with an undefined call).
- **The scorer reads only kept files**: the model world's verdict is scored with a read log; every file
  it opened exists in the kept stage (`SCORE_READLOG`).
- **No start-up timing in the mock**: the fake sudo's `regs` read during a hold waits for the fake tool
  to have answered the latest case marker; a world runs with the fake 3 s late and HOLD_READ 0.2 s.
- **Laptop files**: `~/scratch/r6h/{run,out}` (part P `~/scratch/r6h/p/...`), one `mktemp -d
  ~/scratch/tmp/r6h.XXXXXX` a stage, each job's work directory removed once kept, the mktemp directory
  at every exit; at least 300 MiB free on ~ at the preflight and before each job (rc 21). Never /tmp.

## Q294: no rows (the oracle did not separate)

Rank decision 5 (a) runs Q294's tick-stop rows only if the S0 oracle separates the seven sa65 words.
O3 was run here before any freeze (`private/o3/`, frozen first: `PREDICTIONS.md` sha256 7ea8768d...).
Its controls that keep held (0x02000000, 0xb0000000 kept the tick 5 of 5), but every test word, and
E814's D1 word, ended in a **simulator refusal** (an unmeasured read: register 0x0728 on bit 4's path,
the leftover pclink on 7's and 10's), so all seven gave the same frozen outcome: **does not separate**.
No Q294 rows; Q294 stays low and open. Post hoc only [RE, infer]: bit 4 is tested before 7 and 10.

## Data-private (firmware-derived)

**`private/o3/` is firmware-derived** (pysgx running the stock microkernel): `PREDICTIONS.md`,
`o3_oracle.py`, `o3_oracle.json`, `o3_oracle.err`, `RESULT.md` go to **data-private only**
(`tools/records/scratch_cites.py --publish --private`); the fold must not publish them. Everything else
here is our own and publishable; `FROZEN.sha256` names the private files by path and hash only. Part P
cites E855 (landed) for its prediction, not the private reading.

## Layout and commands

`gen/hgen.py` writes `tables/`, `predictions/`, `TABLES.md`, `stages.txt`, `gen/data/sources.lst`;
`score/score_h.py` the scorer (`score/scorekit.py` byte for byte main's); `run/`: `run_h.sh`,
`lib_h.sh`, `h.env` run on the laptop, `h.sh` the driver, `stage_h.sh`, `freeze_h.sh`, `guard_h.sh`
(the session's own static guard). `tests/run_all.sh` runs every offline test, part P's included.

```
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHONDONTWRITEBYTECODE=1
export PY=/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
cd /Users/jtorra/src/scratch/resgx545/closing6/r6-held
bash tests/run_all.sh                 # offline: RUN_ALL PASSED
# part P first: see p/README.md (p/run/stage_p.sh, p/run/p.sh ATTEMPT)
run/guard_h.sh && run/freeze_h.sh verify
SGX_DRY_RUN=1 run/stage_h.sh && SGX_DRY_RUN=1 run/h.sh
run/stage_h.sh                        # copies to ~/scratch/r6h, compares, checks the tool hash
run/h.sh                              # s0 then q (gate, scores, health)
$PY score/score_h.py verdict out/ATT  # the SUMMARY lines (several ATT after a --from)
```

## Deviations from the plan

1. **Cells.** The plan's (a) is three 288 x 144 cells (fill, health, health) and (b) the same with the
   flush. Here: a0 640 x 480 with no follow-up (E848 h2's page 0x2000a, never seen in a health fault, as
   the control that a replay happens on this kernel at all, gating the K2 rows), a1 640 x 480 with a fill
   (H-LIST held out at a new size), a2 288 x 144 with a fill (h4's replicate), and three flushed cells
   (two at 640, one at 288). Same count (6 held faults), a control that can fail before the flushed rows.
2. **"Fault budget 3"** read as three replays beyond one a cell (stage limit 15 fault-class events);
   unexplained fault shapes stop at once (rc 18). **"Two -110 in a row"** read per cell (two consecutive
   cells each with a -110 anywhere in their slices); per recovery it would have stopped E848 after h1.
   **"Health within 3 tries"** = the cell's third triangle (E848's h2 drew at its third).
3. **`render_rgn_arrays` goes back to 0 before the cell's follow-up** (E848 kept it 1 to the cell's
   end): the follow-ups are a fill and 1x triangles, for which automatic is one array: no change for
   them, and the knob is never left at 1 while a step runs.
4. **`peek` reads in part H are explore only** (before, during and after each hold); Q111's decisive row
   is part P's (a B1P stop).
5. **Q294 dropped** by the plan's own condition (O3 did not separate, above).
6. **The module srcversion is frozen directly** (the lead built it before this freeze), not as a slot.
7. **300 MiB** free-space floor (HACKING's is 200).
