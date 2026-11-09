#!/usr/bin/env python3
"""p1141/ta gen_ring.py: write events_ring.s (own firmware task, a ring log of events with CR_TIMER).

Same entry shape as asm/fwtask/events_m.s (read there, not edited): entries 0..3, each logs pa0,
pa1, pa2 and an `ldr` of CR_TIMER (register 81, on the allow list since 11.29) into its own region
of the results page.  No computed address (the verifier's base pass refuses one): a ladder of
NSLOT fixed slots, slot i taken iff its flag dword is still 0 (ldad, wdf, and.testtanz, p0 br);
when all are taken the event is dropped (the host sees 'all flags set').  No register is written
(no str), no sa write, no emit, no lock, tail call as events_m.s.
Per slot (8 dwords): +0 flag, +1 pa0, +2 pa1 (raw), +3 pa2, +4 CR_TIMER, +5..7 unused (0).
Region of entry e: res + 0x200 + 0x100*e (8 slots x 8 dwords x 4 B = 0x100).
Usage: gen_ring.py OUT.s      (then fwtask.py OUTDIR OUT.s verifies it, offline)
"""
import sys
NSLOT = 8
def entry(e):
    base = 0x200 + 0x100 * e
    o = [f"@entry {e}",
         f"        mov r1, #0xdeadbeef                 ; @patch res+{base}",
         "        mov r4, pa0", "        mov r5, pa1", "        mov r6, pa2",
         "        ldr r8, #81, drc0", "        wdf drc0"]
    for i in range(NSLOT):
        b = 8 * i
        o += [f"s{e}_{i}:",
              f"        ldad.bypassl1 r7, [r1,+#{b}], drc0",
              "        wdf drc0",
              "        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken",
              f"        p0 br @s{e}_{i + 1}",
              "        mov r7, #0x00000001",
              f"        stad [r1,+#{b}], r7",
              f"        stad [r1,+#{b + 1}], r4",
              f"        stad [r1,+#{b + 2}], r5",
              f"        stad [r1,+#{b + 3}], r6",
              f"        stad [r1,+#{b + 4}], r8",
              "        idf drc0, bif", "        wdf drc0",
              f"        br @s{e}_{NSLOT}"]
    o += [f"s{e}_{NSLOT}:",
          f"        mov r30, #0xdeadbeef                ; @patch cont{e}",
          "        mov pclink, r30", "        lapc"]
    return o
def main():
    head = ["; SPDX-License-Identifier: MIT", "; SPDX-FileCopyrightText: 2026 Josep Torra",
            "; events_ring.s -- p1141/ta draft: a ring log of events, each with CR_TIMER (not landed).",
            "; Rules as events_m.s: r0 to r31 only, no sa write, no emit, no lock, no str, same value every lane.", ""]
    body = []
    for e in range(4): body += entry(e)
    open(sys.argv[1], "w").write("\n".join(head + body) + "\n")
if __name__ == "__main__": main()
