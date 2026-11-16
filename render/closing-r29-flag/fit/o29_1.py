#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fit/o29_1.py: O29-1 (closing29/plan/rank-round29.md section 1, Q241). Which word of E1072's two
jobs could carry the address of ISP word 0 bit 18's fetch (BIF fault 0xd0400 at page 0,
FAULT_REQ bit 10, the requestor of E764's background program fetch)? Standard library only; reads
t10's library source (resgx545 a581c06, git show) and E1072's kept outputs (data, git show).

The library source is read at session.toml [freeze] resgx545 (pinned); its sgxfive_tri_block and
render_cmd are t10's (a581c06): `git diff a581c06 c057181 -- userspace/libsgxfive/src/render.c`
touches neither function.

A candidate must be (1) a word of BOTH jobs (b18-lib: the library triangle; b18-ramp: E977's ramp
with its depth buffer) whose value is 0 in both, since both faulted at page 0 alike, and (2) a
word whose role is an address a 3D-side fetch reads, at a known scale. The words of a job:

  state block   the library's 18 words (render.c sgxfive_tri_block), poked as blk:N
  render cmd    the 26 register words of the job (render.c render_cmd), poked as cmd:N
  render det.   the kernel's words the 3D kick carries (rd:N), the tool's own: rd:1 (ZLS base),
                rd:11 (ZLS control), rd:12, 13 (depth load, store), rd:14, 15 (stencil load, store)
                (sgxfive-test.c depth_poke at a581c06)

The rule (R29-2 a): f3 is built only if at most two candidates are frozen by name with a scale.

  python3 fit/o29_1.py [DATA_COMMIT]
"""
import gzip
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("RESGX545_REPO", "/Users/jtorra/src/resgx545")
DATA = os.environ.get("RESGX545_DATA_REPO", "/Users/jtorra/src/resgx545-data")
F4 = "render/closing-r18-flag/out/20261114-133536/f4"
# the roles the sources give the zero words (comments of render.c, the tool's depth_poke)
ADDRESS_ROLES = ("_ptr", "base", "exec", "addr", "rd:12", "rd:13", "rd:14", "rd:15", "rd:1")


def show(repo, commit, path, gz=False):
    b = subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], check=True,
                       capture_output=True).stdout
    return (gzip.decompress(b) if gz else b).decode(errors="replace")


def block_words(src):
    """[(index, value expression, comment)] of sgxfive_tri_block's unconditional words."""
    body = src.split("void sgxfive_tri_block(", 1)[1].split("if (p->isp2_set)", 1)[0]
    out = []
    for m in re.finditer(r"blk\[i\+\+\] = ([^;]+);[ \t]*(?:/\*(.*?)\*/)?", body):
        out.append((len(out), m.group(1).strip(), (m.group(2) or "").strip()))
    return out


def cmd_fields(src):
    """{field: expression} of render_cmd's assignments (the rest of the struct is memset 0)."""
    body = src.split("static void render_cmd(", 1)[1].split("\nint sgxfive_tri_scene(", 1)[0]
    body += src.split("void sgxfive_tiling_cmd(", 1)[1].split("\n}", 1)[0]
    return dict(re.findall(r"c->(\w+(?:\[\d\])?) = ([^;]+);", body))


def main(argv):
    cfg = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
    commit = argv[1] if len(argv) > 1 else cfg["freeze"]["data"][:9]
    TOOL = cfg["freeze"]["resgx545"]
    render = show(REPO, TOOL, "userspace/libsgxfive/src/render.c")
    tool = show(REPO, TOOL, "userspace/libsgxfive/tools/sgxfive-test.c")
    lib = show(DATA, commit, f"{F4}/b18-lib.txt.gz", gz=True)
    ramp = show(DATA, commit, f"{F4}/b18-ramp.txt.gz", gz=True)
    faults = [re.search(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)",
                        show(DATA, commit, f"{F4}/{n}.dmesg.gz", gz=True)).groups() for n in ("b18-lib", "b18-ramp")]
    print(f"O29-1 on data {commit}, tool source {TOOL[:7]}")
    print(f"E1072's faults: b18-lib {faults[0][0]} at {faults[0][1]}, b18-ramp {faults[1][0]} at {faults[1][1]}")
    assert faults[0] == faults[1] == ("0xd0400", "0x1")
    cands = []
    print("state block (blk:N), zero words and address words:")
    for i, expr, com in block_words(render):
        zero = expr == "0"
        addr = any(r in expr or r in com for r in ADDRESS_ROLES)
        if zero or addr:
            print(f"  blk:{i} = {expr} /* {com} */: {'zero' if zero else 'non-zero'}, "
                  f"{'an address' if addr else 'no address role'}")
        if zero and addr:
            cands.append(f"blk:{i}")
    f = cmd_fields(render)
    zero_cmd = [k for k, v in f.items() if v.strip() in ("0", "0u")]
    print(f"render cmd: {len(f)} words assigned, zero among them: {zero_cmd or 'none'}; "
          f"address words (pds_exec, stream base, bg pointers) non-zero")
    nrd = len(re.findall(r'depth_poke[(]"rd:1[1-5]?=', tool))
    depth = re.search(r"^depth: (0x[0-9a-f]+) (\d+) pages.*base (0x[0-9a-f]+)", ramp, re.M)
    print(f"render details: b18-lib has no depth buffer ({'depth:' in lib}); b18-ramp's depth "
          f"{depth.group(1)} base {depth.group(3)} (rd:1, rd:12, rd:13 non-zero in it, depth_poke: "
          f"{nrd} rd words) and it faulted alike: "
          "the ZLS words are out; rd:14, rd:15 (stencil) are 0 in both but ZLS addresses "
          "(FAULT_REQ bit 9, E965, E1070), not bit 10's requestor")
    print("bit 10's requestor fetches low memory with no word of the job holding the address "
          "(E363: a data-rows flip of the background pointer faults at 0x1f000) [infer]")
    print(f"candidates (zero in both jobs, an address role, read by bit 10's requestor): "
          f"{', '.join(cands) if cands else 'none'}")
    print("rule: at most two candidates frozen by name with a scale: "
          + ("yes (f3 is built)" if 0 < len(cands) <= 2 else "no (f3 is not built)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
