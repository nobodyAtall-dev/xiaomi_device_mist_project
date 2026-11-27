#!/usr/bin/env python3
"""Normalize every remaining direct allocator V1/V2 overlap in the generated vendor tree."""
import subprocess, re, sys, hashlib, json
from pathlib import Path
root=Path(sys.argv[1]); dev=root/'device'; vendor=root/'vendor'
allocator='android.hardware.graphics.allocator-V1-ndk'
common='android.hardware.camera.common-V2-ndk'
targets={}
def cmd(*a):return subprocess.check_output(a,text=True)
def needed(p):return cmd('patchelf','--print-needed',str(p)).splitlines()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
bp=vendor/'Android.bp'; content=bp.read_text()
fix=dev/'extract-files.py'; source=fix.read_text()
marker='    blob_fixups={\n'
assert source.count(marker)==1
entries=[]; plans=[]
# Scan every generated module, not just the first Soong error.
for block in re.split(r'(?=^[a-z_]+ \{\n)',content,flags=re.M):
    if '"'+allocator+'"' not in block:continue
    name=re.search(r'^    name: "([^"]+)"',block,re.M)
    assert name and block.startswith('cc_prebuilt_library_shared {'),block[:200]
    assert '"android.hardware.graphics.allocator-V2-ndk"' in block,name.group(1)
    paths=re.findall(r'"proprietary/(vendor/[^"]+\.so)"',block)
    assert len(paths)==1,(name.group(1),paths)
    targets[name.group(1)]=([(allocator,'android.hardware.graphics.allocator-V2-ndk')],paths[0])
assert targets, 'No remaining allocator conflicts'
print('All direct allocator conflict roots:',sorted(targets))
for name,(pairs,rel) in targets.items():
    blob=vendor/'proprietary'/rel
    pattern=r'^cc_prebuilt_library_shared \{\n    name: "'+re.escape(name)+r'",[\s\S]*?^\}\n'
    matches=list(re.finditer(pattern,content,re.M));assert len(matches)==1,name
    block=matches[0].group()
    original=needed(blob); version_info=cmd('readelf','--version-info',str(blob))
    for remove,keep in pairs:
        assert original.count(remove+'.so')==1 and keep+'.so' in original,(name,original)
        assert remove+'.so' not in version_info, 'Versioned ELF reference requires separate ABI review: '+remove
        assert block.count('                "'+remove+'",\n')==1
        block=block.replace('                "'+remove+'",\n','')
    content=content[:matches[0].start()]+block+content[matches[0].end():]
    assert repr(rel) not in source
    entries.append('        '+repr(rel)+': blob_fixup()\n'+''.join('            .remove_needed('+repr(remove+'.so')+')\n' for remove,_ in pairs).rstrip()+',\n')
    plans.append((blob,pairs,original))
report=[]
for blob,pairs,original in plans:
    before=digest(blob)
    for remove,_ in pairs:subprocess.run(['patchelf','--remove-needed',remove+'.so',str(blob)],check=True)
    expected=[n for n in original if n not in {remove+'.so' for remove,_ in pairs}]
    assert needed(blob)==expected,(str(blob),needed(blob),expected)
    assert cmd('readelf','-h',str(blob)).find('AArch64')!=-1
    report.append({'file':str(blob.relative_to(vendor)),'before':before,'after':digest(blob),'needed_before':original,'needed_after':expected})
assert '"'+allocator+'"' not in content
assert '"'+common+'"' not in content
bp.write_text(content)
fix.write_text(source.replace(marker,marker+''.join(entries),1))
compile(fix.read_text(),str(fix),'exec')
(root/'reports'/'camera-aidl-batch.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
