# r17-zls

Round 17's session r17-zls (plan `closing17/plan/rank-round17.md` sections 2 and 3, rows 2 and 3;
decisions R17-1 (a), R17-5 (a), R17-6 (a) in `closing17/DECISIONS-R17.md`; records E1068 (Q299)
and E1069 (Q071)), built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 c2180e64ecda, data af46e80770ac. Laptop prefix
`r17z`, module B60AB0B475DD1E8972419B5 (fork 2a650d74). Tool t10 = `~/sgxfive-test-t10` (sha256
9bedc2d6..., already on the laptop), built from resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., `TOOLSRC.sha256`) by
`lead/build_tool10.sh`, a byte copy of the published
`data:render/closing-r10-st1/lead/build_tool10.sh` that session.toml binds as the recipe
(r16-zls's binding). No knob, no kernel change, no boot, safe class only: no `expectfault` row,
`#limit 0` in every stage, no row predicted to fault under any frozen model. Round 16's r16-zls is
the direct predecessor: its helpers are copied into gen/z17.py, whose docstring states every
model.

## What runs, in order (17 jobs, about 2 minutes of jobs, about 6 with staging)

A row's name prefix is its record's: `zo2-` E1068 (Q299), `zb20-` E1069 (Q071). The stages group
the rows by the dump their scorer reads (REQUIRED is per stage), so E1068's stencil rows run in
their own stage.

| Stage (dump) | Jobs | Rows | Controls (can fail) |
| --- | --- | --- | --- |
| zovp2 (depth store) | 5 | zo2-p-65 (65 x 33 G 1), zo2-p-63 (63 x 31 G 0) | zo2-c-160 (E1064's zo-p-160, kept store byte for byte), zo2-c-65, zo2-c-63 (the no-load stores of the two shapes: E996's owner rule; the first also E1041's kept zo-65-ov, its first 3584 dwords) |
| zovs2 (stencil store) | 3 | zo2-s-65, zo2-s-63 | zo2-c-s160 (E1064's zo-s-160, kept stencil store byte for byte) |
| zb20 (depth dump, stencil store; ends the session on a stop) | 9 | zb20-b-6-96, zb20-b-7-96, zb20-b-6-128, zb20-b-7-128, each right after its bit-20-set twin zb20-t-... | zb20-c-f6 (E1063's zb4-c-f6, E1031's zf-flat-f6, kept dumps byte for byte) |

Frozen per record (predictions/STAGE.tsv from gen/z17.py):

- **E1068 (Q299).** E1064's load pass over overlapping tiles, now with edge tiles: the depth
  (E996's plane over a 0.2 load) and the stencil (E988's st1, `bytes` load) at 65 x 33 G 1
  (slots 2 and 4 shared; the last tile column and row one pixel wide and high) and 63 x 31 G 0
  (slot 1 shared by the two edge tiles). H-OVL-PASS-EDGE (every tile loads its slot and passes
  over its whole 32 x 16 tile, the tile visited last owns a shared slot) against H-OVL-FIRST,
  H-EDGE-SKIP (an edge tile takes no load) and H-EDGE-EXT (the load reaches the pixels inside
  the extent only), and on the stencil H-EDGE-CLIP (the pixels beyond the extent are not
  tested). The depth cannot part H-EDGE-CLIP: the plane beyond the extent is above the 0.2 load
  where an edge tile owns its slot, so the models leave it out. Parting on the built rows
  (tests/test_gen.py): depth, 65 x 33 FIRST 221 dwords, SKIP 1536, EXT 1471 from PASS-EDGE;
  63 x 31 FIRST 384, SKIP 1024, EXT 79; drawn counts 845 and 929 (SKIP) at 65 x 33, 756 and
  1825 at 63 x 31. Narrow: Q299's other clause is the planned fault (E411's G 5 in a 16-page
  buffer), one row for the user later.
- **E1069 (Q071).** E1063's post hoc form: with bit 20 cleared, formats 6 and 7 store their
  per-tile records one after another instead of at their slots' starts. At 96 x 48 G 2 and
  128 x 64 G 3 (no overlap, 32 pages named) each row's records are its twin's (bit 20 set, same
  size), packed in slot order from: H-PACK2048 (dword 2048), H-PACK-AFTER (the end of the last
  slot, 512 x rows x (G + 1): 4608 and 8192) or H-PACK-SCALE (1024 x (G + 1): 3072 and 4096).
  The three agree at E1063's 64 x 32 G 1 (2048) and part at both new sizes. The stencil store
  must be the twin's and the drawn count the target's pixels. Narrow: bit 23's source and the
  ISP's use of the control stay.

## Deviations from the plan

1. **63 x 31 G 0 replaces 161 x 49 G 2 as the second shape.** No kept plane reference exists at
   161 x 49, so a frozen drawn count and a prediction before the run need an extra reference job
   (and a score computed from the run's own reference). 63 x 31 has E1041's kept reference
   zo-63-f0 and the other edge geometry (two partial tiles that share a slot); 65 x 33 G 1 is the
   plan's. The cost: header order is raster at both shapes, so the rule of tile order across
   macrotile columns (160 x 48's, E996) is not tested again here.
2. **17 jobs, not 10.** The plan counts 4 rows and 1 control. This session adds: the second and
   third controls of zovp2 (the no-load stores of the two shapes, which hold the owner rule and
   the plane at each shape before the load rows are read), the stencil replicate (the stencil
   rows need a control of their stage), the twins of zb20 (the records of a bit-20-cleared row
   at a new size are its twin's, so each row runs beside its twin) and zovs2 as its own stage.
3. **Stages**: zovp2 (the depth store), zovs2 (the stencil store, the same E1068) and zb20, because
   REQUIRED is per stage and the three groups write different dumps.
4. **zb20's sizes**: 96 x 48 G 2 (the plan's 96 x 32) so that the three starts part at every
   size; 128 x 64 G 3 (the plan's 128 x 64, G named: G = tiles across - 1, no overlap).
5. **Rival H-EDGE-EXT and H-EDGE-CLIP** are the builder's additions to the plan's H-OVL-FIRST and
   H-EDGE-SKIP.
6. **The stencil of an edge tile beyond the extent is tested** [infer]: tri-full covers the whole
   tile area at both shapes (tests/test_gen.py), but the stencil test beyond the extent was
   never read. H-EDGE-CLIP is the negative.
7. **The pack rule's record** is a tile's dwords other than the fill (E1063's look.py): format 7's
   record is two runs of 12 dwords (at +0 and +256), so the rule is "the non-fill dwords of each
   slot in slot order", not a prefix of the slot (the scorer prints the prefix property as a
   reading).

## Predicted outcomes (frozen in predictions/, [infer] where not)

- E1068: H-OVL-PASS-EDGE on all four rows [infer: E1064's rule over whole tiles, E1041's whole
  edge tile]; all three zovp2 controls PASS and zo2-c-s160 PASS. H-EDGE-CLIP is the least sure
  (the stencil beyond the extent). If H-OVL-PASS-EDGE fails on an edge pixel, READING lines give
  the dwords off the model inside the extent and beyond it.
- E1069: H-PACK-AFTER [infer: E1063 saw the records "after the four slots"; at 64 x 32 it is
  indistinguishable from the other two]; H-PACK2048 is the main alternative, H-PACK-SCALE the
  least likely. A fit of none gives the row's written run (start, length, contiguity) as a
  reading [post hoc].

## Stops (stop budget)

Planned faults: none. Any fault or hang (4: the session stops); a control without its reading
(premise, 25); a row without `job: ok` or whose tool does not map the depth buffer at the
`--depth-pages` the row names (`hook_check`, 24: zovp2 and zovs2 stop their stage and the next
runs; zb20's stop ends the session, `on_stop = "end"`); free space under 300 MiB (22). zb20's
128 x 64 pair runs last: bit 20 cleared at that size and the 32-page buffers (records up to dword
8192 plus 44 a tile) are a range never run.

## Replay vectors (HACKING.md "Replay vectors")

| Rows | Vectors table (closing_tables.py, `sgx545-tables`) | replay |
| --- | --- | --- |
| zo2-p-, zo2-c- (zovp2) | `zovp2` (size, pitch, fill, the kept store) | sgx-pipe `zls::pass_plane` over edge tiles (test first; its refusal citing Q299 is lifted only if H-OVL-PASS-EDGE holds) |
| zo2-s-, zo2-c-s160 (zovs2) | `zovs2` (size, pitch, the kept stencil store) | sgx-pipe `zls::stencil_byte` store pass over edge tiles (test first); refused naming Q299 if no form holds |
| zb20-t-, zb20-b- | `zb20` (size, G, the twin's and the row's dumps) | refused: `zls::Ctl::decode` refuses bit 20 cleared with formats 5 to 7 (Q071, Q120) unless a pack form holds, then the format 6 and 7 records of Q120 are still refused |

The freeze pins what the replays read: `crates/sgx-pipe/src/zls.rs` and every kept dump the
scorer compares with (session.toml `[freeze] pins`).

## Mock worlds (mock/world.py)

model (0 everywhere), noread (premise 25 at zovp2), pages20 (the tool maps 19 pages where a row
names 20: zovp2 and zovs2 24, zb20 runs), pages32 (31 where 32: zb20 24, the session ends: driver
24), nojob (a 128-wide render prints `job: rejected`: zb20 4), fault128 (a 128-wide render with bit
20 cleared faults: zb20 4). The library-mock replay of the 17 rows refuses none.

## Commands

Every command is run through its interpreter, never by its mode bits.

- Python: `$HOME/src/resgx545/.venv/bin/python` (tests use it unless `PY` names another).
- Generator: `python3 gen/make.py` (`--check`).
- Offline: `bash tests/run_all.sh`; freeze `python3 kit/session.py freeze .`, then again
  `bash tests/run_all.sh`.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE KEPT_DIR`.

Nothing here is firmware-derived; every file may go to resgx545-data.
