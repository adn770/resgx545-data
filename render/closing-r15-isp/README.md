# r15-isp (round 15, session r15-isp: Q241, stage zcut)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 158bdc5455b2 and resgx545-data cddc7b60b8ed. Plan:
`closing15/plan/rank-round15.md` sections 2 and 3, row zcut (decisions R15-1 to R15-9 (a) of
`closing15/DECISIONS-R15.md`: safe class only, no tool change, one stage). Predecessor:
`closing14/r14-isp` and its fold (E1045, stage wind). Safe class only: no held reset, no planned
fault, `#limit 0` in the table. Built offline; nothing here touched the laptop, cachix or a git
repository. Record E1056 is reserved for its fold (the builder folds it; notes in
fold/FOLD-NOTES.md).

## What runs, in order: 11 jobs, about 4 minutes

Laptop: module srcversion B60AB0B475DD1E8972419B5 (fork 2a650d74, the test boot); one tool, t10
`~/sgxfive-test-t10` (sha256 9bedc2d6..., built from resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` sha256 23e1fa76... by resgx545-data
`render/closing-r10-st1/lead/build_tool10.sh`, `TOOLSRC.sha256`), so the kit's library mock
replays every row (11 rows, none refused); files under `~/scratch/r15i/`; no extra laptop file.
One stage, `zcut` (alarm 900 s, `on_stop = "end"`: it is the only stage, its stop ends the session).

| # | rows | jobs | what | label |
|---|---|---|---|---|
| 1 | zcut-ctl-zhi, zcut-ctl-zlo | 2 | E1045's wind-zhi and wind-zlo replicated (E977's ramp setting, 80 x 40, compare always with the depth written, `--pixels`) | controls |
| 2 | zcut-ctl-b15 | 1 | E065's job `blk:1^=0x8000` on the library's 64 x 64 triangle (48 pixels, hash 0x7e7562918f5b5125) | control |
| 3 | zcut-hi1 to hi3 | 3 | a triangle with one vertex depth 1.25: the plane crosses 1 inside the target | held out |
| 4 | zcut-lo1 to lo3 | 3 | the same with one vertex depth -0.25: the plane crosses 0 | held out |
| 5 | zcut-b16, zcut-b17 | 2 | E065's `blk:1^=0x10000` and `^=0x20000` on the library triangle, `--pixels` | held out |

Time: every job a 64 x 64 or 80 x 40 render, tens of milliseconds, about 6 s with the reset,
health fill and triangle (E1045's 8 jobs ran in under 2 minutes); with staging, the preflight and
the copy back about 4 minutes. `min_free_mb` 300; `job_timeout` 120 s.

**Stops.** No fault is planned: any fault, hang or unexplained failure stops the stage (rc 4) and
the session. A control without its reading stops the session (rc 25, premise). A row that read ok
without `job: ok`, or without its whole image (H rows of W values; 64 x 64 for E065's rows), stops
the stage (hook_check, rc 24) and, being the only stage, the session. A file the scorer reads that
was not kept stops it (rc 23). The stop budget is the whole session: 11 jobs, none expected to
stop. A control that FAILS does not stop the run (the scorer prints no headline for the models it
gates). No row reaches a range never run before: the depths are E1045's kinds (past [0, 1], compare
always, writes), the vertices lie inside H-VP's guard (E1023's quarter), E065's pokes are its own.

## Hypotheses, controls, verdicts (frozen in predictions/, scored by score/score.py)

- **The cut (Q241; E1045, E287, E606, E1037).** E1045's form: 80 x 40, CR_ISP_ZLSCTL 0x00171014
  (float, pitch G 2), the buffer pre-filled 0xdeadbeef and dumped, ISP word 0 0x01c00200 (compare
  always, depth written) by `--poke blk:1`, every row also `--pixels`; the triangles' vertices as
  `--tri-v` integers in 1/256 px. Three frozen forms (gen/zcut.py), each an image of the target and
  the dwords of the 96 x 48 store band (E465's layout, E730):
  - H-PIXCUT: the plane is drawn unchanged (E606's coverage of the triangle) and a pixel is removed
    iff its depth at the centre lies past [0, 1]; undetermined ('?') within 2^-18 of 0 or 1.
  - H-POLYCLIP: the MTE clips the polygon at z = 1 (or 0; E287), each made vertex the exact
    intersection rounded half away from zero to 1/256 px (E1037's CLIP-HA), coverage by E606's rule.
  - H-POLYCLIP-NR: the same with the made vertices unrounded.
  - Rows: three triangles with the apex at 1.25 (cut at 1) and three at -0.25 (cut at 0), found by
    a seeded search (README "Layout"): the cut line passes within 1/512 px of 8 to 10 pixel
    centres (lattice lines of slope 1/4 to 2/3), the made vertices land up to 1/2 unit off
    the 1/256 grid so the rounding moves the polygon's edge by up to 0.7 unit onto the lattice
    centres: H-POLYCLIP parts from the other two on 8 to 11 target pixels a row (all determined)
    and on 8 to 11 background dwords, with no pixel undetermined; the depth margin of every pixel
    is at least 2.4e-5 (H-PIXCUT's undetermined band is 3.8e-6). H-PIXCUT and H-POLYCLIP-NR are
    one image on every row (they part only on an exact tie, which H-PIXCUT leaves undetermined):
    no row can part them (Deviations 2).
  - Verdict per row: every target pixel the form claims is as drawn and the count of 0x3f800000 in
    the `depth #1:` line lies in the form's range. The dump is kept; the fold checks its 4608 band
    dwords against `predictions/zcut/NAME.MODEL.txt` (the drawn dwords within 2^-10 of the plane,
    the rest 1.0; the engine reproduces E1045's two dumps in all 4608 dwords, tests).
  - Controls that can fail: zcut-ctl-zhi and zcut-ctl-zlo (E1045's wind-zhi and wind-zlo: drawn
    1600, their hashes 0x1ae0dc9078287f25 and 0xead5832ba1f27f25 and their `depth #1:` lines),
    gating the three forms.
- **E065's flips (Q241; E065, E998, E1045).** The library's 64 x 64 triangle (1062 pixels, hash
  0x99385a04ee01c585) with ISP word 0 flipped as E065 did (`--poke 'blk:1^=0x...'`):
  - zcut-ctl-b15: bit 15 leaves 48 triangle pixels (E065, hash 0x7e7562918f5b5125): the control
    (gates H-EQUIV and H-NONE; the job found in
    `isp/pass-counters/tri-isp-timeline/raw.txt`, case `blk:1^=0x8000`).
  - zcut-b16, zcut-b17: bit 16 or 17 alone. Frozen H-EQUIV (the pixels bit 15 leaves: drawn 48,
    hash 0x7e75...) against H-NONE (no pixel: drawn 0, hash 0xfc5ff15e0434a325, E065's two jobs).
    The READING lines say whether each row's pixel set is the control's.

**Predicted outcomes.** Controls PASS 3 of 3. Cut rows: H-POLYCLIP held 6 of 6 and H-PIXCUT and
H-POLYCLIP-NR FAILED 6 of 6 [infer: E1037 found the clip vertex rounded half away from zero on the
guard clip, E287 put the depth clip in the MTE; the same clipper and its rounding]. E065: H-NONE
held 2 of 2 and H-EQUIV FAILED 2 of 2 [infer: E065's flips of bits 16 and 17 left no pixel; these
rows are its replicates with the pixels printed]. Every job `job: ok` [infer]. Q241 narrows only:
bit 18, the visibility counter, the offset's units, pass types and the gate pairs stay open.

## The mock's worlds (mock/world.py, kit/session.py mock)

model (zcut 0), nopix (no pixel rows: hook_check stops zcut at its first row, 24, the session ends),
nodepth (no `depth #1` line: zcut-ctl-zhi has no depth_changed reading, premise 25), nohash (no
`target:` line: zcut-ctl-b15 reads no hash, premise 25), rejected (`job: rejected` with a diff
line, E934: 4), cutfault (a depth row past [0, 1] other than E1045's two faults: zcut-hi1, 4), lost
(`job: lost` at zcut-hi1: 24), short (a 64 x 64 row prints 4095 values: 24 at zcut-ctl-b15). The
fake answers from the argv only. Before the worlds, every row goes through the library mock built
from t10's bound source (a581c06: 11 rows): none is refused. Scorer tokens (tests/test_score.py):
pixcut, nr, equiv, old.

## Replay vectors

The fold builds one `sgx545-tables` table (`closing_tables.py` format) from the kept files alone
(pinned: `tools/usse-asm/closing_tables.py`, `crates/sgx-pipe/src/mte.rs`, `isp.rs`, `zls.rs` at
158bdc5):

- zcut → `zcut` (per row the vertices in 1/256 px, the three depths, ISP word 0, the drawn image of
  the target, the count of background dwords; E065's rows the poked word, drawn and hash): replay
  sgx-pipe `mte` (the z clip, `cut_triangle`, today refused under Q230 and Q241 for a cut triangle)
  and `isp` (coverage of the clipped polygon) extended with the clip vertex's rounding once the fold
  models what held; `refused` under Q241 for what does not hold.

## Layout

- gen/make.py writes `tables/zcut.txt`, `predictions/zcut.tsv` and `predictions/zcut/NAME.MODEL.txt`
  (the drawn bitmap, `?` for an undetermined pixel, then one line per dword of the band) from
  gen/zcut.py (new: the engine, the rows, the frozen forms) over the byte copies gen/guard.py
  (r14-isp's clip and coverage) and gen/q261_rule2.py (c6's engine), read at the pinned data commit
  (gen/pins.py; tests/test_gen.py checks every copy). Standard library only.
- The rows were found by a seeded search (the construction is the header of gen/zcut.py) in
  debug/design.py, debug/pick.py and debug/pick2.py (scratch, not frozen); tests/test_gen.py
  re-checks every property on the literal rows.
- score/score.py, run/hooks.sh (readings job, drawn, pixels, hash, diff, depth_changed; checks job
  ok and the whole image), mock/world.py, `tests/` (`test_gen.py`, `test_twin.py`, `test_score.py`,
  `kept.py`), PREFLIGHT.md, TOOLSRC.sha256; fold/FOLD-NOTES.md (fold/ is outside the freeze).
  debug/ is scratch.

Publishable: everything (our own models and kept records' readings; no firmware-derived file).
**Nothing is marked for data-private.**

## Deviations from the plan

1. **One kit stage, but the scorer reads no dump.** The kit's REQUIRED names one set of per-row
   files for a stage, and E065's three rows (the library triangle, no `--depth`) have no dump;
   adding `--depth` would change the job E065 ran. The scorer therefore decides on the target image
   and the count of background dwords in the `depth #1:` line (a bracket per form: the dwords it
   says are 1.0 up to those plus the pixels it does not claim); the dumps of the eight depth rows
   are kept (`--depth-dump`) and the fold checks them against the frozen per-dword files.
2. **H-PIXCUT and H-POLYCLIP-NR cannot be parted by a row.** Both are the exact cut: one image
   except on a pixel whose centre lies exactly on the line, where the hardware's float plane may
   land either way, so H-PIXCUT leaves it undetermined and no row is built on ties. The three forms
   part as H-POLYCLIP against the pair (what the plan's "the three forms part on those pixels"
   can mean offline); a held pair names the exact cut, H-POLYCLIP the rounded one. [A tie row
   with a determinate H-PIXCUT would freeze float iteration to the exact tie: not frozen.]
3. **E065's bits 16 and 17 rows are the xor of E065's own flips** (`blk:1^=V`, the form of its
   sweep), so they are replicates of its two jobs (0 triangle pixels each) with `--pixels` added;
   the prediction is H-NONE (E065 measured it), H-EQUIV stays the frozen rival the plan names. The
   tool of E065 was an older build (sha256 f95b9f...), the library triangle's baseline hash
   0x99385a04ee01c585 is the same one t10's health triangle prints in r14-isp's kept files.
4. **The cut rows' vertices are found, not hand-set** (a seeded search, then fixed as literals):
   the apex vertex, two on the far side, every crossing on a pixel-centre lattice line within 1/2
   unit; two of the six are in the reversed order (the clip does not depend on it).

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest; numpy unused here), which
  the offline tests use unless `PY` names another.
- Generator: `python3 gen/make.py` (`--check`: current or not; about 1 s).
- Offline: `bash tests/run_all.sh` (the guard, own tests, the library mock and the mock of every
  world, the verify once frozen).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).
