# r10-zls

Round 10's session S10-zls (seeds plan `closing10/seeds/exp-seeds-r10.md` sections 5 and 6,
decision R10-4 (a) as the lead's DECISIONS-R10.md takes it; records E986 (zst2, Q120) and E987
(zbg and zw, Q101); E988-E989 are reserved for st1), built with the session kit (resgx545
HACKING.md, "Session kit"), scaffolded by `tools/closing/new_session.py` from resgx545
9849dab7540c, data 1324301bef13. Laptop prefix `r10z`, module B60AB0B475DD1E8972419B5 (fork
2a650d74, as it runs since 03:11). Tools: t4 = `~/sgxfive-test-rgn4` (sha256 e6951558..., built
from resgx545 4623753 `userspace/libsgxfive/tools/sgxfive-test.c`, sha256 703cbcea..., recipe
`userspace/libsgxfive/Makefile`, as r9-x) and t9 = `~/sgxfive-test-t9` (sha256 7a28be39..., built
from 97447b04, sha256 5de42943..., by `lead/build_tool9.sh`, r9-k1's binding, a byte copy of
`data:render/closing-r9-k1/lead/build_tool9.sh`); `TOOLSRC.sha256`. No knob, no kernel change, no
boot, safe class only: no `expectfault` row, `#limit 0` everywhere.

Stage st1 (Q121, and the ranking plan's R10-4 Q071 stencil rows) is not here: it needs t10
(`tri --isp2`, `--stencil-fill bytes`), which neither t4 nor t9 takes (lead/dryrun_checks.out).
It is built later as its own session when the lead asks.

## What runs, in order (39 jobs, about 5 minutes of jobs at r9-x's 6.4 s, 15 with staging)

| Stage | Tool | Jobs | Controls (can fail) | Frozen | Record |
| --- | --- | --- | --- | --- | --- |
| zst2 | t4 | 26 | z2x-f0, z2y-f0, z2d-f0, z2e-f0 (E831's 2048 dwords, E467's 512 stencil-store dwords), z2x-f4 (E978's 640) | per byte: E985's layouts H-E985 (f3, f4, f5, f6), the stencil orders H-RASTER, H-F2ORD, f6's H-F6ITI; H-E978 (no stencil store) on every format 3-7 row; f7 a reading | E986 |
| zbgc | t9 | 2 | zbg-c1 (1.0), zbg-c25 (0.25): every background dword at the poked word | (zbg's gate) | E987 |
| zbg | t9 | 7 | zbgc's two (gate) | per background dword: H-RAW, H-CLAMP0, H-CLAMP0P, H-ABS, H-B19-INT (-0.25, formats 0-2, bit 19 or not); H-ZERO (-0.0, format 1) | E987 |
| zw | t9 | 4 | zw-c50 (word 10 = 0.5): byte for byte E977's kept z242-a-f0 | per dword where x/512 + y/256 <= 0.5: H-LIN, H-HYP, H-OFF | E987 |

Each stage's header (`tables/STAGE.txt`) and its generator module (zst2.py or zbg.py in gen/)
say what each row tests; `predictions/STAGE.tsv` is frozen with the session. The scorer prints one
SUMMARY line per frozen model, gated by the stage's controls; zbg's by zbgc's (GATES, and the
runner skips zbg when zbgc's gate is closed). A held-out zst2 row holds a model when every byte it
predicts matches and every changed dword is one it predicts whole.

Stops: any fault or hang (the session stops, 4); a control without its reading (premise, 25); a
tri row without `job: ok` (hook_check, 24: the stage stops, the next runs); free space under 300
MiB (22). zbg does not run when either zbgc control fails (rd:16 is then not the background depth
as the plan reads it): SKIPPED, zw still runs.

Verdicts the fold draws (seeds plan section 14): Q120 retires if H-E985 holds on every f3, f4, f5
and f6 row and f7 decodes from these dumps (post hoc, the fold), else narrows to f7. Q101 retires
if one rival holds on all six -0.25 rows and zw decides word 10; otherwise it narrows.

## Deviations from the plan

1. **zst2: 26 jobs, not 24, and different ones.** E985's rules give each pixel's stored bytes from
   the format-0 float of the same plane, so each new plane (y, d, e) has its own format-0
   reference (a control: E831's count, E467's stencil copy); the plan's 24 named none. E978's x
   plane keeps only its two controls (z120-ctl-s rerun as z2x-f0, z120-f4-s as z2x-f4): its index
   rows were E985's fit set.
2. **zst2 "the full depth range 0 to 1 in x":** `--tri-full` spans 3W, so a ramp 0 to 1 across
   the target needs a vertex depth of 3 (t4 takes 0 to 1, and the MTE clips past 1, E287). The d
   plane is (0,0) (2W,0) (0,2H) at depths 0, 1, 1: z = x / 2W + y / 2H, 0.012 to 0.988 over the
   target (tests/test_gen.py), in x and y.
3. **zbg is two stages, zbgc then zbg** (`gate = true`): the plan's "zbg-c25 off (gate)" needs a
   gate the runner can apply before the held-out rows.
4. **zw (word 10) is its own stage, with a control the plan lacked:** zw-c50, word 10 = 0.5
   poked, byte for byte E977's kept z242-a-f0 (13 jobs for Q101, plan 12). Debug check
   (`lead/w10_look.py`, post hoc, on E977 and E981's kept dumps): E977's ramp is exactly
   (x + 0.5) / 512; E981's ramp a is 0.6 of it within one ulp only where x/512 + y/256 < 0.81 and
   leaves it beyond (912 pixels), so the frozen mask is x/512 + y/256 <= 0.5 and the rest of the
   target is a reading. The plan's "1.6 w + 0.2" is H-LIN; H-HYP (a hyperbola through the same two
   points) and H-OFF (word 10 as the z offset, refuted by E981) are rivals that can fail.
5. **zbg's rivals are split** where the plan's "0 in every format" is ambiguous under bit 19:
   H-CLAMP0 (clamp, then E466's sign flip: 0x80000000) and H-CLAMP0P (+0 everywhere).
6. **The kit's libmock replay does not reach the depth rows' render** (r10-x's finding 6; no kpoke
   file). `lead/dryrun_checks.sh` replays all 39 rows on both bound sources' library mocks with
   the kpoke file: every row ends `job: ok`, writes its dump, and the zbg rows' kpoke holds
   `rd:16=V` after the tool's own ZLS pokes.

## Replay vectors (HACKING.md "Replay vectors")

| Stage | Vectors table (closing_tables.py, `sgx545-tables`) | replay |
| --- | --- | --- |
| zst2 | `zls-packed-formats` (W, H, G, format, stencil fill; the format-0 reference and the kept dump) | sgx-pipe `zls` store test once the fold models formats 3 to 6 test first (`Ctl::format` refuses 3 to 7 under Q120 today); f7 refused unless the fold decodes it |
| zbgc, zbg | `zls-background-depth` (format, bit 19, rd:16 word, the kept background dword) | sgx-pipe `zls` pass test (`without_bits_1_and_14_the_pass_starts_from_the_clear_value`) and `encode_depth`, widened test first below 0 with the held rival (Q101) |
| zw | `isp-viewport-w10` (word 10, x, y, the kept float) | refused unless a rival holds (a reading otherwise); sgx-pipe has no viewport z model to widen |

The freeze pins what those replays read: `crates/sgx-pipe/src/zls.rs`, E977's z242-a-f0, E978's
kept zst dumps, E981's ramp dumps, r9-x's zst and zls tables (session.toml `[freeze] pins`).

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another.
- Generator: `python3 gen/make.py` (`--check`: current or not).
- Dry-run checks: `bash lead/dryrun_checks.sh` (library mocks only, Mac).
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).
- Score: `python3 score/score.py STAGE KEPT_DIR [ROOTS...]`.

Mock worlds (`mock/world.py`): model (all four stages 0), nodepth (premise 25 at zst2), rejected
(`job: rejected` with a diff line: 4 at zst2), bgoff (rd:16 ignored: zbg-c25 FAILS, zbg skipped,
zw runs: 0), negfault (a negative background faults: 4 at zbg).

Nothing here is firmware-derived; every file may go to resgx545-data.
