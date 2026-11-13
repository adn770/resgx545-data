# r9-k1: Q190's layered background (and Q066's explore rows)

Round 9, session K1 (plan `closing9/k1/exp-k1-r9.md`, decisions K-1..K-6 all (a),
`closing9/DECISIONS-R9.md`). Built on the session kit from resgx545 d95a264 (the kit as f32dfac's,
with t9's source merged), data 2d666bfaf. Module B60AB0B475DD1E8972419B5 (fork 2a650d74:
debugfs `render_bg_layer`, `render_bg_src`, bg pokes to word 22 with the layer). Laptop prefix
`r9k`, records E970-E974. Safe class: no planned fault, `#limit 0` in every table.

## Tools

- t9 `~/sgxfive-test-t9`: sgxfive-test with `--bg-layer` and `--mock-knob`, resgx545 97447b04
  (source sha256 5de42943...), built on the build host by `lead/build_tool9.sh` (the tool
  builder's recipe), binary sha256 7a28be39... The lead stages it to `~/sgxfive-test-t9` before
  the run; the session never ships its bytes. Its FROZEN.commits `built` line binds it:
  `7a28be3952fb310170e861da0622d890a2e215cb761d6f21bc9321223e1b40ce  built
  97447b04b38cadac7733f0cd12503e2ef207a3bf  userspace/libsgxfive/tools/sgxfive-test.c
  5de429431a93ddbdcd9c20141f5c286dcc5cc72265f95d662279e09b655a3f50
  data:render/closing-r9-k1/lead/build_tool9.sh`.
- t4 `~/sgxfive-test-rgn4`: the health fill and triangle only (layerless; the knobs are restored
  before it runs).

The kit owns both knobs as row words (`dbg:render_bg_layer=Y dbg:render_bg_src=0x3e800000`):
written before the job, read back, restored after it and by the exit trap. render_bg_layer is a
debugfs bool, so the rows write `Y` and `N` (a `1` reads back `Y` and would stop the runner,
rc 19). The tool only reads them and refuses a mismatch (rc 2, before any device call).

## What runs (7 stages, 100 rows, 94 on the H-ITER path)

| stage | rows | gate | what |
| --- | --- | --- | --- |
| s0t | 3 controls | none | c-off (layerless, E590's hash), c-tex (H-BUILT: rd:18 layers 1, object words 3-10; H-TEX: 3034 identity texels), c-noop (bg:5 at its own 1.0) |
| s0p | 4 controls | s0t c-off, c-tex:built | POS without and with the layer (E442's primary, f32(x + 0.5)), L-RAW u (pa0) and v (pa1) |
| s1n | 6 fit | H-NONE at c-rawu and c-rawv | bg:3..8 = 0.5 (the H-NONE confirmation; skipped on H-ITER) |
| s1 | 14 fit, 30 held-out | every s0t and s0p control | words 3-8 poked (1-3 words, k/8 values, seed `r9-k1`), read through texels |
| s2 | 20 held-out | s1: H-VM right on >= 28 of 30, each rival wrong on >= 3 | words 15-22: a 16 px move and a bit flip each, four two-word moves (H-VBOX vs H-VPLANE) |
| s3 | 21 explore | as s2 | words 9-14 and the format word 10 (eight values), bgobj_words[1] (cmd:24) at 0, 1, 4 rows; every 0xffffffff last |
| s4 | 2 controls | s0t c-off, c-tex:built; s0p c-pos | c-tex2, c-off2 |

Expected time: 94 jobs at 5-10 s with health, 10-16 min of runs, about 25 min with staging and
verify. Stops: any hang or fault (rc 4); a tri row without `job: ok`, a probe row without its 64
pixel rows, a layered row without the tool's `bg-layer:` line, and c-rawv with pa1 not a function
of y (more than 4 values in one background row), each rc 24 (hooks.sh); a control without its
reading, rc 25. A closed gate skips its stage (the driver goes on).

## Deviations from the plan (the kit forced them)

1. The kit's guard forbids `--kpoke` in every row, and probe's kernel poke is `--kpoke`; only
   tri's `--kpoke-render` is allowed. So every poked row reads the layer through texels (L-TEX:
   `tri --bg-layer --kpoke-render 1:bg:N=V`), and L-RAW (exact u and v) is read in the two unpoked
   controls only. An L-TEX row reads u and v at once (texel = floor(64 u), floor(64 v)), so the
   plan's U/V row pairs became one row each and the freed rows are more fit and held-out pokes
   (s1 14 + 30, s2 20, s3 21 as planned). Precision: a texel is 1/64 where L-RAW was 2^-12; a
   pixel within 1/64 texel of a texel edge, or out of [0, 1), is not predicted.
2. A stage's REQUIRED files are per row, so s0 is two stages: s0t (tri controls, with dumps and
   words) and s0p (probe controls). The H-NONE confirmation is its own stage s1n.
3. Every tri row has `--keep-going`: without it a render that differs from the tool's reference
   breaks before `--dump-render`, and the poke's read-back dump would be missing (rc 23).

## Predictions and the model

The frozen model is gen/bgl_model.py (standard library): attribute = the plane through the
three vertex values at the pixel centre (x + 0.5, y + 0.5), texel nearest. Models: H-VM (vertex
major at the render box), H-VPLANE (at the vertices words 15-22 give, E590's decoding), H-LM,
H-SWAP, H-NOREAD, H-NONE, H-17, H-NOTEX. `predictions/STAGE.tsv` freezes each texel map as
`sha256:HEX/N`; the scorer recomputes every map and stops (no SUMMARY) if one is not the frozen.
A texel-map verdict is right at <= 1 % of the predicted pixels wrong, wrong above 10 %, at least
256 predicted. Scored pixels: the hardware's 3034 background pixels (`gen/bgmask.txt`, from
E590's kept control; E437's 1062 triangle pixels), not the library mock's 2998.

## Mock worlds

model (every gate but s1n's opens), none (only s1n and s4 after s0), noread (s1 runs, s2 and s3
shut), hang (c-pos hangs: rc 4), stale (a knob left on: c-off refused, rc 4), eexist (the source
overlaps the render's pages: `render context: File exists`, rc 4), rawvbad (c-rawv stops s0p,
rc 24), noline (c-tex without its layer summary: rc 25), mockgeom (the library mock's geometry:
s0t's controls fail, every gate shuts). The library-mock replay passes every row's knob words as
`--mock-knob`; tests/test_twin.py shows a row without them is refused.

## Replay vectors

Every stage's measured rows become a `texture` table (`tools/usse-asm/closing_tables.py`, format
`sgx545-tables`: the `--pixels` words of each job, tri's and probe's) under
`vectors/closing/r9-k1/`. Replay: `refused` for now: sgx-pipe models a one-layer background
object only for a transfer copy (`crates/sgx-pipe/src/xfer.rs`, pinned), not for a render. If s1
and s2 hold, the fold names a render-layer replay test and passes `--replayed`. The freeze pins
closing_tables.py, closing_vectors.py, pbdump.py and xfer.rs.

## Commands

Every command is run through its interpreter, never by its mode bits.

- Offline: `bash tests/run_all.sh` (asm build, guard, own tests, mock of every world, verify).
- Generator: `python3 gen/make.py` (writes tables, predictions, bins, gen/bgmask.txt), `--check`.
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.

No file of this session derives from firmware: nothing goes to data-private.
