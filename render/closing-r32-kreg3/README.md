# r32-kreg3

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 bf0ba5618263, data 6b5c5112a06e.

**Q024** (pds, low; E045, E141, E396, E1114, E1124, E1125): "does CR_PDS_REG_0A78 change timing,
when two of its values were slower in one timing run?" E1124 closed the 256x256 clause (64 of 64
values within 1 percent on two passes). Left open: "whether a load of many small triangles, timed
to about a percent, shows a difference". E1125 could not tell: one 64x64 render of 500 small
triangles takes about 0.72 ms and its references spread 8.27 percent. This session is that last
clause. Kit word `kreg:0x0a78=V` in flagged stages only, values 0x00-0x3f, read back and restored
to 0x2c after every job, never on an expectfault row (the user's approval in round 29,
closing29/DECISIONS-R29.md). Records **E1128** (s0, the calibration) and **E1129** (the flagged
stage that runs), assigned by the lead.

**The load (user decision 2026-11-16, answer a):** the question's own, as asked: t30
`probe --tri pixel --width 64 --height 64 --vertices 1500 F ... F`, F =
`bins/p1139-green.bin` (pinned, data:render/closing-s1b/bins/p1139-green.bin), the triangle and
499 copies each moved c/16 pixel, so 500 small triangles in one 64x64 render. The program file
given N times makes N renders a job, each on its own context, each printing `tri 64x64 #1: T us`.
**Checked on t30's library mock first** (source 42c4de7, debug/probe/run.sh, not frozen): 20 and
40 files print 20 and 40 timing lines and 20 and 40 identical `o0` lines, rc 0, no `failed:`;
at 1024x768 10 and 40 files the same (`tri 1024x768 #1: N us`). t30 takes any number of files (one
`probe_tri_one` a file, cmd_probe's loop).

**What runs** (`python3 kit/session.py run .`, in order; tools t10 and t30, nothing built):

| stage | class | rows | jobs |
|---|---|---|---|
| s0 | safe, end | c0-tri; v<form>-1..8, six forms, 8 shuffled rounds; no write | 49 |
| k<form> (six) | flagged, end, gate: s0's pick | 128 values, c01-c16 (0x2c), c-end | 145 |

At most one k stage runs (the gates open only for the picked form), so 49 + 145 = 194 jobs, or 49
when no form qualifies.

**The candidate forms (frozen order, gen/gen.py FORMS):** 10, 20, 40 renders a job at 64x64 (the
question's load), then the same list at 1024x768 (l10, l20, l40; E438: 1500 vertices complete at
1024x768 in the default parameter buffer). At 1024x768 the copies are not small: the green covers
about a quarter of the target on t30's library mock, as at 64x64 [infer: the triangle scales with
the target], so a 1024x768 pick times 500 overlapping large triangles; the claim names the form.

**The calibration and the frozen PICK rule (s0; score.py `pick`):** a form's reference draws when
its job timed as many renders as the form has, printed no `failed:` line and one image (the
form's first reference's). A form qualifies when its eight references all draw and their spread,
the interquartile range of the eight readings in percent of their median (E1125's measure),
is **at most 0.8 percent**. PICK = the first qualifying form in the order above. No pick, or
c0-tri not exact: every k gate is shut, **the session stops before any flagged row** (the driver
ends 0 after s0; `q024` prints NOTHING, STOPPED). Tested: E1125's own references (8.27 percent,
pinned data:render/closing-r31-kreg2/fold/posthoc.txt) qualify no form.

**The reading (frozen, E1124's rule):** the MEDIAN of renders 2-N (run/hooks.sh's `job_us`,
score.py's `reading`, tested alike).

**The flagged stage (as r31-kreg2's k2, E1125, with the picked form):** every value 0x00-0x3f on
two passes, pass A (fit) and pass B (held out), each its own seeded shuffle (SEED 20261118 + 1,
the same for every form); a 0x2c control c01-c16 before every 8 value rows; c-end, an exact 64x64
triangle with no write.

- REF = the picked form's eight references' median; BOUND = max(1.0, 3 x their IQR percent),
  so at most 2.4 percent under the pick (CAP 2.5 kept as a control). Controls must draw the
  reference image; their band is BOUND around REF.
- **Single-control outlier rule (E1124's, kept):** at most ONE control outside its band is
  allowed, named (`OUTLIERS:`) and left out of MED and the spread; two or more fail the controls.
  A control that does not draw is never the allowed outlier.
- Premise: the in-band controls' IQR at most BOUND / 2 of MED (MED their median), else every
  value is cannot tell. A value row drawing another image is cannot tell and named (`IMAGE`).

**Frozen prediction (H0, the negative; predictions/k*.tsv):** for every value, not both passes
more than BOUND from MED on the same side. Outside on both passes, same side: FAILED. Outside on
its fit pass only: noise by the frozen rule.

**The retire rule (frozen; `python3 score/score.py q024 out/ATT`), against the question text:**
the question asks whether the register changes timing; E1124 answered no for the 256x256
triangle. Q024 **RETIRES only** when the picked form's k stage prints its claim with **64 of 64
values decided and none FAILED** (controls under the outlier rule, the spread premise, BOUND at
most 2.5, c-end exact): "CR_PDS_REG_0A78 at every value 0x00-0x3f leaves the render time of 500
triangles (1500 vertices) at WxH, N renders a job within BOUND percent of 0x2c's on two shuffled
passes"; with E1124 the answer is no, on both loads. A value FAILED on both passes is a FINDING
(Q024 stays open, narrowed to it). Anything else (no pick, the stage not run, fewer than 64
decided) is NOTHING: Q024 stays as it is, the readings go into E1128/E1129.

**Expectation, not frozen [infer]:** E1125's within-job spread (IQR median 6.05 percent over
renders 2-6) and drift (c01-c08 701.5 us, c09-c16 738.5 us) suggest the 64x64 forms will not reach
0.8 percent even at 40 renders (a job-to-job component that more renders do not shrink); a
1024x768 form, with renders tens of times longer, may. s0 measures it; nothing is chosen by hand.

**Stops:** rc 7 a kreg word the runner refuses (nothing runs); rc 19 0x0a78 not at 0x2c before its
write, not reading back its value (the job never runs), or not back at 0x2c after the job and a
reset; rc 4 any fault, hang or unexplained failure (no row takes `expectfault`); rc 24 the hook,
a wedge's symptom only: a t10 row without `tri: N renders ok` or with a wrong pixel, a t30 row
with a `failed:` line, a form other than 10, 20 or 40 renders or fewer timing lines than renders,
or a median above twice the stage's first timed row of the same form (`WxH/N`). s0 and every k
stage end the session on rc 24 (`on_stop = "end"`). Any stop: report to the user, no retry, no
reboot.

**Time (estimate about 30-45 minutes, under the 60 minute budget)** [infer: r31-kreg2's k2 ran 145
six-render jobs in about 13 minutes, 5.4 s a job, mostly the kit's fixed per-job work; each
further render a new context, assumed at most 0.15 s at 1024x768]: staging and preflight about 3
min; s0 49 jobs, 140 renders a round, about 6-8 min; the k stage 145 jobs, about 14 min (k10) to
22-28 min (kl40). No pick: about 12 minutes in all. Alarms: s0 2400 s, each k 3600 s; job_timeout
120 s.

**Mock worlds** (mock/world.py): model (0: s0, k10 0; 64x64 steady, pick 10); large (0: s0, kl10;
64x64 noisy, pick l10); noisy (0: s0 only, every gate shut); nodiff (24: s0); slowprobe (24: k10's
third row three times slower); probebad (4: a k10 render fails, the tool ends rc 3); kregstuck
(19: the write not taken, k10's first row stops before its job).

**Tests** (tests/test_session.py): tables and stages as above; hooks and scorer read the same
median at 10, 20, 40 renders and both targets; the wedge rule keeps one reference a form; the
pick is the first qualifying form in order (ten cases, 0.8 inclusive), a reference with another
image disqualifies its form, E1125's references qualify none; steady holds and `q024` RETIRES;
64x64 noisy falls back to l10; none qualifying shuts every gate (`q024` NOTHING, STOPPED); a k
stage without its pick cannot tell; one control out allowed, two fail; a drawing failure is never
the outlier; a value out on both passes FAILS (FINDING), E141's 5.5 and 2.6 percent FAIL, out on
its fit pass only holds; the spread premise; BOUND widens with the pick's spread; an image change
is named.

**Replay vectors:** none. A timing has no sgx-sim twin (SIM_UNMODELLED's timing entries).
Nothing firmware-derived; nothing for data-private.

**Pins:** data:render/closing-s1b/bins/p1139-green.bin (bins/),
data:render/closing-r31-kreg2/fold/posthoc.txt (E1125's references, replayed by the tests).

Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top (verify reports a new file there).
