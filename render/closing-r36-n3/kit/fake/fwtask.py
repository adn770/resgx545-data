#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""fwtask.py SUB JSON: the fake of tools/fwtask/fwtask_run.py for the kit's mock (fake/sudo execs
it for `python3 .../kit/fwtask_run.py SUB JSON`, the kit's owntask_call). It answers each
subcommand with the JSON object the real runner prints, from a fake own-task state:

  arm    {blob, arm}: the blob file must exist; the task is armed (FAKE_DIR/own holds the arm
         line), the results page reset (magic 0x4e574f53); ok unless the world has ownarmbad
  run    {name, outdir, jobs}: each job {n, params, runid, timeout_ms} needs the task armed (a
         reset in between disarms it: the job never reports done); the task stores what the
         world's optional own_res(cmd, params, world) gives ({dword: value}), the run id echo and
         state 2. World ownstop: the first job never reports done, the runner's stop dump is
         written to OUTDIR (stopI-own_res.json, -regs.txt, -status.txt, -dmesg.txt), rc 1
  page   the results page, {"page": [1024 dwords]}
  gate   the fill and triangle, ok unless the world has owngatebad
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
KEYS = {"arm": {"blob", "arm"}, "run": {"name", "outdir", "jobs"}, "page": set(), "gate": set(),
        "reset": set()}
JOB_KEYS = {"n", "params", "runid", "timeout_ms"}


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
        log(f"run {a['name']} n={j['n']} runid={j.get('runid', i + 1)}")
        p = page()
        done = armed() and "ownstop" not in w
        if done:
            for k, v in j.get("params", {}).items():
                vals = v if isinstance(v, list) else [v]
                p[int(k):int(k) + len(vals)] = vals
            got = getattr(mod, "own_res", None)
            for k, v in ((got(j["n"], j.get("params", {}), w) if got else None) or {}).items():
                p[int(k)] = v
            p[CMD], p[STATE], p[RUNID], p[ECHO] = 0, 2, j.get("runid", i + 1), j.get("runid", i + 1)
            save(p)
        base = RESULTS + 4 * j["n"]
        records.append({"done": done, "ms": 1.0 if done else float(j.get("timeout_ms", 100)),
                        "slot": p[base:base + 4], "echo": p[ECHO], "cmd_after": p[CMD],
                        "overlap": 0, "job": j, "H": {}, "restored": True})
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
    if not stop:
        out.update(alive=alive(), health=health(), log_bad=[], kreg_after={})
    emit(out)
    return 1 if stop else 0


def main(argv):
    if len(argv) < 2 or argv[1] not in KEYS:
        return usage(f"subcommand {argv[1:2]}")
    try:
        a = json.loads(argv[2]) if len(argv) > 2 else {}
    except ValueError as e:
        return usage(f"JSON {argv[2]!r}: {e}")
    sub = argv[1]
    if not isinstance(a, dict) or set(a) - KEYS[sub] or not KEYS[sub] <= set(a):
        return usage(f"{sub} takes {sorted(KEYS[sub])}, not {a!r}")
    if sub == "arm":
        return arm(a)
    if sub == "run":
        return run(a)
    log(f"gate {os.environ.get('FWTASK_HEALTH_TOOL', '-')}" if sub == "gate" else sub)
    if sub == "page":
        emit({"page": page()})
    elif sub == "gate":
        ok = "owngatebad" not in world()
        emit({"fill": "diff: 0 of 2048", "tri": "diff: %d of 4096" % (0 if ok else 7), "ok": ok})
    else:
        if os.path.exists(fake("own")):
            os.remove(fake("own"))
        emit({"own_arm": "off", "alive": alive(), "rate_hz": 1000.0, "misc": {},
              "health": health(), "log": [], "ok": True})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
