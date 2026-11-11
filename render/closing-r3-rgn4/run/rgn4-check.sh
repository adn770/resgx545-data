#!/bin/bash
# D3 laptop check (rgn4-REPORT.md "Laptop check proposal"), order 5 1 3 6 2 4
T="sudo /home/jtorra/sgxfive-test-rgn4"
D=/sys/kernel/debug/dri/0000:00:02.0/sgx
W=~/rgn4; mkdir -p $W
S4X="--poke cmd:1=0xe0000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26"
job() {  # job NAME ARRAYS HOLD ARGS...
  n=$1; a=$2; h=$3; shift 3
  for x in "$@"; do case $x in *.dump) sudo rm -rf $x; mkdir -p $x;; esac; done
  echo 1 | sudo tee $D/reset >/dev/null
  echo $a | sudo tee $D/render_rgn_arrays >/dev/null
  echo $h | sudo tee $D/hold_recovery >/dev/null
  echo "rgn4-check: start $n" | sudo tee /dev/kmsg >/dev/null
  $T "$@" > $W/$n.out 2>&1; rc=$?
  echo "rgn4-check: end $n" | sudo tee /dev/kmsg >/dev/null
  sudo dmesg | sed -n "/rgn4-check: start $n\$/,/rgn4-check: end $n\$/p" > $W/$n.kmsg
  echo "== $n rc=$rc arrays=$(sudo cat $D/render_rgn_arrays) hold=$(sudo cat $D/hold_recovery)"
  grep -E "made for|wrong|EINVAL|Invalid|fault|BIF|hash|echo|renders|triangle|error|fail" $W/$n.out | head -12
  grep -E -i "fault|BIF_INT|page|EINVAL|reset|recovery" $W/$n.kmsg | head -8
  [ -d $W/$n.dump ] && sudo ls -l $W/$n.dump | awk 'NR>1{print "   dump", $5, $9}'
}
case "$1" in
1r) job j1r-aa4-auto 0 N tri --tri-full --keep-going --wait-ms 20000 --width 288 --height 144 --max-width 288 --max-height 144 --aa4 $S4X --dump-render $W/j1r-aa4-auto.dump
   job j6r-forced1-tee0 1 N tri --tri-full --keep-going --wait-ms 20000 --width 256 --height 160 --max-width 256 --max-height 160 $S4X --dump-render $W/j6r-forced1-tee0.dump
   echo 0 | sudo tee $D/render_rgn_arrays >/dev/null; echo "knob back: $(sudo cat $D/render_rgn_arrays)";;
1) job j5-ctl-1x 0 N tri --width 1024 --height 768 -n 1 --keep-going --keep-overflow --wait-ms 20000
   job j1-aa4-auto 0 N tri --tri-full --keep-going --wait-ms 20000 --width 288 --height 144 --max-width 288 --max-height 144 --aa4 $S4X --dump-render $W/j1-aa4-auto.dump
   job j3-noflag-refused 0 N tri --tri-full --keep-going --wait-ms 20000 --width 288 --height 144 --max-width 288 --max-height 144 $S4X
   job j6-forced1-tee0 1 N tri --tri-full --keep-going --wait-ms 20000 --width 256 --height 160 --max-width 256 --max-height 160 $S4X --dump-render $W/j6-forced1-tee0.dump
   echo 0 | sudo tee $D/render_rgn_arrays >/dev/null; echo "knob back: $(sudo cat $D/render_rgn_arrays)";;
2) job j2-forced1-fault 1 Y tri --tri-full --keep-going --wait-ms 20000 --width 288 --height 144 --max-width 288 --max-height 144 $S4X
   sudo dmesg | grep -i -E "BIF_INT_STAT|fault" | tail -4
   echo N | sudo tee $D/hold_recovery >/dev/null; echo 0 | sudo tee $D/render_rgn_arrays >/dev/null
   echo 1 | sudo tee $D/reset >/dev/null
   echo "knobs back: arrays=$(sudo cat $D/render_rgn_arrays) hold=$(sudo cat $D/hold_recovery)";;
4) job j4-aa4-4096 0 N tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width 4096 --height 4096 --aa4 $S4X --dump-render $W/j4-aa4-4096.dump
   echo 0 | sudo tee $D/render_rgn_arrays >/dev/null;;
esac
