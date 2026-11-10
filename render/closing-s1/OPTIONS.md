# S1: tool options the tables rely on, checked against the current source

Source read: `~/src/resgx545/userspace/libsgxfive/tools/sgxfive-test.c` (4331 lines, file time
2026-11-09 16:54), `src/tri_probe.c`, `src/render.c`, the local build `build/sgxfive-test` (18:10,
newer than the source).  Kernel side: the fork's branch `resgx545` (`git show resgx545:...` in
`/Volumes/linux/linux-sgx`; the working tree there is on the OLD branch `sgx545`, which has no
`alias_skip`, `hold_recovery`, `render_keep`, `tadata_fill`, `kregnow`).  Checks: **S** read in
the source, **M** run against the tool's in-process mock (`tests/mock_all.py`: every one of the
167 commands is accepted, 0 usage errors), **E** `--mock --emit-scene` word check
(`tests/emit_checks.py`), **P** the tool echoes it at run time (the scorer reads the echo), **H**
only hardware can show it.  Nothing here ran on the laptop.

Both the tool and the tables use `tri` (render N times) and `probe` (a program as the fill shader,
or with `--tri SLOT` as a slot of the first triangle's render).  Line numbers are in
`sgxfive-test.c` unless named.

## tri

- **`-n N`**: line: 3362; what the tables assume: N successive renders of one-triangle scenes;
  check: S; status: ok
- **`--width/--height`**: line: 3353; what the tables assume: target size; the context's maximum
  defaults to it; check: S, M; status: ok
- **`--geometry N` (repeat)**: line: 3594, 4235; what the tables assume: render N (1 to n-1) is
  TA-only and leaves the scene open; the last render closes it; rejected for N >= n; check: S, M,
  P; status: ok: prints `tri WxH #k: geometry only, the scene left open`; the kernel flag
  `DRM_SGXFIVE_SUBMIT_JOB_RENDER_GEOMETRY` is in branch `resgx545` (`sgxfive_submit.c:224`, uapi
  header line 821)
- **`--move N:DX,DY`**: line: 3625, 2921; what the tables assume: render N's triangle moved DX, DY
  pixels (whole pixels, negative allowed); check: S, M, P; status: ok: prints `tri: render N moved
  by DX,DY`. **Defect found**: the move changes only `p.v` (1/16 px); with `--tri-v` the render
  uses `p.v256`, so the move is silently ignored there (and the CPU reference then disagrees). No
  S1 job combines them
- **`--keep-overflow`**: line: 3382; what the tables assume: a render that overflows the PB
  (ENOSPC) is counted, not a failure; check: S; status: ok
- **`--keep-going`**: line: 3377; what the tables assume: report every render, checked or not;
  check: S; status: ok
- **`--wait-ms MS`**: line: 3616; what the tables assume: wait per render, 1 to 600000; check: S;
  status: ok
- **`--dump-render DIR`**: line: 3604; what the tables assume: DIR/tri.param.bin and
  DIR/tri.tadata.bin (with `--dump-each`: tri.N.*) after the renders; check: S, M; status: ok; DIR
  must exist (the runner makes `$W/dump`)
- **`--dump-each`**: line: 3382; what the tables assume: the dump after every render N (needs
  `--dump-render`); check: S; status: ok; a geometry-only render dumps too (E627 has such files)
- **`--words DIR`**: line: 3608, 2879; what the tables assume: DIR/words.N.txt and ta3d.N.bin
  around each render; check: S; status: ok; DIR must exist
- **`--regs LO-HI`**: line: 3650; what the tables assume: registers after the job, read-only
  through /dev/mem; **not** printed after a geometry-only render (the `continue` before
  `print_regs`, about line 3055); check: S; status: ok
- **`--tri-v X0,Y0,X1,Y1,X2,Y2`**: line: 3410; what the tables assume: window coordinates in 1/256
  pixel (1/2^K with `--tri-unit`); check: S, M, P; status: ok: prints `tri: vertices256 ...` (the
  B scorers check it against the table)
- **`--tri-z A,B,C`**: line: 3419; what the tables assume: vertex depths 0..1 (strtof); check: S,
  M, P; status: ok: echoed with the vertices
- **`--depth`, `--depth-ctl V`, `--depth-fill F`, `--depth-pages N`, `--depth-dump DIR`**: line:
  3383, 3369, 3347, 3371, 3442; what the tables assume: a depth buffer the ZLS words point at,
  control word V, filled with F (a raw dword), N pages (at least width x height x 4 / 4096),
  dumped as DIR/depth.N.bin after render N; check: S, M; status: ok; the kernel writes the ZLS
  words by debugfs kpoke from the tool (the debug option must be on). The control word's pitch
  field g = tiles across - 1 is set per width by `s1pix.depth_args` (tri1141.py's rule)
- **`--poke blk:1=V`**: line: 3533; what the tables assume: the state block's word 1 (ISP word 0)
  before submit; check: S, M, E; status: ok: block word 1 is ISP0 (`render.c:103`)
- **`--pixels`**: line: 3526; what the tables assume: every pixel, `row Y: 0x...` lines; check: S,
  M; status: ok

## probe (fill)

- **`--temps N`, `--coords`, `--pixels`**: line: 4083, 3765, 3769; what the tables assume: as the
  p1141 runs (64 x 32 fill, `pa0 = y << 16 | x`); check: S, M; status: ok
- **`--scratch-pages N`**: line: 3773; what the tables assume: scratch buffer of N pages, 16 to 64
  (default 16 = 64 KiB); prints `scratch at 0x... (N*4 KiB)`; check: S, M, P; status: ok (the D
  scorer reads the printed KiB)

## probe --tri

- **`--tri SLOT[:N]`**: line: 3827; what the tables assume: the FILE is the program of SLOT of the
  first triangle's render; check: S, M; status: ok
- **`--slot NAME=FILE[:N]`**: line: 3832; what the tables assume: another slot's program (PDS ones
  with N data dwords); check: S, M; status: ok
- **`--vertices N`**: line: 3838; what the tables assume: N vertices (whole triangles, at most
  1500 with the wide rig); copy c is moved c/16 pixel; check: S, M; status: ok; `tri_probe.c:365`
  also refuses other counts: E704's 1400 and 1300 were refused (rc 2), the ladder uses 1410 and
  1380
- **`--copy-depth`**: line: 3912; what the tables assume: copy c at clip z = c / 16 (always
  farther under `less`); check: S, M; status: ok
- **`--vtx-coords N`**: line: 4028; what the tables assume: N more output dwords per vertex;
  check: S, M; status: ok
- **`--vdm N=V` / `N^=V`**: line: 3951; what the tables assume: the VDM stream's word N set / bits
  flipped, after `--vtx-coords`; word 2 is the index-list header whose count field is bits 21:0
  (`tri_probe.c:61, 245`); check: S, M, E; status: ok: the E4 flip changes exactly bit 24 of one
  gen-page dword (`tests/emit_checks.py`)
- **`--blk N=V`**: line: 3950; what the tables assume: state block word N (6 viewport x offset, 14
  w clamp: E061, `render.c:98-118`); check: S, M, E; status: ok (emit check for words 6 and 14)
- **`--obj2 FIRST`, `--obj2-blk N=V`, `--obj2-pixel FILE`**: line: 3860, 3867, 3882; what the
  tables assume: the copies from vertex FIRST on as a second object whose state block is the
  first's with words set; check: S, M, E; status: ok (emit check: second block word 1 and word 10
  land)
- **`--tri-v`, `--tri-unit K`**: line: 3932, 3920; what the tables assume: as `tri`; not with
  `--vertices` (line 1994); check: S, M; status: ok; `tools/usse-asm/probe.py` does not model
  them: appended by hand in the E3 fine-grid rows
- **`--dump-render DIR`**: line: 3846; what the tables assume: DIR/NAME.param.bin and
  NAME.tadata.bin, NAME the program's file stem; check: S, M; status: ok
- **`--emit-scene FILE`**: line: 3850; what the tables assume: (checks only); check: M, E; status:
  ok; options must come before the FILE argument

## Debugfs knobs the runner writes (branch `resgx545`, `sgxfive_debug.c`)

- **`render_pb_pages`**: line: 1828; assumption: x32; read at render-context creation; clamped at
  use: below 0x23 or above 0x422 gives 0x422 (`sgx_render.c:48-53`, `sgxfive_drv.c:168`); the
  read-back shows the value written, not the clamp; status: ok; the effect proof is the first
  sample of 0x0624 (P - 0x22), per job
- **`alias_skip`**: line: 1816; assumption: a mask of firmware buffer ids 0-15 left out of the
  alias of render VMs made after the write; bits 16-31 refused; a reset leaves it alone; status:
  ok, in the new branch only
- **`reset`**: line: 1809; assumption: a write runs the in-place recovery (see PREFLIGHT: it
  re-runs the boot sequence); status: ok
- **`regs`, `buf09`, `render_param`, `render_tadata`**: line: 1353 (sgxfive.c), 1417, 1830;
  assumption: read-only; kept per job; status: ok; the runner's preflight refuses a driver without
  them

## Needs a change, or cannot be checked offline

- **`--move` also moving `v256` when `--tri-v` is given (the defect above)**: about 6 lines in
  `sgxfive-test.c` (`tri`); not needed by S1; needed if E2 wants a small triangle
- **`health.sh` prints `hold_recovery rtds_keep alias_ta3d_ro render_pb_pages render_ctx_flags`
  but not `alias_skip`**: 1 word in its `for` list; `s1.sh` reads it by a second ssh instead
- **`health.sh` has no timeout of its own (a stuck GPU process keeps the ssh alive)**: a `timeout
  120` in front of each tool call; `s1.sh` wraps it in a perl alarm
- **`tools/campaign`/`run-table.sh` cannot run these tables: a table must be
  `probes/<unit>/<feature>.toml` in the repository, markers are per table not per job, no
  regtimeline per job, no knob columns**: wrap each stage as a script table (one toml + the
  stage's template, 20 to 40 lines each); only if the user wants datasets and manifests straight
  away; S1 writes raw keep directories (`~/s1-out/STAGE`) like the 11.39/11.41 batches
- **`regtimeline` on the laptop: no bringup script builds it (earlier batches expected
  `~/regtimeline`)**: `stage_s1.sh` builds it from `tools/sweep/regtimeline.c` (one `cc` line,
  userspace); all `rt` jobs
- **E4's `--index-width 32`**: about 20 lines in `put_copies` and the header (proposal); only if
  E4 shows the HW signature
- **a landed, numpy-free gradient-range scorer (`depth_drift.py grad_bounds` as a `tools/`
  script)**: about 80 lines; B1, before its result is recorded (the proposal asks for it); the S1
  scorer is scratch
- **laptop-side tool/program identity: `~/sgxfive-test-s1`, `~/s1-stage/*.bin` are built or copied
  by `stage_s1.sh`; the earlier stage directories (`~/sgxprobes-stage`, `-1134`, `-1139`) are not
  used, so identity with E702/E709/E704's programs is by rebuilding, not by their sha**: none; E5,
  C (programs rebuilt from `probes/ta`, `probes/usse`; `p1139-green.bin` is byte-identical to the
  data repo's copy; `pds_iter_xy.s` exists in two different versions, `probes/pbe` and
  `probes/usse`: the usse one is used)
