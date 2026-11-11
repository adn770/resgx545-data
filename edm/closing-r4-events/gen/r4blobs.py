# SPDX-License-Identifier: MIT
"""r4blobs.py (R4-events): the two new firmware tasks of the session, generated here and verified by the landed `tools/fwtask`
(resgx545 5a13042: the exit `phas`, `own_end`, the lint).  PREPARED, NOT RUN.  Our own source, written from doc/specs/usse_isa.md
and the records E146, E155, E532, E746, E747, E793, E813, E817, E823, E830; nothing here reads a closed binary.

  ring_exit2.s   R3k's ring_exit.s (S2's ring: slots 0 to 3 with 16, 8, 8, 8 rungs; the pass counter in dword 20) reduced to the one
                 end this session asks about and extended by a kick pass.  In slot 0, window 2 only, a pass of the host's KIND (1
                 plain tick: pa0 = 2 and no bit of pa1[23:0]; 2 kick: pa0 = 0 and pa1[23:0] = 0x100, as ring_end.s, E813) is ACTED
                 on while COUNT > 0: logged first (flag 3), COUNT - 1, ACTED + 1, ACT_SEEN = ACT, then ACT 4 ends the pass with
                 `own_end` (idf, wdf, phas #0, #0, pixel, end, parallel, nop.end): the exit's phase end and nothing else (no cfi.global,
                 no tail call to the closed task).  No other ACT exists in this blob.
  ring_skip3p.s  R3k's ring_skip3.s without its `str #77` command: the ring of S2, slot 0 only counts its passes, and slot 3 skips
                 the fill's end-of-render pass once (the host's SKIP3 flag: the first pass with pa0 = 0 and pa1[23:0] = 0x10, E747):
                 it is logged with flag 3, SKIPPED + 1, and ends with `own_end` (idf, wdf, phas end, nop.end) instead of the tail
                 call, so the closed slot 3 handler is not called.  No firmware `str` at all (R4-7).
Registers r1-r18 and r22-r31 only.  Every store is the same value from every lane.
"""
import hashlib
import json
import pathlib
import re
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r4layout as L  # noqa: E402
import r3blobs as B  # noqa: E402

TRIPLE = B.TRIPLE
IDF = "        idf drc0, bif"
WDF = "        wdf drc0"
OWN_END = ["        own_end                             ; idf, wdf are before it: phas #0, #0, pixel, end, parallel; nop.end"]
STR_RE = re.compile(r"(?:[!]?p\d\s+)?str\s+#(\d+)\s*,")


def _pass_counter():
    return [f"        ldad.bypassl1 r8, [r1,+#{L.A_PASS}], drc0", "        wdf drc0", "        mov r9, #0xffffffff",
            "        ima32.u r8, r8, #1, r9.neg", f"        stad [r1,+#{L.A_PASS}], r8                 ; passes of slot 0", IDF, WDF]


def ring_entry(k, mode):
    """One slot's entry.  mode 'exit2': slot 0 acts (KIND, ACT, COUNT).  'skip3p': slot 3 skips once, slot 0 counts passes."""
    acting = mode == "exit2" and k == 0
    flagged = acting or (mode == "skip3p" and k == 3)      # the rung's flag is the register r13
    base = L.RING_BASE[k] * 4
    a = [f"@entry {k}", "        mov r1, #0xdeadbeef                 ; @patch res+0",
         f"        mov r2, #0xdeadbeef                 ; @patch res+{base:#x}",
         "        mov r4, pa0", "        mov r5, pa1", "        mov r6, pa2",
         "        ldr r11, #81, drc0                  ; CR_TIMER at the pass's start", "        wdf drc0"]
    if flagged:
        a += ["        mov r13, #0x00000001                ; the flag of this pass's rung: 1 logged, 3 own end",
              "        mov r14, #0x00000000                ; the ACT in force on this pass (0: none)"]
    if k == 0:
        a += _pass_counter()
    if mode == "skip3p" and k == 3:
        a += [f"        ldad.bypassl1 r8, [r1,+#{L.SKIP3}], drc0", "        wdf drc0", "        and.testtanz.chan0 !c0, p1, r8, r8",
              "        !p1 br @noskip",
              "        and.testtanz.chan0 !c0, p1, r4, r4  ; p1 = pa0 is not 0: not the fill's end of render",
              "        p1 br @noskip",
              "        mov r9, #0x00ffffef",
              "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = a bit but 4 in pa1[23:0]",
              "        p1 br @noskip",
              f"        mov r9, #0x{L.SKIP3_WORD_BIT:08x}",
              "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = bit 4 set",
              "        !p1 br @noskip",
              f"        mov r13, #0x{L.SKIP_FLAG:08x}                ; the skipped pass: logged with flag 3",
              "        mov r14, #0x00000001",
              "        mov r9, #0x00000000", f"        stad [r1,+#{L.SKIP3}], r9                  ; the flag is taken: once",
              f"        ldad.bypassl1 r8, [r1,+#{L.SKIPPED}], drc0", "        wdf drc0", "        mov r9, #0xffffffff",
              "        ima32.u r8, r8, #1, r9.neg", f"        stad [r1,+#{L.SKIPPED}], r8",
              "noskip:"]
    a += [f"        ldad.bypassl1 r3, [r1,+#{L.WINDOW}], drc0   ; the window", "        wdf drc0",
          "        and.testtanz.chan0 !c0, p0, r3, r3  ; p0 = window open", f"        !p0 br @x{k}",
          "        xor.testtaz.chan0 !c0, p1, r3, #2   ; p1 = window 2: every pass",
          f"        p1 br @{'k0' if acting else f's{k}_0'}",
          "        mov r9, #0x00ffffff",
          "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = pa1[23:0] not 0 (31:24 is a count, S2 run 1)", f"        p1 br @s{k}_0",
          "        xor.testtanz.chan0 !c0, p1, r4, #2  ; p1 = pa0 is not 2", f"        p1 br @s{k}_0",
          f"        br @x{k}                             ; a plain tick in window 1: not logged"]
    if acting:
        a += ["k0:", f"        ldad.bypassl1 r8, [r1,+#{L.COUNT}], drc0     ; passes still to act on (window 2 only)",
              f"        ldad.bypassl1 r10, [r1,+#{L.KIND}], drc0     ; 1 plain tick pass, 2 kick pass", "        wdf drc0",
              "        and.testtanz.chan0 !c0, p0, r8, r8", "        !p0 br @s0_0",
              f"        xor.testtaz.chan0 !c0, p1, r10, #{L.KIND_KICK}  ; p1 = KIND 2: a kick pass is wanted", "        p1 br @kk",
              f"        xor.testtanz.chan0 !c0, p1, r10, #{L.KIND_TICK} ; p1 = KIND is not 1 either: nothing is wanted", "        p1 br @s0_0",
              "        xor.testtanz.chan0 !c0, p1, r4, #2  ; p1 = pa0 is not 2: not a tick pass", "        p1 br @s0_0",
              "        mov r9, #0x00ffffff", "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = a bit in pa1[23:0]: not a plain tick",
              "        p1 br @s0_0", "        br @kact",
              "kk:", "        and.testtanz.chan0 !c0, p1, r4, r4  ; p1 = pa0 is not 0: not a kick pass", "        p1 br @s0_0",
              "        mov r9, #0x00fffeff", "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = a bit but 8 in pa1[23:0]: not a kick pass",
              "        p1 br @s0_0",
              "        mov r9, #0x00000100", "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = bit 8 set: a kick pass", "        !p1 br @s0_0",
              "kact:", "        mov r9, #0x00000001", "        ima32.u r8, r8, #1, r9.neg          ; COUNT - 1", f"        stad [r1,+#{L.COUNT}], r8",
              f"        ldad.bypassl1 r8, [r1,+#{L.ACTED}], drc0", f"        ldad.bypassl1 r10, [r1,+#{L.ACT}], drc0", "        wdf drc0",
              "        mov r9, #0xffffffff", "        ima32.u r8, r8, #1, r9.neg          ; ACTED + 1", f"        stad [r1,+#{L.ACTED}], r8",
              f"        stad [r1,+#{L.ACT_SEEN}], r10                ; the ACT this pass acts with (the task's own record: the host wrote it)",
              "        mov r14, r10",
              f"        mov r13, #0x{L.SKIP_FLAG:08x}                ; own end: logged with flag 3",
              "        br @s0_0"]
    n = L.RUNGS[k]
    for j in range(n):
        o = L.RUNG * j
        nxt = f"s{k}_{j + 1}" if j + 1 < n else f"full{k}"
        a += [f"s{k}_{j}:", f"        ldad.bypassl1 r7, [r2,+#{o}], drc0", "        wdf drc0",
              "        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = rung taken", f"        p0 br @{nxt}"]
        if flagged:
            a += [f"        stad [r2,+#{o}], r13"]
        else:
            a += ["        mov r7, #0x00000001", f"        stad [r2,+#{o}], r7"]
        a += [f"        stad [r2,+#{o + 1}], r4", f"        stad [r2,+#{o + 2}], r5", f"        stad [r2,+#{o + 3}], r6",
              f"        stad [r2,+#{o + 4}], r11", IDF, WDF, f"        br @x{k}"]
    a += [f"full{k}:", f"        ldad.bypassl1 r8, [r1,+#{L.DROP + k}], drc0", "        wdf drc0", "        mov r9, #0xffffffff",
          "        ima32.u r8, r8, #1, r9.neg", f"        stad [r1,+#{L.DROP + k}], r8                 ; the ring is full: counted",
          IDF, WDF, f"        br @x{k}", f"x{k}:"]
    if acting:
        a += [f"        xor.testtaz.chan0 !c0, p1, r14, #{L.ACT_PHAS}  ; p1 = ACT 4: own end with the exit's phase end", "        p1 br @endp"]
    if mode == "skip3p" and k == 3:
        a += ["        xor.testtaz.chan0 !c0, p1, r14, #1  ; p1 = the skipped pass", "        p1 br @end3"]
    t = "\n".join(a) + "\n" + TRIPLE.format(k=k)
    if acting:
        t += "endp:\n" + "\n".join([IDF, WDF] + OWN_END) + "\n"
    if mode == "skip3p" and k == 3:
        t += "end3:\n" + "\n".join([IDF, WDF] + OWN_END) + "\n"
    return t


def ring_source(name):
    mode = {"ring_exit2": "exit2", "ring_skip3p": "skip3p"}[name]
    desc = {"ring_exit2": "KIND 1 tick pass or KIND 2 kick pass acted on, ACT 4 own end with the exit's phase end",
            "ring_skip3p": "slot 3 skip-once of the fill's end of render, ended with the exit's phase end"}[name]
    hdr = (f"; SPDX-License-Identifier: MIT\n; {name}.s -- generated by closing4/r4-events/gen/r4blobs.py (R4-events, PREPARED, NOT RUN)\n"
           f"; S2's event ring (slots 16, 8, 8, 8 rungs), the pass counter (dword 20).  {desc}.\n"
           "; Our own source (usse_isa.md, E146, E532, E746, E747, E793, E813, E817, E823, E830); only forms the landed verifier\n"
           "; accepts.  No sa write, no pa, i or pclink write but the tail triples, no str, no cfi.global.\n\n")
    return hdr + "".join(ring_entry(k, mode) for k in range(4))


SOURCES = {"ring_exit2": lambda: ring_source("ring_exit2"), "ring_skip3p": lambda: ring_source("ring_skip3p")}


def build(name):
    """(source text, blob bytes) of one generated task; the landed verifier runs inside build_blob_text."""
    text = SOURCES[name]()
    return text, B.fwtask.build_blob_text(text, B.fwtask.load_regs())
