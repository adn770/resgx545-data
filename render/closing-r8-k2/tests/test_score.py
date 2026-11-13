# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept records it must hold on and must fail on.

- the mock's worlds (tests/kept.py): model holds H-WO, H-CC-NEW and H-EDM-NONE on both stages and
  refutes their rivals; edmclient holds H-EDM-CLIENT; rival holds H-WO-NONE and H-CC-STALE;
- r8-geo's lesson: a knob row the kernel rejected (`job: rejected` with a diff line, read ok under
  expectdiff) is cannot tell, never held nor FAILED; a row without its PTE line is cannot tell;
  a fault outside the mapping and a hang are read and FAIL every hypothesis;
- the hardware's own records the controls are frozen on (pinned at the data commit): r7-rp's
  health fill and triangle pass, the tool's isolation (render/client-jobs) passes, and
  copy-addresses' copy, whose source sits behind a page (0x3e002000), FAILS the copy control
  (its hash alone would pass it); a control that faulted or was rejected FAILS."""
import os
import re
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, HERE)
import kitscore as K  # noqa: E402
import kept as KD  # noqa: E402
import score as S  # noqa: E402

DATA = tomllib.load(open(os.path.join(KP, "session.toml"), "rb"))["freeze"]["data"]
R7 = "render/closing-r7-rp/out/20261112-205431/p7-rd/"


def score(stage, d):
    _, rows, lines, summ = S.verdicts(stage, str(d))
    return "\n".join(lines + summ)


def summary(text, stage, group, h):
    m = re.search(rf"^SUMMARY: {stage} {group} {h}: (.*)$", text, re.M)
    assert m, (stage, h, text)
    return m[1]


def held(s):
    return "rows decided)" in s and "not supported" not in s and not s.startswith(("cannot", "controls"))


def test_model_world_holds_the_frozen_hypotheses(tmp_path):
    for st in ("xf", "tri"):
        t = score(st, KD.from_world(st, str(tmp_path / st)))
        assert "FAILED (" not in "\n".join(ln for ln in t.splitlines() if ln.startswith("CONTROL")), t
        assert held(summary(t, st, "WRITEONLY", "H-WO")) and "(2 of 2 rows decided)" in t
        assert held(summary(t, st, "CACHECONSISTENT", "H-CC-NEW"))
        assert held(summary(t, st, "EDMPROTECT", "H-EDM-NONE"))
        for h in ("H-WO-NONE", "H-WO-ALL"):
            assert "not supported" in summary(t, st, "WRITEONLY", h)
        assert "not supported" in summary(t, st, "CACHECONSISTENT", "H-CC-STALE")
        assert "not supported" in summary(t, st, "EDMPROTECT", "H-EDM-CLIENT")


def test_edmclient_and_rival_worlds_flip_their_verdicts(tmp_path):
    for st in ("xf", "tri"):
        t = score(st, KD.from_world(st, str(tmp_path / ("e" + st)), ("edmclient",)))
        assert held(summary(t, st, "EDMPROTECT", "H-EDM-CLIENT"))
        assert "not supported" in summary(t, st, "EDMPROTECT", "H-EDM-NONE")
        r = score(st, KD.from_world(st, str(tmp_path / ("r" + st)), ("rival",)))
        assert held(summary(r, st, "WRITEONLY", "H-WO-NONE"))
        assert "not supported" in summary(r, st, "WRITEONLY", "H-WO")
        assert held(summary(r, st, "CACHECONSISTENT", "H-CC-STALE"))


def _replace(d, name, out=None, dmesg=None, rc=None, cls=None):
    """Rewrite one kept row of a stage directory with new text."""
    rows = K.rows(d, "cases.tsv")
    r = rows[name]
    if out is not None:
        KD._gz(os.path.join(d, name + ".txt"), out)
    if dmesg is not None:
        KD._gz(os.path.join(d, name + ".dmesg"), dmesg)
    lines = open(os.path.join(d, "cases.tsv")).read().splitlines(True)
    with open(os.path.join(d, "cases.tsv"), "w") as f:
        for ln in lines:
            fs = ln.rstrip("\n").split("\t")
            if fs[0] == name:
                fs[7] = str(rc if rc is not None else r["rc"])
                fs[8] = cls or r["class"]
                ln = "\t".join(fs) + "\n"
            f.write(ln)


def test_a_rejected_job_reads_nothing(tmp_path):
    d = KD.from_world("xf", str(tmp_path / "xf"))
    rej = ("programs asm\njob: rejected (Invalid argument)\ntarget: 64x32 hash 0x377096476db13725\n"
           "diff: 2048 of 2048 pixels, first (0, 0) 0xdeadbeef expected 0xff336699\noutside: 0 dwords\n")
    _replace(d, "xf-wo-fill", out=rej, rc=1, cls="ok")
    t = score("xf", d)
    assert re.search(r"^READ xf-wo-fill .*: rejected;.*not a reading", t, re.M), t
    for h in ("H-WO", "H-WO-NONE", "H-WO-ALL"):
        assert f"ROW xf-wo-fill {h} (frozen" in t
        assert re.search(rf"^ROW xf-wo-fill {h} \(frozen [a-z]+\): cannot tell$", t, re.M), t
    assert "(1 of 2 rows decided)" in summary(t, "xf", "WRITEONLY", "H-WO")


def test_a_row_without_its_pte_line_cannot_tell(tmp_path):
    d = KD.from_world("tri", str(tmp_path / "tri"))
    _replace(d, "tri-wo-gen", dmesg=KD.KMSG + "sgxfive: BIF fault 0x80010 at 0x3e000002 (PD 0x1) stalls job 7\n")
    t = score("tri", d)
    assert re.search(r"^READ tri-wo-gen .*cannot tell; no PTE line 0x2 at 0x3e000000", t, re.M), t
    assert re.search(r"^ROW tri-wo-gen H-WO \(frozen fault\): cannot tell$", t, re.M)
    # flags other than the frozen ones are no premise either
    d2 = KD.from_world("tri", str(tmp_path / "tri2"))
    _replace(d2, "tri-wo-fb", dmesg=KD.KMSG + "sgxfive: vm_map 0x3e001000 +0x5000: PTE flags 0x12 (x)\n")
    assert re.search(r"^ROW tri-wo-fb H-WO \(frozen exact\): cannot tell$", score("tri", d2), re.M)


def test_a_fault_elsewhere_or_a_hang_fails_every_hypothesis(tmp_path):
    d = KD.from_world("xf", str(tmp_path / "xf"))
    _replace(d, "xf-wo-copy", dmesg=KD.KMSG + "sgxfive: vm_map 0x3e001000 +0x3000: PTE flags 0x6 (x)\n"
             + KD.KMSG + "sgxfive: BIF fault 0x80010 at 0x3e004002 (PD 0x1) stalls job 7\n")
    t = score("xf", d)
    assert re.search(r"^READ xf-wo-copy .*: fault-elsewhere;.*matches no frozen hypothesis", t, re.M), t
    for h in ("H-WO", "H-WO-NONE", "H-WO-ALL"):
        assert re.search(rf"^ROW xf-wo-copy {h} \(frozen [a-z]+\): FAILED$", t, re.M), (h, t)
    tr = KD.from_world("tri", str(tmp_path / "tri"), ("hang",))
    t = score("tri", tr)
    assert re.search(r"^READ tri-wo-gen .*: hang;", t, re.M), t
    assert re.search(r"^ROW tri-wo-gen H-WO \(frozen fault\): FAILED$", t, re.M)


def _section(text, start, stop):
    out = text.split(start, 1)[1]
    return out.split(stop, 1)[0]


def test_hardware_controls(tmp_path):
    fill = KD.git_show("data", DATA, R7 + "begin.fill1.txt.gz")
    tri = KD.git_show("data", DATA, R7 + "begin.health1.txt.gz")
    import gzip
    fill, tri = gzip.decompress(fill).decode(), gzip.decompress(tri).decode()
    copy_all = KD.git_show("data", DATA, "texture/copy-addresses/output.txt").decode()
    copy = _section(copy_all, "#### run 1 plain as built: tex:2 none\n", "## exit")
    jobs = KD.git_show("data", DATA, "render/client-jobs/output.txt").decode()
    iso = _section(jobs, "#### isolation\n", "## exit")
    iso_log = "".join(ln + "\n" for ln in _section(jobs, "## log isolation\n", "####").splitlines())
    tab = {r["name"]: r for r in K.table(KP, "xf")}
    d = str(tmp_path / "xf")
    for n in ("xf-c-fill", "xf-c-addr", "xf-c-end"):
        KD.write_row(d, "xf", tab[n], fill, "", 0)
    KD.write_row(d, "xf", tab["xf-c-copy"], copy, "", 0)
    KD.write_row(d, "xf", tab["xf-c-ro"], iso, iso_log, 0)
    t = score("xf", d)
    for n in ("xf-c-fill", "xf-c-addr", "xf-c-end", "xf-c-ro"):
        assert re.search(rf"^CONTROL {n}: PASS", t, re.M), (n, t)
    assert re.search(r"^CONTROL xf-c-copy: FAILED \(src 0x3e002000 \(frozen 0x3e001000\)\)", t, re.M), t
    assert "0x9b1c0be484ac0d25" in copy        # the hash alone would have passed it
    assert summary(t, "xf", "WRITEONLY", "H-WO").startswith("controls FAILED")
    dt = str(tmp_path / "tri")
    ttab = {r["name"]: r for r in K.table(KP, "tri")}
    for n in ("tri-c", "tri-c-end"):
        KD.write_row(dt, "tri", ttab[n], tri, "", 0)
    t = score("tri", dt)
    assert re.search(r"^CONTROL tri-c: PASS", t, re.M) and re.search(r"^CONTROL tri-c-end: PASS", t, re.M), t
    assert summary(t, "tri", "WRITEONLY", "H-WO").startswith("cannot tell: no row decided")


def test_a_control_that_faulted_or_was_rejected_fails(tmp_path):
    d = KD.from_world("xf", str(tmp_path / "xf"))
    _replace(d, "xf-c-end", out="job: rejected (Invalid argument)\ntarget: 64x32 hash 0xb60c6095080bd325\n"
             "diff: 0 of 2048 pixels\n", rc=1, cls="ok")
    t = score("xf", d)
    assert re.search(r"^CONTROL xf-c-end: FAILED", t, re.M), t
    d2 = KD.from_world("tri", str(tmp_path / "tri"))
    _replace(d2, "tri-c", rc=1, cls="fault")
    assert re.search(r"^CONTROL tri-c: FAILED", score("tri", d2), re.M)


def test_read_files_reads_what_verdicts_reads(tmp_path):
    d = KD.from_world("xf", str(tmp_path / "xf"))
    S.read_files("xf", d)
    assert set(S.REQUIRED["xf"]) == {".txt", ".dmesg", "cases.tsv", "void.tsv", "readings.tsv"}
