# SPDX-License-Identifier: MIT
"""ops_k0.py: the K0 ops of the R3k runner (the re-baseline on the new module).  A mixin of Runner.

`defaults` (stage k0f): after the debugfs reset, every file of r3layout.K0F_FILES exists and the knobs read their defaults
(r3layout.K0F_DEFAULTS), `kicker` reads in the kernel's format, `kregnow` lists its six rows and neither clear register.
`tooljob` (stage k0t): one job of L1 (g-dd dd-p1, a geometry job: 64x64 triangle with made vertices) and one of L2 (q-t
t-ctl-green-16x16, a pixel job), exactly the arguments those runs used, through their pinned tool (~/sgxfive-test-r1, sha256 in
TOOLR1.sha256); stock firmware, a reset before each; the outputs are compared with the kept L1 and L2 ones (r3layout.GD_FROZEN, PX_FROZEN).
"""
import hashlib
import os
import pathlib
import re
import subprocess
import time

import r3layout as L
import fwtask_run as FR
from r3common import Stop


def _sha(b):
    return hashlib.sha256(b).hexdigest()


class K0Ops:
    def check_defaults(self, j, spec, row):
        if list(j.get("files", [])) != list(L.K0F_FILES) or j.get("defaults") != L.K0F_DEFAULTS:
            raise Stop(7, f"{j['name']}: the files or the defaults are not the frozen ones")

    def defaults_job(self, j, rec):
        self.pre_reset_arm(j, rec)
        rec["srcversion"] = {"loaded": open(SRCV_PATH_FN()).read().strip(), "installed": FR.sh("modinfo -F srcversion gma500_gfx", check=False).strip()}
        rec["files"] = {f: os.path.exists(f"{FR.D}/{f}") for f in j["files"]}
        rec["defaults"] = {name: FR.rd(name).strip() for name in j["defaults"]}
        rec["kicker"] = self.kicker_read()
        text = FR.rd("kregnow")
        rows = [(int(m.group(1), 16), int(m.group(2), 16)) for m in (re.match(r"(0x[0-9a-f]+) (0x[0-9a-f]+)$", ln) for ln in text.splitlines()) if m]
        rec["kregnow"] = {"rows": rows, "raw": text[:400]}
        rec["rc"] = 0
        self.check_tick(rec, "after-defaults")

    def check_tooljob(self, j, spec, row):
        n = j["name"]
        if j.get("args") != spec["args"] or j.get("tool") != spec["tool"] or j.get("frozen") != spec["frozen"]:
            raise Stop(7, f"{n}: the tool arguments or the frozen outcome are not row {row}'s")

    def tooljob_job(self, j, rec):
        self.pre_reset_arm(j, rec)
        progs = pathlib.Path(__file__).resolve().parent.parent / "bins" / "progs"
        work = self.out / f"work-{j['name']}"
        (work / "dump").mkdir(parents=True, exist_ok=True)
        args = [a.replace("$S", str(progs)).replace("$W", str(work)) for a in j["args"]]
        rec["status2_pre"] = self.status2()
        p = subprocess.Popen([self.tool_r1] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True)
        try:
            o, _ = p.communicate(timeout=120)
            rec["tool_rc"] = p.returncode
        except subprocess.TimeoutExpired:
            p.kill()
            o, _ = p.communicate()
            rec["tool_rc"] = "timeout"
        o = o or ""
        (self.out / f"{j['name']}.tool.txt").write_text(o)
        rec["tool_tail"] = o[-300:]
        rec["status2_post"] = self.status2()
        lines = o.splitlines()
        rec["o0_lines"] = [ln.split(": ", 1)[1] for ln in lines if re.match(r"probe \S+: o0 ", ln)]
        keep = [ln for ln in lines if re.match(r"probe \S+: (o0 mixed|row \d+:)", ln)]
        rec["lines_sha256"] = _sha(("\n".join(keep) + "\n").encode()) if keep else None
        rec["dump_sha256"] = {f.name: _sha(f.read_bytes()) for f in sorted((work / "dump").glob("*"))}
        rec["bad_output"] = [ln[:160] for ln in lines if re.search(r"FAIL|Traceback|hung|faulted|BIF fault", ln)]
        rec["rc"] = 0
        self.check_tick(rec, "after-tool")

    def classify_tooljob(self, j, rec):
        if rec.get("rc") is None:
            rec["class"] = "void"
        elif not rec["alive"].get("advancing"):
            rec["class"] = "tickstop"
        elif rec.get("tool_rc") == "timeout":
            rec["class"] = "no-answer"
        elif not rec["health"].get("ok") or rec["log_bad"] or rec.get("bad_output"):
            rec["class"] = "unhealthy"
        elif rec.get("tool_rc") != 0:
            rec["class"] = "trigfail"
        else:
            rec["class"] = "ok"
        return True


def SRCV_PATH_FN():
    return os.environ.get("R3_SRCV_PATH", "/sys/module/gma500_gfx/srcversion")
