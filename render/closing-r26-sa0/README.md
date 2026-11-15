# r26-sa0

Round 26's session r26-sa0 (closing26/plan/rank-round26.md 2.2, decision R26-3 a), built with the
session kit (resgx545 HACKING.md, "Session kit"), scaffolded by `tools/closing/new_session.py`
from resgx545 95445c7de9fd and resgx545-data e639458f08ca. Record E1106, laptop prefix `r26s`
(files under `~/scratch/r26s/`).

## What runs

Tool t24 (`~/sgxfive-test-t24`, sha256 fd15fce4..., built on the laptop from resgx545 1341034,
`lead/build_tool24_laptop.sh`, `lead/TOOL24.built`); health fill and triangle with t10. Module
E0CC40275493F8AEAD8180B as loaded; no knob, no debugfs write of ours, no register write, no
`--poke`, no `--pds`. Safe class only; every stage `#limit 0`. 8 jobs, about 5 minutes with the
runner's reset and health between jobs.

Question (Q126 clause 2): what `iaddu32` writes into sa0 when one writer alone writes it (E1061's
sa0 row, every instance writing, read other pairs' values: post hoc, sa0 shared). Every program is
a `probe --coords` fill (pa0 = (y << 16) | x, 2048 instances) over eight (r1, source 2) pairs, one
value stored to its own scratch dword a pair (dword k = pair k).

**The writer is a quad, not one lane (a deviation from the plan, from E513 [HW]).** The writer is
chosen as E513 chose it: `xor.testtaz.chan0 !c0, p0, r7, r9` (r7 = pa0, r9 = the writer's pa0)
and `!p0 br #m` over the body. The branch is decided per 2x2 quad from its TOP-LEFT lane's test:
the four lanes of the quad whose top-left lane is (0, 0) (pixels 0, 1, 64, 65) run the body with
the same values, and an odd lane selects nothing. So "(63, 31)" cannot be a writer: row s-6331
uses the quad whose top-left lane is (62, 30) (pa0 = 0x001e003e; pixels 1982, 1983, 2046, 2047;
the plan's (63, 31) is its fourth lane). One writer QUAD alone writes sa0: its four lanes write the
same value of a pair; whether they run in lockstep is not told (H-MIX would show it).

| stage | job | writer | destination | pairs | label |
|---|---|---|---|---|---|
| uc (gate, on_stop end) | c-e521 | every instance | r10 | E521's, E1061's u-ctl-e521 byte for byte | control (H-E521, E521's kept values) |
| uc | c-one-r10 | quad (0, 0) | r10 | E1061's u-sa0 pairs | control: the branch form, H-ZX 8 of 8 |
| us | s-00-a, s-00-b | quad (0, 0) | sa0 | E1061's u-sa0 pairs, runs a and b (same program) | held out |
| us | s-6331-a | quad (62, 30) | sa0 | the same | held out (another quad) |
| us | s-new-a, s-new-b | quad (0, 0) | sa0 | 8 new pairs (seed 26126), r1 low 0x8000-0xffff | held out |
| us | s-new-6331 | quad (62, 30) | sa0 | the new pairs | held out |

Per pair: `mov r1, #a`, `mov r2, #b`, `iaddu32.testtaz.chan0 sa0, p0, r1, r2`, `mov r3, sa0`, `stad
[r29,+#k], r3` (E1061's u-sa0 form); the controls store r10 directly. Then `idf drc0, bif`, `wdf
drc0`, `mov.skipinv.end o0, r10` for every instance (r10 = 0xc0de0001 preset in the branch rows).

## Frozen predictions (predictions/uc.tsv, us.tsv; PREDICTIONS.sha256 at the freeze)

- H-ZX: dword k = (r1 & 0xffff) + source 2 (E521), 8 of 8 dwords a row. H-SX: the sign extension
  of r1's low half (differs from H-ZX in 7 of 8 dwords of E1061's pairs, 8 of 8 of the new ones).
  H-MIX: E1061's reading: every dword the H-ZX value of some pair of the row, at least one not its
  own pair's. A dword changed outside the eight fails every model.
- Expected (planner, [infer]): H-ZX on all six held-out rows (E1061's other forms and E521 read it
  with every instance writing; the mixture was an effect of the shared sa0). A row that reads H-MIX
  would mean a quad's four lanes interleave. Retirement of Q126 (R26-3 a): H-ZX holds on all six
  held-out rows, the controls passing (clause 1 not observable by E498's rules, no run).
- Controls: c-e521 (H-E521) and c-one-r10 (H-ZX), both gate us. They can fail: the branch form
  into r10 reads another quad's lanes or nothing if the writer is mis-selected.
- Stops: a control without its scratch readout (premise, rc 25); the second row of a stage
  without its scratch readout (no writer quad stored: run/hooks.sh, rc 24); any fault or hang.

## Mock worlds (mock/world.py)

zx, sx, mix (all run); ctlfail (c-one-r10 off H-ZX: uc runs, the gate skips us); ctlnoread
(premise, rc 25); nobranch (us stops by its rule, 24); fault (rc 4); hang (rc 6).

## Replay vectors

- uc, us: `closing_tables.py` rows of the eight dwords per job (format `sgx545-tables`); replay
  `refused`: sgx-sim refuses these programs ("reads pa0 before the program writes it", checked on
  main's built sim, debug/sim_s00a.txt, not pinned) and has no quad branch; the value rule itself
  (E521: zero extension) is replayed by `usse-integer-iaddu32-value`. A refusal is the replay.

## Firmware-derived files

None (every program is ours; E521's kept vectors and E1061's kept outputs are published).

## Commands

Every command is run through its interpreter, never by its mode bits:
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). Tee nothing into this directory's top.
