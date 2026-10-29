"""TAC75 experimental updater. Importing this module never opens USB.

Read-only diagnostics and simulation are the default UI actions. Flashing needs
an explicit future user action; no test in this package calls real flash methods.
"""
from __future__ import annotations
from pathlib import Path
import ctypes, hashlib, json, re, struct, time, uuid
from dataclasses import dataclass, asdict
from tac75_readonly import feature_layout,parse_identity,packet,ValidationError,ORIGINAL_SHA256

VID,PID,DEVICE_ID=0x3151,0x502D,2782
BOOT_PIDS=(0x5024,0x502A)

def digest(b): return hashlib.sha256(b).hexdigest()
def protocol_packet(op,sequence=0,block=0,payload=b''):
    if len(payload)>56 or not all(0<=v<=255 for v in [op,sequence,block]):
        raise ValidationError('RGB packet outside allowed bounds.')
    p=bytearray(64);p[:7]=bytes([15,167,1,op,sequence,block,len(payload)])
    p[7]=255-(sum(p[:7])&255);p[8:8+len(payload)]=payload
    return bytes(p)

def frame_packets(frame,sequence):
    if len(frame)!=249:raise ValidationError('A frame must contain exactly 83 RGB colors.')
    return [protocol_packet(1,sequence,b,frame[b*56:(b+1)*56]) for b in range(5)]+[protocol_packet(2,sequence)]

def port_location(path):
    """Read-only Windows CM LocationPaths; remove interface-only USBMI suffix."""
    if isinstance(path,bytes):path=path.decode(errors='strict')
    parts=path.removeprefix('\\\\?\\').split('#')
    if len(parts)<3:raise ValidationError('Unrecognized HID path.')
    instance='\\'.join(parts[:3])
    dll=ctypes.WinDLL('cfgmgr32')
    class KEY(ctypes.Structure):
        _fields_=[('guid',ctypes.c_ubyte*16),('pid',ctypes.c_uint32)]
    key=KEY((ctypes.c_ubyte*16).from_buffer_copy(uuid.UUID('a45c254e-df1c-4efd-8020-67d146a850e0').bytes_le),37)
    locate=dll.CM_Locate_DevNodeW;locate.argtypes=[ctypes.POINTER(ctypes.c_uint32),ctypes.c_wchar_p,ctypes.c_uint32];locate.restype=ctypes.c_uint32
    prop=dll.CM_Get_DevNode_PropertyW
    prop.argtypes=[ctypes.c_uint32,ctypes.POINTER(KEY),ctypes.POINTER(ctypes.c_uint32),ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32),ctypes.c_uint32]
    prop.restype=ctypes.c_uint32
    parent=dll.CM_Get_Parent;parent.argtypes=[ctypes.POINTER(ctypes.c_uint32),ctypes.c_uint32,ctypes.c_uint32];parent.restype=ctypes.c_uint32
    node=ctypes.c_uint32()
    if locate(ctypes.byref(node),instance,0)!=0:raise ValidationError('Could not locate the physical keyboard USB port.')
    for _ in range(8):
        typ=ctypes.c_uint32();size=ctypes.c_uint32()
        prop(node.value,ctypes.byref(key),ctypes.byref(typ),None,ctypes.byref(size),0)
        if 2<=size.value<=65536:
            buf=(ctypes.c_ubyte*size.value)()
            if prop(node.value,ctypes.byref(key),ctypes.byref(typ),buf,ctypes.byref(size),0)==0:
                paths=bytes(buf).decode('utf-16le').rstrip('\0').split('\0')
                paths=[re.sub(r'#USBMI\([^)]*\)$','',x.upper()) for x in paths if 'USB(' in x.upper()]
                if paths:return sorted(paths)[0]
        p=ctypes.c_uint32()
        if parent(ctypes.byref(p),node.value,0)!=0:break
        node=p
    raise ValidationError('Stable USB location unavailable; update refused.')


class Handle:
    def __init__(self,hid_module,device):
        self.h=hid_module.device();self.h.open_path(device['path'])
        try:feature_layout(bytes(self.h.get_report_descriptor()))
        except Exception:self.h.close();raise
    def send(self,p):
        if len(p)!=64:raise ValidationError('Invalid HID packet size.')
        count=self.h.send_feature_report(b'\0'+bytes(p))
        if count not in [64,65]:raise ValidationError(f'Incomplete HID write: {count}.')
    def receive(self):
        r=bytes(self.h.get_feature_report(0,65))
        if len(r)==65 and r[0]==0:r=r[1:]
        if len(r)!=64:raise ValidationError('Incomplete HID reply.')
        return r
    def exchange(self,p,delay=.05):self.send(p);time.sleep(delay);return self.receive()
    def close(self):self.h.close()


class Hardware:
    def __init__(self):
        import hid
        self.hid=hid
    def normal(self):
        return [d for d in self.hid.enumerate(VID,PID) if d.get('usage_page')==65535 and d.get('usage')==2 and d.get('interface_number')==2]
    def boot(self,location):
        found=[]
        for pid in BOOT_PIDS:
            for d in self.hid.enumerate(VID,pid):
                if d.get('usage_page')==65281 and d.get('usage')==1 and d.get('interface_number')==0:
                    if port_location(d['path'])==location:found.append(d)
        return found
    def open(self,d):return Handle(self.hid,d)
    def inspect(self,d):
        h=self.open(d)
        try:
            identity=parse_identity(h.exchange(packet(0x8F)))
            if identity['firmware']!='V502':raise ValidationError('Expected firmware base: ID2782_V502.')
            cap=h.exchange(protocol_packet(4))
            compatible=cap[8:16]==b'AK75RAM1' and cap[16:18]==b'\x53\x01'
            return {**identity,'port':port_location(d['path']),
                    'rgb_ram_firmware':compatible,'rgb_ram_active':compatible and cap[24]==1}
        finally:h.close()


def verify_package(root):
    root=Path(root)
    meta=json.loads((root/'firmware/manifest.json').read_text(encoding='utf8'))
    validation=json.loads((root/'validation_firmware.json').read_text(encoding='utf8'))
    base=(root/'firmware/TAC75_ID2782_V502_original.bin').read_bytes()
    patched=(root/'firmware/TAC75_ID2782_V502_RAM1_EXPERIMENTAL.bin').read_bytes()
    if digest(base)!=ORIGINAL_SHA256 or digest(base)!=meta['original_sha256']:raise ValidationError('Original V502 hash mismatch.')
    if digest(patched)!=meta['patched_sha256'] or digest(patched)!=validation['patched_sha256']:raise ValidationError('Experimental image does not match the validation report.')
    if not validation['status'].startswith('PASS'):raise ValidationError('Image did not pass emulation.')
    if patched[:0x5000]!=base[:0x5000] or len(patched)>=0x28000:raise ValidationError('Invalid boot/application boundaries.')
    for data in [base,patched]:
        if len(data)<=0x5208 or len(data)%64:raise ValidationError('Misaligned or incomplete image.')
        if data[0x5000:0x500e]!=b'AT32F405 8KMKB':raise ValidationError('Invalid application identifier.')
    return meta,base,patched


def make_plan(root,target):
    meta,base,patched=verify_package(root)
    if target not in ['original','experimental']:raise ValidationError('Invalid target.')
    image=base if target=='original' else patched
    app=image[0x5000:]
    return {'target':target,'device_id':2782,'sha256':digest(image),'image_bytes':len(image),
            'application_bytes':len(app),'blocks':len(app)//64,'checksum':sum(app),
            'bootloader_written':False,'physical_validation_complete':False,
            'steps':['Identify ID2782/V502 and USB location','Save local session record',
                     'Enter bootloader (erases application)','Transfer blocks and verify checksum',
                     'Verify returning identity and USB location'],
            'limitation':'USB restore requires an accessible bootloader. Recovery from an application hang is not guaranteed.'}


def transfer_in_boot(handle,payload,progress=lambda p:None,sleep=time.sleep):
    """Exact vendor update framing, tested with mocks. NEVER retries C0 or data."""
    if not payload or len(payload)%64 or len(payload)>0x23000:raise ValidationError('Application outside allowed bounds.')
    blocks=len(payload)//64
    begin=bytearray(64);begin[0:2]=b'\xba\xc0';struct.pack_into('<H',begin,2,blocks);struct.pack_into('<I',begin,4,len(payload))
    begin[7]=255-(sum(begin[:7])&255)
    reply=handle.exchange(bytes(begin),.1)
    if reply[:2]!=b'\xab\xc0' or int.from_bytes(reply[2:4],'little')!=blocks:
        raise ValidationError('Bootloader did not acknowledge start. No automatic retry.')
    for block in range(blocks):
        handle.send(payload[block*64:(block+1)*64]);sleep(.01);progress((block+1)/blocks)
    final=bytearray(64);final[:2]=b'\xba\xc2';struct.pack_into('<H',final,2,blocks)
    struct.pack_into('<I',final,4,sum(payload));struct.pack_into('<I',final,8,len(payload))
    reply=handle.exchange(bytes(final),.1)
    if reply[:2]!=b'\xab\xc2' or reply[2:4]!=final[2:4] or reply[4]!=0x55:
        raise ValidationError('Bootloader verification failed. No automatic restore.')


class UpdateService:
    def __init__(self,root,state_dir,hardware=None,sleep=time.sleep):
        self.root=Path(root);self.state=Path(state_dir);self.hw=hardware;self.sleep=sleep
    def diagnose(self):
        if self.hw is None:self.hw=Hardware()
        devices=self.hw.normal()
        if len(devices)!=1:raise ValidationError('Connect exactly one TAC75 HE by cable and close other keyboard controllers.')
        info=self.hw.inspect(devices[0])
        self.state.mkdir(parents=True,exist_ok=True)
        (self.state/'known_device.json').write_text(json.dumps(info,indent=2),encoding='utf8')
        return info
    def wait_boot(self,port):
        for _ in range(100):
            candidates=self.hw.boot(port)
            if len(candidates)==1:return candidates[0]
            if len(candidates)>1:raise ValidationError('Multiple bootloaders at the expected USB location.')
            self.sleep(.25)
        raise ValidationError('Bootloader did not appear at the recorded USB location. Operation stopped.')
    def flash(self,target,operator_confirmed=False,recovery_cold_boot_confirmed=False,progress=lambda p:None,log=lambda s:None):
        if not operator_confirmed:raise ValidationError('Firmware update requires manual confirmation by the operator at the keyboard.')
        plan=make_plan(self.root,target)
        if self.hw is None:self.hw=Hardware()
        normal=self.hw.normal()
        if len(normal)==1:
            info=self.diagnose();port=info['port']
            log('ID2782/V502 and USB location verified. Entering update mode.')
            h=self.hw.open(normal[0])
            try:h.send(packet(0x7F,bytes([0x55,0xAA,0x55,0xAA])))
            except OSError:log('Interface reset during the command; checking bootloader USB location.')
            finally:h.close()
            self.sleep(1)
            boot=self.wait_boot(port)
        elif len(normal)==0 and target=='original' and recovery_cold_boot_confirmed:
            saved=self.state/'known_device.json'
            if not saved.exists():raise ValidationError('No previous ID2782 location record. Refusing to select another bootloader.')
            info=json.loads(saved.read_text(encoding='utf8'))
            if info.get('device_id')!=2782:raise ValidationError('Invalid recovery record.')
            port=info['port'];boot=self.wait_boot(port)
        else:raise ValidationError('Keyboard missing or ambiguous. For recovery, power-cycle and confirm bootloader mode at the recorded USB location.')
        progress(.1)
        image=(self.root/'firmware'/('TAC75_ID2782_V502_original.bin' if target=='original' else 'TAC75_ID2782_V502_RAM1_EXPERIMENTAL.bin')).read_bytes()
        h=self.hw.open(boot)
        try:transfer_in_boot(h,image[0x5000:],lambda p:progress(.1+.8*p),self.sleep)
        finally:h.close()
        log('Bootloader acknowledged checksum. Waiting for keyboard restart.')
        for _ in range(120):
            devices=self.hw.normal()
            if len(devices)==1:
                try:
                    final=self.hw.inspect(devices[0])
                    if final['port']!=port:raise ValidationError('Keyboard returned at another USB location.')
                    if final['rgb_ram_firmware']!=(target=='experimental'):raise ValidationError('Returning firmware signature does not match the selected target.')
                    progress(1)
                    result={'plan':plan,'final_identity':final,'boot_checksum_confirmed':True,'full_flash_readback':False}
                    (self.state/'last_update.json').write_text(json.dumps(result,indent=2),encoding='utf8')
                    return result
                except (OSError,ValidationError):pass
            self.sleep(.25)
        raise ValidationError('Transfer was acknowledged but the keyboard did not return with the expected identity. No automatic reflash.')


class RGBSession:
    def __init__(self,hardware=None):self.hw=hardware or Hardware();self.h=None;self.sequence=0
    def connect(self):
        ds=self.hw.normal()
        if len(ds)!=1:raise ValidationError('Keyboard missing or ambiguous.')
        info=self.hw.inspect(ds[0])
        if not info['rgb_ram_firmware']:raise ValidationError('RAM1 firmware is not installed. No colors sent.')
        self.h=self.hw.open(ds[0]);return info
    def send_frame(self,colors):
        if self.h is None:raise ValidationError('RGB session is not connected.')
        for p in frame_packets(bytes(colors),self.sequence):
            r=self.h.exchange(p,.002)
            expected=2 if p[3]==2 else 1
            if r[8]!=0xA5 or r[9]!=expected:raise ValidationError('Keyboard did not acknowledge the frame. Streaming stopped.')
        self.sequence=(self.sequence+1)&255
    def close(self):
        if self.h:
            try:self.h.exchange(protocol_packet(3),.01)
            finally:self.h.close();self.h=None
