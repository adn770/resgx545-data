# r20-own

closing20/plan/rank-round20.md section 4 (S2): Q191 (whose scene, which kick; E1091) and Q192
(regimes, a repeat, whose lists; E1092). Built on the session kit from resgx545 c0f8c41fbbf9, data
ba3990f01, module srcversion E0CC40275493F8AEAD8180B, laptop prefix `r20o`. Safe class: no planned
fault, no hang, no register write. Nothing assumes cachix (travel cable). Tools: t18b (sha256
58e79855..., source ec50498, recipe `data:render/closing-r19-own/lead/build_tool18b.sh`, as
r19-own1b binds it) under rt (regtimeline 079f6359..., read only, as r19-dpm binds it); t10 for
the health pair.

## What runs

Every row is E1087's form under regtimeline (`0 0.3 REGS --`):

    tri --width 1024 --height 768 -n 1 --keep-overflow --wait-ms 20000 --ctx2 \
        --close-first-early --kept-copy "$W" --words "$W" --kpoke-render 1:ta:7^=0xc [--move
        1:DX,DY]

with `dbg:render_keep=1` and `dbg:render_pb_pages=P`. `--move 1:` moves the owner's triangle only.

- ow (4): ow-c (control, P 0x422, unmoved), ow-m1-a, ow-m1-b (fit, `--move 1:-112,-80`), ow-m2
  (held out, `--move 1:64,64`). REGS 0x0620-0x0634, 0x0658, 0x065c, 0x0674, 0x0694, 0x0698,
  0x0700-0x0728.
- owt (2): owt-a (control and fit), owt-b (held out), unmoved at 0x422, REGS 0x062c, 0x0634,
  0x0694, 0x0698 only.
- owp (5): owp-30-a (control and fit), owp-30-b (fit), owp-30m (held out, `--move 1:-112,-80`),
  owp-2c, owp-34 (held out); ow's REGS.

11 jobs, about 15 s each with reset and health: about 3 min of jobs, 6 to 8 min with staging.
Alarms 600, 300, 600 s.

Deviation from the plan: the plan's move -128,-96 puts vertices on macrotile edges (768, 576),
where the pixel-centre and the conservative tile covers differ ({0,1,2,4,5,6,8,9} against
{0,1,2,3,4,5,6,8,9,12}); gen/cover.py moves by -112,-80 instead, where both give
{0,1,2,3,4,5,6,8,9,12} (stable to +-8 px). 64,64 kept (both give {0,1,4,5,6,7,9,10,11,13,14}).
owt and owp had no control in the plan: their first rows are controls too (r19-own's own2 form).

## Hypotheses (frozen: predictions/*.tsv from gen/make.py)

- ow: H-SECOND (pages 4 to 6 after the second render equal E1087's o1-big-a dword for dword,
  whatever the owner's move) against H-OWNER (the non-zero lists 0 to 15 of page 6 are the moved
  cover). ow-c: ovf 0, kept 2, size 69632, closed pages zero, after pages E1087's.
- owt [infer]: H-TA (0x062c holds the owner's state base, words.101 rtds:11, with a task write in
  0x0694/0x0698 after the first sample with another state base and before that base's last task
  write) against H-END (after it); no such sample: cannot tell. Also read on ow and owp rows.
- owp: H-REGIME by the owner's regime read (ta3d.101.bin dword 38 non-zero = raised, E625):
  raised, page 6 zero; not raised, E627 lists, and at 0x30 unmoved E1084's o2-p30 10 dwords
  exactly (a repeat; owp-30-a is the control on it, ovf 1). owp-30m also H-SECOND (o2-p30's
  dwords) against H-OWNER (other lists within the moved cover), group owpw.

An empty copy right after the close (E1085) makes its row (or control) cannot tell, never a stop.

## Stops

- hook_check (rc 24): the copy after the second render not made, or the copy right after the close
  empty in two rows in a row (the stage stops; the next stage runs).
- A copy missing (render_kept unreadable): the runner stops (23). Any fault, hang or failure: the
  kit's stop (4). A control without its reading: the premise stops (25). `#limit 0` everywhere.

## Mock worlds

`model` (H-SECOND, H-REGIME, H-TA), `alt` (H-OWNER, H-END), `oneempty` (one empty copy: goes on),
`twoempty` (two in a row: ow 24, owt and owp run), `nokeep` (23), `fault` (4).

## Replay vectors

No table: closing_tables.py has no kind for kept TA data copies; ow, owt and owp are refused (no
simulator models a DPM owner's kept pages; the records go to crates/SIM_UNMODELLED.toml as
E1084's and E1087's).

## Commands

- Offline: `bash tests/run_all.sh`. Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Freeze: `python3 kit/session.py freeze .` (done). Laptop: `python3 kit/session.py stage .`,
  then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE out/ATT/STAGE` for ow, owt, owp.

No firmware-derived file: nothing here goes to data-private.
