"""English firmware manager. Launching never starts an update."""
from pathlib import Path
import sys,json,queue,threading,time
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog,filedialog
from lab_core import UpdateService,verify_package,make_plan,RGBSession

VERSION='0.4.0-rc.1'
BG='#0d1421';CARD='#162235';TEXT='#edf3ff';MUTED='#a5b5cc';ACCENT='#68dbc5'
def resource_root():return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
def portable_root():return Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]

class App:
 def __init__(self,root):
  self.root=root;self.data=resource_root();self.portable=portable_root();self.service=UpdateService(self.data,self.portable/'dados')
  self.q=queue.Queue();self.busy=False;self.writing=False;self.identity=None;self.valid=False
  self.present=tk.BooleanVar(value=False);self.cold=tk.BooleanVar(value=False);self.progress=tk.DoubleVar(value=0)
  self.status=tk.StringVar(value='Ready. Check your keyboard or preview an update without USB writes.')
  self.device=tk.StringVar(value='Not checked');self.firmware=tk.StringVar(value='—');self.ram=tk.StringVar(value='—');self.package=tk.StringVar(value='Checking package…')
  root.title(f'Akko TAC75 HE · Firmware Manager {VERSION}');root.geometry('1160x880');root.minsize(1100,840);root.configure(bg=BG)
  style=ttk.Style();style.theme_use('clam')
  style.configure('TButton',font=('Segoe UI',10),padding=(13,9),background='#273b56',foreground=TEXT,borderwidth=0)
  style.map('TButton',background=[('active','#345072'),('disabled','#1c293c')],foreground=[('disabled','#718096')])
  style.configure('Accent.TButton',background=ACCENT,foreground='#0b2523');style.map('Accent.TButton',background=[('active','#91ead9'),('disabled','#233c42')])
  style.configure('TCheckbutton',font=('Segoe UI',10),background=CARD,foreground=TEXT);style.map('TCheckbutton',background=[('active',CARD)],foreground=[('disabled','#718096')])
  style.configure('Horizontal.TProgressbar',background=ACCENT,troughcolor='#26354b',borderwidth=0)
  side=tk.Frame(root,bg='#101c2d',width=196);side.pack(side='left',fill='y');side.pack_propagate(False)
  self.label(side,'TAC75',24,True,ACCENT).pack(anchor='w',padx=22,pady=(28,0))
  self.label(side,'FIRMWARE MANAGER',9,False,MUTED).pack(anchor='w',padx=22,pady=(3,28))
  for item in ['01  Check','02  Preview','03  Install / Restore','04  Test lighting']:self.label(side,item,11,True).pack(anchor='w',padx=22,pady=14)
  self.label(side,f'L30k\nVersion {VERSION}\nExperimental release',10,False,MUTED).pack(anchor='sw',side='bottom',padx=22,pady=24)
  body=tk.Frame(root,bg=BG);body.pack(side='left',fill='both',expand=True,padx=24,pady=22)
  self.label(body,'Akko TAC75 HE',25,True).pack(anchor='w');self.label(body,'Install RAM lighting firmware, or return to the official V502.',11,False,MUTED).pack(anchor='w',pady=(3,12))
  tk.Label(body,text='STILL IN TESTING · Use at your own risk. No warranty or guaranteed recovery.',bg='#3b2c1d',fg='#ffdb9d',font=('Segoe UI',10,'bold'),anchor='w',padx=13,pady=10).pack(fill='x',pady=(0,13))
  cards=tk.Frame(body,bg=BG);cards.pack(fill='x')
  for column,(title,var) in enumerate([('DEVICE',self.device),('FIRMWARE',self.firmware),('RAM LIGHTING',self.ram)]):
   card=tk.Frame(cards,bg=CARD,padx=14,pady=12);card.grid(row=0,column=column,sticky='nsew',padx=(0,8 if column<2 else 0));cards.columnconfigure(column,weight=1)
   self.label(card,title,9,False,MUTED).pack(anchor='w');tk.Label(card,textvariable=var,font=('Segoe UI',15,'bold'),fg=TEXT,bg=CARD).pack(anchor='w',pady=(4,0))
  row=tk.Frame(body,bg=BG);row.pack(fill='x',pady=12)
  self.diag=ttk.Button(row,text='Check keyboard',command=self.diagnose,style='Accent.TButton');self.diag.pack(side='left')
  self.sim=ttk.Button(row,text='Preview update / restore',command=self.simulate);self.sim.pack(side='left',padx=8)
  self.export=ttk.Button(row,text='Export plan',command=self.export_plan);self.export.pack(side='left')
  tk.Label(body,textvariable=self.package,bg=BG,fg=MUTED,font=('Segoe UI',9),anchor='w').pack(fill='x',pady=(0,10))
  update=tk.Frame(body,bg=CARD,padx=16,pady=14);update.pack(fill='x');self.label(update,'Firmware actions',14,True).pack(anchor='w')
  self.label(update,'Entering update mode erases the application and may reset settings.\nIf neither the application nor the bootloader is reachable, this app cannot recover the keyboard.',10,False,MUTED).pack(anchor='w',pady=8)
  self.check=ttk.Checkbutton(update,text='I am at the keyboard and accept the experimental firmware risks and lack of guaranteed recovery.',variable=self.present,command=self.update_buttons);self.check.pack(anchor='w',pady=4)
  self.coldcheck=ttk.Checkbutton(update,text='Recovery only: power-cycled into bootloader, on the previously recorded USB port.',variable=self.cold,command=self.update_buttons);self.coldcheck.pack(anchor='w',pady=4)
  row=tk.Frame(update,bg=CARD);row.pack(fill='x',pady=(10,0))
  self.install=ttk.Button(row,text='Install RAM lighting firmware',command=lambda:self.flash('experimental'),state='disabled',style='Accent.TButton');self.install.pack(side='left')
  self.restore=ttk.Button(row,text='Restore official V502',command=lambda:self.flash('original'),state='disabled');self.restore.pack(side='left',padx=8)
  test=tk.Frame(body,bg=CARD,padx=16,pady=13);test.pack(fill='x',pady=12);self.label(test,'Lighting check',13,True).pack(anchor='w')
  self.label(test,'Disable the keyboard in SignalRGB before a test. The direct plugin needs no bridge app.',10,False,MUTED).pack(anchor='w',pady=(3,9))
  row=tk.Frame(test,bg=CARD);row.pack(fill='x')
  self.rgbtest=ttk.Button(row,text='Test Esc / A / W · 3 seconds',command=self.test_rgb,state='disabled');self.rgbtest.pack(side='left')
  self.stop=ttk.Button(row,text='Return to built-in effects',command=self.stop_rgb,state='disabled');self.stop.pack(side='left',padx=8)
  ttk.Progressbar(body,maximum=100,variable=self.progress).pack(fill='x',pady=(0,8))
  tk.Label(body,textvariable=self.status,bg=BG,fg=TEXT,font=('Segoe UI',10),wraplength=880,anchor='w',justify='left').pack(fill='x',pady=(0,9))
  self.log=tk.Text(body,height=8,bg='#09111d',fg='#bbd4e8',font=('Consolas',9),relief='flat',wrap='word',padx=12,pady=10);self.log.pack(fill='both',expand=True);self.log.configure(state='disabled')
  self.label(body,'No automatic updates. This manager is not needed while SignalRGB controls the LEDs.',9,False,MUTED).pack(anchor='w',pady=(8,0))
  try:
   self.meta,_,_=verify_package(self.data);self.valid=True;self.package.set('Package verified · ID2782 · V502 RAM1 · both firmware image hashes match')
   self.append(f'Firmware Manager {VERSION} — L30k. No update has started.');self.append('RAM receiver: 544 bytes; reserved stack: 15,840 bytes. Hardware peak stack and forced recovery remain unverified.')
  except Exception as e:self.package.set('Invalid or incomplete firmware package');self.append('PACKAGE ERROR: '+str(e))
  self.update_buttons();root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)
 def label(self,parent,text,size=10,bold=False,color=TEXT):return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,font=('Segoe UI',size,'bold' if bold else 'normal'),anchor='w',justify='left')
 def append(self,text):
  self.log.configure(state='normal');self.log.insert('end',str(text)+'\n');self.log.see('end');self.log.configure(state='disabled')
 def update_buttons(self):
  common='normal' if not self.busy and self.valid else 'disabled'
  for b in [self.diag,self.sim,self.export]:b.configure(state=common)
  for b in [self.check,self.coldcheck]:b.configure(state='disabled' if self.busy else 'normal')
  can=not self.busy and self.valid and self.present.get();known=(self.portable/'dados/known_device.json').exists()
  self.install.configure(state='normal' if can and self.identity else 'disabled');self.restore.configure(state='normal' if can and (self.identity or self.cold.get() and known) else 'disabled')
  rgb=not self.busy and bool(self.identity and self.identity.get('rgb_ram_firmware'))
  for b in [self.rgbtest,self.stop]:b.configure(state='normal' if rgb else 'disabled')
 def job(self,name,fn,writing=False):
  if self.busy:return
  self.busy=True;self.writing=writing;self.progress.set(0);self.status.set(name);self.update_buttons()
  def run():
   try:self.q.put(('done',(name,fn())))
   except Exception as e:self.q.put(('error',str(e)))
  threading.Thread(target=run,daemon=True).start()
 def diagnose(self):self.job('Checking device identity and RAM lighting support…',self.service.diagnose)
 def simulate(self):self.job('Building update plans without opening USB…',lambda:{'simulation':[make_plan(self.data,t) for t in ['experimental','original']]})
 def export_plan(self):
  path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',initialfile='TAC75_update_plans.json',filetypes=[('JSON','*.json')])
  if path:
   try:Path(path).write_text(json.dumps({'app_version':VERSION,'experimental':make_plan(self.data,'experimental'),'restore':make_plan(self.data,'original')},indent=2),encoding='utf8')
   except Exception as e:messagebox.showerror('Export failed',str(e),parent=self.root)
 def flash(self,target):
  if self.busy or not self.present.get():return
  label='EXPERIMENTAL V502 RAM1' if target=='experimental' else 'OFFICIAL V502'
  answer=simpledialog.askstring('Confirm firmware update',f'Install {label} on ID2782?\n\nEXPERIMENTAL: still being tested. Use at your own risk.\nNo warranty or guaranteed recovery. The maintainer disclaims\nliability to the extent permitted by applicable law.\n\nThe application is erased before transfer. Keep USB connected.\nRecovery after an application hang is not proven.\n\nType ID2782 to start now:',parent=self.root)
  if answer is None:return
  if answer.strip()!='ID2782':
   self.append('Confirmation did not match. No update was started.');messagebox.showinfo('Update not started','Type exactly ID2782 to confirm. No firmware was written.',parent=self.root);return
  cold=self.cold.get()
  self.job('Writing firmware — keep the keyboard connected.',lambda:self.service.flash(target,operator_confirmed=True,recovery_cold_boot_confirmed=cold,progress=lambda p:self.q.put(('progress',100*p)),log=lambda s:self.q.put(('log',s))),writing=True)
 def test_rgb(self):
  def test():
   session=RGBSession();session.connect()
   try:
    frame=bytearray(249)
    for index,color in [(0,(255,0,0)),(57,(0,255,0)),(32,(0,0,255))]:frame[index*3:index*3+3]=bytes(color)
    session.send_frame(frame);time.sleep(3)
   finally:session.close()
   return {'rgb_test':True}
  self.job('Three-second RAM test: Esc red, A green, W blue; then built-in effects resume.',test)
 def stop_rgb(self):
  if self.busy:return
  def release():
   session=RGBSession();session.connect();session.close();return {'effects_resumed':True}
  self.job('Releasing RAM lighting control…',release)
 def set_identity(self,info):
  self.identity=info;self.device.set('ID2782');self.firmware.set(info['firmware']);self.ram.set('Available' if info.get('rgb_ram_firmware') else 'Not installed')
 def poll(self):
  try:
   while True:
    kind,value=self.q.get_nowait()
    if kind=='log':self.append(value);continue
    if kind=='progress':self.progress.set(value);continue
    self.busy=False;self.writing=False
    if kind=='error':self.append('STOPPED: '+value);self.status.set('Operation stopped. Read the log; no automatic retry was made.')
    else:
     _,result=value
     if 'device_id' in result:self.set_identity(result);self.append('Identity and USB location recorded locally. No firmware written.');self.status.set('Keyboard checked. Choose an action when ready.')
     elif 'final_identity' in result:self.set_identity(result['final_identity']);self.append('Bootloader checksum and returning identity verified. No full flash readback was performed.');self.status.set('Firmware transfer completed and device identity verified.')
     elif 'simulation' in result:
      for p in result['simulation']:self.append(f"PREVIEW {p['target']}: {p['blocks']} blocks, {p['application_bytes']} bytes. USB was not opened.")
      self.status.set('Preview complete. No firmware written.')
     elif 'rgb_test' in result:self.append('RAM test finished; built-in effects resumed.');self.status.set('Lighting test finished.')
     else:self.append('External lighting released.');self.status.set('Built-in effects resumed.')
    self.update_buttons()
  except queue.Empty:pass
  self.root.after(100,self.poll)
 def close(self):
  if self.writing:messagebox.showinfo('Update in progress','Wait for the update to finish. Keep USB connected.',parent=self.root);return
  if self.busy:self.status.set('Wait for the current operation to finish before closing.');return
  self.root.destroy()

if __name__=='__main__':
 root=tk.Tk();App(root);root.mainloop()
