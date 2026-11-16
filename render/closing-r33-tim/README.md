# r33-tim

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main f888bb7694a6 (the kit as merged; no branch),
data 052c0a8bf76b, module srcversion 7CE8E38EDB97FC5EA4F6C90 (fork 8bc0877e8603), laptop prefix
`r33t`, over the travel cable. **Safe class**: no knob, no kreg, no register write, no planned
fault or hang; regtimeline only reads through /dev/mem. Records reserved: **E1131** (t1 and t1d);
E1132 (t2) is not built (below); E1133 spare.

## Why

fwsim's M2 kick under replay (E1130) passes the CR_EVENT_STATUS poll, writes bit 26 to
CR_EVENT_HOST_CLEAR and emits PDS #14, which passes the counter `tim` on to its task (E146: `ir0`
and the timer to destination words 0 and 0x200); no record gives `tim` there, so the run stops.
`tim` is CR_EVENT_TIMER (0x0acc; doc/specs/pds_isa.md "Input and special registers" and 8.9).
This session samples 0x0acc across the window the kick pass runs in, from CR_CACHE_CTRL's change
to 0x1000ffff (the pass's own write, E1120, E1122, E1123, E1126) to bit 26's fall (E1115, E1120),
so that fwsim can state a `tim` rule: the count at the change minus the rate times the time since.

The model, from the records that measured the timer: bits 31:24 0x01 (bit 24 the run bit), bits
23:0 counting down 400000 core clocks and reloading by themselves (E008, E532's correction, E746,
E751, hw_spec 12.2); 997.46 ticks a second, so 398.98 counts a us (E009 via hw_spec 12 and
boot_sequence 2.1); written by the firmware only at boot and POWER resume (E010, pds_isa), so not
in a kick pass [infer]; a kick's pa2 is the timer as sampled, at any phase (E746, E747). The kit
snapshots of r30-evst2, r31-cc and r32-misc read 0x0acc 208 of 208 with bit 24 set and bits 23:0
below 400000 (post hoc, counted while building).

## What runs

Every job: t10 (`~/sgxfive-test-t10`, sha256 9bedc2d6..., source a581c06) `tri --width 64
--height 64` after the kit's reset, under regtimeline (`rt`, `~/regtimeline`, sha256
079f6359..., read only). In run order:

| stage | rows | regtimeline | what it reads |
|---|---|---|---|
| t1 | 11: c1, 01-04, c2, 05-08, c3 | `0.06 0.005 0x012c,0x0804,0x0acc` | the window and the timer |
| t1d | 4: c1, 01-03 | `0.04 0.005 0x0acc` (densest, about 540 ns) | the timer alone |

15 jobs. Sampling starts 5 ms before t10 and stops 60 ms (t1) or 40 ms (t1d) after regtimeline
starts, so CR_CACHE_CTRL's change (18.3 to 25.2 ms after the tool starts, E1122, E1127) falls
inside it with 30 ms to spare; the tool runs on to its end after the sampling stops. With 0x0acc
in the set every sample is a change, so every sample is stored: about 50 000 lines a t1 job and
74 000 a t1d job (1.5 to 2.5 MB of text, about 1 MB gzipped each; some 15 MB for the session)
[infer]; regtimeline's store holds 3.3 million at three registers. Time: r31-cc's 52 jobs took
about 12 minutes, so about 4 minutes of jobs, 6 to 8 with staging [infer]. Alarms 900 s a stage.

## Hypotheses (frozen: predictions/*.tsv from gen/make.py; every row held out)

Every row, both stages (the timer over the whole timeline; score/score.py's docstring defines each
reading):

- **H-TIM-EN**: no sample without bit 24 alone in 31:24 (`tnoen` 0).
- **H-TIM-RANGE**: no sample with bits 23:0 at 400000 or more (`tover` 0), against **H-TIM-24**
  (a free 24-bit counter: some sample above).
- **H-TIM-RELOAD**: the largest count 398500 to 399999 (the reload to 400000, E008, E532).
- **H-TIM-399** (rate 398.5 to 399.5 counts/us, period 1001.2 to 1003.8 us; E009) against
  **H-TIM-400** (399.5 to 400.5, 998.8 to 1001.2: the DDK's 400 MHz). The timeline is cut at each
  reload; each piece is fitted by least squares; rate is minus the median slope and period the
  median spacing of the pieces' zero crossings.

t1 rows, the window:

- **H-CC-ONE** (one change, to 0x1000ffff) and **H-CC-LAT** (10 to 40 ms after the tool starts),
  the window's premise and E1122's repeat.
- **H-TIM-FREE**: in the window (the change sample to bit 26's fall; without a bit 26 episode in
  the 200 us after the change, to the change + 120 us) the count follows `tcc - rpre x (t -
  t_change)` mod 400000, where `rpre` is the rate fitted on the samples more than 2 us before the
  change only (fit outside, held out inside): median and last-quarter |residual| at most 300
  counts (0.75 us), 90 % of the samples within 400; against **H-TIM-WRITE**: the last quarter's
  median |residual| 2000 or more (the kick pass writes or reloads the timer).
- **H-TIM-ASYNC**: the count at the change (`tcc`) spreads over 100 000 counts or more of the
  400 000 circle across the decided rows (5 at least; E746, E747), against **H-TIM-SYNC** (within
  20 000: the kick pass at a fixed phase of the tick). The stage case `t1-all`.

Controls, all can fail: t1-c1, t1-c2, t1-c3, t1d-c1: `diff` 0, `ivl` (700 to 2000 ns in t1, 400 to
1200 in t1d), `ten` 1 (every stored 0x0acc sample a running count) as the runner's premise
(`reads:diff,ivl,ten`), and **snap0's and snap9's 0x0acc** a running count (`ten0`, `ten9` 1),
scored by score.py and not a premise (the kit's mock snapshots have no 0x0acc). A timer stopped
or zeroed (POWER IDLE writes 0, pds_isa) fails them.

## What decides, what cannot

- **Decides**: the rate (399 against 400 counts a us, a 0.25 % gap measured over about 60 reloads
  a row), the range and reload, whether the kick pass's window leaves the count on its line, and
  whether the phase at the change is free. With H-TIM-FREE and H-TIM-ASYNC held, fwsim's rule is
  [infer]: `tim` = 0x01000000 | ((tcc - 399.0 x elapsed us) mod 400000), with tcc the count at
  the CR_CACHE_CTRL write taken from the replayed kept row, or equivalently 400000 less the
  clocks since the last tick's reload (pa2 of a tick served at once is 0x01061a70, E532).
- **Cannot**: the count PDS #14 itself reads (its `tim` read is inside the kick pass, between two
  samples; the window bounds it within one sample, 0.5 to 1.2 us, i.e. 200 to 480 counts); where
  PDS #14's douta writes the count (t2, below); the TA kick and anything later. The host's clock
  (CLOCK_MONOTONIC, not NTP-checked on the road) carries the rate: its error is far below the
  0.25 % the pair separates [infer].

## t2 (left out: no safe form)

The question: an emitted PDS program that does `douta` to attributes 0 and 2 then `doutu`, with
the started task storing pa0, pa2, sa0 and sa2, to tell whether an emitted program's douta lands
in the primary (pa) or the secondary (sa) attributes. No tool on the laptop can run it safely:

- **t10 and t30** (`probe --place OFFSET=FILE --pds N --use USE`, resgx545 a581c06 and 42c4de7
  alike): the placed USE program can `emitpds` the fill's PDS secondary (the 0x5CB0 limm patch),
  whose douta and doutu would start the `--use` program, which can store pa0, pa2, sa0 and sa2 to
  scratch. But a client `emitpds` faulted or hung every job (E488 24 of 24, E520 39 of 39,
  usse_isa 6.26, Q128): a planned fault each row, so a flagged stage needing the user's OK, not
  safe class; and the fill's own secondary runs the same program, so the rows must tell the
  emitted run from the fill's own (E520 did it by `ir0`: 3 or 2 against 0x400 to 0x403).
- Without the emit, `probe --pds N --use USE` runs the program as the fill's own secondary, not
  emitted (E125, E381, E390 already measured douta there): it does not answer the question.
- **Own firmware tasks** (tools/fwtask, the kernel's sgxfive_owntask.c verifier): `emitpds` is
  refused (gen_verify.py's crafted blob `emitpds`, Why UNKNOWN, -EPERM), and the kit has no job
  kind that arms an own task.

What it needs, either: (a) a flagged t10 or t30 stage (the user's OK; one planned fault per row,
E488's
recovery), rows whose PDS program writes `ir0`-tagged words with douta 0 and 2 and whose USE
program stores pa0, pa2, sa0, sa2 and a marker; or (b) a module change allowing one `emitpds`
form in own tasks (the verifier table in tools/fwtask/gen_verify.py, KUnit and host tests, the
PDS page and its USE task placed by the loader), a one-shot boot with the user's OK, and a kit job
kind for own-task arms (added to the kit with a test). (b) is the one that measures the firmware's
own path (an EDM emit), which is what PDS #14 is [infer].

## Stops

hook_check (rc 24): a row that does not draw exactly or lacks `tri: 1 renders ok`; a missing or
cut timeline, or regtimeline's rc not 0. A control without its reading: 25. Any fault or hang in
a job: 4. `#limit 0` everywhere. Both stages declare `on_stop = "end"`: a stop ends the session.

## Mock worlds

`model` (both 0), `nodiff` (t1 stops at its first row, 24), `notl` (t1 stops at its first row, 24),
`timerstop` (0x0acc reads 0: no stop, the controls' `ten` reads 0 and the scorer fails them).
The kit's fake timeline is 1 us a sample with TOTAL 0, so `ivl` is the stored rows' step there.
The scorer is tested on synthetic timelines built on r30-evst2's kept rows (e2-01: bit 26 39.1 us
after the change, 5.0 us wide; e2-02: none) that decide each pair both ways and that cannot tell
(no change), and on r32-misc's kept snapshots (snap0 0x01041c73).

## Replay vectors

No vectors table (closing_tables.py has no timeline kind): t1 and t1d refused as tables. The fold
changes sgx-sim's hardware model (crates/sgx-sim/src/hw.rs) and tools/fwsim's seeds or replay
rules for CR_EVENT_TIMER only from what the frozen rows decide (test first, on the kept `.txt`
files); otherwise the refusal stays and names E1131.

## Commands

- Offline: `bash tests/run_all.sh`. Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Freeze: `python3 kit/session.py freeze .`. Laptop: `python3 kit/session.py stage .`, then
  `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE out/ATT/STAGE`.

Fold notes: FOLD-NOTES.md. No firmware-derived file: nothing here goes to data-private. Python is
the repo's own `.venv` (`$HOME/src/resgx545/.venv/bin/python`); every command is run through its
interpreter.
