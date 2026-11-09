#!/bin/bash
# run-all-1141tex.sh: the p1141/tex batch on the laptop in the order of plan.md section 6 (safe scripts, then
# the risky ones, one at a time, last), each with its own log. Run it on the laptop after stage-p1141tex.sh has
# put the programs in ~/sgxprobes-stage-1141tex; the tool is ~/sgxfive-test-1138b. It stops after the first
# script that stopped itself (three failed recoveries): read dmesg before another run. No script here writes a
# register (no clock-gate register, no kreg, no /dev/mem write).
set -u
cd "$(dirname "$0")"
OUT=${OUT:-$HOME/p1141tex-out}
mkdir -p "$OUT"
for s in tex-a-lod tex-b-bilin tex-c-addr tex-d-t0b27 tex-e-etc1 tex-f-types msaa-a-vis msaa-b-te29 isp-a-guard isp-b-depth tex-g-types-risky tex-h-cube msaa-c-q140; do
	echo "#### $s $(date +%T)"
	bash "./$s.sh" > "$OUT/$s.out" 2>&1
	rc=$?
	echo "rc $rc, $(grep -c '^== ' "$OUT/$s.out") jobs, $(grep -c 'kept ' "$OUT/$s.out") kept, $(grep -c 'MISMATCH' "$OUT/$s.out") declared mismatches"
	grep -E "^## abort|^  health: the plain|^## journalctl" "$OUT/$s.out" | head -4
	[ "$rc" -ne 0 ] && { echo "stopped after $s"; break; }
done
