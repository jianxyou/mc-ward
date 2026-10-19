"""Patch prismarine-viewer's browser bundles so worlds below y=0 render.

prismarine-viewer 1.33 only meshes sections with 0 <= y < 256 and indexes
`column.sections` without the column's minY offset, so a 1.18+ world whose
blocks sit at negative y (every superflat world, including Sophie's Hospital)
shows nothing but entities. Run this once after `npm install`:

    python3 patch_viewer.py
"""
import os
import sys

PUB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'node_modules', 'prismarine-viewer', 'public')

PATCHES = {
    'index.js': [
        ('for(let i=0;i<256;i+=16)', 'for(let i=-64;i<320;i+=16)'),
    ],
    'worker.js': [
        ('i.sections[Math.floor(a/16)]', 'i.sections[Math.floor((a-(i.minY||0))/16)]'),
        ('l.sections[Math.floor(n/16)]', 'l.sections[Math.floor((n-(l.minY||0))/16)]'),
        # face culling: every face whose neighbour is below y=0 was skipped
        ('position.y<0)continue', 'position.y<-64)continue'),
    ],
}

for fname, pairs in PATCHES.items():
    path = os.path.join(PUB, fname)
    src = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if new in src and old not in src:
            print(f'{fname}: already patched ({new[:40]}...)')
            continue
        n = src.count(old)
        if n == 0:
            sys.exit(f'{fname}: pattern not found, viewer version changed? {old}')
        src = src.replace(old, new)
        print(f'{fname}: replaced {n} occurrence(s) of {old[:40]}...')
    open(path, 'w', encoding='utf-8').write(src)
print('done')
