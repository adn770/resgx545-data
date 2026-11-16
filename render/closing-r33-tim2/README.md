# r33-tim2

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main 7dba6bd12e84 (the kit's fake regtimeline gives
the laptop's sample spacing), data 052c0a8bf76b, module srcversion 7CE8E38EDB97FC5EA4F6C90 (fork
8bc0877e8603), laptop prefix `r33u`, over the travel cable. **Safe class**: no knob, no kreg, no
register write, no planned fault or hang; regtimeline only reads through /dev/mem. Record
reserved: **E1133**.

## Why

The rerun of r33-tim (E1131). fwsim's M2 kick (E1130) stops on PDS #14, which passes the counter
`tim` (CR_EVENT_TIMER, 0x0acc; E146, pds_isa) to its task; this session samples 0x0acc across the
window the kick pass runs in, from CR_CACHE_CTRL's change (E1120, E1122, E1123, E1126) to bit 26's
fall (E1115, E1120), so that fwsim can state a `tim` rule. r33-tim ran clean, but every control
failed on its sample interval: the builder froze the idle loop's spacing of E1115, E1120 and E1122
(TOTAL / samples over 1.5 s windows that are mostly idle), while these windows are almost all job
time, where the sampler is spaced 4.6 to 6.2 us (E1131). Nothing was decided. This rerun keeps
the design and freezes the interval from E1131's measurement and E1131's post-hoc readings as
held-out hypotheses.

Two corrections from E1131, in the scorer and the hooks (not new hypotheses): a running count
reaches 400000 itself (t1-c2 read 0x01061a80 once), so `ten` and `tover` take bits 23:0 up to
400000; and the window is read against the count's own line fitted on the 1 ms before the change
(twice, the second time without the samples more than 1000 counts off the first fit), not against
the change sample, which can be a read late after its timestamp (t1-08: 29478 counts low).

## What runs

As r33-tim. Every job: t10 (`~/sgxfive-test-t10`, sha256 9bedc2d6..., source a581c06) `tri --width
64 --height 64` after the kit's reset, under regtimeline (`rt`, `~/regtimeline`, sha256
079f6359..., read only). In run order:

| stage | rows | regtimeline | what it reads |
|---|---|---|---|
| t1 | 11: c1, 01-04, c2, 05-08, c3 | `0.06 0.005 0x012c,0x0804,0x0acc` | the window and the timer |
| t1d | 4: c1, 01-03 | `0.04 0.005 0x0acc` | the timer alone |

15 jobs. Sampling starts 5 ms before t10 and stops 60 ms (t1) or 40 ms (t1d) after regtimeline
starts; the change came 22.93 to 24.10 ms after the tool started in E1131. E1131's whole
published session is 1.9 MB. Time: E1131's 15 jobs took about 2.5 minutes of
stages (21:10:55 to about 21:13), 5 to 7 with staging. Alarms 900 s a stage.

## Hypotheses (frozen: predictions/*.tsv from gen/make.py; every row held out)

Values from E1131's post-hoc readings (render/closing-r33-tim fold/posthoc.txt, not frozen there)
and the earlier timer records; score/score.py's docstring defines each reading.

Every row, both stages:

- **H-SPACING**: the sampler's median spacing before t10 starts (t1 1100 to 1500 ns, t1d 550 to
  900; E1131 1213 to 1283 and 622 to 782) and while it runs (3500 to 7500 ns; E1131 4592 to 6190).
- **H-TIM-EN**: no sample without bit 24 alone in 31:24 (E1131 15 of 15).
- **H-TIM-RANGE**: no sample above 400000 (`tover` 0), against **H-TIM-24**.
- **H-TIM-RELOAD**: the largest count 399500 to 400000 (E1131 399960 to 400000).
- **H-TIM-399** (rate 398.9 to 399.1 counts/us, period 1002.40 to 1002.65 us; E1131 398.96 to
  399.01 and 1002.497 to 1002.535; E009) against **H-TIM-400** (399.5 to 400.5, 998.8 to 1001.2).

t1 rows:

- **H-CC-ONE** (one change, to 0x1000ffff) and **H-CC-LAT** (18 to 27 ms after the tool starts;
  E1131, E1122, E1127).
- **H-TIM-LINE**: against the line fitted on the 1 ms before the change, the window's median
  |residual| (the change sample to bit 26's fall, or + 120 us) at most 800 counts and the median
  residual 120 to 300 us after the change at most 400 (E1131: 28 to 633, and within 93 in 10 of
  11 rows, 347 in one); against **H-TIM-WRITE**: that 120 to 300 us median 2000 counts or more off
  the line (a write, reload or stop by the kick pass leaves the count off its line for good).
- **H-TIM-ASYNC**: the line's count at the change spreads over 100 000 counts or more across the
  decided rows (5 at least; E1131 7389 to 384863; E746, E747), against **H-TIM-SYNC** (within
  20 000). The stage case `t1-all`.

Controls, all can fail: t1-c1, t1-c2, t1-c3, t1d-c1: `diff` 0, `ivl` (TOTAL / samples: t1 3500 to
6500 ns, t1d 2500 to 5000; E1131 4061 to 4992 and 3002 to 3696), `ten` 1 (every stored 0x0acc
sample a running count) as the runner's premise (`reads:diff,ivl,ten`), and snap0's and snap9's
0x0acc a running count (`ten0`, `ten9` 1), scored and not a premise (the kit's mock snapshots
have no 0x0acc). A stopped or zeroed timer fails them.

## What decides, what cannot

- **Decides**: the rate (399 against 400 counts a us), range and reload; whether the count stays
  on its pre-change line through the kick pass's window and after it; whether its phase at the
  change is free. With H-TIM-LINE, H-TIM-ASYNC and H-TIM-399 held, fwsim's rule is [infer]: `tim`
  = 0x01000000 | ((lcc - 399.0 x elapsed us) mod 400000), lcc the count at the CR_CACHE_CTRL write,
  taken from the replayed kept row.
- **Cannot**: the count PDS #14 itself reads (inside the pass, between samples 4.8 to 7.1 us apart
  in E1131: 1900 to 2800 counts); whether E1131's transient +600 count step 18 to 40 us after the
  change is the host's read timing or the counter (H-TIM-LINE's 800 bound admits it; the 120 to
  300 us clause says only that it does not last); where PDS #14's douta lands (t2, not built;
  r33-tim's README "t2"); bit 26's episodes that fall between samples.

## Stops

As r33-tim. hook_check (rc 24): a row that does not draw exactly or lacks `tri: 1 renders ok`; a
missing or cut timeline, or regtimeline's rc not 0. A control without its reading: 25. Any fault
or hang: 4. `#limit 0` everywhere. Both stages `on_stop = "end"`.

## Mock worlds

`model` (both 0), `nodiff` (t1 stops at its first row, 24), `notl` (t1 stops at its first row, 24),
`timerstop` (0x0acc reads 0: no stop, the controls' `ten` reads 0 and the scorer fails them). The
world's `interval_ns` gives the kit's fake (7dba6bd) E1131's job spacing (4800 ns with three
registers, 3300 with one), so the controls' `ivl` passes there. The scorer is tested on synthetic
timelines built on r30-evst2's kept rows (lead 1213 ns and job 4800 ns a sample), decided both
ways for each pair, cannot tell without a change, a late read at the change moving only `rcc`
(E1131's t1-08), and the reload word read as a running count (t1-c2). E1131's own kept rows are
not pinned (its data branch is not on data main); fold/ replays the scorer on them post hoc.

## Replay vectors

No vectors table (closing_tables.py has no timeline kind): t1 and t1d refused as tables. The fold
changes sgx-sim's hardware model and tools/fwsim's seeds or replay rules for CR_EVENT_TIMER only
from what the frozen rows decide (test first, on the kept `.txt` files).

## Commands

- Offline: `bash tests/run_all.sh`. Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Freeze: `python3 kit/session.py freeze .`. Laptop: `python3 kit/session.py stage .`, then
  `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE out/ATT/STAGE`.

Fold notes: FOLD-NOTES.md. No firmware-derived file: nothing here goes to data-private. Python is
the repo's own `.venv` (`$HOME/src/resgx545/.venv/bin/python`); every command is run through its
interpreter.
