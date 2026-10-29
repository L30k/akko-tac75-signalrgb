"""Build the Windows manager after obtaining/building the verified firmware files."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from lab_core import verify_package
def main():
 verify_package(ROOT)
 subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--onefile','--windowed',
  '--name','TAC75_Firmware_Manager','--distpath',str(ROOT/'dist'),
  '--workpath',str(ROOT/'build'),'--specpath',str(ROOT/'build'),
  '--add-data',str(ROOT/'firmware')+';firmware',
  '--add-data',str(ROOT/'validation_firmware.json')+';.',
  str(ROOT/'app/app.py')],check=True)
if __name__=='__main__':main()
