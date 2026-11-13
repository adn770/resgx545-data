# Round 9 K1: Q190's layered background, userspace and rows (planner, 2026-11-13, read-only)

Basis: resgx545 main 5e58278 (records to E946), linux fork `resgx545` 2a650d74 (fafea977 builds
the 23-dword object from the tag's layers; 2a650d74 adds debugfs `render_bg_layer` /
`render_bg_src`, read with `git show` only), IGT `sgxfive` effb512a5, laptop module B60AB0B4.
Inputs read: `closing8/rank/rank-round8.md` §3 (K1), `closing8/DECISIONS-R8.md` R8-5, the handover
`plans/resgx545-handover-2026-11-13-r8.md`, Q190, Q066, Q019, E069, E209, E590, E131, E437, E442,
`doc/specs/3d.md` §12.2, HACKING "Session kit" and "tools are bound by source". Nothing was built
or run; no scratch scripts in this directory.

## 0. Findings (read first)

1. **The tool is not in the IGT fork.** `sgxfive-test` is resgx545's
   `userspace/libsgxfive/tools/sgxfive-test.c`; sessions build it from a resgx545 commit (recipe
   as `closing6/r6-misc/lead/build_tool6.sh` / `closing7/r7-rp/lead/build_tool7.sh`: `git archive`
   of `userspace/libsgxfive include/uapi`, `make build/sgxfive-test` in the push-tools image on the
   build host). The IGT fork only *vendors* libsgxfive (`lib/sgxfive/`, flat copy, checked by
   `userspace/libsgxfive/tests/test_vendored.py` with `RESGX545_IGT`), and `build-igt.sh` builds
   IGT's `tests/sgxfive` programs, not sgxfive-test. So "the IGT fork change" is: the
   libsgxfive change in resgx545 (the real one), then a re-sync commit on IGT `sgxfive`, plus
   (optional) two IGT subtests that `build-igt.sh`'s `--list-subtests` smoke lists (section 1.5).
2. **The kernel builds the layer's words, not its source.** fafea977: with the tag saying one
   layer, `sgx_render_bgobj()` writes `sgx_xfer_bgobj_copy_words(bg, c->bgobj_words, &r, &r,
   W, H)`: words 0-2 the user's PDS words verbatim, 3-8 = (u, v) of the three vertices, vertex-
   major, 0 / 0 / 1.0 / 0 / 0 / 1.0 (the source rect is the target's own, so the coordinates run
   0 to 1), word 9 = 0, word 10 = 0x202 (the format word), 11-14 = 0, 15-22 the target rectangle's
   vertices (E590's 24-bit encoding). `render_bg_src` is only *checked* (non-zero, a valid PTE in
   the render's VM, else -EINVAL at submit); what is sampled is whatever the user's PDS program's
   texture words name. So the userspace must (a) map a source at the knob's address, (b) give a
   background primary that iterates and fetches, (c) set `bgobj_words[1]` to one attribute row:
   today's triangle sets `PIX_SIZE(0)` (render.c:385), and the kernel copies it verbatim, so an
   unchanged tool would build a layered object whose primary has no attribute row for the texel.
3. **The programs exist; only one file is new.** The copy's own pair is the layer sampler:
   `asm/transfer/pds_prim_1src.s` (DOUTU1 0x02000004, DOUTI0 0x40012001: fetch from coordinate
   set 1, source 36 = the texel, then `doutt` T0-T3) and `asm/transfer/use_copy.s` (o0 = pa0).
   The positive control is E442's background primary `probes/dpm/templates/pds_bg_pos.s` (source
   0: x + 0.5, y + 0.5 into pa0, pa1; E437 exact at 1062/1062) with `probes/pds/templates/
   pix_pa0.s`. The direct read of the iterated coordinates is new: a copy of
   `probes/pds/templates/pds_iter_nofetch.s` with DOUTI0 source 1, two components and the fetch
   bit (E131: with the fetch wait and a `doutt`, source 1 delivers the coordinate set's value).
4. **E934's slip has a twin here and the kit cannot see it today.** The kit's library-mock replay
   (`tools/closing/kit/session.py` `libmock()`) runs `sgxfive-test --mock ARGS` with no debugfs
   state, so a row with `--bg-layer` and no `dbg:render_bg_layer=1` (or the reverse) replays
   `job: ok` and on the laptop either is refused (-EINVAL) or silently renders the layerless
   object. Design-out in section 4 (tool reads the knobs and refuses; mock models them; kit passes
   a row's `dbg:` words to a library mock that lists `--mock-knob`).
5. **No kernel change is needed.** Everything below runs on B60AB0B4: the kpoke parser takes
   bg:17..22 when the knob is on at write time (the kit writes knobs before the job, the tool
   writes `--kpoke-render` after), a reset leaves the knobs, the replay rebuilds the same form.

## 1. The tool change (libsgxfive in resgx545, test-first), and its IGT re-sync

### 1.1 Option and behaviour

`--bg-layer` for `tri` and for `probe --tri` (same code path in the library; the session needs
both: `tri` for the sampled image with a CPU reference, `probe --tri` for the raw coordinate and
position reads through the `bgpds`/`bgpixel` slots).

- **What the tool writes to debugfs: nothing.** The kit owns both knobs as row words
  (`dbg:render_bg_layer=1 dbg:render_bg_src=0x3e800000`): written before the job, read back
  (rc 19), restored after the job before the health fill/triangle and by the exit trap
  (run_stage.sh line 168, before `health`). The tool *reads* them (it runs under `sudo -n`, as it
  already reads `render_param` for `--dump-render`): `render_bg_layer` (Y/N) and `render_bg_src`
  (hex) under `SGXFIVE_DEBUGFS` or `/sys/kernel/debug/dri/0/sgx`; a missing file reads as N / 0
  (older modules). On `--mock` the values come from `--mock-knob` (1.3). Rationale: a tool that
  writes the knob and is killed by `timeout -k` leaves it set for the next render (the kit's
  restore covers only knobs it wrote); R9-2 (b) is the `render_share_pb` alternative.
- **When:** once, before the VM and contexts are made. With `--bg-layer` the tool maps a source
  BO of `W x H` RGBA8888 (stride `W * 4`, pages rounded up) at exactly `render_bg_src` in the
  render's VM (the general heap, `scratch_create(t, vm, pages, at, ...)` as `--scratch-at` does,
  before `sgxfive_render_create` so nothing else can take the range), fills it with
  `texel(x, y) = ((x ^ y ^ 0xa5) & 0xff) << 24 | (y & 0xfff) << 12 | (x & 0xfff)` and prints
  `bg-layer: source 0x3e800000 64x64 RGBA8888, knob Y`.
- **The program (`tri --bg-layer`, and `probe --tri --bg-layer` when no `bgpds` slot is given):**
  `sgxfive_tri_scene` with `params.bg_src != 0` places `pds_prim_1src` and `use_copy` in free room
  of the pixel PDS and pixel USE pages (new offsets `SGXFIVE_TRI_PP_BGCOPY` /
  `SGXFIVE_TRI_UP_BGCOPY`
  [check: room below the probe slots at 0x800/0xc00 in both layouts]), patches its data as
  `xfer_job.c` patches a copy's (U0 to `use_copy`, U1 0x02000004, DOUTI 0x40012001 and 0, T0-T3
  = `sgxfive_tex_words(bg_src, W, H, ...)` of the copy), and sets `bgobj_words[1] = 1 | 3 << 16`
  (one attribute row, the copy's `put_pds_state(..., 1)`) and `bgobj_words[2]` to it. The two
  tables come from `asm/transfer/*.s` through `tools/gen_tri_progs.py` (one source of truth).
  With a `bgpds` slot the probe's own patching stays (`tri_probe.c:451-476`: PROBE_PIX_ROWS rows),
  the source is still mapped and the knobs still checked.
- **CPU reference (`tri --bg-layer`):** a background pixel (outside the reference triangle) must
  be `texel(x, y)`; the summary line gains `L layer texels in place, M layer texels elsewhere, N
  not a texel` and `print_target` reports the diff as today, so a poked row ends rc 1 with
  `job: ok` and a `diff:` line (`expectdiff`).
- **Refusals (exit 2, a `usage:` line on stderr, before any device call, so the kit's
  library-mock replay counts them as findings):** `--bg-layer` while the knob reads N; knob Y
  without `--bg-layer` (the tool's reference and the row's premise would both be wrong);
  `--bg-layer`
  with `render_bg_src` 0, not page-aligned, outside the general heap, or with the source not
  fitting before the heap's end; `--bg-layer` with `--tri-full` (no background pixel), `--aa4`
  (4x targets: the kernel's rectangle is the stored size, not checked here), `--ctx2`,
  `--geometry`, `--fault`, `-n` other than 1, or width or height above 4095. A VM_MAP failure at the
  knob's address (an overlap) is rc 1, `bg-layer: cannot map the source at 0x...: <errno>`.
- **Unchanged without `--bg-layer`:** every word of every existing job byte-identical (the tri
  64 x 64 control hash 0x99385a04ee01c585 of E590).

### 1.2 Tests first (libsgxfive, `make check` and `make check CC='cc -m32'`)

- `tests/test_render.c`: without `bg_src` every page and the command equal today's (the existing
  fixtures, `sgx_tri.c`'s words); with it, `bgobj_words[1] == 0x30001`, `bgobj_words[2]` points at
  the new primary, and the primary's 12 data dwords equal the transfer engine's copy primary for a
  W x H copy from the same address (`test_job.c`'s harness layout comparison), at 3 sizes.
- `tests/test_render_job.c` (mock): knob Y + mapped source: the render completes and every
  background pixel is `texel(x, y)`; knob Y + source 0 or unmapped: submit -EINVAL (job rejected,
  no image); knob N: today's image.
- `tests/test_cli_bg_layer.py` (new, pytest on the CLI against the mock): each refusal of 1.1 is
  rc 2 with its line; `--mock --mock-knob render_bg_layer=1 --mock-knob render_bg_src=0x3e800000
  tri --bg-layer --pixels` rc 0 and the summary's counts (3034 texels in place at 64 x 64, 0
  elsewhere); knob Y without the option rc 2; `--mock-knob` without `--mock` rc 2 (as
  `--mock-pb-pages`); an unknown knob name accepted with one `mock: debugfs NAME not modelled`
  stderr line (so older sessions' `dbg:` words replay unchanged).
- `tests/test_vendored.py` with `RESGX545_IGT` after the IGT re-sync.

### 1.3 The library mock

`struct sgxfive_mock_config` gains `bg_layer`, `bg_src` (set by `--mock-knob`). `check_render`
(mock.c:747) adds the kernel's `sgxfive_render_check_bg` rule (layer on: src non-zero and mapped
in the context's VM, else -EINVAL); the render interpreter, layer on, builds the 23-word object
with `sgxfive_bgobj_copy` (xfer.c:92, the kernel's twin) and paints background pixels through the
transfer interpreter's copy path (mock.c:922ff), generalised from a translation (`su`, `sv` from
bg+12/+16 only) to the three vertices' (u, v): enough for the identity image and for the kit
worlds' plumbing. The mock does not model kpokes or iteration rules; the predictions come from
the session's frozen model (section 3), not from the mock.

### 1.4 The kit (round tooling agent, not this session; R9-3)

`libmock()` passes a row's `dbg:NAME=V` words as `--mock-knob NAME=V` after `--mock`, only to a
library-mock binary whose usage lists `--mock-knob` (older sources replay as today). Test in
`tools/closing/test_kit.py`: a row with `--bg-layer` and no knob word is a finding; with both
words none; a row with the knob word and no option is a finding.

### 1.5 IGT fork (`~/src/igt-gpu-tools`, branch `sgxfive`)

1. `lib/sgxfive: re-sync libsgxfive with resgx545 <commit>`: the changed files of
   `test_vendored.py`'s FILES (render.c, sgxfive_render.h, tri_progs_gen.h, and xfer.c if touched),
   flat. `RESGX545_IGT=~/src/igt-gpu-tools .venv/bin/pytest userspace/libsgxfive/tests/
   test_vendored.py` passes.
2. Optional (R9-1): `tests/sgxfive/sgxfive_render.c` subtests `bg-layer-refused` (knob Y, source
   unmapped: SUBMIT -EINVAL; mapped: completes) and `bg-layer-texels` (identity background), each
   `igt_require` on the debugfs files, saving and restoring both knobs in an exit handler as the
   `render_pb_pages` fixture does (line 251-272). `tools/bringup/build-igt.sh <commit>` builds and
   smokes; the manifest's subtest list must name both. Not run on the laptop this round.

### 1.6 Binding in the session (never ship the binary)

session.toml `[tools.t9] path = "sgxfive-test-bgl"`, `sha256` the built binary's (the lead fills
it after the build), `source = "<resgx545 commit>:userspace/libsgxfive/tools/sgxfive-test.c"`,
`source_sha256` (the kit's libmock builds the mock from that blob's commit). FROZEN.commits gets
`<bin-sha256>  built  <commit>  userspace/libsgxfive/tools/sgxfive-test.c  <src-sha256>
data:render/closing-r9-k1/lead/build_tool9.sh` (a copy of build_tool7.sh with the commit and
target dir changed; or a resgx545 recipe if r9-tooling's `new_session.py` source binding lands
first). The health tool stays t4 (`sgxfive-test-rgn4`, as r8-k2). The templates are pinned as
`resgx545:probes/...` and assembled by the session's gen step, as r7-rp's.

## 2. The layer-sampling program and its controls

| name | primary (bgpds) | shader | reads | writes | what the pixel proves |
| --- | --- | --- | --- | --- | --- |
| L-TEX | built in: pds_prim_1src (DOUTI0 0x40012001, doutt of the source) | use_copy | the layer's coordinate set 1, the source BO at render_bg_src | o0 = pa0 = the texel | which texel (x', y') the layer's coordinates named: the check byte decodes it, or "not a texel" |
| L-RAW-U | `probes/isp/templates/pds_bgl_raw.s` (new): U1 0x02000004 in dword 3, DOUTI0 0x40400801 (source 1, two components, fetch bit), doutt of a 16x16 texture in the probe's scratch (SCRATCH_IMM) | pix_pa0.s | coordinate set 1 | o0 = pa0 = u as f32 bits | the iterated u at the pixel, exactly |
| L-RAW-V | the same | pix_pa1.s | the same | o0 = pa1 = v | the iterated v |
| POS | pds_bg_pos.s (E442) | pix_pa0.s | source 0 (no layer word) | o0 = f32(x + 0.5) | the background program and attribute path work with the layered object, independently of the layer words |

`pds_bgl_raw.s` [check before freezing: DOUTI0 0x40400801 = E131's tex-sources word for source 1
(0x40000000 | 1 << 11 | 1) with bits 23:22 = 1 (two components, 3d.md §12.2); the second component
of source 1 in pa1 is not yet measured, so L-RAW-V's control row is itself a premise check].

How the output proves which layer words were sampled: the object has exactly one coordinate
set (words 3-8); POS shows the program and attribute path alive without it; L-RAW reads the
iterated (u, v) directly at f32 precision, so a poke of one word predicts a different plane per
reading (vertex-major, component-major, none); L-TEX shows the texture unit takes those
coordinates and maps them to texels as a transfer copy does (E209). A pixel that is not a texel
(check byte wrong, or x' >= W, y' >= H) is counted, never decoded.

Mock test of the programs: assemble the new `.s` in a test next to `test_prog_asm.py` (data
dwords 3-9 as stated, two DOUTs and halt); the CLI test of 1.2 for L-TEX on the mock; the
session's `mock/world.py` answers L-RAW/POS rows from the frozen model (the mock does not
interpret them).

## 3. Rows: one kit session `r9-k1` on B60AB0B4 (prefix `r9k`, safe class)

Model (`gen/bgl_model.py`, standard library, frozen by hash with the predictions before the run):
attribute at pixel centre (x + 0.5, y + 0.5) = the plane through the three vertex values at the
render box's corners (0, 0), (W, 0), (0, H); texel = (floor(u W), floor(v H)), nearest, values kept
in [0, 1) for every L-TEX row (no wrap/clamp rule needed); f32 tolerance 2^-12 absolute for L-RAW
(E437 was exact; rivals differ by >= 1/128 at most pixels). Scored: the 3034 background pixels of
the 64 x 64 triangle scene (the CPU reference's), every one.

Hypotheses (frozen) and rivals:

- **H-BUILT** (premise): `--words` shows rd:18 (`SGX_RENDER_RD_BGTAG` 0x48) bits 30:25 = 1 and the
  `--dump-render` object is the 23 words of finding 2. Rival: the knob did not reach the job (tag
  0, 17 words). Fails: STOP.
- **H-POS** (premise control that can fail): POS with the layer gives f32(x + 0.5) at >= 3000 of
  3034, as POS without it. Rival: the layered object breaks or hangs the background. Fails: STOP.
- **H-ITER** (main): L-RAW u = (x + 0.5) / 64, v = (y + 0.5) / 64. Rivals: H-NONE (constant: 0 or
  stale, the render does not iterate the layer), H-SWAP (u and v exchanged), H-17 (read with the
  17-word layout: values from words 9-14, i.e. 0 / 0x202 garbage).
- **H-TEX:** L-TEX gives `texel(x, y)` at every background pixel. Rivals: H-ONE (one texel
  everywhere, E209's size-2 picture), other.
- **H-VM** (the Q190 clause): a poked value acts as vertex-major (3, 4) = v0, (5, 6) = v1 (top
  right), (7, 8) = v2 (bottom left). Rivals: H-LM (component-major: u at 3-5, v at 6-8), H-NONE.
- **H-AFF:** under H-VM the attribute is the model's plane (held-out values, exact).
- **H-VPLANE vs H-VBOX** (vertex words 15-22 in the layered form): the plane is anchored at the
  vertices the words give (E590's decoding [infer]) vs at the fixed render box (E590 saw coverage
  ignore them). Both frozen; the row set decides.
- **H-FMT0** (explore, E069/E209 analog): bg:9, bg:10 (eight values incl. 0x0, 0xffff) and
  bg:11-14 change nothing; rival for bg:10 = 0xffffffff: every pixel texel (0, 0) (E209).
- **H-ROWS** (explore, Q066 word 1): `--poke cmd:24=` (bgobj_words[1]) at 0, 1, 4 rows with
  L-TEX: the texel arrives at every value (Q019's analog: rows did not limit secondary
  attributes) vs lost at 0 rows. (Words 0-2 are never kpoked: the EDM rewrites them, E590.)

| stage | rows | set | tool | knobs |
| --- | --- | --- | --- | --- |
| s0 premise | c-off (tri, no layer: E590 hash), c-pos-off (POS, no layer), c-pos (POS, layer), c-tex (L-TEX + `--words` + `--dump-render`), c-rawu, c-rawv, c-noop (bg:5 = its own 0x3f800000) | control, 7 | t9 | layer rows `dbg:render_bg_layer=1 dbg:render_bg_src=0x3e800000 reads:...` |
| s1 coordinates | fit: bg:3..8 = 0.5 one at a time, read U and V (12); held-out: 12 seeded pokes (1-3 words, values in [0, 1]) read U and V (24); L-TEX: 2 fit + 6 held-out with u, v kept in [0, 1) (8) | fit 14, heldout 30 | t9 | layer + `--kpoke-render 1:bg:N=V` / `--kpoke bg:N=V`; L-TEX rows `expectdiff` |
| s2 vertex words | bg:15..22, one that moves an edge by 16 px under E590's decoding and one bit flip each, read U (16) and V on the y words (4) | heldout 20 | t9 | layer |
| s3 explore | bg:9 (2), bg:10 (8), bg:11..14 (2 each, 8), cmd:24 rows 0/1/4 (3) | explore 21 | t9 | layer, `expectdiff` |
| s4 end | c-tex, c-off again | control 2 | t9 | as s0 |

94 jobs; at round 8's 5-10 s a job with health, about 10-16 min of run, ~25 min with stage and
verify, one sitting. `#limit 0` in every stage (no `expectfault` row). Held-out values: drawn by
`gen/bgl_model.py` with seed `r9-k1` after the model's hash is written, predictions in
`predictions/s1.tsv` .. `s3.tsv`, `PREDICTIONS.sha256` frozen before staging. Fit rows may only
change a disclosed convention post hoc (pixel-centre offset, tolerance), never a held-out score.

Stop conditions: any hang or fault: stop (rc 4, reset, health), the session ends at that row.
s0 gate (`score.py gate`): H-BUILT and H-POS hold, else stop; H-ITER holds: run s1-s4; H-NONE
holds instead: run only s1's 6 one-word U rows (group `none`) to confirm, then stop; neither: stop,
fold as cannot-tell. s1 gate: H-VM + H-AFF right on >= 28 of 30 held-out rows and every rival
wrong on >= 3, else skip s2/s3. Q190 is answered (retire) when H-ITER, H-TEX and H-VM + H-AFF
hold; Q066 narrowed by s2/s3 (vertex words, format and zero words, word 1 rows).

Kit fit: yes, with R9-3's `--mock-knob` replay (or the session test of section 4 as a stand-in);
rows use only `dbg:` knobs, `expectdiff`, `reads:`, `gate`/`grp:`; `forbid_options` as r8-k2's
minus `--kpoke-render`/`--kpoke` plus `--tri-full`, `--aa4`, `--fault`. Mock worlds: H-VM world
(all stages), H-NONE world (s0 gate to the `none` group), premise-hang world (stop rc 4), missing-
knob world (the libmock finding stops the mock), stale-knob world (tool rc 2 on a control).

Records proposed (lead assigns): **E970** premise and plain reads (H-BUILT, H-POS, H-ITER,
H-TEX); **E971** coordinate words vertex by vertex, the plane held out (H-VM, H-AFF); **E972**
vertex words and the plane (H-VPLANE/H-VBOX); **E973** format, zero words and word 1 rows
(explore, Q066); **E974** spare (a correction or a slip).

## 4. What would make the rows unreadable, and how the design prevents it

| risk | prevention |
| --- | --- |
| Knob missing or src unmapped on a row (E934's twin): kernel -EINVAL, or a layerless object scored as layered | tool reads both knobs and refuses mismatches (rc 2 before any job); mock models the knobs; kit libmock passes `dbg:` words; session test: every row with `--bg-layer` has both `dbg:` words with the one address and vice versa |
| `bgobj_words[1]` left at 0 rows: texel not delivered | library sets one row; c-tex premise; H-ROWS rows separate it as a reading |
| Background program hangs (texture dependency never met) | premise rows first, any hang stops the stage (one recovered hang at most); no planned fault |
| Texel decode ambiguous; triangle and fill colours read as texels | check byte; 0xff203040 and 0xff00ff00 fail it; out-of-range coordinates counted as not a texel |
| Triangle covers the pixels scored | score only the reference's 3034 background pixels; `--tri-full` refused |
| Pokes on words 0-2 lost to the EDM (E590) | no bg:0-2 rows (guard via `forbid` in the session test); word 1 through `cmd:24` |
| A poke lost on a replay after recovery | a recovered job is a stop, never scored |
| Stale knob after a killed tool or a failed restore | kit owns the knobs (restore before health, rc 19); tool refuses knob Y without the option |
| Controls on a different scene (round 7 slip) | every layer control uses the subject scene and tool; c-off is a regression control only |
| Scorer reading the wrong dump name | `REQUIRED` names `tri.param.bin`, `words.1.txt`, probe's `NAME.param.bin`; the mock's sessioncheck kept; tests on kept fake records |
| expectdiff without `job: ok`; `#limit` counting a control's fault (E946) | kit since r8-tooling; no `expectfault` rows here |
| Sampling at range edges (wrap/clamp unknown) | L-TEX values kept in [0, 1); out-of-range only in L-RAW (no sampling read) |
| Source collides with the tool's own allocations | mapped first at the knob's address; a VM_MAP failure is rc 1 with its line |
| Iteration precision | tolerance frozen (2^-12), rivals >= 1/128 apart; E437 exact precedent |

Offline conclusions this plan rests on: finding 2 rests on the fork source (fafea977, 2a650d74);
finding 3 on E131, E437, E442 (records) and the asm sources; refutable by s0 alone.

## 5. Order and cost

1. libsgxfive tests then code (1.1-1.3), `make check` both ABIs: ~3-4 h. 2. r9-tooling: kit
`--mock-knob` replay + test (~30 min, same agent as the round's tooling). 3. IGT re-sync (+
subtests, build-igt.sh smoke): ~45 min. 4. `pds_bgl_raw.s` + its test, `gen/bgl_model.py`,
session r9-k1 on the kit (tables, predictions, scorer, worlds, tests/run_all.sh): ~2 h.
5. Build t9 on cachix (recipe), freeze, mock, stage, run: ~40 min. 6. Fold E970-E974: ~1.5 h.
Laptop: one sitting on B60AB0B4, any time before the next reboot; independent of the other
round 9 sessions (it writes only its two knobs).

## 6. User decisions

R9-1 Where the change lives: (a) libsgxfive in resgx545 (`tri` and `probe --tri --bg-layer`),
     IGT re-sync plus two subtests built and smoked by build-igt.sh, not run on the laptop
     (recommended); (b) as (a) and run the IGT subtests on the laptop too (outside the kit);
     (c) `tri --bg-layer` only (no L-RAW, no POS: H-ITER and H-VM read only through texels).
R9-2 Who writes the knobs: (a) the kit (`dbg:` row words); the tool reads them and refuses a
     mismatch (recommended); (b) the tool writes and restores them itself (`render_share_pb`
     pattern; a killed tool leaves them set).
R9-3 The kit's library-mock replay passes `dbg:` words as `--mock-knob`: (a) yes, by the round
     tooling agent before the session's mock (recommended); (b) no, the session's own test
     checks rows and knobs instead.
R9-4 Rows: (a) s0-s4, 94 jobs, ~25 min, safe class (recommended); (b) s0 + s1 only, 51 jobs;
     (c) s0 only (7 jobs), then plan the rest.
R9-5 Q066's explore rows (s3: format, zero words, word 1 rows, 21 jobs): (a) include
     (recommended); (b) drop.
R9-6 Records: (a) E970-E973 plus E974 spare, as section 3 (recommended); (b) the lead's
     numbering.
