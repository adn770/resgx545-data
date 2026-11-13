# r10-st1

Round 10's stage st1 as its own kit session (seeds plan `closing10/seeds/exp-seeds-r10.md`
section 5 "Stage st1", decisions R10-4 (a) and R10-6 (a); with the ranking plan's R10-4 Q071
stencil rows, `closing10/rank/rank-round10.md` R10-D; records E988 (Q121) and E989 (Q071's stencil
clause)), scaffolded by `tools/closing/new_session.py` from resgx545 287031c64102, data
1324301bef13. Laptop prefix `r10s`, module B60AB0B475DD1E8972419B5. Tool t10 =
`~/sgxfive-test-t10` (sha256 9bedc2d6..., already on the laptop), built from resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., `TOOLSRC.sha256`) by
`lead/build_tool10.sh`, a byte copy of `closing10/k10/build_tool10.sh` whose last line prints a
recipe path of `closing-r10-zls`: the copy is kept byte for byte, and session.toml binds the recipe
as `data:render/closing-r10-st1/lead/build_tool10.sh` (the lead's `built` line). No knob, no
kernel change, no boot, safe class only: no `expectfault` row, `#limit 0`.

## What runs (18 jobs, about 2 minutes of jobs, 10 with staging)

One stage, st1, every row `tri --tri-full --depth --stencil --stencil-store --pixels` with E978's
control 0x0017300e (the stencil loaded, depth and stencil stored, G 1) and, but for one control,
`--isp2 V`: ISP word 2 in the state block and ISP word 0 0x01d00300 (reference 0, depth always;
render.c, pinned). V = mode << 25 | 5 << 16 | m << 8 | 0xff: under EQUAL a pixel draws iff its
loaded stencil byte S has S & m == 0 (E284), and its byte is stored inverted (SOP3 invert).

| Rows | Fill | Mask | Reads |
| --- | --- | --- | --- |
| st1-always, st1-never, st1-noisp (controls) | bytes | always / never / no --isp2 | 2048, 0, 2048 drawn |
| st1-b0 .. st1-b7 | bytes (byte b = b & 0xff) | 1 << k | bit k of each pixel's byte index j: j mod 256 for every pixel and lane |
| st1-s1b1 | bytes:1 | 0x02 | the carry of j + 1 (the fill's exact form) |
| st1-lane0, st1-lane1 | 0x03020100 | 0x01, 0x02 | each pixel's byte lane |
| st1-e-b0, st1-e-b4 | bytes, 40 x 20, `--depth-pages 16` | 0x01, 0x10 | edge tiles |
| q071-b0, q071-l1 | as st1-b0, st1-lane1 | | the control's inert bits flipped together (r10-x zbits' mask) |

Frozen (gen/st1.py), per row: the drawn pixels (triangle colour 0xff00ff00 in the `row N:` lines)
and the stored stencil bytes of the target's pixels, under H-DEPTHORD (E985's reading: byte j =
y0 x0 y1 x1 y2 x2 y3 x3 x4 of the tile's 512), H-RASTER, H-F2ORD (E985: 0 of 13 tiles) and H-NOLOAD
(the test reads 0: everything draws, the store holds 0xff); q071 rows: H-INERT, the image and the
whole stencil-store dump equal to their base row's. Controls that can fail: the drawn counts of
st1-always (2048), st1-never (0) and st1-noisp (2048). Stops: any fault or hang (4), a control
without its reading (premise, 25), a tri row without `job: ok` (hook_check, 24), free space under
300 MiB (22). Verdicts for the fold: Q121 retires if H-DEPTHORD holds on all 13 rows (the test
clause and the order on every lane, edge tiles included); Q071 retires (with r10-x's zbits) if
H-INERT holds on both q071 rows.

## Deviations from the plan

1. **18 jobs, not 16 + 9 + 2.** The bytes fill (R10-6, landed in t10) reads j mod 256 for every
   pixel in 8 rows, so the plan's index rows (st1-idx-0, -5) and bit:K rows (st1-bit-K, 7) are
   dropped: their readings are subsets of the bytes rows'. The f0ctl control is st1-noisp. The
   edge rows use the bytes fill (masks 0x01, 0x10) instead of 0x03020100.
2. **H-NOLOAD's store** is frozen as 0xff (the ISP's 0, inverted); the plan named no store value.
3. **Edge tiles:** pixels past the 40 x 20 target are a reading (E831's band may process them).
4. **The kit is 287031c** (r10-tooling3: the library-mock replay gets a kpoke file and flags every
   bad end). `lead/dryrun_checks.sh` also replays the 18 rows on t10's library mock and prints
   what they write: every row ends `job: ok`, prints its isp2 line and its pixel rows, and writes
   the three dumps; the bytes:1 buffer starts 01 02 03 ... A first build of this session on
   cfa98c0 (closing10/r10-st1-cfa98c0-retired, frozen, never staged) is superseded.

## Replay vectors (HACKING.md "Replay vectors")

`isp-stencil-loaded` (closing_tables.py, `sgx545-tables`: fill, ISP word 2, the kept image and
stencil store): replay sgx-pipe's `zls` pass test of the loaded stencil's copy, widened test
first with the stencil test and the held byte order; refused if no model holds. The freeze pins
`crates/sgx-pipe/src/zls.rs` and `userspace/libsgxfive/src/render.c`.

## Commands

- Python: `$HOME/src/resgx545/.venv/bin/python` (tests use it unless `PY` names another).
- Generator: `python3 gen/make.py` (`--check`).
- Dry run: `bash lead/dryrun_checks.sh` (library mock only, Mac).
- Offline: `bash tests/run_all.sh`; freeze `python3 kit/session.py freeze .`, then again
  `bash tests/run_all.sh`.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py st1 KEPT_DIR`.

Mock worlds (`mock/world.py`): model (0), nopixels (premise 25), rejected (4), ispfault (4).
Nothing here is firmware-derived; every file may go to resgx545-data.
