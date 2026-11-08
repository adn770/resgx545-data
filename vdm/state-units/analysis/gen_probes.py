#!/usr/bin/env python3
"""Writes draft/probes/: one wrapper toml per dataset, the scripts as templates, the programs' templates and table.
python3 -B gen/gen_probes.py from p1131/ (after gen_records.py, which clears draft/probes)."""
import pathlib, shutil
R = pathlib.Path(".")
D = R / "draft" / "probes"
sets = {
 ("ta", "object-format"): ["ta-object-format", "ta-object-format2"],
 ("ta", "tri-region"): ["ta-tri-boundary", "ta-tri-corner"],
 ("ta", "line-point"): ["ta-line-point", "ta-line-bisect", "ta-line-width"],
 ("ta", "points"): ["ta-points", "ta-points-vertex", "ta-risky"],
 ("vdm", "vtask-capacity"): ["vdm-vtask", "vdm-vtask2", "vdm-vtask3", "vdm-vtask4", "vdm-vtask5", "vdm-vtask-risky"],
 ("vdm", "state-units"): ["vdm-state-units", "vdm-state-risky", "vdm-state-grid"],
 ("platform", "event-bits"): ["event-timelines", "event-irq-matrix"],
}
Q = {"object-format": "Q070: the object's format word, set masks and stored dwords", "tri-region": "Q070: the region test of triangles at tile boundaries",
     "line-point": "Q070: the region test of lines", "points": "Q070, the old Q117: points, their size and OUTSEL",
     "vtask-capacity": "Q094, Q092: the vertices of a vertex task", "state-units": "Q047: VDM_STATE1 fields in a two-block stream",
     "event-bits": "Q111: the event bits of ordinary jobs and the host interrupts they raise"}
for (unit, name), scripts in sets.items():
    (D / unit / "templates").mkdir(parents=True, exist_ok=True)
    text = ("# SPDX-License-Identifier: MIT\n# SPDX-FileCopyrightText: 2026 Josep Torra\n# %s: %d shell scripts run on the laptop by hand (phase 11.31). %s.\n"
            "# The scripts, in the order they ran: %s.\n" % (name, len(scripts), Q[name], ", ".join(scripts)))
    text += 'needs = ["render", "kpoke", "reset"]\nname = "%s-%s"\nscript = "%s.sh"\n' % (unit, name, scripts[0])
    (D / unit / (name + ".toml")).write_text(text)
    for sc in scripts:
        shutil.copy2(R / (sc + ".sh"), D / unit / "templates" / (sc + ".sh"))
    shutil.copy2(R / "lib1131.sh", D / unit / "templates" / "lib1131.sh")
shutil.copy2(R / "event-irq-matrix.sh", D / "platform/templates/event-irq-repeat.sh")
for f in sorted((R / "templates").glob("*.s")):
    shutil.copy2(f, D / "ta" / "templates" / f.name)
shutil.copy2(R / "p1131-progs.toml", D / "ta" / "p1131-progs.toml")
shutil.copy2(R / "stage-p1131.sh", D / "ta" / "templates" / "stage-p1131.sh")
print(sum(1 for p in D.rglob("*") if p.is_file()), "probe files")
