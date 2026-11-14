# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer replayed on kept records it must hold on and must fail
on. Kept directories are built in a tmp directory from the frozen predictions (s0's readings as
the runner's hook_reading writes them) and from published kept files read at the frozen data
commit: E1047's f1-ref-a text (the image f2's H-EDM-READ predicts), E509's kernel fault lines
(f3's kinds), E756's ix-c and ix32-n texts (h1's H-B24-W32 o0 line)."""
import gzip
import os
import subprocess
import sys
import tomllib

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
DATA = "/Users/jtorra/src/resgx545-data"
COLS = K.COLUMNS


def data(path):
    return subprocess.run(["git", "-C", DATA, "show", f"{CFG['freeze']['data']}:{path}"], check=True,
                          capture_output=True).stdout


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
    ref = gzip.decompress(data("render/closing-r14-flag/out/20261114-060824/f1/f1-ref-a.txt.gz")).decode()
    return kept_dir(root, "s0", [(r["name"], "ok") for r in K.table(KP, "s0")], rd, {"f1-ref-a": ref})


def bif(stat, addr):
    return f"[1.0] gma500: [drm] *ERROR* sgxfive: BIF fault {stat} at {addr} (PD 0x1) stalls job 7, recovering\n"


def lines(stage, d, root):
    return score.score_stage(stage, d, [root])


def verdict(out, row, model):
    ln = next(x for x in out if x.startswith(f"ROW {row} {model}:"))
    return ln.rsplit(": ", 1)[1]


def test_s0_controls_pass_on_their_frozen_readings_and_fail_on_one_change(tmp_path):
    d = s0_kept(str(tmp_path / "a"))
    ctl, _ = score.s0_controls(d)
    assert all(ctl.values()) and len(ctl) == 7
    for st in ("f1", "f2", "f3", "f4", "h1", "h2"):
        assert score.main(["score.py", "gate", st, str(tmp_path / "a")]) == 0
    d2 = s0_kept(str(tmp_path / "b"), ("zv-g5-24", "fb", "0x3e015000"))
    ctl2, _ = score.s0_controls(d2)
    assert ctl2["zv-g5-24"] is False and sum(ctl2.values()) == 6
    assert score.main(["score.py", "gate", "f1", str(tmp_path / "b")]) == 1
    assert score.main(["score.py", "gate", "f2", str(tmp_path / "b")]) == 0


def test_image_of_e1047_is_the_frozen_one_and_a_changed_pixel_fails(tmp_path):
    ref = gzip.decompress(data("render/closing-r14-flag/out/20261114-060824/f1/f1-ref-a.txt.gz")).decode()
    want = K.predictions(KP, "s0")["f1-ref-a"]["image"]["H-REF"]
    assert score.image_sha(ref) == want
    assert score.image_sha(ref.replace("row 0: d0000000", "row 0: d0000001", 1)) != want
    d = s0_kept(str(tmp_path / "c"))
    open(os.path.join(d, "f1-ref-a.txt"), "w").write(ref.replace("row 0: d0000000", "row 0: d0000001", 1))
    assert score.s0_controls(d)[0]["f1-ref-a"] is False


def test_gate_closes_on_a_failed_recovery_of_an_earlier_stage(tmp_path):
    root = str(tmp_path / "r")
    s0_kept(root)
    d = kept_dir(root, "f1", [("q299-g3", "ok"), ("q299-g5", "fault")],
                 dmesg={"q299-g5": bif("0x90200", "0x3e016092") + "SGX recovery failed: -110\n"})
    assert os.path.isdir(d)
    assert score.main(["score.py", "gate", "f2", root]) == 1
    assert score.main(["score.py", "gate", "h2", root]) == 1
    assert score.main(["score.py", "gate", "f1", root]) == 0


def test_f1_ends_and_pages(tmp_path):
    root = str(tmp_path / "r")
    s0_kept(root)
    d = kept_dir(root, "f1", [("q299-g3", "ok"), ("q299-g5", "fault")],
                 texts={"q299-g3": "job: ok\nlayout: fb 0x3e011000\n"},
                 dmesg={"q299-g5": bif("0x90200", "0x3e016092")})
    out = lines("f1", d, root)
    assert verdict(out, "q299-g5", "H-PAST-FAULT") == "held"
    assert verdict(out, "q299-g5", "H-PAST-FAULT-PAGE") == "held"
    assert verdict(out, "q299-g3", "H-PAST-ANY") == "FAILED"
    assert verdict(out, "q299-g5", "H-DROP") == "FAILED"
    # the fault elsewhere: the ends still hold, the page model fails, the other page model fails too
    d2 = kept_dir(str(tmp_path / "r2"), "f1", [("q299-g3", "ok"), ("q299-g5", "fault")],
                  dmesg={"q299-g5": bif("0x90200", "0x3e013092")})
    s0_kept(str(tmp_path / "r2"))
    out2 = lines("f1", d2, str(tmp_path / "r2"))
    assert verdict(out2, "q299-g5", "H-PAST-FAULT") == "held"
    assert verdict(out2, "q299-g5", "H-PAST-FAULT-PAGE") == "FAILED"


def test_f1_is_cannot_tell_when_its_references_failed(tmp_path):
    root = str(tmp_path / "r")
    s0_kept(root, ("zv-c-g3", "zdump", "0" * 64))
    d = kept_dir(root, "f1", [("q299-g3", "ok"), ("q299-g5", "fault")], dmesg={"q299-g5": bif("0x90200", "0x3e016092")})
    out = lines("f1", d, root)
    assert verdict(out, "q299-g5", "H-PAST-FAULT") == "cannot tell"
    assert any(x.startswith("SUMMARY: f1: H-PAST-FAULT: controls FAILED") for x in out)


def test_f2_texture_read_through_needs_e1047s_image(tmp_path):
    root = str(tmp_path / "r")
    s0_kept(root)
    ref = gzip.decompress(data("render/closing-r14-flag/out/20261114-060824/f1/f1-ref-a.txt.gz")).decode()
    rows = [("q108-edm-load", "ok"), ("q108-edm-tex", "ok"), ("q108-wo-load", "fault"), ("q108-wo-tex", "fault")]
    dm = {"q108-wo-load": bif("0x80200", "0x3e001091"), "q108-wo-tex": bif("0x80002", "0x3e003012")}
    d = kept_dir(root, "f2", rows, texts={"q108-edm-tex": ref, "q108-edm-load": "job: ok\n"}, dmesg=dm)
    out = lines("f2", d, root)
    for n, m in (("q108-edm-load", "H-EDM-READ"), ("q108-edm-tex", "H-EDM-READ"), ("q108-wo-load", "H-WO-ALL"),
                 ("q108-wo-tex", "H-WO-ALL")):
        assert verdict(out, n, m) == "held", (n, m)
    assert verdict(out, "q108-wo-load", "H-WO-LOAD-OK") == "FAILED"
    open(os.path.join(d, "q108-edm-tex.txt"), "w").write(ref.replace("row 0: d0000000", "row 0: d0000001", 1))
    assert verdict(lines("f2", d, root), "q108-edm-tex", "H-EDM-READ") == "FAILED"


@pytest.mark.parametrize("stat,addr,kind,one", [("0x90004", "0x20008025", "held", "FAILED"),
                                                ("0x90100", "0x10000012", "FAILED", "held")])
def test_f3_kind_on_e509s_own_fault_lines(tmp_path, stat, addr, kind, one):
    log = \
        data("ta/mtile-fields-risky/kernel.log").decode()
    line = next(ln for ln in log.splitlines() if f"BIF fault {stat} at {addr}" in ln) + "\n"
    root = str(tmp_path / "r")
    s0_kept(root)
    d = kept_dir(root, "f3", [("f3-k4", "fault"), ("f3-k100", "fault")],
                 dmesg={"f3-k4": line, "f3-k100": bif("0x90100", "0x10000012")})
    out = lines("f3", d, root)
    assert verdict(out, "f3-k4", "H-KIND") == kind
    assert verdict(out, "f3-k4", "H-ONE-KIND") == one
    assert verdict(out, "f3-k4", "H-PAGE-END") == "FAILED"     # E509's page on the old layout
    assert verdict(out, "f3-k100", "H-PAGE-END") == "held"


def test_f4_fault_any_needs_one_requestor(tmp_path):
    root = str(tmp_path / "r")
    s0_kept(root)
    d = kept_dir(root, "f4", [("b18-lib", "fault"), ("b18-ramp", "fault")],
                 dmesg={"b18-lib": bif("0x91000", "0x3e002011"), "b18-ramp": bif("0x91000", "0x3e002011")})
    assert verdict(lines("f4", d, root), "b18-ramp", "H-FAULT-ANY") == "held"
    open(os.path.join(d, "b18-ramp.dmesg"), "w").write(bif("0x90100", "0x10000012"))
    assert verdict(lines("f4", d, root), "b18-ramp", "H-FAULT-ANY") == "FAILED"
    assert verdict(lines("f4", d, root), "b18-ramp", "H-NEEDS-BUF") == "FAILED"


def test_h1_on_e756s_kept_texts(tmp_path):
    root = str(tmp_path / "r")
    s0_kept(root)
    ixc = gzip.decompress(data("render/closing-s1b/out/g-e4w/ix-c.txt.gz")).decode()
    ixn = gzip.decompress(data("render/closing-s1b/out/g-e4w/ix32-n-r1.txt.gz")).decode()
    d = kept_dir(root, "h1", [("b24-w32", "ok")], texts={"b24-w32": ixc})
    out = lines("h1", d, root)
    assert verdict(out, "b24-w32", "H-B24-W32") == "held"
    assert verdict(out, "b24-w32", "H-B24-HANG") == "FAILED"
    d = kept_dir(str(tmp_path / "r2"), "h1", [("b24-w32", "ok")], texts={"b24-w32": ixn})
    s0_kept(str(tmp_path / "r2"))
    assert verdict(lines("h1", d, str(tmp_path / "r2")), "b24-w32", "H-B24-W32") == "FAILED"
    d = kept_dir(str(tmp_path / "r3"), "h1", [("b24-w32", "hang")])
    s0_kept(str(tmp_path / "r3"))
    assert verdict(lines("h1", d, str(tmp_path / "r3")), "b24-w32", "H-B24-HANG") == "held"


def test_h2_models_and_its_own_control(tmp_path):
    t = [r["name"] for r in K.table(KP, "h2")]
    m1 = dict(zip(t, ("ok", "ok", "ok", "ok", "hang", "ok", "ok", "hang")))
    texts = {n: "probe p1131-blue__0: o0 mixed 0xff0000ff x1024\n" for n, c in m1.items() if c == "ok"}
    d = kept_dir(str(tmp_path), "h2", list(m1.items()), texts=texts)
    out = lines("h2", d, str(tmp_path))
    assert verdict(out, "h2-a3", "M1-SHAPE") == "held" and verdict(out, "h2-b3", "M1-SHAPE") == "held"
    assert verdict(out, "h2-a3", "H-SCALE") == "FAILED" and verdict(out, "h2-a2", "H-ALT") == "FAILED"
    assert any(x.startswith("SUMMARY: h2: M1-SHAPE: ") and "rows decided" in x and "not supported" not in x
               for x in out)
    d = kept_dir(str(tmp_path / "x"), "h2", [("h2-c-a", "ok"), ("h2-c-b", "hang")])
    out = lines("h2", d, str(tmp_path / "x"))
    assert any(x.startswith("CONTROL h2-c-b") and x.endswith("FAILED") for x in out)


def test_required_and_read_files_agree(tmp_path):
    d = s0_kept(str(tmp_path))
    assert all(v == (".txt", ".dmesg", "cases.tsv", "void.tsv", "readings.tsv") for v in score.REQUIRED.values())
    score.read_files("s0", d)
