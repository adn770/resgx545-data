#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""guard_blobs.py [--root DIR]: the laptop limits applied to the ASSEMBLED code of every blob and to every table of R3-events.
Exit 0 clean, 1 with one `GUARD:` line a finding.  Run by run/guard_r3.sh; the tests feed it bad blobs and bad tables.

What it checks (the limits of the session):
  * each bins/NAME.blob is exactly what asm/NAME.s assembles to (the landed `fwtask.build_blob_text`, which runs the landed
    verifier), and the source's instructions are the blob's words, one for one;
  * no `str` word at all (the laptop limit is `str` only to 0x0814 and 0x0a78; our tasks use none); `ldr` only of register #81
    (CR_TIMER); no clock register is reachable by either (the landed verifier refuses those);
  * the destination of every register move is decoded from the WORD (not the source text): temporary, sa(n), r20/r21, i(n); the
    sa registers a command may write are exactly r3layout.CMD_SA (alias.s: sa63, sa64, sa65, one command each, none in the
    reader or in A6), no other blob writes any sa; r20, r21, i0, i1 are written only by alias.s command 6 (A6); pclink only by the
    patched continue triple (the verifier) and one triple an entry;
  * the tables: rows only A0-A6, B0-B2, K7 (A7, A8, B3 do not exist); the command of a row is its own; the `sa` set of a row is the
    set the blob's command writes, within sa63/sa64/sa65; skip counts 0, 1, 5; the hold n is 1508279 (S2b's 90 ticks); kick modes
    none, misc1, xfer2; arm lines from the allow-list; no knob, no register, no trc in any table.
"""
import json
import os
import pathlib
import re
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R3 = HERE.parent
sys.path.insert(0, str(R3 / "gen"))
import r3layout as L  # noqa: E402
import r3blobs as B  # noqa: E402

fw = B.fwtask
TEMP_MASK = (0x1FF << 21) | (1 << 51)
ARMS = {"slots=0x1 entry=0", "slots=0xf entry=0,1,2,3"}
ROWS = {"a": {"A0", "A1", "A2", "A3", "A4", "A5", "A6"}, "b": {"B0", "B1", "B2"}, "k7": {"K7"}}
BLOB_OF = {"a": "alias", "b": "ring_skip", "k7": "ring_hold"}
SKIPS = {"B0": 0, "B1": 1, "B2": 5}


def _ref():
    """{destination bits of a mov reg word: (bank, index)} from reference assemblies of `mov rN, r11` and `mov saN, r11`."""
    ref = {}
    for bank, base in (("r", 0), ("sa", 0), ("i", 124)):
        for n in range(128 if bank != "i" else 4):
            try:
                w = fw.assemble_text(f"mov {bank}{n}, r11")[0]
            except Exception:
                continue
            ref.setdefault(w & TEMP_MASK, ("r" if bank == "i" else bank, n + base))
    return ref


REF = _ref()


def dest_of(w):
    """('sa', n), ('i', n), ('r20',), ('r21',), ('temp', n) or ('unknown',) of a MOVREG word."""
    d = REF.get(w & TEMP_MASK)
    if d is None:
        return ("unknown",)
    bank, n = d
    if bank == "sa":
        return ("sa", n)
    if n in (20, 21):
        return (f"r{n}",)
    if n >= 124:
        return ("i", n - 124)
    return ("temp", n)


def label_ranges(text):
    """{label: (first instruction index, last + 1)} of a source (a label runs to the next label)."""
    idx, cur, out, last = 0, None, {}, None
    for _, lab, s in B.code_lines(text):
        if lab:
            if cur is not None:
                out[cur] = (out[cur][0], idx)
            cur = lab
            out[cur] = (idx, idx)
        elif not s.startswith("@"):
            idx += 1
    if cur is not None:
        out[cur] = (out[cur][0], idx)
    return out


def scan(text, blob, regs=None):
    """The findings about one assembled blob as a dict (see keys)."""
    regs = regs or fw.load_regs()
    p = fw.parse_blob(blob)
    words = p.words
    lines = B.instructions(text)
    f = {"problems": [], "str": 0, "ldr": set(), "sa_by_cmd": {}, "sa_all": set(), "special_writes": {}, "pclink": 0}
    if len(lines) != len(words):
        f["problems"].append(f"source has {len(lines)} instructions, the blob {len(words)} words")
        return f
    cmd_of = {}
    for lab, (a, b) in label_ranges(text).items():
        m = re.fullmatch(r"c(\d)([a-z]\w*)?", lab)
        if m:
            for i in range(a, b):
                cmd_of[i] = int(m.group(1))
    for i, w in enumerate(words):
        kind, name = fw.classify(w)
        if kind == "STR":
            f["str"] += 1
            f["problems"].append(f"word {i}: a str ({lines[i]})")
        elif kind == "LDR":
            idx = fw.reg_index(w)
            f["ldr"].add(idx)
            if idx != 81:
                f["problems"].append(f"word {i}: ldr of register #{idx} ({lines[i]}); only #81 (CR_TIMER) is allowed")
        elif kind == "MOVPCLINK":
            f["pclink"] += 1
        elif kind == "MOVREG":
            d = dest_of(w)
            src_dest = B.writes_of([lines[i]])
            if d[0] == "sa":
                f["sa_all"].add(f"sa{d[1]}")
                f["sa_by_cmd"].setdefault(cmd_of.get(i), set()).add(f"sa{d[1]}")
                if src_dest != [f"sa{d[1]}"]:
                    f["problems"].append(f"word {i}: an sa{d[1]} write the source line does not show ({lines[i]})")
            elif d[0] in ("r20", "r21", "i"):
                nm = d[0] if d[0] != "i" else f"i{d[1]}"
                f["special_writes"].setdefault(cmd_of.get(i), set()).add(nm)
            elif d[0] == "unknown":
                f["problems"].append(f"word {i}: a register move to a bank the guard cannot decode ({lines[i]})")
    return f


def check_blob(name, text, blob, policy, regs=None):
    """Problems of one blob against its policy: policy["cmd_sa"] = {command: set of sa} for alias.s, None: no sa write at all;
    policy["special_ok_cmd"] = the one command allowed to write r20, r21, i0, i1 (6), or None."""
    regs = regs or fw.load_regs()
    out = []
    try:
        if fw.build_blob_text(text, regs) != blob:
            out.append(f"{name}: the blob is not what its source assembles to")
    except fw.VerifyError as e:
        out.append(f"{name}: the landed verifier refuses the source: {e}")
    try:
        bad = fw.verify_blob(blob, regs)
    except Exception as e:
        bad = [repr(e)]
    if bad:
        out.append(f"{name}: the landed verifier refuses the blob: {bad[:2]}")
    try:
        f = scan(text, blob, regs)
    except Exception as e:
        return out + [f"{name}: the scan failed: {e!r}"]
    out += [f"{name}: {x}" for x in f["problems"]]
    if policy["cmd_sa"] is None:
        if f["sa_all"]:
            out.append(f"{name}: writes {sorted(f['sa_all'])}; this blob may write no sa register")
    else:
        if not f["sa_all"] <= L.SA_ALLOWED:
            out.append(f"{name}: writes {sorted(f['sa_all'] - L.SA_ALLOWED)}; only {sorted(L.SA_ALLOWED)} are allowed")
        got = {c: sorted(s) for c, s in f["sa_by_cmd"].items() if c is not None}
        want = {c: sorted(s) for c, s in policy["cmd_sa"].items() if s}
        if got != want:
            out.append(f"{name}: sa writes by command are {got}, not {want}")
        if None in f["sa_by_cmd"]:
            out.append(f"{name}: an sa write outside any command block")
    for c, s in f["special_writes"].items():
        if c is None or c != policy["special_ok_cmd"]:
            out.append(f"{name}: writes {sorted(s)} in {'command ' + str(c) if c is not None else 'the common code'}; only command "
                       f"{policy['special_ok_cmd']} may")
    ent = len(fw.parse_blob(blob).entries)
    if f["pclink"] != ent:
        out.append(f"{name}: {f['pclink']} pclink writes for {ent} entries (only the continue triple, once an entry)")
    return out


def policy_of(name):
    return {"alias": {"cmd_sa": {c: set(v) for c, v in L.CMD_SA.items()}, "special_ok_cmd": L.CMD_A6},
            "ring_skip": {"cmd_sa": None, "special_ok_cmd": None},
            "ring_hold": {"cmd_sa": None, "special_ok_cmd": None}}[name]


def check_tables(tables, binfo):
    """Problems of the job tables ({stage: table}) against blobs.json's info."""
    out = []
    for st, t in tables.items():
        if t.get("stage") != st or t.get("blob") != BLOB_OF[st]:
            out.append(f"table {st}: stage or blob wrong")
        if t.get("arm") not in ARMS:
            out.append(f"table {st}: arm line {t.get('arm')!r} is not on the allow-list")
        if int(t.get("stop_budget", 1)) != 1:
            out.append(f"table {st}: stop budget is not 1")
        text = json.dumps(t)
        if re.search(r"trc|kreg|kpoke|alias_skip|clk|CLK|hold_recovery|render_pb_pages|knob|\"A7\"|\"A8\"|\"B3\"", text):
            out.append(f"table {st}: a forbidden word (trc, kreg, kpoke, a knob, a clock register, or a row A7/A8/B3)")
        for j in t["jobs"]:
            n, row = j.get("name"), j.get("row")
            if row not in ROWS[st]:
                out.append(f"{st}/{n}: row {row} is not an approved row")
                continue
            if st == "a":
                want = dict(zip(("A0", "A1", "A2", "A3", "A4", "A5", "A6"), (0, L.CMD_A1, L.CMD_A2, L.CMD_A3, L.CMD_A4, L.CMD_A5, L.CMD_A6)))[row]
                if j["cmd"] != want:
                    out.append(f"{st}/{n}: command {j['cmd']} is not row {row}'s ({want})")
                blob_sa = sorted(binfo["alias"]["cmd_sa"].get(str(j["cmd"]), []))
                if sorted(j["sa"]) != blob_sa or not set(j["sa"]) <= L.SA_ALLOWED:
                    out.append(f"{st}/{n}: sa set {j['sa']} is not what the blob's command {j['cmd']} writes ({blob_sa})")
                if (j["read_1200"] or j["restore63"]) and row != "A1":
                    out.append(f"{st}/{n}: the 1200 ms reader and the sa63 restore belong to A1")
            elif st == "b":
                if j["skip"] != SKIPS[row] or j["window"] != 2:
                    out.append(f"{st}/{n}: skip {j['skip']} / window {j['window']} is not row {row}'s")
            else:
                if j["kick"] not in ("none", "misc1", "xfer2") or j["n"] != L.n_for_ticks(L.K7_HOLD_TICKS) or j["window"] != 2:
                    out.append(f"{st}/{n}: kick mode, n or window outside the allow-list")
    return out


def run(root):
    root = pathlib.Path(root)
    out = []
    binfo = json.loads((root / "bins" / "blobs.json").read_text())
    regs = fw.load_regs()
    for name in ("alias", "ring_skip", "ring_hold"):
        text = (root / "asm" / f"{name}.s").read_text()
        blob = (root / "bins" / f"{name}.blob").read_bytes()
        out += check_blob(name, text, blob, policy_of(name), regs)
        if binfo[name]["str"] != 0:
            out.append(f"{name}: blobs.json counts a str")
    tabs = {st: json.loads((root / "tables" / f"{st}.json").read_text()) for st in ROWS}
    out += check_tables(tabs, binfo)
    return out


def main(argv):
    root = pathlib.Path(argv[argv.index("--root") + 1]) if "--root" in argv else R3
    problems = run(root)
    for p in problems:
        print("GUARD: " + p)
    if not problems:
        print("guard_blobs: clean (3 blobs, 3 tables)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
