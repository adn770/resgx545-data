# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer replayed on kept records it must hold on and must fail
on. Kept directories are built in a tmp directory from the frozen predictions (s0's readings as
the runner's hook_reading writes them) and from published kept files read at the frozen data
commit: E1047's f1-ref-a text (the s0 image), E1071's kernel fault lines (r18-flag f2: WRITEONLY
alone on these two reads, the reading H-WO-READ predicts), E1074's f3-k4 line (0x90004 at
0x20008021: H-KIND and H-AXIS's x page, not H-SIZE's), E1103's copies (r25-csc y28-zc, y28-bc:
the two hashes Q010's hypotheses read)."""
import gzip
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
DATA = "/Users/jtorra/src/resgx545-data"
COLS = K.COLUMNS
R18 = "render/closing-r18-flag/out/20261114-133536"
CSC = "render/closing-r25-csc/out/20261115-213805/csc"


def data(path):
    return subprocess.run(["git", "-C", DATA, "show", f"{CFG['freeze']['data']}:{path}"], check=True,
                          capture_output=True).stdout


def gtext(path):
    return gzip.decompress(data(path)).decode()


def kept_dir(root, stage, rows, readings=None, texts=None, dmesg=None):
    """rows: [(name, class)]; readings: {control: {k: v}}; texts/dmesg: {name: str}."""
    d = os.path.join(root, stage)
    os.makedirs(d, exist_ok=True)
    tab = {r["name"]: r for r in K.table(KP, stage)}
    with open(os.path.join(d, "cases.tsv"), "w") as f:
        f.write("\t".join(COLS) + "\n")
        for n, cls in rows:
            r = tab[n]
            rc = {"ok": 1 if "expectdiff" in r["knobs"] else 0, "fault": 3, "hang": 3}[cls]
            f.write("\t".join([n, stage, r["set"], r["risk"], " ".join(r["knobs"]), r["tool"], r["args"],
                               str(rc), cls, "-", "-", "1000"]) + "\n")
    open(os.path.join(d, "void.tsv"), "w").write("\t".join(COLS) + "\n")
    with open(os.path.join(d, "readings.tsv"), "w") as f:
        f.write("name\treads\treading\n")
        for n, kv in (readings or {}).items():
            f.write(f"{n}\t-\t{' '.join(f'{k}={v}' for k, v in kv.items())}\n")
    for n, _ in rows:
        open(os.path.join(d, n + ".txt"), "w").write((texts or {}).get(n, ""))
        open(os.path.join(d, n + ".dmesg"), "w").write((dmesg or {}).get(n, ""))
    return d


def s0_kept(root, change=None):
    p = K.predictions(KP, "s0")
    rd = {n: {k: mv["H-REF"] for k, mv in q.items() if k != "image"} for n, q in p.items()}
    if change:
        rd[change[0]][change[1]] = change[2]
    ref = gtext("render/closing-r14-flag/out/20261114-060824/f1/f1-ref-a.txt.gz")
    return kept_dir(root, "s0", [(r["name"], "ok") for r in K.table(KP, "s0")], rd, {"f1-ref-a": ref})


def bif(stat, addr):
    return f"[1.0] gma500: [drm] *ERROR* sgxfive: BIF fault {stat} at {addr} (PD 0x1) stalls job 7, recovering\n"


HUNG = "[1.0] gma500: [drm] *ERROR* sgxfive: job 9 hung, recovering\n"


def copy_text(which):
    return gtext(f"{CSC}/y28-{'bc' if which == 'bt601' else 'zc'}.txt.gz")


def verdict(out, row, model):
    ln = next(x for x in out if x.startswith(f"ROW {row} {model}:"))
    return ln.rsplit(": ", 1)[1]


def test_s0_controls_pass_on_their_frozen_readings_and_fail_on_one_change(tmp_path):
    d = s0_kept(str(tmp_path / "a"))
    ctl, _ = score.s0_controls(d)
    assert all(ctl.values()) and len(ctl) == 8
    for st in ("f1", "f2", "h1", "h2"):
        assert score.main(["score.py", "gate", st, str(tmp_path / "a")]) == 0
    d2 = s0_kept(str(tmp_path / "b"), ("c10-bn", "hash", "0xd3522437a14b6325"))
    ctl2, _ = score.s0_controls(d2)
    assert ctl2["c10-bn"] is False and sum(ctl2.values()) == 7
    assert score.main(["score.py", "gate", "h1", str(tmp_path / "b")]) == 1
    assert score.main(["score.py", "gate", "f1", str(tmp_path / "b")]) == 0
    d3 = s0_kept(str(tmp_path / "c"), ("c-512", "tadata", "24576"))
    assert score.s0_controls(d3)[0]["c-512"] is False
    assert score.main(["score.py", "gate", "f2", str(tmp_path / "c")]) == 1


def test_gate_closes_on_a_failed_recovery_of_an_earlier_stage(tmp_path):
    root = str(tmp_path / "r")
    s0_kept(root)
    kept_dir(root, "f1", [("q108-both-load", "fault"), ("q108-both-tex", "fault")],
             dmesg={"q108-both-load": bif("0x80200", "0x3e001001") + "SGX recovery failed: -110\n"})
    for st in ("f2", "h1", "h2"):
        assert score.main(["score.py", "gate", st, root]) == 1
    assert score.main(["score.py", "gate", "f1", root]) == 0


def test_f1_holds_on_e1071s_fault_words_and_fails_on_edmprotects(tmp_path):
    root = str(tmp_path / "r")
    s0_kept(root)
    k = {"q108-both-load": gtext(f"{R18}/f2/q108-wo-load.dmesg.gz"),
         "q108-both-tex": gtext(f"{R18}/f2/q108-wo-tex.dmesg.gz")}
    d = kept_dir(root, "f1", [("q108-both-load", "fault"), ("q108-both-tex", "fault")], dmesg=k)
    out = score.score_stage("f1", d, [root])
    for n in k:
        assert verdict(out, n, "H-WO-READ") == "held"
        assert verdict(out, n, "H-EDM-TYPE") == "FAILED"
        assert verdict(out, n, "H-PASS") == "FAILED"
    d = kept_dir(str(tmp_path / "e"), "f1", [("q108-both-load", "fault"), ("q108-both-tex", "ok")],
                 dmesg={"q108-both-load": bif("0xa0200", "0x3e001001")},
                 texts={"q108-both-tex": gtext("render/closing-r14-flag/out/20261114-060824/f1/f1-ref-a.txt.gz")})
    s0_kept(str(tmp_path / "e"))
    out = score.score_stage("f1", d, [str(tmp_path / "e")])
    assert verdict(out, "q108-both-load", "H-EDM-TYPE") == "held"
    assert verdict(out, "q108-both-load", "H-WO-READ") == "FAILED"
    assert verdict(out, "q108-both-tex", "H-PASS") == "held"


def test_f2_reads_e1074s_page_as_h_axis_not_h_size(tmp_path):
    root = str(tmp_path / "r")
    s0_kept(root)
    k4 = gtext(f"{R18}/f3/f3-k4.dmesg.gz")
    assert "BIF fault 0x90004 at 0x20008021" in k4
    d = kept_dir(root, "f2", [("f2-x512", "fault"), ("f2-y512", "fault")],
                 dmesg={"f2-x512": k4, "f2-y512": bif("0x90004", "0x20012021")})
    out = score.score_stage("f2", d, [root])
    assert verdict(out, "f2-x512", "H-KIND") == "held"
    assert verdict(out, "f2-x512", "H-AXIS") == "held"
    assert verdict(out, "f2-x512", "H-SIZE") == "FAILED"
    assert verdict(out, "f2-y512", "H-SIZE") == "held"
    assert verdict(out, "f2-y512", "H-AXIS") == "FAILED"
    s0_kept(str(tmp_path / "x"), ("f2-ctl-256", "tadata", "32768"))
    d = kept_dir(str(tmp_path / "x"), "f2", [("f2-x512", "fault")], dmesg={"f2-x512": k4})
    assert verdict(score.score_stage("f2", d, [str(tmp_path / "x")]), "f2-x512", "H-AXIS") == "cannot tell"


def q010_attempt(root, after, faults=True, hangs=True, ctl_hash=None):
    s0_kept(root)
    kept_dir(root, "f1", [("q108-both-load", "fault" if faults else "ok"), ("q108-both-tex", "fault" if faults else "ok")],
             dmesg={"q108-both-load": bif("0x80200", "0x3e001001"), "q108-both-tex": bif("0x80002", "0x3e003001")})
    end = "hang" if hangs else "ok"
    h1 = [("q010-af", "ok"), ("q010-ld2", "ok"), ("q010-pre", "ok"), ("q010-h1", end), ("q010-p1", "ok"),
          ("q010-h2", end)]
    bt = "0xb6067a95fa98de2d"
    kept_dir(root, "h1", h1, readings={"q010-ld2": {"job": "ok", "hash": bt},
                                         "q010-pre": {"job": "ok", "hash": ctl_hash or bt}},
             texts={n: copy_text(after) for n in ("q010-af", "q010-p1")},
             dmesg={"q010-h1": HUNG, "q010-h2": HUNG})
    return kept_dir(root, "h2", [("q010-p2", "ok"), ("h2-c-a", "ok"), ("h2-c-b", "ok")],
                    texts={"q010-p2": copy_text(after), "h2-c-b": "probe p1131-blue__0: o0 mixed 0xff0000ff x1024\n"})


def test_q010_keep_retires_and_clear_fails_it(tmp_path):
    root = str(tmp_path / "k")
    d = q010_attempt(root, "bt601")
    out = score.score_stage("h1", os.path.join(root, "h1"), [root])
    for n in ("q010-af", "q010-p1"):
        assert verdict(out, n, "H-KEEP") == "held" and verdict(out, n, "H-RECOV-CLR") == "FAILED"
    out = score.score_stage("h2", d, [root])
    assert verdict(out, "q010-p2", "H-KEEP") == "held"
    assert out[-1].endswith("one hypothesis, H-KEEP: RETIRE (R29-3 a)")
    root = str(tmp_path / "c")
    q010_attempt(root, "zeros")
    out = score.q010_rule([root])
    assert out[-1].endswith("one hypothesis, H-RECOV-CLR: RETIRE (R29-3 a)")


def test_q010_needs_its_recoveries_and_its_controls(tmp_path):
    root = str(tmp_path / "n")
    q010_attempt(root, "bt601", faults=False, hangs=False)
    out = score.score_stage("h1", os.path.join(root, "h1"), [root])
    assert verdict(out, "q010-af", "H-KEEP") == "cannot tell"
    assert verdict(out, "q010-p1", "H-KEEP") == "cannot tell"
    assert score.q010_rule([root])[-1].endswith("narrow only")
    root = str(tmp_path / "f")
    q010_attempt(root, "bt601", ctl_hash="0xd3522437a14b6325")
    out = score.score_stage("h1", os.path.join(root, "h1"), [root])
    assert verdict(out, "q010-p1", "H-KEEP") == "cannot tell"
    assert score.q010_rule([root])[-1].endswith("narrow only")


def test_h2_parts_the_deciders_and_its_control_gates(tmp_path):
    root = str(tmp_path / "h")
    s0_kept(root)
    o0 = "probe p1131-blue__0: o0 mixed 0xff0000ff x1024\n"
    rows = [("q010-p2", "ok"), ("h2-c-a", "ok"), ("h2-c-b", "ok"), ("h2-a3", "ok"), ("h2-b1", "ok"), ("h2-b2", "ok"),
            ("h2-b3", "hang"), ("h2-c1", "ok"), ("h2-c2", "ok"), ("h2-c3", "hang")]
    texts = {n: o0 for n, c in rows if c == "ok" and n.startswith("h2")}
    d = kept_dir(root, "h2", rows, texts=texts, dmesg={"h2-b3": HUNG, "h2-c3": HUNG})
    out = score.score_stage("h2", d, [root])
    for n in ("h2-a3", "h2-b3", "h2-c3"):
        assert verdict(out, n, "H-PREV16") == "held"
    assert verdict(out, "h2-b3", "D-PREVADD") == "FAILED" and verdict(out, "h2-a3", "H-ALWAYS") == "FAILED"
    texts.pop("h2-c-b")
    d = kept_dir(str(tmp_path / "g"), "h2", rows, texts=texts, dmesg={"h2-b3": HUNG, "h2-c3": HUNG})
    s0_kept(str(tmp_path / "g"))
    out = score.score_stage("h2", d, [str(tmp_path / "g")])
    assert verdict(out, "h2-b3", "H-PREV16") == "cannot tell"
