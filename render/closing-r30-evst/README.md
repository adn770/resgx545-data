# r30-evst

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 9cfced4db831 (data 2da506767cf6), module srcversion
E0CC40275493F8AEAD8180B, laptop prefix `r30e`. **Safe class**: no knob, no kreg, no register
write, no planned fault or hang; regtimeline only reads. Nothing assumes cachix (travel cable).
Records reserved: **E1115, E1116**.

## Why

The firmware-in-sim run of main 9cfced4 (fwsim, M2 kick): after a render job's TA kick (one
plain 64 x 64 triangle, FIRST and LAST) the microkernel writes CR_CACHE_CTRL (0x0804, E013),
then reads CR_EVENT_STATUS (0x012c) in a loop while the cache invalidation runs; no kept reading
gives the value it needs, so the simulator stops (crates/sgx-sim/src/hw.rs refuses unclaimed
reads). The kept readings closest to it are E547's: the idle word 0x20000000, and
MADD_CACHE_INVALCOMPLETE (bit 26) in 5 of 10 tri64 jobs, always as the word 0x24000000, 53 to
81 us wide, the first bit of the job, 88 to 128 us before the render end (bits 18 and 0); at 1.22
us sampling 4 of 5, at 2.67 us 1 of 5. CR_USE0_SERV_EVENT (0x0b14) is modelled only across ticks
(E009; hw.rs drops its count at the first served kick). This session samples them densely across
plain triangles and across idle, to seed the fwsim hardware read rule (Q111, E547, E009, E017).

## What runs

Every row: t10 (`~/sgxfive-test-t10`, sha256 9bedc2d6..., source a581c06, as every round since
10) running E547's `tri --width 64 --height 64` (e5: `-n 3`) under regtimeline (`rt`, sha256
079f6359..., read only, as r20-own and r23-dpm bind it), `TOTAL LEAD REGS --
"$HOME/sgxfive-test-t10"
...`. In run order:

| stage | rows | REGS | TOTAL LEAD | what it reads |
|---|---|---|---|---|
| e1 | 16 (2 controls, 6 fit, 8 held) | 0x012c | 1.5 0.5 | bit 26 at the densest sampling |
| e5 | 7 (2, 2, 3) | 0x012c | 1.5 0.5 | `-n 3`: a bit 26 episode per render or per job |
| e2 | 12 (2, 4, 6) | 0x0118, 0x012c, 0x0804, 0x0b14 | 1.5 0.5 | STATUS2, CACHE_CTRL, SERV_EVENT |
| e3 | 10 (2, 3, 5) | 27: r23-dpm's set, 0x0218, R4 | 0 0.3 | density; a pipeline anchor |
| e4 | 2 (1, 0, 1) | as e2 | 6 5.5 | 5.5 s idle, then one triangle |

47 jobs. The lead window (0.3 to 5.5 s after the runner's reset) is the idle sample of every row;
e1, e2, e5 and e4 also sample about 0.9 s after the job. Every register is one the existing
timeline tooling already read around a kick (E258's register-timelines set, E547's event-timelines
sets, r23-dpm's rows), and 0x0b14, which every kit job's `regs` snapshot reads (E009);
tests/test_session.py checks it. Time: about 10 s a job with the reset and snapshots [infer]:
8 to 10 minutes of jobs, 12 to 15 with staging. Alarms 900, 600, 900, 900, 600 s.

**Sampling.** regtimeline reads the registers in a tight loop and keeps the changes; its mean
interval (`ivl`, the run's length over its samples) was 1.7 to 1.8 us with 2 registers and 3.9 to
4.7 us with 7 in E547's kept rows; one register cannot go much below a microsecond (one uncached
read and a clock read a sample) [infer]. A pulse under one sample is not seen, and the tool does
not report its longest gap (a preemption), so a miss is never bounded per job. This is the
best the tool can do: e1 gives the densest rate, e3 the contrast.

## Hypotheses (frozen: predictions/*.tsv from gen/make.py)

Fit: E547's kept tri64 rows (tests/test_session.py replays the scorer on them) and each stage's
fit rows; held out: the held rows. Inferences [infer].

- **H-ALONE** (Q111 bit 26, the read rule's word): while bit 26 is set CR_EVENT_STATUS reads
  0x24000000 exactly. **H-WIDE**: 40 to 140 us. **H-BEFORE** (Q111 order within a job): its first
  rise is 60 to 200 us before the first rise of bit 18 or 0 and it falls before that.
- **H-EVERY** (seen in 13 or 14 of e1's 14 rows) against **H-PART** (0 to 12) [infer: E547's r2
  4 of 5]. **H-DENSITY** (e1's seen fraction at least 0.4 above e3's) against **H-INDEP** (within
  0.25): the miss is under a sample, or an absence.
- **H-ONCE** (e5: no row with two or more bit 26 episodes) against **H-EACH** (2 or more rows of
  5); 1 row: cannot tell.
- **H-SW** (14 and 31 together, E547 41 of 41), **H-SUB** (bits 6, 9, 20, which E548 armed,
  never seen: their pulses are under a sample), **H-IDLE** (0x012c 0x20000000 outside the job
  window, end plus 5 ms; E547).
- **H-ST2** (0x0118 0x400 throughout, E547). **H-CC-FLAT** (0x0804 1000ffff throughout, E258 at
  about 75 us) [infer]; a change is read with its lead to bit 26's rise (`cc26`, the CACHE_CTRL
  write to the invalidation's end) [infer].
- **H-SE-EVENTS** (0x0b14 counts 3 or more beyond the ticks over the job window, the rate from
  the lead window) against **H-SE-TICKS** (within 1) [infer: E009's COUNT reading].
- e4: the tick rate 0.9 to 1.1 counts a ms (E009) and H-IDLE over 5.5 s.

Controls (first and last row of each stage; e4 first only), all can fail: the draw (`diff` 0),
`idle` 0x20000000, `ivl` within the stage's window, and with R4: `idle2` 0x400, `cache` 1000ffff,
`se16` 1. A FAILED control voids its stage's headlines.

**Decides** (with the controls passing): the bit 26 word, width, order against the render end, its
seen rate at the densest sampling and against density, one or more a render; 0x0118 and 0x0804
across a kick; 0x0b14's count and bit 16 across a served kick. **Cannot decide**: the time from
the CACHE_CTRL write to bit 26 (unless 0x0804 shows the write), how many polls the loop makes,
whether an unseen bit 26 rose under a sample, who clears it (the firmware's acknowledgement is
[infer], E547), and which hardware event sets it beyond the order.

## Stops

- hook_check (rc 24): no `tri: N renders ok` or a draw that is not exact; no timeline, a cut one,
  or regtimeline's rc not 0; 0x0118 bit 6 or 7 (a hang latch, E357); with 0x0b14 sampled, bit 16
  clear in the last sample or under half a count a ms (the tick stopped). e1 and e5 go on to the
  next stage; e2, e3 and e4 end the session (`on_stop = "end"`).
- A control without its reading: the premise stops (25). Any fault, hang or failure: the kit's
  stop (4). `#limit 0` everywhere.

## Mock worlds

`model` (every stage 0), `nodiff` (e1 and e5 24, e2 24 ends), `latch` (e2 24 ends), `tickstop`
(e2 24 ends), `notl` (no timeline: as nodiff). The kit's fake prints its samples 1 us apart with
start 0 end 0, so the mock checks the flow and the hooks; the scorer is tested on E547's kept
rows and synthetic timelines.

## Replay vectors

No vectors table: closing_tables.py has no kind for event timelines, so e1 to e5 are **refused**
as tables. The fold seeds crates/sgx-sim/src/hw.rs's read rules for 0x012c (and 0x0b14 if
H-SE-EVENTS or H-SE-TICKS holds) from the kept readings with a test that reads the kept
`.txt` files (the fold names it); everything it needs is in the kept files and the pins.

## Commands

- Offline: `bash tests/run_all.sh`. Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Freeze: `python3 kit/session.py freeze .` (done). Laptop: `python3 kit/session.py stage .`, then
  `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE out/ATT/STAGE out/ATT` (e3 reads e1 from the attempt);
  one job: `python3 score/score.py file NAME.txt`.

No firmware-derived file: nothing here goes to data-private. The "Why" paragraph states one fact
of the fwsim run (what the microkernel does after the kick), no trace content; the lead decides
whether it stays (resgx545 FW trace separation rule).

Every command is run through its interpreter, never by its mode bits; Python is the repo's own,
`$HOME/src/resgx545/.venv/bin/python`. The driver keeps its own logs, `out/stage.log` and
`out/ATTEMPT/run.log`; tee nothing into this directory's top.
