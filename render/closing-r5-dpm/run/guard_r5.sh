#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_r5.sh (R5-dpm): static check of everything that runs in R5-dpm against the forbidden list.  Built from R3-geo's guard_r3.sh.
# Run before staging (stage_r5.sh runs it).  The session's OWN guard: it never runs the repository's clean-room guard.
#   runner scripts: no reboot / shutdown / boot-loader / kernel build or install / push-gma500; no trc_hazard; no clock-gate register; no
#   kreg, kregnow, kpoke of any kind; no /dev/mem write; the own task only through fwtask_run.py's arm, write, page and status (never
#   its kreg path, run, pair, tailpair, events or gate); no git stash / clean / reset; no recursive delete; no wait loop; every line
#   that names the debugfs runs it through sudo -n; every `timeout` has -k; no other session's laptop directory.
#   run/fwtask_run.py: byte for byte the landed tools/fwtask/fwtask_run.py (its own kreg allow-list is 0x0814 and 0x0a78; R5 never
#   calls it).  bins/oomring.blob: the landed verifier accepts it, it has no str word, its only ldr is CR_TIMER (#81), it is what
#   asm/oomring.s assembles to.  Tables: no --kreg / --kpoke / --ctx2 / --share-pb / --late / --poke option.
# Exit 0 clean, 1 with the matching lines.
cd "$(dirname "$0")/.." || exit 1
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
BAD='reboot|shutdown|poweroff|systemctl (reboot|poweroff|kexec)|kexec|grub|update-grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|fast-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kregnow|--kreg|kreg-render|\bkreg\b|git (stash|clean|reset)|rm -r|rm -fr|rm -rf|>[[:space:]]*/dev/mem|of=/dev/mem|kpoke|SGXFIVE_KPOKE'
LOOP='(^|[;&|[:space:]])(while|until)[[:space:]]'
DEBUGFS='\$D"?/|\$\{D\}"?/|/sys/kernel/debug'
st=0
for f in run/lib_r5.sh run/lib_check.sh run/run_stage.sh run/r5.sh run/stage_r5.sh run/freeze_r5.sh run/r5.env run/r5read.py tables/*.txt; do
	[ -f "$f" ] || { echo "MISSING $f"; st=1; continue; }
	# comment lines may NAME what is forbidden (the lib's header names own_code etc. as the landed script's files); code may not
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#' ; then echo "FORBIDDEN in $f"; st=1; fi
	# the own task's debugfs files may only be named in the preflight's existence check
	if grep -nE 'own_(code|arm|res)' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'for f in own_code own_arm own_res load boot status miscinfo; do'; then
		echo "OWN TASK FILE NAMED in $f"; st=1; fi
	if grep -nE "$LOOP" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then echo "WAIT LOOP in $f"; st=1; fi
	if grep -nE "$DEBUGFS" "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then echo "UNPRIVILEGED DEBUGFS ACCESS in $f"; st=1; fi
	if grep -nE '(^|[^-])\btimeout[[:space:]]' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'timeout -k|JOB_TIMEOUT|tmo' | grep -E 'timeout [0-9"$]'; then
		echo "TIMEOUT WITHOUT -k in $f"; st=1; fi
done
# the reader never touches the debugfs or a device
if grep -nE 'open\(.*(/sys|/dev)' run/r5read.py; then echo "the reader opens a device"; st=1; fi
# the own task: only these fwtask_run.py subcommands, always through `fw` (sudo -n timeout -k)
if grep -nE '(^|[[:space:];|&(])fw ' run/lib_r5.sh run/run_stage.sh | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#' | grep -vE '\bfw (arm|write|page|status)\b|fw\(\)|fw_[a-z]+' ; then
	echo "fwtask_run.py subcommand other than arm/write/page/status"; st=1; fi
grep -q 'fw() { sudo -n timeout -k' run/lib_r5.sh || { echo "fw() does not run fwtask_run.py through sudo -n timeout -k"; st=1; }
cmp -s run/fwtask_run.py "$MAIN/tools/fwtask/fwtask_run.py" || { echo "run/fwtask_run.py is not the landed tools/fwtask/fwtask_run.py"; st=1; }
# the laptop directory prefix is ~/r5d: no script may name another session's directory
for f in run/lib_r5.sh run/run_stage.sh run/r5.sh run/stage_r5.sh; do
	if grep -nE 'r3g|r3p-|r3xev|r4e-|r4p|r4g|r5e-|r5p-|r5x-|r5k-|~/r[0-4]|\$HOME/r[0-4]' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then echo "ANOTHER SESSION'S DIRECTORY in $f"; st=1; fi
done
if grep -nE -- '--kreg|--kpoke|--ctx2|--share-pb|--late|--poke' tables/*.txt; then echo "FORBIDDEN option in a table"; st=1; fi
# the blob
RESGX545_MAIN="$MAIN" "$PY" - <<'PYEOF' || st=1
import os, sys, pathlib, hashlib
sys.dont_write_bytecode = True
main = pathlib.Path(os.environ["RESGX545_MAIN"])
sys.path.insert(0, str(main / "tools/fwtask"))
import fwtask
b = pathlib.Path("bins/oomring.blob").read_bytes()
regs = fwtask.load_regs()
p = fwtask.parse_blob(b)
kinds = [fwtask.classify(w)[0] for w in p.words]
bad = []
if fwtask.refusal(b, regs) is not None: bad.append(f"refused: {fwtask.refusal(b, regs)}")
if "STR" in kinds: bad.append("a str word")
ldr = sorted({fwtask.reg_index(w) for w, k in zip(p.words, kinds) if k == "LDR"})
if ldr != [81]: bad.append(f"ldr of {ldr} (only #81, CR_TIMER)")
if any(k == "MOVPA" for k in kinds): bad.append("a pa write")
if fwtask.build_blob_text(pathlib.Path("asm/oomring.s").read_text(), regs) != b: bad.append("asm/oomring.s does not assemble to bins/oomring.blob")
for x in bad: print("BLOB:", x)
sys.exit(1 if bad else 0)
PYEOF
exit $st
