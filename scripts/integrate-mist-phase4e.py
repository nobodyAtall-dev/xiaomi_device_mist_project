#!/usr/bin/env python3
"""Phase 4E: add exact stock missing vendor dependencies, not source interfaces."""
import json, re, sys, collections
from pathlib import Path
from elftools.elf.elffile import ELFFile
w=Path(sys.argv[1]); dump=w/'dump'; dev=w/'android/device/xiaomi/mist'; ven=w/'android/vendor/xiaomi/mist'; reports=w/'reports'
pl=dev/'proprietary-files.txt'; old=pl.read_text()
listed={l.strip().lstrip('-').split('|')[0].split(';')[0].split(':')[0] for l in old.splitlines() if l.strip() and not l.lstrip().startswith('#')}
stock={str(p.relative_to(dump)):p for p in (dump/'vendor').rglob('*') if p.is_file() and not p.is_symlink()}
def elf(p):
    with p.open('rb') as f:
        if f.read(4)!=b'\x7fELF':return None
        f.seek(0); e=ELFFile(f); tags=[t for s in e.iter_segments() if s.header.p_type=='PT_DYNAMIC' for t in s.iter_tags()]
        return (e.elfclass,[t.needed for t in tags if t.entry.d_tag=='DT_NEEDED'],next((t.soname for t in tags if t.entry.d_tag=='DT_SONAME'),p.name))
have=set(); deps=collections.defaultdict(set)
for p in (ven/'proprietary/vendor').rglob('*'):
    if not p.is_file() or p.is_symlink():continue
    m=elf(p)
    if m:
        have.add((m[0],m[2]));have.add((m[0],p.name))
        for n in m[1]:deps[(m[0],n)].add(str(p.relative_to(ven/'proprietary')))
# Exact stock runtime candidates only, no generic platform or AIDL blobs.
approved={'libhdr10plus.so','libqti_vndfwk_detect.so','libc++_shared.so'}
chosen=set(); unresolved={}
for (bits,n),users in sorted(deps.items()):
    if (bits,n) in have:continue
    if n not in approved:continue
    prefix='vendor/lib64/' if bits==64 else 'vendor/lib/'
    path=prefix+n
    if path in listed or path not in stock:
        unresolved[f'{bits}:{n}']=sorted(users);continue
    m=elf(stock[path])
    if not m or m[0]!=bits or m[2]!=n:
        unresolved[f'{bits}:{n}']=sorted(users);continue
    chosen.add(path)
# Camera RC invokes this exact stock helper; preserve existing service declaration.
rc=ven/'proprietary/vendor/etc/init/vendor.qti.camera.provider-service_64.rc'
helper='vendor/bin/init.qti.cam.perfopt.sh'
if rc.is_file() and '/'+helper in rc.read_text() and helper in stock and helper not in listed:chosen.add(helper)
new=sorted(chosen)
if new:pl.write_text(old.rstrip()+'\n\n# Mist Phase 4E remaining stock runtime dependencies\n'+'\n'.join(new)+'\n')
(reports/'phase4e-selection.json').write_text(json.dumps({'added':new,'unresolved_approved':unresolved,'missing_sonames_before_extraction':{f'{b}:{n}':sorted(u) for (b,n),u in sorted(deps.items()) if (b,n) not in have}},indent=2))
print('Selected',len(new),'additional stock assets:',new)
