#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_guard.py: run/guard_blobs.py on the ASSEMBLED code: the frozen blobs and tables pass; every limit of the session is
broken in a copy (a str that the landed verifier accepts, an sa write the verifier cannot see, an sa write in the wrong command,
a write in A6, an ldr that is not CR_TIMER, a pclink write, a table row outside ROW_SPEC, a bare kick, ...) and the guard must refuse each.  Offline.

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


def refuse(name, text, why_part, policy=None, label=""):
    """Assemble the modified source with the landed verifier and run the guard's check on it."""
    try:
        blob = fw.build_blob_text(text, fw.load_regs())
    except fw.VerifyError as e:
        check(False, f"{label}: the modified source did not assemble ({e})")
        return
    out = G.check_blob(name, text, blob, policy or G.policy_of(name))
    check(any(why_part in x for x in out), f"{label}: refused ({why_part!r} in {out[:2]})")


def main():
    alias = (R3 / "asm" / "alias2.s").read_text()
    end = (R3 / "asm" / "ring_end.s").read_text()
    hold = (R3 / "asm" / "ring_hold.s").read_text()
    check(G.run(R3) == [], "the frozen blobs and tables pass the guard")
    # the guard decodes the destination from the WORD: every sa write in alias2.s is where CMD_SA2 says
    f = G.scan(alias, (R3 / "bins" / "alias2.blob").read_bytes())
    check({c: sorted(s) for c, s in f["sa_by_cmd"].items()} == {1: ["sa63"], 2: ["sa65"], 3: ["sa65"], 4: ["sa64"], 5: ["sa64"], 7: ["sa63"],
                                                              10: ["sa65"], 11: ["sa63", "sa64", "sa65"], 12: ["sa64"]},
          f"alias2.blob: the sa registers each command writes, decoded from the words: {f['sa_by_cmd']}")
    check(f["str"] == 0 and f["ldr"] == set() and f["special_writes"] == {6: {"r20", "r21", "i0", "i1"}, 11: {"r20", "r21", "i0", "i1"}},
          f"alias2.blob: no str, no ldr, r20/r21/i0/i1 only in commands 6 and 11 ({f['special_writes']})")
    for n in ("ring_end", "ring_hold"):
        f = G.scan({"ring_end": end, "ring_hold": hold}[n], (R3 / "bins" / f"{n}.blob").read_bytes())
        check(f["sa_all"] == set() and f["str"] == 0 and f["ldr"] == {81} and f["special_writes"] == {}, f"{n}.blob: no sa, no str, ldr #81 only, no r/i write")
    check(G.scan(end, (R3 / "bins" / "ring_end.blob").read_bytes())["pclink"] == 5, "ring_end.blob: five pclink writes (four entries and the act0 triple)")
    # source modified, blob rebuilt: each must be refused
    refuse("alias2", alias.replace("c1:\n", "c1:\n        mov sa100, r10\n", 1), "only ['sa63', 'sa64', 'sa65'] are allowed", label="alias2: sa100 write")
    refuse("alias2", alias.replace("c1:\n", "c1:\n        mov sa65, r10\n", 1), "sa writes by command", label="alias2: sa65 write in A1's command")
    refuse("alias2", alias.replace("c10:\n", "c10:\n        mov sa64, r10\n", 1), "sa writes by command", label="alias2: an sa64 write in cmd 10 (sa65 only)")
    refuse("alias2", alias.replace("c12:\n", "c12:\n        mov sa63, r10\n", 1), "sa writes by command", label="alias2: an sa63 write in cmd 12 (sa64 only)")
    refuse("alias2", alias.replace("c12more:\n", "c12more:\n        mov sa65, r10\n", 1), "sa writes by command", label="alias2: an sa65 write in cmd 12's second block")
    refuse("alias2", alias.replace("c6:\n", "c6:\n        mov sa64, r10\n", 1), "sa writes by command", label="alias2: an sa write in A6's command")
    refuse("alias2", alias.replace("c9:\n", "c9:\n        mov sa63, r10\n", 1), "sa writes by command", label="alias2: an sa write in the reader")
    refuse("alias2", alias.replace("tail:\n", "tail:\n        mov sa63, r10\n", 1), "outside any command block", label="alias2: an sa write in the common code")
    refuse("alias2", alias.replace("c2:\n", "c2:\n        mov r20, r10\n", 1), "writes ['r20']", label="alias2: an r20 write outside 6 and 11")
    refuse("alias2", alias.replace("c12:\n", "c12:\n        mov i0, r10\n", 1), "writes ['i0']", label="alias2: an i0 write in cmd 12")
    refuse("alias2", alias.replace("c1:\n", "c1:\n        str #517, r10\n", 1), "a str", label="alias2: a str to 0x0814 (the verifier accepts it)")
    refuse("alias2", alias.replace("c10:\n", "c10:\n        ldr r10, #7, drc0\n        wdf drc0\n", 1), "only #81 (CR_TIMER)", label="alias2: an ldr of CORE_ID")
    refuse("alias2", alias.replace("c1:\n", "c1:\n        mov r12, #0xdeadbeef                ; @patch cont0\n        mov pclink, r12\n        lapc\n", 1), "pclink", label="alias2: a pclink write")
    refuse("ring_end", end.replace("k0:\n", "k0:\n        mov sa63, r10\n", 1), "may write no sa register", label="ring_end: an sa write")
    refuse("ring_end", end.replace("k0:\n", "k0:\n        str #517, r10\n", 1), "a str", label="ring_end: a str")
    refuse("ring_end", end.replace("k0:\n", "k0:\n        mov r20, r10\n", 1), "writes ['r20']", label="ring_end: an r20 write")
    refuse("ring_end", end.replace("act0:\n        mov r30, #0xdeadbeef                ; @patch cont2", "act0:\n        mov r30, #0xdeadbeef                ; @patch cont1", 1),
           "continue patches", label="ring_end: the act0 triple continues slot 1, not slot 2")
    refuse("ring_end", end.replace("act0:\n        mov r30, #0xdeadbeef                ; @patch cont2", "act0:\n        mov r30, #0xdeadbeef                ; @patch cont3", 1),
           "continue patches", label="ring_end: the act0 triple continues slot 3")
    refuse("ring_end", end.replace("k0:\n", "k0:\n        mov r30, #0xdeadbeef                ; @patch cont2\n        mov pclink, r30\n        lapc\n", 1),
           "pclink writes", label="ring_end: a third continue triple outside act0")
    refuse("ring_hold", hold.replace("h0:\n", "h0:\n        mov sa64, r10\n", 1), "may write no sa register", label="ring_hold: an sa write")
    # the blob is not its source
    try:
        out = G.check_blob("alias2", alias, (R3 / "bins" / "ring_end.blob").read_bytes(), G.policy_of("alias2"))
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
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][0], name="c6", row="C6")), "c", "not an approved row", "a table with a row C6")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][0], name="f0", row="F0")), "e", "not an approved row", "a table with a stage-f row")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][0], name="q0", row="Q0")), "d", "not an approved row", "a table with a Q290 row")
    tbl(lambda t: t["jobs"][3].__setitem__("cmd", 11), "c", "differs in", "a command that is not its row's")
    tbl(lambda t: t["jobs"][3].__setitem__("sa", ["sa63", "sa100"]), "c", "sa set", "an sa set beyond the blob's")
    tbl(lambda t: t["jobs"][2].__setitem__("sa", ["sa64"]), "c", "sa set", "an sa set that is not what the command writes")
    tbl(lambda t: t.__setitem__("arm", "slots=0x1 entry=0 trc=8"), "c", "arm line", "a trc in the arm line")
    tbl(lambda t: t["jobs"][9].__setitem__("w65", {"k": 1, "or": 0x4}), "c", "differs in", "another word in C4")
    tbl(lambda t: [j.__setitem__("w65", {"k": 1, "or": 0x0001C0CC}) for j in t["jobs"] if j["row"] == "C3"], "c", "some ukernel code tests", "C3 with a bit some ukernel code tests (0x80)")
    tbl(lambda t: [j.__setitem__("w65", {"k": 1, "or": 0x00800010}) for j in t["jobs"] if j["row"] == "C1"], "c", "some ukernel code tests", "C1 with bit 4 (a handler)")
    tbl(lambda t: [j.__setitem__("npass", 49) for j in t["jobs"] if j["row"] == "C5"], "c", "differs in", "C5 with 49 passes")
    tbl(lambda t: t["jobs"][0].__setitem__("n", 1508280), "h", "outside the allow-list", "another hold n")
    tbl(lambda t: t["jobs"][4].__setitem__("sig_ms", [20, 95]), "h", "differs in", "a signature outside the hold")
    tbl(lambda t: t["jobs"][-1].__setitem__("trigger", "kick"), "e", "never a bare kick", "a bare kick as B3's trigger")
    tbl(lambda t: t["jobs"][-1].__setitem__("trigger", "kicker"), "e", "never a bare kick", "the kicker file as a trigger")
    tbl(lambda t: t["jobs"][-1].__setitem__("act", 2), "e", "differs in", "B3 with a tail call")
    tbl(lambda t: t["jobs"][2].__setitem__("act", 1), "e", "differs in", "X1 with an own end")
    tbl(lambda t: t["jobs"][2].__setitem__("count", 2), "e", "differs in", "X1 with count 2")
    tbl(lambda t: t["jobs"].reverse(), "e", "differs in", "B3 first (the order is the frozen one)")
    tbl(lambda t: t.__setitem__("note", "kreg 0x0814=1"), "c", "forbidden word", "a register write in a table")
    tbl(lambda t: t.__setitem__("note", "cont4"), "e", "forbidden word", "cont4 in a table")
    tbl(lambda t: t.__setitem__("stop_budget", 2), "c", "stop budget", "a stop budget of 2")
    tbl(lambda t: t.__setitem__("stop_budget", 1), "h", "stop budget", "stage h with a stop budget of 1 (its first stop ends it)")
    tbl(lambda t: t.__setitem__("per_job_reset", True), "c", "per_job_reset", "per_job_reset flipped")
    tbl(lambda t: [j.__setitem__("w63", 5) for j in t["jobs"] if j["row"] == "D1"], "d", "differs in", "a stray sa63 word in D1")
    tbl(lambda t: [j.__setitem__("w65", {"lit": 0xB009C5DD}) for j in t["jobs"] if j["row"] == "D3"], "d", "differs in", "D3 with another word")
    print(f"{len(FAIL)} failed" if FAIL else "all guard checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
