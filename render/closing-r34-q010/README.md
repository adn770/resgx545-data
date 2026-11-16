# r34-q010

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main 5745c8dc1a8d and resgx545-data main 8e59b150be5f,
module srcversion 7CE8E38EDB97FC5EA4F6C90, laptop prefix `r34q`, travel cable (`host_key_alias =
"cedar"`). **Safe class**: no expectfault, `#limit 0`, no kreg, no knob, no planned fault or hang.
Record reserved: **E1134**. Plan: `closing29/plan/rank-round34.md` section 3.1 (R34-1).

## Why

Q010 (texture, low): "which job clears colour-space set 0 between jobs, given that a copy that
does not load it converts with the last loaded words across a debugfs reset (E1097, E1103,
E1112), and with zeros after the kit's health fill and triangle with no fault or hang and after a
recovered hang followed by them (E1112), and the first job of a session after hung jobs converts
with zeros (E271)?". E1112 left two candidate jobs, the health fill (t10 `fill`) and the health
triangle (t10 `tri`), and could not part them from the stage boundary. Neither the fill nor
library transfers set `DRM_SGXFIVE_TRANSFER_LOAD_YUV` (E1103: an unflagged fill keeps the set), so
both rivals are real.

## What runs: one stage `c`, 32 jobs, about 12 minutes (15 at most)

Copies on t30 (`~/sgxfive-test-t30`, sha256 b5ea288d..., source 42c4de7, its copy path the same
code as t22's for these argv) with E1103's and E1112's forms; the health pair's own argv on t10
(`~/sgxfive-test-t10`, sha256 9bedc2d6..., source a581c06, the session's health tool). Every row
gets the kit's debugfs reset first (but `t6-xt`, `noreset`); the health pair runs only at the
stage's begin and end, so every triple is inside the stage (no `after` word).

| rows | what | set |
|---|---|---|
| z0-ld, z0-rd | load zeros, then the copy without the load: black on this module and tool | control |
| L = `tX-ld` | load BT.601 (xfer:17^=0x1, xfer:18-22): E037's 0xb6067a95fa98de2d | control |
| X | the job under test (below) | between |
| R = `tX-rd` | the copy without the load: KEPT (E037's hash) or CLEARED (0xd3522437a14b6325) | held out |

| triple | X | replicates (run order) |
|---|---|---|
| T0 | none: R right after L and a reset (clause (a); R is a control here) | t0a, t0b |
| T1 | t10 `fill` | t1a, t1b |
| T2 | t10 `tri` | t2a, t2b |
| T3 | t30 `copy --every-value --pixels` (a transfer that is not a fill, no YUV, no load) | t3a, t3b |
| T4 | none, `idle:60` on R (after R's reset, right before R) | t4 |
| T5 | none, `idle:120` on R | t5 |
| T6 | t10 `fill`, then t10 `tri` with `noreset` (the pair as `health_ok` runs it) | t6 |

Order: z0, t0a, t1a, t2a, t3a, t4, t5, t6, then t3b, t2b, t1b, t0b (second replicates reversed,
frozen before the first is read). Time: 32 jobs at about 10 s (a 3 s reset each), 180 s of idle,
two health pairs, staging: about 12 minutes. Alarm 1800 s.

## Frozen values: where they come from

No register value is frozen; no value comes from another session's idle readings (the r30-evst
and r33-tim lesson). KEPT and CLEARED are job outputs the hardware already gave: E1112's
r29-flag2 q010-pre and q010-ld2 (KEPT) and q010-af and q010-p1 (CLEARED), pinned and checked by
gen/make.py. This session re-reads both itself before using them: z0-ld and z0-rd must read
CLEARED and every L must read KEPT on this module and t30 (controls), and T0's R must read KEPT
(the reset keeps the set on 7CE8E38E as on E0CC4027).

## Hypotheses (predictions/c.tsv from gen/make.py; every R row held out)

- **H-FILL**: the fill clears (T1, T6 CLEARED; T2-T5 KEPT).
- **H-TRI**: the triangle clears (T2, T6 CLEARED; T1, T3-T5 KEPT).
- **H-BOTH**: each clears alone (T1, T2, T6 CLEARED; T3-T5 KEPT).
- **H-NONE**: nothing in the stage clears (every R KEPT): then the stage boundary [infer].
- **H-IDLE** (T4, T5 CLEARED) and **H-COPYNL** (T3 CLEARED), scored on their own rows; the full
  patterns are their rivals (KEPT there).

Gates: z0-ld, z0-rd, t0a-rd, t0b-rd gate every R row; each R row also needs its own L.

## The retire rule (score/score.py, frozen; `python3 score/score.py q010 out/ATT`)

RETIRE-CAPABLE iff every control passed (15), all 9 held-out R rows are decided (KEPT or CLEARED)
and exactly one of H-FILL, H-TRI, H-BOTH holds on all 9: the line's question ("which job") is
then answered by held-out rows with both replicates agreeing, H-IDLE and H-COPYNL failed. Clause
(a) is re-read held out (t0a-rd, t0b-rd) and (b)'s health pair without a fault (t6-rd). (b)'s
recovered hangs and (c) (E271) are not re-run (a hang is flagged class); the rule prints them as
givens the answer explains [infer], for the lead to confirm. Anything else: narrow only, with the
reason (H-NONE: the stage boundary or a longer idle; a split replicate; a failed control).

## Stops

Any fault or hang (rc 4: no expectfault row); a control without its job or hash (25); a copy
without `job: ok` or its target hash, a triangle that does not draw exactly, a fill without
`fill: ok` (hook_check, 24). `on_stop = "end"` (one stage). Never retried, never rebooted.

## The mock's worlds

fill (= model), tri, both, none, copyclr, resetclr (T0 fails, every row cannot tell): 0; noread,
nojob: 24; fault, hang: 4. The world clears the set in the health pair too (the same argv). The
library-mock replay runs all 32 rows on t10's and t30's pinned sources (none refused).

## Replay vectors

`refused`: sgx-sim and sgx-pipe model each job alone (`csc_unloaded` per job,
crates/sgx-sim/src/vectors.rs); a set kept or cleared across jobs is session state no replay
holds. The fold may tabulate the hashes in run order and add the clearing job to
SIM_UNMODELLED.toml or a sequence model (sim work, not this session).

## Layout and commands

gen/make.py, score/score.py, run/hooks.sh, mock/world.py (+ mock/kept/, r29-flag2's published
texts), tests/, PREFLIGHT.md, FOLD-NOTES.md. Publishable: everything; nothing for data-private (no
firmware-derived file).

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python`, which the offline tests use
  unless `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` (done by the builder).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top.
