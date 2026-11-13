# r9-geo

Round 9's session S9-geo (decision R9-3 (a) of the seeds plan
`closing9/seeds/exp-seeds-r9.md`, sections 1, 3, 4 and 10; user decisions
`closing9/DECISIONS-R9.md`),
built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 f32dfacc8db8 (kit/ is that commit's blobs), data
2d666bfafa21. Its generator, scorer and world are r8-geo's (resgx545-data `render/closing-r8-geo`),
copied and extended; r8-geo's frozen inputs (`gen/q284_rule.json`, `gen/o8/`) are copied byte for
byte and checked against their published copies (tests/test_r9geo.py).

## What runs

Four stages in this order, 77 jobs, one tool: t4 = `~/sgxfive-test-rgn4` (sha256 e6951558...),
bound by source to resgx545 4623753 `userspace/libsgxfive/tools/sgxfive-test.c` (sha256
703cbcea..., `TOOLSRC.sha256`), recipe `userspace/libsgxfive/Makefile` at that commit (the
binary's `built` line of FROZEN.commits); every row is replayed on that source's library mock
before the worlds run. Module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed.
Laptop files under `~/scratch/r9g/`.

| stage | plan | question | jobs | risk | what is frozen | records |
|---|---|---|---|---|---|---|
| seam1 | S-1 (a) | Q141 | 24 | safe | the O8 R8-1 table (E922), H-REGION vs H-UNION | E953 |
| seam4 | S-1 (a) | Q141 | 25 | safe | H-SAME4 vs H-FULL4 [infer], H-UNION | E954 |
| cube2 | section 3 | Q284 | 17 | safe | face-local laws, face distance, tie and edge rivals | E955, E956 |
| addr2 | section 4 | Q177 | 11 | safe | the offset rivals, the T3 null, two replicates | E957 |

Expected time: about 1 minute of jobs a stage (each job under 2 s plus the runner's reset,
snapshot and health; j1r prints 41472 pixels), about 20 to 25 minutes with staging, preflight and
health; stage alarms 25, 25, 20 and 15 minutes.

- **seam1** (`tables/seam1.txt`, Q141's held-out row). r8-geo's 24 seam rows (E934, refused
  there: no `--aa4`) with `--aa4` **and** `dbg:render_rgn_arrays=1`: a context made for 4x targets
  (the module takes a TE_AA with bit 31 or 30 only then) whose region headers are forced to one
  array, E502's, E504's and E727's condition (fork 2a650d74 `sgxfive_render.c
  sgxfive_render_init`: `ctx->aa_ms = ctx->aa4 || setting`, arrays `sgx_render_rgn_arrays(1, aa4)
  = 1`; the tail room is the 4x one [infer: it does not reach a 128 x 96 image]). Frozen:
  `predictions/seam1.tsv` = the O8 table byte for byte. Controls that can fail: tri-full 64 x 64
  mode 1 TE 0x60000000 (64 holes, E502's A-m1-te60-64x64 set: the test checks the kept dump's
  background set against the frozen hash) and mode 2 TE 0x20000000 (no hole). Held out: 14
  tri-full sets, 6 single triangles, 2 zero-hole twins.
- **seam4** (`tables/seam4.txt`, a reading). The same rows, `f4-` before their names, with `--aa4`
  alone (four arrays, never run in modes 0 or 1). Frozen per job: H-SAME4 (the O8 table's H-REGION
  set), H-UNION and, on the 17 tri-full rows, H-FULL4 [infer] (no hole). Controls: E828's j1r (288
  x 144, mode 2, TE 0xe0000000, `--aa4`: hash 0x4a61860dcb4ab325, 0 background) and 64 x 64 mode 2
  TE 0x20000000 (no hole under every rival).
- **cube2** (`tables/cube2.txt`). E726's probe form, r8-geo's frozen (s, t) rule (E923, E930).
  Control: E726's cu-xn program (2048 pixels known). (a) three new directions at 32 x 32 faces
  and r8-geo's three at 64 x 64 faces (T1 0x4c03f03f, `--scratch-pages 32`: six faces of 4096
  dwords are 24 pages): H-E561 (E561's tile law for the face-local index) vs H-MORTON (E923's, which
  E930 refuted at 32) and H-PAIRSWAP (equal to H-E561 at 32, parted at 64 on 702 to 895 pixels a
  job); (b) two directions at 4 x 4 faces (T1 0x4c003003): H-NN (faces 16 dwords apart) vs H-PAD64
  (64) [infer]; (c) four face-tie sweeps (x = y and y = z, the tied coordinates of opposite signs,
  32 tie pixels each): H-HIGHAXIS (z > y > x, E931's w over u) vs H-LOWAXIS and H-POS (the
  positive tied axis, the higher when both are [infer: E931's two rows are consistent with it]);
  each sweep parts H-HIGHAXIS from H-LOWAXIS, and H-POS goes with one of them on two sweeps each;
  (d) two texel-tie grids at |ma| 1.5 and 1.25 (readings, the boundary table per E931); (e)
  bilinear (T0 0x07fe1400) at the +z/+x and -y/+x edges: H-SEAM-ADJ (the out-of-face tap reads the
  neighbour face's texel adjacent across the edge: the rule's texel for the tap centre's direction)
  vs H-SEAM-WRAP (the neighbour face at the tap's own local (s, t) mod 16), each out pixel's four
  bytes within 1 of the exact blend, gated by the in pixels (90% within 1 of their exact in-face
  blend; E931's kept in pixels read it 1536 of 1536).
- **addr2** (`tables/addr2.txt`). Twiddled 32-bit textures at page 12 of a 32-page named scratch
  (T2 0x5CAFC000 and `--scratch-pages 32` on every row), the swept axis over 128 positions at one
  texel a step. Control: mode 0 on u (the repeat image; r8-geo's program byte for byte).
  Replicates: E932's addr-u4 (H-OFF180: H-MASK-V's index + 180) and addr-u5 (its per-position read,
  H-U5-E932), programs byte for byte r8-geo's. Held out: u modes 4 and 6 at 8 x 8 and 32 x 32
  (H-OFF180 vs H-OFFSCALE (+ 180 N^2 / 256) and H-OFFNONE); u mode 4 at 16 x 16 with T3 0, 0x800 and
  0x800000 (the null H-T3-INERT, else a reading); u and v both in mode 4 (H-OFF180 vs H-OFF360
  [infer] and H-MASK-V). Every read decodes to its dword: the scorer prints each row's index less
  H-MASK-V's and the index per position.

## Predictions and what each verdict does

Frozen before the run: `predictions/STAGE.tsv` and the per-pixel files `predictions/STAGE/`
(sha256 in the tsv; `PREDICTIONS.sha256` at the freeze). Expected, not frozen: seam1 H-REGION on
every held-out row if the controls pass (then Q141 retires, R8-3 (a)); seam4 open; cube2 H-E561 at
32 (E930's post hoc index, 4831 of 4831) and at 64 open between H-E561 and H-PAIRSWAP; addr2 the
replicates as E932. **Edges, read in sample:** on E931's kept edge jobs (other edges, +x/+y and
+z/-x) H-SEAM-ADJ matches 0 of 96 and 64 of 128 out pixels within 1 and H-SEAM-WRAP 0 of both
(`python3 gen/insample.py`, output gen/insample.out, post hoc, not frozen), so both rivals are
likely to fail on
the new edges:
the edge rows then stay a reading (the out values are printed). The plan's -y/+z edge cannot part
the two rivals (the faces' (s, t) line up across it: equal on 96 of 96 out pixels), so -y/+x
replaces it. Q284 retires when the 32 and 64 rows hold H-E561, the tie rows hold one rival 4 of 4
and the edge rows decide one rival; Q177 when size, T3 and mode 5 are decided (seeds plan section
9).

## Stops (kit/run_stage.sh, kit/session.py)

Any fault or hang stops the stage and the session (rc 4 / 6; none in E502, E504, E727, E726, E844,
E930, E931, E932's jobs); a tri job refused by the kernel (`job: rejected`, E934) is no reading
for expectdiff and stops the stage (rc 4); a control without its reading (pixels, `job: ok`, j1r's
hash) stops the session (rc 25); the second row of a stage without pixel rows or `job: ok` stops
that stage (rc 24, run/hooks.sh) and the driver goes on; a knob that does not read back (rc 19);
less than 300 MiB free on ~ (rc 22).

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest, numpy), which the offline
  tests use unless `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Generator: `python3 gen/make.py --check` (tables, predictions and programs current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).

Mock worlds (`mock/world.py`, the kernel's TE_AA check and region arrays modelled from the knob):
model, alt (every rival the other way), nopix (cube2 stops at its second row without pixels, addr2
runs), ctlnopix (premise stop), reject (the kernel refuses seam1's first control: rc 4), fault
(addr2 rc 4), hang (cube2 rc 6).

## Replay vectors

- seam1, seam4: `vectors/closing/r9-geo/seam1.table.json`, `seam4.table.json` (kind texture);
  `refused`: sgx-pipe's `isp::msaa_source` refuses the seam tiles (E618's reason), unless the fold
  admits them.
- cube2: `vectors/closing/r9-geo/cube2.table.json`; replay
  `crates/sgx-pipe/tests/texture_cube.rs` once `cube::point_index` takes E561's index above 16 and
  faces of 4 and 64 (the fold's sim update); ties, texel ties and edges refused (no tie rule, no
  bilinear sampler).
- addr2: `vectors/closing/r9-geo/addr2.table.json`; `refused`: no sampler models T0 address modes
  4 to 7.

The replays read only kept files, the frozen predictions (session files) and session.toml's pins.

## Data

No file here derives from the closed firmware: everything is publishable (resgx545-data
`render/closing-r9-geo`). bins/*.bin are our own probe programs (assembled from the pinned p1141
template by usse-asm), not tools.
