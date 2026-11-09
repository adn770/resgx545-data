phas #0, #0, pixel, end, parallel
mov.skipinv r0, #0x00000000
mov.skipinv r0, #0x00000000
mov.skipinv r0, #0x00000000
mov.skipinv r0, #0x00000000
emitpix1.freep #0 /* incp */, r0, r1
mov.skipinv r1, #0x5CAF0050
stad [r1,+#0], r2
idf drc0, bif
wdf drc0
emitpix2.end.freep #0 /* incp */, r2, r3, r0, #0x00000000
