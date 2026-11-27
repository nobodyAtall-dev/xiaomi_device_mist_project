#!/usr/bin/env python3
"""Review actual stock integration inputs without pretending a full Android build has passed."""
import json,sys,collections,subprocess,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
work=Path(sys.argv[1]); root=work/'android'; dump=work/'dump'; reports=work/'reports'
device=root/'device/xiaomi/mist'; vendor=root/'vendor/xiaomi/mist'; kernel=root/'kernel/xiaomi/mist-prebuilt'
def save(n,x): (reports/n).write_text(json.dumps(x,indent=2))
blobs=json.loads((reports/'blob-review.json').read_text())
deps=collections.defaultdict(list)
for e in blobs['unresolved_dependency_review']:deps[e['needed']].append(e)
save('dependency-review.json',[{'soname':n,'consumers':sorted({e['consumer'] for e in es}),'stock_candidates':sorted({p for e in es for p in e['stock_candidates']}),'classification':'stock candidate or platform provider' if any(e['stock_candidates'] for e in es) else 'platform provider or unresolved'} for n,es in sorted(deps.items())])
vintf=[]; errors=[]
for part in ('vendor','odm','system_ext','product'):
    for p in (dump/part/'etc/vintf').rglob('*.xml'):
        try:
            t=ET.parse(p).getroot()
            vintf.append({'path':str(p.relative_to(dump)),'type':t.tag,'attributes':t.attrib,'hals':[{'name':h.findtext('name'),'format':h.get('format'),'versions':[v.text for v in h.findall('version')],'instances':[v.text for v in h.findall('fqname')]} for h in t.findall('hal')]})
        except ET.ParseError as e:errors.append({'path':str(p.relative_to(dump)),'error':str(e)})
save('vintf-review.json',{'files':vintf,'errors':errors})
services=[]
for part in ('vendor','odm','system_ext','product'):
    for p in (dump/part/'etc/init').rglob('*.rc'):
        for line in p.read_text(errors='replace').splitlines():
            if line.startswith('service '):
                fields=line.split()
                if len(fields)>=3:services.append({'file':str(p.relative_to(dump)),'name':fields[1],'executable':fields[2],'in_generated_vendor':(vendor/'proprietary'/fields[2].lstrip('/')).exists()})
save('init-service-review.json',services)
mods={}
for section in ('vendor_ramdisk','vendor_dlkm','system_dlkm'):
    for p in (kernel/section).glob('*.ko'):
        cmd=lambda field:subprocess.run(['modinfo','-F',field,str(p)],capture_output=True,text=True).stdout.strip()
        mods[section+'/'+p.name]={'name':cmd('name'),'vermagic':cmd('vermagic'),'depends':cmd('depends').split(',') if cmd('depends') else [],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
names={x['name'] for x in mods.values()}
save('module-dependency-review.json',{'modules':mods,'unresolved_module_names':sorted({d for x in mods.values() for d in x['depends'] if d not in names}),'note':'Built-in kernel providers may account for absent module names; symbol CRC compatibility not established.'})
for p in (device/'BoardConfig.mk',device/'device.mk',device/'init/fstab.qcom',device/'proprietary-files.txt',vendor/'Android.bp',vendor/'mist-vendor.mk'):
    assert p.is_file() and p.stat().st_size,p
save('integration-summary.json',{'unique_dependency_names':len(deps),'vintf_files':len(vintf),'vintf_parse_errors':len(errors),'stock_services':len(services),'kernel_modules':len(mods),'status':'candidate only','unvalidated':['Android build module providers','VINTF compatibility','SELinux compilation','module symbol CRCs','AVB and dynamic partition layout','boot/hardware']})
print((reports/'integration-summary.json').read_text())
