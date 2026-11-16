# r34-sa0

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main fd916fedc118 (kit/ is that commit's blobs, with
round 34's T1 forms: `session.py lint` is clean, no register premise is frozen) and resgx545-data
main 9a809796f99d, module srcversion 7CE8E38EDB97FC5EA4F6C90, laptop prefix `r34s`, travel cable
(`host_key_alias = "cedar"`). **Safe class**: no expectfault, `#limit 0`, no kreg, no knob, no
planned fault or hang. Record reserved: **E1139**. Plan: `closing29/plan/rank-round34.md` section
3.6 (Q136), with the lead's sketch. Built offline, frozen, not staged, not run.

## Why

Q136 (usse, low): "how long does a value written to sa0 last across jobs, and is the 0xff00ff00
and 0xff203040 mixture that pa0 reads in the first jobs of a table the colour left by the job
before it?" E496's job 8 read sa0 = 0x79, which was both the marker job 7 wrote and the colour
job 7 output, so persistence and E484's colour rule were confounded; E484 had sa1/5/7 read by the
next job only. E496's first jobs read pa0 as 0xff00ff00 x1536 and 0xff203040 x512, after a table
whose `before` job was a triangle (`usse/pa-dest/env.toml`), not checked.

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, recipe
  `data:render/closing-r30-pde/lead/build_tool30_laptop.sh`): every `probe` row, a plain 64 x 32
  fill (no `--coords`) whose pixel task is our program, the scratch dwords printed.
- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6..., source a581c06): the health pair and the X rows
  (bare `fill`, colour 0xff336699; bare `tri`, colours 0xff00ff00 and 0xff203040, its source's
  `cmd_tri` colours[0], read by gen/make.py from the bound source).

## What runs: one stage `s`, 60 jobs, about 18 minutes (25 at most; alarm 2700 s)

Programs (bins/, gen/make.py; every instance runs the same body):

| program | body | output |
|---|---|---|
| `w-M` (W, control) | `iaddu32.testtaz.chan0 sa0, p0, r1, r2` (r1 = 1, r2 = M - 1: E521/E1106's zero-extended sum = M), `mov r3, sa0`, dword 0 = r3 | o0 = K1 0xc0de0a01 |
| `r` (R, held out) | `mov r3, sa0`, dword 0 = r3 | o0 = sa0 ^ K2 0x33330000 |
| `p` (P) | `mov r3, pa0`, dword 0 = r3 | o0 = pa0 ^ K4 0x00550000 |
| `k` (K, control) | writes no sa or pa | dword 0 = o0 = K3 0xc0de0a03 |

Markers M = 0x5a0c0a01..09 (first replicate) and 0x5a0c0b01..09 (second), one per writer row; no
value of the session equals another, its xor with K2 or K4, 0xd0000000 or 0xdeadbeef
(tests/test_gen.py). Groups, first replicate in this order, the second reversed (frozen before the
first is read); every W and every group's first row gets the kit's debugfs reset, everything after
it in the group is `noreset` unless named:

| group | rows | what it isolates |
|---|---|---|
| nr | W, R | the next job, nothing between |
| rs | W, R (reset) | a debugfs reset, no job |
| i10, i60, i120 | W, R (`noreset idle:S`) | 10, 60, 120 s idle, no job, no reset |
| k3 | W, K, R | a colour fill between (writes no sa) |
| fl | W, t10 fill, R | the t10 fill between (another process, the health fill's argv) |
| tr | W, t10 tri, R | the t10 triangle between |
| rr | W, R, R | a job that reads sa0 and writes none, between |
| ptr | t10 tri, P | (b) fit: E496's mixture re-read after a triangle |
| pk3 | K, P | (b) a colour fill before pa0 |
| pfl | t10 fill, P | (b) the t10 fill before pa0 |
| pk3r | K, P (reset) | (b) a reset between |

Jobs: 13 groups, 30 a replicate. Time: 60 jobs at about 8 s (26 resets), 380 s of idle, the
health pairs, staging.

## Frozen values: where they come from

No register value and no other session's idle reading is frozen (the r30-evst and r33-tim lesson).
Controls: W's dword 0 = M (E1106/E521 [HW], E496 job 7's in-job readback) and its most frequent
o0 value K1; K's dword 0 and top = K3: the programs' own constants. A reader's expectation is read
in this attempt: M is its group's writer constant; PREV is the output of the job right before it
(its kept o0 line, the t10 fill's own `colour` line, or the t10 tri's two colours).

## Hypotheses (predictions/s.tsv, from gen/make.py; scorer categories in score/score.py)

A reader's decoded pixels (o0 xor its key) are **M** (2048 of its marker), **PREV** (every value
one the job before output, its most frequent one the same; after a tri, each one of the two
colours) or **TRI** (each one of the tri's two colours); anything else is cannot tell.

- (a), every R row held out (20): **H-PERSIST** (M everywhere), **H-ONEJOB** (E484's sa rule: M
  with no job between, PREV after K, the fill, the tri and the first reader), **H-COLOUR** (PREV
  everywhere: E496's job 8 was the colour). Side: **H-RESET** (rs: not M), **H-IDLE** (idle rows:
  not M).
- (b), P rows: **H-PREV** (PREV) against **H-FIXED** (TRI); ptr is the fit (both say TRI after a
  tri); pk3, pfl held out (4); pk3r held out, side **H-RESETP** (not PREV).

Every reader is gated by its group's controls (W, K). The odd pixels of a writer (E484: 12 of the
sa writers' pixels showed the sa values) are allowed: W's control is its most frequent value, and
PREV compares value sets and the most frequent value, not counts.

## The retire rule (score/score.py, frozen; `python3 score/score.py q136 out/ATT`)

Against the line's two clauses:

- **(a)** DECIDED iff every W and K control of the R groups passed, all 20 R rows are decided and
  exactly one of H-PERSIST, H-ONEJOB, H-COLOUR holds on all 20 (both replicates); its answer
  names how long: every job, one job, or none, and the reset and idle readings with it.
- **(b)** DECIDED iff the K controls passed, both ptr fits read TRI and H-PREV holds, H-FIXED
  fails on all four of pk3 and pfl; pk3r is printed in the answer either way. The identity with
  E496's first jobs is [infer]: its table's `before` was a triangle with those two colours.

RETIRE-CAPABLE iff both are DECIDED; else NARROW, naming the decided clause. Which can retire: (b)
is the likelier (one rule over four held-out rows whose two rivals predict disjoint readings); (a)
retires only if one of the three patterns holds on all 20 rows, idle and reset included (a
reader of zeros after the reset, say, is cannot tell and narrows). The rule names what is not the
line's question for the lead: an o destination, other operands, one job per register of the banks
(body extras), the instance slots (Q129, Q193), the kernel's own jobs beyond a debugfs reset.

## Stops

Any fault or hang (rc 4: no expectfault row); a control without its reading (25); a probe without
its o0 line or with a `failed` line, a W or K without its dword 0, a t10 fill without `fill: ok`
and `diff: 0 of 2048`, a t10 tri not drawn exactly (hook_check, 24). `on_stop = "end"` (one
stage). Never retried, never rebooted.

## The mock's worlds

onejob (= model), persist, colour, resetclr, fixed, odd (E484's odd pixels in every writer),
wbad (W's readback 0: the R rows cannot tell): 0; noread, nofill: 24; fault, hang: 4. The scorer
on each world's kept output gives the matching rule (debug/, not frozen). The library-mock replay
runs all 52 t30 rows and 8 t10 rows on their pinned sources (none refused; the 30 noreset rows
start from a fresh library mock there).

## Replay vectors

`refused`: sgx-sim and sgx-pipe model each job alone; an sa0 or pa0 value carried from one job to
the next is session state no replay holds (Q136's answer). The fold may tabulate the readers'
decoded pixels in run order (`closing_tables.py`, format `sgx545-tables`) and add the carried
value to crates/SIM_UNMODELLED.toml (sim work, not this session).

## Layout and commands

gen/make.py (+ gen/pins.py, gen/constants.txt), score/score.py, run/hooks.sh, mock/world.py
(+ mock/kept/: r34-q010's kept health pair texts), tests/, PREFLIGHT.md, FOLD-NOTES.md.
Publishable: everything; nothing for data-private (no firmware-derived file).

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python`, which the offline tests use
  unless `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` (done by the builder).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top.
