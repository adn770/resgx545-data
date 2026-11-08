#!/bin/bash
# runs the safe scripts in turn on the laptop; each output kept in ~/p1131-out/NAME.out
mkdir -p ~/p1131-out
for s in ta-object-format ta-tri-boundary vdm-vtask vdm-state-units event-timelines event-irq-matrix; do
	echo "### $s $(date)" >> ~/p1131-out/progress.txt
	bash ~/p1131/$s.sh > ~/p1131-out/$s.out 2>&1
	echo "### $s done rc $? $(date)" >> ~/p1131-out/progress.txt
done
