# r10-dpm: the fold (2026-11-13, the builder)

Run by the lead on the laptop, attempt `out/20261113-102513` (driver log `fold/run-r10d.log`, the
lead's `closing10/logs/r10-dpm-run.log` copied), driver rc 0: the one stage ran, 17 jobs, no stop,
no fault, no lead decision. Folded as E1009. README.md, PREFLIGHT.md and FOLD-NOTES.md are the
pre-run documents, unchanged; nothing frozen was changed.

- `fold/reproduce.sh`: the frozen scorer re-run on the kept stage is byte-identical to the kept
  `score-s6rep.txt` (`fold/reproduce.out`). No post-run scorer fix.
- `fold/readall.py` and `fold/brackets.py` (POST HOC, written after the score was read; outputs
  `readall.out`, `brackets.out`): every row's steps beside the replay and the sampled bracket of
  S_6 against it.

## What the frozen score said

Both controls PASS (the a0 pair repeats E935 on B60AB0B4). Per target, S_6 of the three replicates
(replay R in brackets): 4096x1024 0x17d, 0x17e, 0x17e (0x17c); 4096x1536 0x22a, 0x245, 0x22b
(0x229); 3584x1024 0x14e, 0x14f, 0x14e (0x14d); 2048x512 0x6f x 3 (0x6e); 2048x2304 0x1ad x 3
(0x1ac). H-NOISE 0 of 5 targets (R never inside the range); H-BIAS 4 of 5; the DECISION line:
BIAS decided (4 of 5, at most 1 NOISE). The fifth target, 4096x1536, is NEITHER only because one
replicate's S_6 is 0x245, 28 pages above R: a sampling gap, not a page step.

## Post hoc: why 0x245 is not a miss of the bias

The reader's S_6 is the upper end of the bracket the two samples around the global page step give
(`score/read.py`: S_k = max(a, b - 1), a and b the 0x0724 high halves before and after). Every
replicate's bracket has a = R + 1 (`brackets.out`): the page count was R + 1 or more already
when global page 6 was taken, in 15 of 15 replicates and in every kept read of the same targets
(E962's four, E961's seven at 2048x2304). The width of the bracket is the sampler's: 1 page in 10
replicates, 2 in 4, 28 in the 0x245 one (a stalled sample). So the replay is below the bracket's
lower end at all five targets, which is the bias; the spread above it (0 to 1 page, or one wide
gap) is the sampler's. The same spread shows at other steps: S_2 of 2048x512 0x1a, 0x1b, 0x1b and of
4096x1536 0x73, 0x74, 0x74; S_3 of 4096x1536 and 2048x2304 one above the replay in every
replicate (so S_3 is biased there too, E961, E962). These are readings after the score, not a
verdict.

## What it leaves open (Q210)

- No rule for where the offset is: 0 at 1280x1280, 1536x1536, 1792x1792, 2048x2048, 2304x1792,
  2304x2304 (cells), 2560x2048 and 4096x2048, R + 1 at the five targets here (the lower end). No
  parameter of the replay (lag, block, cap) was refitted: a refit on five targets with no held-out
  target would be a fit of its own noise. The offline candidates are for a later round.
- A calibration at P 0x422 against a partial-render cell: 2304x2304 read S_6 0x1e1 in its
  calibration and 0x1dd in its cells (r9-ldpm); the replicates here are all calibrations.
