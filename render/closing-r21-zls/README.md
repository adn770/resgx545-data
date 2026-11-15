# r21-zls

Round 21's session S1 r21-zls (plan `closing21/plan/rank-round21.md` section 3; decisions in
`closing21/DECISIONS-R21.md`: R21-1 (a), the rest the plan's recommendations; records E1093 (zc,
zl), E1094 (zw), E1095 (zz), E1096 spare: Q088, Q107), built with the session kit (resgx545
HACKING.md, "Session kit"), scaffolded by `tools/closing/new_session.py` from resgx545
fa073da2ef13, data 99a8cda42679. Laptop prefix `r21z`, module E0CC40275493F8AEAD8180B (fork
456404fcffe5, debugfs `render_final_pb_pages`), run on the road over the travel cable (nothing here
assumes cachix). Tools, all already on the laptop, bound as r20-zls binds them: t18b =
`~/sgxfive-test-t18b` (sha256 58e79855..., resgx545 ec50498, recipe `lead/build_tool18b.sh`, a byte
copy of `closing18/k18/build_tool18b.sh`, bound as
`data:render/closing-r19-k0/lead/build_tool18b.sh`,
built line `lead/TOOL18b.built`); rt = regtimeline (079f6359, `wraps = true`, no source: a
read-only sampler); t10 (9bedc2d6..., the health fill and triangle only). Every row runs t18b
under rt with r20-zls's register set (0x0480-0x0490 included, read only). Safe class only; `#limit
0` everywhere; no `expectfault`; no tool change; no param hash anywhere (no param comparison in
this session, so `kitscore.param_hash` is not needed).

## What runs, in order (16 jobs, about 6 minutes of jobs, about 15 with staging and health)

| Stage (record) | Jobs | Rows | Controls (can fail) |
| --- | --- | --- | --- |
| zc (E1093) | 2 | - | zc-r25 (E1088's zr-28-nl-1 byte for byte: store.2 = 0.25 at all 589824 hi window dwords, store.1 = depth.1 there), zc-nl (r20's E628 dl cell: ovf1 0, sidx 0); zregs2 (a reading control) |
| zl (E1093, Q088) | 7 | 0x28 no-load (fit); 0x24, 0x2c no-load, 0x2a load (raised, held out); 0x2e no-load, 0x2e load, 0x34 no-load (not raised, held out) | every row's premise and its refill line |
| zw (E1094, Q088) | 3 | E336's 0x0011700a at 0x2c (raised) and 0x2e (not), E1082's G 1 0x0017100c at 0x28 | every row's premise and its refill line |
| zz (E1095, Q107, optional) | 4 | E629's ramp at 0x24, 0x38 (raised), 0x3c, 0x50 (not raised), all held out | every row's premise |

The common form (r20-zls's zr): `tri --width 1024 --height 768 -n 2 --geometry 1 --final-pb-pages
0x100 --keep-going --keep-overflow --wait-ms 20000 --dump-render "$W" --dump-each --words "$W"
--regs 0x0600-0x0750 --poke blk:1=0x00400200 --depth --depth-ctl C --depth-ctl-next C
--depth-pages 0x340 --depth-fill 0x3f800000 --depth-dump "$W" --depth-store --depth-store-fill M
--refill 2:depth=R --move 2:96,0`, R = 0x3f400000 (0.75) in zl and zw, 0x3e800000 in zc-r25. zz
is r20-zls's zq form (E629's ramp, G 33, no refill, no move). P by `dbg:render_pb_pages`, every
row `expectdiff` with its premise `ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0xde` (+ `ctl:refill=1`).

Frozen per stage (predictions/STAGE.tsv, gen/plan.py; score/score.py's docstring states every
rule; window dwords only, depth rules on the hi region only, never a whole-buffer hash):

- zl: raised rows H-LOADTEST (0.5 inside T2, 0.75 elsewhere) vs H-LOADNOTEST (0.75 everywhere);
  not-raised rows H-HOSTBITS (load: as H-LOADTEST; no load: 0.5 inside T2, 0.5 or 1.0 in T1 \ T2,
  1.0 elsewhere). The regime read from ta3d.1.bin dword 38, not the label. Predicted [infer]:
  H-HOSTBITS on the three not-raised rows (E1088's 0x30 rows at 0.25); the raised rows pick one
  of the two at zl-28-nl (fit) and hold it on the three held out (no prediction between them).
- zw (and zl's rows): H-PRMASK (>= 80 % of the partial-render 0x0480 samples read rd:11 |
  0x000c4000, the rest rd:11) vs H-PR1419 and H-OTHER; predicted H-PRMASK 10 of 10 (E1088's four
  words, look.out). Void unless zregs2 (H-OFFS) passes on zc-r25.
- zz: H-ZCOUNT (zero window dwords of tile rows 0-11 in depth.2: 184320 raised, 118784 not, none
  signed) vs H-ZP; predicted H-ZCOUNT 4 of 4 [infer].

Retire Q088 (R21-2 a) only if zc passes, the zl-28-nl pick holds on the three held-out raised
rows, H-HOSTBITS holds on the three not-raised rows and H-PRMASK holds on zw's three and zl's
seven with zregs2 passing.

## Stops

- zc: a control off in the hook (premise, refill, sidx) stops zc (rc 24) and ends the session
  (`on_stop = "end"`); a control the scorer fails (the hi store window) closes the gates of zl,
  zw and zz. zregs2 never stops.
- Any premise off on a geometry row (the final overflowed, 0x0624 not 0xde, no overflow in the
  kick, no refill line): rc 24, the stage stops, the next stage runs.
- A control without its reading: rc 25 (the session stops). Any unexpected fault, hang or
  failure: rc 4. Stop budget: `#limit 0` in every stage, no fault or hang planned.

## Commands

- Offline: `bash tests/run_all.sh` (guard, tests, the library-mock replay, every world).
- Freeze: `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score (Mac): `python3 score/score.py STAGE out/ATT/STAGE out/ATT` for each stage (zl and zw read
  zc's zregs2 from ROOT/zc).

## Mock worlds (mock/world.py)

model (every stage 0), finalovf (zc 24, the session ends), noregs (25), ctloff (zc 24, the session
ends), storeoff (zc 0, its scorer control fails, zl, zw, zz skipped by their gates), norefill (25:
zc-r25 lacks its refill reading), zregsoff (no stop: the H-PRMASK verdicts void).

## Replay vectors (HACKING.md "Replay vectors")

- zc: zc-nl's -n 1 store replays through `zls::final_store` (crates/sgx-pipe src/zls.rs); zc-r25
  `refused` (a store after partial renders).
- zl, zw, zz: `refused` (sgx-pipe's `zls::final_store` refuses stores after partial renders; the
  fold names the SIM_UNMODELLED entry); the 0x0480-0x0488 timelines are readings for sgx-sim's ZLS
  register model (H-PRMASK, H-OFFS), if one lands.
- Tables: `closing_tables.py` format `sgx545-tables`, one per stage, from the kept files alone.

No firmware-derived file is in this directory (nothing for data-private).
