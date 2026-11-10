#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_guard.py: run/guard_blobs.py on the ASSEMBLED code: the frozen blob and table pass; every limit of the session is broken in a
copy (a str that the landed verifier accepts, an sa write the verifier cannot see, an sa write other than sa63 or in the wrong
command, an r20/i0 write outside the writer, an ldr that is not CR_TIMER, a pclink write, a table row from another session, a stop
budget of 1, ...) and the guard must refuse each.  Offline.

    ../../closing/pixel-faults/.venv/bin/python tests/test_guard.py
"""
import json
import pathlib
import sys

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R3 / "gen"))
sys.path.insert(0, str(R3 / "run"))
import c3layout as L  # noqa: E402
import c3blobs as B  # noqa: E402
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
    start = (R3 / "asm" / "start.s").read_text()
    check(G.run(R3) == [], "the frozen blob and table pass the guard")
    f = G.scan(start, (R3 / "bins" / "start.blob").read_bytes())
    check({c: sorted(s) for c, s in f["sa_by_cmd"].items()} == {1: ["sa63"]},
          f"start.blob: the only sa register written is sa63, in command 1, decoded from the words: {f['sa_by_cmd']}")
    check(f["str"] == 0 and f["ldr"] == set() and f["special_writes"] == {1: {"r20", "r21", "i0", "i1"}},
          f"start.blob: no str, no ldr, r20/r21/i0/i1 only in command 1 ({f['special_writes']})")
    check(f["pclink"] == 1 and f["sa_all"] == {"sa63"}, "start.blob: one pclink triple, sa63 the only sa written")
    # source modified, blob rebuilt: each must be refused
    refuse("start", start.replace("c1:\n", "c1:\n        mov sa100, r10\n", 1), "only ['sa63'] are allowed", label="start: sa100 write")
    refuse("start", start.replace("c1:\n", "c1:\n        mov sa127, r10\n", 1), "only ['sa63'] are allowed", label="start: sa127 write")
    refuse("start", start.replace("c1:\n", "c1:\n        mov sa20, r10\n", 1), "only ['sa63'] are allowed", label="start: sa20 write")
    refuse("start", start.replace("c1:\n", "c1:\n        mov sa64, r10\n", 1), "only ['sa63'] are allowed", label="start: sa64 write (R2-1 b allows it, C3 does not need it)")
    refuse("start", start.replace("c1:\n", "c1:\n        mov sa65, r10\n", 1), "only ['sa63'] are allowed", label="start: sa65 write")
    refuse("start", start.replace("c9:\n", "c9:\n        mov sa63, r10\n", 1), "sa writes by command", label="start: an sa63 write in the reader")
    refuse("start", start.replace("tail:\n", "tail:\n        mov sa63, r10\n", 1), "outside any command block", label="start: an sa63 write in the common code")
    refuse("start", start.replace("c9:\n", "c9:\n        mov r20, r10\n", 1), "writes ['r20']", label="start: an r20 write in the reader")
    refuse("start", start.replace("work:\n", "work:\n        mov i0, r10\n", 1), "writes ['i0']", label="start: an i0 write in the common code")
    refuse("start", start.replace("c1:\n", "c1:\n        str #517, r10\n", 1), "a str", label="start: a str to 0x0814 (the verifier accepts it)")
    refuse("start", start.replace("c9:\n", "c9:\n        ldr r10, #7, drc0\n        wdf drc0\n", 1), "only #81 (CR_TIMER)", label="start: an ldr of CORE_ID")
    refuse("start", start.replace("c9:\n", "c9:\n        mov r12, #0xdeadbeef                ; @patch cont0\n        mov pclink, r12\n        lapc\n", 1), "pclink",
           label="start: a second pclink write")
    # the blob is not its source
    try:
        out = G.check_blob("start", start.replace("c9:\n", "c9:\n        nop\n", 1), (R3 / "bins" / "start.blob").read_bytes(), G.policy_of("start"))
        check(any("not what its source assembles to" in x or "instructions" in x for x in out), "a blob that is not its source's assembly is refused")
    except Exception as e:
        check(True, f"a blob that is not its source's: refused by an error ({e!r})")
    # the table
    binfo = json.loads((R3 / "bins" / "blobs.json").read_text())
    tabs = {"c3": json.loads((R3 / "tables" / "c3.json").read_text())}

    def tbl(mod, part, label):
        t = json.loads(json.dumps(tabs))
        mod(t["c3"])
        out = G.check_tables(t, binfo)
        check(any(part in x for x in out), f"{label}: refused ({out[:1]})")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][1], name="x1", row="A7")), "not an approved row", "a row from another session (A7)")
    tbl(lambda t: t["jobs"].append(dict(t["jobs"][1], name="x2", row="B3")), "not an approved row", "a row B3")
    tbl(lambda t: t["jobs"][1].__setitem__("perturb", "fill"), "is not row", "a perturbation that is not its row's")
    tbl(lambda t: t["jobs"][7].__setitem__("perturb", "reset"), "is not row", "an L job asking for a reset")
    tbl(lambda t: t["jobs"][0].__setitem__("write", True), "only S0 has no writer", "S0 with a writer")
    tbl(lambda t: t["jobs"][3].__setitem__("write", False), "only S0 has no writer", "a writer job without a writer")
    tbl(lambda t: t["jobs"][2].__setitem__("flags", [0, 2, 0, 0]), "flags", "a flag that is not 0 or 1")
    tbl(lambda t: t["jobs"][2].__setitem__("sa63", -1), "marker", "a marker that is not a 32-bit integer")
    tbl(lambda t: t.__setitem__("arm", "slots=0x1 entry=0 trc=8"), "arm line", "a trc in the arm line")
    tbl(lambda t: t.__setitem__("arm", "slots=0xf entry=0,1,2,3"), "arm line", "another arm line")
    tbl(lambda t: t.__setitem__("note", "kreg 0x0814=1"), "forbidden word", "a register write in the table")
    tbl(lambda t: t.__setitem__("stop_budget", 1), "stop budget", "a stop budget of 1")
    tbl(lambda t: t.__setitem__("gap_ms", 5000), "gap_ms", "another gap")
    print(f"{len(FAIL)} failed" if FAIL else "all guard checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
