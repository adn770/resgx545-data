# r19-own

Round 19's S3 (closing19/plan/rank-round19.md section 4, DECISIONS-R19.md): Q192 (own2, E1084) and
Q191 (own1, E1085) on t18b's kept copies of a kept first context. Built on the session kit from
resgx545 6809cddd24ce, data 95df71e98, module srcversion E0CC40275493F8AEAD8180B (the round's
fallback B60AB0B4 needs a twin of this session: only `srcversion` and the frozen
`render_final_pb_pages` knob differ; ask the builder). Laptop prefix `r19o`. Safe class: no
planned fault, no hang, no expectfault row; nothing in it assumes cachix (travel cable).

## What runs

Every row is E631's form on t18b (sha256 58e79855..., source ec50498, recipe
`lead/build_tool18b.sh`, built line `lead/TOOL18b.built`):

    tri --width W --height H -n 1 --keep-overflow --wait-ms 20000 --ctx2 --close-first-early \
        --kept-copy "$W" --words "$W" --kpoke-render 1:ta:7^=F

with `dbg:render_keep=1` (the first context's early close keeps its TA data; without it the
second context's render faults, E631) and `dbg:render_pb_pages=P` (both contexts). t18b copies
debugfs render_kept to `kept.closed.1.bin` right after the close, before the second context's
render, and to `kept.1.bin` after that render, before any other close. The DPM control, OTPM and
state pages are found by the fork's layout (score.py `layout`, tested against the fork's KUnit
table): 64x64 pages 1, 2, 3; 1024x768 pages 4, 5, 6; 2048x1536 pages 0x10, 0x11, 0x12.

| stage | rows | jobs | question |
|---|---|---|---|
| own2 | o2-c-a (control, also E631's case), o2-c-b, o2-4 (fit), o2-p30, o2-p24, o2-2k (held out) | 6 | Q192 |
| own1 | o1-4 (control), o1-c-a, o1-c-b (fit), o1-big-a, o1-big-b, o1-p200 (held out) | 6 | Q191 |

Order: own2, then own1 (neither gated; own1 runs whatever own2 shows). 12 jobs; about 13 s a job
with reset and health (o2-2k, two 2048x1536 contexts in partial renders, maybe 30 s): about 4 min
of jobs, 7 min with staging. Alarms 900 s and 600 s.

## Hypotheses (frozen in predictions/, written by gen/make.py)

- own2 (Q192): H-RSTORE: the closed copy's state page holds the owner's lists (18 non-zero dwords
  at 0x28, E464 and E631's solo; more than 0 at 0x30, 0x24 and 2048x1536) and the after copy's is
  0, so the zero E631 read after the tool exits is made between the close and the second
  render's end. Rivals: H-EARLY (both 0: the close or the second context's creation) and H-LATE
  (both hold the lists: the zero comes after the second render, at its close). Each row also
  prints the pages that differ between the two copies and the after copy's non-zero words of the
  control, OTPM and state pages (what the store writes).
- own1 (Q191): (a, c) H-RENDER: the 64x64 owner's words (0x00200047, 0x04000417, 0x00020001, 2)
  are in no closed copy and in every after copy, against H-CLOSE (in both); (b) the 1024x768
  owner at P 0x422 (no partial render): H-COUNT (state words (U << 16 | head), tail with U 0x11 to
  0x15) against H-CONST (0x00020001, 2) and H-NONE (0, 0; E631's partial owner).

Controls that can fail: o2-c-a reads `ovf=1 kept=2 size=69632` (the first render overflowed, both
copies made, the 1024x768 TA data); o1-4 reads `ovf=0 kept=2 size=24576` and the scorer fails it
if any owner word shows in either copy with flag 0x4 (E631: none).

## Stops

- A copy file missing (render_keep not taken, render_kept unreadable): the runner stops (23) and
  the session with it.
- hook_check (rc 24, the stage stops, the next runs): fewer than two copies made, or an own2 row
  whose first render did not overflow (no partial-render owner).
- Any fault, hang or failure: the kit's stop (4), the session ends. The one known fault of this
  form is the close without keep (E631), which the knob's read-back (rc 19) excludes.
- A control without its reading: the premise stops the stage (25).

## Mock worlds

`model` (H-RSTORE, H-RENDER, H-COUNT), `alt` (H-LATE, H-CLOSE, H-CONST), `early` (H-EARLY,
H-NONE), `nokeep` (the closed copy fails: 23), `noovf` (no overflow: own2 24, own1 runs), `fault`
(the second render faults in own2's second row: 4).

## Replay vectors

Both stages' measured rows become `vectors/closing/r19-own/own2.table.json` and `own1.table.json`
(`closing_tables.py`, format `sgx545-tables`) with `replay = refused`: neither sgx-sim nor
sgx-pipe models a kept context's TA data or the store after another context's render
(crates/SIM_UNMODELLED.toml's E631 entry, "dpm: not modelled or refused"). The tables are built
from the kept copies alone (`out/`); the freeze pins E631's four kept records the tests read.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python`.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top.

No firmware-derived file: nothing here goes to data-private.
