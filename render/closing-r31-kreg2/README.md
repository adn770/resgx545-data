# r31-kreg2

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 2ffa9a93727d.

**Q024** (pds, low; E045, E141, E396, E1114): "does CR_PDS_REG_0A78 change timing, when two of
its values were slower in one timing run?" The rerun of r29-kreg (E1114, whose frozen control
rule was voided by one slow control job, c11) with the control rule fixed before the run, and
the second load E1114 could not time. Kit word `kreg:0x0a78=V` in flagged stages only, values
0x00-0x3f, read back and restored to 0x2c after every job, never on an expectfault row: the
user's approval in round 29 (closing29/DECISIONS-R29.md, closing29/kreg/design.md). Records
E1124 (k1) and E1125 (k2) [the builder's pick: r31-cc had claimed none when this was built, so
E1122-E1123 are left to it; the lead renumbers at the fold if they differ].

**What runs** (`python3 kit/session.py run .`, in order; tools t10 and t30, nothing built):

| stage | class | rows | jobs |
|---|---|---|---|
| s0 | safe, end | c0-tri (64x64 exact), r1-r8 (L1, t10), v1-v8 (L2, t30); no write | 17 |
| k1 | flagged, gate c0-tri r1-r8, end | L1: 128 value rows, c01-c16 (0x2c), c-end | 145 |
| k2 | flagged, gate c0-tri v1-v8, end | L2: 128 value rows, c01-c16 (0x2c), c-end | 145 |

307 jobs. Time [infer from r29-kreg's attempt 20261116-061842: 9 s0 jobs in 80 s, 144 k1 jobs
in 802 s, about 5.6 s a job]: s0 about 2 min, k1 about 14 min, k2 about 15 min (six render
contexts a job, each render a few ms on the library mock; never timed on the laptop), with
staging and the preflight about 40 minutes, inside the 90 minute budget. Both loads fit: no
split. If k2's jobs prove much slower, k2's alarm (7200 s) bounds it; the user may stop after
k1 and rerun k2 alone (a split session r31-kreg2b of s0 and k2 only).

- **L1** (k1): t10 `tri --width 256 --height 256 -n 6`, as r29-kreg and E396.
- **L2** (k2): t30 `probe --tri pixel --width 64 --height 64 --vertices 1500 F F F F F F`, F =
  `bins/p1139-green.bin` (pinned, data:render/closing-s1b/bins/p1139-green.bin, the green pixel
  shader of every DPM session): the triangle and 499 copies, each moved c/16 pixel, so 500 small
  triangles in one 64x64 render; the file given six times makes six renders a job, each on its
  own context, each printing `tri 64x64 #1: T us` (t30, resgx545 2cc9c5b). **Verified on the
  library mock of t30's source (42c4de7) before anything else was built**: every one of the 152
  t30 rows replays, none refused, and the hand run in debug/probe printed per file
  `probe p1139-green: tri 64x64 (1500 vertices), pixel replaced`, `tri 64x64 #1: N us` and
  `probe p1139-green: o0 mixed 0xff203040 x2961 0xff00ff00 x1135`. On the laptop the stock
  module completed 1500 vertices at 1024x768 and 2048x2048 in the default parameter buffer
  (E438, E839), so a 64x64 target overflows nothing [infer].

**The reading (frozen, both loads):** the MEDIAN of renders 2-6 (`us`; run/hooks.sh's
`job_us`, score.py's `reading`, tested alike). E1114 read the mean, which one slow render moved
by up to 4.8 percent; by the median every E1114 value lies within 0.82 percent and c11 reads
67271 us (+0.16 percent), in band.

**The control rule (frozen before the run, gen/gen.py and score/score.py):**

- c01-c16 write 0x2c before their job, like a value row. Each must draw (k1: no wrong pixel and
  `tri: 6 renders ok`; k2: six timed renders, no `failed:`, one `o0` line within the job and
  equal to s0's v1). A control that does not draw or has no reading FAILS the stage's controls:
  never an allowed outlier.
- Band: k1 within 1.0 percent of s0's r1-r8 median (REF1); k2 within BOUND2 of s0's v1-v8
  median (REF2), where BOUND2 = max(1.0, 3 x the interquartile range of v1-v8 in percent of
  REF2). BOUND2 above 2.5 percent (it would not resolve E141's 2.6 percent) makes k2 cannot tell.
- **Single-control outlier rule:** at most ONE control a stage outside its band is allowed: it is
  named (`OUTLIERS:` line) and left out of MED and of the spread; two or more outside fail the
  controls. So one slow job cannot void the stage, two can (tested: E1114 with c11 at its mean,
  +3.04 percent, holds 64 of 64 under this rule).
- Premise: the in-band controls' interquartile range at most 0.5 percent of MED (k1) or BOUND2 / 2
  (k2), else every value is cannot tell. c-end, an exact 64x64 triangle with no write, after the
  last row of each stage.

**Frozen prediction (H0, the negative; predictions/k1.tsv, k2.tsv):** for every value, not both
passes more than the bound (k1 1.0 percent, k2 BOUND2) from MED on the same side. Pass A (fit)
and pass B (held out) are each their own seeded shuffle (SEED 20261117 for k1, +1 for k2); a value
outside on its fit pass only is noise by the frozen rule. A value outside on both passes, same
side, is FAILED (a dependence). A k2 value drawing another image than v1's is cannot tell and
named on an `IMAGE` line (a finding of its own, not timing).

**The retire rule (frozen; `python3 score/score.py q024 out/ATT`), against the question text:**
Q024 asks whether the register changes timing. It RETIRES with the answer "no" when k1 and k2
both print their claim with **64 of 64 values decided and none FAILED** (each stage's controls
passed under the outlier rule, the spread premise held, BOUND2 at most 2.5 percent, c-end exact,
every value row drew): "CR_PDS_REG_0A78 at every value 0x00-0x3f leaves the render time within
1.0 percent (the 256x256 triangle) and within BOUND2 percent (500 small triangles at 64x64) of
0x2c's on two shuffled passes; E141's 2.6 and 5.5 percent were noise (E396, E1114)". A value
FAILED on both passes is a FINDING: Q024 stays open, narrowed to that value and load. One load
decided and the other not: NARROW (that load's clause closed). Neither: nothing changes.

**Stops:** rc 7 a kreg word the runner refuses (nothing runs); rc 19 0x0a78 not at 0x2c before
its write, not reading back its value (the job never runs), or not back at 0x2c after the job and
a reset; rc 4 any fault, hang or unexplained failure (no row takes `expectfault`); rc 24 the hook,
a wedge's symptom only: a t10 row without `tri: N renders ok` or with a wrong pixel, a t30 row
with a `failed:` line or not six timed renders, or a median above twice the stage's first timed
row of the same form. Every stage's rc 24 ends the session (`on_stop = "end"`); k1 and k2 are
each gated on their own s0 references. Any stop: report to the user, no retry, no reboot.

**Mock worlds** (mock/world.py): model (0: s0, k1, k2 0; 894 debugfs writes, 0x2c at the end);
nodiff (24: s0 24); slow (24: k1's third timed row three times slower); slowprobe (24: k2's third
row three times slower); probebad (4: a k2 render fails, the tool ends rc 3, the runner stops);
kregstuck (19: the write not taken, k1's first row stops before its job).

**Tests** (tests/test_session.py): tables as above; hooks and scorer read the same median; the
wedge and failure checks; flat records hold both loads and `q024` says RETIRE; one control out of
band allowed, two fail (each load); a drawing failure is never the allowed outlier; a value out
on both passes FAILS (`q024` FINDING), out on its fit pass only holds; the spread premise; k2
cannot tell when v1-v8 are too noisy (`q024` NARROW), its bound widens up to the cap; a k2 image
change is named; each gate needs its own load's references; E1114's own renders (pinned
data:render/closing-r29-kreg/fold/posthoc.txt) hold 64 of 64 under the frozen rule [post hoc: a
calibration of the rule on the run that motivated it, not evidence]; E141's two slow values on
both passes FAIL.

**Replay vectors:** none. A timing has no sgx-sim twin (SIM_UNMODELLED's timing entries).
Nothing firmware-derived; nothing for data-private.

**Pins:** data:pds/reg-0a78-timing/output.txt (E396), data:render/closing-s1b/bins/p1139-green.bin
(bins/), data:render/closing-r29-kreg/fold/posthoc.txt (E1114's renders).

Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top (verify reports a new file there).
