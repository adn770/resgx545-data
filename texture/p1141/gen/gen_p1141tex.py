#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""Writes everything of p1141/tex that is generated: probe tables (probes/), staged programs (stage-bins/),
the laptop scripts, cases.json, declared.tsv, predictions-declared.tsv and their sha256.

    ~/src/sgxhumation/.venv/bin/python -B gen/gen_p1141tex.py        (from p1141/tex/; writes nothing elsewhere)

It deletes nothing: a program of an earlier generation under stage-bins/ is overwritten, never removed.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
P = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(P / "recompute"))
sys.path.insert(0, str(pathlib.Path.home() / "src/resgx545/tools/usse-asm"))
sys.path.insert(0, str(pathlib.Path.home() / "src/sgxhumation/debug/wt-phase10/debug/phase11/p1132/gen"))
import build      # noqa: E402  (p1132's: a spec as USSE text)
import cat1141    # noqa: E402
import probe      # noqa: E402
import shell_lib  # noqa: E402
import tex2       # noqa: E402
import tri1141    # noqa: E402

TEMPLATES = P / "templates"
SCRIPTS = {
    "tex-a-lod": ("Q175,Q050", "independent gradient operands (the footprint rule) and fine ladders (the LOD fraction)", 0),
    "tex-b-bilin": ("Q115", "bilinear on random texels: joint or two-stage rounding, x or y first", 0),
    "tex-c-addr": ("Q078,Q176", "T3 level select (28:27), scale (19:18) and bit 10 on sizes and combinations not yet read", 0),
    "tex-d-t0b27": ("Q078", "T0 bit 27 (sRGB to half) on injected texels; the second destination dword; bilinear", 0),
    "tex-e-etc1": ("Q179", "format 27 (ETC1) on new blocks and non-square sizes", 0),
    "tex-f-types": ("Q178", "TEXTYPE 3 at sizes other than 16 x 16", 1),
    "msaa-a-vis": ("Q089,Q138,Q030", "does the ISP walk the even regions of a split grid (visibility count)", 0),
    "msaa-b-te29": ("Q030", "CR_TE_AA 0x40, 0x80, 0xc0 (bit 29 clear): the TA's dumps, kept whatever the image check says", 0),
    "isp-a-guard": ("Q122,Q199,Q202", "the clip band at 1.25 of the target on five sizes where it falls inside the last tile", 0),
    "isp-b-depth": ("Q200", "the depth plane per tile corner: classes with exact, non-dyadic and tie steps", 0),
    "tex-g-types-risky": ("Q178", "RISKY: TEXTYPE 1 and 4 at sizes other than 16 x 16", 1),
    "tex-h-cube": ("Q113", "RISKY: TEXTYPE 2, six cube directions and two third-coordinate sweeps", 1),
    "msaa-c-q140": ("Q140", "RISKY, last: 4x targets that fit or fault the TA data (BIF faults expected)", 1),
}
ORDER = list(SCRIPTS)


def hyp_pixels(c):
    out = {}
    if "pred_pixels" in c:
        for k, px in c["pred_pixels"].items():
            out[k] = tex2.tm.digest(px)
        return out
    for label, rules, opts in c["hyps"]:
        px = tex2.predict(c["spec"], rules, **opts)
        if px is not None:
            out[label] = tex2.tm.digest(px)
    return out


def write_table(tag, cases, tmpl):
    lines = ["# SPDX-License-Identifier: MIT", "# SPDX-FileCopyrightText: 2026 Josep Torra",
             f"# p1141 {tag}: {len(cases)} cases (gen/gen_p1141tex.py)", 'needs = ["render"]', "", "[[probe]]",
             f'name = "p1141-{tag}"',
             f'question = {json.dumps("smp on a 64 x 32 fill, one coordinate rule a pixel: " + tag)}',
             f'source = "{tmpl}"', "coords = true", "pixels = true", "params = { }", 'inputs = ["PRE", "SETUP", "SMP"]',
             "labels = [" + ", ".join(json.dumps(c["label"]) for c in cases) + "]"]
    rows = [build.case_inputs(c["spec"]) for c in cases]
    lines.append("cases = [" + ", ".join("[" + ", ".join(json.dumps(x) for x in r) + "]" for r in rows) + "]")
    f = P / "probes" / f"p1141-{tag}.toml"
    f.parent.mkdir(exist_ok=True)
    f.write_text("\n".join(lines) + "\n")
    return f


def main() -> None:
    (P / "stage-bins").mkdir(exist_ok=True)
    tex = cat1141.all_texture()
    by = collections.OrderedDict()      # one table per (group, template)
    for c in tex:
        by.setdefault((c["group"] + ("" if c["tmpl"] == "tx_map.s" else "-r11"), c["tmpl"]), []).append(c)
    for (tag, tmpl), cases in by.items():
        f = write_table(tag, cases, tmpl)
        ps = probe.load(f)
        assert len(ps) == 1 and len(ps[0].cases) == len(cases)
        probe.build(ps[0], P / "stage-bins", TEMPLATES)
        for i, c in enumerate(cases):
            c["bin"] = f"p1141-{tag}__{i}.bin"
            n = (P / "stage-bins" / c["bin"]).stat().st_size
            assert n % 8 == 0 and n // 8 <= 256, (c["name"], n // 8)
    cases = tex + tri1141.all_tri()
    declared, preds = [], []
    for c in cases:
        if c["kind"] == "probe":
            c["preds"] = hyp_pixels(c)
        for h, sh in c["preds"].items():
            preds.append((c["script"], c["name"], c["set"], h, sh))
        declared.append((c["script"], c["name"], c["set"], c["risk"], c["group"]))
    for sname in ORDER:
        qs, about, every = SCRIPTS[sname]
        rows = []
        for c in cases:
            if c["script"] != sname:
                continue
            one = next(iter(c["preds"].values())) if len(c["preds"]) == 1 and c["kind"] == "probe" else "-"
            if c["kind"] == "probe":
                rows.append((c["name"], "probe", c["bin"], one, c["set"], c["risk"], "-"))
            else:
                rows.append((c["name"], "tri", "-", "-", c["set"], c["risk"], " ".join(c["opts"])))
        (P / f"{sname}.sh").write_text(shell_lib.script(sname, qs, about, rows, every))
    (P / "run-all-1141tex.sh").write_text(runall())
    (P / "stage-p1141tex.sh").write_text(stage())
    (P / "gen" / "cases.json").write_text(json.dumps(
        [{k: v for k, v in c.items() if k not in ("pred_pixels",)} for c in cases], default=str, sort_keys=True))
    (P / "declared.tsv").write_text("script\tcase\tset\trisk\tgroup\n" + "".join("\t".join(r) + "\n" for r in declared))
    (P / "predictions-declared.tsv").write_text(
        "script\tcase\tset\thypothesis\tsha256\n" + "".join("\t".join(r) + "\n" for r in preds))
    cnt = collections.Counter((c["script"], c["risk"]) for c in cases)
    for f in ("declared.tsv", "predictions-declared.tsv"):
        print(f, hashlib.sha256((P / f).read_bytes()).hexdigest(), sum(1 for _ in open(P / f)) - 1, "rows")
    for (s, r), n in sorted(cnt.items(), key=lambda kv: ORDER.index(kv[0][0])):
        print(f"{s:20s} {r:6s} {n:3d} jobs")
    print("jobs", len(cases))


def runall() -> str:
    names = " ".join(ORDER)
    return f"""#!/bin/bash
# run-all-1141tex.sh: the p1141/tex batch on the laptop in the order of plan.md section 6 (safe scripts, then
# the risky ones, one at a time, last), each with its own log. Run it on the laptop after stage-p1141tex.sh has
# put the programs in ~/sgxprobes-stage-1141tex; the tool is ~/sgxfive-test-1138b. It stops after the first
# script that stopped itself (three failed recoveries): read dmesg before another run. No script here writes a
# register (no clock-gate register, no kreg, no /dev/mem write).
set -u
cd "$(dirname "$0")"
OUT=${{OUT:-$HOME/p1141tex-out}}
mkdir -p "$OUT"
for s in {names}; do
	echo "#### $s $(date +%T)"
	bash "./$s.sh" > "$OUT/$s.out" 2>&1
	rc=$?
	echo "rc $rc, $(grep -c '^== ' "$OUT/$s.out") jobs, $(grep -c 'kept ' "$OUT/$s.out") kept, $(grep -c 'MISMATCH' "$OUT/$s.out") declared mismatches"
	grep -E "^## abort|^  health: the plain|^## journalctl" "$OUT/$s.out" | head -4
	[ "$rc" -ne 0 ] && {{ echo "stopped after $s"; break; }}
done
"""


def stage() -> str:
    return """#!/bin/bash
# stage-p1141tex.sh: the programs of the texture scripts (the generator wrote them to stage-bins/ already)
# copied to the laptop's ~/sgxprobes-stage-1141tex. SGX_TARGET_HOST / SGX_TARGET_SSH_OPTS as in the other stage scripts.
set -eu
P=$(cd "$(dirname "$0")" && pwd)
ls "$P"/stage-bins/*.bin | wc -l
if [ -n "${SGX_TARGET_HOST:-}" ]; then
	ssh ${SGX_TARGET_SSH_OPTS:-} "$SGX_TARGET_HOST" 'mkdir -p sgxprobes-stage-1141tex'
	scp -q ${SGX_TARGET_SSH_OPTS:-} "$P"/stage-bins/*.bin "$SGX_TARGET_HOST:sgxprobes-stage-1141tex/"
	echo "copied to $SGX_TARGET_HOST:sgxprobes-stage-1141tex"
fi
"""


if __name__ == "__main__":
    main()
