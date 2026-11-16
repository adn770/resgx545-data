# Design note: the kit row word `pre:miscinfo` (not built)

Written by r31-cc's fold (E1122, E1123). It lives in `fold/` because the frozen session's verify
refuses a new file at the session's top. A tooling agent builds it in the kit, with tests;
sessions do not hand-roll it.

## Why

r31-cc refuted H-CC-HW in the 2 rows that could order it (the kick pass's BIF write, CR_BIF_CTRL
0x8, comes before CR_CACHE_CTRL's change). In 22 rows the BIF write was shorter than a sample.
The direct test is a served kick whose command carries no INVAL_DATA (cache-control bit 3), right
after a reset:

- H-CC-FW (the change is the firmware's `| 0x10000000` at bit 3, E013): 0x0804 stays 0x0000ffff
  after that kick.
- H-CC-HW (any served kick sets bit 28): 0x0804 reads 0x1000ffff after it.

Our kernel already sends such a kick. The debugfs `miscinfo` read (fork 8bc0877e8603,
`sgxfive_miscinfo`) sends one GETMISCINFO command with the pending cache control. After a reset
the boot leaves that at the firmware file's meta word 30, INVAL_BIF_PD 0x2 (`sgxfive_boot`;
doc/specs/boot_sequence.md), so bit 3 is clear, and the command then sets it to 0. The kernel's
arm path sends GETMISCINFO as well (E768), so the command is ordinary. Reading the file also
checks the answer against the registers and the firmware file, and a failure prints `bad`
lines.

## The word

`pre:miscinfo` is a row knob word in `kit/run_stage.sh`. It is allowed in any stage, safe
class, and at most once a row; with `noreset` it is refused (rc 7).

1. Order in the row: reset, knobs, kregs, idle, then **`pre:miscinfo`**, then `snap0`, the job,
   and `snap9`. The read happens after the reset and before `snap0`. No timeline is needed:
   `snap0` itself then reads 0x0804 after a served kick without bit 3.
2. Action: `sudo -n timeout -k 5 10 cat "$D/miscinfo" > "$JW/miscinfo.out"`, with `$D` the
   kit's debugfs directory. Keep it as `NAME.miscinfo` with the row's other files.
3. Checks:
   - the read's rc is 0 (else stop, rc 19, as for a knob that does not read back);
   - the output has the kernel's success line and no `bad` line (the exact pattern is taken
     from `sgxfive_miscinfo`'s `drm_printf` lines at the fork pin; else stop, rc 19);
   - the dmesg slice has no fault (the existing FATAL and fault rules apply unchanged).
4. Preflight: add `miscinfo` to the files that must exist (`DEBUGFS_NEED`) when any row uses
   the word.
5. Mock: the fake `sudo` answers `cat .../miscinfo` with a fixed success text. A world
   `miscinfo-bad` answers with a `bad` line, and a test checks that the stage stops with rc 19.
6. sessioncheck and kitscore: the kept `.miscinfo` file is required for a row with the word.
   `kitscore` exposes it so the scorer can read whether the kick was served (the success line).

The kit's rule "no debugfs write but reset and knobs" still holds, because this is a read. It
is the first kit read that sends a firmware command, so HACKING's "Session kit" section must say
so.

## The session that would use it (r3x-cc2, about 10 rows, safe)

| row | knobs | job | frozen reading |
|---|---|---|---|
| m-c1 | `reads:diff,cache,mi` | `tri --width 64 --height 64` | without the word: snap0 0x0804 0x0000ffff (control) |
| m-01..m-08 | `pre:miscinfo` | the same triangle | snap0 0x0804: H-CC-FW 0x0000ffff, H-CC-HW 0x1000ffff; snap9 0x1000ffff (H-CC-ONE) |
| m-c2 | `pre:miscinfo reads:diff,cache,mi` | the same | mi = the success line (the kick was served) |

The triangle after the read is the positive control: it must still change the word to
0x1000ffff (E1120, E1122). A row whose `miscinfo` shows no success line cannot tell. One
optional row wraps the triangle in regtimeline (`0x0804,0x0b14`) to time the triangle's change
as r31-cc's c2 did.

## Cost and risks

- Kit change: `run_stage.sh` (the word, the order, the checks), `session.py` (allow the word,
  preflight), the fake, `sessioncheck.py` and `kitscore.py`, with tests. No module or kernel
  change, no laptop build.
- Risk: GETMISCINFO on a just-reset EDM. The boot path and the kernel's arm already do it right
  after a boot (E768). If the command hangs, the kit's watchdog and the hang rules apply, so that
  row is a stop, not a reading.
