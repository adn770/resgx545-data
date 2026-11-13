# r9-z2

Round 9's stage z2 as its own kit session (ranking plan R9c-F / X-3, Q101, decision R9-3 (a);
record E981), scaffolded by `tools/closing/new_session.py` from resgx545 02ae0a0ec5e6, data
2d666bfafa21. Laptop prefix `r9z`, module B60AB0B475DD1E8972419B5, tool t9 = `~/sgxfive-test-t9`
(sha256 7a28be39..., built from resgx545 97447b04 `userspace/libsgxfive/tools/sgxfive-test.c`,
sha256 5de42943..., by `lead/build_tool9.sh`, copied byte for byte from closing9/k1build; its
rows replay on that source's library mock in the kit). No knob, no kernel change, safe class.

## What runs (10 jobs, about 1 minute of jobs, 10 to 15 with staging and health)

One stage, z2, at 256 x 128 (G 7), E466's store control: two depth ramps, a (-0.25 to +0.25)
and b (-0.75 to -0.25), each in format 0 (the reference and the control: every dword of the 64
tiles stored, E831, frozen 32768) and in formats 1 and 2 without and with bit 19 (8 rows). Frozen
per dword from each ramp's format-0 reference: H-ABS, H-CLAMP, H-WRAP, H-B19 (gen/z2.py; all four
are E466/E490's rule over z >= 0). Stops: any fault or hang (4); a control without its reading
(premise, 25); a tri row without `job: ok` (24); free space under 300 MiB (22).

## Deviation from the plan: how the depth is made negative

The plan's rows put `--tri-z` outside [0, 1] (the reason for t9). That does not reach the store
negative: the tool's clip z is 2t - 1 and the MTE clips at clip z = -w (E287: a flat triangle at
-1.01 is removed, a sloped one cut where its z passes -1). The rows keep `--tri-z 0,1,0` and set
the viewport's z offset (state-block word 10, `--poke blk:10`; 3d.md, E797) to +0.25 or -0.25,
which comes after the clip and is not clipped (E287: offsets -0.5 to 1.5 draw whole). A negative
depth compares as 0 (E287 [infer]), so depth less against the clear 1.0 draws every pixel. t9's
wider `--tri-z` is not exercised; t9 is used as bound (its other changes do not touch `tri
--depth`). The plan's two E490 1024 x 768 controls are replaced by the two format-0 references at
256 x 128 (the same rule, E831, can fail). If the reference stores negative depths as 0, the
rivals collapse onto that: a reading the fold states.

## Replay vectors

`zls-negative-depth` (closing_tables.py, `sgx545-tables`: dword, format-0 float, kept 24/16-bit,
bit 19): replay sgx-pipe `zls::encode_depth`, which refuses bit 19 below the ramp today (Q101); the
fold widens it test first with the held model. The freeze pins `crates/sgx-pipe/src/zls.rs`.

## Commands

- Python: `$HOME/src/resgx545/.venv/bin/python` (tests use it unless `PY` names another).
- Generator: `python3 gen/make.py` (`--check`).
- Offline: `bash tests/run_all.sh`; freeze `python3 kit/session.py freeze .`, then again
  `bash tests/run_all.sh`.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py z2 KEPT_DIR`.

Mock worlds: model (0), nodepth (25), rejected (4), negfault (4). Nothing is firmware-derived.
