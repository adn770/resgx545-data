# r34-ev

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main fd916fedc118 (the T1 kit forms of c6d17ec:
`@snap0`, `@cal:STAGE`, `session.py lint`) and resgx545-data main 9a809796f99d, module srcversion
7CE8E38EDB97FC5EA4F6C90 (N1), laptop prefix `r34e`, travel cable (`host_key_alias = "cedar"`).
**Safe class**: every stage `#limit 0`, no expectfault, no kreg, no idle, no noreset, no planned
fault or hang; the one knob is debugfs `render_pb_pages` (restored to 0x422 after every job);
regtimeline only reads through /dev/mem. Records reserved: **E1137** (Q111: e0, e1, e2c, e2),
**E1138** (Q036: d0, d1). Plan: `closing29/plan/rank-round34.md` sections 1, 3.3, 3.4 (R34-2 a).

## Why

Q111 (platform, high) asks which event sets each bit of CR_EVENT_STATUS (0x012c) and
CR_EVENT_STATUS2 (0x0118); its open parts this session reaches are the DPM bits in an overflowing
render (E547's partial jobs show 13, 12, 5, 1, 0; no bit 3, E771) and the events of transfers
other than the fill. Q036 (vdm, medium) asks what 0x0748 holds bit by bit and what
CR_DPM_3D_PAGE_COUNTS' (0x0660) high half is; E1057 saw bit 2 clear in 4 us pulses at partial
renders, sampling 0x0748 alone at 1.7 us. Neither question can retire safely (Q111's host-clear
clause, Q036's builder-fault clause): this session narrows both.

r30-evst and r33-tim voided whole stages on remembered premises (E1116, E1131). Here every
control premise is read: a register control is `@snap0` (the row's own snapshot; 0x0748, which
the kit does not snapshot, keeps 0x1f, the first sample of 18 of 18 kept overflow rows of E1032
and E1057), an interval control is `@cal:STAGE`, the job-window interval a calibration stage
measured on the exact register set in the same job forms; `python3 kit/session.py lint .` prints
"lint: clean".

## What runs

Every job after the kit's reset under regtimeline (`rt`, `~/regtimeline`, sha256 079f6359...),
`0 0.005 REGS -- TOOL ...` (TOTAL 0: sampling lasts as long as the command, after a 5 ms lead;
`ivl` = end / samples). Three job forms, each a past session ran without a fault:

- **ovf**: t10 (`~/sgxfive-test-t10`, sha256 9bedc2d6..., source a581c06) `probe --tri pixel
  --width 3072 --height 2048 --vertices 1500 $S/bins/p1139-green.bin` with `dbg:render_pb_pages=P
  expect:rc3-overflow`: P 0x422 completes (rc 0, no partial render), 0x2b6, 0x1c2, 0xe2, 0x82
  overflow (rc 3) after 1, 2, 4, 7 partial renders (the label, not a reading). The exact form of
  r13-dpm pr2 (E1032) and r15-dpm pr4 (E1057): 18 of 18 rows, no fault, on modules E0CC4027 and
  B60AB0B4. Not yet run on 7CE8E38E (the render path is unchanged by N1 [infer]: lead check 3).
- **copy**: t30 (`~/sgxfive-test-t30`, sha256 b5ea288d..., source 42c4de7) `copy`, 64 x 32.
- **lcopy**: t30 `copy --width 256 --height 256 --src-stride 1024 --dst-stride 1024`, the large
  copy (plan: "a large copy's events"; t30's `--large-copy DIR` is the vm_large dump of Q109, not
  a size, so it is not used). A size no record ran; libsgxfive checks it (SGXFIVE_TEX_MAX 4096,
  stride at most 0x8000) and the library-mock replay takes it.

| stage | rows | registers | what |
|---|---|---|---|
| e0 | 6 controls | 0x012c | calibration: ovf 0x422, copy, lcopy, two each |
| e1 | 16 (4 controls) | 0x012c | ovf 0x422 (2 controls), 4 sizes x2; copy, lcopy x3 |
| e2c | 4 controls | 0x012c, 0x0118 | calibration: ovf 0x422, copy, two each |
| e2 | 6 (2 controls) | 0x012c, 0x0118 | ovf 0x422 (control), 0x2b6, 0xe2, 0x82; copy x2 |
| d0 | 2 controls | 0x0660, 0x0748 | calibration: ovf 0x422 x2 |
| d1 | 8 (2 controls) | 0x0660, 0x0748 | ovf 0x422 x2 (controls), 0x2b6, 0x1c2, 0xe2 x2, 0x82 x2 |

42 jobs; the second replicate of e1 and d1 runs in reversed order. An overflow job took 1.2 to 1.6
s under regtimeline (E1032, E1057), a copy about 0.1 s; with the kit's reset, snapshots and the
health pair of each stage about 15 to 25 minutes in all (40 at most). e1, e2 and d1 are gated
(`gate = true`) on their calibration (score.py gate): it opens when the calibration ran, no control
there FAILED, every form a later control cites has a window (the median of its rows' `ivl`,
+-25 %, every row inside: kitscore.calibration per form, since the probe loads the CPU unlike a
copy), and for d1 a median of at most 3500 ns (E1057's bit 2 pulse is 3.9 to 4.1 us). A shut
gate skips the stage and the session goes on.

## Hypotheses (frozen: predictions/*.tsv from gen/make.py; every non-calibration row held out)

The fit is read with the scorer's own analyse() from kept rows of other sessions (gen/fit.py,
gen/fit.txt: r13-dpm pr2, r15-dpm pr4, E547's event timelines); score/score.py defines each
reading. Controls (every stage): the first sample of 0x012c, 0x0118, 0x0660 = the row's snap0
(@snap0: 6 of 6 kept r13-dpm rows), of 0x0748 = 0x1f; the probe's kept image (`o0 ... 0xff00ff00
xG`, the same G in every kept row of a PB size) or the copy's own check (diff 0); in e1, e2, d1 the
interval inside the calibration's window (@cal); in d1, the 0x422 rows read no bit 2 clear
(E1057's control). Each can fail.

e1 (0x012c alone), rows that overflow: **H-OOM-SET** (an episode of bit 1 or 2; kept: 3 of 5 E547
partial jobs at 3.7 us, 1 of 6 r13-dpm rows at 7.5 us) against **H-OOM-NONE**; **H-OOM-MT** (no
bit 2: every kept OOM sample is bit 1) against **H-OOM-GBL**; **H-THR-NEVER** (no bit 3, every
form); **H-SHORT** (bits 0 and 13 at most 8 us; E547 4.2 to 6.0); 0x422 rows: **H-PR0-QUIET** (no
bit 1 or 2). Copies: **H-COPY** (no bit 18 and no bit 0; E547's copies 10 of 10) against
**H-COPY-END** (bit 18 as in a fill, 7 of 10 kept fills). Every probe row: **H-IMG**.

e2 (0x012c + 0x0118): H-OOM-SET against H-OOM-NONE again, **H-S2-SET** (STATUS2 bit 12 or 0 in an
overflowing job; E547 partial 3 of 10) against **H-S2-NONE**; copies: **H-S2-COPYIDLE** (one
STATUS2 word through a copy; E547 10 of 10).

d1 (0x0660 + 0x0748): **H-B2PR** (bit 2's clears at most 7 us wide at PR 1-7, summed over them 1 to
60; E1057 17 in 8 rows, 3.9 to 4.1 us) against **H-B2-NONE** (0 summed); **H-B4-ONE** (bit 4 clears
once a job, 10 of 10 r15 rows) against **H-B4-PR** (two or more at PR 1-7); **H-B4-LEN** (its
width by PR: 15-26, 110-175, 120-200, 135-215, 150-240 ms at PR 0, 1, 2, 4, 7; r15 20, 138, 170,
190); **H-B1-PR** (bit 1 clear counts 0-4, 2-8, 3-12, 5-14, 10-28 by PR, each at most 7 us);
**H-B3-LONG** (a bit 3 clear of 20 to 60 us at PR 4 and 7, none over 10 us at PR 0; r15 6 of 6
and 2 of 2) against **H-B3-SHORT**; **H-B0-N** (30 to 90 bit 0 clears a job; r15 44 to 68);
**H-PC-ONCE** (0x0660 changes at most once a job, r13 8 of 8) against **H-PC-RENDER** (plan's
H-HI3D: a word a render); **H-PC-FIN** (final word 0x70305, 0x60294, 0x401a0, 0x200c0 at 0x422,
0x2b6, 0x1c2, 0xe2, r13 2 of 2 each; at 0x82 [infer] low half 0x60, high half 0 to 2).

## What decides, what cannot

Each pair decides on its held-out rows (scorekit.headline: no FAILED control, no FAILED row). A
held H-OOM-SET / H-S2-SET names the DPM and OTPM bits of an overflow with their widths (READ
lines: every bit seen, the widest episode of bits 0, 1, 13, 18); H-COPY decides a copy's end
event. Q111 keeps its host-clear clause and the order of bits within a job; Q036 keeps the owner
words, CR_DMS_CTRL, settle registers and the builder-fault clause, and what the 0x0748 bits mark.
Not decided: the partial-render count (a label, not read back), whether a pulse narrower than
the sample interval exists.

## Stops

`#limit 0` everywhere: any fault or hang stops the stage (rc 4) and the driver. hook_check stops a
stage (rc 24, the next stage runs) on a row without its whole timeline, a probe without its image
line, a copy without `copy: ok` with diff 0 or a timeline rc other than 0. A control without its
reading stops the stage (rc 25).

## Mock worlds

`model` (every stage 0), `slow748` (0x0660 + 0x0748 every 5000 ns: d1's gate shut), `noimg` (the
probe without its image line: e0, e2c, d0 stop at their first row, 24; e1, e2, d1 skipped),
`nocopy` (a copy without `copy: ok`: e0 and e2c stop, 24; e1 and e2 skipped; d0, d1 run). The
library-mock replay runs all 42 wrapped rows (28 of t10, 14 of t30), none refused.

## Replay vectors

No vectors table (closing_tables.py has no timeline kind): every stage refused as a table, the
records stay in crates/SIM_UNMODELLED.toml (event and DPM status timing: not modelled by sgx-sim
or sgx-pipe). The fold changes sgx-sim's hardware model only from what the frozen rows decide
(test first, on the kept `.txt` files). Nothing firmware-derived is written: no file goes to
data-private.

## Commands

- Offline: `bash tests/run_all.sh`. Regenerate: `python3 gen/make.py`, `python3 gen/fit.py`
  (`--check` in the tests).
- Run (the lead): `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score a kept stage: `python3 score/score.py STAGE out/ATT/STAGE out/ATT`; a gate: `python3
  score/score.py gate STAGE out/ATT`.
