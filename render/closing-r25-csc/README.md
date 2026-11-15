# r25-csc

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 7f214e511d6a.

## What runs (rank-round24.md 2.2 and 5; DECISIONS-R24 all (a))

Tool t22 (`~/sgxfive-test-t22`, sha256 9b62d315..., built on the laptop from resgx545 3c68e8d by
`lead/build_tool22_laptop.sh`, `lead/TOOL22.built`, the recipe pinned as r23-pk's published copy);
health fill and triangle with t10. Module E0CC40275493F8AEAD8180B as loaded; no knob, no debugfs
write of ours, no register write, no `--kpoke`. Safe class; `#limit 0`. Laptop prefix r25c.
Record E1103 (rank-round24.md section 5).

One stage, `csc` (Q181; Q050's YUV clause narrowed), 16 jobs in table order. The kit runs no
health job between rows (only at the stage's ends and after a fault, which stops the stage), and
the colour-space set survives its debugfs reset (E1097), so each row reads the set the rows
before it left. Per format F of 28 and 29 (E568's fy-F-p0 program, r23-pk's bins):

| row | job | set | H-FILLLOAD | H-FILLIGNORE |
|---|---|---|---|---|
| yF-zc | E037's UYVY copy loading set 0 with zeros | control | hash 0xd3522437a14b6325 (black) | same |
| yF-a | the fill, unpoked | control | black | black |
| yF-b | the fill, poked: set 0 BT.601 | fit | conversion | black |
| yF-c | the fill, unpoked | fit | conversion | black |
| yF-bc | E037's UYVY copy loading set 0 with BT.601 | control | hash 0xb6067a95fa98de2d | same |
| yF-d | the fill, unpoked | control | conversion | conversion |
| yF-e | the fill, poked: set 0 zeros | held out | black | conversion |
| yF-f | the fill, unpoked | held out | black | conversion |

Conversion is E1097's measured pixels (r23-pk's kept fy-F-p0-csc, pixel sha256 frozen in
predictions/csc.tsv; E037's formula on texel x mod 16, which `mock/world.py` reproduces), black
0xff000000 at 2048 pixels. Each fill is scored only when every control of its half before it
passed (zc, a for b and c; bc, d for e and f), else cannot tell; headlines per model and half
(fit, heldout). Every poke row reads its `probe NAME: poked ...` echo as a premise (scorer) and
stops the stage when its echo count is not its poke count (run/hooks.sh). Either verdict retires
Q181 (the fill loads the set, or it does not and the copy is the path that loads it).

About 8 minutes (16 jobs, reset between jobs, health at the ends). Stops: a missing echo, any
fault or hang (kit). Mock worlds: model (H-FILLLOAD), ignore (H-FILLIGNORE), clears (a reset that
clears: the held-out half's d control fails), copynoop (the zeros copy does not load: the fit
half's zc fails), noecho (the hook stops the stage). Which world the laptop is in is not
predicted beyond the frozen table; E1097's post hoc reading (a fill loads) is H-FILLLOAD, held
out here by e and f.

Deviation from the plan's table: 16 jobs as the plan's count, so one copy per half (zc before a
and b, bc before d and e) rather than a copy before each of a, b, d and e (20 jobs); a and d,
the unpoked fills right after each copy, are controls that read the state b and e start from.

Firmware-derived files: none (E568's published programs, E037's copy of E028's source).

## Replay vectors

- csc: `closing_tables.py` rows of each fill's pixel sha256 and each copy's hash, in run order;
  replay: sgx-sim `tex.rs` (`the_yuv_texel_model_is_opaque_black_for_an_unloaded_set`) for the
  rows whose set is zeros; rows after a load are `refused` (the sim stops on colour-space load
  jobs, E568's note) until the fold models a kept set. Pinned: r23-pk's kept fills and copies.

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
