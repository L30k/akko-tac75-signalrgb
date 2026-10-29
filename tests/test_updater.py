import unittest,sys,tempfile,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from lab_core import *

PORT='TEST_USB_PORT'
class Fake:
 def __init__(self,target='experimental',initial_boot=False,wrong_start=False,wrong_final=False,wrong_port=False,fail_block=None,wrong_cap=False):
  self.target=target;self.is_normal=not initial_boot;self.is_boot=initial_boot;self.received=bytearray();self.commands=[];self.block=0
  self.wrong_start=wrong_start;self.wrong_final=wrong_final;self.wrong_port=wrong_port;self.fail_block=fail_block;self.wrong_cap=wrong_cap
 def normal(self):return ['normal'] if self.is_normal else []
 def boot(self,port):return ['boot'] if self.is_boot and port==PORT and not self.wrong_port else []
 def inspect(self,d):return {'device_id':2782,'firmware':'V502','port':PORT,'rgb_ram_firmware':self.target=='experimental' and self.is_normal and bool(self.received) and not self.wrong_cap}
 def open(self,d):
  outer=self
  class H:
   def send(self,p):
    outer.commands.append(bytes(p))
    if d=='normal':
     assert p[0]==0x7f
     outer.is_normal=False;outer.is_boot=True
    else:
     if outer.block==outer.fail_block:raise OSError('Synthetic cable failure')
     outer.received.extend(p);outer.block+=1
   def exchange(self,p,delay=.1):
    outer.commands.append(bytes(p));r=bytearray(64)
    if p[:2]==b'\xba\xc0':
     r[:2]=b'\xab\xc0';r[2:4]=p[2:4]
     if outer.wrong_start:r[0]=0
    elif p[:2]==b'\xba\xc2':
     assert struct.unpack_from('<I',p,4)[0]==sum(outer.received)
     assert struct.unpack_from('<I',p,8)[0]==len(outer.received)
     r[:2]=b'\xab\xc2';r[2:4]=p[2:4];r[4]=0xAA if outer.wrong_final else 0x55
     outer.is_normal=True;outer.is_boot=False
    else:raise AssertionError('Unexpected command')
    return bytes(r)
   def close(self):pass
  return H()

class Tests(unittest.TestCase):
 def service(self,fake,tmp):return UpdateService(ROOT,tmp,fake,sleep=lambda _:None)
 def test_bundle(self):
  m,b,p=verify_package(ROOT);self.assertEqual(b[:0x5000],p[:0x5000]);self.assertFalse(m['hardware_tested'])
 def test_no_confirmation_no_io(self):
  f=Fake()
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:
   with self.assertRaises(ValidationError):self.service(f,t).flash('experimental')
  self.assertEqual(f.commands,[])
 def test_experimental_transfer(self):
  f=Fake()
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:r=self.service(f,t).flash('experimental',True)
  self.assertTrue(r['final_identity']['rgb_ram_firmware'])
  self.assertEqual(f.received,(ROOT/'firmware/TAC75_ID2782_V502_RAM1_EXPERIMENTAL.bin').read_bytes()[0x5000:])
  self.assertEqual(sum(p[:2]==b'\xba\xc0' for p in f.commands),1)
 def test_restore_transfer(self):
  f=Fake('original')
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:r=self.service(f,t).flash('original',True)
  self.assertFalse(r['final_identity']['rgb_ram_firmware'])
  self.assertEqual(f.received,(ROOT/'firmware/TAC75_ID2782_V502_original.bin').read_bytes()[0x5000:])
 def test_wrong_begin_stops_without_payload(self):
  f=Fake(wrong_start=True)
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:
   with self.assertRaises(ValidationError):self.service(f,t).flash('experimental',True)
  self.assertEqual(f.received,b'')
  self.assertEqual(sum(p[:2]==b'\xba\xc0' for p in f.commands),1)
 def test_failure_no_retry_or_automatic_rollback(self):
  f=Fake(fail_block=10)
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:
   with self.assertRaises(OSError):self.service(f,t).flash('experimental',True)
  self.assertEqual(f.block,10)
  self.assertEqual(sum(p[:2]==b'\xba\xc0' for p in f.commands),1)
  self.assertFalse(any(p[:2]==b'\xba\xc2' for p in f.commands))
 def test_checksum_rejection_stops(self):
  f=Fake(wrong_final=True)
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:
   with self.assertRaises(ValidationError):self.service(f,t).flash('experimental',True)
  self.assertEqual(sum(p[:2]==b'\xba\xc0' for p in f.commands),1)
 def test_wrong_port_no_payload(self):
  f=Fake(wrong_port=True)
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:
   with self.assertRaises(ValidationError):self.service(f,t).flash('experimental',True)
  self.assertEqual(f.received,b'')
 def test_wrong_capability_does_not_claim_success(self):
  f=Fake(wrong_cap=True)
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:
   with self.assertRaises(ValidationError):self.service(f,t).flash('experimental',True)
  self.assertEqual(sum(p[:2]==b'\xba\xc0' for p in f.commands),1)
 def test_cold_recovery_requires_known_device(self):
  f=Fake('original',initial_boot=True)
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:
   with self.assertRaises(ValidationError):self.service(f,t).flash('original',True,True)
  self.assertEqual(f.commands,[])
 def test_cold_recovery_known_port(self):
  f=Fake('original',initial_boot=True)
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:
   Path(t,'known_device.json').write_text(json.dumps({'device_id':2782,'port':PORT}))
   r=self.service(f,t).flash('original',True,True)
  self.assertEqual(r['final_identity']['device_id'],2782)
  self.assertEqual(f.commands[0][:2],b'\xba\xc0')
 def test_unconfirmed_cold_recovery_no_io(self):
  f=Fake('original',initial_boot=True)
  with tempfile.TemporaryDirectory(dir=ROOT/"tests") as t:
   with self.assertRaises(ValidationError):self.service(f,t).flash('original',True,False)
  self.assertEqual(f.commands,[])
 def test_frame_format(self):
  p=frame_packets(bytes(range(249)),15)
  self.assertEqual([x[6] for x in p],[56,56,56,56,25,0])
  self.assertTrue(all(sum(x[:8])&255==255 for x in p))
  self.assertEqual(b''.join(x[8:8+x[6]] for x in p[:5]),bytes(range(249)))
  self.assertEqual(p[-1][3],2)
 def test_bad_frame_rejected(self):
  with self.assertRaises(ValidationError):frame_packets(bytes(250),0)
 def test_rgb_original_rejects_before_sending(self):
  f=Fake('original');s=RGBSession(f)
  with self.assertRaises(ValidationError):s.connect()
  self.assertEqual(f.commands,[])
 def test_transport_max_limit(self):
  with self.assertRaises(ValidationError):transfer_in_boot(None,b'x'*65)
 def test_plans_both_images(self):
  self.assertEqual(make_plan(ROOT,'experimental')['blocks'],1863)
  self.assertEqual(make_plan(ROOT,'original')['blocks'],1769)
 def test_no_arbitrary_image_target(self):
  with self.assertRaises(ValidationError):make_plan(ROOT,'another keyboard')

if __name__=='__main__':unittest.main(verbosity=2)
