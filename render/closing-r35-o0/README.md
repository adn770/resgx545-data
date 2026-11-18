# r35-o0

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main eea6d2ab8f45.

A closing session for **Q073** (isp, medium: "what does o0 hold at the start of an opaque pass's
pixel shader?"), plan `closing29/plan/rank-round35.md` section 3.1 (R35-1 a), resgx545-data
1f5ebe6b6e9d, module srcversion 7CE8E38EDB97FC5EA4F6C90 (the lead boots it before the run: the
laptop is on stock Arch now), laptop prefix `r35o`, travel cable (`host_key_alias = "cedar"`).
**SAFE** class: no expectfault, `#limit 0`, no knob, no kreg, no register write. Record reserved:
**E1143**. Built offline, frozen, not staged, not run.

## Tool (none is built)

t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6..., source resgx545 a581c06, recipe
`data:render/closing-r10-st1/lead/build_tool10.sh`): every row and the health pair.

## What runs: one stage `o`, 27 jobs, about 6 minutes (alarm 1800 s)

Every probe is E417's argv form: `probe --temps 32 --pixels --tri pixel --width N --height N
--max-width 128 --max-height 128` (N 64 or 128). Programs (bins/, gen/make.py):

| program | body | role |
|---|---|---|
| `a.bin` (A', control) | o0 = (pa0 & 0xffff0000) \| ((pa1 >> 16) & 0xffff), with E081's pixpds (`pds_iter_xy.bin:12`, coordinate set 1) and `vtx_coords.bin`, `--vtx-coords 2` | a value unique per pixel by construction |
| `k.bin` (K, control) | o0 = 0xff00ff00 (E417 job A, its kept bytes) | E417's previous colour |
| `p.bin` (P) | o0 = o0 (E417 job P, its kept bytes) | the pass-through: reads o0 at the start |
| t10 `fill` (h5) | the 64 x 32 fill, colour 0xff336699 | a non-triangle job between |

pa under this pixpds is (c + 0.5) * 2 / n - 1 (E081's oreg-x/oreg-y kept images: 1062 of 1062
each, tests/test_gen.py); each such single has at most 7 significant bits, so the top 16 bits
name the coordinate exactly and A' is injective at 64 and 128 and never a session colour.

| group | rows | purpose | replicates |
|---|---|---|---|
| c0 | A' 64 ; A' 128 | D1: the decoder's known value at both sizes | 1 |
| c1 | K ; P (noreset) | D1 on P: P's non-background pixels all K (E417's form) | 2 |
| h1 | A' 64 ; P 64 (noreset) | which pixel's value (h1a fit, h1b and h1c held out) | 3 |
| h2 | A' 128 ; P 64 (noreset) | a previous job of another size | 2 |
| h3 | A' 64 ; P 128 (noreset) | the other direction | 2 |
| h4 | A' 64 ; reset ; P 64 | does a debugfs reset keep it | 2 |
| h5 | A' 64 ; t10 fill (noreset) ; P 64 (noreset) | does a fill between replace it | 1 |

Order: replicate a c0 c1 h1 h2 h3 h4 h5, replicate b reversed h4 h3 h2 h1 c1, then h1c. The
first row is an A' (D4); every A' and K row gets the kit's reset.

## Hypotheses (frozen in predictions/o.tsv; score/score.py's docstring has the exact rules)

Every expected value comes from this session's own rows: a P row is read against its group's
A' image (value -> the pixel that wrote it). h1-h3: **H-SAMEPIX** (the same pixel), **H-SLOTMAP**
(a non-identity map fitted on h1a, held out on the rest), **H-OTHER**; h2, h3 also
**H-TILESLOT** (same 32 x 16 tile index [infer]). h4: **H-RESETKEEP** / **H-RESETCLEAR**. h5:
**H-FILLREPLACE** / **H-TRIONLY**. The count of leftover pixels is a reading (E417: 390-450).

## Retire rule (frozen against Q073's line; `python3 score/score.py q073 out/ATT`)

RETIRE-CAPABLE iff every control passed (c0, c1 both replicates, every group's A'); (a) the same
one of H-SAMEPIX / H-SLOTMAP held on both held-out h1 rows; (b) at least one decided row in h2
and in h3, and exactly one of H-SAMEPIX / H-TILESLOT / H-SLOTMAP held on every decided h2/h3 row.
Else NARROW, naming what decided. h4/h5 (lifetime) and the count are printed, not the rule
(R35-2 a). A row with no leftover pixel is cannot tell.

## Stops

Any fault or hang (rc 4, 6; `#limit 0`); a control without its pixel rows (25); a probe without
exactly --height pixel rows or with a failed line, the fill without `fill: ok` (24). `on_stop =
"end"`. Never retried or rebooted.

## The mock's worlds

model = samepix, slotmap, tileslot, other, resetclear, trionly (0); anopix (24: hook_check before the premise), pshort (24),
fillbad (24), fault (4), hang (6). tests/test_score.py simulates the table in every world: the D2
test asserts each frozen name (H-REF and the eight models) is printed held and FAILED.

## Replay vectors

| stage | vectors table | replay |
|---|---|---|
| o | `vectors/closing/r35-o0/o.table.json` (row, size, A' group row, per-pixel P value) | refused: neither sgx-sim nor sgx-pipe models o0 at the start of a pass (the fold adds the SIM_UNMODELLED entry citing E1143) |

## Deviations from the plan

- A''s pixpds is E081's (`probes/usse/templates/pds_iter_xy.s`, coordinate set 1, no eot slot),
  not E385's: E385's ran only with an eot slot and sideband, while E417's K and P ran without
  one; E081's form ran on hardware in exactly this slot set and its pa values are checked
  exactly offline. A' packs the top halves of pa0/pa1 (no float-to-int conversion).
- 27 jobs (h1 three replicates). Every row carries E417's `--max-width/--max-height 128`.
- The "freeze refuses a name in no test" check is tests/test_score.py's D2 test (run_all runs it
  before and after the freeze), not a kit change.

## Data

Every input is a kept record of resgx545-data (E417 isp/o0-start, E081 usse/output-registers,
E1134's health texts) or resgx545's templates, pinned. Nothing is firmware-derived.


Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top (verify reports a new file there).
