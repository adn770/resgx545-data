"""worlds.py: r5-render4x's ARGV-DRIVEN worlds (closing5/render4x/exp-render4x-r5.md 2.1 dry run 2, 3.6).  Round 4's fake tool answered
by the case NAME of the last kmsg marker and wrote every dump as tri.*, so a row's argv never reached a test (o2's default triangle and
t's probe dump names slipped through).  Here the fake tool never sees a name: it answers from its argv and the fake debugfs knobs
(render_pb_pages, render_rgn_arrays, hold_recovery) only, as the module and the tool would:

  - a TE_AA word with bits 31:30 on a context made without --aa4 is refused unless render_rgn_arrays forces a count (fork a2788bd8);
  - the scene's page need: the kept TWIN of the argv (gen/twins.py: real kept outputs and dumps are replayed) or, for a scene never
    kept, the model (U4 for the 4x full triangle, u1_full for the 1x full triangle); it overflows iff P - 0x22 is below the need;
  - a 4x full triangle faults (BIF_INT_STAT 0x90100, BIF_FAULT 0x10000011) iff the world's Q292 rule says so for the argv's target and
    maximum (gen/rules.py; a threshold rule gets the world's threshold); a completed one writes a TA-data dump of the maximum's layout
    with region headers on the doubled-grid rule;
  - a probe writes DIR/PROG.{param,tadata}.bin (PROG the program's label), as sgxfive-test.c dump_render(f->name) does; with --cmd
    1=0x40000000 or 1=0x80000000 the world inserts a dword before the object's format word (zero in the model world).

One answer function, two uses:
  kept(outdir, stage, world)   a kept stage directory as the runner writes it (cases.tsv, NAME.txt.gz, NAME.dmesg.gz, the dumps under
                               the names the tool gives them, the registers), for the scorer tests
  tool ARGS...                 the fake sgxfive-test-rgn4 of tests/run_mock.sh
"""
import gzip
import os
import re
import shlex
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import twins as TW  # noqa: E402

STAGES = ["s0", "t", "o", "m", "l", "x", "d"]
FAULT_LINE = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x%x at 0x%08x (PD 0x2d75000) stalls job 86, recovering"
HELD_LINE = "gma500 0000:00:02.0: [drm] sgxfive: job 86 hung, recovery held (debugfs hold_recovery)"
RESET_LINES = ["gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0x0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/0x480",
               "gma500 0000:00:02.0: [drm] SGX reset: after the fault clear BIF_FAULT 0x0 BIF_INT_STAT 0x80000"]
THRESHOLD = {"K-TPM": 160, "K-P": 250, "K-AREA": 1000000}     # a threshold rule's world: one threshold inside its interval


# ---- worlds ------------------------------------------------------------------------------------------------------------------------
def world_rule(world):
    return world[5:] if world.startswith("rule:") else "TPC-d-rgn"


def q292_fault(world, w, h, mw, mh):
    r = world_rule(world)
    if world == "m-split" and (w, h) == (1280, 1024) and (mw, mh) == (1280, 1040):
        return True
    if r in THRESHOLD:
        return R.metric(r, w, h) > THRESHOLD[r]
    return R.fault(r, w, h, mw, mh)


WORLDS = ["model"] + ["rule:" + r for r in R.RULES] + ["o-fault4", "o-ctl", "t-field", "t-pos", "t-draw", "s0-miss", "m-split",
                                                       "d-complete", "d-short"]


# ---- the tool's output -------------------------------------------------------------------------------------------------------------
def parse(argv):
    a = {"verb": argv[0], "w": 64, "h": 64, "mw": None, "mh": None, "full": "--tri-full" in argv, "aa4": "--aa4" in argv,
         "te": 0x20000000, "cmd": None, "dump": None, "n": 1, "prog": None}
    for i, x in enumerate(argv):
        nx = argv[i + 1] if i + 1 < len(argv) else None
        if x == "--width":
            a["w"] = int(nx)
        elif x == "--height":
            a["h"] = int(nx)
        elif x == "--max-width":
            a["mw"] = int(nx)
        elif x == "--max-height":
            a["mh"] = int(nx)
        elif x == "--poke" and nx.startswith("cmd:1="):
            a["te"] = int(nx[6:], 16)
        elif x == "--cmd" and nx.startswith("1="):
            a["cmd"] = int(nx[2:], 16)
        elif x == "--dump-render":
            a["dump"] = nx
        elif x == "-n":
            a["n"] = int(nx)
    a["mw"] = a["mw"] or a["w"]
    a["mh"] = a["mh"] or a["h"]
    if a["verb"] == "probe":
        a["prog"] = os.path.basename(argv[-1])[:-4]
    return a


def tri_text(a, hashv, state="ok", tri=None, overflowed=False):
    w, h, mw, mh = a["w"], a["h"], a["mw"], a["mh"]
    n = w * h
    o = ["tri: render context for targets up to %dx%d" % (mw, mh)]
    if a["aa4"]:
        o.append("tri: render context made for 4x targets (DRM_SGXFIVE_CTX_RENDER_AA_4X)")
    if a["full"]:
        o.append("tri: triangle (0,0) (%d,0) (0,%d), depth 0.5 0.5 0.5" % (3 * w, 3 * h))
    if state == "fault":
        return o + ["job: failed: job faulted, context lost (Input/output error)", "target: %dx%d hash 0x00ed1e2eb204fb25" % (w, h),
                    "diff: %d of %d pixels, first (0, 0) 0xdeadbeef expected 0xff00ff00" % (n, n), "outside: 0 dwords", "layout: fb 0x3e001000",
                    "sgxfive-test: render: job faulted, context lost (Input/output error)", "tri: FAILED after 0 renders"]
    tri = n if tri is None else tri
    o += ["job: ok", "target: %dx%d hash %s" % (w, h, hashv)]
    if overflowed:
        return o + ["diff: %d of %d pixels, first (0, 0) 0xdeadbeef expected 0xff00ff00" % (n, n), "outside: 0 dwords", "layout: fb 0x3e001000",
                    "tri %dx%d #1: overflowed, 0 triangle, 0 background, %d other; wrong %d inside, 0 outside, 0 at edges; 0 if flipped; guard 0" % (w, h, n, n - 1),
                    "tri: 0 of 1 renders ok, 1 overflowed"]
    return o + ["diff: 0 of %d pixels" % n, "outside: 0 dwords", "layout: fb 0x3e001000",
                "tri %dx%d #1: %d triangle, %d background, 0 other; wrong 0 inside, 0 outside, 0 at edges; 0 if flipped; guard 0" % (w, h, tri, n - tri),
                "tri: 1 renders ok"]


def scene_param(used, pages=0x464):
    b = bytearray(pages * 4096)
    for i in range(min(used, pages)):
        b[i * 4096: i * 4096 + 8] = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    for i in (0x422, 0x423, 0x463):
        if i < pages:
            b[i * 4096: i * 4096 + 8] = b"\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11"
    return bytes(b)


def tadata_4x(w, h, mw, mh, zero_below=None):
    """A TA-data dump of the maximum's layout whose region headers follow the doubled-grid rule (the inverse of rlib.headers); with
    zero_below, the headers from the base up to that offset are zero (H-TPC's reading of a faulting job)."""
    size = M.tadata_4x(mw, mh)
    b = bytearray(size)
    tx, ty, n, mx, my, _ = L._lay(w, h)
    base = L._lay(mw, mh)[5]
    i = 0
    for col in range(n):
        for row in range(n):
            mt = col * n + row
            for by in range(2 * my // 4):
                for bx in range(2 * mx // 4):
                    for yy in range(4):
                        for xx in range(4):
                            x, y = col * 2 * mx + bx * 4 + xx, row * 2 * my + by * 4 + yy
                            inside = x < 2 * tx and y < 2 * ty
                            o = base + 12 * i
                            i += 1
                            if zero_below is not None and o < zero_below:
                                continue
                            w0 = (x << 16) | (mt << 12) | y | (0 if inside else 1 << 25)
                            struct.pack_into("<3I", b, o, w0, (0x1000 + 0x40 * i) if inside else 0, 0)
    return bytes(b)


_TB = None


def _nodump(tokens):
    out, skip = [], False
    for x in tokens:
        if skip:
            skip = False
            continue
        if x == "--dump-render":
            skip = True
            continue
        out.append(x)
    return out


def twin_of(args, knobs=""):
    """The kept twin of an argv: (raw output, param, tadata) of the twin row whose argv is the same token for token (the dump directory
    aside) if one is, else the first."""
    global _TB
    if _TB is None:
        _TB = {}
        for src, name, kn, a, cls, p, o in TW.kept_rows():
            if cls == "ok" and not TW.overflowed(o):
                _TB.setdefault(TW.key(a, kn), []).append((a, p, o))
    tw = _TB.get(TW.key(args, knobs), [])
    if not tw:
        return None
    me = _nodump(TW.tokens(args))
    exact = [t for t in tw if _nodump(TW.tokens(t[0])) == me]
    a, p, o = (exact or tw)[0]
    return L.read_text(o), L.read_bytes(p), L.read_bytes(p.replace(".param.bin.gz", ".tadata.bin.gz"))


def result(**k):
    r = dict(out="", rc=0, files={}, kmsg=[], latch=None, held_param=None, held_tadata=None)
    r.update(k)
    return r


def fault_result(a, held):
    out = "\n".join(tri_text(a, "0x0", state="fault")) + "\n"
    kmsg = [FAULT_LINE % (0x90100, 0x10000011)] + ([HELD_LINE] if held else RESET_LINES)
    return result(out=out, rc=1, kmsg=kmsg, latch=(0x100, 0x10000011) if held else None)


def answer(argv, pb=0x422, rgn=0, hold="N", world="model"):
    """The fake tool's answer to argv on the fake laptop: {out, rc, files (dump name -> bytes), kmsg, latch, held dumps}."""
    args = " ".join(shlex.quote(x) if " " in x else x for x in argv)
    a = parse(argv)
    dump = {}
    if a["verb"] == "fill":
        return result(out="diff: 0 of 2048 pixels\n")
    if a["verb"] == "tri" and len(argv) == 1:
        return result(out="tri: render context for targets up to 64x64\njob: ok\ndiff: 0 of 4096 pixels\ntri: 1 renders ok\n")
    if a["verb"] == "probe":
        return probe_answer(argv, a, rgn, world)
    te_bad = a["te"] & 0xC0000000 and not a["aa4"] and rgn == 0
    if te_bad:
        return result(out="tri: render context for targets up to %dx%d\njob: rejected (Invalid argument)\ntri: FAILED after 0 renders\n" % (a["mw"], a["mh"]), rc=1)
    # the t rows: E827's rg-pb record (a TE_AA 0x40 / 0x80 poke)
    if a["te"] in (0x40000000, 0x80000000):
        e40 = L.read_text(L.REG + "/pb-e40-m2-64a.txt.gz")
        if a["aa4"]:
            e40 = e40.replace("tri: triangle", "tri: render context made for 4x targets (DRM_SGXFIVE_CTX_RENDER_AA_4X)\ntri: triangle", 1)
        par = L.read_bytes(L.REG + "/pb-e40-m2-64a.tri.param.bin.gz")
        if world == "t-draw" and a["aa4"] and a["te"] == 0x40000000:
            return result(out="\n".join(tri_text(a, "0xd0530839d87ea325")) + "\n", files={"tri": (par, bytes(24576))})
        return result(out=e40, rc=1, files={"tri": (par, L.read_bytes(L.REG + "/pb-e40-m2-64a.tri.tadata.bin.gz"))})
    four = a["aa4"] and a["te"] == 0xE0000000 and a["full"]
    usable = M.usable(pb)
    tw = twin_of(args, "")
    if four:
        need = R.u4(a["w"], a["h"])
        if q292_fault(world, a["w"], a["h"], a["mw"], a["mh"]) and not (world == "d-complete" and hold == "Y"):
            r = fault_result(a, hold == "Y")
            if hold == "Y":
                if world == "d-short":
                    r["held_param"], r["held_tadata"] = b"cat: render_param: No such device or address\n" + b"x" * 16, b"cat: render_tadata: No such device or address\n" + b"x" * 16
                else:
                    v = world_rule(world).split("-")[1] if world_rule(world).startswith("TPC") else "d"
                    r["held_param"] = scene_param(need)
                    r["held_tadata"] = tadata_4x(a["w"], a["h"], a["mw"], a["mh"], zero_below=R.extent(R.lay(a["w"], a["h"]), v))
            return r
    elif a["full"]:
        need = M.u1_full(a["w"], a["h"])
    else:
        need = None
    if tw is not None:
        out, par, ta = tw
        need = TW.scene_pages(par)
        if world == "o-ctl" and not a["full"] and pb == 0x34:
            usable = need          # the control that can fail: o2 completes
        if usable < need:
            if four and world == "o-fault4":
                return fault_result(a, hold == "Y")
            return result(out="\n".join(tri_text(a, "0x1234000000000325", overflowed=True)) + "\n", files={"tri": (scene_param(min(need, usable)), ta)})
        if world == "s0-miss" and four and a["w"] == 288:
            out = out.replace("0x4a61860dcb4ab325", "0x4a61860dcb4ab326")
        return result(out=out, rc=1 if "diff: 0 of" not in out else 0, files={"tri": (par, ta)})
    if need is None:
        raise SystemExit("worlds: no twin and no model for %s" % args)
    if usable < need:
        if four and world == "o-fault4":
            return fault_result(a, hold == "Y")
        return result(out="\n".join(tri_text(a, "0x1234000000000325", overflowed=True)) + "\n", files={"tri": (scene_param(min(need, usable)), bytes(8192))})
    ta = tadata_4x(a["w"], a["h"], a["mw"], a["mh"]) if four else bytes(M.tadata_4x(a["mw"], a["mh"]) // 4)
    return result(out="\n".join(tri_text(a, "0x5555%04x%04x2325" % (a["w"], a["h"]))) + "\n", files={"tri": (scene_param(need), ta)})


def probe_answer(argv, a, rgn, world):
    line = a["prog"] == "p1131-green__0"
    outf, parf = (L.LINE + "/ln-ctl64-r1.txt.gz", L.LINE + "/ln-ctl64-r1.param.bin.gz") if line else (L.POINT + "/pp-c-s1.txt.gz", L.POINT + "/pp-c-s1.param.bin.gz")
    out, par = L.read_text(outf), L.read_bytes(parf)
    if a["cmd"] is not None:
        if a["cmd"] & 0xC0000000 and rgn == 0:
            return result(out="programs asm\nprobe %s: job: rejected (Invalid argument)\n" % a["prog"], rc=1)
        w = L.dwords(par)
        pos = w.index(0x00040101)
        val = 0
        if world == "t-field" and a["cmd"] == 0x80000000:
            val = 0x2
        if world == "t-pos" and a["cmd"] == 0x80000000 and not line:
            pos = 3
        w2 = w[:pos] + [val] + w[pos:]
        par = struct.pack("<%dI" % len(w2), *w2)
    return result(out=out, rc=0, files={a["prog"]: (par, bytes(24576))})


# ---- kept(): a stage directory as the runner writes it ----------------------------------------------------------------------------
def table(stage, kp=KP):
    rows = []
    for ln in open(os.path.join(kp, "tables", stage + ".txt")).read().splitlines():
        if ln and not ln.startswith("#"):
            name, sset, risk, knobs, rt, args = ln.split("|", 5)
            rows.append(dict(name=name, set=sset, risk=risk, knobs=knobs, args=args))
    return rows


def _wgz(p, data):
    if isinstance(data, str):
        data = data.encode()
    with open(p, "wb") as f:
        f.write(gzip.compress(data, 6, mtime=0))


def regs_text(latch=None):
    stat, word = latch or (0, 0)
    return "\n".join(["sgxfive regs 1", "reg 0x0000 0x0000a6aa", "reg 0x0008 0x00000020", "reg 0x012c 0x20000000", "reg 0x0118 0x00000480",
                      "reg 0x0c04 0x%08x" % (stat | 0x80000), "reg 0x0c08 0x%08x" % word, "reg 0x0724 0x00000000"]) + "\n"


def classify(r):
    txt = r["out"] + "\n".join(r["kmsg"])
    if re.search(r"BIF fault|faulted", txt):
        return "fault"
    if r["rc"] == 0:
        return "ok"
    if r["rc"] == 1 and "diff:" in r["out"] and not re.search(r"FAILED after|rejected|failed:|^sgxfive-test: ", r["out"], re.M):
        return "ok"
    return "fail"


def kept(outdir, stage, world="model", kp=KP, rows=None, skip=()):
    """The stage as the runner keeps it, every answer from the row's argv and knobs (never its name)."""
    os.makedirs(outdir, exist_ok=True)
    cs = ["name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg"]
    for row in rows or table(stage, kp):
        name = row["name"]
        if name in skip:
            continue
        knobs = row["knobs"].split()
        held = "held" in knobs
        pb = int(next((k[3:] for k in knobs if k.startswith("pb:")), "0x422"), 16)
        rgn = 1 if "rgn:1" in knobs else 0
        argv = shlex.split(row["args"].replace("$W", "/w").replace("$S", "/s"))
        r = answer(argv, pb, rgn, "Y" if held else "N", world)
        _wgz(os.path.join(outdir, name + ".txt.gz"), r["out"])
        _wgz(os.path.join(outdir, name + ".dmesg.gz"), "\n".join(r["kmsg"]) + ("\n" if r["kmsg"] else ""))
        cls = classify(r)
        if "--dump-render" in argv and cls == "ok":
            for stem, (par, ta) in r["files"].items():
                _wgz(os.path.join(outdir, "%s.%s.param.bin.gz" % (name, stem)), par)
                _wgz(os.path.join(outdir, "%s.%s.tadata.bin.gz" % (name, stem)), ta)
        _wgz(os.path.join(outdir, name + ".snap0.regs.gz"), regs_text())
        if held:
            _wgz(os.path.join(outdir, name + ".snap1.regs.gz"), regs_text(r["latch"]))
            if "dumpheld" in knobs and r["held_param"] is not None:
                _wgz(os.path.join(outdir, name + ".heldparam.bin.gz"), r["held_param"])
                _wgz(os.path.join(outdir, name + ".heldtadata.bin.gz"), r["held_tadata"])
        else:
            _wgz(os.path.join(outdir, name + ".snap9.regs.gz"), regs_text())
        fr = "%d" % (r["latch"][0] if r["latch"] else 0) if held else "-"
        cs.append("\t".join([name, stage, row["set"], row["risk"], row["knobs"], "-", row["args"], str(r["rc"]), cls,
                             "held" if held else "plain", fr, "-", "yes" if held and cls == "fault" else "no"]))
    with open(os.path.join(outdir, "cases.tsv"), "w") as f:
        f.write("\n".join(cs) + "\n")


# ---- the fake tool ---------------------------------------------------------------------------------------------------------------
def tool(argv):
    """The fake sgxfive-test-rgn4: the answer from argv and the fake debugfs ($FAKE_DBGREAL's render_pb_pages and render_rgn_arrays,
    $FAKE_DIR/hold).  FAKE_RULES ("ARGV-SUBSTRING|OUTCOME" lines) override: fatal, timeout, hang, nodiff, resetinfo, fault (a fault of
    another word: TA side 0x20006061).  FAKE_HEALTH_BAD / FAKE_HEALTH_SEQ act on the health pair (a bare `tri` or `fill`)."""
    kmsg = os.environ["KMSG"]
    F, D = os.environ["FAKE_DIR"], os.environ["FAKE_DBGREAL"]
    log = os.environ.get("FAKE_LOG")
    if log:
        open(log, "a").write(" ".join(argv) + "\n")
    world = os.environ.get("FAKE_WORLD", "model")
    if argv in (["tri"], ["fill"]):
        if os.environ.get("FAKE_HEALTH_BAD"):
            print("job: failed: job faulted, context lost (Input/output error)")
            return 1
        seq = (os.environ.get("FAKE_HEALTH_SEQ") or "").split()
        if seq:
            cf = os.path.join(F, "hcount")
            k = int(open(cf).read()) if os.path.exists(cf) else 0
            open(cf, "w").write(str(k + 1))
            if k < len(seq) and seq[k] == "fail":
                print("job: failed: job faulted, context lost (Input/output error)")
                return 1
    pb = int(open(os.path.join(D, "render_pb_pages")).read().strip(), 0)
    rgn = int(open(os.path.join(D, "render_rgn_arrays")).read().strip(), 0)
    hold = open(os.path.join(F, "hold")).read().strip()
    joined = " ".join(argv)
    outcome = "world"
    for r in (os.environ.get("FAKE_RULES") or "").split("\n"):
        if r and r.rsplit("|", 1)[0] in joined and len(argv) > 1:
            outcome = r.rsplit("|", 1)[1]
            break
    if outcome == "timeout":
        return 124
    if outcome == "fatal":
        open(kmsg, "a").write("watchdog: BUG: soft lockup - CPU#0 stuck\n")
        print("job: ok")
        return 0
    if outcome == "nodiff":
        print("something went wrong")
        return 1
    if outcome == "hang":
        open(kmsg, "a").write("gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, %s\n" % ("recovery held (debugfs hold_recovery)" if hold == "Y" else "recovering"))
        print("job: failed: job hung, context lost (Connection timed out)")
        return 1
    if outcome == "fault":
        open(kmsg, "a").write("\n".join([FAULT_LINE % (0x90004, 0x20006061)] + RESET_LINES) + "\n")
        print("job: failed: job faulted, context lost (Input/output error)\ntri: FAILED after 0 renders")
        return 1
    r = answer(argv, pb, rgn, hold, world)
    if outcome == "resetinfo":
        open(kmsg, "a").write("\n".join(RESET_LINES) + "\n")
    a = parse(argv)
    if a["dump"] and os.path.isdir(a["dump"]) and r["rc"] in (0, 1) and r["files"] and not r["latch"] and "faulted" not in r["out"]:
        for stem, (par, ta) in r["files"].items():
            open(os.path.join(a["dump"], stem + ".param.bin"), "wb").write(par)
            open(os.path.join(a["dump"], stem + ".tadata.bin"), "wb").write(ta)
    if r["kmsg"]:
        open(kmsg, "a").write("\n".join(r["kmsg"]) + "\n")
    if r["latch"]:
        stat, word = r["latch"]
        open(os.path.join(F, "state"), "w").write("0x%x 0x%08x 0x480 0x20000000\n" % (stat, word))
        open(os.path.join(F, "heldparam"), "wb").write(r["held_param"] or b"")
        open(os.path.join(F, "heldtadata"), "wb").write(r["held_tadata"] or b"")
    sys.stdout.write(r["out"])
    return r["rc"]


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "tool":
        sys.exit(tool(sys.argv[2:]))
    if len(sys.argv) == 5 and sys.argv[1] == "kept":
        kept(sys.argv[2], sys.argv[3], sys.argv[4])
