# r35-sa

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main eea6d2ab8f45 (kit/ is that commit's blobs;
`session.py lint` is clean, no register premise is frozen) and resgx545-data 1f5ebe6b6e9d, module
srcversion 7CE8E38EDB97FC5EA4F6C90, laptop prefix `r35s`, travel cable (`host_key_alias =
"cedar"`). **Safe class**: no expectfault, `#limit 0` in both stages, no kreg, no knob, no idle,
no planned fault or hang. Records reserved: **E1144** (stage a, Q129) and **E1145** (stage t,
Q193). Plan: `closing29/plan/rank-round35.md` sections 1 (D1-D4), 3.2 and 3.4; the lead took
R35-3a (Q129's "why" moves to Q098) and R35-5a (Q193 narrows). Built offline, frozen, not staged,
not run.

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, recipe
  `data:render/closing-r30-pde/lead/build_tool30_laptop.sh`): every probe row, `probe --temps N
  --pixels FILE` (a 64 x 32 fill, our program as the pixel task, every pixel printed row by row);
  c1 adds `--coords` (a copy whose texel (x, y) is (y << 16) | x, in pa0).
- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6..., source a581c06): the health pair and stage t's
  `tri` rows.

What the rows rely on in t30's source is checked by gen/make.py (gen/constants.txt T30_*): the
`--pixels` row print, `coord_texel` = (y << 16) | x, one VM and context per process (side_init:
every row is its own context, Q193's "another context" by construction) and the probe's 16 PDS
attributes (sa0-sa15 are allocated).

## Stage a (Q129): 40 jobs, about 6 minutes (alarm 2400 s)

Programs (bins/, gen/make.py). W_n: `iaddu32.testtaz.chan0 sa_n, p0, r1, r2` (r1 = 1, r2 = M - 1:
E1106), `mov r3, sa_n`, dword 0 = r3, o0 = K1 0xc0de0a01 (E1139's writer); W_157 the same for sa1,
sa5, sa7 (dwords 0-2; iaddu32 as the singles, not E484's `mov`, so the union compares one form).
X_1: a W_1 with its own marker and o0 = K2 0xc0de0a02. R_5: `mov r10, sa5`, dword 0 = o0 = r10
(E1140's form, D3). K: o0 = dword 0 = K3 0xc0de0a03. C: o0 = dword 0 = pa0. Markers 0x5a35RRNN
(RR the row, NN the sa), one per writer row.

| group | rows | purpose | reps |
|---|---|---|---|
| c0 | K | D1: position decode, every pixel K3 | 1 |
| c1 | C with --coords | D1: position decode, pixel i = (y << 16) \| x | 1 |
| c2 | W_5, R_5 | D1: reader form on sa5 (marker in 2048 of 2048) | 2 |
| f | W_0, W_1 | fit: S0 (f0a) and the shift d (f1a) | 2 each |
| h | W_2..W_15, W_157 | held out: n = 2, 3, 5, 7, 15 and 157 twice, 4, 6, 8-14 once | 21 |
| p | W_5, X_1, R_5 | clause (b): a gap job writing another sa | 2 |
| q | W_5, K, R_5 | clause (b), E484's form (fit) | 1 |

Replicate b runs the two-replicate groups in reverse order. Every W and every group's first row
gets the kit's debugfs reset, the rest of a group `noreset`. The first row after the stage-begin
health pair is K (not a reader, D4).

## Stage t (Q193): 23 jobs, about 4 minutes (alarm 1800 s)

T: r20 = M (0x7e00RR14) in every instance, dword 0 = r20, o0 = K1. U: `mov r10, r20` (r20 never
written), dword 0 = o0 = r10. T8 (`--temps 8`): r0-r5 = 0x7e08RR0k, dword 0 = r0, o0 = K1 (the
allocation is the larger of 8 and the fill program's own [check: not read from the source]).

| group | rows | purpose | reps |
|---|---|---|---|
| c | T, U | D1: U reads T's marker in 2048 of 2048 (E593's first order, E484's r40) | 2 |
| t1 | T, K, U | a job writing no r20 between | 2 |
| t2 | T, t10 tri, U | the triangle between | 2 |
| t3 | T, U (reset) | a debugfs reset between | 2 |
| t4 | T, T8, U | a smaller allocation's writer between | 1 |

First row: T (D4). Replicate b reversed (t3, t2, t1, c).

## Hypotheses (predictions/*.tsv from gen/make.py; categories in score/score.py)

- a, clause (a): **H-FOUR** / **H-OTHERN** (4 odd pixels per sa written, each marker 4 times);
  **H-FIXED4** (positions = S0) / **H-SHIFT** (S0 + n d mod 2048, d fitted on f1a); **H-VAR**
  (replicate b's positions differ from a's); **H-UNION** (W_157's per-marker positions = the same
  replicate's W_1, W_5, W_7). Pixel index i = y * 64 + x; odd = not K1.
- a, clause (b): R_5 after X_1 reads PREV (**H-ONEJOB**: X_1's output, E1140's rule) or M
  (**H-UNTILWRITE**: sa5 kept across a job that writes another sa); q: both say PREV (E484).
- t: per U, **H-LASTWRITER** (all T's marker), **H-LASTJOB** (no r20 marker after a job between),
  **H-SPLIT** (a marker and other values after a job between, E593's 1536/512), **H-TRI1536**
  (t2: two values, 1536 and 512), **H-RESETCLR** (t3: not the marker).

D1: c0, c1 gate every W row's positions; c2 gates every R_5 reading; stage t's c gates every U.
D2: tests/test_score.py has, for every frozen name, a mock world where the scorer prints it held
on every held-out row and one where it prints it FAILED; a frozen name with no world fails the
test. Expected values come only from this session's rows (program constants, the row before's
output, the fit rows' positions).

## Rules (score/score.py, frozen)

- **Q129** (`python3 score/score.py q129 out/ATT`): (a) DECIDED iff c0, c1 pass, every f/h row is
  read (32 rows agreeing with the o0 line, the in-job readback, K1 most frequent), H-FOUR on
  all, |S0| = 4, H-FIXED4 or H-SHIFT on every held-out single n, H-UNION on both h157, H-VAR
  failed on every replicate pair. (b) DECIDED iff the c2/p/q controls pass, qa-r reads PREV and
  exactly one of H-ONEJOB, H-UNTILWRITE holds on both p rows. RETIRE-CAPABLE iff both (R35-3a:
  the answer plus the [infer] storage statement; the mechanism moves to Q098); else NARROW.
- **Q193** (`python3 score/score.py q193 out/ATT`): per group t1, t2, t4 exactly one of
  H-LASTWRITER, H-LASTJOB, H-SPLIT on every row; t3 kept or cleared; another context decided by
  construction; always NARROW (power cycle and module reload open, R35-5a).

## Stops

Any fault or hang (rc 4: no expectfault row); a control without its reading (25); a probe
without its o0 line, its 32 whole pixel rows, a `failed` line, or (W, W_157, X, T, T8, K) its
scratch dword 0 (W_157 also dword 2); a t10 tri not drawn exactly (hook_check, 24). Stage a's stop
goes on to t (independent register files; t starts with a writer after the health pair); t's
ends the session. Never retried, never rebooted.

## The mock's worlds

model (shift, onejob, lastwriter), fixed, var, othern, untilwrite, lastjob, split, tri1536,
resetclr, badcoords (D1 fails), wbad (readbacks 0): 0; noread (t 24, ends), norows (a 24, t
runs): 24; fault (a 4), hang (t 4): 4. The library-mock replay runs every row on its pinned
source (programs not simulated; noreset rows from a fresh mock).

## Replay vectors

`refused`: sgx-sim and sgx-pipe model each job alone and take sa and temporaries as inputs; a
value carried from the job before (clause (b), Q193) is session state, and which instances show
an sa write (clause (a)) is not modelled. The fold may tabulate the W rows' odd positions with
`closing_tables.py` (format `sgx545-tables`) from the kept texts alone, and add the positions
rule to crates/SIM_UNMODELLED.toml (sim work, not this session).

## Layout and commands

gen/make.py (+ gen/pins.py, gen/constants.txt), score/score.py, run/hooks.sh, mock/world.py
(+ mock/kept/: r34-q010's kept health pair texts), tests/ (attempt.py builds attempts from the
mock), PREFLIGHT.md, FOLD-NOTES.md. Publishable: everything; nothing for data-private.

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python`, which the offline tests use
  unless `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` (done by the builder).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). After the run: `python3 score/score.py a out/ATT/a`,
  `python3 score/score.py t out/ATT/t`, and the q129 and q193 commands. The driver keeps its own
  logs, `out/stage.log` and `out/ATTEMPT/run.log`; tee nothing into this directory's top.
