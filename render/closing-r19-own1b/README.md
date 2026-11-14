# r19-own1b

r19-own's own1 (Q191; closing19/plan/rank-round19.md section 4, S3) again: the lead's decision
after r19-own's attempt 20261114-223625, whose own1 stopped at its first flag-0xc row because
t18b's copy of render_kept right after the first context's early close read 0 bytes (E1085;
[infer] the context is parked when its last reference goes, which can be after the close call
returns). Built on the session kit from resgx545 50606dc1cd12, data 95df71e98, module srcversion
E0CC40275493F8AEAD8180B, laptop prefix `r19o2`. Safe class: no planned fault, no hang. Nothing
in it assumes cachix (travel cable). Tool t18b as r19-own binds it (sha256 58e79855..., source
ec50498, recipe published by r19-own: `data:render/closing-r19-own/lead/build_tool18b.sh`).

## What runs

One stage, own1, 8 jobs in order, every row r19-own's form:

    tri --width W --height H -n 1 --keep-overflow --wait-ms 20000 --ctx2 --close-first-early \
        --kept-copy "$W" --words "$W" --kpoke-render 1:ta:7^=F

with `dbg:render_keep=1` and `dbg:render_pb_pages=P`: `o1-4` (control, 64x64, flag 0x4), `o1-c-a`
to `o1-c-d` (64x64, flag 0xc, fit: own1's two and the lead's two repeats), `o1-big-a`, `o1-big-b`
(1024x768 at P 0x422, held out), `o1-p200` (64x64 at P 0x200, held out). About 13 s a job with
reset and health: under 2 min of jobs, about 5 min with staging. Alarm 900 s.

## Hypotheses (frozen, as r19-own's own1; predictions/own1.tsv from gen/make.py)

- (a, c) H-RENDER: the 64x64 owner's words (0x00200047, 0x04000417, 0x00020001, 2) are in no copy
  made right after the close and in every copy after the second render, against H-CLOSE (in both).
- (b) the 1024x768 owner at P 0x422: H-COUNT (state words (U << 16 | head), tail, U 0x11 to 0x15)
  against H-CONST (0x00020001, 2) and H-NONE (0, 0). The state page is page 6 (the fork's layout).

Control o1-4 reads `ovf=0 kept=2 size=24576` and fails if any owner word shows with flag 0x4; an
empty copy there makes it cannot tell. A row whose copy right after the close is empty (0 bytes)
is cannot tell, never a pass or a failure.

## Stops

- hook_check (rc 24): the copy after the second render not made, or the copy right after the close
  empty in two rows in a row.
- A copy file missing (render_kept unreadable): the runner stops (23). Any fault, hang or failure:
  the kit's stop (4). A control without its reading: the premise stops (25).

## Mock worlds

`model`, `alt`, `early` (the hypotheses), `oneempty` (one empty copy: the stage goes on),
`twoempty` (two in a row: 24), `nokeep` (23), `fault` (4).

## Replay vectors

No table: closing_tables.py has no kind for kept TA data copies; the records go to
crates/SIM_UNMODELLED.toml (no simulator models a kept context's TA data), as r19-own's.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py); the driver keeps its logs under `out/`.

No firmware-derived file: nothing here goes to data-private.
