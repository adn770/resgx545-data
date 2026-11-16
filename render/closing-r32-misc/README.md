# r32-misc

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 f09c011 on branch `r32-miscinfo` and its kit re-copied
from the branch tip 80d9f2a1b3dc (the kit word `pre:miscinfo`, 45bbaaa, and the fake laptop's boot
answer and CR_CACHE_CTRL, f09c011 and 80d9f2a; not merged: the lead stages from a named commit),
data 6b5c5112a06e, module srcversion 7CE8E38EDB97FC5EA4F6C90 (fork 8bc0877e8603), laptop prefix
`r32m`, over the travel cable. **Safe class** (user decision 2026-11-16): no knob, no kreg, no
register write, no planned fault or hang; the one new step is the kit's `pre:miscinfo`, a debugfs
read that sends the firmware one GETMISCINFO command. Records reserved: **E1126** (m1) and **E1127**
(m2). Question: Q111 (E1122, E1123).

## Why

E1123 ordered the kick pass's BIF write before CR_CACHE_CTRL's change in 2 rows and read the change
as the firmware's own `| 0x10000000` at INVAL_DATA (cache-control bit 3, E013) [infer]; in 22 rows
the BIF write was shorter than a sample. The design closing29/r31-cc/fold/next-miscinfo.md names the
direct test: a served kick whose command carries no INVAL_DATA, right after a reset.

- **H-CC-FW**: bit 28 is the firmware's response to INVAL_DATA: 0x0804 stays 0x0000ffff after a
  served GETMISCINFO without it.
- **H-CC-HW**: any served kick sets bit 28: 0x0804 reads 0x1000ffff after it.

**Already in the kept data, post hoc** (found while building; the design note missed it): the fork's
boot ends every reset with its own GETMISCINFO (`sgxfive_ident_ask`, sgxfive.c, at the fork pin),
sent with the firmware file's cache control (meta word 30, INVAL_BIF_PD 0x2 per the design note and
doc/specs/boot_sequence.md; no bit 3), and the kernel logs its answer (`SGX firmware: core 545 ...,
answered after N us`). r31-cc's kernel.log (pinned) has 67 resets and 67 such answers (130 to 285
us), and all 52 of its snap0 snapshots read 0x0000ffff 3 s after them. So every kit control since
the boot ask landed is already a served kick without INVAL_DATA followed by 0x0000ffff: H-CC-HW as
"any served kick" is contradicted post hoc [infer: the kernel's code orders the ask before the reset
write returns; nothing in the kit's snapshots times it]. This session makes it a frozen, held-out
test with a second, kit-checked kick: the word's command is sent with no cache control pending at
all (`sgxfive_command` clears it after the boot's), and its answer is kept and checked.

## What runs

Every job: t10 (`~/sgxfive-test-t10`, sha256 9bedc2d6..., source a581c06) `tri --width 64 --height
64`, after the kit's reset; m2's under regtimeline (`rt`, sha256 079f6359..., read only, `1.5 0.5
0x0804,0x0b14 -- ...`). In run order:

| stage | rows | word | what it reads |
|---|---|---|---|
| m1 | 9: c1, 01-03, c2, 04-06, c3 | on 01-06 and c2 | snap0, snap9 0x0804; the answer |
| m2 | 2: c1, 01 | on both | the triangle's change, timed |

11 jobs. Per row with the word: reset, then the kit marks `miscinfo NAME`, reads debugfs `miscinfo`
(`sudo -n timeout -k 5 10 cat`), keeps it as `NAME.miscinfo`, checks it was served (else rc 19
before the job), then snap0, the triangle, snap9. Time: r31-cc's 52 jobs took about 12 minutes
[infer], so about 3 to 4 minutes of jobs, 6 to 8 with staging. Alarms 900 s a stage.

## Hypotheses (frozen: predictions/*.tsv from gen/make.py; every non-control row held out)

- m1, m2 rows with the word: **H-CC-FW** (snap0 0x0804 0x0000ffff; m2 also the timeline's first
  sample, `ccfirst`) against **H-CC-HW** (0x1000ffff). A row decides only where its premises hold:
  the read was served (`mi`) and the triangle after it still set bit 28 (snap9 0x1000ffff); else
  cannot tell.
- **H-CC-ONE**: snap9 0x1000ffff after the triangle (E1122, E1123; r31-cc 52 of 52); m2: one change,
  to 0x1000ffff.
- **H-CC-LAT** (m2): the triangle's change 10 to 40 ms after the tool starts, as without the read
  (E1122 18.3 to 25.2).
- **H-MI-LAT**: the word's GETMISCINFO answered in 100 to 400 us (the boot's 130 to 285, post hoc).

Controls, all can fail: m1-c1 and m1-c3 (no word) diff 0, cache 0x0000ffff, cache9 0x1000ffff and
**kicks 1** (the boot's answer logged after the last `SGX boot: kicking the EDM` before the row's
snap0 mark); m1-c2 and m2-c1 (the word) diff 0, mi 1 and **kicks 2** (the boot's and the word's);
m2-c1 also ivl 400 to 3000 ns. A `kicks` that is not the frozen count fails its control (the read
reached the firmware twice, or the boot's ask was not answered). m1-c2's and m2-c1's cache readings
are scored as held rows'.

## What decides, what cannot

- **Decides**: snap0 0x0000ffff in the decided word rows (H-CC-FW held, H-CC-HW refuted): a served
  kick with no cache control at all does not set bit 28, so its setting needs the command's
  INVAL_DATA (the triangle's 0xb and the fill's 0x8 carry it, E1123); with the controls' kicks, the
  boot's 0x2 kick does not either. 0x1000ffff in them: H-CC-HW held, and the controls' own
  0x0000ffff after the boot's kick then says the two kicks differ (first after the boot, or its
  0x2) [infer]: the fold names a correction to E1123's [infer] clause. H-CC-ONE and H-CC-LAT say
  whether the read changes the triangle's own change.
- **Cannot**: whether bit 28 is the firmware's literal write or a hardware response to the
  firmware's INVAL_DATA work (both need bit 3; a kick carrying INVAL_DATA alone is not in the kit);
  the value the firmware's own read after a TA kick returns (inside a sample, E1123); when
  CR_USE0_SERV_EVENT counts within a pass; anything about the other CR_EVENT_STATUS bits Q111 names.
  The sampling of m2 starts 0.5 s before t10, after snap0, so it does not time the read itself.

## Stops

hook_check (rc 24): a row that does not draw exactly or lacks `tri: 1 renders ok`; in m2 a missing
or cut timeline or regtimeline's rc not 0. The kit: a read not served (rc 19, before the job), a
FATAL line after it (3), a fault or hang after it (4). Both stages declare `on_stop = "end"`: a stop
ends the session. A control without its reading: 25. Any fault or hang in a job: 4. `#limit 0`
everywhere.

## Mock worlds

`model` (both 0), `nodiff` (m1 stops at its first row, 24), `miscinfobad` (the kit's token: the read
prints a MISMATCH, m1 stops at m1-01, 19), `notl` (m1 runs, m2 stops, 24). The kit's fake answers
miscinfo as the kernel does, logs the boot's answer after each reset and shows 0x0804 as the
laptop's snapshots read it (H-CC-FW's world); its samples are 1 us apart, so m2's control fails on
ivl there, as r31-cc's did. The scorer is tested on r31-cc's kept rows and on synthetic kept
directories that decide both ways and that cannot tell.

## Commands

- Offline: `bash tests/run_all.sh`. Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Freeze: `python3 kit/session.py freeze .` (done). Laptop: `python3 kit/session.py stage .`, then
  `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE out/ATT/STAGE`.

Fold notes: FOLD-NOTES.md. No firmware-derived file: nothing here goes to data-private. Python is
the repo's own `.venv` (`$HOME/src/resgx545/.venv/bin/python`); every command is run through its
interpreter.
