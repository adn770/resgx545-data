# r35-pk (round 35: Q302, channel rounding over the pack modes)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 eea6d2ab8f45 (kit/ is that commit's blobs) and
resgx545-data 1f5ebe6b6e9d. Plan: `closing29/plan/rank-round35.md` section 3.3, R35-1 (a), R35-4
(a) (Q302 narrows only: mode 14 stays on the flagged list). **SAFE** class: no planned fault, no
hang, no knob, no kreg, no register write, `#limit 0` everywhere; pack mode 14 never runs, nor 22,
26, 34 (Q012). Record **E1146** (only that number). Laptop prefix `r35p`. Module
7CE8E38EDB97FC5EA4F6C90 (the lead boots it before running); travel cable (`host_key_alias =
"cedar"`). Built offline, not staged, not run.

## Tool (none is built)

- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), source resgx545 a581c06 (sha256 23e1fa76...),
  recipe `data:render/closing-r10-st1/lead/build_tool10.sh`: every row and the health pair, as
  r34-q044 (E1135). Word 11 is `pixelbe`, the word that loads CR_REG_0400.

## Programs

- colour: E031's kept program (o0 = 0x80ff8040 over 0xff203040), `bins/colour.bin`, for the
  layout controls only.
- ramp: our own `src/ramp_xy.s`, assembled by resgx545's `tools/usse-asm/usse-asm` into
  `bins/ramp_xy.bin` (29 instructions: two `fmad` of pa0, pa1 with 1.0 and 2^22, shifts, ands,
  xors). With E385's `pds_iter_xy` (pa0 = x + 0.5, pa1 = y + 0.5: E382's kept xy image, every
  one of the 1062 triangle pixels) it stores o0 = XOR of X << {0, 8, 16, 20, 25} and Y << {4,
  11, 19, 22, 29}: every triangle colour unique, every byte lane all 256 values (2 to 6 pixels
  each), so each channel takes every byte and each stored dword names its pixel. sgx-sim runs it
  to the same words (tests/test_gen.py). It replaces the plan's `b = x + 64 (y & 3)` ramp, which
  cannot reach every byte on a triangle of columns 8 to 54 (deviation 1).

## What runs: 92 jobs, about 20 minutes (30 at most)

| # | stage | jobs | what | gate |
|---|---|---|---|---|
| 1 | s0 | 9 | controls: ramp mode 0 (H-RAMP, its image by construction), ramp mode 4 (E1136's split at 0x80: 127 clear, 128 set), E031's colour images of modes 3, 4, 5, 6, 7, 9, 10 | none; a stop ends the session |
| 2 | r1 | 15 | mode 0 reference, then modes 3, 4, 5, 6, 9, 10, 11 at 0x80, twice (the second reversed) | s0 |
| 3 | r2 | 41 | mode 0 reference, the 40 ARGB8888-like modes other than 0 at 0x80 | s0 |
| 4 | r3 | 20 | mode 0 reference, modes 4, 5, 6 references at 0x80, then modes 0, 4, 5, 6 at 0x02000040 and 0x020000c0, twice (the second reversed) | s0 |
| 5 | pw | 7 | mode 0 reference, E031's colour images of modes 12, 13, then the ramp in 12, 13, 13, 12 (they write past the target into the tool's 64 KiB scratch, E031) | s0 |

Every row reads all 4096 dwords; modes 12 and 13 also print every scratch dword changed. At
about 13 s a job with the kit's reset, snapshots and health: about 20 minutes.

## Hypotheses (frozen in predictions/, gen/pk.py)

Expected values come from THIS session's own references: every stage starts with the ramp in mode
0 at 0x80 (a control frozen to the ramp's image by construction), and each model's image of a row
is computed by the scorer from that row's stage reference (D1, D3 of the plan).

- Clause (d) and (a), modes 3 (RGB565), 4 (ARGB1555, alpha by E1136's threshold), 5 (ARGB4444),
  6 (A8 RGB332), `match` per mode: **H-RZ** (truncate, v >> (8 - w)), **H-RN** (round half up,
  saturated), **H-RNE** (half to even), **H-SCALE** (round(v (2^w - 1) / 255)). Fit: E385's mode 5
  alpha (4 bits over 47 alphas: H-RZ on 4096 of 4096 pixels, the other three fail) and E031's
  mode 6 green 0x30 (H-RZ and H-SCALE; H-RN and H-RNE fail). Held out: every r1 row. Prediction:
  H-RZ [infer from the fit].
- ARGB8888-like modes and 11, `match`: **H-AS0** (the stage reference dword for dword) against
  **H-AS0-PART**.
- Modes 9, 10, 12, 13, `whole`: **H-WHOLE** (every dword written, and every scratch dword, is one
  of the reference's values) against **H-NARROW**. The layout (which pixel each dword holds,
  the stride past the target) is a reading, no frozen form.
- Clause (e), r3, `rel`: **H-1136** (bit 25 inverts the mode's alpha field, E1135/E268: 0xff000000
  mode 0, 0x80008000 mode 4, 0xf000f000 mode 5, 0xff00ff00 mode 6; the low byte sets mode 4's
  alpha where alpha >= it, E1136, and nothing elsewhere) against **H-LOWDEP**.
- Controls: **H-RAMP** (every stage's mode 0 reference), **H-E031** (E031's kept images),
  **H-E1136** (s0's ramp mode 4 split "127,128").

D1: a row whose decoder form's control did not PASS (the ramp control s0-m00-ref for every ramp
row; s0-mMM-col for modes 3 to 6, 9, 10; s0-m04-ramp for 4; pw-m12-col, pw-m13-col) is "cannot
tell: form control". D2: tests/test_score.py prints every frozen name held in one world and
FAILED in another (the mock worlds model, rn, rne, scale, alt, s0diff and a test-only ctlfail).

## Narrow rule (frozen; `python3 score/score.py narrow out/ATT`)

Always NARROW (R35-4 (a)): Q302 stays open on (b) what 9 to 13 write past the target (readings
only) and (c) mode 14. Printed per clause: (d) decided when exactly one of the four rules holds
on every dword of both mode 3 rows (that clause then goes into Q302's body as answered); (a) per
mode 4, 5, 6 the same, the ARGB8888-like class when H-AS0 holds on all 42 rows, modes 9, 10, 12, 13
when H-WHOLE or H-NARROW holds on both rows; (e) when H-1136 (or H-LOWDEP) holds on every row of
modes 0, 4, 5, 6. Any FAILED control or a stage not run is printed as a reason.

## Stops (mock worlds, mock/world.py)

Any fault or hang stops its stage (`#limit 0`); a control without its pixel rows (25) and, in s0,
any stop ends the session; the second output without its 64 pixel rows stops a stage (24).
Worlds: model, rn, rne, scale, alt (0), s0diff (s0 control FAILED: later stages skipped),
s0nopix (25), r1nopix (r1 24, the rest run), pwfault (4), r2hang (6).

## Deviations from the plan

1. The ramp is the XOR form above, not `b = x + 64 (y & 3)` with A = b xor 0x5a, G = 255 - b,
   B = 37 b: the triangle covers columns 8 to 54 only, so the plan's form reaches 188 bytes.
2. s0 adds E031's colour images of modes 5, 6, 9 and 10 (a known value for every decoder form),
   and pw adds 12 and 13's; r3 adds mode 0 at the two words and runs its mode references once.
3. 92 jobs, not ~110: r2 one replicate as planned; no row outside the line's modes.
4. Modes 12 and 13 run last in their own stage (r34-q044's pw), not in r1.

## Replay vectors

The fold builds `sgx545-tables` from r1, r2, r3 and pw's kept rows (`closing_tables.py`): replay
in sgx-pipe's PBE (`pbe.rs`) for the modes and words it then models, a new
`crates/sgx-pipe/tests/closing_r35_pk.rs` alongside `closing_r34_q044.rs`; modes 12 and 13's
scratch is `refused` (no frozen layout). Pinned: every kept image the generator reads.

Nothing here is firmware-derived: no file goes to data-private.

Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top (verify reports a new file there).
