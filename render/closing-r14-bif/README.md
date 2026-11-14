# r14-bif

Round 14's session r14-bif (plan `closing14/plan/rank-round14.md` sections 2 and 3, row 11;
decisions R14-4 (a) and the round's routine (a)s in `closing14/DECISIONS-R14.md`; record E1046,
Q108's stale-data clause), built with the session kit (resgx545 HACKING.md, "Session kit"),
scaffolded by `tools/closing/new_session.py` from resgx545 c58f9f9c87aa, data 3309b5fd9bd7.
Laptop prefix `r14b`, module B60AB0B475DD1E8972419B5 (fork 2a650d74: debugfs vm_pte_addr and
vm_pte_flags). Tool t14 = `~/sgxfive-test-t14` (sha256 aa550b94..., on the laptop), built from
resgx545 c58f9f9 `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 9cef7a20...,
`TOOLSRC.sha256`; `tri --refill K:BUF=V`) by `lead/build_tool14.sh`, a byte copy of
`closing14/k14/build_tool14.sh`, which session.toml binds as
`data:render/closing-r14-bif/lead/build_tool14.sh` (the path it takes when the fold publishes this
session; its built line is `closing14/k14/TOOL14.built`). No kernel change, no boot, safe class
only: no `expectfault` row, `#limit 0`.

## What runs (1 stage, 6 jobs, about 1 minute of jobs, about 4 with staging and preflight)

| Row | Set | Knob | Form | Frozen (store of render 2) |
| --- | --- | --- | --- | --- |
| rf-c-plain | control | - | `tri -n 2 --depth --depth-store` (E965's tri-c-depth twice) | both renders exact, each store 4096 changed |
| rf-c-depth | control | - | refill form, no refill | both stores byte for byte E1029's zb-c-id (F) |
| rf-c-unread | control | CC 0x8 | render 1 control 0x0017100c (no load), render 2 0x0017500e (`--depth-ctl-next`), refill | store 1 byte for byte E1029's zb-c-off (clear), store 2 V |
| rf-cc-keep | heldout | CC 0x8 | no refill | H-CC-NOOP: F |
| rf-cc-refill | heldout | CC 0x8 | `--refill 2:depth=0x3f400000` | H-CC-COHERENT: V; H-CC-STALE: F |
| rf-nc-refill | heldout | - | `--refill 2:depth=0x3f400000` (then `after`: health) | H-NC-COHERENT: V; H-NC-STALE: F |

**The form** is E1029's zb-c-id (r13-zls zbase, passed): 64 x 32, the triangle over the target at
depth 0.5 with the depth test never (`--poke blk:1=0x00000200`, E467: the store holds what was
loaded), ZLS control 0x0017500e (load and store), the depth buffer `index` (dword k holds k) at
0x3e001000, a separate store filled 0x3e800000 at 0x3e015000, `--depth-pages 20`; here as `tri -n
2 --keep-going` on one context. Without `--depth-ctl-next`, t14 fills every buffer again before
render 2 (the same index and store fill, `cmd_tri`), then a refill row's `--refill 2:depth=V`
writes V = 0x3f400000 (0.75) to every dword of the depth buffer right before render 2's kick and
prints `refill: render 2 buf depth value 0x3f400000`. Render 2's store then says what render 2
loaded: **F** (dword k = k: what render 1 loaded), **V** (the host's refill) or a mix, counted
dword by dword (`gen/rf.store_class`). The knob rows put CACHECONSISTENT (PTE flag 0x8,
`dbg:vm_pte_addr=0x3e001000 dbg:vm_pte_flags=0x8`) on the depth buffer's mapping; the kernel logs
`vm_map 0x3e001000 +0x14000: PTE flags 0x8` (E965's line form, pinned).

**Hypotheses** (frozen, `predictions/refill.tsv`, written by the generator from gen/rf.py):
H-CC-COHERENT (flag set:
render 2 reads V) against H-CC-STALE (it reads render 1's F); H-NC-COHERENT against H-NC-STALE for
the flag clear; H-CC-NOOP (the flag without a refill changes nothing: F; E945's "changed nothing",
held out on a depth load). Every row's premise: all `job:` lines ok, the buffers at gen/rf's
addresses, store 1 F, and the kernel's PTE line on a knob row; else cannot tell.

**Controls that can fail:** rf-c-plain (the two-render job draws exactly, `tri: 2 renders ok`, each
store 4096 changed as E965's), rf-c-depth (both stores E1029's kept zb-c-id dump byte for byte: the
form replicates on render 1 and the second fill reaches render 2), rf-c-unread (the refill of a
buffer render 1 never read must reach render 2: store 2 V; store 1 E1029's zb-c-off byte for
byte). A failed control prints no headline (scorekit).

**Stops:** `#limit 0` and no `expectfault` row: any fault or hang stops the session (4) with the
kit's recovery and strict health; a control without its reading stops it (25); `hook_check` (24):
a `job:` line not ok, the buffers elsewhere than 0x3e001000 / 0x3e000000 / 0x3e015000, a knob row
without the kernel's PTE line (or a PTE line on a row without the knob), a refill row without its
`refill:` line. The stage is the only one: any stop ends the session.

## Predicted outcomes ([infer] where not frozen)

All 6 jobs complete (the four depth rows rc 1 with `job: ok` and a diff line: test never draws
nothing, `expectdiff`); the three controls pass; H-CC-NOOP, H-CC-COHERENT and H-NC-COHERENT hold
(render 2 reads V with and without the flag) [infer: the host maps a BO write-combined (fork
`sgxfive_drv.c`, "mapped write-combined on the CPU"), and no kept record shows a ZLS load reused
across renders]. If H-CC-COHERENT holds, Q108's stale-data clause narrows to "no stale read seen on
a depth load, either flag state"; if a STALE model holds on one flag state only, CACHECONSISTENT
decides what the load sees. Narrow either way: WRITEONLY and EDMPROTECT on a texture read, the TA's
writes and the EDM's buffers need faults.

## Replay vectors (HACKING.md "Replay vectors")

| Stage | Vectors table (closing_tables.py, `sgx545-tables`) | replay |
| --- | --- | --- |
| refill | `pte-refill` (row, PTE flags from the kernel line, refill value, class of each render's store) | sgx-pipe `tests/pte_table.rs` with `bif::pte_access` widened test first by a ZLS-load access (0x8: clean, the load reads the host's last write); refused if the fold does not model it |

The freeze pins what the replay reads: `crates/sgx-pipe/src/bif.rs`, `tests/pte_table.rs`,
`tools/usse-asm/closing_tables.py` and `closing_vectors.py` (session.toml `[freeze] pins`).

## Commands

- Python: `$HOME/src/resgx545/.venv/bin/python` (tests use it unless `PY` names another).
- Generator: `python3 gen/make.py` (`--check`).
- Offline: `bash tests/run_all.sh`; freeze `python3 kit/session.py freeze .`, then again
  `bash tests/run_all.sh`.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py refill KEPT_DIR`.
- Tool build (done by the lead; the binary is not in the session): `bash lead/build_tool14.sh`.

Mock worlds (`mock/world.py`): model (0), noread (premise 25 at rf-c-plain), rejected (a knob row
`job: rejected`: 4), nopte (no kernel PTE line: refill 24 at rf-c-unread), norefill (no `refill:`
line: refill 24 at rf-c-unread), fault (a refill row faults: 4). The library mock (t14 at c58f9f9)
replays all 6 rows, none refused.

## Deviations from the plan

- "The plain two-render job" is E965's knob-free `tri --depth --depth-store` run twice, so that it
  keeps the two store dumps every row's scorer input names (the kit's REQUIRED is per row).
- The flag-clear "without the refill" row is the control rf-c-depth (a replicate of E1029's
  zb-c-id); rf-c-unread runs with the flag set, so it controls the refill through a CC mapping.

Nothing here is firmware-derived; every file may go to resgx545-data.
