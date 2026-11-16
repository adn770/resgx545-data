# r29-kreg

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 adca9929556b.

**Q024** (pds, low; E045, E141, E396): does CR_PDS_REG_0A78 change a render's time? Design:
`closing29/kreg/design.md` (the kit word `kreg:OFF=V`, resgx545 main adca992). User-approved in
round 29 (relayed by the lead): the kit rule lifted for kreg to 0x0a78 in flagged stages, this
session as the design proposes. Records from E1114.

**What runs** (`python3 kit/session.py run .`, in order; tool t10 only, nothing built):

| stage | class | rows | jobs |
|---|---|---|---|
| s0 | safe, `on_stop = "end"` | c0-tri (64x64 exact), r1-r8 (256x256, six renders, no write) | 9 |
| k1 | flagged, gated on s0, `on_stop = "end"` | 128 value rows, c01-c16 (0x2c), c-end | 145 |

154 jobs; at about 25 s a job (reset wait, snaps, keeps) about 65 minutes [infer]. k1's value
rows: every value 0x00-0x3f once in pass A (`aVV`, fit) and once in pass B (`bVV`, held out),
each pass its own shuffle of gen/gen.py SEED; a `kreg:0x0a78=0x2c` control before every 8 value
rows. `#limit 0` everywhere: no planned fault or hang.

**k2 dropped (a deviation from the design):** Q024's second load, "a render with many small
triangles", has no timed form in t10 (or main's sgxfive-test): `probe --tri --vertices N` draws
copies but prints no job time, and `tri` takes no triangle count. So Q024 can only narrow on
that clause; a later round needs a tool change (a timed `probe --tri`, or `tri --vertices`).

**Reading:** a row's `us` is the mean of renders 2-6 (`tri 256x256 #i: T us`; E141, E396), its
`diff` the wrong pixels of all renders summed (run/hooks.sh and score/score.py alike).

**Frozen predictions** (`predictions/k1.tsv`, gen/gen.py, score/score.py):

- H0 (the negative): no value lies more than 1.0 percent from MED, the median of c01-c16, on
  both passes on the same side. Pass A is the fit; pass B, held out, must repeat a deviation for
  it to count. A value outside on its fit pass only is noise by the frozen rule.
- Controls that can fail: c0-tri, c-end and every row draw exactly; each 0x2c control within
  1.0 percent of s0's r1-r8 median (the write path does not move the time); the premise: the
  controls' interquartile range at most 0.5 percent of MED, else every value is "cannot tell"
  (too noisy to read 1 percent; no retirement).
- What the result does: H0 held on 64 of 64 with the controls passing narrows Q024 to its
  many-small-triangles clause (k2 dropped), the 256x256 clause closed for every value; a value
  FAILED on both passes is a finding (Q024 stays open, narrowed to that value); cannot tell
  leaves Q024 as it is.
- Tested on kept records built from E396's own renders (holds, 64 of 64) and E141's 0x01 and
  0x20 means on both passes (fails both): tests/test_session.py.

**Stops:** rc 7 a kreg word the runner refuses (nothing runs); rc 19 0x0a78 not at 0x2c before
its write, or not reading back its value (the job never runs), or not back at 0x2c after the
job and a reset; rc 4 any fault or hang (kreg rows take no `expectfault`); rc 24 the hook: a row
without `tri: N renders ok`, with any wrong pixel, or a render mean above twice the stage's first
timed row (a wedge's symptom); s0's and k1's rc 24 end the session; the gate keeps k1 from
running unless s0's controls passed. Any stop: report to the user, no retry, no reboot.

**Mock worlds** (mock/world.py): model (0: s0 0, k1 0; 289 kreg writes, 0x2c at the end),
nodiff (24: s0 24), slow (24: k1's third timed job three times slower), kregstuck (19: the write
not taken, k1's first row stops before its job).

**Replay vectors:** none. A timing has no sgx-sim twin (the sim keeps no clock; SIM_UNMODELLED's
timing entries): `refused`, with that reason. The images are E045's 64x64 baseline (`diff 0`).

**Pins:** `data:pds/reg-0a78-timing/output.txt` (E396's renders, which the tests replay). No
firmware-derived file; nothing for data-private.

Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top (verify reports a new file there).
