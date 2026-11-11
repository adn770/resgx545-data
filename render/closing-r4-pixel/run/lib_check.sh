# SPDX-License-Identifier: MIT
# lib_check.sh: small checks of r3.sh, sourced (and tested by tests/run_mock.sh).
# The kernel prints a debugfs x32 as 0x%08llx (0x00000422, 0x00000000): numbers are compared numerically.
is_num() { case "$1" in 0x[0-9a-fA-F]*|[0-9]*) return 0 ;; *) return 1 ;; esac; }
num_eq() { is_num "$1" && is_num "$2" && [ $(($1)) -eq $(($2)) ]; }
# bounded SECONDS COMMAND...: the Mac side never waits on the laptop without a limit (a stuck GPU job keeps
# an ssh session alive); exit 142 (SIGALRM) when the limit is reached
bounded() { local s=$1; shift; perl -e 'alarm shift; exec @ARGV' "$s" "$@"; }
# fault_events DIR...: the fault-class events (class fault or hang, column 9 of cases.tsv) of the stage directories given
fault_events() {
	local n=0 c
	for d in "$@"; do
		[ -f "$d/cases.tsv" ] || continue
		c=$(awk -F'\t' 'NR > 1 && ($9 == "fault" || $9 == "hang") { n++ } END { print n + 0 }' "$d/cases.tsv")
		n=$((n + c))
	done
	echo "$n"
}
# toolsrc SRC: sha256 of every deploy input of tools/bringup/deploy-tool.sh in the checkout SRC (what its tar ships:
# userspace/libsgxfive without build/, include/uapi, tools/gen_tri_progs.py; caches left out), one line a file, sorted
toolsrc() {
	( cd "$1" && find userspace/libsgxfive include/uapi tools/gen_tri_progs.py -type f \
		! -path '*/build/*' ! -path '*/__pycache__/*' ! -path '*/.pytest_cache/*' ! -name '*.pyc' ! -name '.DS_Store' \
		| LC_ALL=C sort | xargs shasum -a 256 )
}
