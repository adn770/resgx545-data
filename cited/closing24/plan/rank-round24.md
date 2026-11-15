# Round 24 plan: tool changes ranked by the questions a later session could retire

Planner (Opus, 2026-11-15, on the road, user present), offline and read only. Basis: resgx545 main
7f214e5 (141 open, 131 hw; records to E1101), data 40050d0ac, fork 456404fcffe5, module
E0CC40275493F8AEAD8180B, laptop tools t10, t14, t18, t18b, t22 (9b62d315), t22b (2ae2800a).
Read: BRIEF-COMMON (round 24), round 22's plan, the r23 handover, the closing log's 2026-11-15
lines, the state digest (open list, "Known tool weaknesses"), `git diff 0a7849e 7f214e5` over
`questions/`, `HACKING.md`, `tools/closing`, `userspace`, the question files Q019, Q181, Q123
(as deleted by the unmerged 788b62c), Q191, Q107, Q050, Q043, Q119, and records E037, E125, E391,
E492, E973, E1096 to E1098; `sgxfive-test.c` (probe report, lines 1793 to 1862, 2085 to 2105,
2705 to 2723), `probes/pds/templates/sa64_dump.s`, the kit's `run_stage.sh` and `lib_kit.sh`
(row loop, `noreset`, reset and health), r23-pk's README and `tables/q181.txt`.

No records are made by this round. E1102 to E1104 are pencilled in for the sessions of section 5.

## 0. Summary

- **Only one tool change still unlocks a retirement: an opt-in print of more than 32 scratch
  dwords in `probe` (T1, Q019).** `probe_scratch` is called with `max_shown` 32 on the fill and
  copy paths (`sgxfive-test.c` lines 2099 and 2104); `probe --tri` already prints the whole
  buffer (lines 2712 to 2722). T1 adds `--scratch-show N`, default 32, so every earlier row's
  output stays byte for byte. About 1 to 1.5 agent hours, t24 built on the laptop in ~1 min.
- **Q181 needs no tool change.** E037's own zeros-load copy (`copy ... --poke xfer:17^=0x1 --poke
  xfer:18..22=0`, already run on t22 in r23-pk's form) *is* the colour-space reset, and E1097 shows
  the set survives the kit's debugfs reset, so a copy row in front of each probe row sets the
  state the next row reads. The kit runs rows in table order and runs no health job between rows
  (only after a fault and at the stage's end: `lib_kit.sh` `health`, `run_stage.sh` line 267).
  Pairs of a set copy then a probe job decide H-FILLLOAD against H-FILLIGNORE both ways round
  (section 2.2): either result retires Q181. An in-process reset (`probe --csc-load`, T2) only
  saves one job per pair; it is listed, not recommended.
- **Q123 needs no tool change** (the lead's two reasons for declining, r23 handover: the code step
  rests on an offline fit, words past 256 partly on a control row). Two held-out stages on t22:
  four new placements of E492's read and jump programs whose links the frozen 0x80000 step
  predicts, and lapc/ba landings at ten frozen indices in 256 to 8191 (section 2.3).
- **Dropped** (no retirement any more; question text unchanged since round 22's check): `--blk-add`
  bits 16-31 (Q069, Q162), TA data across a recovery (Q139, Q100), PDS patch/offset and PB dump
  (Q057, Q058, Q060, Q062, Q054), large copies, `--th-delay`, scratch VA (Q011, Q004, Q096), and a
  regtimeline memory watch for Q191's "which part of the kick" (narrow: clause (c) and "why only
  another context's kick" stay, R22-3 a).
- **Kept but not proposed:** a filtered copy (Q043, conditional), the kit `kreg:` word (Q024 as a
  bounded negative, a rule change), `tri --kick-flags` (Q119, parked fw), and the two module knobs
  (Q109, Q068). Each is below 0.35 value points per hour.
- **Packages:** P1 (tool only, one agent, ~2 h): T1 with tests, the usage text, the HACKING upkeep
  (the `probe --poke` entry leaves: r23-pk ran; a YUV-row note joins the kit's readings), recipe
  `build_tool24_laptop.sh`, t24. P2 is optional (T2) and not recommended. **Sessions for round
  25:** r25-q123 (t22, 21 jobs, now), r25-csc (t22, 16 jobs, now, can share r25-q123's sitting),
  r25-sa64 (t24, 58 jobs). All safe class. Up to three retirements (Q123 2, Q181 1, Q019 2c).

## 1. Ranking (value-weighted retirements per tool hour)

Weights as rounds 18 and 22: high 3, medium 2, low 1, parked 0.5; c marks a conditional
retirement. Hours are agent hours with tests; every sgxfive-test build is ~1 min on the laptop
(t22's recipe: `make CC=gcc build/sgxfive-test` ~50 s, `make check` ~2 min, 0 failures).

| # | change | syntax | retire-capable | later row | h | ret/h | risk | laptop build |
|---|---|---|---|---|---|---|---|---|
| 0a | none | E492's programs, `--place` on t22 | Q123 (2) | r25-q123 | 0 | - | safe | no |
| 0b | none (kit order) | E037 set copy, then the probe job | Q181 (1) | r25-csc | 0 | - | safe | no |
| T1 | scratch print (P1) | `probe --scratch-show N` | Q019 (2c) | r25-sa64 | 1.25 | 1.6c | low | t24, ~1 min |
| T2 | in-process reset (P2) | `probe --csc-load zero\|bt601` | none added | r25-csc, 8 jobs fewer | 2 | 0 | low | t24 |
| T3 | `kreg:OFF=V` kit word | row word, register write | Q024 (1, negative) | 640 timed jobs | 3 | 0.33 | high, rule | no (kit) |
| T4 | filtered copy | `copy --filter` | Q043 (2c) | E412's tagged pair | 8 | 0.25 | medium | t24 |
| T5 | `tri --kick-flags` | FIRST+LAST in one TA command | Q119 (0.5) | split vs both flags | 2.5 | 0.2 | low | t24 |
| N1 | module: large-page PDE | `vm_pde_size` debugfs | Q109 (1c) | PDE sizes | 4 + 45 min + boot | 0.1 | medium | module |
| N2 | module: TA preemption | `ctx_switch` mode | Q068 (2) | resumed TA | 12 + boot | 0.1 | high | module |

Rows T3 to N2 are carried from round 22 (section 1, rows 6 to 8 and N1, N2) after checking that
their question files did not change since 0a7849e (the diff touches only Q038, Q071, Q088, Q191,
Q019, Q181 and the new Q301). None is proposed this round (R24-5).

## 2. What retires, and how

### 2.1 T1: `probe --scratch-show N` (P1; Q019, medium, conditional)

**Syntax.** `probe [--scratch-show N] ...`: print up to N changed scratch dwords (1 to the
scratch buffer's dwords, `--scratch-pages` included; default 32, the output of every earlier row
unchanged). `--scratch-show all` is the buffer's size. It applies to the fill and copy probe paths
(the `probe_report` and `probe_report_failed` calls of lines 2099 and 2104); with `--tri` it is
refused (that path already prints all). The `scratch N more changed` line stays for N exceeded.

**What blocks Q019 today (checked).** Q019's last note (E1096): "whether attributes 32-63 arrive in
sa32-sa63 ... needs a probe that prints sa32-sa63 (a tool change)". E1096's results: every row
counts `scratch 32 more changed`. `sa64_dump.s` stores sa0-sa63 to scratch dwords 0-63, so the
data are on the GPU side already; only the print stops at 32.

**Later row (r25-sa64, section 5).** E391's 40 jobs again, E391's `sa64_dump.bin` and douta
programs byte for byte, with `--scratch-show 64`, plus 16 held-out jobs at 3 and 6 rows. Each row
reads sa0-sa31 again: **E1096's reading is the in-row control** (it can fail), and sa32-sa63 are
the new reading. Frozen: H-ALL64 (attributes 32-63 at their own sa at every size), H-NONE (none at
any size: the 32 is set elsewhere, E391's "never sa32-sa63" stands), and H-ROWS (fitted on 0, 1 and
4 rows, its table hashed before the held-out rows, held out at 2, 3, 6 and 8; the natural reading
[infer] is 16 attributes a row past 32, or 16 a row from 0 with a floor of 32).

**Retires Q019 only if** H-ROWS holds out with a fit table that is not flat (the field's limit
read off a fill), and the user moves E973's layered-background 0-row clause to Q066, where that
scene's other words already are (R24-3). Under H-ALL64 or H-NONE Q019 narrows: the fill's task
then takes no limit from the field up to 64, and "or does the task take its size from elsewhere"
needs a second word. Under H-ALL64, E391's claim "never sa32-sa63" needs an appended correction
(it read only sa0-sa31: E1096's "What it does not show").

**Fallback without a tool [infer].** A USE program `sa_hi_dump.s` storing sa32-sa63 to scratch
dwords 0-31 prints within today's limit on t22. It loses the in-row control (E391's program is no
longer byte for byte) and doubles the jobs if both halves are wanted. Kept as R24-1 c.

**Tests (first).** The mock writes no scratch dwords by itself; the agent adds a mock-only way to
dirty them (e.g. `--late` accepted more than once, or a mock knob that writes N scratch dwords
after the job). Then: default prints 32 lines and `scratch 32 more changed` for 64 dirty dwords
(byte for byte as t22); `--scratch-show 64` prints 64 lines and no "more changed" line;
`--scratch-show all` prints every dirty dword; 0, a value over the buffer, and `--tri` are
refused (status 2); the failed-job path (`probe_report_failed`) honours N. The usage header and
`usage()` text name the option. **Cost** 1 to 1.5 h. **Risk** low: output only.

### 2.2 Q181 with the kit as it is (no tool; r25-csc)

**Open (Q181's last note, E1097):** whether a fill's transfer command loads the colour-space set;
"no fill ran on a set known to be unloaded". Its own "to settle it": a zeros load, the poked fill,
the same fill unpoked, frozen in that order. E1097 also shows the set persists across jobs and the
kit's reset; E037 shows a zeros load reads opaque black.

**Rows** (one format each of 28 and 29, E568's `fy-*-p0` programs on t22; the set copies are
E037's UYVY copy with `xfer:17^=0x1` and set 0's five words, BT.601 or zeros, as r23-pk's
`c-copy-csc`):

| pair | set copy (control) | probe job | H-FILLLOAD | H-FILLIGNORE | label |
|---|---|---|---|---|---|
| a | zeros (black) | unpoked | black | black | control |
| b | zeros (black) | poked BT.601 | conversion | black | fit |
| c | (none: after b) | unpoked | conversion | black | fit |
| d | BT.601 (E037 hash) | unpoked | conversion | conversion | control (can fail: a reset that clears) |
| e | BT.601 (E037 hash) | poked zeros | black | conversion | held out |
| f | (none: after e) | unpoked | black | conversion | held out |

16 jobs (2 x 8). The scorer reads each probe job against the copy just before it and scores
"cannot tell" when that copy's hash is not E037's (black or 0xb6067a95fa98de2d), so a failed set
copy never becomes a verdict. Rows keep the kit's reset (E1097: the set survives it; pair d tests
that again). The stage stops on a probe row with no echo (r23-pk's hook) and on any fault. Either
verdict answers the question (the fill loads, or not and the copy is E037's path): **retire Q181**.
It also narrows Q050's YUV clause, whose text still says formats 28 and 29 read black in a fill
(E568, corrected); the fold appends that note.

**Kit fit.** Yes: rows in table order, `expectdiff reads:hash` on the copies as r23-pk, a pair
scorer in the session's `score/`. If a stage is re-staged it reruns from its first row, so a pair
is never split across attempts. No new kit word.

**T2 instead (not recommended).** `probe --csc-load zero|bt601` would run the set copy inside the
probe's process before its job and print its hash, so one row per pair (8 jobs fewer, ~4 min) and
no order dependence. 2 h of tool work for no added retirement.

### 2.3 Q123's held-out rows (no tool; r25-q123)

**Open (788b62c was not merged, so Q123's text is the pre-E1098 one):** the counter's carry into
bits 16 and 17 (E1098: held out, 7 of 7), the step (E1098: an offline fit only), and every index
256 to 8191 (E1098: a sequential run to word 8100 held out, the lapc to word 590 a control). The
lead's reasons: the step and the indices past 256 need held-out rows.

**Rows** (t22, `--place OFF=PROG --place-form cbase`, E492's read and jump programs from
`probes/usse/place-more.toml`, pads as E1098's `gen/q123.py`):

- q123s (code step, held out): four new placements, frozen before the run with their predicted
  links `(X mod 0x80000) / 8 + 2` and the lapc landing at link + 8, chosen so that every other
  power of two that fits five or more of the ten old links (E492: 0x40000 seven, 0x20000 and
  0x100000 five) and no step at all predict a different link (X mod 0x80000 at or above 0x40000,
  X mod 0x100000 at or above 0x80000): 0x0c3010 (0x8604; 0x40000 gives 0x0604, 0x100000 0x18604),
  0x2ca7f8 (0x9501), 0x3d0100 (0xa022), 0x1c8008 (0x9003); the generator checks every multiple of
  8 that fits the ten old links against them (only 0x80000, E1098). Control first: E492's 0x300008
  (link 0x3) repeated. 5 placements x
  read + jump = 10 jobs.
- q123w (indices past 256, held out): an 8192-word program at 0x40000 (E1098's in-step form);
  lapc to six and ba to four target words drawn by a seed fixed in PREDICTIONS before the run from
  256 to 8191, 256 and 8191 included; o0 names the landing word. Control: E1098's c-lapc (word
  590). 11 jobs, or one job per target pair if the generator chains two hops [infer].

21 jobs, ~10 min, safe (E1098: 10 such jobs, no fault). Frozen H-STEP80000 against "any other
step" (the predicted links), H-INDEX (every drawn target lands on itself) against H-WRAP256 (the
probe's own page). **Retires Q123** if all held-out rows hold, with "every index" read as E1098's
sequential run plus the drawn landings (R24-4); the fold can then take 788b62c's text over.

## 3. HACKING and kit upkeep (in P1)

- "Known tool weaknesses": the `probe --poke` entry leaves (its own condition, "stays until r23-pk
  has run", is met: E1096 repeats match, E568 has its correction). The `tri --depth` default size
  entry stays as R22-7 a left it. The sgx-sim, r5-events and texmodel entries stay.
- A new entry if R24-1 is not a: "probe prints the first 32 changed scratch dwords" (as E1096).
  With T1 it is listed with its fixing commit instead, and with the records it limited (E391,
  E1096: sa32-sa63 not read).
- The kit's "Readings" list gains: the colour-space set survives the runner's reset and later jobs
  (E1097); a YUV row's reading depends on the last job that loaded a set, so it is scored against
  the set copy in front of it (section 2.2).
- Observed, not a weakness [infer]: `probe_scratch` scans the whole `--scratch-pages` buffer, so
  `--scratch-show all` costs nothing extra.

## 4. Packages

### P1 (tool only, one agent, ~2 h; sonnet suffices)

Branch `r24-tooling` off main 7f214e5 in the lead's named worktree, its own `CARGO_TARGET_DIR`
(no cargo needed: C and pytest). Tests first: T1 (2.1) with the mock's dirty-scratch switch, the
usage texts, the HACKING edits of section 3. Recipe `closing24/k24/build_tool24_laptop.sh` from
`closing22/k22/build_tool22_laptop.sh`: bundle, source sha256 pinned, `make CC=gcc
build/sgxfive-test` (~50 s), `make check` with 0 failures. The lead runs it over the cable and
writes `TOOL24.built`. No module change, nothing installed. Laptop build ~3 min with the check.
**Later session:** r25-sa64.

### P2 (optional, one agent, ~2 h; only if R24-2 b)

T2 on its own branch or on P1's, the same recipe (t24 includes both if merged first). **Later
session:** r25-csc in its one-row-per-pair form.

### No module package (R24-5)

No retirement needs a module change this round. N1 (Q109, low, conditional) and N2 (Q068, medium)
stay listed for the user; each needs a ~45 min laptop module build and a one-shot boot.

## 5. The round 25 sessions

| session | tool | stages (jobs) | questions | record | wall | class | kit fit |
|---|---|---|---|---|---|---|---|
| r25-q123 | t22 | q123s (10), q123w (11) | Q123 | E1102 | ~10 min | safe | yes |
| r25-csc | t22 | csc (16) | Q181 (Q050 narrow) | E1103 | ~8 min | safe | yes |
| r25-sa64 | t24 | gate (2), q019 (56) | Q019 | E1104 | ~28 min | safe | yes, world prints 64 lines |

- **r25-q123** (the small session): module E0CC4027 as loaded, no knob, `#limit 0`, control rows
  first with `on_stop = "end"` if a control fails; scaffold with `--srcversion
  E0CC40275493F8AEAD8180B`. Can run now; it can share one sitting with r25-csc (two stages, ~18
  min).
- **r25-csc**: 2.2's table; stop on a missing echo or any fault. Can run now.
- **r25-sa64**: gate = E1096's pk-e391 and pk-e125 rows with `--scratch-show 64` (sa0-sa31 must
  read E1096's; sa32-sa63 printed, no "more changed" line), then E391's 40 jobs and 16 held out
  at 3 and 6 rows (4 attribute sets x 2 runs each). The session world prints 64 scratch lines.
  After P1's t24 is built.
- Order: r25-q123 and r25-csc first (no build), P1 meanwhile; r25-sa64 last. Each under the 45
  min sitting limit with one re-stage.

## 6. Retire summary if every frozen form holds

Without any tool: Q123 (2) and Q181 (1). With P1: Q019 (2) if H-ROWS holds out non-flat and
R24-3 a. Up to 5 value points and 3 questions from ~2 tool hours and ~46 min of laptop jobs.

## 7. R24 decisions for the user

1. **R24-1 Q019's sa32-sa63 print.**
   - a) P1: `probe --scratch-show N`, default 32, t24 built on the laptop (recommended: E391's
     program byte for byte, with E1096's sa0-sa31 as an in-row control).
   - b) No Q019 work this round.
   - c) No tool: a new `sa_hi_dump.s` storing sa32-sa63 at dwords 0-31, run on t22.
2. **R24-2 Q181's colour-space reset.**
   - a) The kit as it is: an E037 set copy in front of each probe row, scored in pairs (recommended:
     no tool hours, the same retirement).
   - b) P2: `probe --csc-load zero|bt601`, the reset inside the probe's process.
3. **R24-3 Q019's layered-background clause (E973 at 0 rows).**
   - a) Move it to Q066 at the fold (that scene's words are Q066's), so a fill-side answer can
     retire Q019 (recommended).
   - b) Keep it in Q019: Q019 then only narrows this round.
4. **R24-4 Q123's "every index from 256 to 8191".**
   - a) E1098's sequential run to word 8100 plus ten drawn held-out landings answer it
     (recommended).
   - b) Also run every index as a landing (8000 jobs: not feasible; Q123 would stay open).
5. **R24-5 The other tool and module items (T3 kreg, T4 filtered copy, T5 kick flags, N1, N2).**
   - a) Not this round (recommended: each below 0.35 value points per hour; T3 needs a rule change).
   - b) Name one to plan in round 25.
6. **R24-6 Sittings.**
   - a) r25-q123 and r25-csc in one sitting now on t22, r25-sa64 after t24 (recommended).
   - b) Three separate sittings.
   - c) All three in one sitting on t24 after P1.
