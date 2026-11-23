#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""fwtask.py SUB JSON: the fake of tools/fwtask/fwtask_run.py for the kit's mock (fake/sudo execs
it for `python3 .../kit/fwtask_run.py SUB JSON`, the kit's owntask_call). It answers each
subcommand with the JSON object the real runner prints, from a fake own-task state:

  arm    {blob, arm}: the blob file must exist; the task is armed (FAKE_DIR/own holds the arm
         line), the results page reset (magic 0x4e574f53); ok unless the world has ownarmbad
  run    {name, outdir, jobs}: each job {n, params, runid, timeout_ms[, ticks]} needs the task
         armed (a reset in between disarms it: the job never reports done); the task stores what the
         world's optional own_res(cmd, params, world) gives ({dword: value}), the run id echo and
         state 2. World ownstop: the first job never reports done, the runner's stop dump is
         written to OUTDIR (stopI-own_res.json, -regs.txt, -status.txt, -dmesg.txt), rc 1;
         world ownhang: the same with the tick frozen after the stop, the real runner's
         "firmware hung" stop (r36-n3). A job with ticks true records ticks, ticks_expected and
         window_ms as the real runner (0 ticks in world ownhang); a job with kick "miscinfo"
         (round 39) logs "kick miscinfo" after its run line and records k0 (cmd 1, the job's
         slot as the runner initfilled it), the kick's reply and, with ticks, ticks_from_kick
         (round 41) A job's slots are read into its record as the real runner's extra result
         slots, its sleep_ms recorded as slept {ms, ticks}; world ownstop2: the jobs after the
         first never report done (the same stop dump and rc 1). Each job is posted first as the
         real runner posts it (round 41, LC2): its slot and extra slots initfilled 0xdeadc0de,
         its params, state 0, its run id, last its cmd word; a job never done leaves that on the
         page, the stop dump and its record (cmd_after its command, as row LC's job 2 on the
         laptop). Each record keeps bif {pre, post}, [BIF_INT_STAT, BIF_FAULT] before the command
         and after the poll as the real runner's (round 42, K5): zeros, or the world's optional
         bif(index, n, world) ({pre, post}); world bifjob2: a fault after job 1 (0x000d0400,
         0x0004300f) in every later job's pre and post
  page   the results page, {"page": [1024 dwords]}
  gate   {order, outdir} optional (round 41): the fill and triangle in that order (t30-shaped
         texts; world owngatebad: the fill fails), or the texts the world's optional gate(world,
         arm) gives by the armed line ({fill, tri, pre, post}, any of them; None: the defaults),
         ok read from them as the real runner reads them; with outdir its gate-fill.txt,
         gate-tri.txt, devcd-pre.txt and devcd.txt (pre and post, else "devcd: none pending");
         the log line names a non-default order
  reset  disarm; ok

Every call is logged in FAKE_DIR/own.log ("arm LINE", "run NAME n=N runid=R", "page", "gate",
"reset"); the fake debugfs reset (fake/sudo) logs "kit reset" there and disarms too. A JSON
argument that does not parse, an unknown subcommand or key ends rc 2 (usage), as a slip in the
kit's runner must fail its mock."""
import importlib.util
import json
import os
import sys

PAGE, MAGIC, CMD, STATE, RUNID, ECHO, RESULTS = 1024, 0, 1, 2, 3, 5, 0x40
INITFILL = 0xdeadc0de          # fwtask_run.py's
KEYS = {"arm": {"blob", "arm"}, "run": {"name", "outdir", "jobs"}, "page": set(), "gate": set(),
        "reset": set()}
OPTIONAL = {"gate": {"order", "outdir"}}
JOB_KEYS = {"n", "params", "runid", "timeout_ms", "ticks", "kick", "sleep_ms", "slots"}
ORDERS = ("fill,tri", "tri,fill")
FILL_OK = ("programs asm\njob: ok\njob time: 470 us\ntarget: 64x32 hash 0xb60c6095080bd325\n"
           "diff: 0 of 2048 pixels\noutside: 0 dwords\n"
           "fill: ok, 64x32 at (0, 0), stride 256, colour 0xff336699\n")
FILL_BAD = "programs asm\njob: faulted, context lost (Input/output error)\nFAIL fill\n"
TRI_OK = ("tri: render context for targets up to 64x64\njob: ok\n"
          "target: 64x64 hash 0x99385a04ee01c585\ndiff: 0 of 4096 pixels\noutside: 0 dwords\n"
          "tri: 1 renders ok\n")
KICKS = ("miscinfo",)
BIF_FAULTED = [0x000D0400, 0x0004300F]    # world bifjob2's words (B11's fill fault, E1172)


def fake(name):
    return os.path.join(os.environ["FAKE_DIR"], name)


def log(line):
    with open(fake("own.log"), "a") as f:
        f.write(line + "\n")


def world():
    return set((os.environ.get("FAKE_WORLD") or "model").split(","))


def world_mod():
    p = os.environ.get("KIT_WORLD")
    if not p:
        return None
    spec = importlib.util.spec_from_file_location("world", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def page():
    try:
        with open(fake("own_res.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return [0] * PAGE


def save(p):
    with open(fake("own_res.json"), "w") as f:
        json.dump(p, f)


def armed():
    return os.path.exists(fake("own"))


def emit(obj):
    print(json.dumps(obj, sort_keys=True))


def usage(why):
    sys.stderr.write(f"usage: fwtask_run.py SUB JSON (fake): {why}\n")
    return 2


def alive():
    return {"advancing": True, "serv_moves": True, "ticks": [1, 2, 3], "serv_event": [1, 2, 3]}


def health():
    return {"event_status2": 0x400, "bif_int_stat": 0, "bif_fault": 0, "faults_status": 0,
            "ok": True}


def arm(a):
    if not os.path.isfile(a["blob"]):
        sys.stderr.write(f"FileNotFoundError: No such file or directory: {a['blob']!r}\n")
        return 1
    log(f"arm {a['arm']}")
    with open(fake("own"), "w") as f:
        f.write(a["arm"] + "\n")
    p = [0] * PAGE
    p[MAGIC] = 0x4e574f53
    save(p)
    emit({"own_arm": "on " + a["arm"], "alive": alive(), "rate_hz": 1000.0, "misc": {},
          "health": health(), "log_bad": [], "log": [], "magic": p[MAGIC],
          "ok": "ownarmbad" not in world()})
    return 0


def run(a):
    w, mod = world(), world_mod()
    records, stop = [], None
    for i, j in enumerate(a["jobs"]):
        if set(j) - JOB_KEYS or not isinstance(j.get("n"), int):
            return usage(f"job {j!r}")
        if j.get("kick", "miscinfo") not in KICKS:
            return usage(f"kick {j['kick']!r}")
        log(f"run {a['name']} n={j['n']} runid={j.get('runid', i + 1)}")
        p = page()
        base = RESULTS + 4 * j["n"]
        k0 = {"tick": 1000, "cmd": j["n"], "slot": [0xdeadc0de] * 4, "ms": 0.5}  # the initfill
        if "kick" in j:
            log(f"kick {j['kick']}")
        # posted as fwtask_run.py's one_cmd posts it, before its poll (round 41, LC2): the slot
        # and extra slots initfilled, the params, state 0, the run id, last the cmd word
        for s in (j["n"], *j.get("slots", ())):
            p[RESULTS + 4 * s:RESULTS + 4 * s + 4] = [INITFILL] * 4
        for k, v in j.get("params", {}).items():
            vals = v if isinstance(v, list) else [v]
            p[int(k):int(k) + len(vals)] = vals
        p[STATE], p[RUNID], p[CMD] = 0, j.get("runid", i + 1), j["n"]
        save(p)
        done = armed() and not w & {"ownstop", "ownhang"} and not ("ownstop2" in w and i > 0)
        if done:
            got = getattr(mod, "own_res", None)
            for k, v in ((got(j["n"], j.get("params", {}), w) if got else None) or {}).items():
                p[int(k)] = v
            p[CMD], p[STATE], p[RUNID], p[ECHO] = 0, 2, j.get("runid", i + 1), j.get("runid", i + 1)
            save(p)
        word = list(BIF_FAULTED) if "bifjob2" in w and i > 0 else [0, 0]
        bif = (getattr(mod, "bif", None) or (lambda *x: None))(i, j["n"], w) or \
            {"pre": word, "post": list(word)}
        records.append({"done": done, "ms": 1.0 if done else float(j.get("timeout_ms", 100)),
                        "slot": p[base:base + 4], "echo": p[ECHO], "cmd_after": p[CMD],
                        "overlap": 0, "bif": bif, "job": j, "H": {}, "restored": True})
        if j.get("slots"):          # the real runner's extra result slots, read after the job
            records[-1]["slots"] = {str(x): p[RESULTS + 4 * x:RESULTS + 4 * x + 4]
                                    for x in j["slots"]}
        if j.get("sleep_ms"):
            records[-1]["slept"] = {"ms": j["sleep_ms"], "ticks": j["sleep_ms"]}
        if j.get("ticks"):          # the real runner's HostCtl dword 12 count over the window
            ms = records[-1]["ms"] + 30.0
            records[-1].update(ticks=0 if "ownhang" in w else int(ms), ticks_expected=ms * 0.997,
                               window_ms=ms)
        if "kick" in j:
            reply = {"ms": 2.0, "lines": 1, "text": "fake miscinfo\n"} if done else \
                {"error": "[Errno 110] Connection timed out"}
            records[-1].update(k0=k0, kick={"kind": j["kick"], "reply": reply})
            if j.get("ticks"):
                records[-1]["ticks_from_kick"] = max(records[-1]["ticks"] - 1, 0)
        if not done:
            stop = f"no done within {j.get('timeout_ms', 100)} ms (job {i})"
            os.makedirs(a["outdir"], exist_ok=True)
            for n, body in (("regs.txt", "sgxfive regs 1\n"), ("status.txt", "bif_faults 0\n"),
                            ("own_res.json", json.dumps(p)), ("dmesg.txt", "")):
                with open(os.path.join(a["outdir"], f"stop{i}-{n}"), "w") as f:
                    f.write(body)
            break
    out = {"name": a["name"], "records": records, "stop": stop, "n_jobs": len(a["jobs"]),
           "ran": len(records)}
    if stop:
        hung = "ownhang" in w
        out["alive_at_stop"] = {"ticks": [7, 7, 7] if hung else [7, 8, 9], "advancing": not hung}
        if hung:
            out["stop"] = stop + "; firmware hung: the tick stopped"
    else:
        out.update(alive=alive(), health=health(), log_bad=[], kreg_after={})
    emit(out)
    return 1 if stop else 0


def gate(a):
    order = a.get("order", ORDERS[0])
    if order not in ORDERS:
        return usage(f"gate order {order!r}")
    log(f"gate {os.environ.get('FWTASK_HEALTH_TOOL', '-')}"
        + (f" {order}" if order != ORDERS[0] else ""))
    w, mod = world(), world_mod()
    arm_line = open(fake("own")).read().strip() if armed() else ""
    got = (getattr(mod, "gate", None) or (lambda w_, a_: None))(w, arm_line) or {}
    texts = {"fill": got.get("fill", FILL_BAD if "owngatebad" in w else FILL_OK),
             "tri": got.get("tri", TRI_OK)}
    fill = [ln for ln in texts["fill"].splitlines() if ln.startswith("diff") or "FAIL" in ln][:3]
    tri = [ln for ln in texts["tri"].splitlines()
           if ln.startswith(("diff", "tri 64x64")) or "FAIL" in ln][:4]
    out = {"order": order, "fill": "\n".join(fill), "tri": "\n".join(tri)}
    out["ok"] = ("diff: 0 of 2048" in out["fill"] and "diff: 0 of 4096" in out["tri"]
                 and "FAIL" not in out["fill"] + out["tri"])
    if "outdir" in a:
        os.makedirs(a["outdir"], exist_ok=True)
        for when, f in (("pre", "devcd-pre.txt"), ("post", "devcd.txt")):
            text = got.get(when) or "devcd: none pending\n"
            with open(os.path.join(a["outdir"], f), "w") as fh:
                fh.write(text)
            out["devcd_pre" if when == "pre" else "devcd"] = \
                [] if text.startswith("devcd: none") else ["devcd0"]
        for name in order.split(","):
            with open(os.path.join(a["outdir"], f"gate-{name}.txt"), "w") as fh:
                fh.write(texts[name])
    emit(out)
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] not in KEYS:
        return usage(f"subcommand {argv[1:2]}")
    try:
        a = json.loads(argv[2]) if len(argv) > 2 else {}
    except ValueError as e:
        return usage(f"JSON {argv[2]!r}: {e}")
    sub = argv[1]
    opt = OPTIONAL.get(sub, set())
    if not isinstance(a, dict) or set(a) - KEYS[sub] - opt or not KEYS[sub] <= set(a):
        return usage(f"{sub} takes {sorted(KEYS[sub] | opt)}, not {a!r}")
    if sub == "arm":
        return arm(a)
    if sub == "run":
        return run(a)
    if sub == "gate":
        return gate(a)
    log(sub)
    if sub == "page":
        emit({"page": page()})
    else:
        if os.path.exists(fake("own")):
            os.remove(fake("own"))
        emit({"own_arm": "off", "alive": alive(), "rate_hz": 1000.0, "misc": {},
              "health": health(), "log": [], "ok": True})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
