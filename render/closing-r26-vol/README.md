# r26-vol

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 95445c7de9fd.

## What runs (rank-round26.md 2.1 and 4; DECISIONS-R26: R26-2 a)

Tool t24 (`~/sgxfive-test-t24`, sha256 fd15fce4..., built on the laptop from resgx545 1341034 by
`lead/build_tool24_laptop.sh`, `lead/TOOL24.built`, the recipe pinned as r25-sa64's published
copy); health fill and triangle with t10. Module E0CC40275493F8AEAD8180B as loaded; no knob, no
debugfs write of ours, no register write, no poke. Safe class; `#limit 0` in both stages. Laptop
prefix r26v. Record E1105. Question Q114 (Q300 narrows either way).

Every row is `probe --temps 32 --coords --pixels` of one of E567's programs (its case text in
`probes/texture/templates/tx_map.s`, assembled by usse-asm built from resgx545 95445c7 into
`debug/asm/`): the twiddled 16 x 16 format 12 texture, point, T0 0x07fe0000, T1 0x0c00f00f, T2
0x5caf0000, T3 0x00800800, smp3d with r26 the third coordinate.

| stage | rows | set | what |
|---|---|---|---|
| vc (5, gate of vb, on_stop end) | c-w0, c-w15 | control | E567's ty0-3d-w0, -w15: pixel sha256 2b49c848... (both) |
| | c-cube-w5, c-cube-w15 | control | E567's rt2-3d-w5, -w15 (TEXTYPE 2): 79970597..., 480213ab... (w acts: two images) |
| | c-w0b | control | c-w0 again: 2b49c848... |
| vb (40, gated on vc) | vb-B-w0, vb-B-w15 for 19 bits B | heldout | E567's w 0 and w 1.5 programs with T0 (r20) or T3 (r23) bit B flipped |
| | vb-t0b27-w0r, vb-t0b30-w0r | heldout | repeats of the w 0 job (E564: those bits read no name of the buffer) |

Bits (each ran on a twiddled texture without a fault): T0 14, 15, 16, 28, 29 (E564), 27, 30
(E564, E567); T3 8, 9, 15, 20, 21, 22 (E564), 11, 12 (E564, E1027), 10, 18, 27, 28 (E567, E722).
Not run, left to Q300: T0 0, 2, 31; T3 13, 14 (fault, E566), 19, 24-26; T1's size bits; T2.

Frozen (predictions/): H-NOVOL, every bit's w 0 and w 1.5 images equal at 2048 pixels (E567's
w3d=ignore, 8 of 8, with the bit set), against H-VOL(bit), the pair differs. A bit is cannot
tell when a job of its pair did not complete or print 2048 pixels, or its repeat differs from
its w 0 job. No fit set: the controls carry E567's readings; every bit row is held out. The
controls can fail (a reset that leaves state, a tool or texture path that changed since E567, a
TEXTYPE 2 that no longer reads w). Headline H-NOVOL over 19 bits (score/score.py vb).

Retires Q114 only under H-NOVOL 19 of 19 with no cannot tell and R26-2 a (the never-run and
faulting bits stay Q300's). If a bit acts, Q114 is answered in part (that bit is a volume
candidate) and narrows. Either way the fold appends the 19 bits under smp3d to Q300's note.

About 22 minutes (45 jobs, the kit's reset around each job, health at the stage ends). Stops:
a probe row without its 32 pixel rows (run/hooks.sh; in vc it ends the session), any fault or
hang (`#limit 0`; a fault in vc leaves vc's controls incomplete and the gate shut). vb runs only
when every vc control passed (score.py gate). Risk [infer]: the bits ran without a fault on
twiddled textures with E567's or E564's words, but never with smp3d and w 1.5 except T0 27, 30
and T3 10, 18, 27, 28 (at w 0.625); a bit that made w act as a volume slice could read past the
64 KiB scratch and fault: that is the stage's stop, not a finding to chase.

Mock worlds (mock/world.py): novol (H-NOVOL 19 of 19), vol (T3 9 acts: not supported, bit
named), drift (t0b27's repeat differs: 18 of 19), cubeoff (c-cube-w15 reads w5's image: control
FAILS, gate skips vb), nopix (no pixel rows: hook stop in vc, session ends, 24), fault (a vb row
faults: 4).

Deviations from the plan: none in rows or counts. The usse-asm used is built from the pinned
commit's sources (git archive) rather than the probe.py command line; the control programs
are checked byte for byte against E567's kept programs (tests/test_plan.py), and probe.py's
render is the same template substitution (no params in these tables).

Firmware-derived files: none (our own programs; E567's published dumps).

## Replay vectors

- vc, vb: `closing_tables.py texture` rows (the kit kind, `pixels/`: each row's 2048 pixels);
  replay `refused`: sgx-sim reads smp3d as smp2d only at E567's T words (`tex.rs` test
  `smp3d_is_smp2d_only_where_it_ran`); the flipped words are Q300's, and TEXTYPE 2 is refused
  in that rule itself. The fold may extend the rule to the bits that held (a sim change it
  names, not this session). Pinned: E567's kept images and programs.

## Commands

Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top (verify reports a new file there).
