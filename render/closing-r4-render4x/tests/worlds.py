"""worlds.py: R4-G worlds built from the REAL kept records (E824's k-f4 outputs and dumps, E828's, E827's rg-pb, E726's cube probe, the
11.31 line and point dumps, K2's c1 registers) and from the frozen predictions where no record has the value (the page counts of
sizes never run, the faces of the held-out cube programs).  One world, two uses:

  kept(outdir, stage, world)   a kept stage directory (cases.tsv, NAME.txt.gz, NAME.dmesg.gz, dumps, registers) for the scorer tests
  tool ARGS...                 the fake sgxfive-test-rgn4 of tests/run_mock.sh: it reads the case from the last "resgx545 case NAME RUN"
                               marker of $KMSG, prints that world's output, writes its dumps, logs its kernel lines and, for a held
                               fault, latches the fake GPU ($FAKE_DIR/state)

Worlds (WORLDS): model (every hypothesis held), and the variants named in the table at the end of this file.
"""
import gzip
import hashlib
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402

STAGES = ["s0", "c", "p", "o", "t", "h"]
FIXED = (0x422, 0x423, 0x463)


class _Lazy:
    def __getattr__(self, k):
        import cubegen
        return getattr(cubegen, k)


C = _Lazy()


def table(stage):
    rows = []
    for ln in open(os.path.join(KP, "tables", stage + ".txt")).read().splitlines():
        if ln and not ln.startswith("#"):
            name, sset, risk, knobs, rt, args = ln.split("|", 5)
            rows.append(dict(name=name, set=sset, risk=risk, knobs=knobs, args=args))
    return rows


def all_cases():
    return {r["name"]: (st, r) for st in STAGES for r in table(st)}


def P(stage):
    return L.load_predictions(stage + ".tsv")


def pv(stage, case, q):
    return L.pred(P(stage), case, q)


# ---- text of the tool's output ---------------------------------------------------------------------------------------------------
def dims(args):
    m = re.search(r"--width (\d+) --height (\d+)", args)
    mm = re.search(r"--max-width (\d+) --max-height (\d+)", args)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (64, 64)
    mw, mh = (int(mm.group(1)), int(mm.group(2))) if mm else (w, h)
    return w, h, mw, mh


def tri_text(args, hashv, state="ok", tri=None, regs=None, dump=None, overflowed=False, wrong=0):
    w, h, mw, mh = dims(args)
    n = w * h
    o = ["tri: render context for targets up to %dx%d" % (mw, mh)]
    if "--aa4" in args:
        o.append("tri: render context made for 4x targets (DRM_SGXFIVE_CTX_RENDER_AA_4X)")
    o.append("tri: triangle (0,0) (%d,0) (0,%d), depth 0.5 0.5 0.5" % (3 * w, 3 * h))
    if state == "fault":
        return o + ["job: failed: job faulted, context lost (Input/output error)", "target: %dx%d hash 0x00ed1e2eb204fb25" % (w, h),
                    "diff: %d of %d pixels, first (0, 0) 0xdeadbeef expected 0xff00ff00" % (n, n), "outside: 0 dwords", "layout: fb 0x3e001000",
                    "sgxfive-test: render: job faulted, context lost (Input/output error)", "tri: FAILED after 0 renders"]
    tri = n if tri is None else tri
    o += ["job: ok", "target: %dx%d hash %s" % (w, h, hashv)]
    if overflowed:
        o += ["diff: %d of %d pixels, first (0, 0) 0xdeadbeef expected 0xff00ff00" % (n, n), "outside: 0 dwords", "layout: fb 0x3e001000",
              "tri %dx%d #1: overflowed, 0 triangle, 0 background, %d other; wrong %d inside, 0 outside, 0 at edges; 0 if flipped; guard 0" % (w, h, n, n - 1),
              "tri %dx%d #1: 1000 us" % (w, h)]
        if dump:
            o.append("probe tri: render memory to %s/tri.{param,tadata}.bin (4603904, 32768 bytes)" % dump)
        o.append("tri: 0 of 1 renders ok, 1 overflowed")
    elif wrong:
        o += ["diff: %d of %d pixels, first (1, 1) 0xff203040 expected 0xff00ff00" % (wrong, n), "outside: 0 dwords", "layout: fb 0x3e001000",
              "tri %dx%d #1: %d triangle, %d background, 0 other; wrong %d inside, 0 outside, 0 at edges; 0 if flipped; guard 0" % (w, h, tri, n - tri, wrong),
              "tri %dx%d #1: 1000 us" % (w, h)]
        if dump:
            o.append("probe tri: render memory to %s/tri.{param,tadata}.bin (4603904, 24576 bytes)" % dump)
        o.append("tri: 0 of 1 renders ok")
    else:
        o += ["diff: 0 of %d pixels" % n, "outside: 0 dwords", "layout: fb 0x3e001000",
              "tri %dx%d #1: %d triangle, %d background, 0 other; wrong 0 inside, 0 outside, 0 at edges; 0 if flipped; guard 0" % (w, h, tri, n - tri),
              "tri %dx%d #1: 1000 us" % (w, h)]
        if dump:
            o.append("probe tri: render memory to %s/tri.{param,tadata}.bin (4603904, 32768 bytes)" % dump)
        o.append("tri: 1 renders ok")
    if regs and "--regs" in args:
        o += ["regs: 0x0700-0x072c at 0x3e000000"] + ["reg 0x%04x 0x%08x" % (k, v) for k, v in sorted(regs.items())]
    return o


def scene_param(used, fixed=True, pages=0x464):
    b = bytearray(pages * 4096)
    for i in range(min(used, pages)):
        b[i * 4096: i * 4096 + 8] = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    if fixed:
        for i in FIXED:
            if i < pages:
                b[i * 4096: i * 4096 + 8] = b"\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11"
    return bytes(b)


def read(path):
    return L.read_bytes(path)


def cube_text(name, pixels):
    return "\n".join(["programs asm", "probe %s: scratch at 0x3e003000 (64 KiB)" % name, "probe %s: job time: 398 us" % name] +
                     ["probe %s: row %d: %s" % (name, y, " ".join("%08x" % v for v in pixels[y * 64:(y + 1) * 64])) for y in range(32)]) + "\n"


def face_pixels(faces, off=17):
    return [0xD0000000 | (int(f) * 256 + (off + i) % 256) for i, f in enumerate(faces)]


# ---- the model world: every hypothesis held --------------------------------------------------------------------------------------
def result(**k):
    r = dict(out="", rc=0, cls="ok", param=None, tadata=None, kmsg=[], latch=None, regs={}, held=False, reg0724=None)
    r.update(k)
    return r


FAULT_LINE = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x%x at 0x%08x (PD 0x2d75000) stalls job 86, recovering"
HELD_LINE = "gma500 0000:00:02.0: [drm] sgxfive: job 86 hung, recovery held (debugfs hold_recovery)"
RESET_LINES = ["gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0x0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/0x480",
               "gma500 0000:00:02.0: [drm] SGX reset: after the fault clear BIF_FAULT 0x0 BIF_INT_STAT 0x80000"]


def fault_result(args, stat, word, held):
    out = "\n".join(tri_text(args, "0x0", state="fault")) + "\n"
    kmsg = [FAULT_LINE % (0x80000 | stat, word), HELD_LINE] if held else [FAULT_LINE % (0x80000 | stat, word)] + RESET_LINES
    return result(out=out, rc=1, cls="fault", kmsg=kmsg, latch=(stat, word) if held else None, held=held)


def model_case(case, args, knobs):
    st, row = all_cases()[case]
    pr = P(st)
    held = "held" in knobs.split() or any(k.startswith("cell:") for k in knobs.split())
    w, h, mw, mh = dims(args)
    if case == "s0-1x-1024x768":
        return result(out=L.read_text(L.RGN4 + "/j5-ctl-1x.out"), param=scene_param(97), tadata=bytes(8192))
    if st in ("s0", "p"):
        hashv = L.pred_or(pr, case, "target_hash", "0x1234567800000325")
        used = int(L.pred_or(pr, case, "pb_used", "0"))
        regs = {0x0724: int(L.pred_or(pr, case, "reg0724", "0x0"), 16)}
        ta = int(L.pred_or(pr, case, "tadata_size", "32768"))
        tri = None
        txt = tri_text(args, hashv, dump="/home/x/dump", regs=regs)
        return result(out="\n".join(txt) + "\n", param=scene_param(used), tadata=bytes(ta), reg0724=regs[0x0724])
    if st == "o":
        pbv = re.search(r"pb:(0x[0-9a-f]+)", knobs)
        need_ok = L.pred_or(pr, case, "outcome")
        if need_ok == "complete":
            return result(out="\n".join(tri_text(args, "0xde0b9233c9822325", dump="/home/x/dump", regs={0x0724: 0xc000c0})) + "\n",
                          param=scene_param(193 if "--aa4" in args else 97, pages=0x464), tadata=bytes(122880))
        if need_ok == "overflow":
            return result(out="\n".join(tri_text(args, "0x1234000000000325", overflowed=True, dump="/home/x/dump")) + "\n", param=scene_param(40, False, 0x100), tadata=bytes(32768))
        pc = "o5-4x-288x144-p23-held" if case.startswith("o6") else case
        return fault_result(args, int(L.pred(pr, pc, "fault_int"), 16), 0x10000011, held)
    if st == "c":
        if case == "c-cu-xn":
            return result(out=L.read_text(L.CUBE + "/cu-xn.txt.gz"))
        spec = C.HELDOUT["r4g-" + case[2:]]
        f, _ = C.faces(*spec)
        return result(out=cube_text("r4g-" + case[2:], face_pixels(f)))
    if st == "t":
        return t_case(case, args)
    if st == "h":
        stat = int(L.pred(pr, case, "job_int"), 16)
        word = int(L.pred(pr, case, "job_word"), 16)
        return fault_result(args, stat & 0xffff, word, True)
    raise KeyError(case)


def t_case(case, args):
    e40 = L.read_text(L.REG + "/pb-e40-m2-64a.txt.gz")
    e40p = L.read_bytes(L.REG + "/pb-e40-m2-64a.tri.param.bin.gz")
    e40t = L.read_bytes(L.REG + "/pb-e40-m2-64a.tri.tadata.bin.gz")
    if case in ("t6-ctl-te40-1array", "t1-aa4-te40", "t2-aa4-te80"):
        out = e40
        if "--aa4" in args:
            out = out.replace("tri: triangle", "tri: render context made for 4x targets (DRM_SGXFIVE_CTX_RENDER_AA_4X)\ntri: triangle", 1)
        return result(out=out, rc=1, param=e40p, tadata=e40t)
    line = case.startswith("t3")
    outf, parf = (L.LINE + "/ln-ctl64-r1.txt.gz", L.LINE + "/ln-ctl64-r1.param.bin.gz") if line else (L.POINT + "/pp-c-s1.txt.gz", L.POINT + "/pp-c-s1.param.bin.gz")
    out, par = L.read_text(outf), L.read_bytes(parf)
    if case.endswith("-te40"):
        w = L.dwords(par)
        pos = w.index(0x00040101)
        w2 = w[:pos] + [0] + w[pos:]
        par = struct.pack("<%dI" % len(w2), *w2)
    return result(out=out, rc=0, param=par, tadata=bytes(24576))


def h_step(cell, step, world_flags):
    """Result of one step of a cell: ok, or a fault with a word."""
    stat, word = 0x4, int(pv("h", cell, "job_word"), 16)
    kind = cell.split("-")[-1]
    fails = 2 if kind in ("health", "fill") else 0
    if kind == "fill" and step == "fill":
        return result(out="diff: 0 of 2048 pixels\n")
    if kind == "ctx" and step == "ctx":
        return result(out="tri: render context for targets up to 1024x768\njob: ok\ndiff: 0 of 4096 pixels\ntri: 1 renders ok\n")
    k = int(step[1]) if step.startswith("h") else 0
    flags = world_flags
    if "noreplay" in flags:
        fails = 0
    if "stop" in flags:
        fails = 4
    if "ownend" in flags and kind == "health" and cell.startswith("h2"):
        fails, word = 2, 0x20006061
    if "nofill" in flags and kind == "fill":
        fails = 0
    if k <= fails:
        return result(out="tri: render context for targets up to 64x64\njob: failed: job faulted, context lost (Input/output error)\ntarget: 64x64 hash 0xe4364b426cdce325\n"
                      "diff: 4096 of 4096 pixels, first (0, 0) 0xdeadbeef expected 0xff203040\noutside: 0 dwords\nlayout: fb 0x3e001000\n"
                      "sgxfive-test: render: job faulted, context lost (Input/output error)\ntri: FAILED after 0 renders\n", rc=1, cls="fault",
                      kmsg=[FAULT_LINE % (0x80000 | stat, word)] + RESET_LINES)
    return result(out="tri: render context for targets up to 64x64\njob: ok\ntarget: 64x64 hash 0x99385a04ee01c585\ndiff: 0 of 4096 pixels\ntri: 1 renders ok\n")


# ---- variants --------------------------------------------------------------------------------------------------------------------
def with_out(r, f):
    r = dict(r)
    r["out"] = f(r["out"])
    return r


def v_s0_miss(case, r, args, knobs):
    if case == "s0-4x-288x144":
        return with_out(r, lambda o: o.replace("0x4a61860dcb4ab325", "0x4a61860dcb4ab326"))
    return r


def v_s0_nodata(case, r, args, knobs):
    if case == "s0-4x-1024x768":
        return result(out="tri: render context for targets up to 1024x768\n")
    return r


def v_p_fault(case, r, args, knobs):
    if case in ("p-4096x960", "p-960x4096"):
        return fault_result(args, 0x100, 0x10000011, False)
    return r


def v_p_overflow(case, r, args, knobs):
    if case == "p-3072x1280":
        return result(out="\n".join(tri_text(args, "0x1234000000000325", overflowed=True, dump="/home/x/dump")) + "\n", param=scene_param(1024, True), tadata=bytes(0x84000))
    return r


def v_p_pages(case, r, args, knobs):
    if case == "p-2048x1536":
        used = int(pv("p", case, "pb_used")) + 32
        r = dict(r)
        r["param"] = scene_param(used)
    return r


def v_p_ta(case, r, args, knobs):
    if case == "p-1280x1024":
        r = dict(r)
        r["tadata"] = bytes(0x35000)
    return r


def v_o_enospc(case, r, args, knobs):
    if case in ("o4-4x-1024x768-pe2", "o5-4x-288x144-p23-held", "o7-4x-4096x1152-p422"):
        return result(out="\n".join(tri_text(args, "0x1234000000000325", overflowed=True)) + "\n", param=scene_param(40, False, 0x100))
    return r


def v_o_o2fault(case, r, args, knobs):
    if case == "o2-1x-1024x768-p82":
        return fault_result(args, 0x100, 0x10000011, False)
    return r


def v_o_o3over(case, r, args, knobs):
    if case == "o3-4x-1024x768-pe3":
        return result(out="\n".join(tri_text(args, "0x1234000000000325", overflowed=True)) + "\n", param=scene_param(40, False, 0x100))
    return r


def v_o_o8fault(case, r, args, knobs):
    if case == "o8-1x-4096x4096-p422":
        return fault_result(args, 0x100, 0x10000011, False)
    return r


def v_o_word(case, r, args, knobs):
    if case == "o4-4x-1024x768-pe2":
        return fault_result(args, 0x4, 0x20006061, False)
    return r


def v_o5_nofault(case, r, args, knobs):
    if case == "o5-4x-288x144-p23-held":
        return result(out="\n".join(tri_text(args, "0x1234000000000325", overflowed=True)) + "\n", param=scene_param(40, False, 0x100))
    return r


def v_t_field(case, r, args, knobs):
    if case == "t3-line-te40":
        w = L.dwords(r["param"])
        w[9] = 0x2
        r = dict(r)
        r["param"] = struct.pack("<%dI" % len(w), *w)
    return r


def v_t_draw(case, r, args, knobs):
    if case == "t1-aa4-te40":
        return result(out="\n".join(tri_text(args, "0xd0530839d87ea325", tri=4096)) + "\n", param=r["param"], tadata=r["tadata"], rc=0)
    return r


def v_t_pos(case, r, args, knobs):
    if case == "t4-point-te40":
        w = L.dwords(r["param"])
        pos = w.index(0x00040101)
        w = w[:pos - 1] + w[pos:]            # undo the insertion at pos and insert elsewhere (at 3)
        w = w[:3] + [0] + w[3:]
        r = dict(r)
        r["param"] = struct.pack("<%dI" % len(w), *w)
    return r


def v_c_wrong(case, r, args, knobs):
    if case == "c-cube-a":
        spec = C.HELDOUT["r4g-cube-a"]
        f, gap = C.faces(*spec)
        idx = [i for i in range(2048) if gap[i] < 0.02][:12]
        f = list(f)
        for i in idx:
            f[i] = (f[i] + 2) % 6
        return result(out=cube_text("r4g-cube-a", face_pixels(f)))
    return r


def v_c_ctl(case, r, args, knobs):
    if case == "c-cu-xn":
        spec = C.E726["cu-zp"]
        f, _ = C.faces(*spec)
        return result(out=cube_text("p1141-cube__4", face_pixels(f)))
    return r


WORLDS = {
    "model": None,
    "s0-miss": v_s0_miss, "s0-nodata": v_s0_nodata,
    "p-fault": v_p_fault, "p-overflow": v_p_overflow, "p-pages": v_p_pages, "p-ta": v_p_ta,
    "o-enospc": v_o_enospc, "o-o2fault": v_o_o2fault, "o-o3over": v_o_o3over, "o-o8fault": v_o_o8fault, "o-word": v_o_word, "o5-nofault": v_o5_nofault,
    "t-field": v_t_field, "t-draw": v_t_draw, "t-pos": v_t_pos,
    "c-wrong": v_c_wrong, "c-ctl": v_c_ctl,
    "h-noreplay": None, "h-ownend": None, "h-stop": None, "h-nofill": None, "h-nofault": None,
}
H_FLAGS = {"h-noreplay": "noreplay", "h-ownend": "ownend", "h-stop": "stop", "h-nofill": "nofill"}


def case_result(world, case, args=None, knobs=None):
    """The world's result for a case (a table row, or 'CELL.STEP' of stage h)."""
    cases = all_cases()
    if "." in case:
        cell, step = case.rsplit(".", 1)
        return h_step(cell, step, H_FLAGS.get(world, ""))
    st, row = cases[case]
    args = args if args is not None else row["args"]
    knobs = knobs if knobs is not None else row["knobs"]
    r = model_case(case, args, knobs)
    if world == "h-nofault" and case == "h1-288x144-health":
        r = result(out="\n".join(tri_text(args, "0x1234000000000325", dump="/home/x/dump")) + "\n", rc=0, param=scene_param(5), tadata=bytes(32768))
    fn = WORLDS.get(world)
    if fn:
        r = fn(case, r, args, knobs)
    return r


# ---- kept(): a stage directory as the runner writes it ----------------------------------------------------------------------------
def _wgz(p, data):
    if isinstance(data, str):
        data = data.encode()
    with open(p, "wb") as f:
        f.write(gzip.compress(data, 6, mtime=0))


def regs_text(r, held_stage=None, state="idle", reg0724=None):
    stat, word = (0, 0)
    if r.get("latch"):
        stat, word = r["latch"]
    lines = ["sgxfive regs 1", "state loaded 1 live 1 sw_events 0 bif_faults 0", "reg 0x0000 0x0000a6aa",
             "reg 0x0008 0x%08x" % (0x000ccff8 if state == "latched" else 0x78 if state == "after" else 0x20),
             "reg 0x012c 0x%08x" % (0x20000000), "reg 0x0118 0x00000480", "reg 0x0c04 0x%08x" % ((stat | 0x80000) if stat else 0x80000),
             "reg 0x0c08 0x%08x" % word, "reg 0x0724 0x%08x" % (reg0724 or 0)]
    return "\n".join(lines) + "\n"


def kept(outdir, stage, world="model", skip=()):
    os.makedirs(outdir, exist_ok=True)
    rows = ["name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg"]
    for row in table(stage):
        name = row["name"]
        if name in skip:
            continue
        knobs = row["knobs"].split()
        held = "held" in knobs or any(k.startswith("cell:") for k in knobs)
        # needs: a row that needs an earlier row's class
        need = [k for k in knobs if k.startswith("needs:")]
        if need:
            nn, nc = need[0][6:].split("=")
            have = next((x[8] for x in map(lambda s: s.split("\t"), rows[1:]) if x[0] == nn), "none")
            if have != nc:
                rows.append("\t".join([name, stage, row["set"], row["risk"], row["knobs"], "-", row["args"], "-", "skipped", "-", "-", "-", "no"]))
                continue
        r = case_result(world, name)
        if r.get("out") is None:
            continue
        _wgz(os.path.join(outdir, name + ".txt.gz"), r["out"])
        _wgz(os.path.join(outdir, name + ".dmesg.gz"), "\n".join(r["kmsg"]) + ("\n" if r["kmsg"] else ""))
        if r["param"] is not None:
            _wgz(os.path.join(outdir, name + ".tri.param.bin.gz"), r["param"])
        if r["tadata"] is not None:
            _wgz(os.path.join(outdir, name + ".tri.tadata.bin.gz"), r["tadata"])
        _wgz(os.path.join(outdir, name + ".snap0.regs.gz"), regs_text(result()))
        if held:
            _wgz(os.path.join(outdir, name + ".snap1.regs.gz"), regs_text(r, state="latched"))
            _wgz(os.path.join(outdir, name + ".snap3.regs.gz"), regs_text(result(), state="after"))
        else:
            _wgz(os.path.join(outdir, name + ".snap9.regs.gz"), regs_text(r, reg0724=r.get("reg0724")))
        fr = "-"
        if held:
            fr = "%d" % (r["latch"][0] if r.get("latch") else 0)
        rows.append("\t".join([name, stage, row["set"], row["risk"], row["knobs"], "-", row["args"], str(r["rc"]), r["cls"],
                               "held" if held else "plain", fr, "-", "yes" if (held and r["cls"] == "fault") else "no"]))
        for k in knobs:
            if k.startswith("cell:"):
                fault = r["cls"] == "fault"
                if not fault:
                    continue
                seq = []
                if k == "cell:ctx":
                    seq.append("ctx")
                if k == "cell:fill":
                    seq.append("fill")
                for stp in seq + ["h1", "h2", "h3", "h4"]:
                    s = h_step(name, stp, H_FLAGS.get(world, ""))
                    if stp in ("h2", "h3", "h4") and rows[-1].split("\t")[8] == "ok" and stp.startswith("h"):
                        break
                    _wgz(os.path.join(outdir, "%s.%s.txt.gz" % (name, stp)), s["out"])
                    _wgz(os.path.join(outdir, "%s.%s.dmesg.gz" % (name, stp)), "\n".join(s["kmsg"]) + ("\n" if s["kmsg"] else ""))
                    _wgz(os.path.join(outdir, "%s.snap%s.regs.gz" % (name, stp)), regs_text(result(), state="after"))
                    cls = s["cls"]
                    rows.append("\t".join(["%s.%s" % (name, stp), stage, row["set"], row["risk"], row["knobs"], "-", "tri", str(s["rc"]), cls, "step", "-", "-", "no"]))
                    if cls == "ok" and stp.startswith("h"):
                        break
    with open(os.path.join(outdir, "cases.tsv"), "w") as f:
        f.write("\n".join(rows) + "\n")


# ---- the fake tool ---------------------------------------------------------------------------------------------------------------
def last_marker(kmsg_path):
    last = None
    for ln in open(kmsg_path).read().splitlines():
        m = re.search(r"resgx545 case (\S+) \S+$", ln)
        if m:
            last = ("case", m.group(1))
        elif re.search(r"resgx545 r4g health \S+ (fill|tri) try", ln):
            last = ("health", None)
    return last


def tool(argv):
    kmsg = os.environ["KMSG"]
    log = os.environ.get("FAKE_LOG")
    if log:
        open(log, "a").write(" ".join(argv) + "\n")
    F = os.environ["FAKE_DIR"]
    args = " ".join(argv)
    if argv == ["tri"] or argv == ["fill"]:
        mk = last_marker(kmsg)
        if os.environ.get("FAKE_HEALTH_BAD"):
            print("job: failed: job faulted, context lost (Input/output error)")
            return 1
        if mk and mk[0] == "health":
            seq = (os.environ.get("FAKE_HEALTH_SEQ") or "").split()
            if seq:            # the Nth health call (fill or tri) answers the Nth word of the sequence, then ok
                cf = os.path.join(F, "hcount")
                k = int(open(cf).read()) if os.path.exists(cf) else 0
                open(cf, "w").write(str(k + 1))
                if k < len(seq) and seq[k] == "fail":
                    print("job: failed: job faulted, context lost (Input/output error)")
                    return 1
            if argv == ["fill"]:
                print("diff: 0 of 2048 pixels")
            else:
                print("diff: 0 of 4096 pixels")
            return 0
    mk = last_marker(kmsg)
    if mk is None or mk[0] != "case":
        print("fake tool: no case marker")
        return 1
    case = mk[1]
    world = os.environ.get("FAKE_WORLD", "model")
    hold = open(os.path.join(F, "hold")).read().strip()
    outcome = "world"
    for r in (os.environ.get("FAKE_RULES") or "").split("\n"):
        if r and r.split("|")[0] in case:
            outcome = r.split("|")[1]
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
    r = case_result(world, case, args=args if "." not in case else None, knobs=None)
    if outcome == "resetinfo":
        open(kmsg, "a").write("\n".join(RESET_LINES) + "\n")
    dump = None
    for i, a in enumerate(argv):
        if a == "--dump-render":
            dump = argv[i + 1]
    # a held row's fault latches only when the hold is on (the kernel's recovery otherwise logs its own lines)
    if r["cls"] == "fault" and "." not in case and r.get("latch") is None and hold == "Y":
        r = dict(r)
        r["latch"] = (int(re.search(r"BIF fault 0x([0-9a-f]+)", "\n".join(r["kmsg"])).group(1), 16) & 0xffff,
                      int(re.search(r"at 0x([0-9a-f]+)", "\n".join(r["kmsg"])).group(1), 16))
        r["kmsg"] = [r["kmsg"][0], HELD_LINE]
    elif r["cls"] == "fault" and r.get("latch") and hold != "Y":
        r = dict(r)
        r["kmsg"] = [FAULT_LINE % (0x80000 | r["latch"][0], r["latch"][1])] + RESET_LINES
        r["latch"] = None
    if dump and r["param"] is not None and os.path.isdir(dump):
        open(os.path.join(dump, "tri.param.bin"), "wb").write(r["param"])
        open(os.path.join(dump, "tri.tadata.bin"), "wb").write(r["tadata"] or b"")
    if r["kmsg"]:
        open(kmsg, "a").write("\n".join(r["kmsg"]) + "\n")
    if r.get("latch"):
        stat, word = r["latch"]
        open(os.path.join(F, "state"), "w").write("0x%x 0x%08x 0x480 0x20000000\n" % (stat, word))
        open(os.path.join(F, "heldparam"), "wb").write(scene_param(4, False, 0x40))
        open(os.path.join(F, "heldtadata"), "wb").write(bytes(4096))
    open(os.path.join(F, "reg0724"), "w").write("0x%08x\n" % (r.get("reg0724") or 0))
    sys.stdout.write(r["out"])
    return r["rc"]


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "tool":
        sys.exit(tool(sys.argv[2:]))
    if len(sys.argv) == 5 and sys.argv[1] == "kept":
        kept(sys.argv[2], sys.argv[3], sys.argv[4])
