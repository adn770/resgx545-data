# r23-dpm

Round 23's session r23-dpm: the P2 rows of `closing22/plan/rank-round22.md` (sections 2.3, 2.4
and 2.5, session table of section 6), with `closing22/DECISIONS-R22.md` (all (a)) and
`closing23/DECISIONS-R23.md`. Records E1099 (rl: Q038), E1100 (og: Q191, narrow only, R22-3 a)
and E1101 (zn: Q088), after r23-pk's E1096 to E1098. Built with the session kit (resgx545
HACKING.md, "Session kit"), scaffolded by `tools/closing/new_session.py` from resgx545 b2b6bc0d44fc,
data 40abeab5a215. Laptop prefix `r23d`, module E0CC40275493F8AEAD8180B (fork 456404fcffe5,
debugfs `render_final_pb_pages`), run on the road over the travel cable (nothing here assumes
cachix). Safe class only; `#limit 0` everywhere; no `expectfault`; no fault or hang planned.

Tools, all already on the laptop:

- t22b = `~/sgxfive-test-t22b` (sha256 2ae2800a..., resgx545 b2b6bc0 `sgxfive-test.c` e0c5ae5b...,
  built on the laptop by `lead/build_tool22b_laptop.sh`, a byte copy of
  `closing22/k22/build_tool22b_laptop.sh`, bound as
  `data:render/closing-r23-dpm/lead/build_tool22b_laptop.sh`; built line `lead/TOOL22b.built`, a
  byte copy of `closing22/k22/TOOL22b.built`). Every row runs it.
- rt = regtimeline (079f6359, `wraps = true`, no source: a read-only sampler) around rl's and zn's
  rows, with r21-zls's register list (0x0480-0x0490 included, read only).
- t10 (9bedc2d6..., recipe `data:render/closing-r10-st1/lead/build_tool10.sh`): the health fill
  and triangle only.

`bins/pds_bg_pos.bin` and `bins/bg_reload_1024.bin` are E442's own programs, byte copies of
`data:dpm/partial-reload/dpm-partial-reload-green/bins/` (pinned; tests check the bytes),
assembled from resgx545 `probes/dpm/templates/pds_bg_pos.s` and `bg_reload_1024.s` (ours, not
firmware-derived).

## What runs, in order (21 jobs, about 10 minutes of jobs, about 20 with staging and health)

| Stage (record) | Jobs | Rows | Controls (can fail) |
| --- | --- | --- | --- |
| rl (E1099, Q038) | 10 | 0x28 x2 (fit, raised), 0x2c x2 (raised), 0x30 x2, 0x34 x2 (not raised), held out | rl-c1 (E442's -n 1 0x422 reload cell: 207456 triangle, wrong 0 inside, 578976 other), rl-c2 (no reload, 0x28, --keep-target 2: 786432 changed, red 207456, 0xff000080 578976, E1089's zm-28); every row's premise |
| og (E1100, Q191) | 6 | 64x64 flag 0xc at 0x422 x4 (2 fit, 2 held out), at 0x200 (held out) | og-4 (flag 0x4: no owner word in the geo or after copy, both 24576 bytes); every row's geometry kick |
| zn (E1101, Q088) | 5 | load bits 0x0017510e at 0x2e (fit), 0x30, 0x32, 0x34 (held out), none raised | zn-c (E1093's zl-2e-nl form, no load bits); every row's premise and refill line |

Forms (gen/plan.py writes every row; tests/test_plan.py holds them to the kept rows they repeat):

- rl: E1089's zm form, `tri --width 1024 --height 768 -n 2 --geometry 1 --final-pb-pages 0x100
  --keep-going --keep-overflow --wait-ms 20000 --dump-render "$W" --dump-each --words "$W" --regs
  0x0600-0x0750 [--bg-pds "$S/bins/pds_bg_pos.bin:12" --bg-pixel "$S/bins/bg_reload_1024.bin"]
  --keep-target 2 --move 2:96,0`, P by `dbg:render_pb_pages`, premise `ctl:ovf1=1 ctl:ovf2=0
  ctl:thr=0xde`. rl-c1: `-n 1` at 0x422 with the reload. No depth buffer (E1089's 18582-pixel
  reading at 0x30, the plan's not-raised prediction, is a no-depth reading).
- og: E1087's own1 form plus `--ctx2-geometry 1`: `tri --width 64 --height 64 -n 1
  --keep-overflow --wait-ms 20000 --ctx2 --close-first-early --kept-copy "$W" --words "$W"
  --kpoke-render 1:ta:7^=F --ctx2-geometry 1`, `dbg:render_keep=1`. Copies: `kept.closed.1.bin`
  (after the close), `kept.geo.1.bin` (after the second context's geometry kick, before its
  closing render), `kept.1.bin` (after the closing render).
- zn: E1093's zl form (r21-zls) with t22b, its own markers 0xd0230001 to 0xd0230005.

Frozen per stage (predictions/STAGE.tsv; score/score.py's docstring states every rule; window
dwords only, depth rules on the hi region only, never a whole-buffer hash; no param comparison,
so `kitscore.param_hash` is not needed):

- rl, render 2's keep line (`tri 1024x768 #2: target kept, X pixels changed, colours ...`):
  H-RELOAD (X = the red count, colours only red 0xffff0000, render 1's green 0xff00ff00 and the
  sentinel 0xdeadbeef, green > 0) vs H-REPAINT (X > red, no green). Predicted [infer]: H-RELOAD 8
  of 8 (E442: the reload paints each pixel with the target's own texel; with the target kept,
  render 1's colour is that texel). Readings: red = 207456 raised, more when not raised (E1089
  zm-30: + 18582, render 1's rest drawn in the final's red), render 1's line.
- og: H-TAKICK (E631's four words, page 1 dword 0 0x00200047, page 2 dword 0 0x04000417, page 3
  dwords 0 and 1 0x00020001 and 2, in kept.geo.1.bin and kept.1.bin) vs H-RENDEREND (0 in
  kept.geo.1.bin, 4 in kept.1.bin). No lean between them: either decides the kick clause. An
  empty copy is cannot tell (E1085's park race), never a stop.
- zn: H-LOADNODRAW (0.75 at every hi window dword of store.2: the load written back, T2 absent;
  frozen from E1093's zl-2e-ld, post hoc there) vs H-HOSTBITS (0.5 inside T2, 0.75 elsewhere). The
  regime read from ta3d.1.bin dword 38: a row read raised is cannot tell. Predicted [infer]:
  H-LOADNODRAW 4 of 4.

Retire (the fold proposes, the lead confirms): Q038's colour clause if H-RELOAD holds on the
held-out rows with both controls passing; Q088 if H-LOADNODRAW holds on the three held-out rows
with zn-c passing (R22-8 a: "why" and the closed driver's purpose left as fw). Q191 narrows only
(R22-3 a).

## Stops

- rl, zn: a premise off on a geometry row (the kick did not overflow, the final overflowed, 0x0624
  not 0xde, zn: no refill line): rc 24, the stage stops, the next stage runs. rl-c1: render 1
  overflowed: rc 24.
- og: no geometry kick or closing render of the second context, or no copy after its render: rc
  24 (a missing kept.geo.1.bin is the runner's rc 23 first: the session stops). An empty copy
  after the close or the kick: counted, cannot tell, no stop.
- A control without its reading: rc 25 (the session stops). Any unexpected fault, hang or failure:
  rc 4. A FAILED control (the scorer) voids its own stage's headlines; no stage gates another.
- Stop budget: `#limit 0` in every stage, no fault or hang planned.

## Commands

- Offline: `bash tests/run_all.sh` (guard, tests, the library-mock replay, every world).
- Freeze: `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score (Mac): `python3 score/score.py STAGE out/ATT/STAGE` for each stage.

## Mock worlds (mock/world.py)

model (every stage 0: H-RELOAD, H-TAKICK, H-LOADNODRAW), alt (0: H-REPAINT, H-RENDEREND,
H-HOSTBITS), finalovf (rl 24, og 0, zn 24; driver 0), noregs (25: rl-c2 lacks thr), nogeo (23:
no kept.geo.1.bin at og's first row), geoempty (0: every geo copy empty, og cannot tell), fault
(4: og's second row faults).

## Replay vectors (HACKING.md "Replay vectors")

- rl: `refused` (sgx-pipe has no background object reading the target and no partial-render
  colour model; the keep lines are readings for one, tables from the kept text).
- og: `refused` (sgx-sim models no render_keep or kept DPM pages; the owner words per copy are
  readings).
- zn: `refused` (sgx-pipe's `zls::final_store` refuses stores after partial renders; the fold
  names the SIM_UNMODELLED entry).
- Tables: `closing_tables.py` format `sgx545-tables`, one per stage, from the kept files alone.

## Deviations from the plan

- zn's held-out P are 0x30, 0x32 and 0x34, not 0x30, 0x34 and 0x38: at 0x38 the triangle's kick
  does not overflow (E625: P - 0x22 = 22 >= U 19), so the row would stop on its premise.
- rl has no depth buffer (E1089's zm form): the plan's "r21's zl form" names the geometry, final
  and move; its not-raised prediction (E1089's 18582) is a no-depth reading.
- H-RELOAD is frozen as "every changed pixel became the final's red, render 1's green kept", not
  as E442's 207456-pixel T1 count: after a raised kick the final draws no rest of T1 (E1089), so
  T1 is whole only where the partial render drew it [infer].

No firmware-derived file is in this directory (nothing for data-private).
