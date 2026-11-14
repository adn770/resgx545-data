# SPDX-License-Identifier: MIT
"""test_score.py: r14-bif's scorer on kept-record directories built from E1029's kept stores
(zb-c-id: the index loaded, F; zb-c-off: the clear, 1.0) and the twin's texts: it must hold the
coherent models on a coherent run, hold the stale ones and fail the coherent ones on a stale run,
fail a control whose store is not its kept reference (and print no headline), and read a row
without its dumps as cannot tell, never a pass."""
import os
import shlex
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("gen", "kit", "score", "mock"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import pins  # noqa: E402
import rf as R  # noqa: E402
import score as SC  # noqa: E402
import world  # noqa: E402

ROWS = K.table(KP, "refill")


def v_store():
    return struct.pack("<%dI" % R.DWORDS, *([R.V] * R.N + [R.SFILL] * (R.DWORDS - R.N)))


def kept_dir(tmp, monkeypatch, store2=None, store1=None, drop=()):
    """A kept directory as the runner leaves it, from the twin's answers (model world) with
    NAME's store 1 / store 2 replaced by store1 / store2's bytes."""
    d = tmp / "refill"
    d.mkdir()
    cases = ["\t".join(K.COLUMNS)]
    for row in ROWS:
        n = row["name"]
        dbg = tmp / ("dbg-" + n)
        dbg.mkdir()
        for w in row["knobs"]:
            if w.startswith("dbg:"):
                k, v = w[4:].split("=")
                (dbg / k).write_text(v + "\n")
        monkeypatch.setenv("FAKE_DBGREAL", str(dbg))
        a = world.answer("t14", shlex.split(row["args"].replace('"$W"', "/w")), {"model"})
        (d / f"{n}.txt").write_text(a["out"])
        (d / f"{n}.dmesg").write_text("".join(f"[1.0] gma500 0000:00:02.0: [drm] {k}\n"
                                              for k in a.get("kmsg", [])))
        for r in (1, 2):
            b = a["files"][f"/w/depth-store.{r}.bin"]
            b = {1: store1, 2: store2}[r].get(n, b) if {1: store1, 2: store2}[r] else b
            if (n, r) not in drop:
                (d / f"{n}.depth-store.{r}.bin").write_bytes(b)
        cases.append("\t".join([n, "refill", row["set"], row["risk"], " ".join(row["knobs"]),
                                row["tool"], row["args"], str(a["rc"]), "ok", "-", "-", "1"]))
    (d / "cases.tsv").write_text("\n".join(cases) + "\n")
    (d / "void.tsv").write_text("\t".join(K.COLUMNS) + "\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return str(d)


def summary(d):
    controls, per_model, lines = SC.verdicts("refill", d)
    import scorekit as SK
    return controls, {m: SK.headline(m, controls, s) for m, s in per_model.items()}, lines


def test_coherent_run_holds_the_favoured_models(tmp_path, monkeypatch):
    controls, heads, lines = summary(kept_dir(tmp_path, monkeypatch))
    assert all(controls.values()) and len(controls) == 3, lines
    for m in R.FAVOURED:
        assert heads[m].startswith(m + " (1 of 1 rows decided)"), heads[m]
    assert "is not supported" in heads["H-CC-STALE"] and "is not supported" in heads["H-NC-STALE"]


def test_stale_flag_row_holds_stale_and_fails_coherent(tmp_path, monkeypatch):
    stale = pins.blob(R.KEPT["id"])      # render 2 reads what render 1 loaded: the index
    controls, heads, lines = summary(kept_dir(tmp_path, monkeypatch,
                                              store2={"rf-cc-refill": stale}))
    assert "ROW rf-cc-refill: store 2 F; H-CC-COHERENT V; H-CC-STALE F: held H-CC-STALE" in lines
    assert heads["H-CC-STALE"].startswith("H-CC-STALE (1 of 1")
    assert "is not supported" in heads["H-CC-COHERENT"]
    assert heads["H-NC-COHERENT"].startswith("H-NC-COHERENT (1 of 1")


def test_mixed_store_is_neither_model(tmp_path, monkeypatch):
    d = R.dwords(v_store())
    d[:100] = range(100)
    mixed = struct.pack("<%dI" % len(d), *d)
    _, heads, lines = summary(kept_dir(tmp_path, monkeypatch, store2={"rf-nc-refill": mixed}))
    assert any(ln.startswith("ROW rf-nc-refill: store 2 mixed F 100 V 1948") for ln in lines)
    assert "is not supported" in heads["H-NC-COHERENT"] and "is not supported" in heads["H-NC-STALE"]


def test_failed_control_gates_the_headlines(tmp_path, monkeypatch):
    off = pins.blob(R.KEPT["off"])       # rf-c-depth's store 1 the clear, not E1029's identity
    controls, heads, lines = summary(kept_dir(tmp_path, monkeypatch, store1={"rf-c-depth": off}))
    assert controls["rf-c-depth"] is False
    assert all(not h.startswith(m + " (") for m, h in heads.items()), heads


def test_unread_control_fails_when_render_2_reads_no_refill(tmp_path, monkeypatch):
    controls, _, _ = summary(kept_dir(tmp_path, monkeypatch,
                                      store2={"rf-c-unread": pins.blob(R.KEPT["off"])}))
    assert controls["rf-c-unread"] is False


def test_missing_dump_is_cannot_tell(tmp_path, monkeypatch):
    controls, heads, lines = summary(kept_dir(tmp_path, monkeypatch,
                                              drop={("rf-cc-refill", 2), ("rf-c-depth", 1)}))
    assert controls["rf-c-depth"] is None
    assert any(ln.startswith("ROW rf-cc-refill: store 2 None") and ln.endswith("cannot tell")
               for ln in lines), lines
    assert all(not h.startswith(m + " (") for m, h in heads.items())


def test_required_files_and_producible_keys():
    assert SC.REQUIRED["refill"][:4] == (".txt", ".dmesg", ".depth-store.1.bin",
                                         ".depth-store.2.bin")
    for row in ROWS:
        assert set(row["reads"]) <= SC.producible(row), row["name"]
