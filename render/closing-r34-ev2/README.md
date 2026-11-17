# r34-ev2

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main c60afd788d2c (r34-ev's fold merged; the T1 kit
forms `@snap0`, `@cal:STAGE`, `session.py lint`) and resgx545-data main 0aeeedfd7144, module
srcversion 7CE8E38EDB97FC5EA4F6C90 (N1), laptop prefix `r34f`, travel cable (`host_key_alias =
"cedar"`). **Safe class**: every stage `#limit 0`, no expectfault, kreg, idle or noreset, no planned
fault or hang; the one knob is debugfs `render_pb_pages` (restored to 0x422 after every job);
regtimeline only reads through /dev/mem. `python3 kit/session.py lint .` prints "lint: clean".
Records reserved: **E1141** (Q036: c0, d1 or d1s, p0, p1), **E1142** (Q111: e0, e1).

## Why

The follow-up of r34-ev (E1137, E1138). Q111: r34-ev's post hoc reading, CR_EVENT_STATUS bit 1
(DPM_OUT_OF_MEMORY_MT) in 6 of 6 overflowing rows at the PBs of 0xe2 and 0x82 pages and in 0 of 5
at 0x2b6 and 0x1c2, is frozen here as a held-out hypothesis with four new rows a size, against bit
1 by chance; and a copy's bit 18 (10 of 14 copies) against its form, six rows of each. Q036:
r34-ev's d1 never ran (d0 sampled 0x0660 + 0x0748 at 4.1 us, above the bound for E1057's 4 us bit
2 pulse); here 0x0748 is sampled alone and CR_DPM_3D_PAGE_COUNTS (0x0660) alone, each in stages of
its own with its own calibration.

## What runs

Every job after the kit's reset, `regtimeline 0 0.005 REGS -- TOOL ...` (`ivl` = end / samples), in
r34-ev's three forms (E1137: 34 of 34 jobs without a fault on this module): **ovf**, t10
(`~/sgxfive-test-t10`, 9bedc2d6..., source a581c06) `probe --tri pixel --width 3072 --height 2048
--vertices 1500 $S/bins/p1139-green.bin` with `dbg:render_pb_pages=P expect:rc3-overflow` (0x422
no partial render, rc 0; 0x2b6, 0x1c2, 0xe2, 0x82 labelled 1, 2, 4, 7, rc 3); **copy**, t30
(`~/sgxfive-test-t30`, b5ea288d..., source 42c4de7) `copy`, 64 x 32; **lcopy**, t30 `copy --width
256 --height 256 --src-stride 1024 --dst-stride 1024`.

| stage | rows | registers | what |
|---|---|---|---|
| e0 | 6 controls | 0x012c | calibration: ovf 0x422, copy, lcopy, two each |
| e1 | 30 (4 controls) | 0x012c | ovf 0x422 first and last; 4 sizes x4 shuffled; 6 copy, 6 lcopy |
| c0 | 3 controls | 0x0748 | calibration: ovf 0x422 x3 |
| d1 | 10 (2 controls) | 0x0748 | ovf 0x422 x2, 4 sizes x2 reversed; when c0's median <= 3890 ns |
| d1s | 10 (2 controls) | 0x0748 | the same rows when c0's median is in (3890, 12000] ns |
| p0 | 2 controls | 0x0660 | calibration: ovf 0x422 x2 |
| p1 | 10 (2 controls) | 0x0660 | the rows of d1 |

61 jobs run (d1 and d1s exclude each other). r34-ev ran 34 jobs in about 5.5 minutes of stages
(00:10:59 to 00:16:30), so about 10 to 15 minutes, 30 at most. Gates (score.py gate): a stage runs
when its calibration ran, no control there FAILED, each form a later control cites has a window
(median +-25 %, every row inside), and for d1 / d1s the median's side of 3890 ns.

The bound: E1057's bit 2 clears are 3890 to 4090 ns wide, so a sampler at most 3890 ns apart sees
every one; r34-ev's d0 read 4095 and 4168 ns with two registers, and 0x0748 alone read 1.66 to 1.70
us on B60AB0B4 (E1057). Whether 0x0748 alone samples under 3890 ns in this module's job window is
not known: c0 measures it. If it does not, d1s narrows with what a coarser sampler keeps (a 4 us
pulse is still seen with a probability near width / interval, so bit 2 summed over the stage, bit
4's single clear and its length, bit 3's 20 to 30 us clears).

## Hypotheses (frozen: predictions/*.tsv from gen/make.py; every non-calibration row held out)

Fit sets read with the scorer's analyse() (gen/fit.py, gen/fit.txt): r13-dpm pr2, r15-dpm pr4,
E547's event timelines and r34-ev's kept rows. Controls: the first sample of 0x012c and 0x0660 =
the row's snap0 (@snap0), of 0x0748 = 0x1f (not snapshotted; 20 of 20 kept rows); the kept image
or the copy's own check; the interval in the calibration's window (@cal); in c0, d1, d1s the 0x422
rows read no bit 2 clear (E1057's control).

- e1: **H-OOM-SMALL** (per row: bit 1 at 0xe2 and 0x82, none at 0x2b6 and 0x1c2; the stage: 0 of 8
  rows at 0x2b6/0x1c2) against **H-OOM-CHANCE** (2 or more of those 8 rows show it). **H-C18-LARGE**
  (5 or 6 of 6 large copies end with bit 18, at most 3 of 6 plain) against **H-C18-ANY** (both 2 to
  6 of 6, within 2). **H-COPY-NO0**, **H-THR-NEVER**, **H-IMG**.
- d1: r34-ev's d1 hypotheses unchanged (H-B2PR against H-B2-NONE, H-B4-ONE against H-B4-PR,
  H-B4-LEN, H-B1-PR, H-B3-LONG against H-B3-SHORT, H-B0-N). d1s: H-B2PR (summed) against
  H-B2-NONE, H-B4-ONE against H-B4-PR, H-B4-LEN, H-B3-LONG against H-B3-SHORT.
- p1: **H-PC-ONCE** against **H-PC-RENDER**, **H-PC-FIN** (0x70305, 0x60294, 0x401a0, 0x200c0;
  at 0x82 [infer] low half 0x60, high half 0 to 2).

Caveat frozen with H-OOM-SMALL: 0x012c alone sampled at 3.1 to 3.9 us in r34-ev, about one bit 1
pulse width (about 4 us); a row at 0x2b6 or 0x1c2 without bit 1 does not show the pulse cannot
be under a sample. H-OOM-CHANCE is the hypothesis that would show it.

## Stops

`#limit 0`: any fault or hang stops the stage (rc 4) and the driver. hook_check stops a stage (rc
24, the next stage runs) on a row without its whole timeline, a probe without its image line, or
a copy without `copy: ok` and diff 0. A control without its reading stops the stage (rc 25).

## Mock worlds

`model` (d1 opens), `slow748` (d1s opens), `vslow748` (neither), `noimg` (the probe's calibrations
stop, their stages skipped), `nocopy` (e0 stops, e1 skipped). The library-mock replay runs every
wrapped row of t10 and t30.

## Replay vectors

No vectors table (closing_tables.py has no timeline kind): every stage refused as a table, the
records go to crates/SIM_UNMODELLED.toml as E1137 and E1138 did. Nothing firmware-derived.

## Commands

- Offline: `bash tests/run_all.sh`. Regenerate: `python3 gen/make.py`, `python3 gen/fit.py`.
- Run (the lead): `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE out/ATT/STAGE out/ATT`; a gate: `python3 score/score.py gate
  STAGE out/ATT`.
