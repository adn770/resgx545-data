# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on.

The kept records are E499's rawcond, E529's rawjoin-o, E521's iaddu32 values and E498's iaddu32
tests (the pinned vector files), written as the probe of this session prints them (the packed
fields of a pair, a dword a pair; each value its dword): as their own controls they PASS, swapped
(E529's table read as the a join control, E499's as the o join one) or with E521's values
sign-extended they FAIL. A held-out row printing H-RULE's dwords holds H-RULE and fails its
rivals, one printing H-SETAND's fails H-RULE, a dword changed outside the model fails every model,
a row with no o0 line or past 32 dwords is cannot tell, and a FAILED control turns every SUMMARY
into "controls FAILED"."""
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import progs  # noqa: E402
import rule as R  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")


def kept(tmp, stage, outputs):
    d = tmp / stage
    d.mkdir()
    table = {ln.split("|")[0]: ln.split("|") for ln in open(os.path.join(KP, "tables", stage + ".txt"))
             if ln.strip() and not ln.startswith("#")}
    rows = ["\t".join(COLS)]
    for n, text in outputs.items():
        (d / f"{n}.txt").write_text(text)
        t = table[n]
        rows.append("\t".join([n, stage, t[1], t[2], t[3], t[4], "x", "0", "ok", "-", "-", "0"]))
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text("name\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return d


def score(stage, d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), stage, str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def line(out, kind, name):
    return [ln for ln in out.splitlines() if ln.startswith(f"{kind} {name}:") or
            ln.startswith(f"{kind} {name} (")][0]


def probe_out(name, dw, o0=True):
    out = [f"probe {name}: scratch at 0x3e003000 (64 KiB)"]
    if o0:
        out.append(f"probe {name}: o0 0x00000000 (2048 of 2048)")
    shown = [k for k in sorted(dw) if dw[k] != 0xD0000000 | k // 4]
    out += [f"probe {name}: scratch +0x{k:03x} 0x{dw[k]:08x}" for k in shown[:32]]
    if len(shown) > 32:
        out.append(f"probe {name}: scratch {len(shown) - 32} more changed")
    return "\n".join(out) + "\n"


def kept_table(pin, values):
    """A pair's packed fields from a kept raw table (bit f when the field-f word set p0), with the
    values the session's program stores beside them."""
    pairs, bits = [], {}
    for w, a, b, o0 in progs.kept_cases(pin):
        if (a, b) not in pairs:
            pairs.append((a, b))
        if o0:
            bits[(a, b)] = bits.get((a, b), 0) | 1 << R.fields_of(w)[0]
    dw = dict(values)
    for j, p in enumerate(pairs):
        dw[4 * (2 * j + 1)] = progs.MARK | bits.get(p, 0)
    return dw


def job(name):
    return (progs.utest_job if name.startswith("t-") else progs.uadd_job)(name)


def model(name, m, q=None):
    p = job(name)["preds"]
    out = {}
    for qq, ms in p.items():
        if q is None or qq == q:
            out.update(ms.get(m, {}))
    return out


def test_utest_controls_on_their_kept_tables(tmp_path):
    va = model("t-ctl-and-a", "H-SIM", "values")
    vo = model("t-ctl-and-o", "H-SIM", "values")
    out = score("utest", kept(tmp_path, "utest", {
        "t-ctl-and-a": probe_out("t-ctl-and-a", kept_table(progs.RAWCOND, va)),
        "t-ctl-and-o": probe_out("t-ctl-and-o", kept_table(progs.RAWJOIN, vo)),
        "t-shl-a": probe_out("t-shl-a", model("t-shl-a", "H-RULE", "tests")
                             | model("t-shl-a", "H-SIM", "values"))}))
    assert line(out, "CONTROL", "t-ctl-and-a").endswith("PASS")
    assert line(out, "CONTROL", "t-ctl-and-o").endswith("PASS")
    assert "held H-RULE (tests), H-SIM (values)" in line(out, "ROW", "t-shl-a")
    assert "SUMMARY: utest: tests H-RULE (heldout) (1 of 18 rows decided)" in out
    assert "SUMMARY: utest: tests H-SETAND (heldout) is not supported" in out


def test_utest_controls_swapped_fail(tmp_path):
    va = model("t-ctl-and-a", "H-SIM", "values")
    out = score("utest", kept(tmp_path, "utest", {
        "t-ctl-and-a": probe_out("t-ctl-and-a", kept_table(progs.RAWJOIN, va)),
        "t-ctl-and-o": probe_out("t-ctl-and-o", kept_table(progs.RAWCOND, va)),
        "t-shl-a": probe_out("t-shl-a", model("t-shl-a", "H-RULE", "tests")
                             | model("t-shl-a", "H-SIM", "values"))}))
    assert line(out, "CONTROL", "t-ctl-and-a").endswith("FAILED")
    assert line(out, "CONTROL", "t-ctl-and-o").endswith("FAILED")
    assert "SUMMARY: utest: tests H-RULE (heldout): controls FAILED" in out


def test_utest_rows(tmp_path):
    rows = {}
    for n in ("t-shl-o", "t-iaddu32-o", "t-iadd8-o", "t-asr-a", "t-or7-a", "t-iadd16-a"):
        rows[n] = model(n, "H-RULE", "tests") | model(n, "H-SIM", "values")
    rows["t-rol7-o"] = model("t-rol7-o", "H-AJOIN", "tests") | model("t-rol7-o", "H-SIM", "values")
    rows["t-shr-a"] = model("t-shr-a", "H-SETAND", "tests") | model("t-shr-a", "H-SIM", "values")
    extra = model("t-asr-o", "H-RULE", "tests") | model("t-asr-o", "H-SIM", "values")
    extra[0x40] = 0x12345678
    outs = {n: probe_out(n, d) for n, d in rows.items()}
    outs["t-asr-o"] = probe_out("t-asr-o", extra)
    outs["t-iadd32-a"] = probe_out("t-iadd32-a", model("t-iadd32-a", "H-RULE"), o0=False)
    out = score("utest", kept(tmp_path, "utest", outs))
    for n in ("t-shl-o", "t-iaddu32-o", "t-iadd8-o", "t-asr-a", "t-or7-a", "t-iadd16-a"):
        ln = line(out, "ROW", n)
        assert "held H-RULE (tests)" in ln and "H-AJOIN" not in ln.rsplit(": held ", 1)[1], ln
        assert "H-CHAN0" not in ln.rsplit(": held ", 1)[1] and "H-SETAND" not in ln.rsplit(": held ", 1)[1], ln
    assert "held H-AJOIN (tests)" in line(out, "ROW", "t-rol7-o")
    assert "H-RULE (tests)" not in line(out, "ROW", "t-rol7-o").rsplit(": held ", 1)[1]
    assert "held H-SETAND (tests), H-SIM (values)" in line(out, "ROW", "t-shr-a")
    assert "read +0x" in line(out, "ROW", "t-shr-a")
    assert line(out, "ROW", "t-asr-o").endswith("no frozen model exact")
    assert "changed outside the model: +0x040" in line(out, "ROW", "t-asr-o")
    assert line(out, "ROW", "t-iadd32-a").endswith("no o0 line: cannot tell")
    assert line(out, "ROW", "t-iadd32-o").endswith("not run: cannot tell")
    assert "SUMMARY: utest: tests H-RULE (heldout): cannot tell: no row decided" not in out
    assert "cannot tell: controls" in out             # no control ran: no headline


def test_uadd_on_kept_records(tmp_path):
    e521 = model("u-ctl-e521", "H-E521")
    e498 = model("u-ctl-e498", "H-E498")
    out = score("uadd", kept(tmp_path, "uadd", {
        "u-ctl-e521": probe_out("u-ctl-e521", e521),
        "u-ctl-e498": probe_out("u-ctl-e498", e498),
        "u-imm1": probe_out("u-imm1", model("u-imm1", "H-ZX")),
        "u-c56": probe_out("u-c56", model("u-c56", "H-SX"))}))
    assert line(out, "CONTROL", "u-ctl-e521").endswith("PASS")
    assert line(out, "CONTROL", "u-ctl-e498").endswith("PASS")
    assert line(out, "ROW", "u-imm1").endswith("held H-ZX (dwords)")
    assert line(out, "ROW", "u-c56").endswith("held H-SX (dwords)")
    assert "SUMMARY: uadd: dwords H-ZX (heldout) is not supported" in out
    # E521's values sign-extended: the control fails, every headline with it
    sx = {k: R.iaddu32(a, b, "H-SX") for k, (a, b) in zip(sorted(e521), progs.E521_PAIRS)}
    (tmp_path / "b").mkdir()
    out = score("uadd", kept(tmp_path / "b", "uadd", {
        "u-ctl-e521": probe_out("u-ctl-e521", sx),
        "u-ctl-e498": probe_out("u-ctl-e498", e498),
        "u-imm1": probe_out("u-imm1", model("u-imm1", "H-ZX"))}))
    assert line(out, "CONTROL", "u-ctl-e521").endswith("FAILED")
    assert "SUMMARY: uadd: dwords H-ZX (heldout): controls FAILED" in out


def test_urpt(tmp_path):
    out = score("urpt", kept(tmp_path, "urpt", {
        "u-ctl-rpt": probe_out("u-ctl-rpt", model("u-ctl-e521", "H-E521")),
        "u-rpt2": probe_out("u-rpt2", model("u-rpt2", "H-NOREP")),
        "u-rpt4": probe_out("u-rpt4", model("u-rpt4", "H-ZX-ADV"))}))
    assert line(out, "CONTROL", "u-ctl-rpt").endswith("PASS")
    assert line(out, "ROW", "u-rpt2").endswith("held H-NOREP (dwords)")
    assert "read +0x004=0xa4a5a6a7" in line(out, "ROW", "u-rpt2")
    assert line(out, "ROW", "u-rpt4").endswith("held H-ZX-ADV (dwords)")
    assert "SUMMARY: urpt: dwords H-ZX-ADV (heldout) is not supported: 1 held, 1 FAILED" in out


def test_past_32_dwords_is_cannot_tell(tmp_path):
    d = model("u-imm1", "H-ZX")
    d.update({0x100 + 4 * k: k + 1 for k in range(30)})
    out = score("uadd", kept(tmp_path, "uadd", {"u-imm1": probe_out("u-imm1", d)}))
    assert line(out, "ROW", "u-imm1").endswith("more than 32 dwords changed: cannot tell")
