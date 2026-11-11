#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_gen_r4b.py: the table and the predictions of R4b against their sources.  The blob, its source and blobs.json are R3k-events'
frozen files (the published freeze's hashes); the E817 records the tests use are the published out/f files byte for byte; every
frozen control value holds on E817's own kept job of the same shape, and H-REP's values are E817's fcf values."""
import hashlib
import json
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R4 = HERE.parent
sys.path.insert(0, str(R4 / "gen"))
sys.path.insert(0, str(R4 / "score"))
import gen_r4b as G  # noqa: E402
import r4blayout as L  # noqa: E402
import scorelib as C  # noqa: E402

PUB = pathlib.Path.home() / "src/resgx545-data/edm/closing-r3k-events"
FAIL = []


def ok(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    frozen = dict(reversed(ln.split("  ", 1)) for ln in (PUB / "FROZEN.sha256").read_text().splitlines())
    for f in ("asm/ring_exit.s", "bins/ring_exit.blob", "bins/blobs.json", "gen/r3layout.py", "score/scorelib.py", "run/r3common.py",
              "run/health_remote.sh", "run/guard_py.py"):
        ok(frozen.get(f) == sha(R4 / f), f"{f} is R3k-events' frozen file")
    for p in sorted((HERE / "fixtures" / "e817f").iterdir()):
        ok(sha(p) == sha(PUB / "out" / "f" / p.name), f"fixture {p.name} is the published out/f file")
    ok(json.loads((R4 / "tables" / "fr.json").read_text()) == json.loads(json.dumps(G.table())), "tables/fr.json is the generator's")
    rows = [ln.split("\t") for ln in (R4 / "predictions" / "fr.tsv").read_text().splitlines()[1:]]
    ok([tuple(r) for r in rows] == G.preds(), "predictions/fr.tsv is the generator's")
    t = G.table()
    names = [j["name"] for j in t["jobs"]]
    block = ["e0", "fc4", "fc4-r2", "fb", "fb-r2"]
    want = []
    for b in (1, 2, 3):
        want += [f"b{b}{x}" for x in block] + [f"fcf{b}", f"fk{b}"]
    ok(names == want, f"the job order: three blocks of E817's sequence, each fcfN then fkN ({names})")
    ok([j["name"] for j in t["jobs"] if j["may_stop"]] == ["fcf1", "fcf2", "fcf3"], "only the FCF replicates may stop")
    ok(t["stop_budget"] == 3 and t["per_job_reset"] is False, "budget 3 (the replicates), no reset between the jobs of a block")
    ok([j["name"] for j in t["jobs"] if j.get("block_start")] == ["b1e0", "b2e0", "b3e0"], "a reset and an arm only at each block start")
    ok([j.get("block") for j in t["jobs"]] == [b for b in (1, 2, 3) for _ in range(7)], "each job names its block")
    ok(all(j["act"] == L.ACT_CFI for j in t["jobs"] if j["row"].startswith("FCF")), "every FCF replicate is E817's ACT 3")
    ok(all(j["act"] == L.ACT_PHAS for j in t["jobs"] if j["row"].startswith("FK")), "fkN is E817's fph pass (ACT 4)")
    # each block reproduces E817's jobs from the arm to fcf, act by act, and fkN its first job after the re-arm
    tab = json.loads((PUB / "tables" / "f.json").read_text())
    E = {j["name"]: j for j in tab["jobs"]}
    st = json.loads((HERE / "fixtures" / "e817f" / "stage.json").read_text())
    seq = st["jobs_run"][:st["jobs_run"].index("fcf") + 1]
    ok(seq == ["e0", "fc4", "fc4-r2", "fb", "fb-r2", "fcf"], f"E817 from its arm to fcf: {seq}")
    ok(st["jobs_run"].index("fph") > st["jobs_run"].index("fcf") and st["classes"]["fcf-r2"] == "skipped",
       "E817's fph ran after fcf's stop and the re-arm (not between the arm and fcf)")
    for b in (1, 2, 3):
        J = {j["name"]: j for j in t["jobs"] if j["block"] == b}
        got = [(J[f"b{b}{x}"]["kind"], J[f"b{b}{x}"]["act"], J[f"b{b}{x}"]["count"]) for x in block] + \
              [(J[f"fcf{b}"]["kind"], J[f"fcf{b}"]["act"], J[f"fcf{b}"]["count"])]
        ok(got == [(E[x]["kind"], E[x]["act"], E[x]["count"]) for x in seq], f"block {b}: the kinds, acts and counts of E817's sequence")
        ok((J[f"fk{b}"]["act"], J[f"fk{b}"]["count"]) == (E["fph"]["act"], E["fph"]["count"]), f"fk{b} is E817's fph job")
        ok(all(J[n]["pre_ms"] == E["fcf"]["pre_ms"] and J[n]["open_ms"] == E["fcf"]["open_ms"] for n in J), f"block {b}: E817's times")
    ok({j["name"]: j.get("run_if") for j in t["jobs"] if j["row"].startswith("FCF")} ==
       {"fcf1": "all_kept:B1FB:2", "fcf2": "all_kept:B2FB:2", "fcf3": "all_kept:B3FB:2"}, "fcfN runs only after its block's two FB passes kept")
    ok(all(j.get("run_if") == f"all_kept:FK{j['block'] - 1}:1" for j in t["jobs"] if j["block"] > 1 and j["row"].endswith(("E0", "FC4"))),
       "a block after the first runs only if the previous fkN kept the tick")
    # E817's kept values against the frozen ones
    fix = HERE / "fixtures" / "e817f"
    tab = json.loads((PUB / "tables" / "f.json").read_text())
    E = {j["name"]: j for j in tab["jobs"]}
    for src in ("fc4", "fc4-r2", "fb", "fb-r2", "fph", "fph-r2"):     # every kept control shape against its frozen window
        rec = json.loads((fix / f"{src}.json").read_text())
        r = C.ring(rec["page"])
        ev = [e for e in C.from_stamp(C.merged(r), rec["window_stamp"]) if e[0] == 0]
        acted = [e for e in ev if e[1] in (L.SKIP_FLAG, L.TAIL_FLAG)]
        nxt = [C.rel(e[5], acted[-1][5]) for e in ev if C.rel(e[5], acted[-1][5]) > 0][0]
        ok(L.E817_KEPT_GAP[0] <= nxt <= L.E817_KEPT_GAP[1] and rec["page"][L.ACT_SEEN] == E[src]["act"],
           f"E817 {src}: next entry +{nxt} inside the frozen window, ACT_SEEN {rec['page'][L.ACT_SEEN]}")
    rec = json.loads((fix / "fcf.json").read_text())
    sg = C.rec_sig(rec)
    mk = C.marks_from_samples(rec["sig"]["samples"])
    e = L.E817_FCF
    ok(sg["matches_e537"] and sg["values"]["clkstat"] == e["clkstat"] and sg["values"]["event_status"] == e["event_status"]
       and mk["rmw"] == e["read_minus_write"] and mk["hc14"] == e["dword14"] and rec["p3"]["answered"] is False
       and rec["page"][L.ACT_SEEN] == e["act_seen"], "E817 fcf: the signature H-REP freezes")
    st = json.loads((fix / "stage.json").read_text())
    ok(st["classes"]["fcf"] == "stop" and st["classes"]["fcf-r2"] == "skipped" and st["jobs_run"].index("fcf") == 5,
       "E817: FCF ran once (job fcf, the sixth after the arm), fcf-r2 was not run")
    rec0 = json.loads((fix / "e0.json").read_text())
    n0 = len([x for x in C.from_stamp(C.merged(C.ring(rec0["page"])), rec0["window_stamp"]) if x[0] == 0])
    ok(L.E817_E0_ENTRIES[0] <= n0 <= L.E817_E0_ENTRIES[1], f"E817 e0: {n0} entries inside the frozen window")
    print(f"{len(FAIL)} FAILED" if FAIL else "all passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
