#!/usr/bin/env python3
"""Install the requested original brazier scene locally, outside tracked source."""
import hashlib
from pathlib import Path
import urllib.request

URL = 'https://static.runelite.net/loginscreens/normal.jpg'
SHA256 = '2db7f4e9f3a2fb85ee85211e7a21434697c2acde926b6916931dc58cf26d9272'


def main():
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
