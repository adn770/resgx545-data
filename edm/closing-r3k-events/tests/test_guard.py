#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_guard.py: run/guard_blobs.py on the ASSEMBLED code: the frozen blobs and tables pass; every limit of the kernel batch is broken in a copy
(a str of a register that is not on the blob's list, a str of the timer with another word, an sa write the verifier cannot see, a mov to pa0 or pa1
or a pa in the wrong command, a cfi outside the exit blocks, a cont4 outside act4, an ldr that is not CR_TIMER, a pclink write, a table row outside
ROW_SPEC, a bare kick, a CLEAR value off the list, ...) and the guard must refuse each.  Offline.

    ../../closing/pixel-faults/.venv/bin/python tests/test_guard.py
"""
import json
import pathlib
import sys

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R3 / "gen"))
sys.path.insert(0, str(R3 / "run"))
import r3layout as L  # noqa: E402
import r3blobs as B  # noqa: E402
import guard_blobs as G  # noqa: E402

fw = B.fwtask
FAIL = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def refuse(name, text, why_part, label="", verifier_ok=False):
    """Assemble the modified source with the landed verifier and run the guard's check on it."""
    try:
        blob = fw.build_blob_text(text, fw.load_regs())
    except fw.VerifyError as e:
        check(verifier_ok, f"{label}: the modified source did not assemble ({e})" + (": refused by the landed verifier itself" if verifier_ok else ""))
        return
    out = G.check_blob(name, text, blob, G.policy_of(name))
    check(any(why_part in x for x in out), f"{label}: refused ({why_part!r} in {out[:2]})")


def src(n):
    return (R3 / "asm" / f"{n}.s").read_text()


def main():
    S = {n: src(n) for n in L.BLOBS}
    check(G.run(R3) == [], "the frozen blobs and tables pass the guard")
    # decoded from the words
    f = G.scan("alias2", S["alias2"], (R3 / "bins" / "alias2.blob").read_bytes())
    check({c: sorted(s) for c, s in f["sa_by_cmd"].items()} == {1: ["sa63"], 2: ["sa65"], 3: ["sa65"], 4: ["sa64"], 5: ["sa64"], 7: ["sa63"],
                                                              10: ["sa65"], 11: ["sa63", "sa64", "sa65"], 12: ["sa64"]}, f"alias2: the sa registers each command writes: {f['sa_by_cmd']}")
    f = G.scan("pa_write2", S["pa_write2"], (R3 / "bins" / "pa_write2.blob").read_bytes())
    check({c: sorted(s) for c, s in f["sa_by_cmd"].items()} == {2: ["sa67"], 3: ["sa68"]} and {c: sorted(s) for c, s in f["pa"].items()} == {4: ["pa3"], 5: ["pa4"], 6: ["pa2"]},
          f"pa_write2: sa67 in 2, sa68 in 3; pa3 in 4, pa4 in 5, pa2 in 6 ({f['sa_by_cmd']}, {f['pa']})")
    for n, want in (("ring_timer", [691, 691]), ("strclr", [69]), ("ring_skip3", [77]), ("ring_exit", []), ("ring_hold", [])):
        f = G.scan(n, S[n], (R3 / "bins" / f"{n}.blob").read_bytes())
        check(sorted(f["str"]) == want and f["sa_all"] == set() and f["pa"] == {} and f["ldr"] <= {81}, f"{n}: str {f['str']}, no sa, no pa write, ldr #81 only")
    f = G.scan("ring_exit", S["ring_exit"], (R3 / "bins" / "ring_exit.blob").read_bytes())
    check(sum(len(v) for v in f["exit"].values()) == 4 and f["pclink"] == 5, f"ring_exit: the exit's four words (cfi x2, phas x2) and five pclink writes (four entries and act4)")
    # source modified, blob rebuilt: each must be refused
    a = S["alias2"]
    refuse("alias2", a.replace("c1:\n", "c1:\n        mov sa100, r10\n", 1), "only ['sa63', 'sa64', 'sa65'] are allowed", label="alias2: sa100 write")
    refuse("alias2", a.replace("c1:\n", "c1:\n        mov sa65, r10\n", 1), "sa writes by command", label="alias2: sa65 write in A1's command")
    refuse("alias2", a.replace("c12:\n", "c12:\n        mov sa63, r10\n", 1), "sa writes by command", label="alias2: an sa63 write in cmd 12 (sa64 only)")
    refuse("alias2", a.replace("tail:\n", "tail:\n        mov sa63, r10\n", 1), "outside any command block", label="alias2: an sa write in the common code")
    refuse("alias2", a.replace("c2:\n", "c2:\n        mov r20, r10\n", 1), "writes ['r20']", label="alias2: an r20 write outside 6 and 11")
    refuse("alias2", a.replace("c1:\n", "c1:\n        str #517, r10\n", 1), "str register", label="alias2: a str to 0x0814 (the verifier accepts it)")
    refuse("alias2", a.replace("c1:\n", "c1:\n        str #691, r10\n", 1), "str register", label="alias2: the EVENT_TIMER str outside ring_timer")
    refuse("alias2", a.replace("c10:\n", "c10:\n        ldr r10, #7, drc0\n        wdf drc0\n", 1), "only #81 (CR_TIMER)", label="alias2: an ldr of CORE_ID")
    refuse("alias2", a.replace("c1:\n", "c1:\n        mov pa3, r10\n", 1), "outside pa_write2.s", label="alias2: a mov to pa3")
    refuse("alias2", a.replace("c1:\n", "c1:\n        cfi.global #3, #0, #3\n", 1), "carries the closed exit's words", label="alias2: the exit's cfi word")
    pw = S["pa_write2"]
    refuse("pa_write2", pw.replace("mov pa3, r9", "mov pa1, r9", 1), "pa1", label="pa_write2: mov to pa1", verifier_ok=True)
    refuse("pa_write2", pw.replace("mov pa3, r9", "mov pa0, r9", 1), "pa0", label="pa_write2: mov to pa0", verifier_ok=True)
    refuse("pa_write2", pw.replace("mov pa4, r9", "mov pa3, r9", 1), "pa writes by command", label="pa_write2: command 5 writes pa3")
    refuse("pa_write2", pw.replace("c1:\n", "c1:\n        mov pa2, r10\n", 1), "pa writes by command", label="pa_write2: a pa write in the read command")
    refuse("pa_write2", pw.replace("c9:\n", "c9:\n        mov sa67, r10\n", 1), "sa writes by command", label="pa_write2: an sa write in the next-pass read")
    refuse("pa_write2", pw.replace("c2:\n", "c2:\n        mov sa66, r9\n", 1), "only ['sa67', 'sa68']", label="pa_write2: sa66 written (the PDS's word)")
    rt = S["ring_timer"]
    refuse("ring_timer", rt.replace("mov r12, #0x01061a80", "mov r12, #0x01061a70", 1), "the EVENT_TIMER store is not", label="ring_timer: the word of the tick's pa2 instead of the handler's")
    refuse("ring_timer", rt.replace("str #691, r12", "str #517, r12", 1), "str of register #517", label="ring_timer: a str of 0x0814")
    refuse("ring_timer", rt.replace("tstr:\n", "tstr:\n        str #691, r12\n", 1), "the EVENT_TIMER store is not", label="ring_timer: a third store without its mov")
    refuse("ring_timer", rt.replace("k0:\n", "k0:\n        mov sa63, r10\n", 1), "may write no sa register", label="ring_timer: an sa write")
    sc = S["strclr"]
    refuse("strclr", sc.replace("str #69, r10", "str #77, r10", 1), "str of register #77", label="strclr: the CLEAR register instead of CLEAR2")
    refuse("strclr", sc.replace("c1:\n", "c1:\n        str #69, r10\n", 1), "str registers", label="strclr: two stores")
    sk = S["ring_skip3"]
    refuse("ring_skip3", sk.replace("str #77, r10", "str #69, r10", 1), "str of register #69", label="ring_skip3: CLEAR2 instead of CLEAR")
    refuse("ring_skip3", sk.replace("noskip:\n", "noskip:\n        mov pa3, r10\n", 1), "outside pa_write2.s", label="ring_skip3: a pa write")
    ex = S["ring_exit"]
    refuse("ring_exit", ex.replace("k0:\n", "k0:\n        cfi.global #3, #0, #3\n", 1), "exit words", label="ring_exit: a cfi in the common code")
    refuse("ring_exit", ex.replace("endp:\n", "endp:\n        cfi.global #3, #0, #3\n", 1), "block endp has the exit words", label="ring_exit: a cfi in the phas-only block")
    refuse("ring_exit", ex.replace("endc:\n        cfi.global #3, #0, #3                 ; the exit's first word (R-1)\n", "endc:\n", 1), "block endc has the exit words", label="ring_exit: the cfi block without its cfi")
    refuse("ring_exit", ex.replace("act4:\n        mov r30, #0xdeadbeef                ; @patch cont4", "act4:\n        mov r30, #0xdeadbeef                ; @patch cont1", 1), "continue patches", label="ring_exit: act4 continues slot 1, not the exit")
    refuse("ring_exit", ex.replace("k0:\n", "k0:\n        mov r30, #0xdeadbeef                ; @patch cont4\n        mov pclink, r30\n        lapc\n", 1), "pclink writes", label="ring_exit: a second cont4 triple outside act4")
    refuse("ring_exit", ex.replace("k0:\n", "k0:\n        str #691, r10\n", 1), "str register", label="ring_exit: a str")
    refuse("ring_hold", src("ring_hold").replace("h0:\n", "h0:\n        mov sa64, r10\n", 1), "may write no sa register", label="ring_hold: an sa write")
    for name in ("ring_timer", "ring_skip3", "ring_hold", "pa_write2", "strclr"):
        t = S[name].replace("@patch cont0", "@patch cont4", 1) if "@patch cont0" in S[name] else None
        if t:
            refuse(name, t, "continue patches", label=f"{name}: a cont4 triple")
    # the blob is not its source
    try:
        out = G.check_blob("alias2", a, (R3 / "bins" / "ring_hold.blob").read_bytes(), G.policy_of("alias2"))
        check(any("not what its source assembles to" in x for x in out), "a blob that is not its source's assembly is refused")
    except Exception as e:
        check(True, f"a blob that is not its source's: refused by an error ({e!r})")
    # tables
    binfo = json.loads((R3 / "bins" / "blobs.json").read_text())
    tabs = {st: json.loads((R3 / "tables" / f"{st}.json").read_text()) for st in L.STAGES}

    def tbl(mod, st, part, label):
        t = json.loads(json.dumps(tabs))
        mod(t[st])
        out = G.check_tables(t, binfo)
        check(any(part in x for x in out), f"{label}: refused ({out[:1]})")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][0], name="c6x", row="C6")), "k0c", "not an approved row", "a table with a row C6")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][0], name="b3", row="B3")), "f", "not an approved row", "stage f with L3's B3")
    tbl(lambda t: t["jobs"][5].__setitem__("act", 5), "f", "differs in", "FCF with the replica's act")
    tbl(lambda t: t["jobs"][1].__setitem__("act", 2), "f", "differs in", "the cont4 control with L3's slot-2 tail")
    tbl(lambda t: t["jobs"][1].__setitem__("trigger", "kick"), "f", "never a bare kick", "a bare kick as a trigger")
    tbl(lambda t: t["jobs"][1].__setitem__("trigger", "kicker"), "f", "never a bare kick", "the kicker file as a trigger")
    tbl(lambda t: t["jobs"].reverse(), "f", "differs in", "the rows out of the frozen order")
    tbl(lambda t: t["jobs"][4].pop("run_if"), "f", "differs in", "FB without its gate on the control")
    tbl(lambda t: t.__setitem__("stop_budget", 3), "f", "stop budget", "stage f with a stop budget of 3 (cap 2 stops)")
    tbl(lambda t: t.__setitem__("stop_budget", 1), "e3b", "stop budget", "stage e3b with a stop budget of 1 (its budget is 3 stops)")
    tbl(lambda t: t["jobs"][1].__setitem__("set_kicker", 67), "kb", "differs in", "a kicker word other than 0x42")
    tbl(lambda t: t["jobs"][0].__setitem__("no_bump", True), "kb", "differs in", "Q0 with kick_no_bump")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][0], name="q9", row="Q9")), "kb", "not an approved row", "a table with a Q9 row")
    tbl(lambda t: t["jobs"][0].__setitem__("pa", ["pa0"]), "e2b", "pa write outside pa2-pa4", "a pa write set on pa0")
    tbl(lambda t: t["jobs"][4].__setitem__("cmd", 6), "e2b", "differs in", "C4 with command 6")
    tbl(lambda t: t["jobs"][4].__setitem__("marker", 0), "e2b", "differs in", "C4 with another marker")
    tbl(lambda t: t["jobs"][0]["steps"][2].__setitem__(1, 0x4), "e3h", "differs in", "a CLEAR2 value off bits 15 and 6")
    tbl(lambda t: t["jobs"][0]["steps"][3].__setitem__(1, 0x8000), "e3a", "differs in", "step 4 writing bit 15 again")
    tbl(lambda t: t["jobs"][3].__setitem__("clear_values", [0x8000, 0x4]), "e3b", "differs in", "a CLEAR value other than bit 18")
    tbl(lambda t: t["jobs"][3].__setitem__("timer_bit", 0x40000000), "e3b", "differs in", "another timer bit")
    tbl(lambda t: t["jobs"][0].__setitem__("hold_recovery", "Y"), "e3b", "differs in", "hold_recovery Y in b0")
    tbl(lambda t: t["jobs"][3].__setitem__("hold_recovery", "N"), "e3b", "differs in", "hold_recovery N in b1")
    tbl(lambda t: t.__setitem__("note", "kreg 0x0814=1"), "k0c", "forbidden word", "a register write in a table")
    tbl(lambda t: t.__setitem__("note", "kpoke"), "kb", "forbidden word", "a kpoke in a table")
    tbl(lambda t: t.__setitem__("note", "0x0c00"), "e3b", "forbidden word", "a BIF register in a table")
    tbl(lambda t: t.__setitem__("arm", "slots=0x1 entry=0 trc=8"), "e2b", "arm line", "a trc in the arm line")
    tbl(lambda t: t.__setitem__("per_job_reset", False), "kb", "per_job_reset", "per_job_reset flipped")
    tbl(lambda t: t["jobs"][1].__setitem__("args", t["jobs"][1]["args"] + ["--kpoke", "x"]), "k0t", "differs in", "a poke argument in a tool job")
    tbl(lambda t: t["jobs"][0].__setitem__("n", 1508280), "k0h", "outside the allow-list", "another hold n")
    tbl(lambda t: [j.__setitem__("w65", {"k": 1, "or": 0x00800010}) for j in t["jobs"] if j["row"] == "C1"], "k0c", "some ukernel code tests", "C1 with bit 4 (a handler)")
    # the frozen values of the rows themselves
    old = L.CLEAR_BITS
    L.CLEAR_BITS = (0x8000, 0x4)
    check(any("CLEAR_BITS" in x for x in G.check_rowspec()), "r3layout: another CLEAR value is refused")
    L.CLEAR_BITS = old
    old = L.CLEAR2_BITS
    L.CLEAR2_BITS = (0x8000, 0x10)
    check(any("CLEAR2_BITS" in x for x in G.check_rowspec()), "r3layout: another CLEAR2 value is refused")
    L.CLEAR2_BITS = old
    check(G.check_rowspec() == [], "r3layout's rows pass the guard again")
    print(f"{len(FAIL)} failed" if FAIL else "all guard checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
