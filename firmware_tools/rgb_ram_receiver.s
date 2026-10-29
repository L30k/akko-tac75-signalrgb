/* ARM Thumb module, NOT a complete keyboard firmware.
 * ABI: r0 -> exactly 64 input bytes, r1 -> 544 bytes of zeroed, RESERVED RAM.
 * Returns 0 invalid, 1 chunk staged, 2 complete frame published, 3 released.
 * Preserves r4-r7 and SP. No function calls, hardware addresses or flash writes.
 * RAM context: seq[0], chunk_mask[1], active_index[2], enabled[3];
 * frame0[32..280], frame1[288..536]; reserved padding up to 544.
 * Caller must serialize calls and consumers. DMA integration is NOT implemented.
 * Packet: 0F A7 01 OP SEQ BLOCK LENGTH CHECKSUM + up to 56 payload bytes.
 * OP 1=DATA (blocks 0..4; lengths 56/56/56/56/25), 2=COMMIT, 3=RELEASE.
 * Header byte sum modulo 256 must be FF. COMMIT requires all five chunks.
 * A new frame starts at DATA block 0. There is no timeout/watchdog in this module.
 * A stream-specific release restores only the enabled flag, not keyboard state.
 * Integration, physical RAM reservation and firmware hooks remain UNVALIDATED.
 */
.syntax unified
.thumb
rgb_ram_receiver:
    push {r4-r7, lr}
    mov r4, r0
    mov r5, r1
    ldrb r2, [r4, #0]
    cmp r2, #15
    bne invalid
    ldrb r2, [r4, #1]
    cmp r2, #167
    bne invalid
    ldrb r2, [r4, #2]
    cmp r2, #1
    bne invalid
    movs r2, #0
    movs r3, #0
checksum_loop:
    ldrb r6, [r4, r2]
    adds r3, r3, r6
    adds r2, r2, #1
    cmp r2, #8
    blo checksum_loop
    uxtb r3, r3
    cmp r3, #255
    bne invalid
    ldrb r2, [r5, #2]
    cmp r2, #1
    bhi invalid
    ldrb r2, [r4, #3]
    cmp r2, #1
    beq data_packet
    cmp r2, #2
    beq commit_packet
    cmp r2, #3
    beq release_packet
    b invalid
data_packet:
    ldrb r2, [r4, #5]
    cmp r2, #4
    bhi invalid
    movs r3, #56
    cmp r2, #4
    bne length_ready
    movs r3, #25
length_ready:
    ldrb r6, [r4, #6]
    cmp r6, r3
    bne invalid
    ldrb r6, [r4, #4]
    cmp r2, #0
    bne check_sequence
    strb r6, [r5, #0]
    movs r7, #0
    strb r7, [r5, #1]
    b sequence_ok
check_sequence:
    ldrb r7, [r5, #0]
    cmp r6, r7
    bne invalid
sequence_ok:
    ldrb r7, [r5, #2]
    movs r6, #1
    eors r7, r6
    lsls r7, r7, #8
    adds r7, r7, r5
    adds r7, r7, #32
    movs r6, #56
    muls r2, r6, r2
    adds r7, r7, r2
    adds r6, r4, #8
copy_payload:
    ldrb r2, [r6]
    strb r2, [r7]
    adds r6, r6, #1
    adds r7, r7, #1
    subs r3, r3, #1
    bne copy_payload
    ldrb r2, [r4, #5]
    movs r3, #1
    lsls r3, r3, r2
    ldrb r2, [r5, #1]
    orrs r2, r3
    strb r2, [r5, #1]
    movs r0, #1
    pop {r4-r7, pc}
commit_packet:
    ldrb r2, [r4, #5]
    ldrb r3, [r4, #6]
    orrs r2, r3
    bne invalid
    ldrb r2, [r4, #4]
    ldrb r3, [r5, #0]
    cmp r2, r3
    bne invalid
    ldrb r2, [r5, #1]
    cmp r2, #31
    bne invalid
    ldrb r2, [r5, #2]
    movs r3, #1
    eors r2, r3
    strb r2, [r5, #2]
    strb r3, [r5, #3]
    movs r2, #0
    strb r2, [r5, #1]
    movs r0, #2
    pop {r4-r7, pc}
release_packet:
    ldrb r2, [r4, #5]
    ldrb r3, [r4, #6]
    orrs r2, r3
    bne invalid
    movs r2, #0
    strb r2, [r5, #3]
    strb r2, [r5, #1]
    movs r0, #3
    pop {r4-r7, pc}
invalid:
    movs r0, #0
    pop {r4-r7, pc}
