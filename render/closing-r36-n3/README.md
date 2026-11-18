# r36-n3

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 main b9098a41fc8d (kit/ is that
commit's blobs) and resgx545-data 6b29384403f5, module srcversion C01FB3203FDA4FEF01E4891 (fork
c78059370315: one own-task `emitpds` form, debugfs `own_code`, `own_arm`, `own_res`), laptop prefix
`r36n`, HostKeyAlias `cedar`. Design: `closing29/kernel33/design.md` (N3, §3 readings and controls);
plan row: `closing29/plan/rank-round34.md` (N3, Q128). **Flagged** (the user approved: user present,
reset ready): stage own runs our own firmware task, a planned firmware break if wrong. Same-value
variant only. Records reserved: **E1148-E1155**. Built offline, frozen, not staged, not run.

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, recipe
  `data:render/closing-r30-pde/lead/build_tool30_laptop.sh`; r35-sa's binding): the health tool (the
  kit's health pair and the own-task gate, `FWTASK_HEALTH_TOOL`) and stage post's two rows.
- The own task: `owntask/emitsa.blob`, written by `tools/fwtask/fwtask.py OUTDIR
  asm/fwtask/emitsa.s` at b9098a4, sha256 3dc8152d846c... = `asm/fwtask/fwtask.map`'s `emitsa` at
  b9098a4 (the freeze pins the map). Our own code, not firmware-derived.

## Stage own: 10 jobs, about 1 minute (alarm 900 s), flagged, on_stop "end"

The kit arms `emitsa` once after the stage's first reset and health pair (`slots=0x1 entry=0`; the
kernel patches the `emitpds` sources with its image's control word, address >> 4 and 0, and builds
the image with V0, V2 = TA3DCtl dwords 0 and 2), runs each row with no reset between (one tester
command 1 each, run id = the row's place), keeps the results page and the gate (t30 fill and
triangle with the task armed) after each, and disarms with fwtask_run.py's reset at the end.

Entry 0 (the general task, the tick): slot 1 = M1 0x5a5a3301 and the run id, cmd = 0, fence, the one
`emitpds`, then the closed task. The image: `douta` V0 to attribute 0, `douta` V2 to attribute 2,
`doutu` entry 1. Entry 1: slot 2 = pa0-pa3, slot 3 = sa0-sa3, slot 4 = M4 0x5a5a3302 and the run id,
echo, state 2.

| rows | set | the host's fill of slots 2-4 (params dwords 72-83) |
|---|---|---|
| e1-a, e2-b | fit (exploration) | A 0xdeadc0de, B 0x0badf00d |
| h1-a ... h8-b | heldout | A and B alternating |

## Hypotheses (predictions/own.tsv, frozen; score/score.py)

V0-V3: TA3DCtl dwords 0-3 in each row's own snap0 (the kernel's regs file; on 7CE8E38E they were
0x32004000, 0x32005000, 0x32002000, 0: r35-sa, E1144).

- **H-PA**: pa0 = V0 and pa2 = V2 (the emitted `douta` lands in the started task's primary
  attributes, as the event path does, E146/E532).
- **H-SA**: pa0 != V0 and pa2 != V2, sa0/sa2 = V0/V2 unchanged (shown only as "not pa": the values
  are sa's own, design §4).
- **H-NONE**: entry 0 ran (slot 1) and entry 1 left no trace (no M4, no state 2): the image did not
  start our task. Such a job never reports done, so the runner stops the stage at the first row
  (rc 4) and the session ends; score the kept directory by hand.

Controls (every row; all can fail): E0 slot 1 = M1 and the run id, cmd 0; E1 slot 4 = M4 and the run
id, state 2, echo; SA sa0-sa3 = V0-V3 (else the firmware's attributes changed); PA13 pa1, pa3 not V0
or V2 (no `douta` off its attribute). A row with exactly one of pa0 = V0, pa2 = V2 (a split landing)
fails both H-PA and H-SA.

## Rule (score/score.py, frozen)

N3 DECIDED-PA (H-PA held on >= 6 of the 8 held-out rows, none FAILED, every control PASS:
sgx-sim/fwsim model emitted `douta` to pa), NOT-PA (H-SA likewise: weak; a distinct-value follow-up
is a separate decision), NONE (H-NONE on the first kept row with E0), else OPEN. Q128 NARROW in
every outcome, never RETIRE (its clauses are a client emit's fault page, s0-s2 and the addend
window).

## Stage post: 2 jobs, under 1 minute (alarm 600 s), flagged

After own's disarm: p1-tri (`tri`) and p2-fill (`fill`), t30, the health pair's bare argv, controls
`reads:diff` frozen at 0: the stock firmware draws exactly. Flagged only because it follows a
flagged stage.

## Stops

`#limit 0` in both stages: no planned fault or hang, so any fault or hang (rc 4), a runner stop (a
job not done: rc 4), a failed gate (16), a failed arm (26) or a failed disarm (13) ends the session
(the driver ends on every status but 0 and 24). run/hooks.sh stops own (rc 24; on_stop "end" ends
the session) after a job whose cmd was not cleared, whose state is not 2 or echo not the run id,
whose slot 1 or slot 4 is not its marker and run id, or whose sa0-sa3 are not TA3DCtl dwords 0-3 in
the row's snap0 (r35-sa's values when a snap0 has no ta3dctl line: only the kit mock's fake regs).
Post stops (24) on a draw without `job: ok`/`fill: ok` and `diff: 0`. Unplanned events: at most 1
(the first ends the session). Never retried, never rebooted.

## The mock's worlds

model (H-PA): 0; sa (H-SA): 0; sabad (sa0 wrong: own 24, ends); nomark4 (no entry-1 marker: own 24);
ownstop (no done: own 4); owngatebad (16); ownarmbad (26); postbad (post 24, driver 0). The
library-mock replay runs post's two t30 rows on t30's pinned source; owntask rows are not
sgxfive-test rows. The kit mock's snap0 has no ta3dctl lines, so its scored worlds print "cannot
tell" (the scorer never uses the hooks' fallback); tests/attempt.py builds kept attempts with them
for tests/test_score.py.

## Replay vectors

own: `refused` for now: no sgx-sim/sgx-pipe test runs an own EDM task's `emitpds`; the measured
landing (pa or not) becomes fwsim's M2 kick change in the fold, test first (E1133's sa landing), its
table `n3-own` (`closing_tables.py`, format `sgx545-tables`) built from the kept pages and snap0s
alone. post: `refused` (the health pair; no measured quantity beyond exactness).

## Layout and commands

gen/make.py (+ gen/pins.py, gen/constants.txt), owntask/emitsa.blob, score/score.py, run/hooks.sh,
mock/world.py, tests/ (attempt.py builds own attempts), PREFLIGHT.md, FOLD-NOTES.md. Publishable:
everything; nothing for data-private (the kept pages hold our task's stores and TA3DCtl pointers the
kernel allocates).

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python`, which the offline tests use unless
  `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` (done by the builder).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .` (stop codes:
  kit/session.py). After the run: `python3 score/score.py own out/ATT/own` and `python3
  score/score.py post out/ATT/post` (also after a stop: the driver scores only stages that ended 0
  or 24). The driver keeps its own logs, `out/stage.log` and `out/ATTEMPT/run.log`; tee nothing into
  this directory's top.
