# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py (and run/hooks.sh's stop rule) on kept records it must hold
on and must fail on.

- the mock's worlds (tests/kept.py): model holds S9-k2's frozen hypotheses (H-WO-ALL, H-LASTROW,
  H-CC-NEW, H-EDM-WRITE, H-OR) and H-ONLY09, and refutes the rivals; rival flips every one;
- the hardware's own records, pinned at the data commit: E946's kept xf rows (r8-k2) hold
  H-LASTROW at 0x3e002000 and H-EDM-WRITE on the fill, and FAIL H-MAPEND and H-FIRST; E945's
  tri-edm-fb and tri-wo-fb outputs, read as the flags-together row, decide H-EDM-FIRST and
  H-WO-FIRST apart; E745's exact mask row and its buffer 0 fault, E761's overflowing scene and
  its held-out mask, E457's TA3DCtl fault: the bif controls pass on their sources, a held-out
  mask's exact record holds H-ONLY09, a fault outside the left-out buffers FAILS both;
- r8-geo's lesson: a knob row the kernel rejected is cannot tell; a row without its PTE line is
  cannot tell; replicates that disagree are mixed, never held;
- hooks.sh: two `SGX recovery failed: -110` lines since the stage's begin marker stop the stage,
  one does not, nor two before the marker; an overflowed-kept job line is not a refusal."""
import gzip
import os
import re
import shutil
import subprocess
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

CONF = tomllib.load(open(os.path.join(KP, "session.toml"), "rb"))
DATA = CONF["freeze"]["data"]
R8 = "render/closing-r8-k2/out/20261113-032428/"
S1 = "render/closing-s1/out/p-f/"
S1B = "render/closing-s1b/out/p-f/"
# every data file these tests read (each must be a pin of session.toml)
READS = [R8 + "xf/cases.tsv", R8 + "tri/cases.tsv"] + \
    [R8 + f"xf/{n}.{x}.gz" for n in ("xf-c-fill", "xf-c-copy", "xf-c-addr", "xf-c-ro", "xf-wo-fill",
                                     "xf-cc-copy", "xf-edm-fill", "xf-wo-copy") for x in ("txt", "dmesg")] + \
    [R8 + f"tri/{n}.{x}.gz" for n in ("tri-c", "tri-c-end", "tri-wo-fb", "tri-edm-fb") for x in ("txt", "dmesg")] + \
    [S1 + f"{n}.{x}.gz" for n in ("f-12-r1", "f-ctl0-r1") for x in ("txt", "dmesg")] + \
    [S1B + f"{n}.{x}.gz" for n in ("f-dpm-0", "f-dpm-1e-r1") for x in ("txt", "dmesg")] + \
    ["bif/render-directories/kernel.log", "bif/render-directories/output.txt"]


def data(path):
    b = KD.git_show("data", DATA, path)
    return (gzip.decompress(b) if path.endswith(".gz") else b).decode(errors="replace")


def score(stage, d):
    _, rows, lines, summ = S.verdicts(stage, str(d))
    return "\n".join(lines + summ)


def summary(text, stage, group, h):
    pat = rf"^SUMMARY: {stage} {re.escape(group)} {h}: (.*)$" if group else rf"^SUMMARY: {stage} {h}: (.*)$"
    m = re.search(pat, text, re.M)
    assert m, (stage, h, text)
    return m[1]


def held(s):
    return "rows decided)" in s and "not supported" not in s and not s.startswith(("cannot", "controls"))


def row(text, name, group, h):
    m = re.search(rf"^ROW {re.escape(name)} {re.escape(group) + ' ' if group else ''}{h} \(frozen [^)]*\): (.*)$", text, re.M)
    assert m, (name, h, text)
    return m[1]


def table(stage):
    return {r["name"]: r for r in K.table(KP, stage)}


def test_every_data_file_the_tests_read_is_pinned():
    pins = set(CONF["freeze"]["pins"])
    for p in READS:
        assert "data:" + p in pins, p


def test_model_world_holds_the_frozen_hypotheses(tmp_path):
    t = score("xf2", KD.from_world("xf2", str(tmp_path / "xf2")))
    assert "FAILED (" not in "\n".join(ln for ln in t.splitlines() if ln.startswith("CONTROL")), t
    for g, h in (("WRITEONLY", "H-WO-ALL"), ("WO-PAGE", "H-LASTROW"), ("CACHECONSISTENT", "H-CC-NEW"),
                 ("EDM-XF", "H-EDM-WRITE"), ("EDMPROTECT", "H-EDM-CLIENT")):
        assert held(summary(t, "xf2", g, h)), (g, h, t)
    for g, h in (("WO-PAGE", "H-MAPEND"), ("WO-PAGE", "H-FIRST"), ("EDM-XF", "H-EDM-REQ"),
                 ("WRITEONLY", "H-WO")):
        assert "not supported" in summary(t, "xf2", g, h)
    assert "(2 of 2 rows decided)" in summary(t, "xf2", "WO-PAGE", "H-LASTROW")     # held out only
    tt = score("tri2", KD.from_world("tri2", str(tmp_path / "tri2")))
    for g, h in (("WO+EDM", "H-OR"), ("EDM-3D", "H-EDM-WRITE"), ("WRITEONLY", "H-WO-ALL"),
                 ("WO+EDM-PAGE", "H-EDM-FIRST")):
        assert held(summary(tt, "tri2", g, h)), (g, h, tt)
    assert "not supported" in summary(tt, "tri2", "EDM-3D", "H-EDM-3D")
    assert re.search(r"^READ tri-edm-dld \[reading\] .*: exact;", tt, re.M)
    assert "(1 of 1 rows decided)" in summary(tt, "tri2", "EDM-3D", "H-EDM-WRITE")   # not dld
    b = score("bif", KD.from_world("bif", str(tmp_path / "bif")))
    assert held(summary(b, "bif", None, "H-ONLY09")) and "(8 of 8 rows decided)" in b
    assert "not supported" in summary(b, "bif", None, "H-SET")


def test_rival_world_flips_them(tmp_path):
    t = score("xf2", KD.from_world("xf2", str(tmp_path / "xf2"), ("rival",)))
    assert held(summary(t, "xf2", "WRITEONLY", "H-WO")) and held(summary(t, "xf2", "EDM-XF", "H-EDM-REQ"))
    assert held(summary(t, "xf2", "CACHECONSISTENT", "H-CC-STALE"))
    tt = score("tri2", KD.from_world("tri2", str(tmp_path / "tri2"), ("rival",)))
    assert held(summary(tt, "tri2", "WO+EDM", "H-CANCEL")) and held(summary(tt, "tri2", "EDM-3D", "H-EDM-3D"))
    b = score("bif", KD.from_world("bif", str(tmp_path / "bif"), ("rival",)))
    assert held(summary(b, "bif", None, "H-SET")) and "not supported" in summary(b, "bif", None, "H-ONLY09")


def kept_from_data(d, stage, pairs, cases_src=None):
    """A kept stage directory of `stage` whose rows NAME take the hardware's record SRC (txt and
    dmesg gz of a kit-format kept dir, or (out, dmesg, rc, class) texts)."""
    tab = table(stage)
    for name, src in pairs.items():
        if isinstance(src, tuple):
            out, dm, rc, cls = src
        else:
            out, dm = data(src + ".txt.gz"), data(src + ".dmesg.gz")
            rc, cls = cases_src[name] if cases_src else (0, None)
        KD.write_row(d, stage, tab[name], out, dm, rc, cls)
    return d


def r8_cases(stage):
    out = {}
    for ln in data(R8 + f"{stage}/cases.tsv").splitlines()[1:]:
        f = ln.split("\t")
        out[f[0]] = (int(f[7]), f[8])
    return out


def test_e946s_kept_rows(tmp_path):
    c = r8_cases("xf")
    names = ["xf-c-fill", "xf-c-copy", "xf-c-addr", "xf-c-ro", "xf-wo-fill", "xf-cc-copy",
             "xf-edm-fill", "xf-wo-copy"]
    d = kept_from_data(str(tmp_path / "xf2"), "xf2", {n: R8 + "xf/" + n for n in names}, c)
    t = score("xf2", d)
    for n in ("xf-c-fill", "xf-c-copy", "xf-c-addr", "xf-c-ro"):
        assert re.search(rf"^CONTROL {n}: PASS", t, re.M), (n, t)
    assert re.search(r"^CONTROL xf-c-end: cannot tell \(did not run\)", t, re.M)
    assert re.search(r"^READ xf-wo-fill \[repeat\] .*: fault@0x3e002000;", t, re.M), t
    assert row(t, "xf-wo-fill", "WO-PAGE", "H-LASTROW") == "held"
    assert row(t, "xf-wo-fill", "WO-PAGE", "H-MAPEND") == "FAILED"
    assert row(t, "xf-wo-fill", "WO-PAGE", "H-FIRST") == "FAILED"
    assert row(t, "xf-wo-fill", "WRITEONLY", "H-WO-ALL") == "held"
    assert row(t, "xf-edm-fill", "EDM-XF", "H-EDM-WRITE") == "held"
    assert row(t, "xf-cc-copy", "CACHECONSISTENT", "H-CC-NEW") == "held"
    assert row(t, "xf-wo-copy", "WRITEONLY", "H-WO") == "held"
    # the held-out-only summaries have no row of E946's: none of its post hoc readings counts
    assert summary(t, "xf2", "WO-PAGE", "H-LASTROW").startswith("cannot tell")
    assert "controls" in summary(t, "xf2", "WRITEONLY", "H-WO-ALL")       # xf-c-end did not run


def test_e945s_records_tell_the_flags_together_apart(tmp_path):
    c = r8_cases("tri")
    for src, held_h, failed_h in (("tri-edm-fb", "H-EDM-FIRST", "H-WO-FIRST"),
                                  ("tri-wo-fb", "H-WO-FIRST", "H-EDM-FIRST")):
        out, dm = data(R8 + f"tri/{src}.txt.gz"), data(R8 + f"tri/{src}.dmesg.gz")
        dm = re.sub(r"PTE flags 0x[0-9a-f]+", "PTE flags 0x12", dm)
        d = str(tmp_path / src)
        kept_from_data(d, "tri2", {"tri-c": R8 + "tri/tri-c", "tri-c-end": R8 + "tri/tri-c-end"}, c)
        kept_from_data(d, "tri2", {"tri-woedm-fb": (out, dm, *c[src])})
        t = score("tri2", d)
        assert re.search(r"^CONTROL tri-c: PASS", t, re.M) and re.search(r"^CONTROL tri-c-end: PASS", t, re.M), t
        assert row(t, "tri-woedm-fb", "WO+EDM", "H-OR") == "held"
        assert row(t, "tri-woedm-fb", "WO+EDM-PAGE", held_h) == "held", t
        assert row(t, "tri-woedm-fb", "WO+EDM-PAGE", failed_h) == "FAILED"
        assert held(summary(t, "tri2", "WO+EDM-PAGE", held_h))


def bif_rec(out_src, dm_src, rc, cls):
    return (data(out_src), data(dm_src), rc, cls)


def test_bif_controls_and_rows_on_the_hardware_records(tmp_path):
    d = str(tmp_path / "bif")
    ok = bif_rec(S1 + "f-12-r1.txt.gz", S1 + "f-12-r1.dmesg.gz", 0, "ok")
    c1 = bif_rec(S1 + "f-ctl0-r1.txt.gz", S1 + "f-ctl0-r1.dmesg.gz", 1, "fault")
    ovf = bif_rec(S1B + "f-dpm-0.txt.gz", S1B + "f-dpm-0.dmesg.gz", 0, "ok")
    ovf1e = bif_rec(S1B + "f-dpm-1e-r1.txt.gz", S1B + "f-dpm-1e-r1.dmesg.gz", 0, "ok")
    log = data("bif/render-directories/kernel.log")
    c9_line = next(ln for ln in log.splitlines() if "BIF fault 0x90400 at 0x32004001" in ln)
    c9 = ("tri: render context for targets up to 64x64\njob: failed: job faulted, context lost "
          "(Input/output error)\ndiff: 4096 of 4096 pixels, first (0, 0) 0xdeadbeef expected 0xff203040\n"
          "tri: FAILED after 0 renders\n", c9_line + "\n", 1, "fault")
    kept_from_data(d, "bif", {"bif-c0": ok, "bif-c9": c9, "bif-1213": ok, "bif-most": ok, "bif-most-r2": c1,
                              "bif-c-ovf": ovf, "bif-most-ovf": ovf1e, "bif-c1": c1, "bif-c0-end": ok})
    t = score("bif", d)
    for n in ("bif-c0", "bif-c9", "bif-c-ovf", "bif-c1", "bif-c0-end"):
        assert re.search(rf"^CONTROL {n}: PASS", t, re.M), (n, t)
    assert row(t, "bif-1213", "", "H-ONLY09") == "held" and row(t, "bif-1213", "", "H-SET") == "FAILED"
    assert re.search(r"^READ bif-most-ovf \[heldout\] .*: exact;", t, re.M), t
    # buffer 0's fault under a mask that keeps buffer 0: matches no hypothesis (fault-elsewhere)
    assert re.search(r"^READ bif-most-r2 \[replicate\] .*: fault-elsewhere;", t, re.M), t
    assert row(t, "bif-most-r2", "", "H-SET") == "FAILED" and row(t, "bif-most-r2", "", "H-ONLY09") == "FAILED"
    assert re.search(r"^REPLICATES bif-most H-ONLY09: mixed", t, re.M), t
    # the ovf control gates only the ovf row; every other control gates every row
    # 1213 and most-ovf held, most mixed (never held), the five rows that did not run cannot tell
    assert summary(t, "bif", None, "H-ONLY09").endswith("(2 of 8 rows decided)")
    # a control read on the wrong record FAILS: the TA3DCtl control on buffer 0's fault
    d2 = str(tmp_path / "bif2")
    kept_from_data(d2, "bif", {"bif-c9": c1})
    assert re.search(r"^CONTROL bif-c9: FAILED \(fstat 0x91000 \(frozen 0x90400\); fpage 0x3000b000", score("bif", d2), re.M)


def _replace(d, name, out=None, dmesg=None, rc=None, cls=None):
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


def test_a_rejected_job_or_a_missing_pte_line_reads_nothing(tmp_path):
    d = KD.from_world("xf2", str(tmp_path / "xf2"))
    rej = ("programs asm\njob: rejected (Invalid argument)\ntarget: 64x16 hash 0x377096476db13725\n"
           "diff: 1024 of 1024 pixels, first (0, 0) 0xdeadbeef expected 0xff336699\noutside: 0 dwords\n")
    _replace(d, "xf-wo-fill-low", out=rej, rc=1, cls="ok")
    _replace(d, "xf-wo-fill-64", dmesg=KD.KMSG + "sgxfive: BIF fault 0x80020 at 0x3e0041f1 (PD 0x1) stalls job 7\n")
    t = score("xf2", d)
    assert re.search(r"^READ xf-wo-fill-low .*: rejected;.*not a reading", t, re.M), t
    assert row(t, "xf-wo-fill-low", "WO-PAGE", "H-LASTROW") == "cannot tell"
    assert re.search(r"^READ xf-wo-fill-64 .*cannot tell; no PTE line 0x2 at 0x3e001000", t, re.M), t
    assert row(t, "xf-wo-fill-64", "WO-PAGE", "H-LASTROW") == "cannot tell"
    assert summary(t, "xf2", "WO-PAGE", "H-LASTROW").startswith("cannot tell")


def hook(tmp_path, dmesg_all, out="job: ok\n", args="tri -n 2", prefix="r9f", run="77-1"):
    jw = tmp_path / "jw"
    jw.mkdir(exist_ok=True)
    (jw / "x.out").write_text(out)
    (jw / "x.dmesg").write_text("")
    (jw / "dmesg.all").write_text(dmesg_all)
    sh = (f'. {KP}/run/hooks.sh; JW={jw}; args="{args}"; dbgs=""; PREFIX={prefix}; RUN={run}; '
          f'STAGE=bif; hook_check x')
    return subprocess.run(["bash", "-c", sh], capture_output=True, text=True, timeout=30).stdout


def test_hooks_stop_on_two_recovery_timeouts(tmp_path):
    begin = "[1.0] resgx545 r9f row begin 77-1\n"
    r110 = "[2.0] gma500 0000:00:02.0: [drm] *ERROR* SGX recovery failed: -110\n"
    assert hook(tmp_path, begin + r110) == ""
    assert "2 'SGX recovery failed: -110' lines" in hook(tmp_path, begin + r110 + r110)
    assert hook(tmp_path, r110 + r110 + begin) == ""                 # an earlier stage's
    assert hook(tmp_path, r110 + "[1.0] resgx545 r9f row begin 66-1\n" + r110) == ""
    ovf = "job: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"
    assert hook(tmp_path, begin, out=ovf + ovf) == ""
    assert "without job: ok" in hook(tmp_path, begin, out="job: ok\njob: rejected (Invalid argument)\n")
    assert "without a job line" in hook(tmp_path, begin, out="diff: 0 of 4096 pixels\n")


def test_hook_readings_are_the_scorers(tmp_path):
    """hooks.sh's hook_reading and score.py's parse read the same keys from a record."""
    for out_src, dm_src in ((S1 + "f-12-r1.txt.gz", S1 + "f-12-r1.dmesg.gz"),
                            (S1 + "f-ctl0-r1.txt.gz", S1 + "f-ctl0-r1.dmesg.gz"),
                            (S1B + "f-dpm-0.txt.gz", S1B + "f-dpm-0.dmesg.gz")):
        jw = tmp_path / "r"
        shutil.rmtree(jw, ignore_errors=True)
        jw.mkdir()
        out, dm = data(out_src), data(dm_src)
        (jw / "x.out").write_text(out)
        (jw / "x.dmesg").write_text(dm)
        got = subprocess.run(["bash", "-c", f". {KP}/run/hooks.sh; JW={jw}; hook_reading x"],
                             capture_output=True, text=True, timeout=30).stdout.split()
        rd = dict(w.split("=", 1) for w in got)
        p = S.parse(out, dm)
        for k in ("job", "hash", "hash2", "renders", "fstat", "fpage"):
            assert rd.get(k) == p.get(k), (out_src, k, rd, p)
        assert rd == {k: v for k, v in KD.reading(out, dm).items()}, (rd, KD.reading(out, dm))


def test_read_files_reads_what_verdicts_reads(tmp_path):
    for st in ("xf2", "tri2", "bif"):
        d = KD.from_world(st, str(tmp_path / st))
        S.read_files(st, d)
        assert set(S.REQUIRED[st]) == {".txt", ".dmesg", "cases.tsv", "void.tsv", "readings.tsv"}
