"""Replay the prepared updater against the ORIGINAL boot parser in a virtual MCU.
Flash programming/unlock/lock are replaced with in-memory test doubles.
No USB library/device access; no actual hardware flash operation.
"""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from lab_core import transfer_in_boot,ValidationError
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE,UC_PROT_READ,UC_PROT_EXEC
from unicorn.arm_const import *

original=(ROOT/'firmware/TAC75_ID2782_V502_original.bin').read_bytes()
STOP=0x08004F00;STATE=0x200004F4
results=[]
for target in ['original','RAM1_EXPERIMENTAL']:
 image=(ROOT/f'firmware/TAC75_ID2782_V502_{target}.bin').read_bytes()
 payload=image[0x5000:]
 u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
 u.mem_map(0x08000000,0x40000);u.mem_write(0x08000000,b'\xff'*0x40000);u.mem_write(0x08000000,original[:0x5000])
 u.mem_protect(0x08000000,0x40000,UC_PROT_READ|UC_PROT_EXEC)
 u.mem_map(0x20000000,0x10000)
 writes=[]
 def code(uc,address,size,user):
  if address in [0x08001084,0x08000FC0]:uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  elif address==0x0800109C:
   dest=uc.reg_read(UC_ARM_REG_R0);source=uc.reg_read(UC_ARM_REG_R1);count=uc.reg_read(UC_ARM_REG_R2)
   assert 0x08005000<=dest and dest+count<=0x08028000 and count==64
   uc.mem_write(dest,bytes(uc.mem_read(source,count)))
   writes.append((dest,count));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,code)
 def run(entry):
  u.reg_write(UC_ARM_REG_SP,0x20004E00);u.reg_write(UC_ARM_REG_LR,STOP|1)
  u.emu_start(entry|1,STOP,count=100000)
  assert u.reg_read(UC_ARM_REG_PC)==STOP and u.reg_read(UC_ARM_REG_SP)==0x20004E00
 class VirtualHandle:
  def exchange(self,p,delay=.1):
   u.mem_write(STATE+0x60,p);run(0x0800048C)
   return bytes(u.mem_read(STATE+0x20,64))
  def send(self,p):u.mem_write(STATE+0x60,p);run(0x080006D0)
 transfer_in_boot(VirtualHandle(),payload,sleep=lambda _:None)
 assert bytes(u.mem_read(0x08005000,len(payload)))==payload
 assert bytes(u.mem_read(0x08000000,0x4800))==original[:0x4800]
 results.append({'target':target,'blocks_programmed_in_virtual_flash':len(writes),'bytes':len(payload),
                 'bootloader_checksum_status':'0x55, success','payload_byte_exact':True,'virtual_bootloader_untouched':True})
report={'status':'PASS against the original boot parser with virtual flash','cases':results,
 'physical_device_access':False,'hardware_flash_operations':0,
 'scope':'Original 0xBA/0xC0 start, 64-byte block parser and 0xBA/0xC2 checksum verification executed. Unlock/lock/program are stubs. Enumeration/reset/real flash electronics remain untested.'}
(ROOT/'validation_boot_transfer.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
