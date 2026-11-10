# SPDX-License-Identifier: MIT
"""r3kblobs.py (R3k, round 3 kernel batch, sessions K0 and K1): the firmware tasks the new module lets us run, generated here and
verified by the landed `tools/fwtask` (main 7aaa017: the rows for cfi/phas exit words, `cont4`, `mov` to pa2-pa4, `str` of #69, #77,
#691).  PREPARED, NOT RUN.  Our own source, written from doc/specs/usse_isa.md and the records E146, E155, E532, E536, E537, E746,
E747, E748, E793 and the readings R-1 to R-4 (closing3/events/readings); nothing here reads a closed binary.

  ring_exit.s    S2's ring (slots 0-3: 16, 8, 8, 8 rungs; the pass counter in dword 20) and, in slot 0, window 2 only: a plain tick
                 pass (KIND 1) is ACTED on while COUNT > 0, logged first (flag 3 own end, 4 tail) and the host's ACT is stored in
                 ACT_SEEN.  ACT 3 own end + cfi.global, 4 own end + phas, 5 own end + both (cfi, idf, wdf, phas, nop.end: the exact
                 exit of the closed tasks, R-1), 6 tail call to the exit itself (`@patch cont4`: cont4, tied to the firmware digest).
  ring_timer.s   the same ring; ACT 7 `str #691, r12` (r12 = 0x01061a80, the word the closed tick handler stores) then the closed task
                 (the normal tail call), ACT 8 the same str then our own end (idf, wdf, nop.end).
  pa_write2.s    E2a's pa_write.s (closing/s2: cmd 1 read, 2 `mov sa67`, 3 `mov sa68`, 9 the next pass's read) plus cmd 4 `mov pa3`,
                 5 `mov pa4`, 6 `mov pa2` (never pa0, pa1), each read back through the pa and its alias in the same pass.
  strclr.s       slot 0 command CMD 1: `str #69, rV` (CR_EVENT_HOST_CLEAR2, V from the page) then the tail call; the other entries are
                 plain tail calls.  The only `str` of the blob.
  ring_skip3.s   the ring of S2's ring_e1, plus in slot 3 a skip-once (the host's SKIP3 flag: the first pass with pa0 = 0 and pa1[23:0]
                 = 0x10 exactly, the fill's end of render, E747, is logged with flag 3, SKIPPED + 1, and ends with idf, wdf, nop.end
                 instead of the tail call) and in slot 0 the command CMD 2: `str #77, rV` (CR_EVENT_HOST_CLEAR, V from the page).
Registers r1-r18 and r22-r31 only.  Every store is the same value from every lane.
"""
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3layout as L  # noqa: E402
import r3blobs as B  # noqa: E402

TRIPLE = B.TRIPLE
CFI = "        cfi.global #3, #0, #3                 ; the exit's first word (R-1)"
IDF = "        idf drc0, bif"
WDF = "        wdf drc0"
PHAS = "        phas #0, #0, pixel, end, parallel   ; the exit's fourth word (R-1)"
END = "        nop.end"
OWN_ENDS = {  # label: instructions (every one ends the task)
    "endc": [CFI, IDF, WDF, END],            # own end + cfi only (cfi first, as the exit orders them)
    "endp": [IDF, WDF, PHAS, END],           # own end + phas ... end only
    "endb": [CFI, IDF, WDF, PHAS, END],      # own end + both: the exact exit replica
}


def _pass_counter(k):
    return [f"        ldad.bypassl1 r8, [r1,+#{L.A_PASS}], drc0", "        wdf drc0", "        mov r9, #0xffffffff",
            "        ima32.u r8, r8, #1, r9.neg", f"        stad [r1,+#{L.A_PASS}], r8                 ; passes of slot 0", IDF, WDF]


def ring_entry(k, mode):
    """One slot's entry of a ring task.  mode: None (plain slot), 'exit' / 'timer' (slot 0 of ring_exit / ring_timer: KIND, ACT, COUNT),
    'skip3' (ring_skip3: slot 0 has the str #77 command, slot 3 the skip-once)."""
    acting = mode in ("exit", "timer") and k == 0
    flagged = acting or (mode == "skip3" and k == 3)      # the rung's flag is the register r13
    base = L.RING_BASE[k] * 4
    a = [f"@entry {k}", "        mov r1, #0xdeadbeef                 ; @patch res+0",
         f"        mov r2, #0xdeadbeef                 ; @patch res+{base:#x}",
         "        mov r4, pa0", "        mov r5, pa1", "        mov r6, pa2",
         "        ldr r11, #81, drc0                  ; CR_TIMER at the pass's start", "        wdf drc0"]
    if flagged:
        a += ["        mov r13, #0x00000001                ; the flag of this pass's rung: 1 logged, 3 own end, 4 tail",
              "        mov r14, #0x00000000                ; the ACT in force on this pass (0: none)"]
    if k == 0 and mode in ("exit", "timer", "skip3"):
        a += _pass_counter(k)
    if mode == "skip3" and k == 3:
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
              f"        ldad.bypassl1 r10, [r1,+#{L.KIND}], drc0     ; 1 plain tick pass", "        wdf drc0",
              "        and.testtanz.chan0 !c0, p0, r8, r8", "        !p0 br @s0_0",
              "        xor.testtanz.chan0 !c0, p1, r10, #1 ; p1 = KIND is not 1: nothing is wanted", "        p1 br @s0_0",
              "        xor.testtanz.chan0 !c0, p1, r4, #2  ; p1 = pa0 is not 2: not a tick pass", "        p1 br @s0_0",
              "        mov r9, #0x00ffffff", "        and.testtanz.chan0 !c0, p1, r5, r9  ; p1 = a bit in pa1[23:0]: not a plain tick",
              "        p1 br @s0_0",
              "kact:", "        mov r9, #0x00000001", "        ima32.u r8, r8, #1, r9.neg          ; COUNT - 1", f"        stad [r1,+#{L.COUNT}], r8",
              f"        ldad.bypassl1 r8, [r1,+#{L.ACTED}], drc0", f"        ldad.bypassl1 r10, [r1,+#{L.ACT}], drc0", "        wdf drc0",
              "        mov r9, #0xffffffff", "        ima32.u r8, r8, #1, r9.neg          ; ACTED + 1", f"        stad [r1,+#{L.ACTED}], r8",
              f"        stad [r1,+#{L.ACT_SEEN}], r10                ; the ACT this pass acts with (the task's own record)",
              "        mov r14, r10",
              f"        mov r13, #0x{L.SKIP_FLAG:08x}                ; own end: logged with flag 3"]
        for act in (L.ACT_ENDS_TAIL if mode == "exit" else (L.ACT_STR_TAIL,)):
            a += [f"        xor.testtaz.chan0 !c0, p1, r10, #{act}",
                  f"        p1 mov r13, #0x{L.TAIL_FLAG:08x}                ; tail call: logged with flag 4"]
        a += ["        br @s0_0"]
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
    if acting and mode == "exit":
        for act, lab in ((L.ACT_CFI, "endc"), (L.ACT_PHAS, "endp"), (L.ACT_BOTH, "endb")):
            a += [f"        xor.testtaz.chan0 !c0, p1, r14, #{act}", f"        p1 br @{lab}"]
        a += [f"        xor.testtaz.chan0 !c0, p1, r14, #{L.ACT_CONT4}", "        p1 br @act4"]
    if acting and mode == "timer":
        a += [f"        xor.testtaz.chan0 !c0, p1, r14, #{L.ACT_STR_TAIL}", "        p1 br @tstr",
              f"        xor.testtaz.chan0 !c0, p1, r14, #{L.ACT_STR_END}", "        p1 br @tstre"]
    if mode == "skip3" and k == 3:
        a += ["        xor.testtaz.chan0 !c0, p1, r14, #1  ; p1 = the skipped pass", "        p1 br @end3"]
    if mode == "skip3" and k == 0:
        a += [f"        ldad.bypassl1 r8, [r1,+#{L.CMD}], drc0", "        wdf drc0",
              f"        xor.testtaz.chan0 !c0, p1, r8, #{L.SC_CMD_CLEAR}", "        !p1 br @t0",
              f"        ldad.bypassl1 r10, [r1,+#{L.SC_VAL}], drc0", "        wdf drc0",
              "        str #77, r10                        ; CR_EVENT_HOST_CLEAR (0x0134): the value the host put in the page",
              "        mov r9, #0x00000000", f"        stad [r1,+#{L.CMD}], r9                   ; the command is taken: once",
              "        mov r9, #0x00000002", f"        stad [r1,+#{L.STATE}], r9", IDF, WDF, "        br @t0"]
    t = "\n".join(a) + "\n" + TRIPLE.format(k=k)
    if acting and mode == "exit":
        for lab, ins in OWN_ENDS.items():
            t += f"{lab}:\n" + "\n".join(ins) + "\n"
        t += "act4:\n        mov r30, #0xdeadbeef                ; @patch cont4\n        mov pclink, r30\n        lapc\n"
    if acting and mode == "timer":
        word = f"0x{L.TIMER_STR_WORD:08x}"
        t += (f"tstr:\n        mov r12, #{word}              ; the word the closed tick handler stores (E155)\n"
              "        str #691, r12                       ; CR_EVENT_TIMER (0x0acc)\n        br @t0\n"
              f"tstre:\n        mov r12, #{word}\n        str #691, r12\n" + "\n".join([IDF, WDF, END]) + "\n")
    if mode == "skip3" and k == 3:
        t += "end3:\n" + "\n".join([IDF, WDF, END + "                             ; the skipped pass: the closed task is not called"]) + "\n"
    return t


def ring_source(name):
    mode = {"ring_exit": "exit", "ring_timer": "timer", "ring_skip3": "skip3"}[name]
    desc = {"ring_exit": "ACT 3 own end + cfi.global, 4 + phas, 5 + both (the exact exit), 6 tail to the exit (cont4)",
            "ring_timer": "ACT 7 str #691 then the closed task, 8 str #691 then our own end",
            "ring_skip3": "slot 3 skip-once (the fill's end of render), slot 0 command 2 str #77"}[name]
    hdr = (f"; SPDX-License-Identifier: MIT\n; {name}.s -- generated by closing3/r3k-events/gen/r3kblobs.py (R3k, PREPARED, NOT RUN)\n"
           f"; S2's event ring (slots 16, 8, 8, 8 rungs), the pass counter (dword 20).  {desc}.\n"
           "; Our own source (usse_isa.md, E146, E155, E532, E746, E747, E793, readings R-1 to R-4); only forms the landed verifier\n"
           "; accepts.  No sa write, no pa, i or pclink write but the tail triples.\n\n")
    return hdr + "".join(ring_entry(k, mode) for k in range(4))


# ---- pa_write2.s ---------------------------------------------------------------------------------------------------------------
def _area_a():
    names = ["r4", "r5", "r6", "r7", "r8", "r10", "r11", "r12", "r13", "r14", "r15", "r16"]
    return [f"        stad [r1,+#{L.PW_A + i}], {r}                  ; {f}" for i, (r, f) in enumerate(zip(names, L.PW_FIELDS))]


def _area_b():
    names = ["r4", "r5", "r6", "r7", "r8", "r10", "r11", "r12", "r13", "r14", "r15", "r16"]
    return [f"        stad [r1,+#{L.PW_B + i}], {r}                  ; {f}" for i, (r, f) in enumerate(zip(names, L.PW_FIELDS))]


def pa_write_source():
    a = ["; SPDX-License-Identifier: MIT",
         "; pa_write2.s -- generated by closing3/r3k-events/gen/r3kblobs.py (R3k stage e2b, PREPARED, NOT RUN)",
         "; E2a's pa_write.s (closing/s2) plus cmd 4 (mov pa3), 5 (mov pa4), 6 (mov pa2): each writes the host's marker, reads back the pa",
         "; and its alias in the same pass (80/81, 82/83, 84/85), then arms the next pass's read (cmd 9, area B).  Never pa0, pa1.", "",
         "@entry 0", "        mov r1, #0xdeadbeef                 ; @patch res+0", "        mov r4, pa0", "        mov r5, pa1", "        mov r6, pa2",
         "        mov r7, pa3", "        mov r8, pa4", "        mov r10, sa64", "        mov r11, sa65", "        mov r12, sa66",
         "        mov r13, sa67", "        mov r14, sa68", "        mov r15, sa0", "        ldr r16, #81, drc0", "        wdf drc0",
         f"        ldad.bypassl1 r2, [r1,+#{L.CMD}], drc0", "        wdf drc0", "        and.testtanz.chan0 !c0, p0, r2, r2",
         "        p0 br @work", "tail:", "        mov r30, #0xdeadbeef                ; @patch cont0", "        mov pclink, r30",
         "        lapc", "work:"]
    for n in (1, 9, 2, 3, 4, 5, 6):
        a += [f"        xor.testtaz.chan0 !c0, p1, r2, #{n}", f"        p1 br @c{n}"]
    a += ["        br @tail"]
    a += ["c1:"] + _area_a() + [f"        ldad.bypassl1 r9, [r1,+#{L.RUNID}], drc0", "        wdf drc0", f"        stad [r1,+#{L.ECHO}], r9",
                                "        mov r3, #0x00000009", f"        stad [r1,+#{L.CMD}], r3                   ; cmd = 9: the next pass reads again",
                                IDF, WDF, "        mov r3, #0x00000002", f"        stad [r1,+#{L.STATE}], r3", IDF, WDF, "        br @tail"]
    a += ["c9:"] + _area_b() + ["        mov r3, #0x00000000", f"        stad [r1,+#{L.CMD}], r3                   ; cmd = 0", IDF, WDF,
                                "        mov r3, #0x00000003", f"        stad [r1,+#{L.STATE}], r3", IDF, WDF, "        br @tail"]
    # writers: pre-state in area A, the write, the read-backs
    writes = {2: ("sa67", "sa67", "pa3"), 3: ("sa68", "sa68", "pa4"), 4: ("pa3", "pa3", "sa67"), 5: ("pa4", "pa4", "sa68"),
              6: ("pa2", "pa2", "sa66")}
    for n, (dst, first, second) in writes.items():
        o = L.PW_C_OF[n][0]
        read1, read2 = (f"mov r17, {dst}", f"mov r18, {second}") if dst.startswith("pa") else (f"mov r17, {second}", f"mov r18, {dst}")
        # cmd 2/3: E2a's order (r17 = the pa, r18 = the sa);  cmd 4/5/6: r17 = the pa written, r18 = its sa alias
        if dst.startswith("pa"):
            r17, r18 = f"mov r17, {dst}", f"mov r18, {second}"
        else:
            r17, r18 = f"mov r17, {second}", f"mov r18, {dst}"
        a += [f"c{n}:"] + _area_a() + [f"        ldad.bypassl1 r9, [r1,+#{L.PW_M}], drc0", "        wdf drc0",
                                       f"        mov {dst}, r9                       ; the one write of this command", f"        {r17}",
                                       f"        {r18}", f"        stad [r1,+#{o}], r17", f"        stad [r1,+#{o + 1}], r18", "        br @fin"]
    a += ["fin:"] + [f"        ldad.bypassl1 r{22 + i}, [r1,+#{L.PW_FLAGS + i}], drc0" for i in range(4)] + [
        f"        ldad.bypassl1 r9, [r1,+#{L.RUNID}], drc0", "        wdf drc0", f"        stad [r1,+#{L.ECHO}], r9",
        "        mov r3, #0x00000009", f"        stad [r1,+#{L.CMD}], r3                   ; cmd = 9: the next pass reads again", IDF, WDF,
        "        mov r3, #0x00000002", f"        stad [r1,+#{L.STATE}], r3", IDF, WDF,
        "        and.testtanz.chan0 !c0, p0, r22, r22   ; p0..p3 at the tail call as E536's writer",
        "        and.testtanz.chan0 !c0, p1, r23, r23", "        and.testtanz.chan0 !c0, p2, r24, r24",
        "        and.testtanz.chan0 !c0, p3, r25, r25", "        br @tail"]
    return "\n".join(a) + "\n"


# ---- strclr.s ------------------------------------------------------------------------------------------------------------------
def strclr_source():
    a = ["; SPDX-License-Identifier: MIT",
         "; strclr.s -- generated by closing3/r3k-events/gen/r3kblobs.py (R3k stage e3a, PREPARED, NOT RUN)",
         "; Slot 0 on host command CMD 1: `str #69, rV` (CR_EVENT_HOST_CLEAR2 0x0114; V, bit 15 or bit 6, from the page), the record, then",
         "; the tail call.  Every other pass and every other entry is a plain tail call.  The only `str` of the blob.", "",
         "@entry 0", "        mov r1, #0xdeadbeef                 ; @patch res+0",
         f"        ldad.bypassl1 r2, [r1,+#{L.CMD}], drc0", "        wdf drc0", "        and.testtanz.chan0 !c0, p0, r2, r2",
         "        p0 br @work", "tail:", "        mov r30, #0xdeadbeef                ; @patch cont0", "        mov pclink, r30", "        lapc",
         "work:", f"        xor.testtaz.chan0 !c0, p1, r2, #{L.SC_CMD_CLEAR2}", "        p1 br @c1", "        br @tail", "c1:",
         f"        ldad.bypassl1 r10, [r1,+#{L.SC_VAL}], drc0", "        wdf drc0",
         "        str #69, r10                        ; CR_EVENT_HOST_CLEAR2 (0x0114): the value the host put in the page",
         f"        ldad.bypassl1 r9, [r1,+#{L.RUNID}], drc0", "        wdf drc0", f"        stad [r1,+#{L.ECHO}], r9",
         "        mov r3, #0x00000000", f"        stad [r1,+#{L.CMD}], r3                   ; the command is taken: once",
         "        mov r3, #0x00000002", f"        stad [r1,+#{L.STATE}], r3", IDF, WDF, "        br @tail"]
    for k in (1, 2, 3):
        a += [f"@entry {k}"] + TRIPLE.format(k=k).splitlines()
    return "\n".join(a) + "\n"


SOURCES = {"ring_exit": lambda: ring_source("ring_exit"), "ring_timer": lambda: ring_source("ring_timer"),
           "ring_skip3": lambda: ring_source("ring_skip3"), "pa_write2": pa_write_source, "strclr": strclr_source}


def build(name):
    """(source text, blob bytes) of one of the generated tasks; the landed verifier runs inside build_blob_text."""
    if name == "alias2":
        return B.build(name)
    text = SOURCES[name]()
    return text, B.fwtask.build_blob_text(text, B.fwtask.load_regs())
