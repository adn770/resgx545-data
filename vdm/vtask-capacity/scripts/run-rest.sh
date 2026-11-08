#!/bin/bash
# the follow-up scripts, then the risky ones one at a time; each output kept in ~/p1131-out/NAME.out
mkdir -p ~/p1131-out
for s in ta-object-format2 vdm-vtask2 ta-tri-corner ta-line-point ta-risky vdm-vtask-risky vdm-state-risky; do
	echo "### $s $(date)" >> ~/p1131-out/progress.txt
	bash ~/p1131/$s.sh > ~/p1131-out/$s.out 2>&1
	rc=$?
	echo "### $s done rc $rc $(date)" >> ~/p1131-out/progress.txt
	grep -q "abort" ~/p1131-out/$s.out && { echo "### stopped after abort in $s" >> ~/p1131-out/progress.txt; break; }
done
