
        cmp r0, #86
        blo valid_led
        bx lr
    valid_led:
        push {r4, lr}
        sub sp, sp, #8
        ldr r4, [sp, #16]
        str r4, [sp, #0]
        cmp r0, #83
        bhs original_encode
        mrs r12, primask
        cpsid i
        ldr r4, =0x20009d98
        ldrb r4, [r4, #3]
        cmp r4, #1
        bne restore_irq
        ldr r4, =0x20009d98
        ldrb r4, [r4, #2]
        cmp r4, #1
        bhi restore_irq
        lsls r4, r4, #8
        ldr r1, =0x20009db8
        adds r4, r4, r1
        add.w r4, r4, r0, lsl #1
        adds r4, r4, r0
        ldrb r2, [r4, #0]
        ldrb r3, [r4, #1]
        ldrb r4, [r4, #2]
        str r4, [sp, #0]
        movs r1, #100
    restore_irq:
        msr primask, r12
    original_encode:
        bl 0x08007182
        add sp, sp, #8
        pop {r4, pc}
    