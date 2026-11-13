# r13-tex

Round 13's session r13-tex (closing13/plan/rank-round13.md sections 2 and 3, decision R13-1 (a) of
closing13/DECISIONS-R13.md), built with the session kit (resgx545 HACKING.md, "Session kit"),
scaffolded by `tools/closing/new_session.py` from resgx545 05b7039ee021 (kit/ is that commit's
blobs), data 75d01ee20311. Generators: gen/make.py with gen/srgb.py, gen/addr.py, gen/t3.py and
gen/sb.py (r10-tex's gen/tex.py, gen/texprog.py and gen/pins.py copied, resgx545-data
`render/closing-r10-tex`); every repository file they read is read at the frozen commits
(gen/pins.py) and pinned. Records E1025 (srgb3), E1026 (addr4), E1027 (t3c), E1028 (sb12).

## What runs

Four stages in this order, 53 jobs, laptop prefix `r13t` (files under `~/scratch/r13t/`), one
binary: `~/sgxfive-test-t10` (t10, sha256 9bedc2d6...), bound by source to resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., `TOOLSRC.sha256`), recipe
`data:render/closing-r10-st1/lead/build_tool10.sh` (the `built` line of FROZEN.commits). The rows
name it t10 (sb12 and the health pair) or t10p (the probe fills, "Deviations" 1). Module
B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is written. Safe
class: no planned fault, no expect-fault row, no held reset, `#limit 0` on every stage.

| stage | plan | question | jobs | what is frozen | record |
|---|---|---|---|---|---|
| srgb3 | srgb3 | Q282 | 9 | FTZ-OUT against FTZ-IN, R10-BF11, FTZ-T64; TRI-OUT against TRI-NOFLUSH, TRI-LO | E1025 |
| addr4 | addr4 | Q177 | 12 | H-MAX against H-W, H-H (texels and dwords on u16); uv5 per region, corner bases | E1026 |
| t3c | t3c | Q078 | 16 | B11-LEVEL0 / NORMAL / BIAS, B12-CAPLVL / CHAINLAST / ADDR / BIAS / NORMAL, AS-00 / 01 / 11, H-FOOT / H-TAP | E1027 |
| sb12 | sb12 | Q046 | 16 | H-FIXED (inset) against H-O0; H-FIXED-PX against H-SHIFT on mode 0 | E1028 |

- **srgb3** (`tables/srgb3.txt`, gen/srgb.py). r10-tex's srgb2 forms (E723's g-bl-st form,
  strided, injected bytes, two half channels a pixel from bytes 0 and 1). Frozen rules: closing11
  c2's `rule_b.py` (resgx545-data `cited/closing11/plan/c2-texture/rule_b.py`, sha256
  84bd4264..., pinned and loaded from its frozen bytes). Controls: E723's g-bl-st-a and p1132's
  an-t0b27 (E1016's held-out job), their kept images. Held out: x1 (the x stage alone, ky 0, kx 0
  to 63 on every pixel row, channel 0 corners (0, 1), channel 1 (1, 0): kx 11 and 12 predicted
  flushed, 13 and 14 kept), x2 (bytes 1 to 3), y1 and y2 (the y stage alone, kx 0, ky 0 to 63: the
  FTZ-IN / FTZ-OUT separation, 768 and 484 pixels), sub2 (both stages on bytes 0 to 3), tri
  (trilinear: a twiddled 16 x 16 sRGB chain on the counting fill, smp2dreplace at LOD 1.25, T0
  bit 9; TRI-OUT a third stage of the same rule between the levels [infer]), x1r (the end
  replicate). FTZ-T64 (a threshold at 6.4e-5, the kept bound) parts on 64 pixels of x1.
- **addr4** (`tables/addr4.txt`, gen/addr.py). Twiddled textures at page 12 of a 32-page named
  scratch (T2 0x5CAFC000, `--scratch-pages 32`). Controls: E1000's addr3-16x64-u4 (its published
  program and kept image) and E565's bd-uv5 16 x 16 (p1132's program, base 0, its kept image).
  Swept u (r10-tex's form): 32 x 64, 8 x 64 and 128 x 32 in modes 4 and 6, 32 x 64 in mode 7, and
  a 16-bit (T1 format 9) 32 x 64 in mode 4 (texels against dwords; `h:` tokens). H-MAX parts from
  H-W on every H > W row (2048 of 2048) and from H-H on 128 x 32. uv5 (u and v in mode 5, swept
  past both ends) at 64 x 16 and 16 x 64: every region holds pixels; IN, LR and AB with M, W or H
  (M parts W at 16 x 64, H at 64 x 16), the corners CO-WH2 ((W + H) / 2 = 40) against CO-12M4 (28)
  and CO-12W4 (28 or 16), 512 and 768 corner pixels.
- **t3c** (`tables/t3c.txt`, gen/t3.py). E564's tx-aniso chain form with smp2dreplace. Control:
  E564's an-t3b11 (its kept image). Bit 11 clear at LOD 0 to 6 (LEVEL0 parts NORMAL at LOD 1 to 6,
  BIAS at 4 to 6), bit 12 with T0's max level 3 and 5 at LOD 0, bits 12:11 = 10 at LOD 2, a
  32 x 32 chain with bit 11 (LOD 3) and bit 12 (LOD 0: the chain's last level against the
  constant dword 5460), bit 11 with mips off (T0 top 0: every model reads level 0, the field's
  check). Bit 14 under a bilinear sample on a strided 64 x 32, then its bit-clear reference (the
  reference gates the row). Level images: E561's tile law over E722's offsets with texmodel's
  blend, `t:` tokens within 1 a byte above level 0 (tests: E564's an-t3b11 exact, an-ctl's levels
  3 and 4 within 1, 2048 of 2048).
- **sb12** (`tables/sb12.txt`, gen/sb.py). E383's form (`probe --tri pixel`, eot_plain, colours
  0xc0804020 and 0x13579bdf, E383's published bins) with sideband 0x1200 | mode. Controls:
  E383's 0x208 colour 0 (its kept image) and the mode 0 colour 0 replicate (inset). Replicates:
  modes 1 to 6 on colour 0 (E383's own rows again). Held out: modes 0 to 6 on colour 1 and mode 0
  on colour 0 with the triangle moved (4, 4) pixels (`--tri-v`).

## Predictions and what each verdict does

Frozen before the run: `predictions/STAGE.tsv` and the per-pixel files `predictions/STAGE/`
(sha256 in the tsv; `PREDICTIONS.sha256` at the freeze), sb12's word sets
`predictions/sb12/words-mN.txt`. Expected, not frozen:

- srgb3: FTZ-OUT on the six strided rows (Q282's y-stage flush and the threshold 2^-14 decided;
  retire per R13-9 if the controls pass, the negative-values clause void [infer]); TRI-OUT or
  TRI-LO on the trilinear row (the "other filters" clause; TRI-NOFLUSH parts on 2 pixels only).
- addr4: H-MAX on the seven swept rows (H-MAX-TX on u16) and the M forms on uv5; the corner base
  is the open choice (CO-WH2 or CO-12M4); Q177 retires per R13-9 if one holds.
- t3c: B11-LEVEL0 on the nine bit-11 rows; bit 12 CAPLVL or CHAINLAST (c8's "last level" in its
  two readings); 10 any; bit 14 H-FOOT or H-TAP. Q078 narrows (F1 in r13-flag runs the twiddled
  bit 14).
- sb12: H-FIXED on the 14 held-out and replicate rows (E383's reading), H-FIXED-PX on mode 0.
  Q046 narrows (bit 11 stays for F2).

## Stops (kit/run_stage.sh, kit/session.py)

Any fault or hang stops the stage and the session (rc 4 / 6; none in E1000, E565, E564, E723,
E1003 or E383's jobs; every rival's read is inside the mapped scratch, tests/test_gen.py); a
control without its pixel rows stops the session (rc 25); the second row of a stage without its
pixel rows (32, or 64 on sb12) stops that stage (rc 24, run/hooks.sh) and the driver goes on;
less than 300 MiB free on ~ (rc 22). Stop budget: `#limit 0` on all four stages, 0 faults and 0
hangs expected.

Expected time: probes under 2 s each plus the runner's reset, snapshot and health (about 6 s a
job): about 5.5 minutes of jobs, about 9 minutes with staging and preflight; stage alarms 10, 15,
20 and 20 minutes.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest, numpy), which the offline
  tests use unless `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Generator: `python3 gen/make.py --check` (tables, predictions and programs current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).

Mock worlds (mock/world.py): model (every stage 0, the tested models held), alt (the rivals:
every stage 0, the rows FAILED), nopix (t3c stops at its second row without pixels, rc 24; sb12
runs), ctlnopix (srgb3's control without pixels: the premise stops the session, rc 25), fault
(addr4's first held-out row faults: rc 4), hang (sb12's first held-out row does not return: rc 6).
A fill program whose reads pass the row's scratch faults in every world.

## Deviations from the plan

1. **Two names for t10.** The kit's library-mock replay (kit/session.py, since 287031c) fails
   every probe of a program of ours: libsgxfive's mock at a581c06 runs a copy (`probe --coords`)
   only with its own copy shader (mock.c: "an unknown program", a fault), so all 37 probe-fill
   rows end `failed: job faulted` there, a limit of the mock, not a refusal of the tool or
   kernel. The probe-fill rows name t10p, the same binary (same path and sha256) with a
   `no_source` reason; tests/test_libmock.py replays all 37 on the same library mock (built by the
   kit from t10's pinned source) and requires exactly that end: the argv accepted, no usage line,
   no `job: rejected`, one `failed: job faulted` line; its control (the same row with
   `--scratch-pages 99`) is the tool's usage refusal. sb12's 16 rows (t10) pass the kit's replay.
   The kit itself needs the fix (FOLD-NOTES.md).
2. **srgb3 channels 2 and alpha** are not run: this format returns bytes 0 and 1 as two halves in
   r10, and the second output dword's read-out (E723's tx_map_r11 rows) is not decoded, so no
   frozen prediction exists for bytes 2 and 3 (H-ALPHALIN is not tested). In their place x2 and
   y2 (bytes 1 to 3, both directions) and sub2; channel 1 is in every row. The x stage row covers
   kx 0 to 63 in one job (the plan's kx 11 to 14 and every other weight). FTZ-T64 is added as the
   threshold's rival [infer].
3. **addr4 mode 5** runs u and v both in mode 5 (the uv5 form), so the corners, above and below
   are read; the plan's "type" clause is answered from kept data without a row: E565's strided
   bd-st-u4 to u7 read as bd-st-u0, 2048 of 2048 each (type 6 ignores u modes 4 to 7), and no
   kept job of type 1, 3 or 4 ran them (E910, E940 do not). The u16 row's tile law in texels is
   [infer].
4. **t3c level images** come from E561's tile law, not texmodel's address: texmodel.py's plain
   Morton order is not E561's above 16 a side (it misses E564's an-t3b11 at pixel 16). The bit-14
   bilinear pair is one row and its reference (the plan's 2 jobs); H-FOOT and H-TAP part only
   through byte carries (1011 of 2048 pixels by more than 2 a byte: the move is linear in u, so
   the per-tap and footprint means agree where no byte wraps) [infer]. Bit 12's "last level" is
   frozen in both readings (CAPLVL, CHAINLAST) beside B12-ADDR.
5. **sb12 scoring by word set.** E383's two bit-12 runs were both colour 0 (its two bins are
   one file) and differ run to run on up to 256 of 4096 pixels (mode 1), so H-FIXED is the word
   set (inset >= 4055), not E383's image; H-FIXED-PX (mode 0, whose runs were equal) is scored
   too. The moved row is colour 0, so only the place changes.

## Replay vectors (HACKING.md "Replay vectors")

| stage | vectors table (closing_tables.py, `sgx545-tables`) | replay |
|---|---|---|
| srgb3 | `vectors/closing/r13-tex/srgb3.table.json` (corners, weights, kept halves) | `crates/sgx-sim/src/tex.rs` (the flush since E1016) for the strided rows; the trilinear row refused unless the fold lands the level lerp on halves |
| addr4 | `vectors/closing/r13-tex/addr4.table.json` (pixel, texel, kept dword, read less REPEAT) | refused: sgx-sim refuses u modes 4 to 7 (Q177) unless the fold lands H-MAX and the mode 5 regions |
| t3c | `vectors/closing/r13-tex/t3c.table.json` (pixel, LOD, T3, kept dword) | refused: no path models T3 bits 11 and 12 or bit 14 filtered (tex.rs) unless the fold lands them |
| sb12 | `vectors/closing/r13-tex/sb12.table.json` (mode, colour, word set, inset) | refused: sgx-pipe pbe.rs does not model sideband bit 12 (words not one image run to run) |

The replays read only kept files, the frozen predictions (session files) and session.toml's pins.

## Data

No file here derives from the closed firmware: everything is publishable (resgx545-data
`render/closing-r13-tex`). bins/*.bin are our own probe programs (assembled from the pinned p1141
template by usse-asm) or published bins of earlier sessions (E1000, E565, E383), not tools.
