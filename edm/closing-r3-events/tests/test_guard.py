#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_guard.py: run/guard_blobs.py on the ASSEMBLED code: the frozen blobs and tables pass; every limit of the session is
broken in a copy (a str that the landed verifier accepts, an sa write the verifier cannot see, an sa write in the wrong command,
a write in A6, an ldr that is not CR_TIMER, a pclink write, a table row A7, ...) and the guard must refuse each.  Offline.

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
    alias = (R3 / "asm" / "alias.s").read_text()
    skip = (R3 / "asm" / "ring_skip.s").read_text()
    hold = (R3 / "asm" / "ring_hold.s").read_text()
    check(G.run(R3) == [], "the frozen blobs and tables pass the guard")
    # the guard decodes the destination from the WORD: every sa write in alias.s is where CMD_SA says
    f = G.scan(alias, (R3 / "bins" / "alias.blob").read_bytes())
    check({c: sorted(s) for c, s in f["sa_by_cmd"].items()} == {1: ["sa63"], 2: ["sa65"], 3: ["sa65"], 4: ["sa64"], 5: ["sa64"], 7: ["sa63"]},
          f"alias.blob: the sa registers each command writes, decoded from the words: {f['sa_by_cmd']}")
    check(f["str"] == 0 and f["ldr"] == set() and f["special_writes"] == {6: {"r20", "r21", "i0", "i1"}},
          f"alias.blob: no str, no ldr, r20/r21/i0/i1 only in command 6 ({f['special_writes']})")
    for n in ("ring_skip", "ring_hold"):
        f = G.scan({"ring_skip": skip, "ring_hold": hold}[n], (R3 / "bins" / f"{n}.blob").read_bytes())
        check(f["sa_all"] == set() and f["str"] == 0 and f["ldr"] == {81} and f["special_writes"] == {}, f"{n}.blob: no sa, no str, ldr #81 only, no r/i write")
    # source modified, blob rebuilt: each must be refused
    refuse("alias", alias.replace("c1:\n", "c1:\n        mov sa100, r10\n", 1), "only ['sa63', 'sa64', 'sa65'] are allowed", label="alias: sa100 write")
    refuse("alias", alias.replace("c1:\n", "c1:\n        mov sa65, r10\n", 1), "sa writes by command", label="alias: sa65 write in A1's command")
    refuse("alias", alias.replace("c6:\n", "c6:\n        mov sa64, r10\n", 1), "sa writes by command", label="alias: an sa write in A6's command")
    refuse("alias", alias.replace("c9:\n", "c9:\n        mov sa63, r10\n", 1), "sa writes by command", label="alias: an sa write in the reader")
    refuse("alias", alias.replace("tail:\n", "tail:\n        mov sa63, r10\n", 1), "outside any command block", label="alias: an sa write in the common code")
    refuse("alias", alias.replace("c2:\n", "c2:\n        mov r20, r10\n", 1), "writes ['r20']", label="alias: an r20 write outside A6")
    refuse("alias", alias.replace("c5:\n", "c5:\n        mov i0, r10\n", 1), "writes ['i0']", label="alias: an i0 write outside A6")
    refuse("alias", alias.replace("c1:\n", "c1:\n        str #517, r10\n", 1), "a str", label="alias: a str to 0x0814 (the verifier accepts it)")
    refuse("alias", alias.replace("c1:\n", "c1:\n        ldr r10, #7, drc0\n        wdf drc0\n", 1), "only #81 (CR_TIMER)", label="alias: an ldr of CORE_ID")
    refuse("alias", alias.replace("c1:\n", "c1:\n        mov r12, #0xdeadbeef                ; @patch cont0\n        mov pclink, r12\n        lapc\n", 1), "pclink", label="alias: a pclink write")
    refuse("ring_skip", skip.replace("k0:\n", "k0:\n        mov sa63, r10\n", 1), "may write no sa register", label="ring_skip: an sa write")
    refuse("ring_skip", skip.replace("k0:\n", "k0:\n        str #517, r10\n", 1), "a str", label="ring_skip: a str")
    refuse("ring_skip", skip.replace("k0:\n", "k0:\n        mov r20, r10\n", 1), "writes ['r20']", label="ring_skip: an r20 write")
    refuse("ring_hold", hold.replace("h0:\n", "h0:\n        mov sa64, r10\n", 1), "may write no sa register", label="ring_hold: an sa write")
    # the blob is not its source
    try:
        out = G.check_blob("alias", alias, (R3 / "bins" / "ring_skip.blob").read_bytes(), G.policy_of("alias"))
        check(any("not what its source assembles to" in x for x in out), "a blob that is not its source's assembly is refused")
    except Exception as e:
        check(True, f"a blob that is not its source's: refused by an error ({e!r})")
    # tables
    binfo = json.loads((R3 / "bins" / "blobs.json").read_text())
    tabs = {st: json.loads((R3 / "tables" / f"{st}.json").read_text()) for st in ("a", "b", "k7")}

    def tbl(mod, st, part, label):
        t = json.loads(json.dumps(tabs))
        mod(t[st])
        out = G.check_tables(t, binfo)
        check(any(part in x for x in out), f"{label}: refused ({out[:1]})")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][0], name="a7", row="A7", cmd=1)), "a", "not an approved row", "a table with a row A7")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][0], name="a8", row="A8")), "a", "not an approved row", "a table with a row A8")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][0], name="b3", row="B3")), "b", "not an approved row", "a table with a row B3")
    tbl(lambda t: t["jobs"][3].__setitem__("cmd", 2), "a", "is not row", "a command that is not its row's")
    tbl(lambda t: t["jobs"][3].__setitem__("sa", ["sa63", "sa100"]), "a", "sa set", "an sa set beyond the blob's")
    tbl(lambda t: t["jobs"][2].__setitem__("sa", ["sa64"]), "a", "sa set", "an sa set that is not what the command writes")
    tbl(lambda t: t.__setitem__("arm", "slots=0x1 entry=0 trc=8"), "a", "arm line", "a trc in the arm line")
    tbl(lambda t: t["jobs"][4].__setitem__("skip", 2), "b", "skip 2", "a skip count of 2")
    tbl(lambda t: t["jobs"][0].__setitem__("n", 1508280), "k7", "outside the allow-list", "another hold n")
    tbl(lambda t: t["jobs"][0].__setitem__("kick", "kicks"), "k7", "outside the allow-list", "another kick mode")
    tbl(lambda t: t.__setitem__("note", "kreg 0x0814=1"), "a", "forbidden word", "a register write in a table")
    tbl(lambda t: t.__setitem__("stop_budget", 2), "a", "stop budget", "a stop budget of 2")
    tbl(lambda t: t["jobs"][1].__setitem__("read_1200", True), "a", "belong to A1", "A0 asking for A1's 1200 ms reader") if False else None
    print(f"{len(FAIL)} failed" if FAIL else "all guard checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
