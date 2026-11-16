# r30-evst2

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 24e4a365f48b (data a1c3d8c362d9), module
srcversion 7CE8E38EDB97FC5EA4F6C90 (N1, booted; same render paths), laptop prefix `r30f`.
**Safe class**: no knob, no kreg, no register write, no planned fault or hang; regtimeline only
reads. Nothing assumes cachix. Records reserved: **E1117, E1118**.

## Why

The corrected rerun of r30-evst (E1115, E1116). r30-evst's stages e2, e3 and e4 decided nothing:
their controls were frozen on CR_CACHE_CTRL 0x1000ffff, taken from E258 (read mid-session with no
reset), while the kit resets before every row and its own `snap0.regs` read 0x0000ffff (E1116,
the builder's error). Here the control premises are the kit's post-reset values, and E1116's
post-hoc readings are frozen as held-out hypotheses, so the fwsim read rule for CR_EVENT_STATUS
after a render kick (CR_CACHE_CTRL written, then a loop on 0x012c) and CR_USE0_SERV_EVENT across
a kick can be seeded from frozen rows (Q111, E009, E1115, E1116).

## What runs

Every row: t10 (`~/sgxfive-test-t10`, sha256 9bedc2d6..., source a581c06) running
`tri --width 64 --height 64` (e5: `-n 3`) under regtimeline (`rt`, sha256 079f6359..., read
only), `TOTAL LEAD REGS -- "$HOME/sgxfive-test-t10" ...`. In run order:

| stage | rows | REGS | TOTAL LEAD | what it reads |
|---|---|---|---|---|
| e1 | 10 (2 controls, 8 held) | 0x012c | 1.5 0.5 | the 1-register contrast |
| e5 | 7 (2, 5) | 0x012c | 1.5 0.5 | `-n 3`: bit 26 per render or per job |
| e2 | 12 (2, 10) | 0x0118, 0x012c, 0x0804, 0x0b14 | 1.5 0.5 | CACHE_CTRL, SERV_EVENT |
| e3 | 10 (2, 8) | 27: r23-dpm's set, 0x0218, R4 | 0 0.3 | 27 registers |
| e4 | 2 (1, 1) | as e2 | 6 5.5 | 5.5 s idle, then one triangle |

41 jobs, the registers r30-evst read (tests/test_session.py checks them against the existing
timeline tooling's). Time: r30-evst's 47 jobs ran 12:35 to 12:43 on the laptop's clock, so
about 7 to 8 minutes of jobs, 10 to 12 with staging. Alarms 900, 600, 900, 900, 600 s.

## Hypotheses (frozen: predictions/*.tsv from gen/make.py; every row held out)

Every model is frozen from r30-evst's kept rows (E1115 decided, E1116 post hoc); no row of this
session fits anything. Inferences [infer].

- Every event stage: **H-ALONE** (bit 26 reads 0x24000000 alone, 29 of 29 episodes), **H-SW**,
  **H-IDLE** (0x20000000 outside the job).
- e1: **H-WIDE1** (bit 26's first episode 40 to 140 us; E1115 7 of 8), **H-BEFORE** (first rise
  60 to 200 us before the first rise of bit 18 or 0, fallen before it), **H-SUB**; **H-PART**
  (seen in 0 to 7 of 8) against **H-EVERY** (8 of 8).
- e5, restated: **H-ONCE** (at most 2 of 5 rows with two or more bit 26 episodes) against
  **H-EACH** (3 or more rows with three or more, one a render); anything else refutes both.
- e2, e4: **H-NARROW4** (first episode 3 to 12 us with four registers; E1116 4.9 to 7.6). e3:
  **H-NARROW27** (8 to 20 us; E1116 11.8 to 12.6). Together with H-WIDE1: the width depends on
  what is sampled beside CR_EVENT_STATUS [infer].
- e2-e4: **H-CC-KICK** (CR_CACHE_CTRL 0x0000ffff after the reset, 0x1000ffff from its one change
  to the end of the run, the change 15 to 60 us before bit 26's first rise; that lead is read
  only where bit 26 precedes a render end the row saw, cannot tell otherwise: E1116's two late
  rows, 16 and 21 ms, had none) against **H-CC-FLAT** (no change). **H-SE-EVENTS** (0x0b14 7 to
  13 counts beyond the ticks over the job; E1116 9 to 11) against **H-SE-TICKS** (within 1).
- e3: **H-DENSITY** (e1's seen fraction at least 0.2 above e3's) against **H-INDEP** (within
  0.2) [infer]. e4: the tick rate 0.9 to 1.1 counts a ms.

Controls (first and last row of each stage; e4 first only), all can fail: diff 0, idle
0x20000000, ivl in the stage's window, and with R4: idle2 0x400, **cache 0x0000ffff** (the kit's
`snap0.regs` after the reset; tests/test_session.py reads r30-evst's e2-c1 snapshot), se16 1.

**Decides**: the CACHE_CTRL change at the kick and its lead to bit 26 (the read rule's anchor: the
firmware's write to the invalidation's end [infer]), CR_USE0_SERV_EVENT's counts across a served
triangle, bit 26's width against what is sampled, bit 26 per render in `-n 3`. **Cannot
decide**: the loop's read count, whether an unseen bit 26 rose under a sample, who clears it,
whether CACHE_CTRL bit 28 is the firmware's write or the hardware's.

## Stops

As r30-evst: hook_check (rc 24) on a draw that is not exact, a missing or cut timeline,
regtimeline's rc not 0, a 0x0118 hang latch, a tick stop where 0x0b14 is sampled; e1 and e5 go
on, e2, e3 and e4 end the session. A control without its reading: 25. Any fault or hang: 4.
`#limit 0` everywhere.

## Mock worlds

`model` (every stage 0), `nodiff`, `latch`, `tickstop`, `notl` (as r30-evst). The kit's fake
prints samples 1 us apart with start 0 end 0: the mock checks the flow and the hooks, the
scorer is tested on E547's and r30-evst's kept rows and synthetic timelines.

## Replay vectors

No vectors table (closing_tables.py has no timeline kind): e1 to e5 refused as tables. A fold
seeds crates/sgx-sim/src/hw.rs (the E1115 idle rule's refusal after a kick, the E009 count after
a kick) only from what the frozen rows decide, with a test on the kept `.txt` files.

## Commands

- Offline: `bash tests/run_all.sh`. Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Freeze: `python3 kit/session.py freeze .` (done). Laptop: `python3 kit/session.py stage .`,
  then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE out/ATT/STAGE out/ATT`; one job: `python3 score/score.py
  file NAME.txt`.

No firmware-derived file: nothing here goes to data-private. Python is the repo's own
`.venv`; every command is run through its interpreter.
