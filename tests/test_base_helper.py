import importlib.util,unittest,json,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('base_helper',ROOT/'tools/prepare_base.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
class BaseTests(unittest.TestCase):
 def test_exact_base_and_compressed_input(self):
  meta=json.loads((ROOT/'firmware/base.json').read_text());data=(ROOT/'firmware/TAC75_ID2782_V502_original.bin').read_bytes()
  self.assertEqual(helper.prepare(data,meta),data)
  compressor=zlib.compressobj(wbits=-15);compressed=compressor.compress(data)+compressor.flush()
  self.assertEqual(helper.prepare(compressed,meta),data)
 def test_wrong_base_is_rejected(self):
  meta=json.loads((ROOT/'firmware/base.json').read_text());data=bytearray((ROOT/'firmware/TAC75_ID2782_V502_original.bin').read_bytes());data[-1]^=1
  with self.assertRaises(ValueError):helper.prepare(bytes(data),meta)
