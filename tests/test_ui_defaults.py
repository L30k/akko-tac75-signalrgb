import sys,unittest,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
import tkinter as tk
from app import App

class Defaults(unittest.TestCase):
 def setUp(self):self.root=tk.Tk();self.root.withdraw();self.app=App(self.root)
 def tearDown(self):
  for callback in self.root.tk.call('after','info'):self.root.after_cancel(callback)
  self.root.destroy()
 def test_flash_controls_start_disarmed(self):
  self.assertFalse(self.app.present.get());self.assertFalse(self.app.cold.get())
  self.assertTrue(self.app.install.instate(['disabled']))
  self.assertTrue(self.app.restore.instate(['disabled']))
 def test_unarmed_flash_does_not_reach_service(self):
  with patch.object(self.app.service,'flash',side_effect=AssertionError('Must not flash')) as call:
   self.app.flash('experimental');self.app.flash('original')
   call.assert_not_called()
 def test_wrong_confirmation_has_message_and_no_write(self):
  self.app.present.set(True)
  with patch('app.simpledialog.askstring',return_value='2782'),patch('app.messagebox.showinfo') as notice,patch.object(self.app.service,'flash') as call:
   self.app.flash('experimental')
   notice.assert_called_once();call.assert_not_called();self.assertFalse(self.app.writing)
 def test_canceled_confirmation_never_writes(self):
  self.app.present.set(True)
  with patch('app.simpledialog.askstring',return_value=None),patch.object(self.app.service,'flash') as call:
   self.app.flash('experimental');call.assert_not_called()
 def test_close_during_update_is_blocked(self):
  self.app.writing=True
  with patch('app.messagebox.showinfo') as notice,patch.object(self.root,'destroy') as destroy:
   self.app.close();notice.assert_called_once();destroy.assert_not_called()
 def test_simulation_without_hardware(self):
  with patch('lab_core.Hardware',side_effect=AssertionError('No hardware in simulation')):
   self.app.simulate()
   until=time.time()+2
   while self.app.busy and time.time()<until:self.root.update();time.sleep(.01)
   self.assertFalse(self.app.busy)
   self.assertFalse(self.app.present.get());self.assertFalse(self.app.writing)
  self.assertIn('USB was not opened',self.app.log.get('1.0','end'))

if __name__=='__main__':unittest.main(verbosity=2)
