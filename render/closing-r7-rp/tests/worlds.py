"""worlds.py: r7-rp's ARGV-DRIVEN fake laptop tool.  The fake tool never sees a case name: it answers from its own path (which
build it is: ~/sgxfive-test-rgn4 = t4, ~/scratch/r7r/bin/sgxfive-test-t6 = t6, ...-t7 = t7) and its argv only, as the tool and the
module would (round 4's fake answered by the kmsg marker's case name and so could not see a row's argv).  Each area's world
(tests/world_q287.py, world_q291.py, world_rd.py, world_dump.py, world_q086.py) answers its own rows (`handles(tool, argv)`,
`answer(tool, argv, tokens)`), writing the files the real tool writes and refusing a missing output directory as it does.

  a bare `tri` or `fill`  the health pair: exact unless FAKE_HEALTH_BAD
  FAKE_RULES ("ARGV-SUBSTRING|OUTCOME" lines, newline separated) override the world:  fatal (a soft lockup logged), timeout (rc 124),
            hang (a hung job logged), nodiff (rc 1, no diff line), fault3d (a 3D-side BIF fault), faultta (a TA-side fault),
            neg110 (a 3D-side fault and `recovery failed: -110`), refuse (rc 1, `sgxfive-test: render: Invalid argument`),
            nodump (the job completes but writes no depth or render dump), bigdump (the fake df runs low from the next call)

  tool PATH ARGS...    the fake tool (tests/fake_tool.sh execs this)
World: FAKE_WORLD, comma separated words; `model` (every frozen prediction holds) unless the areas' rival words are given;
the bare `tri` of s0 and of the health is world_q287's (its `t7bad`: t7 draws the default triangle wrong, the s0 gate fails).
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
AREAS = ("world_q291", "world_q287", "world_rd", "world_dump", "world_q086")   # q291 first: it takes only its own H < 16 depth twins
FAULT3D = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90100 at 0x10000016 (PD 0x30d6e000) stalls job 86, recovering"
FAULTTA = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90004 at 0x20006061 (PD 0x30d6e000) stalls job 86, recovering"


def which(path):
    b = os.path.basename(path)
    if b == "sgxfive-test-rgn4":
        return "t4"
    if b.endswith("-t6"):
        return "t6"
    if b.endswith("-t7"):
        return "t7"
    return "t?"


def toks(world):
    return set((world or "model").split(","))


def rule(a):
    line = " ".join(a)
    for r in os.environ.get("FAKE_RULES", "").split("\n"):
        if "|" in r:
            sub, what = r.rsplit("|", 1)
            if sub and sub in line:
                return what
    return None


def answer(tl, a, world):
    if a == ["fill"]:
        bad = os.environ.get("FAKE_HEALTH_BAD")
        return dict(out="job: failed\n" if bad else "job: ok\ndiff: 0 of 2048 pixels\n", err="", rc=1 if bad else 0, kmsg=[])
    if a == ["tri"] and tl == "t4" and os.environ.get("FAKE_HEALTH_BAD"):
        return dict(out="job: failed\n", err="", rc=1, kmsg=[])
    r = rule(a)
    if r == "fatal":
        return dict(out="job: ok\n", err="", rc=0, kmsg=["watchdog: BUG: soft lockup - CPU#0 stuck for 22s! [sgxfive-test:999]"])
    if r == "timeout":
        return dict(out="", err="", rc=124, kmsg=[])
    if r == "hang":
        return dict(out="job: failed: timed out\n", err="", rc=1, kmsg=["gma500 0000:00:02.0: [drm] *ERROR* sgxfive: job 86 hung"])
    if r == "nodiff":
        return dict(out="job: failed\n", err="", rc=1, kmsg=[])
    if r == "fault3d":
        return dict(out="job: failed: job faulted\n", err="", rc=1, kmsg=[FAULT3D])
    if r == "faultta":
        return dict(out="job: failed: job faulted\n", err="", rc=1, kmsg=[FAULTTA])
    if r == "neg110":
        return dict(out="job: failed: job faulted\n", err="", rc=1,
                    kmsg=[FAULT3D, "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: recovery failed: -110"])
    if r == "refuse":
        return dict(out="job: rejected (Invalid argument)\ndiff: 342 of 342 pixels\ntri: FAILED after 0 renders\n", err="", rc=1, kmsg=[])
    w = toks(world)
    for m in AREAS:
        mod = importlib.import_module(m)
        if mod.handles(tl, a):
            res = mod.answer(tl, a, w)
            if r == "nodump":
                for opt in ("--depth-dump", "--dump-render"):
                    if opt in a:
                        d = a[a.index(opt) + 1]
                        for f in os.listdir(d) if os.path.isdir(d) else []:
                            os.unlink(os.path.join(d, f))
            if r == "bigdump" and os.environ.get("FAKE_DIR"):
                with open(os.path.join(os.environ["FAKE_DIR"], "df-low"), "w") as f:
                    f.write("1\n")
            return res
    return dict(out="", err="sgxfive-test: usage (the fake knows no such command)\n", rc=2, kmsg=[])


def tool(argv):
    path, a = argv[0], argv[1:]
    res = answer(which(path), a, os.environ.get("FAKE_WORLD", "model"))
    if res.get("kmsg") and os.environ.get("KMSG"):
        with open(os.environ["KMSG"], "a") as f:
            f.write("\n".join(res["kmsg"]) + "\n")
    with open(os.environ.get("FAKE_LOG", os.devnull), "a") as f:
        f.write("%s %s\n" % (os.path.basename(path), " ".join(a)))
    sys.stdout.write(res.get("out", ""))
    sys.stderr.write(res.get("err", ""))
    return res.get("rc", 0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "tool":
        sys.exit(tool(sys.argv[2:]))
    print(__doc__)
