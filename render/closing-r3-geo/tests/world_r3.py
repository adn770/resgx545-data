"""Synthetic worlds of R3 for the scorer tests and the runner mock: a `World` says, for a job (target, context, scene, thr0), the page
need, whether the raise happens, and the 0x072c counts at each abort; `timeline_text` writes the regtimeline block the real tool prints;
`simulate` is the Python TWIN of run/run_stage.sh's dynamic rows (the bisect pick, the L:/F: references, the fit gate, the calibration
gate, the control stop): it walks a frozen table, resolves each row's P from the observations kept so far (dpm3, the scorer's own
reader), and writes the kept directory the runner would write (cases.tsv with the P actually written).  tests/run_mock.sh runs the
bash runner against the same world through the fake tool and compares its picks with this twin's."""
from __future__ import annotations

import gzip
import pathlib
import re
import struct
import sys

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "gen"), str(R3 / "score")]
import dpm3  # noqa: E402
import r3models as M  # noqa: E402

HDR = "name\tstage\tset\trisk\tP\tknobs\trt\targs\trc\tclass\tnote\n"
REGS = ["0x0624", "0x0628", "0x0654", "0x0658", "0x065c", "0x0660", "0x0700", "0x0708", "0x0720", "0x0724", "0x0728", "0x072c", "0x0748"]


def parse_args(args: str):
    g = lambda k, d=None: (re.search(rf"--{k} (\d+)", args) or [None, d])[1]
    w, h = int(g("width", 64)), int(g("height", 64))
    mw, mh = int(g("max-width", w)), int(g("max-height", h))
    return dict(w=w, h=h, ctx=(mw, mh), full="--tri-full" in args, plain=w * h > 64 * 64)


class World:
    """limit(job) -> last raising thr0 of the job; need(job) -> total pages; counts(job, thr0) -> the 0x072c count before each abort;
    h_last: dword 36 follows H-last (True) or the peak less 2 (False)."""

    def __init__(self, limit, need=None, counts=None, h_last=True, void_cells=()):
        self.limit_fn, self.need_fn, self.counts_fn, self.h_last, self.void_cells = limit, need, counts, h_last, set(void_cells)

    def limit(self, j):
        return self.limit_fn(j)

    def need(self, j):
        if self.need_fn:
            return self.need_fn(j)
        base = 531 * j["w"] * j["h"] // (2048 * 2048)
        return base * (5 // 4 if j["full"] else 1) + (200 if j["full"] else 0)

    def counts(self, j, thr0, nab):
        if self.counts_fn:
            return self.counts_fn(j, thr0, nab)
        return [3, 5, 4, 6, 3, 5, 4, 6][:nab] if nab else []


def LT_WORLD(**kw):
    return World(lambda j: M.lt_last_thr0(j["w"], j["h"]) if not j["full"] else M.lt_last_thr0(j["w"], j["h"]), **kw)


def runs_of_job(need, thr0):
    runs, rem = [], need
    while rem > 0:
        runs.append(min(thr0, rem))
        rem -= thr0
    return runs


def timeline_text(thr0, need, counts):
    """The regtimeline block of a job with the page need `need` at the knob thr0: TA runs climbing to min(thr0, rest), a partial render
    (0x0658 bit 0) after each run but the last.  counts: the 0x072c count (both halves) of each run."""
    runs = runs_of_job(need, thr0)
    rows = []

    def row(status, p658, cnt, knob):
        r = {k: 0 for k in REGS}
        r["0x0624"], r["0x0658"], r["0x0724"], r["0x072c"] = knob, p658, (status << 16) | status, (cnt << 16) | cnt
        rows.append([r[k] for k in REGS])
    row(0, 0, 0, 0x400)
    for i, pk in enumerate(runs):
        c = counts[i] if i < len(counts) else counts[-1] if counts else 0
        for s in range(1, pk + 1):
            row(s, 0, c, thr0)
        if i < len(runs) - 1:
            row(pk, 1, c, thr0)
            row(pk, 1, c, thr0)
            row(0, 0, 0, thr0)
    row(0, 0, 0, thr0)
    t = ["timeline: regs " + " ".join(REGS) + f" samples {len(rows)} seconds 0 start 100 end {100 + 10 * len(rows)} rc 3"]
    for i, r in enumerate(rows):
        t.append(f"tl {100 + 10 * i} " + " ".join(f"{v:08x}" for v in r))
    return "\n".join(t) + "\n"


def job_reading(world: World, args: str, thr0: int):
    """(timeline text, buf09 words) of a job under the world."""
    j = parse_args(args)
    need = world.need(j)
    lim = world.limit(j)
    runs = runs_of_job(need, thr0)
    nab = max(len(runs) - 1, 0)
    cnt = world.counts(j, thr0, nab + 1)
    raised = nab > 0 and thr0 <= lim
    hl = M.hlast(cnt[:nab]) if nab else 0
    dw36 = hl if world.h_last else max(max(cnt, default=0) - 2, 0) + 1
    buf = [0] * 59
    buf[36], buf[38] = dw36, 0x20 if raised else 0
    return timeline_text(thr0, need, cnt), buf


def write_job(d: pathlib.Path, rows: list, name, stage, sset, P, knobs, args, rc, cls, text, buf, note="-"):
    (d / f"{name}.txt.gz").write_bytes(gzip.compress(("probe x: ok\n" * 3 + text).encode()))
    (d / f"{name}.dmesg.gz").write_bytes(gzip.compress(b""))
    if buf is not None:
        (d / f"{name}.after.buf09.bin.gz").write_bytes(gzip.compress(struct.pack("<59I", *buf)))
    rows.append("\t".join((name, stage, sset, "safe", P, knobs, "-", args, str(rc), cls, note)))
    (d / "cases.tsv").write_text(HDR + "\n".join(rows) + "\n")


def load_table(stage):
    rows = []
    for ln in (R3 / "tables" / f"{stage}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            f = ln.split("|", 6)
            rows.append(dict(name=f[0], set=f[1], P=f[3], knobs=f[4].split(), args=f[6]))
    return rows


def knob(row, key):
    return next((k.split(":", 1)[1] for k in row["knobs"] if k.startswith(key + ":")), None)


def resolve_P(row, state):
    """The runner's P resolution: (P hex string or None, why).  state: {'obs': {G: {thr0: cls}}, 'cal': {G: dict(need, nparts)}}."""
    P = row["P"]
    if re.fullmatch(r"-|0x[0-9a-f]+", P):
        return P, ""
    kind, g, *off = P.split(":")
    obs = state["obs"].get(g, {})
    if kind == "B":
        t, why = dpm3.pick(obs)
        return (hex(t + 0x22), "") if t is not None else (None, f"bisect {why}")
    lo, hi, why = dpm3.bracket(obs)
    if why == "not monotone":
        return None, "not monotone"
    base = lo if kind == "L" else hi
    if base is None:
        return None, f"no {'raise' if kind == 'L' else 'silent'} cell in group {g}"
    t = base + (int(off[0]) if off else 0)
    return hex(t + 0x22), ""


def simulate(stage, world: World, out: pathlib.Path, state=None):
    """Walk the frozen table of `stage` as run/run_stage.sh does, writing the kept directory `out`.  `state` carries the observations of
    earlier stages (g-c4's group for g-c6 and g-c7).  Returns (state, stopped) where stopped is None or the stop text."""
    out.mkdir(parents=True, exist_ok=True)
    state = state if state is not None else dict(obs={}, cal={})
    owned = {knob(r, "obs") for r in load_table(stage) if knob(r, "obs")}
    for g in owned:
        state["obs"][g] = {}
    rows, stopped, gated = [], None, False
    for r in load_table(stage):
        name = r["name"]
        cal = knob(r, "cal")
        P, why = resolve_P(r, state)
        thr0 = int(P, 16) - 0x22 if P not in (None, "-") else None
        skip = None
        if gated:
            skip = "gate closed"
        elif P is None:
            skip = why
        elif knob(r, "fit") and thr0 is not None and (state["cal"].get(knob(r, "fit")) or {}).get("need") is not None \
                and 2 * thr0 >= state["cal"][knob(r, "fit")]["need"]:
            skip = f"2 thr0 {2 * thr0:#x} not below the page need {state['cal'][knob(r, 'fit')]['need']:#x}"
        if skip:
            write_job(out, rows, name, stage, r["set"], P or "-", " ".join(r["knobs"]), r["args"], "", "skipped", "x" * 30, None, skip)
            continue
        if P == "-":                                           # a depth job: not simulated here
            continue
        text, buf = job_reading(world, r["args"], thr0)
        write_job(out, rows, name, stage, r["set"], P, " ".join(r["knobs"]), r["args"], 3, "ok", text, buf)
        j = dpm3.read_job(dpm3.Kept(out), name)
        c = dpm3.cls_of(j)
        if cal:
            state["cal"][cal] = dict(need=j["need"], nparts=j["nparts"])
            g = knob(r, "gate")
            if g is not None and j["nparts"] > int(g):
                gated = True
        o = knob(r, "obs")
        if o:
            state["obs"].setdefault(o, {})[thr0] = c
        want = knob(r, "ctl")
        if want and c != want:
            stopped = f"control {name} read {c}, wanted {want}"
            break
    return state, stopped


def named_world(spec: str) -> World:
    """A World from the FAKE_WORLD environment string of tests/run_mock.sh: comma separated key=value:
    lim2048 (default 0xd4: LT), lim4096 (0x351), mode lt|ctx (the other targets by LT of the target / of the context), full (the limit of
    a --tri-full job, default = the target's), needfull (the page need of a --tri-full job), hl true|false (dword 36 follows H-last)."""
    kv = dict(p.split("=", 1) for p in spec.split(",") if p)
    lim2048, lim4096 = int(kv.get("lim2048", "0xd4"), 0), int(kv.get("lim4096", "0x351"), 0)
    mode, full = kv.get("mode", "lt"), (int(kv["full"], 0) if "full" in kv else None)

    def limit(j):
        if j["full"] and full is not None:
            return full
        w, h = (j["ctx"] if mode == "ctx" else (j["w"], j["h"]))
        if (w, h) == (2048, 2048):
            return lim2048
        if (w, h) == (4096, 4096):
            return lim4096
        return M.lt_last_thr0(w, h)
    need = None
    if "needfull" in kv:
        nf = int(kv["needfull"])
        need = lambda j: nf if j["full"] else 531 * j["w"] * j["h"] // (2048 * 2048)
    return World(limit, need=need, h_last=kv.get("hl", "true") == "true")
