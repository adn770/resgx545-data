# SPDX-License-Identifier: MIT
"""worlds_r4b.py: stage directories for the scorer tests, built from E817's kept records (tests/fixtures/e817f, copies of
resgx545-data edm/closing-r3k-events out/f).  Each R4b job takes the record of the E817 job of its shape: block N's bNe0, bNfc4,
bNfc4-r2, bNfb, bNfb-r2 take e0, fc4, fc4-r2, fb, fb-r2; fcfN takes `fcf` (the stop) or `fph` relabelled as an ACT 3 pass that
kept the tick; fkN takes `fph` (E817's first job after the re-arm that followed fcf's stop).  Arm records: bNe0.arm.json (the block's
arm, from E817's arm.json) and rearm-fcfN.json after a stopped fcfN (from E817's rearm1.json).

    make(dst, fcf=("stop", "stop", "stop"), **edits) -> the directory
"""
import copy
import json
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE / "fixtures" / "e817f"
BLOCK = ["e0", "fc4", "fc4-r2", "fb", "fb-r2"]
ORDER = [n for b in (1, 2, 3) for n in [f"b{b}{x}" for x in BLOCK] + [f"fcf{b}", f"fk{b}"]]
RUN = "1800000000-4242"
ACT_SEEN = 13


def src_of(n):
    if n.startswith("fk"):
        return "fph"
    if n.startswith("fcf"):
        return "fcf"
    return n[2:]


def rec_of(src):
    return json.loads((FIX / f"{src}.json").read_text())


def kept_fcf():
    """A kept ACT 3 pass: E817's fph record (kept, flag 3) with ACT_SEEN 3 and the job's act 3."""
    r = rec_of("fph")
    r["page"][ACT_SEEN] = 3
    r["page2"][ACT_SEEN] = 3
    r["job"]["act"] = 3
    return r


def make(dst, fcf=("stop", "stop", "stop"), drop=(), classes=None, arm_exit=None, sig=None, p3=None, marks=None, skip=()):
    """fcf: per replicate "stop" (E817's fcf), "kept" (kept_fcf) or "void" (class void).  drop: jobs with no record.  skip: jobs
    recorded as skipped.  classes: {job: class}.  arm_exit: {arm file stem: exit index}.  sig: {job: {"0x8": v, ...}} register
    overrides in both signature samples.  p3: {job: answered}.  marks: {job: (ccb, hc14)}."""
    dst = pathlib.Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    table = json.loads((HERE.parent / "tables" / "fr.json").read_text())
    jobs = {j["name"]: j for j in table["jobs"]}
    run, cls = [], {}
    arm = json.loads((FIX / "arm.json").read_text())
    rearm = json.loads((FIX / "rearm1.json").read_text())

    def put_arm(stem, a):
        a = copy.deepcopy(a)
        if arm_exit and stem in arm_exit:
            a["exit_index"] = arm_exit[stem]
        (dst / f"{stem}.json").write_text(json.dumps(a))
    for n in ORDER:
        j = jobs[n]
        if n in drop:
            continue
        if n in skip:
            rec = {"name": n, "set": j["set"], "op": "act", "row": j["row"], "job": j, "class": "skipped", "rc": None,
                   "note": "skipped by the test", "run": RUN}
        else:
            if j.get("block_start"):
                put_arm(f"{n}.arm", arm)
            if n.startswith("fcf"):
                kind = fcf[int(n[-1]) - 1]
                rec = rec_of("fcf") if kind in ("stop", "void") else kept_fcf()
                if kind == "void":
                    rec["class"] = "void"
            else:
                rec = rec_of(src_of(n))
            rec = copy.deepcopy(rec)
            rec.update({"name": n, "set": j["set"], "row": j["row"], "job": j, "run": RUN})
            if classes and n in classes:
                rec["class"] = classes[n]
            if sig and n in sig:
                for sm in rec["sig"]["samples"]:
                    sm["regs"].update(sig[n])
            if p3 and n in p3:
                rec["p3"]["answered"] = p3[n]
            if marks and n in marks:
                ccb, h14 = marks[n]
                if rec.get("sig"):
                    for sm in rec["sig"]["samples"]:
                        sm["ccb"], sm["hc14"] = ccb, h14
                else:
                    rec["marks_post"].update({"ccb": ccb, "hc14": h14})
            if rec["class"] == "stop" and n.startswith("fcf"):
                put_arm(f"rearm-{n}", rearm)
        (dst / f"{n}.json").write_text(json.dumps(rec))
        run.append(n)
        cls[n] = rec["class"]
    (dst / "stage.json").write_text(json.dumps({"stage": "fr", "run": RUN, "exit": 0, "why": "", "jobs_run": run,
                                                "stops": sum(1 for c in cls.values() if c == "stop"), "classes": cls}))
    return dst
