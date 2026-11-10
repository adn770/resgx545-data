"""worlds.py: synthetic stage directories for the R3K-pixel scorer tests (what the runner keeps: cases.tsv, NAME.txt.gz, the
kernel-log slice, the regs snapshots, the TA data and parameter buffer dumps, the kw file) in which each hypothesis wins and
loses.  The shapes come from landed data: the tool's output of E728/E729/E788, the held-fault snapshots of S3 and R2, the
split-flow lines of closing-r1-pixgeo; the new module's kernel-log lines are written the way the fork's printk formats print."""
import gzip
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
import klib as L  # noqa: E402
import kgen as G  # noqa: E402

HEAD = "name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg\n"


def gz(path, data):
    if isinstance(data, str):
        data = data.encode()
    with open(path, "wb") as f:
        f.write(gzip.compress(data, 6, mtime=0))


def regs(status2=0x400, status=0x20000000, ctrl=0, int_stat=0x80000, fault=0):
    return ("sgxfive regs 1\nreg 0x0000 0x0000a6aa\nreg 0x0114 skip\nreg 0x0118 0x%08x\nreg 0x012c 0x%08x\n"
            "reg 0x0c00 0x%08x\nreg 0x0c04 0x%08x\nreg 0x0c08 0x%08x\n" % (status2, status, ctrl, int_stat, fault))


class Stage:
    """Builds a stage directory: rows appended with job(); cases.tsv written at close."""

    def __init__(self, outdir, stage):
        self.d, self.stage, self.rows = outdir, stage, []
        os.makedirs(outdir, exist_ok=True)

    def job(self, name, sset="control", knobs="", args="tri", rc=0, cls="ok", mode="plain", out="x\n", dmesg="", snaps=None,
            files=None, fr="-", held="no", kw=None):
        self.rows.append("\t".join([name, self.stage, sset, "safe", knobs, "-", args, str(rc), cls, mode, str(fr), "-", held]))
        if out is not None:
            gz(os.path.join(self.d, name + ".txt.gz"), out)
        if dmesg is not None:
            gz(os.path.join(self.d, name + ".dmesg.gz"), dmesg or "kernel log\n")
        for k, t in (snaps or {}).items():
            gz(os.path.join(self.d, "%s.snap%s.regs.gz" % (name, k)), t)
        for suf, b in (files or {}).items():
            gz(os.path.join(self.d, name + suf + ".gz"), b)
        if kw is not None:
            gz(os.path.join(self.d, name + ".kw.txt.gz"), kw)

    def close(self):
        open(os.path.join(self.d, "cases.tsv"), "w").write(HEAD + "\n".join(self.rows) + "\n")
        return self.d


# ---- k-f4 ----------------------------------------------------------------------------------------------------------------
def tadata(w, h, mw, mh, slots, f, size=None):
    """A TA data dump of the (mw x mh, f arrays) layout with `slots` arrays of the w x h target's rgn_size written."""
    t, m = L.layout(w, h), L.layout(mw, mh, f)
    size = size or m["size"]
    b = bytearray(size)
    for k in range(slots):
        off = m["rgn"] + k * t["rgn_size"]
        for i in range(64):
            if off + 4 * i + 4 <= size:
                struct.pack_into("<I", b, off + 4 * i, 0x10000000 | (k << 8) | i)
    return bytes(b)


def f4_out(w, h, diff=0, mx=None, my=None, extra=""):
    mx, my = mx or w, my or h
    d = "diff: %d of %d pixels" % (diff, w * h) + (", first (0, 0) 0xff203040 expected 0xff00ff00" if diff else "")
    return ("tri: render context for targets up to %dx%d\ntri: triangle (0,0) (192,0) (0,192), depth 0.5 0.5 0.5\njob: ok\n"
            "target: %dx%d hash 0xd0530839d87ea325\n%s\noutside: 0 dwords\n%s"
            "tri %dx%d #1: 4096 triangle, 0 background, 0 other; wrong 0 inside, 0 outside, 0 at edges; 0 if flipped; guard 0\n"
            "tri: 1 renders ok\n" % (mx, my, w, h, d, extra, w, h))


def f4_fault_out(w, h):
    return ("tri: render context for targets up to %dx%d\njob: failed: job faulted, context lost (Input/output error)\n"
            "diff: %d of %d pixels, first (0, 0) 0xdeadbeef expected 0xff00ff00\n" % (w, h, w * h, w * h))


def f4_world(outdir, world="f4"):
    """world: f4 (every frozen quantity holds) | leak (the knob has no effect: TA data of the knob-1 layout, h rows complete) |
    hfault:NAME (that h row faults at 0x20008) | c1ok (c1 completes) | slots3 (h rows write 3 arrays) | overflow (h8 overflowed)
    | c2sha (c2's TA data differs from c3's) | nodata (h3 missing)."""
    s = Stage(outdir, "k-f4")
    for n, sset, risk, knobs, cmd, w, h, f in G.f4_rows():
        held = n.startswith("c1")
        fk = f
        if world == "leak" and n.startswith(("h", "c2")):
            fk = 1                       # the context did not take the knob
        if world == "nodata" and n.startswith("h3"):
            continue
        faulted = (held and world != "c1ok") or world == "hfault:" + n
        nslots = 3 if (world == "slots3" and n.startswith("h")) else 4
        td = tadata(w, h, w, h, nslots, fk)
        if world == "c2sha" and n.startswith("c2"):
            td = tadata(w, h, w, h, 4, fk)[:-8] + b"\x01\0\0\0\x02\0\0\0"
        extra = "tri 64x64 #1: overflowed, 100 triangle, 0 background, 0 other; scene overflowed the parameter buffer, context kept (x)\n" \
            if world == "overflow" and n.startswith("h8") else ""
        if faulted:
            page = 0x20006 if held else 0x20008
            dm = "[1.0] gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90004 at 0x%x062 (PD 0x0) stalls job 7, recovering\n" % page
            kw = dict(out=f4_fault_out(w, h), rc=1, cls="fault", dmesg=dm)
            if held:
                kw.update(mode="held", fr=4, held="yes", dmesg=dm.replace("recovering", "recovering") +
                          "[1.1] gma500 0000:00:02.0: [drm] sgxfive: job 7 hung, recovery held (debugfs hold_recovery)\n",
                          snaps={0: regs(), 1: regs(0x480, 0x20000000, 0, 0x90004, (page << 12) | 0x61),
                                 2: regs(0x480, 0x20000000, 0, 0x90004, (page << 12) | 0x61), 3: regs()})
            s.job(n, sset, knobs, cmd, **kw)
        else:
            s.job(n, sset, knobs, cmd, out=f4_out(w, h, extra=extra), files={".tri.tadata.bin": td, ".tri.param.bin": b"param"},
                  mode="held" if held else "plain", snaps={0: regs(), 1: regs(), 2: regs(), 3: regs()} if held else None)
    return s.close()


# ---- k-pb ---------------------------------------------------------------------------------------------------------------
def pb_dump(own_words, words11_26=None, w11=None):
    a = np.zeros(1150976, dtype="<u4")
    base = G.pb_words()[0] if own_words else G.pb_words()[1]
    for i, v in base.items():
        a[i] = v
    if words11_26:
        for i, v in words11_26.items():
            a[i] = v
    return a.tobytes()


def pb_out(kind):
    """kind: empty (E728) | full (the twin) | partial (pixels drawn, not the twin)."""
    if kind == "full":
        h, d, t, rc = "0xd0530839d87ea325", "diff: 0 of 4096 pixels\n", "4096 triangle, 0 background", 0
    elif kind == "empty":
        h, d, t, rc = "0xfc5ff15e0434a325", "diff: 3969 of 4096 pixels, first (1, 1) 0xff203040 expected 0xff00ff00\n", \
            "0 triangle, 4096 background", 1
    else:
        h, d, t, rc = "0x1234567800000001", "diff: 1000 of 4096 pixels, first (3, 3) 0xff203040 expected 0xff00ff00\n", \
            "3096 triangle, 1000 background", 1
    out = ("tri: render context for targets up to 64x64\ntri: triangle (0,0) (192,0) (0,192), depth 0.5 0.5 0.5\njob: ok\n"
           "tri 64x64 #1: geometry only, the scene left open\njob: ok\ntarget: 64x64 hash %s\n%soutside: 0 dwords\nlayout: fb 0x3e001000\n"
           "tri 64x64 #2: %s, 0 other; wrong 0 inside, 0 outside, 0 at edges; 0 if flipped; guard 0\ntri 64x64 #2: 9381 us\n"
           "tri: 1 of 2 renders ok\n" % (h, d, t))
    return out, rc


def applied(pokes):
    return "".join("[2.0] gma500 0000:00:02.0: [drm] sgxfive: kpoke par:%d=0x%08x applied\n" % (i, v) for i, v in pokes)


def pb0_world(outdir, world="ok"):
    """ok | p0empty (the twin job draws nothing) | p1full (the TE 0x40 job draws) | d0stream (the stream words are not at dword 0)"""
    s = Stage(outdir, "k-pb0")
    own, twin = G.pb_words()
    for r in G.pb0_rows():
        n = r[0]
        kind = "full" if n == "pb-p0-te60" else "empty"
        if world == "p0empty" and n == "pb-p0-te60":
            kind = "empty"
        if world == "p1full" and n == "pb-p1-te40":
            kind = "full"
        out, rc = pb_out(kind)
        param = pb_dump(n != "pb-p0-te60")
        if world == "d0stream" and n == "pb-d0-te40":
            a = np.frombuffer(param, dtype="<u4").copy()
            a[0:2] = 0
            param = a.tobytes()
        s.job(n, r[1], r[3], r[4], out=out, rc=rc, files={".tri.param.bin": param, ".tri.tadata.bin": b"ta"})
    return s.close()


def pb_world(outdir, world="old"):
    """old (H-OLD: p3 gives the twin's image, p4 stays empty) | field (H-FIELD: p3 not the twin's, p4 draws) | bothempty |
    mixed (p3 twin's and p4 draws) | unapplied (the kernel log lacks the p3 pokes) | hang (p4 hangs) | p2changed"""
    s = Stage(outdir, "k-pb")
    own, twin = G.pb_words()
    for r in G.pb_rows():
        n, sset = r[0], r[1]
        pokes = []
        tail = r[4].split(" --dump-render")[0]
        for tok in tail.split(" --kpoke-render ")[1:]:
            _, sp = tok.split(":", 1)
            i, v = sp.replace("par:", "").split("=")
            pokes.append((int(i), int(v, 16)))
        kind, words = "empty", {i: v for i, v in pokes}
        if n.startswith("pb-p3"):
            kind = {"old": "full", "field": "empty", "bothempty": "empty", "mixed": "full"}.get(world, "empty")
        if n.startswith("pb-p4"):
            kind = {"old": "empty", "field": "partial", "bothempty": "empty", "mixed": "partial"}.get(world, "empty")
        out, rc = pb_out(kind)
        cls = "ok"
        if world == "hang" and n.startswith("pb-p4a"):
            s.job(n, sset, r[3], r[4], out="job: failed: job hung, context lost\n", rc=1, cls="hang", dmesg=applied(pokes))
            continue
        dm = applied(pokes) if not (world == "unapplied" and n.startswith("pb-p3")) else ""
        param = pb_dump(True, words)
        if world == "p2changed" and n.startswith("pb-p2"):
            param = pb_dump(True, {11: 0, 12: 0})
        s.job(n, sset, r[3], r[4], out=out, rc=rc, cls=cls, dmesg=dm, files={".tri.param.bin": param, ".tri.tadata.bin": b"ta"})
    return s.close()


# ---- k-bif ---------------------------------------------------------------------------------------------------------------
KW = "[3.0] gma500 0000:00:02.0: [drm] sgxfive: kregnow 0x%04x: 0x%08x -> 0x%08x, reads 0x%08x, BIF_INT_STAT 0x%08x BIF_FAULT 0x%08x\n"


def bif_world(outdir, world="clr", rows=None):
    """world, per row: w1c | clr | rst (the hypotheses) | other (partial change) | s1changed (the unset-bit write changed the
    state) | noeffectstale | ebusy (the writes were refused) | nolines (no kregnow line in the log) | wrongfault (another fault word) |
    nofault (the job completed) | ctrlstuck (BIF_CTRL not restored); n0: ok | n0changed
    A dict {row: world} in `rows` mixes worlds."""
    s = Stage(outdir, "k-bif")
    for r in G.BIF_ROWS:
        n, sset, risk, knobs, cmd = r
        w = (rows or {}).get(n, world)
        if n == "n0-idle":
            w0 = (rows or {}).get(n, "ok")
            snaps = {}
            changed = w0 == "n0changed"
            for k in ("b0", "b1", "b2", "b3", "b4", "b5"):
                snaps[k] = regs(int_stat=0x80001 if (changed and k in ("b3", "b4", "b5")) else 0x80000)
            snaps[0] = regs()
            dm = "".join(KW % (o, a, b, b, 0x80000, 0) for o, a, b in
                         ((0xc04, 0x80000, 1), (0xc04, 0x80000, 0), (0xc00, 0, 0x10), (0xc00, 0x10, 0)))
            s.job(n, sset, knobs, cmd, rc=0, cls="ok", mode="idle", out=None, dmesg=dm, snaps=snaps,
                  kw="set 0x0\n1 0x0c04=0x1 rc 0\n2 0x0c04=0x0 rc 0\n3 0x0c00^=0x10 rc 0\n4 0x0c00^=0x10 rc 0\n")
            continue
        word, page = G.BIF_FAULTS[n]
        wv = int(word, 16)
        if w == "wrongfault":
            wv = 0x90001
        bf = (int(page, 16) << 12) | 1
        s0 = regs(0x480, 0x20000000, 0, wv, bf)
        setv = wv & ~0x80000
        clean = regs(0x480, 0x20000000, 0, 0x80000, 0)
        kwl = "set 0x%x\n1 0x0c04=0x1 rc 0\n2 0x0c04=0x%x rc 0\n3 0x0c00^=0x10 rc 0\n4 0x0c00^=0x10 rc 0\n" % (setv, setv)
        if w == "ebusy":
            kwl = "set 0x%x\n1 0x0c04=0x1 rc 1\n2 0x0c04=0x%x rc 1\n3 0x0c00^=0x10 rc 1\n4 0x0c00^=0x10 rc 1\n" % (setv, setv)
        # state after each step: (int_stat, fault) per hypothesis
        if w in ("w1c", "s1changed", "ctrlstuck", "nolines", "wrongfault", "ebusy"):
            c2, c3 = ("w1c" == w or w in ("s1changed", "ctrlstuck", "nolines", "wrongfault")), True
        elif w == "clr":
            c2, c3 = False, True
        elif w == "rst":
            c2, c3 = False, False
        else:
            c2, c3 = None, None            # other
        st = {}
        st[1] = s0
        if w == "s1changed":
            st[1] = regs(0x480, 0x20000000, 0, 0x90000, bf)
        if w == "ebusy":
            st[2] = st[3] = st[4] = st[5] = s0
        elif c2 is None:
            odd = regs(0x480, 0x20000000, 0, 0x90001, bf)      # changed, not cleared
            st[2] = s0
            st[3] = odd
        else:
            st[2] = clean if c2 else s0
            st[3] = clean if c3 else s0
        if w != "ebusy":
            st[4] = st[3]
            st[5] = st[3]
        ctrl_end = 0x10 if w == "ctrlstuck" else 0
        snaps = {0: regs(), "b0": s0, 1: s0, 2: s0, 3: regs()}
        for k in range(1, 6):
            t = st[k]
            snaps["b%d" % k] = t if not (k >= 4 and w == "ctrlstuck") else regs(0x480, 0x20000000, 0x10, *(int(x, 16) for x in
                                                                              ("0x%x" % (0x80000 if c3 else wv), "0x0")))
        dm = ""
        if w not in ("nolines", "ebusy"):
            seq = [(0xc04, 0x00000000 | 0, 1, st[1]), (0xc04, 0, setv, st[2]), (0xc00, 0, 0x10, st[3]), (0xc00, 0x10, 0, st[4])]
            for o, a, b, t in seq:
                dm += KW % (o, a, b, b, int(t.split("reg 0x0c04 ")[1].split()[0], 16), int(t.split("reg 0x0c08 ")[1].split()[0], 16))
        dm += "[3.5] gma500 0000:00:02.0: [drm] sgxfive: job 9 hung, recovery held (debugfs hold_recovery)\n"
        dm += "[4.0] gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/0x480\n"
        dm += "[4.1] gma500 0000:00:02.0: [drm] SGX reset: after the fault clear BIF_FAULT 0 BIF_INT_STAT 0x80000\n"
        if w == "nofault":
            s.job(n, sset, knobs, cmd, rc=0, cls="ok", mode="held", out="job: ok\ndiff: 0 of 4096 pixels\n", dmesg=dm, snaps=snaps, kw=kwl)
        else:
            s.job(n, sset, knobs, cmd, rc=1, cls="fault", mode="held", fr=wv & 0xffff, held="yes",
                  out="job: failed: job faulted, context lost\n", dmesg=dm, snaps=snaps, kw=kwl)
    return s.close()
