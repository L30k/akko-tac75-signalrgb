"""Obtain and verify the exact vendor base. No USB/device access."""
from pathlib import Path
import argparse,hashlib,json,urllib.request,zlib

ROOT=Path(__file__).resolve().parents[1]
def prepare(blob,meta):
    if len(blob)==meta['decoded_bytes']:
        data=blob
    else:
        decoder=zlib.decompressobj(-15)
        data=decoder.decompress(blob,meta['decoded_bytes']+1)
        if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
            raise ValueError('Unexpected compressed firmware structure')
    if len(data)!=meta['decoded_bytes'] or hashlib.sha256(data).hexdigest()!=meta['decoded_sha256']:
        raise ValueError('Vendor base mismatch; refusing to write a firmware file')
    return data
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--download',action='store_true');group.add_argument('--file',type=Path)
    args=parser.parse_args();meta=json.loads((ROOT/'firmware/base.json').read_text())
    if args.download:
        with urllib.request.urlopen(meta['download_url'],timeout=30) as response:blob=response.read(1048577)
        if len(blob)>1048576:raise ValueError('Download exceeds allowed size')
    else:blob=args.file.read_bytes()
    data=prepare(blob,meta)
    output=ROOT/'firmware/TAC75_ID2782_V502_original.bin'
    output.write_bytes(data);print('Verified exact V502 base:',output)
if __name__=='__main__':main()
