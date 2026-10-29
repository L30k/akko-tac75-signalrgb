"""Run the ACTUAL patched Thumb image. No HID import or device access."""
from pathlib import Path
import sys,json,random,hashlib,struct
ROOT=Path(__file__).resolve().parents[1]
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_PROT_READ, UC_PROT_EXEC
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,UC_HOOK_CODE
from unicorn.arm_const import *

original=(ROOT/'firmware/TAC75_ID2782_V502_original.bin').read_bytes()
modified=(ROOT/'firmware/TAC75_ID2782_V502_RAM1_EXPERIMENTAL.bin').read_bytes()
meta=json.loads((ROOT/'firmware/manifest.json').read_text())
CTX=meta['context_address'];SP=0x2000DF90;STOP=0x08027F00;HID=0x20008D50;ENC=0x20000C9C
counts={'usb_packets':0,'led_differential_cases':0,'legacy_commands':0,'rgb_frames':0}
max_stack=SP

def new(image):
 u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
 u.mem_map(0x08000000,0x40000);u.mem_write(0x08000000,b'\xff'*0x40000);u.mem_write(0x08000000,image)
 # Test-only interrupt-state initialization via real CPSIE/CPSID instructions.
 # This avoids manipulating special CPU registers through the emulator API.
 u.mem_write(0x08027E00,bytes.fromhex('62b6 7047 72b6 7047'))
 u.mem_protect(0x08000000,0x40000,UC_PROT_READ|UC_PROT_EXEC)
 u.mem_map(0x20000000,0x10000)
 def stack_trace(uc,address,size,user):
  global max_stack
  current_sp=uc.reg_read(UC_ARM_REG_SP)
  if meta['stack_bottom']<=current_sp<=SP:max_stack=min(max_stack,current_sp)
 u.hook_add(UC_HOOK_CODE,stack_trace)
 # Execute the original compressed-data initializer, not an invented RAM model.
 for reg,val in [(UC_ARM_REG_R0,0x0802083C),(UC_ARM_REG_R1,0x20000000),
                 (UC_ARM_REG_R2,0x438),(UC_ARM_REG_SP,SP),(UC_ARM_REG_LR,STOP|1)]:u.reg_write(reg,val)
 u.emu_start(0x0800541D,STOP,count=100000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP
 initialized=bytes(u.mem_read(0x20000000,0x438))
 assert not any(CTX<=struct.unpack_from('<I',initialized,i)[0]<CTX+544 for i in range(len(initialized)-3))
 assert bytes(u.mem_read(CTX,544))==bytes(544)
 return u

def run(u,entry):
 u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP|1)
 u.emu_start(entry|1,STOP,count=300000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP,hex(u.reg_read(UC_ARM_REG_PC))
 assert u.reg_read(UC_ARM_REG_SP)==SP,(hex(entry),hex(u.reg_read(UC_ARM_REG_SP)),hex(u.reg_read(UC_ARM_REG_PC)))

def packet(command,data=b''):
 p=bytearray(64);p[0]=command;p[1:1+len(data)]=data
 pos=8 if command in [7,8] else 7;p[pos]=255-(sum(p[:pos])&255)
 return bytes(p)

def rgb(op,seq=0,block=0,payload=b''):
 p=bytearray(64);p[:7]=bytes([15,167,1,op,seq,block,len(payload)])
 p[7]=255-(sum(p[:7])&255);p[8:8+len(payload)]=payload;return bytes(p)

def usb(u,p):
 u.mem_write(HID,b'\x01\x00'+p)
 old_flags=bytes(u.mem_read(0x200000EC,4))
 run(u,0x08012850)
 if p[0]==15:assert bytes(u.mem_read(0x200000EC,4))==old_flags,'RGB must not set persistence flags'
 counts['usb_packets']+=1
 return bytes(u.mem_read(HID+2,64))

def encode(u,index,brightness,r,g,b,primask=0):
 u.reg_write(UC_ARM_REG_R0,index);u.reg_write(UC_ARM_REG_R1,brightness)
 u.reg_write(UC_ARM_REG_R2,r);u.reg_write(UC_ARM_REG_R3,g)
 run(u,0x08027E04 if primask else 0x08027E00)
 assert u.reg_read(UC_ARM_REG_PRIMASK)==primask
 u.mem_write(SP,b.to_bytes(4,'little'))
 before=bytes(u.mem_read(0x20000000,0x10000))
 saved={reg:0x13570000+reg for reg in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]}
 for reg,val in saved.items():u.reg_write(reg,val)
 run(u,0x0800717C)
 assert u.reg_read(UC_ARM_REG_PRIMASK)==primask
 assert int.from_bytes(u.mem_read(SP,4),'little')==b,'Caller argument must be restored'
 for reg,val in saved.items():assert u.reg_read(reg)==val
 after=bytes(u.mem_read(0x20000000,0x10000))
 lo,hi=ENC-0x20000000,ENC-0x20000000+86*24
 assert after[:lo]==before[:lo]
 assert after[hi:SP-0x20000000-64]==before[hi:SP-0x20000000-64]
 assert after[SP-0x20000000:]==before[SP-0x20000000:]
 return bytes(u.mem_read(ENC,86*24))

# RAM and patch extent checks, including unchanged bootloader and exact heap capacity.
assert modified[:0x5000]==original[:0x5000]
assert CTX==0x20009D98 and CTX+544==meta['heap_start']
assert meta['heap_end']-meta['heap_start']==512
assert meta['heap_end']==meta['stack_bottom']<SP<meta['stack_top']
assert 0x20000438<=CTX and CTX+544<=0x2000DF98
assert len(modified)<0x28000 and (len(modified)-0x5000)%64==0
for needle,expected in [(0x20009D98,[0x5528]),(0x20009F98,[0x5530,0x5534])]:
 found=[i for i in range(0,len(original)-3,4) if struct.unpack_from('<I',original,i)[0]==needle]
 assert found==expected,(hex(needle),found)
u=new(modified);run(u,0x08005514)
assert u.reg_read(UC_ARM_REG_R0)==meta['heap_start']
assert u.reg_read(UC_ARM_REG_R1)==meta['stack_top']
assert u.reg_read(UC_ARM_REG_R2)==meta['heap_end']
assert u.reg_read(UC_ARM_REG_R3)==meta['stack_bottom']

# Differential tests of the real original and patched parser for representative legacy reads/setters.
legacy=[3,6,7,8,9,17,27,0x83,0x84,0x85,0x86,0x87,0x88,0x89,0x8f,0x91]
for cmd in legacy:
 a,b=new(original),new(modified)
 p=packet(cmd)
 usb(a,p);usb(b,p)
 assert bytes(a.mem_read(0x20000000,0x9d98))==bytes(b.mem_read(0x20000000,0x9d98)),hex(cmd)
 counts['legacy_commands']+=1

# Inactive hook must produce exactly the original encoded bytes for varied channels and brightness.
rng=random.Random(2782502)
for n in range(180):
 idx=rng.randrange(90);bright=rng.randrange(101);color=[rng.randrange(256) for _ in range(3)]
 a,b=new(original),new(modified)
 assert encode(a,idx,bright,*color,primask=n%2)==encode(b,idx,bright,*color,primask=n%2)
 counts['led_differential_cases']+=1

# Exact code through the ORIGINAL dispatcher table -> receiver -> original dispatcher exit.
u=new(modified)
caps=usb(u,rgb(4));assert caps[8:16]==b'AK75RAM1' and caps[16]==83
assert bytes(u.mem_read(CTX,544))==bytes(544)
assert usb(new(original),rgb(4))[8:16]!=b'AK75RAM1'

def active_bytes():
 index=u.mem_read(CTX+2,1)[0];return bytes(u.mem_read(CTX+32+index*256,249))

# Every active-buffer read by the encoder occurs with interrupts masked.
snapshot_reads=0
def snapshot_guard(uc,address,size,user):
 global snapshot_reads
 pc=uc.reg_read(UC_ARM_REG_PC)
 if meta['led_wrapper_address']<=pc<meta['led_wrapper_address']+meta['led_wrapper_bytes']:
  # All instructions from the context load through the last RGB load are masked.
  code=bytes(uc.mem_read(pc,size))
  if code in [bytes.fromhex('10 8c'),bytes.fromhex('ef f3 10 8c')]:return
  # Use exact disassembly below to identify loads, not memory callbacks on Thumb IT blocks.
  from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
  decoded=list(Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(code,pc))
  if not decoded:return
  op=decoded[0]
  if op.mnemonic=='ldrb' and '[r4' in op.op_str:
   assert uc.reg_read(UC_ARM_REG_PRIMASK)==1
   snapshot_reads+=1
u.hook_add(UC_HOOK_CODE,snapshot_guard)
for seq in range(16):
 frame=bytes(rng.randrange(256) for _ in range(249))
 old=active_bytes()
 for block in range(5):
  response=usb(u,rgb(1,seq,block,frame[block*56:(block+1)*56]))
  assert response[8:10]==bytes([165,1]);assert active_bytes()==old
 response=usb(u,rgb(2,seq));assert response[8:10]==bytes([165,2])
 assert active_bytes()==frame
 for idx in range(83):
  expected=new(original)
  expected.mem_write(ENC,bytes(u.mem_read(ENC,86*24)))
  baseline=encode(expected,idx,100,*frame[idx*3:idx*3+3],primask=seq%2)
  actual=encode(u,idx,7,99,55,22,primask=seq%2)
  assert actual==baseline,(seq,idx)
  counts['led_differential_cases']+=1
 counts['rgb_frames']+=1

# Indicators 83..85 preserve original input; out-of-range indices preserve buffer.
for idx in range(83,90):
 expected=new(original);expected.mem_write(ENC,bytes(u.mem_read(ENC,86*24)))
 assert encode(u,idx,65,11,22,33)==encode(expected,idx,65,11,22,33)
 counts['led_differential_cases']+=1

# Broken/incomplete sequences do not publish; releasing reverts to original encoder behavior.
prior=active_bytes()
usb(u,rgb(1,99,0,bytes(56)));response=usb(u,rgb(2,99))
assert response[9]==0 and active_bytes()==prior
bad=bytearray(rgb(1,99,0,bytes(56)));bad[7]^=1
before=bytes(u.mem_read(CTX,544));usb(u,bytes(bad));assert bytes(u.mem_read(CTX,544))==before
usb(u,rgb(3));assert u.mem_read(CTX+3,1)==b'\0'
for idx in range(83):
 expected=new(original);expected.mem_write(ENC,bytes(u.mem_read(ENC,86*24)))
 assert encode(u,idx,44,10,20,30)==encode(expected,idx,44,10,20,30)
 counts['led_differential_cases']+=1

report={
 'status':'PASS in emulation; NOT a hardware qualification',
 'patched_sha256':hashlib.sha256(modified).hexdigest(),**counts,
 'snapshot_context_reads_with_interrupts_masked':snapshot_reads,
 'ram_context_reserved_without_static_overlap':True,
 'original_compressed_ram_initializer_executed':True,
 'initialized_data_references_into_reserved_context':0,
 'heap_capacity_preserved':True,'stack_reserved_bytes':meta['stack_bytes'],
 'maximum_stack_depth_observed_in_these_paths':SP-max_stack,
 'hardware_stack_peak_measured':False,
 'bootloader_byte_identical':True,
 'flash_or_peripheral_writes_in_executed_paths':0,
 'persistence_flags_unchanged_by_rgb_packets':True,
 'hardware_tests':0,
 'instrumentation':'Flash read/execute-only; hardware unmapped; instruction trace and RAM before/after comparison. Memory callbacks were not used for Thumb conditional-store encoder paths because they changed baseline execution in this emulator build.',
 'remaining':['Worst-case stack/interrupt timing on hardware','USB enumeration in boot and recovery','Physical LED ordering and frame rate','DMA timing/electrical output on the actual board']
}
(ROOT/'validation_firmware.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
