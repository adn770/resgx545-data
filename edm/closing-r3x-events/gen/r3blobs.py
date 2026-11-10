# SPDX-License-Identifier: MIT
"""r3blobs.py (R3x-events, round 3 L3): the two new firmware tasks, alias2.s (stages c and d) and ring_end.s (stage e), the scans
the guard and the generator share (what a task writes, block by block), and the verifier call.  PREPARED, NOT RUN.

alias2.s   = alias.s (closing2/r3-events; commands 0, 1-7, 9 unchanged) plus cmd 10 (sa65 = the host's word, left in place), cmd 11
           (E537's combination: sa63, sa64, sa65, r20, r21, i0, i1 from the host, p0 = p1 = 1 at the tail call) and cmd 12 (sa64 =
           pa0 & ~2 on N consecutive passes, N in the page, the reader armed on the last).
ring_end.s = ring_skip.s generalised: in window 2 a pass of the host's KIND (1 plain tick, 2 kick: pa0 = 0, pa1[23:0] = 0x100) is
           ACTED on while COUNT > 0: logged first (flag 3 own end, 4 fast-path tail), COUNT - 1, ACTED + 1, then ACT 1 ends the pass
           with idf, wdf, nop.end (the closed task not called) or ACT 2 tail-calls the closed task of slot 2 (@patch cont2).

Original docstring of r3blobs.py (closing2):

r3blobs.py: the two new firmware tasks of R3-events (alias.s for Q152 stage A, ring_skip.s for stage B), the scans the
guard and the generator share (what a task writes, block by block), and the verifier call.

alias.s    one entry (own_arm slots=0x1 entry=0, as state3.s ran in E537).  A pass counts itself, then reads the host's
           command.  Command 0: tail call at once.  1, 2, 3, 4, 5, 7: a writer (sa63, sa65, sa65 and back, sa64 = pa0 & ~2,
           sa64 = pa0, sa63 = the host's value), the record, p0..p3 = 0, 0, 1, 1, then the reader is armed (cmd = 9) and the
           closed task is called.  6: r20, r21, i0, i1 and nothing else, p0 = p1 = 1 from the dispatch, the reader armed, the
           closed task called.  9: the reader (the entry values of pclink, p0..p3, r20, r21, i0, i1, then sa64, sa65, sa63,
           pa0..pa2 and the pass count), cmd = 0.
ring_skip.s  S2's ring (slots 0-3: 16, 8, 8, 8 rungs) plus, in slot 0 only: the pass counter in dword 20, and in window 2 a
           plain tick (pa0 = 2, no bit of pa1[23:0]) is skipped while the host's SKIP word is not 0: the pass is logged
           (flag 3), SKIP is decremented, SKIPPED incremented, and the pass ends with idf, wdf and `nop.end`: the closed task
           is NOT called.  Window 0 and 1 never skip.  The other slots tail-call as in S2's ring_e1.
Registers r1-r18 and r22-r31.  No str, no emit, no lock, no clock register.  Every store is the same value from every lane.
"""
import os
import pathlib
import re
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3layout as L  # noqa: E402

R = pathlib.Path(os.environ.get("RESGX545", str(pathlib.Path.home() / "src/resgx545")))
os.environ.setdefault("FWTASK_USSE_ASM", str(R / "tools/usse-asm/usse-asm"))
sys.path.insert(0, str(R / "tools/fwtask"))
import fwtask  # noqa: E402  (landed, read-only)

TRIPLE = """t{k}:
        mov r30, #0xdeadbeef                ; @patch cont{k}
        mov pclink, r30
        lapc
"""
ARM_ALIAS = L.ARM_OF["c"]
ARM_RING = L.ARM_OF["e"]


# ---- alias.s -------------------------------------------------------------------------------------------------------
def _wr_record(extra):
    """The writer's record: pa words, the three sa values at entry, what it wrote, the read-backs."""
    out = ["        stad [r1,+#%d], r4" % (L.WR + 0), "        stad [r1,+#%d], r5" % (L.WR + 1),
           "        stad [r1,+#%d], r6" % (L.WR + 2), "        stad [r1,+#%d], r12            ; sa63 at entry" % (L.WR + 3),
           "        stad [r1,+#%d], r13            ; sa64 at entry" % (L.WR + 4),
           "        stad [r1,+#%d], r14            ; sa65 at entry" % (L.WR + 5)]
    for i, reg in enumerate(extra):
        out.append("        stad [r1,+#%d], %s" % (L.WR + 6 + i, reg))
    return out


SETP = ["        mov r18, #0x00000000", "        mov r19, #0x00000001",
        "        and.testtanz.chan0 !c0, p0, r18, r18", "        and.testtanz.chan0 !c0, p1, r18, r18",
        "        and.testtanz.chan0 !c0, p2, r19, r19", "        and.testtanz.chan0 !c0, p3, r19, r19"]


def alias2_commands(cap):
    """The three commands alias2.s adds (round 3).  Each is self-contained and ends with an unconditional branch."""
    a = []
    # c10: sa65 = the host's word (dword W65), LEFT in place (no restore); the record; the arm; the closed task is called
    a += ["c10:", f"        ldad.bypassl1 r10, [r1,+#{L.W65}], drc0", "        wdf drc0"] + cap + [
        "        mov sa65, r10", "        mov r11, sa65"] + _wr_record(["r10", "r11"]) + ["        br @setp"]
    # c11: E537's combination: sa63, sa64, sa65 (A_M, W64, W65), r20, r21, i0, i1 (A_RI); p0 = p1 = 1 as the dispatch left them
    a += ["c11:", f"        ldad.bypassl1 r10, [r1,+#{L.W65}], drc0", f"        ldad.bypassl1 r9, [r1,+#{L.W64}], drc0",
          f"        ldad.bypassl1 r19, [r1,+#{L.A_M}], drc0"]
    a += [f"        ldad.bypassl1 r{15 + i}, [r1,+#{L.A_RI + i}], drc0" for i in range(4)]
    a += ["        wdf drc0"] + cap + [
        "        mov sa63, r19", "        mov sa64, r9", "        mov sa65, r10", "        mov r3, sa63", "        mov r2, sa64",
        "        mov r11, sa65", "        mov r20, r15", "        mov r21, r16", "        mov i0, r17", "        mov i1, r18"]
    a += _wr_record(["r10", "r11"]) + [f"        stad [r1,+#{L.WR_X}], r19", f"        stad [r1,+#{L.WR_X + 1}], r3",
                                       f"        stad [r1,+#{L.WR_X + 2}], r9", f"        stad [r1,+#{L.WR_X + 3}], r2",
                                       "        br @arm"]
    # c12: sa64 = pa0 & ~2 on NPASS consecutive passes; the record every pass; setp every pass; the reader armed on the last
    a += ["c12:", f"        ldad.bypassl1 r3, [r1,+#{L.NPASS}], drc0", "        wdf drc0",
          "        and.testtanz.chan0 !c0, p0, r3, r3", "        !p0 br @tail"] + cap + [
        "        mov r8, r4", "        and.testtanz.chan0 !c0, p0, r4, #2   ; p0 = bit 1 of pa0 set", "        !p0 br @c12w",
        "        mov r9, #0x00000002", "        ima32.u r8, r8, #1, r9.neg",
        "c12w:", "        mov r10, r8", "        mov sa64, r10", "        mov r11, sa64", "        mov r8, r3", "        mov r9, #0x00000001",
        "        ima32.u r8, r8, #1, r9.neg            ; NPASS - 1", f"        stad [r1,+#{L.NPASS}], r8"] + _wr_record(
        ["r10", "r11"]) + ["        and.testtanz.chan0 !c0, p0, r8, r8    ; p0 = passes still to go", "        p0 br @c12more",
                           "        br @setp", "c12more:"] + SETP + ["        br @tail"]
    return a


def alias_source(ext=False):
    a = ["; SPDX-License-Identifier: MIT",
         "; alias.s -- generated by closing2/r3-events/gen/r3blobs.py (R3-events, Q152 stage A, PREPARED, NOT RUN)",
         "; Our own source, written from doc/specs/usse_isa.md and the records E146, E155, E532, E536, E537; run as an EDM task from",
         "; the page the kernel maps (index 0x4000); only forms the landed verifier accepts.  One entry (slots=0x1 entry=0).  No str,",
         "; no emit, no lock, no clock register.  sa writes: sa63, sa64, sa65 only, one command each (R2-1 b; the guard checks).",
         "",
         "@entry 0",
         "        mov r22, pclink                     ; the entry state first, before anything touches a predicate"]
    a += [f"        mov r{23 + i}, #0x00000000" for i in range(4)]
    a += [f"        p{i} mov r{23 + i}, #0x00000001" for i in range(4)]
    a += ["        mov r27, r20", "        mov r28, r21", "        mov r29, i0", "        mov r31, i1",
          "        mov r1, #0xdeadbeef                 ; @patch res+0",
          "        mov r4, pa0", "        mov r5, pa1", "        mov r6, pa2",
          f"        ldad.bypassl1 r8, [r1,+#{L.A_PASS}], drc0",
          "        wdf drc0",
          "        mov r9, #0xffffffff",
          "        ima32.u r8, r8, #1, r9.neg",
          f"        stad [r1,+#{L.A_PASS}], r8                 ; passes of the task",
          "        idf drc0, bif",
          "        wdf drc0",
          f"        ldad.bypassl1 r2, [r1,+#{L.CMD}], drc0",
          "        wdf drc0",
          "        and.testtanz.chan0 !c0, p0, r2, r2",
          "        p0 br @work",
          "tail:",
          "        mov r30, #0xdeadbeef                ; @patch cont0",
          "        mov pclink, r30",
          "        lapc",
          "work:"]
    for n in (1, 2, 3, 4, 5, 6, 7, 9) + ((10, 11, 12) if ext else ()):
        a += [f"        xor.testtaz.chan0 !c0, p1, r2, #{n}", f"        p1 br @c{n}"]
    a += ["        br @tail"]
    cap = ["        mov r12, sa63", "        mov r13, sa64", "        mov r14, sa65"]
    # c1: A1, sa63 = the host's marker
    a += ["c1:", f"        ldad.bypassl1 r10, [r1,+#{L.A_M}], drc0", "        wdf drc0"] + cap + [
        "        mov sa63, r10", "        mov r11, sa63"] + _wr_record(["r10", "r11"]) + ["        br @setp"]
    # c2: A2, sa65 = its own entry value
    a += ["c2:"] + cap + ["        mov r10, r14", "        mov sa65, r10", "        mov r11, sa65"] + _wr_record(
        ["r10", "r11"]) + ["        br @setp"]
    # c3: A3, sa65 = marker, read back, restored to the entry value before the tail call
    a += ["c3:", f"        ldad.bypassl1 r10, [r1,+#{L.A_M}], drc0", "        wdf drc0"] + cap + [
        "        mov sa65, r10", "        mov r11, sa65", "        mov sa65, r14", "        mov r17, sa65"] + _wr_record(
        ["r10", "r11", "r17"]) + ["        br @setp"]
    # c4: A4, sa64 = pa0 & ~2
    a += ["c4:"] + cap + ["        mov r8, r4", "        and.testtanz.chan0 !c0, p0, r4, #2   ; p0 = bit 1 of pa0 set",
                          "        !p0 br @c4w", "        mov r9, #0x00000002", "        ima32.u r8, r8, #1, r9.neg",
                          "c4w:", "        mov r10, r8", "        mov sa64, r10", "        mov r11, sa64"] + _wr_record(
        ["r10", "r11"]) + ["        br @setp"]
    # c5: A5, sa64 = pa0
    a += ["c5:"] + cap + ["        mov r10, r4", "        mov sa64, r10", "        mov r11, sa64"] + _wr_record(
        ["r10", "r11"]) + ["        br @setp"]
    # c6: A6, r20, r21, i0, i1; no sa write; p0 = p1 = 1 as the dispatch left them, p2 and p3 as at entry
    a += ["c6:"] + [f"        ldad.bypassl1 r{15 + i}, [r1,+#{L.A_RI + i}], drc0" for i in range(4)] + [
        "        wdf drc0", "        mov r20, r15", "        mov r21, r16", "        mov i0, r17", "        mov i1, r18",
        "        stad [r1,+#%d], r4" % (L.WR + 0), "        stad [r1,+#%d], r5" % (L.WR + 1),
        "        stad [r1,+#%d], r6" % (L.WR + 2), "        br @arm"]
    # c7: restore sa63 to the host's value (A1 only)
    a += ["c7:", f"        ldad.bypassl1 r10, [r1,+#{L.A_M}], drc0", "        wdf drc0"] + cap + [
        "        mov sa63, r10", "        mov r11, sa63"] + _wr_record(["r10", "r11"]) + ["        br @setp"]
    if ext:
        a += alias2_commands(cap)
    # setp: p0..p3 = 0, 0, 1, 1 (E536's writer), then arm
    a += ["setp:", "        mov r18, #0x00000000", "        mov r19, #0x00000001",
          "        and.testtanz.chan0 !c0, p0, r18, r18", "        and.testtanz.chan0 !c0, p1, r18, r18",
          "        and.testtanz.chan0 !c0, p2, r19, r19", "        and.testtanz.chan0 !c0, p3, r19, r19"]
    a += ["arm:", "        mov r3, #0x00000002", "        mov r7, #0x00000009",
          f"        ldad.bypassl1 r9, [r1,+#{L.RUNID}], drc0   ; the run id, echoed",
          "        wdf drc0",
          f"        stad [r1,+#{L.ECHO}], r9",
          f"        stad [r1,+#{L.WR_DONE}], r9                 ; the writer ran: a flag that stays",
          f"        stad [r1,+#{L.CMD}], r7                  ; cmd = 9: the next event reads",
          "        idf drc0, bif",
          "        wdf drc0",
          f"        stad [r1,+#{L.STATE}], r3                  ; state = done",
          "        br @tail"]
    # c9: the reader
    a += ["c9:", "        mov r12, sa64", "        mov r13, sa65", "        mov r14, sa63"]
    for i, reg in enumerate(["r22", "r23", "r24", "r25", "r26", "r27", "r28", "r29", "r31", "r12", "r13", "r14", "r4", "r5",
                             "r6", "r8"]):
        a.append(f"        stad [r1,+#{L.RD + i}], {reg}")
    a += ["done:", "        mov r7, #0x00000000", "        mov r3, #0x00000002",
          f"        ldad.bypassl1 r9, [r1,+#{L.RUNID}], drc0   ; the run id, echoed",
          "        wdf drc0",
          f"        stad [r1,+#{L.ECHO}], r9",
          f"        stad [r1,+#{L.CMD}], r7                  ; cmd = 0",
          "        idf drc0, bif",
          "        wdf drc0",
          f"        stad [r1,+#{L.STATE}], r3                  ; state = done",
          "        br @tail"]
    return "\n".join(a) + "\n"


# ---- ring_end.s ----------------------------------------------------------------------------------------------------
def ring_entry(k, end=False):
    base = L.RING_BASE[k] * 4
    a = [f"@entry {k}",
         "        mov r1, #0xdeadbeef                 ; @patch res+0",
         f"        mov r2, #0xdeadbeef                 ; @patch res+{base:#x}",
         "        mov r4, pa0", "        mov r5, pa1", "        mov r6, pa2",
         "        ldr r11, #81, drc0                  ; CR_TIMER at the pass's start",
         "        wdf drc0"]
    if end:
        a += ["        mov r13, #0x00000001                ; the flag of this pass's rung: 1 logged, 3 own end, 4 fast-path tail",
              f"        ldad.bypassl1 r8, [r1,+#{L.A_PASS}], drc0",
              "        wdf drc0",
              "        mov r9, #0xffffffff",
              "        ima32.u r8, r8, #1, r9.neg",
              f"        stad [r1,+#{L.A_PASS}], r8                 ; passes of slot 0",
              "        idf drc0, bif",
              "        wdf drc0"]
    a += [f"        ldad.bypassl1 r3, [r1,+#{L.WINDOW}], drc0   ; the window",
          "        wdf drc0",
          "        and.testtanz.chan0 !c0, p0, r3, r3  ; p0 = window open",
          f"        !p0 br @x{k}",
          "        xor.testtaz.chan0 !c0, p1, r3, #2   ; p1 = window 2: every pass",
          f"        p1 br @{'k0' if end else f's{k}_0'}",
          "        mov r9, #0x00ffffff",
          "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = pa1[23:0] not 0 (31:24 is a count, S2 run 1)",
          f"        p1 br @s{k}_0",
          "        xor.testtanz.chan0 !c0, p1, r4, #2  ; p1 = pa0 is not 2",
          f"        p1 br @s{k}_0",
          f"        br @x{k}                             ; a plain tick in window 1: not logged"]
    if end:
        a += ["k0:",
              f"        ldad.bypassl1 r8, [r1,+#{L.COUNT}], drc0     ; passes still to act on (window 2 only)",
              f"        ldad.bypassl1 r10, [r1,+#{L.KIND}], drc0     ; 1 plain tick, 2 kick pass",
              "        wdf drc0",
              "        and.testtanz.chan0 !c0, p0, r8, r8",
              "        !p0 br @s0_0",
              "        xor.testtaz.chan0 !c0, p1, r10, #2  ; p1 = KIND 2: a kick pass is wanted",
              "        p1 br @kk",
              "        xor.testtanz.chan0 !c0, p1, r10, #1 ; p1 = KIND is not 1 either: nothing is wanted",
              "        p1 br @s0_0",
              "        xor.testtanz.chan0 !c0, p1, r4, #2  ; p1 = pa0 is not 2: not a tick pass",
              "        p1 br @s0_0",
              "        mov r9, #0x00ffffff",
              "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = a bit in pa1[23:0]: not a plain tick",
              "        p1 br @s0_0",
              "        br @kact",
              "kk:",
              "        and.testtanz.chan0 !c0, p1, r4, r4  ; p1 = pa0 is not 0: not a kick pass",
              "        p1 br @s0_0",
              "        mov r9, #0x00fffeff",
              "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = a bit but 8 in pa1[23:0]: not a kick pass",
              "        p1 br @s0_0",
              "        mov r9, #0x00000100",
              "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = bit 8 set: a kick pass",
              "        !p1 br @s0_0",
              "kact:",
              "        mov r9, #0x00000001",
              "        ima32.u r8, r8, #1, r9.neg          ; COUNT - 1",
              f"        stad [r1,+#{L.COUNT}], r8",
              f"        ldad.bypassl1 r8, [r1,+#{L.ACTED}], drc0",
              f"        ldad.bypassl1 r10, [r1,+#{L.ACT}], drc0",
              "        wdf drc0",
              "        mov r9, #0xffffffff",
              "        ima32.u r8, r8, #1, r9.neg          ; ACTED + 1",
              f"        stad [r1,+#{L.ACTED}], r8",
              "        xor.testtaz.chan0 !c0, p1, r10, #2  ; p1 = ACT 2: the tail call to slot 2's closed task",
              f"        mov r13, #0x{L.SKIP_FLAG:08x}                ; own end: logged with flag 3",
              f"        p1 mov r13, #0x{L.TAIL_FLAG:08x}                ; fast-path tail: logged with flag 4",
              "        br @s0_0"]
    n = L.RUNGS[k]
    for j in range(n):
        o = L.RUNG * j
        nxt = f"s{k}_{j + 1}" if j + 1 < n else f"full{k}"
        a += [f"s{k}_{j}:",
              f"        ldad.bypassl1 r7, [r2,+#{o}], drc0",
              "        wdf drc0",
              "        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = rung taken",
              f"        p0 br @{nxt}"]
        if end:
            a += [f"        stad [r2,+#{o}], r13"]
        else:
            a += ["        mov r7, #0x00000001", f"        stad [r2,+#{o}], r7"]
        a += [f"        stad [r2,+#{o + 1}], r4",
              f"        stad [r2,+#{o + 2}], r5",
              f"        stad [r2,+#{o + 3}], r6",
              f"        stad [r2,+#{o + 4}], r11",
              "        idf drc0, bif",
              "        wdf drc0",
              f"        br @x{k}"]
    a += [f"full{k}:",
          f"        ldad.bypassl1 r8, [r1,+#{L.DROP + k}], drc0",
          "        wdf drc0",
          "        mov r9, #0xffffffff",
          "        ima32.u r8, r8, #1, r9.neg",
          f"        stad [r1,+#{L.DROP + k}], r8                 ; the ring is full: counted, not lost silently",
          "        idf drc0, bif",
          "        wdf drc0",
          f"        br @x{k}",
          f"x{k}:"]
    if end:
        a += ["        xor.testtaz.chan0 !c0, p1, r13, #3  ; p1 = this pass is acted on, ACT 1: own end",
              "        p1 br @end0",
              "        xor.testtaz.chan0 !c0, p1, r13, #4  ; p1 = this pass is acted on, ACT 2: tail call to slot 2",
              "        p1 br @act0"]
    t = "\n".join(a) + "\n" + TRIPLE.format(k=k)
    if end:
        t += "end0:\n        idf drc0, bif\n        wdf drc0\n        nop.end                             ; own end: the closed task is not called\n"
        t += ("act0:\n        mov r30, #0xdeadbeef                ; @patch cont%d\n        mov pclink, r30\n        lapc\n" % L.ACT_SLOT)
    return t


def end_source():
    hdr = ("; SPDX-License-Identifier: MIT\n"
           "; ring_end.s -- generated by closing3/r3x-events/gen/r3blobs.py (R3x-events, round 3 stage e, PREPARED, NOT RUN)\n"
           "; S2's event ring (slots 16, 8, 8, 8 rungs), the pass counter (dword 20) and, in slot 0, window 2 only: a pass of the\n"
           "; host's KIND (1 plain tick, 2 kick: pa0 = 0, pa1[23:0] = 0x100) is acted on while COUNT > 0.  It is logged first (flag 3\n"
           "; own end, 4 tail call to slot 2), COUNT - 1, ACTED + 1, then ACT 1 ends the pass with idf, wdf and `nop.end` (the closed\n"
           "; task not called) and ACT 2 tail-calls the closed task of slot 2 (@patch cont2, R-2: the shortest path to the exit with no\n"
           "; group bit).  Our own source (usse_isa.md, E146, E155, E532, E538, E539, E793); only forms the landed verifier accepts.  No\n"
           "; str, no sa write, no pa, i or pclink write but the two tail triples.  Every store the same value from every lane.\n\n")
    return hdr + "".join(ring_entry(k, end=(k == 0)) for k in range(4))


# ---- scans (shared by the generator, the guard and the tests) ------------------------------------------------------
LABEL = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*):\s*$")


def code_lines(text):
    """[(line number, label or None, instruction text)] of a source: comments and blanks dropped, `@entry` lines kept as
    pseudo-lines ('@entry N')."""
    out = []
    for n, ln in enumerate(text.splitlines(), 1):
        s = ln.split(";")[0].strip()
        if not s:
            continue
        m = LABEL.match(s)
        out.append((n, m.group(1) if m else None, s))
    return out


def instructions(text):
    """The instruction lines in word order (labels and @entry dropped): one line, one 64-bit word."""
    return [s for _, lab, s in code_lines(text) if lab is None and not s.startswith("@")]


def blocks(text):
    """{label: [instruction lines]} up to the next label (a label's block ends where another label starts)."""
    out, cur = {}, None
    for _, lab, s in code_lines(text):
        if lab:
            cur = lab
            out.setdefault(cur, [])
        elif not s.startswith("@") and cur is not None:
            out[cur].append(s)
    return out


DEST = re.compile(r"^(?:[!]?p\d\s+)?mov(?:\.\w+)*\s+(sa\d+|pa\d+|i\d+|pclink|r2[01]|o\d+)\s*,")


def writes_of(lines):
    """The special registers a list of instruction lines writes (sa, pa, i, pclink, r20, r21): `mov DEST, ...`."""
    return sorted({m.group(1) for s in lines for m in [DEST.match(s)] if m})


def sa_writes_by_command(text):
    """{command: [sa names]} for alias.s: the blocks c1..c9 (each is self-contained: it ends with an unconditional br)."""
    out = {}
    for k, v in blocks(text).items():
        m = re.fullmatch(r"c(\d+)([a-z]\w*)?", k)       # c4w continues c4, c12more continues c12
        if m:
            out.setdefault(int(m.group(1)), set()).update(w for w in writes_of(v) if w.startswith("sa"))
    return {n: sorted(s) for n, s in out.items()}


def all_writes(text):
    return writes_of(instructions(text))


def build(name):
    """(source text, blob bytes, info) of one of the two new tasks; raises VerifyError if the landed verifier refuses."""
    text = alias_source(ext=True) if name == "alias2" else end_source()
    regs = fwtask.load_regs()
    blob = fwtask.build_blob_text(text, regs)
    return text, blob


def info_of(name, text, blob, arm):
    import hashlib
    p = fwtask.parse_blob(blob)
    lines = instructions(text)
    d = {"insns": len(p.words), "bytes": len(blob), "patches": len(p.patches), "entries": p.entries,
         "sha256": hashlib.sha256(blob).hexdigest(), "arm": arm,
         "sa_writes": sorted({w for w in all_writes(text) if w.startswith("sa")}),
         "str": sum(1 for s in lines if re.match(r"(?:[!]?p\d\s+)?str\b", s)),
         "ldr": sorted({re.sub(r"[^#0-9]", "", s.split(",")[1]) for s in lines if re.match(r"ldr\b", s)})}
    if name == "alias2":
        d["cmd_sa"] = {str(k): v for k, v in sa_writes_by_command(text).items()}
    return d
