# SPDX-License-Identifier: MIT
# run/hooks.sh: r25-q123's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory; $args and $knobs are the row's (the runner's loop).
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
#   o0=0xV       a uniform o0 (2048 of 2048), else o0=mixed
#   placed=K/N   `placed words read back: K of N as built`
hook_reading() {
	local o p
	o=$(sed -n 's/^probe [^ ]*: o0 \(0x[0-9a-f]*\) (2048 of 2048)$/\1/p' "$JW/$1.out" | head -n 1)
	[ -z "$o" ] && grep -q "^probe [^ ]*: o0 mixed" "$JW/$1.out" && o=mixed
	[ -n "$o" ] && printf 'o0=%s\n' "$o"
	p=$(sed -n 's/^probe [^ ]*: placed words read back: \([0-9]*\) of \([0-9]*\) as built.*/\1\/\2/p' "$JW/$1.out" | head -n 1)
	[ -n "$p" ] && printf 'placed=%s\n' "$p"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing:
#   a --place row whose placed words did not read back as built; a control whose o0 is not its
#   frozen word (knob o0:HEX)
hook_check() {
	local p w o
	case "$args" in
	*--place\ *)
		p=$(sed -n 's/^probe [^ ]*: placed words read back: \([0-9]*\) of \([0-9]*\) as built.*/\1 \2/p' "$JW/$1.out" | head -n 1)
		[ -n "$p" ] && [ "${p% *}" = "${p#* }" ] || { printf '%s: placed words not read back as built (%s)\n' "$1" "${p:-no line}"; return 0; } ;;
	esac
	w=$(printf '%s\n' "$knobs" | sed -n 's/.*o0:\([0-9a-f]\{8\}\).*/\1/p')
	if [ -n "$w" ]; then
		o=$(sed -n 's/^probe [^ ]*: o0 0x\([0-9a-f]*\) (2048 of 2048)$/\1/p' "$JW/$1.out" | head -n 1)
		[ "$o" = "$w" ] || printf 'control %s read o0 %s, frozen 0x%s\n' "$1" "${o:-not uniform}" "$w"
	fi
	return 0
}
# hook_fault NAME: no fault or hang is planned (every stage #limit 0)
hook_fault() { return 0; }
