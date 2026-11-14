# r19-dpm

Round 19's session S2 r19-dpm (plan `closing19/plan/rank-round19.md` section 3; decisions R19-1
to R19-6 (a) in `closing19/DECISIONS-R19.md`; records E1079 to E1083: Q045, Q038, Q107, Q088),
built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 50606dc1cd12, data 95df71e98c95. Laptop prefix
`r19d`, module E0CC40275493F8AEAD8180B (fork 456404fcffe5, debugfs `render_final_pb_pages`), run
on the road over the travel cable (nothing here assumes cachix). Tools, all already on the laptop:
t18b = `~/sgxfive-test-t18b` (sha256 58e79855..., resgx545 ec50498, recipe
`lead/build_tool18b.sh`, a byte copy of `closing18/k18/build_tool18b.sh`, bound as S1 r19-k0's
publication `data:render/closing-r19-k0/lead/build_tool18b.sh`, built line `lead/TOOL18b.built`);
t10 = `~/sgxfive-test-t10` (9bedc2d6..., a581c06, r10-st1's recipe); rt = regtimeline (079f6359,
`wraps = true`, no source: a read-only sampler). Every row runs under rt with the plan's register
set (r13-dpm's plus 0x0620 and 0x0668). Safe class, except ld's four zero-fill rows (medium
[infer], `soft`, last in ld); `#limit 0` everywhere; no `expectfault`.

Runs only after S1 r19-k0: its k0 controls and f0-same, f0-up passed (R19-1 a). This session's
premise on every geometry row is f0's H-UPD (the final's 0x0624 = N - 0x22 and no overflow).

## What runs, in order (42 jobs, about 12 minutes of jobs, about 15 with staging)

| Stage (record) | Jobs | Rows | Controls (can fail) |
| --- | --- | --- | --- |
| ld (E1079, Q045) | 8 | base at P 0x28 x2, 0x30, 0x2c; then page 6 zeroed (`--tadata-fill-render 2:6:0`) at the same P (medium, soft) | ld-b28-1/2: premise, the pair repeat byte for byte (final param and TA data, target hash); every zero row: page 6 held lists after render 1 |
| ldb (E1080, Q045) | 6 | 4096x4096 default triangle, -n 1, P 0x40, 0x60, 0x80, 0xa0 (raised) | ldb-c0, ldb-100 (not raised: R-THR) |
| dzl (E1081, Q038) | 2 | - | dz-ac-nl, dz-ac-ld (E628's -n 1 0x422 dl cells, t10: sidx 0 / 1) |
| dza (E1081, gated by dzl) | 6 | E628 dl, final on N: 0x28 no-load x2, load, E336's 0x0011700a; 0x30 no-load, load | every row's premise |
| dzc (E1081) | 3 | layer + depth, -n 1, t10: 0x28 x2 | dz-cc (layer at 0x422: diff 0) |
| dzo (E1081) | 4 | E628 ov, final on N: far and near at 0x28 and 0x30 | every row's premise |
| zsc (E1082, Q107) | 2 | - | zs-c33, zs-c1 (-n 1 0x422 ramp pair, t10: no overflow, q107 RULE holds) |
| zs (E1082, gated by zsc) | 5 | E629's ramp, G 33 x2 and G 1 at 0x28, G 33 and G 1 at 0x30 | every row's premise |
| rd (E1083, Q088) | 6 | ramp, render 1 / render 2 G 33 / G 1 x2 and G 1 / G 33 x2 at 0x28; one each at 0x30 | every row's premise |

The plan's dz and zs are split into stages by the dumps their rows write (the scorer's REQUIRED is
per stage and per row; a dump only the geometry rows write cannot be required of a -n 1 row).

Every geometry row (t18b): `tri --width 1024 --height 768 -n 2 --geometry 1 --final-pb-pages
0x100 --keep-going --keep-overflow --wait-ms 20000 --dump-render "$W" --dump-each --words "$W"
--regs 0x0600-0x0750`, P by `dbg:render_pb_pages`, `expectdiff` (the final's image is short of
the partial render's tiles, E038), and its premise `ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0xde`
(run/hooks.sh): the kick overflowed, the final did not, 0x0624 read 0xde after it. Every
geometry depth row passes `--depth-ctl-next` (else the tool refills before the final). `--ctx2`
and `--bg-layer` refuse `--geometry`: no row combines them (dz-c is -n 1 on t10).

Frozen per stage (predictions/STAGE.tsv, gen/plan.py; score/score.py's docstring states every
rule): ld H-LOAD vs H-NOLOAD; ldb R-PEAK vs R-THR vs R-NEAR (and E625's raise); dz H-PRPATH vs
H-HOSTBITS, H-PRZERO vs H-CLRREAD, H-WHOLE vs H-LOSS, H-PRLOAD vs H-OWNCLEAR; zs H-PRSIGN vs
H-FINALSIGN, H-E996 vs E1020; rd H-RD vs H-FW-CONST vs H-FW-FINAL. Fit: the 0x28 rows; held out:
0x30, 0x2c, the swapped rd rows, the 4096 rows. Predicted outcome [infer]: H-RD 6 of 6 (Q088
retires with dz-a's load half, R19-5 a), H-NOLOAD or H-LOAD decided at ld (Q045 retires with ldb
if both hold, R19-6 a), dz and zs narrow Q038 and Q107.

## Stops

- Any premise off on a geometry row (the final overflowed, 0x0624 not 0xde, or no overflow in the
  kick): rc 24, the stage stops, the next stage runs (all four geometry stages share the premise,
  so a module-side failure stops each at its first geometry row; ldb still runs).
- A control without its reading: rc 25 (the session stops). A control off: rc 24.
- ld's zero rows: a failure without a fault is `soft` (void); the second in a row stops ld (24).
  A fault or hang there is unexpected (no `expectfault`): rc 4, recovery and strict health by the
  kit, the session stops (the plan's stop rule for the medium rows).
- Any unexpected fault, hang or failure elsewhere: rc 4.

## Commands

- Offline: `bash tests/run_all.sh` (guard, tests, the library-mock replay, every world).
- Freeze: `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score (Mac): `python3 score/score.py STAGE KEPT_DIR` for each stage.

## Mock worlds (mock/world.py)

model (every stage 0), finalovf (the final overflows: ld, dza, dzo, zs, rd 24, the -n 1 stages
0), noregs (no 0x0624: 25), ctloff (E628's no-load control stores indices: dzl 24, dza skipped by
its gate), zerosoft (two soft failures: ld 24), zerofault (a zero row faults: 4).

## Replay vectors (HACKING.md "Replay vectors")

- ld, ldb: `refused` (sgx-pipe's DPM model does not model the free-list walk after a final on
  another PB nor the state page's macrotile counts: crates/sgx-sim/SIM_UNMODELLED.toml's DPM
  entries; the fold names the entry).
- dza, dzo: `refused` (the ZLS load of a partial render's store is unmodelled); dzc `refused`
  (the layered background is not in sgx-pipe); dzl: the -n 1 stores replay through
  `zls::final_store` (crates/sgx-pipe src/zls.rs).
- zsc, zs, rd: the non-aborting final's store replays through `zls::final_store` for the G 33 /
  G 1 layout; the overflowed render 1 stores are refused by it.
- Tables: `closing_tables.py` format `sgx545-tables`, one per stage, from the kept files alone.

No firmware-derived file is in this directory (nothing for data-private).
