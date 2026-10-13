#!/usr/bin/env python3
"""Install the requested original brazier scene locally, outside tracked source."""
import argparse
import struct
import hashlib
from pathlib import Path
import urllib.request

URL = 'https://static.runelite.net/loginscreens/normal.jpg'
SHA256 = '2db7f4e9f3a2fb85ee85211e7a21434697c2acde926b6916931dc58cf26d9272'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spritesheet',type=Path,help='Install the owner-supplied 640x480 eight-frame brazier PNG locally.')
    args=parser.parse_args()
    if args.spritesheet:
        data=args.spritesheet.read_bytes()
        if data[:8]!=b'\x89PNG\r\n\x1a\n' or data[12:16]!=b'IHDR' or len(data)<24 or struct.unpack('>II',data[16:24])!=(640,480):
            raise ValueError('Expected a 640x480 PNG with the supplied eight-frame layout.')
        target=Path(__file__).resolve().parents[1]/'.runtime/launcher-art/brazier-flames.png'
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_suffix('.tmp');temporary.write_bytes(data);temporary.replace(target)
        print(target)
        return
    with urllib.request.urlopen(URL, timeout=30) as response:
        data = response.read(2 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('Brazier artwork checksum differs from the original RuneLite background.')
    target = Path(__file__).resolve().parents[1] / '.runtime/launcher-art/brazier.jpg'
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_bytes(data)
    temporary.replace(target)
    print(target)


if __name__ == '__main__':
    main()
