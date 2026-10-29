
        push {r4, lr}
        adds r4, r4, #2
        ldrb r0, [r4, #1]
        cmp r0, #167
        bne usb_done
        ldrb r0, [r4, #2]
        cmp r0, #1
        bne usb_done
        ldrb r0, [r4, #3]
        cmp r0, #4
        beq capabilities
        mov r0, r4
        ldr r1, =0x20009d98
        bl 0x8022000
        strb r0, [r4, #9]
        movs r0, #165
        strb r0, [r4, #8]
        ldr r1, =0x20009d98
        ldrb r0, [r1, #2]
        strb r0, [r4, #10]
        ldrb r0, [r1, #3]
        strb r0, [r4, #11]
        b usb_done
    capabilities:
        ldrb r0, [r4, #5]
        ldrb r1, [r4, #6]
        orrs r0, r1
        bne usb_done
        ldr r0, =0x35374b41
        str r0, [r4, #8]
        ldr r0, =0x314d4152
        str r0, [r4, #12]
        movs r0, #83
        strb r0, [r4, #16]
        movs r0, #1
        strb r0, [r4, #17]
        movw r0, #544
        strh r0, [r4, #18]
        ldr r0, =0x20261029
        str r0, [r4, #20]
        ldr r1, =0x20009d98
        ldrb r0, [r1, #3]
        strb r0, [r4, #24]
    usb_done:
        pop.w {r4, lr}
        b.w 0x08012fc0
    