#!/usr/bin/env python3
"""compare_twin.py OUTROOT SUFFIX WORLDSPEC: the kept directories OUTROOT/<stage>-<SUFFIX> that the bash runner wrote for the five DPM stages
(tests/run_mock.sh) against the Python twin of the runner (tests/world_r3.py `simulate`) on the same world: every row's P (the cell the
runner picked or derived), its class (ok / skipped) and its observation class (R / N / V) must be the same.  Exit 0 only if all agree."""
import pathlib
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import world_r3 as W  # noqa: E402
import dpm3  # noqa: E402

root, sfx, spec = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
world = W.named_world(spec)
tmp = pathlib.Path(tempfile.mkdtemp(dir=str(W.R3 / "debug/tmp")))
state = None
bad, n = 0, 0
for st in ("g-c4", "g-d36", "g-c6", "g-c5", "g-c7"):
    state, stopped = W.simulate(st, world, tmp / st, state)
    kb, kt = dpm3.Kept(root / f"{st}-{sfx}"), dpm3.Kept(tmp / st)
    names_b, names_t = kb.names(), kt.names()
    if names_b != names_t:
        print(f"{st}: rows differ: bash {names_b} twin {names_t}")
        bad += 1
        continue
    for nm in names_b:
        n += 1
        cb, ct = kb.case(nm), kt.case(nm)
        ob = cb["note"].split()[1] if cb["note"].startswith("class ") else ""
        jt = dpm3.read_job(kt, nm) if ct["class"] != "skipped" else None
        ot = dpm3.cls_of(jt) if jt else ""
        if (cb["P"], cb["class"], ob or ot) != (ct["P"], ct["class"], ot):
            bad += 1
            print(f"{st}/{nm}: bash P {cb['P']} {cb['class']} obs {ob!r} | twin P {ct['P']} {ct['class']} obs {ot!r}")
print(f"{n} rows compared, {bad} differ")
sys.exit(1 if bad else 0)
