# r10-x

Round 10's session r10-x (decisions R10-2 (a) and R10-3 (a) of `closing10/rank/rank-round10.md`,
the lead's DECISIONS-R10.md; records E995-E999, more from the lead if sb and win0 both run),
built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 dd2912899299, data 1324301bef13. Laptop prefix
`r10x`, module B60AB0B475DD1E8972419B5 (fork 2a650d74, as it runs since 03:11), tool t4 =
`~/sgxfive-test-rgn4` (sha256 e6951558..., built from resgx545 4623753
`userspace/libsgxfive/tools/sgxfive-test.c`, sha256 703cbcea..., `TOOLSRC.sha256`). One knob,
`render_rgn_arrays` (win0 only). No kernel change, no boot, safe class only: no `expectfault` row.

## What runs, in order (91 jobs, about 10 minutes of jobs at r9-x's 6.4 s, 30 with staging)

| Stage | Plan | Questions | Jobs | Controls (can fail) | Frozen | Record |
| --- | --- | --- | --- | --- | --- | --- |
| dcmp | R10-A | Q241, Q243 | 31 | E977 z243-ctl (2048), eq-m0 (0), eq-m7 (2048) | drawn: H-GL (mode rows); H-UBITS, H-ABS, H-IEEE, H-CLAMP0 (NaN, negative loads) | E995 |
| zov | R10-C | Q242 | 11 | the 5 full-pitch planes (E831's count, every dword distinct) | per shared slot H-LATE / H-EARLY, header and raster order; format 1 by O10-2's floor | E996 |
| zbits | R10-D | Q071 | 11 | z242-c-f0, -f1 reruns (E977's kept dumps) | H-INERT (E977's dumps, drawn, hash); bit 0 H-E665 | E997 |
| isp0x | R10-E | Q241 | 6 | the unpoked z242-c-f0 | H-NULL (E977's dump, drawn, hash); a reading otherwise | E998 |
| sb | R10-F | Q046 | 18 | E383's 0x208 jobs (kept images) | per pixel H-LOW16 (mode 15's image), H-M7 (mode 7's) | E999 |
| win0 | R10-B | Q030 | 14 | E502's A-m1-tee0-64x64-x, A-m0-te20-64x64-x (kept images) | per pixel H-IDENT, H-IDFULL, H-WIN | the lead's next |

Each stage's header (`tables/STAGE.txt`) and generator module (z.py, probes.py in gen/) say what
each row tests; `predictions/STAGE.tsv` and `predictions/STAGE/NAME.MODEL.txt` are frozen with the
session. The scorer prints one SUMMARY line per frozen model per stage, gated by the stage's own
controls (GATES is empty: no stage gates another).

Stops: any fault or hang (no row is `expectfault`; `#limit 0`): the session stops (4); a control
without its reading (premise, 25); a tri row without `job: ok` or a probe row without one pixel
row a target row (hook_check, 24: the stage stops, the next runs); free space under 300 MiB (22);
a knob that does not read back (19). win0 runs last: if the module refuses its TE words with the
knob set (the library mock cannot show that it takes them, below), its first row fails and the
session stops (4) with every other stage done.

## Deviations from the plan, from its checks (lead/dryrun_checks.out)

1. **Stage order: sb before win0.** win0 is the only stage whose premise rests on a reading of
   the kernel's source rather than on a dry run; last, a refusal costs nothing else.
2. **R10-E isp0x: 6 jobs, not 7.** ISP word 0 bit 18 faulted the job in E065 (Q241); round 10 is
   safe class only, so it is not run. `blk:2` is ISP word 1 (check 2: libsgxfive render.c
   `sgxfive_tri_block`, blk[1] isp0 0x01d00200, blk[2] isp1 0x10f0; a row with two pokes runs).
3. **R10-C zov: the plane.** The plan's z 0, 1, 0.5 at (0,0), (2W,0), (0,2H) gives equal depths
   along diagonals at 64 x 32 (both steps 1/128), so no float would name its pixel. The rows use
   z 0, ZX, 1 with ZX the largest power of two at most 1/(2H): the y step exceeds a row's x range
   and every pixel of every tile area has its own float32 (tests/test_gen.py). Every size is whole
   tiles (no edge band to read).
4. **R10-B win0: E502's program files are not published** (`p1126-pos-x__0.bin` and `-y__0.bin`
   are in neither repository). The rows use E437's published primary PDS program
   (`dpm-partial-reload-pos-pa0__0.bin`, 12 data dwords, DOUTI 0x20400000; the same file for its
   pa0 and pa1 jobs) and shaders (`pix_pa0.bin`, `pix_pa1.bin`): E502's record names E437's
   program. The two E502 controls say whether these are E502's set; on the Mac, H-IDENT's mode-1
   image of the first control's geometry equals E502's kept image at 4096 of 4096 pixels
   (tests/test_gen.py), so the decode and the region model hold there.
5. **R10-B win0: the knob is not shown by a dry run.** The library mock of t4 has no
   counterpart of `render_rgn_arrays` (mock.c check_render's comment) and t4 lists no
   `--mock-knob`: its replay fails the 13 rows with TE bit 31 or 30 (`failed: Invalid argument`,
   rc 3, check 5). The kernel takes them: fork 2a650d74 `sgxfive_render_init` sets `ctx->aa_ms =
   ctx->aa4 || setting` at the creation of every render context (sgxfive_ctx.c, the probe's
   included) and `sgxfive_render_check` refuses a multisampled TE_AA only without it; r9-geo's
   seam1 wrote the knob on B60AB0B4. Check 6 replays the 14 rows on a copy of the library mock
   whose check takes the knob as the kernel does: all complete with their 64 or 96 pixel rows.
6. **The kit's libmock replay does not reach the depth rows' render** (a finding for the
   round's tooling agent, not fixed here): it runs without `SGXFIVE_KPOKE`, so every `--depth`
   row ends at `kpoke: No such file or directory` with rc 1, which it does not flag (and a probe's
   `failed:` line, rc 3, neither). Check 5 replays all 91 rows with the kpoke file: the 59 tri rows
   end `job: ok`, the 18 sb rows and win0's TE 0x20000000 control print their 64 pixel rows.
7. **R10-8 grad (Q288) is not built**: its offline check fails (q288_split.out: near 2^-4 the
   nine rules' closest pair is 2.0 ulps over a tile row, at the threshold; near 2^-8, where they
   part by 32, Q200's dyadic controls themselves miss by one or two ulps below binade 0 and E731
   found no single plane origin in b2, so the control the check requires would not hold).
8. **R10-3 sb is built**: one E383 job (0x208, colour 0xc0804020) replays on the library mock as
   a kit probe row (check 4), and every sb row does (check 5).

## Replay vectors (HACKING.md "Replay vectors")

| Stage | Vectors table (closing_tables.py, `sgx545-tables`) | replay |
| --- | --- | --- |
| dcmp | `isp-depth-compare` (mode, t, L, kept drawn count) | sgx-pipe `isp` depth-test test once the fold widens the compare decode past 0, 1, 4, 7 (E660's refusal under Q241) |
| zov | `zls-overlap` (W, H, G, slot, kept dword, the pixel its float names) | sgx-pipe `zls::store` test once the fold lifts `no_overlap`'s refusal (Q242) |
| zbits | none (equalities with E977's kept dumps) | refused: a reading of inert bits, no new value |
| isp0x | none (a reading table) | refused |
| sb | `pbe-sideband` (mode, field, colour, kept image) | sgx-pipe `pbe` pack test once the fold adds modes 20 and 27's field rule |
| win0 | `msaa-ident-m0` (TE, size, kept image) | sgx-pipe `msaa_source` test once the fold lifts the mode-0 window refusal (Q030) |

The freeze pins every input those replays read (session.toml `[freeze] pins`): E977's, E383's
and E502's kept files, the region model, sgx-pipe's `ta.rs` and `zls.rs`.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Generator: `python3 gen/make.py` (`--check`: current or not).
- Dry-run checks: `bash lead/dryrun_checks.sh` (library mock only, Mac).
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).
- Score: `python3 score/score.py STAGE KEPT_DIR`.

Mock worlds (`mock/world.py`): model (all 0), nopix (sb and win0 stop 24, the rest run), nodepth
(premise 25 at zov), rejected (`job: rejected` with a diff line: 4 at dcmp), winrefused (the
module refuses win0's TE words: 4 at win0, every other stage done).

Nothing here is firmware-derived; every file may go to resgx545-data (the bins are byte copies
of published bins of resgx545-data).
