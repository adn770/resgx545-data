# r40-d0-survey

**NEEDS THE USER'S OK BEFORE RUNNING** (approved 2026-11-19 as N3e row D0, per the lead). The row
writes our PDS image into the slack of the firmware's PDS #14 page: ST's write, byte for byte
(below), and emits on a timer pass, as ST (r40-s-sbt, ST-DONE).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 555d8eb (branch r40-d0, off
r40-s c3f9f67, not on main; kit/ is that commit's blobs, byte-equal to r40-s-sbt's) and
resgx545-data 9fce0b9934f2, laptop prefix `r40d0`, HostKeyAlias `cedar`. Design:
`closing29/n3e/design.md` §3.1 (row D0, the landing survey; §1.2 why; §4 risk "as ST").
**Flagged** (user present, reset ready). Built offline, frozen, not staged, not run.

**Module.** The one the laptop runs: srcversion 0CDFCDB73D76F39FE9E593C (r39-kernel, fork
f9453424bf71). No rebuild, no boot. Its verifier accepts `emitsb14d` unchanged: the fork's KUnit
suite on the Mac shim with a scratch copy of the test blobs header (OK_BLOBS plus emitsb14 and
emitsb14d), 34 of 34: `closing29/r40-s-logs/d0-shim-emitsb14d.log`, tree `closing29/r40-d0-shim`.
Every `mov rN, saK` (K <= 31) and `mov rN, paK` (K <= 15) the blob needs is accepted.

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=fw14` (ST's). Image crumb3, 3 rows,
control 0x01800100, in the slack of the firmware's PDS #14 page. Emit word 0xfb20b10800c08184
(#14's sideband 0x843), `s2` = 0.

**The blob** `owntask/emitsb14d.blob` (resgx545 r40-d0 555d8eb, `gen_blobs.gen_emitsb14d`) is
`emitsb14` plus reads and stores, nothing else:

- **pre**: c1 (entry 0), after the M1/run-id stores and before the cmd store and the fence that
  precede the emit, branches to a block after entry 1's end that stores sa0-sa31 through r10 into
  page dwords 128-159, then does c1's `mov r4, #0` and branches back.
- **post**: entry 1, after S1 and the pa0-pa3/sa0-sa3 slots, before M4: sa0-sa31 into dwords
  160-191 and pa0-pa15 into 192-207 through r9.

## The firmware-page write: ST's, byte for byte

The kernel writes crumb3 at #14's buffer + 0x100 (19 dwords, [0x100, 0x14c)): U0, U1 0, U2 0,
0x000, V0, V2, 0x200, 0x005a3305, four zero dwords, crumb's 7 instruction words; zeroes [0x68,
0x1000) first; #14's own 0x68 bytes, PTE and flags untouched; the disarm reset rebuilds #14's
bytes and zeroes the slack. U0 = TRC 8, CBASE 15, index 0x4000 + entry 1: **emitsb14d's entry 1
is emitsb14's (index 30)**, so U0 is 0x080401ef as in ST (and R4, S-PASS). This is why the pre
block is out of line: its branch takes the place of c1's `mov r4, #0` (r40-d0 test
`test_emitsb14d_is_emitsb14_plus_the_survey_only` asserts the entries equal). V0/V2 are the
kernel's (TA3DCtl dwords 0 and 2), as every row. The design allowed U0 to move with entry 1; it
does not.

## Stage own: 1 job, flagged, on_stop "end"

c1-a: one tester command 1, run id 1, the fill 0xdeadc0de in slots 2-5 (dwords 72-87) and in
dwords 128-223 first, `"ticks": true`, timeout 200 ms, no kick (as ST). Then the page,
snap0/snap9, the record, the gate after an ok end, the disarm.

## Outcomes (predictions/own.tsv, frozen; score/score.py)

The start table is ST's (no tick band). DONE is the landing's precondition; it splits into the
design's four landing outcomes by one derived quantity `land` (score.py `land_of`), V0-V3 =
snap0's TA3DCtl dwords 0-3:

| outcome | T | S1 | M4, state | land | prediction |
|---|---|---|---|---|---|
| D0-NEVER | running | fill | fill, 0 | | (start) |
| D0-T1 / T2 / T3 / E1 | 0 / 0x200 / 0x005a3305 / 0x005a3305 | fill / fill / fill / S1 | fill, 0 | | (start) |
| D0-HID | 0x005a3305 | 0x5a5a3304 | M4 + run id, 2 | post sa4-31 = pre; no V0 or V2 in pa0-15 | **held** |
| D0-PA | as HID | | | V0 at pa k and V2 at pa k+2 | failed |
| D0-SHIFT | as HID | | | post sa j = V0, sa j+2 = V2, j >= 4, pre[j] and pre[j+2] differed | failed |
| D0-STIR | as HID | | | any other pre/post difference in sa4-31 | failed |

RULE: `Q128-D0 RULE: D0-<landing>` when every control passed and one landing outcome holds. A
start outcome short of DONE is CANNOT TELL for the landing (the start outcome named in the rule);
so is a DONE whose landing none of the four names (PA and SHIFT at once, or V0/V2 in pa without
the pair and sa4-31 unchanged). FAULT as ST.

Controls (every row, all can fail): PG, E0 (slot 1 = M1 + run id, cmd 0), T0, B (as ST), and the
design's **P0** (no 0xdeadc0de left in 128-159: every pre dword overwritten) and **P1** (pre
sa0-sa3 = V0-V3, the EDM's own secondaries, E002). Printed, never scored: the SURVEY lines (pre/post
differences in sa0-31 with indices, pre and post sa20-sa31 for row L's attribute choice, pre
sa0-19, post pa0-15), the arm line, Δtick, alive, the signature, ST's LANDING line.

## Stage post, stops

As ST: p1-tri and p2-fill on t30 after own's disarm; a runner stop ends the session after reset
and health (rc 4); a failed reset means the user's ordinary reboot.

## Deviations from the design (builder)

- Session name `r40-d0-survey` (the lead's), not `r40-n3e-d0`.
- The pre block is out of line (code order of c1 changed by one branch) so that U0, and the
  firmware-page write, equal ST's; the design allowed U0 to move instead.
- DONE is split into the four landing outcomes through a derived quantity `land`, so the kit's
  one-outcome-holds scoring applies; SHIFT's "where pre differed" is read as pre[j] != post[j]
  and pre[j+2] != post[j+2].
- O1 (folding SB/S2/SP/ST before freezing) is the lead's, not done here.

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`;
after: `python3 score/score.py own out/ATT/own`, `python3 score/score.py post out/ATT/post`.
