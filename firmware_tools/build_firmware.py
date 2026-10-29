"""Reproducible experimental V502 patch builder. NEVER accesses USB."""
from pathlib import Path
import hashlib, json, re, struct, sys

ORIGINAL_SHA = '2e188151b6025aac685855c6088959fa3d9c9058d9055bfb07a92c380b68f306'
FLASH = 0x08000000
CONTEXT, CONTEXT_SIZE = 0x20009D98, 544
CODE_START = 0x08022000

def digest(b): return hashlib.sha256(b).hexdigest()

def build(root=None):
    from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
    root = Path(root or Path(__file__).resolve().parents[1])
    original = (root/'firmware/TAC75_ID2782_V502_original.bin').read_bytes()
    assert digest(original) == ORIGINAL_SHA
    assert len(original) == 133696
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    def asm(text, address):
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        # Keystone lacks M-class special-register names. Use equal-length instruction
        # placeholders, then substitute verified encodings without changing relocations.
        special_mrs='mrs r12, primask' in text
        special_msr='msr primask, r12' in text
        text=text.replace('mrs r12, primask','movw r12, #0')
        text=text.replace('msr primask, r12','movt r12, #0')
        text = '\n'.join(line for line in text.splitlines()
                         if not line.strip().startswith(('.syntax', '.thumb')))
        code=bytes(ks.asm(text, address)[0])
        for used,placeholder,encoding in [
            (special_mrs,'movw r12, #0',bytes.fromhex('eff3108c')),
            (special_msr,'movt r12, #0',bytes.fromhex('8cf31088'))]:
            if used:
                marker=bytes(ks.asm(placeholder)[0]);assert code.count(marker)==1
                code=code.replace(marker,encoding)
        return code
    receiver_addr = CODE_START
    receiver = asm((root/'firmware_tools/rgb_ram_receiver.s').read_text(encoding='utf8'), receiver_addr)
    usb_addr = (receiver_addr+len(receiver)+15)&~15
    usb_source = f'''
        push {{r4, lr}}
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
        ldr r1, ={CONTEXT:#x}
        bl {receiver_addr:#x}
        strb r0, [r4, #9]
        movs r0, #165
        strb r0, [r4, #8]
        ldr r1, ={CONTEXT:#x}
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
        ldr r1, ={CONTEXT:#x}
        ldrb r0, [r1, #3]
        strb r0, [r4, #24]
    usb_done:
        pop.w {{r4, lr}}
        b.w 0x08012fc0
    '''
    usb = asm(usb_source, usb_addr)
    led_addr = (usb_addr+len(usb)+15)&~15
    led_source = f'''
        cmp r0, #86
        blo valid_led
        bx lr
    valid_led:
        push {{r4, lr}}
        sub sp, sp, #8
        ldr r4, [sp, #16]
        str r4, [sp, #0]
        cmp r0, #83
        bhs original_encode
        mrs r12, primask
        cpsid i
        ldr r4, ={CONTEXT:#x}
        ldrb r4, [r4, #3]
        cmp r4, #1
        bne restore_irq
        ldr r4, ={CONTEXT:#x}
        ldrb r4, [r4, #2]
        cmp r4, #1
        bhi restore_irq
        lsls r4, r4, #8
        ldr r1, ={CONTEXT+32:#x}
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
        pop {{r4, pc}}
    '''
    led = asm(led_source, led_addr)
    output = bytearray(original)
    output.extend(b'\xff'*(CODE_START-FLASH-len(output)))
    for address, code in [(receiver_addr,receiver),(usb_addr,usb),(led_addr,led)]:
        offset=address-FLASH
        if len(output)<offset: output.extend(b'\xff'*(offset-len(output)))
        output[offset:offset+len(code)]=code
    output.extend(b'\xff'*((-len(output))%64))
    assert len(output)<0x28000
    assert original[0x717c:0x7182] == bytes.fromhex('5628 28bf 7047')
    led_hook=asm(f'b.w {led_addr:#x}\nnop',FLASH+0x717c)
    assert len(led_hook)==6
    output[0x717c:0x7182]=led_hook
    assert struct.unpack_from('<H',original,0x12938)[0] == 0xDB
    relative=(usb_addr-0x08012932)//2
    assert relative<65536 and 0x08012932+relative*2==usb_addr
    struct.pack_into('<H',output,0x12938,relative)
    # Reserve the context from the former heap/stack region. Keep heap capacity.
    # Startup zeroes this entire region. Global variables and initial SP are unchanged.
    for off,old,new in [(0x5528,0x20009D98,0x20009FB8),
                        (0x5530,0x20009F98,0x2000A1B8),
                        (0x5534,0x20009F98,0x2000A1B8)]:
        assert struct.unpack_from('<I',original,off)[0]==old
        struct.pack_into('<I',output,off,new)
    assert output[:0x5000]==original[:0x5000], 'Bootloader must be byte-identical'
    allowed=set(range(0x717c,0x7182))|set(range(0x12938,0x1293a))
    for off in [0x5528,0x5530,0x5534]:allowed.update(range(off,off+4))
    changed=[i for i in range(len(original)) if original[i]!=output[i]]
    assert set(changed)<=allowed
    manifest={
        'format':'TAC75-FW-LAB-1','device_id':2782,'vendor_id':0x3151,'product_id':0x502d,
        'base_version':'V502','version':'V502-RAM1-experimental',
        'original_sha256':ORIGINAL_SHA,'patched_sha256':digest(output),
        'patched_bytes':len(output),'application_offset':0x5000,
        'context_address':CONTEXT,'context_bytes':CONTEXT_SIZE,
        'context_end_exclusive':CONTEXT+CONTEXT_SIZE,
        'heap_start':0x20009FB8,'heap_end':0x2000A1B8,'heap_bytes':512,
        'stack_bottom':0x2000A1B8,'stack_top':0x2000DF98,'stack_bytes':15840,
        'original_stack_bytes':16384,'stack_reduction_bytes':544,
        'receiver_address':receiver_addr,'receiver_bytes':len(receiver),
        'usb_wrapper_address':usb_addr,'usb_wrapper_bytes':len(usb),
        'led_wrapper_address':led_addr,'led_wrapper_bytes':len(led),
        'changed_original_offsets':changed,
        'bootloader_unchanged':True,'configuration_region_not_in_image':True,
        'capability_signature':'AK75RAM1','protocol_command':15,'protocol_tag':167,
        'physical_leds':83,'hardware_tested':False,'production_release':False,
        'rollback_target':'Official V502, not a readback of the unit',
        'limit':'Experimental. Reduced stack is not measured on hardware; USB timing, LEDs, hardware recovery remain unvalidated.'
    }
    patched=root/'firmware/TAC75_ID2782_V502_RAM1_EXPERIMENTAL.bin'
    patched.write_bytes(output)
    (root/'firmware/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    (root/'firmware_tools/generated_usb_wrapper.s').write_text(usb_source,encoding='utf8')
    (root/'firmware_tools/generated_led_wrapper.s').write_text(led_source,encoding='utf8')
    return manifest

if __name__=='__main__': print(json.dumps(build(),indent=2))
