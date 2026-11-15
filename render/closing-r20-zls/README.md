# r20-zls

Round 20's session S1 r20-zls (plan `closing20/plan/rank-round20.md` section 3; decisions in
`closing20/DECISIONS-R20.md`: R20-1, 2, 4, 5, 6, 7 (a), R20-3 (b); records E1088 (zc, zr), E1089
(zm), E1090 (zq): Q088, Q038, Q107), built with the session kit (resgx545 HACKING.md, "Session
kit"), scaffolded by `tools/closing/new_session.py` from resgx545 c0f8c41fbbf9, data
ba3990f01eb2. Laptop prefix `r20z`, module E0CC40275493F8AEAD8180B (fork 456404fcffe5, debugfs
`render_final_pb_pages`), run on the road over the travel cable (nothing here assumes cachix).
Tools, all already on the laptop: t18b = `~/sgxfive-test-t18b` (sha256 58e79855..., resgx545
ec50498, recipe `lead/build_tool18b.sh`, a byte copy of `closing18/k18/build_tool18b.sh`, bound
as `data:render/closing-r19-k0/lead/build_tool18b.sh`, built line `lead/TOOL18b.built`); rt =
regtimeline (079f6359, `wraps = true`, no source: a read-only sampler); t10 (9bedc2d6..., the
health fill and triangle only). Every row runs t18b under rt with r19-dpm's register set plus
0x0480-0x0490 (CR_ISP_ZLSCTL, the load and store bases, the stencil bases; read only, R20-7 a).
Safe class only; `#limit 0` everywhere; no `expectfault`; no tool change.

## What runs, in order (18 jobs, about 6 minutes of jobs, about 10 with staging)

| Stage (record) | Jobs | Rows | Controls (can fail) |
| --- | --- | --- | --- |
| zc (E1088) | 3 | - | zc-geo (E1081's dz-a-nl28-1 unchanged: the store after the final is render 1's in the window, one partial render), zc-nl, zc-ld (E628's -n 1 0x422 dl cells: sidx 0 / 1); zregs (a reading control) |
| zr (E1088, Q088, Q038) | 8 | 0x28 no-load x2, load (fit); 0x2c no-load, 0x28 no-load unmoved, 0x30 no-load, load (held out); 0x28 E336's 0x0011700a (reading) | every row's premise and its refill line |
| zm (E1089, Q038) | 3 | the moved final without depth at 0x28 (fit), 0x2c, 0x30 | every row's premise |
| zq (E1090, Q107) | 4 | E629's ramp G 33 / G 1 at 0x44 (fit) and 0x4c (held out) | every row's premise |

Every geometry row: `tri --width 1024 --height 768 -n 2 --geometry 1 --final-pb-pages 0x100
--keep-going --keep-overflow --wait-ms 20000 --dump-render "$W" --dump-each --words "$W" --regs
0x0600-0x0750`, P by `dbg:render_pb_pages`, `expectdiff`, its premise `ctl:ovf1=1 ctl:ovf2=0
ctl:thr=0xde` (run/hooks.sh), `--depth-ctl-next` on every depth row (else the tool refills before
the final). zr's form: `--poke blk:1=0x00400200 --depth --depth-ctl C --depth-ctl-next C
--depth-pages 0x340 --depth-fill 0x3f800000 --depth-store --depth-store-fill M --refill
2:depth=0x3e800000 --move 2:96,0` (`ctl:refill=1`: the tool printed its refill line).

Frozen per stage (predictions/STAGE.tsv, gen/plan.py; score/score.py's docstring states every
rule, applied to window dwords only, never a whole-buffer hash): zr H-LOADBASE, H-STOREBASE,
H-NOSTORE, H-HOSTBITS (the regime read from ta3d.1.bin dword 38 per row; a row that is not raised
is scored by H-HOSTBITS's form under every model); readings H-RDREG vs H-EDMPATCH and 0x0480 bit
19 (void if zregs fails); zm H-REPAINT vs H-HOLES; zq H-NR-PLAIN vs H-AFTERPR. Predicted [infer]:
zc passes (repeats of E628 and E1081); zr H-NOSTORE on the four raised rows and H-HOSTBITS on the
two 0x30 rows (E1081's forms), which retires Q088 (R20-2 a); zm H-REPAINT 3 of 3 (r19's finals
painted every pixel); zq H-NR-PLAIN 4 of 4 (E1081's plain store at 0x30). zregs: 0x0480 reads
rd:11 (rd:53 0x480 has bit 4 clear, E169), the bases the tool's addresses [infer].

zm (deviation): the library writes its sentinel into the target before every kick (libsgxfive
render.c, `sgxfive_render_tri_flags`), so the partial render's colour can never reach the final's
check; the plan's rival H-KEEP (wrong outside = |T1 \ T2|, 50162 pixels) cannot occur on this tool.
zm reads only whether the final paints every target pixel (H-REPAINT) or leaves sentinel pixels
(H-HOLES). Q038's colour clause stays open (R20-3 b).

## Stops

- zc: a control off (hook) stops zc (rc 24) and ends the session (`on_stop = "end"`); a control
  the scorer fails (the store window) closes the gates of zr, zm and zq. zregs never stops.
- Any premise off on a geometry row (the final overflowed, 0x0624 not 0xde, no overflow in the
  kick, no refill line in zr): rc 24, the stage stops, the next stage runs.
- A control without its reading: rc 25 (the session stops). Any unexpected fault, hang or
  failure: rc 4.

## Commands

- Offline: `bash tests/run_all.sh` (guard, tests, the library-mock replay, every world).
- Freeze: `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score (Mac): `python3 score/score.py STAGE KEPT_DIR ROOT` for each stage (zr reads zc's zregs
  from ROOT/zc).

## Mock worlds (mock/world.py)

model (every stage 0), finalovf (zc 24, the session ends), noregs (25), ctloff (zc 24, the
session ends), storeoff (zc 0, its scorer control fails, zr, zm, zq skipped by their gates),
norefill (zr 24, zm and zq run), zregsoff (no stop: the register readings void).

## Replay vectors (HACKING.md "Replay vectors")

- zc: zc-nl and zc-ld's -n 1 stores replay through `zls::final_store` (crates/sgx-pipe
  src/zls.rs); zc-geo `refused` (a store after a partial render).
- zr, zm, zq: `refused` (sgx-pipe's `zls::final_store` refuses stores after partial renders; the
  fold names the SIM_UNMODELLED entry); the register timelines of 0x0480-0x0488 are readings for
  sgx-sim's ZLS register model, if one lands.
- Tables: `closing_tables.py` format `sgx545-tables`, one per stage, from the kept files alone.

No firmware-derived file is in this directory (nothing for data-private).
