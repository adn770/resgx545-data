# r35-o0b

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main 204501aac415.

The corrected rerun of r35-o0 (E1143) for **Q073** (isp, medium: "what does o0 hold at the start
of an opaque pass's pixel shader?"), plan `closing29/plan/rank-round35.md` section 3.1. r35-o0's
frozen gate put its 128 x 128 A' control in front of every row; that control failed on 1 to 30
of 4284 pixels (4 x 4 blocks of the A' job holding another pixel's value: a hardware reading),
so nothing was decided. Here (the fix, frozen before the run): an A' control gates only its own
group's P and the P rows whose A' has its size; the 128 x 128 A' control passes with at least
98 % of its pixels A'(x, y); E1143's post hoc readings are the fit (pinned:
`data:render/closing-r35-o0/fold/posthoc.out`) and every P row here is held out.

Scaffolded from resgx545 main 204501aac415 and resgx545-data 1e400772bca8 (the
r35-fold-o0-data commit that publishes r35-o0), module srcversion 7CE8E38EDB97FC5EA4F6C90,
laptop prefix `r35q`, the laptop at home (192.168.12.234). **SAFE** class: no expectfault,
`#limit 0`, no knob, no kreg. Record reserved: **E1147**. Built offline, frozen, not staged, not
run.

## Tool (none is built)

t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6..., source resgx545 a581c06): every row and the
health pair.

## What runs: one stage `o`, 32 jobs, about 7 minutes (alarm 1800 s)

r35-o0's rows and programs (bins/ byte for byte), with h5 twice and h1 four times: replicate a
c0 c1 h1 h2 h3 h4 h5, replicate b reversed h5 h4 h3 h2 h1 c1, then h1c, h1d. c0 = A' 64, A' 128;
c1 = K ; P; h1 = A' 64 ; P 64; h2 = A' 128 ; P 64; h3 = A' 64 ; P 128; h4 = A' 64 ; reset ; P
64; h5 = A' 64 ; t10 fill ; P 64. Every P but h4's is `noreset`.

## Hypotheses (frozen in predictions/o.tsv; score/score.py's docstring has the exact rules)

A kept P pixel is "A at d" (the value its group's A' wrote at the pixel d away), "EARLIER" (a
value of a row before that A') or "NEW". Fit (E1143, post hoc): OFFSETS64 = (0, 0), (0, 32),
(32, -16), (0, -16); OFFSETS128 = (0, 0), (-64, -16). h1: **H-OFFSETS** (every A offset in
OFFSETS64, no NEW) against **H-SAMEPIX** and **H-OTHER**; h2: **H-SIZENONE** (no kept pixel)
against **H-SIZEKEEP**; h3: **H-OFFSETS128** against **H-SAMEPIX**; h4: **H-RESETKEEP** /
**H-RESETCLEAR**; h5: **H-FILLREPLACE** / **H-TRIONLY**.

## Retire rule (frozen against Q073's line; `python3 score/score.py q073 out/ATT`)

RETIRE-CAPABLE iff (a) c1 and every h1 group's A' control passed, at least three of the four h1
rows are decided and H-OFFSETS (or H-SAMEPIX) holds on every decided one; and (b) both h2 rows
agree under H-SIZENONE / H-SIZEKEEP and H-OFFSETS128 holds on every decided h3 row (at least
one). Else NARROW. h4, h5 and the counts are printed, not the rule.

## Stops

Any fault or hang (rc 4, 6; `#limit 0`); a control without its pixel rows (25); a probe without
exactly --height pixel rows or with a failed line, a fill without `fill: ok` (24). `on_stop =
"end"`. Never retried or rebooted.

## The mock's worlds

model = offsets, samepix, shift, other, sizekeep, resetclear, trionly (0); anopix (24: hook_check
before the premise), pshort (24), fillbad (24), fault (4), hang (6). tests/test_score.py
simulates the table in every world: the D2 test asserts each frozen name (H-REF and the ten
models) is printed held and FAILED.

## Replay vectors

| stage | vectors table | replay |
|---|---|---|
| o | none | refused: neither sgx-sim nor sgx-pipe models o0 at the start of a pass (E1143) |

## Data

Every input is a kept record of resgx545-data (E417, E081, E1134's health texts, r35-o0's fold)
or resgx545's templates, pinned. Nothing is firmware-derived.

Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top (verify reports a new file there).
