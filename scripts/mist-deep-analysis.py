#!/usr/bin/env python3
"""Read-only stock firmware evidence collector. Never flashes or publishes trees."""
import collections, csv, hashlib, json, os, re, shutil, struct, subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path
from elftools.elf.elffile import ELFFile

base=Path(sys.argv[1]).resolve()
os.chdir(base)
report=base/'reports'
report.mkdir(exist_ok=True)
stock=base/'stock'
dump=base/'dump'
errors=[]
def write(name,data):
    p=report/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(data,encoding='utf-8')
def cmd(name,args,timeout=120):
    try:
        p=subprocess.run([str(x) for x in args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        write(name,p.stdout.decode(errors='replace'))
        if p.returncode: errors.append([name,p.returncode])
        return p.returncode
    except Exception as e:
        errors.append([name,str(e)])
        return -1
def table(name,header,rows):
    with (report/name).open('w',newline='') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(header);w.writerows(rows)
images={p.name:p for p in stock.rglob('*') if p.is_file() and p.parent.name=='images'}
# Qualcomm flash XML: physical partition sizes, offsets, LUN, sparse flag.
rows=[]
for p in sorted(stock.rglob('rawprogram*.xml')):
    try:
        for e in ET.parse(p).getroot().iter('program'):
            a=e.attrib
            try: size=int(a['SECTOR_SIZE_IN_BYTES'])*int(a['num_partition_sectors'])
            except (ValueError,KeyError): size=''
            rows.append([p.name,a.get('label'),a.get('filename'),a.get('physical_partition_number'),a.get('start_sector'),a.get('num_partition_sectors'),a.get('SECTOR_SIZE_IN_BYTES'),size,a.get('sparse')])
    except Exception as e: errors.append([p.name,str(e)])
table('physical-partitions.tsv',['xml','label','file','lun','start_sector','sectors','sector_bytes','size_bytes','sparse'],rows)
# Parse Android liblp geometry and metadata directly from raw super image.
# Convert sparse super to a temporary raw image only when necessary.
def lp_metadata(p):
    temp=base/'super-analysis.raw'
    try:
        with p.open('rb') as f: sparse=f.read(4)==b'\x3a\xff\x26\xed'
        if sparse:
            if cmd('super-convert.txt',['simg2img',p,temp],1200): return
            p=temp
        with p.open('rb') as f:
            f.seek(4096);g=f.read(52)
            magic,sz=struct.unpack_from('<II',g)
            if magic!=0x616c4467: raise ValueError('Invalid LP geometry magic')
            maxsize,slots,block=struct.unpack_from('<III',g,40)
            result={'metadata_max_size':maxsize,'slots':slots,'logical_block_size':block,'metadata':[]}
            if not (0<slots<=8 and 128<=maxsize<=16*1024*1024): raise ValueError('Invalid geometry bounds')
            for copy in range(2):
                for slot in range(slots):
                    f.seek(12288+(copy*slots+slot)*maxsize)
                    h=f.read(128)
                    if struct.unpack_from('<I',h)[0]!=0x414c5030: continue
                    major,minor,hs=struct.unpack_from('<HHI',h,4)
                    ts=struct.unpack_from('<I',h,44)[0]
                    if hs<128 or hs+ts>maxsize: continue
                    desc=[struct.unpack_from('<III',h,80+i*12) for i in range(4)]
                    f.seek(12288+(copy*slots+slot)*maxsize+hs); data=f.read(ts)
                    def entries(i):
                        off,n,es=desc[i]
                        if es==0 or off+n*es>len(data): raise ValueError('Invalid table')
                        return [data[off+j*es:off+(j+1)*es] for j in range(n)]
                    def name(x): return x.split(b'\0',1)[0].decode(errors='replace')
                    ext=[struct.unpack_from('<QIQI',x) for x in entries(1)]
                    groups=[{'name':name(x[:36]),'flags':struct.unpack_from('<I',x,36)[0],'maximum_size':struct.unpack_from('<Q',x,40)[0]} for x in entries(2)]
                    parts=[]
                    for x in entries(0):
                        attr,first,count,group=struct.unpack_from('<IIII',x,36)
                        parts.append({'name':name(x[:36]),'attributes':attr,'group':groups[group]['name'] if group<len(groups) else group,'size_bytes':sum(e[0]*512 for e in ext[first:first+count]),'extents':[{'sectors':e[0],'type':e[1],'target':e[2],'source':e[3]} for e in ext[first:first+count]]})
                    devices=[]
                    for x in entries(3):
                        first,align,offset,size=struct.unpack_from('<QIIQ',x)
                        devices.append({'name':name(x[24:60]),'size_bytes':size,'first_logical_sector':first,'alignment':align,'alignment_offset':offset})
                    result['metadata'].append({'copy':copy,'slot':slot,'version':[major,minor],'partitions':parts,'groups':groups,'block_devices':devices})
            write('dynamic-partitions.json',json.dumps(result,indent=2))
            if not result['metadata']: errors.append(['super','No readable metadata slots'])
    except Exception as e: errors.append(['super',str(e)])
    finally: temp.unlink(missing_ok=True)
if 'super.img' in images: lp_metadata(images['super.img'])
else: errors.append(['super','super.img missing or split'])
# Inspect AVB descriptors and boot headers, including rescue retry.
for n,p in sorted(images.items()):
    if n.endswith('.img') and n.startswith(('vbmeta','boot','init_boot','vendor_boot','recovery','dtbo','rescue')):
        cmd('avb/'+n+'.txt',[sys.executable,base/'avb/avbtool.py','info_image','--image',p])
    if n in ('boot.img','init_boot.img','vendor_boot.img','recovery.img','rescue.img'):
        out=base/'boot-analysis'/p.stem;out.mkdir(parents=True,exist_ok=True)
        cmd('boot/'+n+'.txt',[sys.executable,base/'mkbootimg/unpack_bootimg.py','--boot_img',p,'--out',out])
        for k in out.glob('kernel*'):
            cmd('kernel/'+p.stem+'-version.txt',['bash','-c','strings "$1" | grep -m 5 "Linux version"','_',k])
            cmd('kernel/'+p.stem+'-config.txt',['bash',base/'linux/scripts/extract-ikconfig',k])
            cmd('kernel/'+p.stem+'-type.txt',['file',k])
# Split flattened device trees and Android DT table images, then decompile.
dtrows=[]
def dt_scan(p):
    try:
        if p.stat().st_size>128*1024*1024:return
        data=p.read_bytes()
        pos=0;idx=0
        while True:
            pos=data.find(b'\xd0\x0d\xfe\xed',pos)
            if pos<0:break
            if pos+40>len(data):break
            total=struct.unpack_from('>I',data,pos+4)[0]
            if 40<=total<=len(data)-pos:
                q=base/'dt-temp.dtb';q.write_bytes(data[pos:pos+total])
                label=p.parent.name+'-'+p.name+'-'+str(idx)
                rc=cmd('dt/'+label+'.dts',['dtc','-I','dtb','-O','dts',q])
                dtrows.append([str(p.relative_to(base)),pos,total,rc])
                q.unlink(missing_ok=True);idx+=1;pos+=total
            else:pos+=4
    except Exception as e:errors.append([str(p),str(e)])
for p in list((base/'boot-analysis').rglob('*'))+list(images.values()):
    if p.is_file() and ('dtb' in p.name.lower() or 'dtbo' in p.name.lower()):dt_scan(p)
table('dt-index.tsv',['source','offset','size','dtc_exit'],dtrows)
# Modem may be FAT; retry read-only with mtools when available.
if 'modem.img' in images:
    p=images['modem.img']
    cmd('modem-type.txt',['file',p])
    if shutil.which('mdir'):
        cmd('modem-fat-list.txt',['mdir','-i',p,'-/','::'])
        out=base/'modem-retry';out.mkdir(exist_ok=True)
        cmd('modem-fat-extract.txt',['mcopy','-i',p,'-s','::/*',out],300)
        write('modem-retry-files.txt','\n'.join(str(x.relative_to(out)) for x in out.rglob('*')))
# Preserve original property sources and relevant text configs; do not follow symlinks.
props=[];hardware=[];elf=[];modules=[];stock_paths=set()
partitions={'system','system_ext','product','vendor','odm','vendor_dlkm','system_dlkm','odm_dlkm','mi_ext'}
config_re=re.compile(r'fstab|manifest|compatibility_matrix|sepolicy|file_contexts|property_contexts|service_contexts|hwservice_contexts|genfs_contexts|modules\.|ueventd|audio|camera|display|fingerprint|biometric|bluetooth|wlan|wifi|nfc|thermal|power|sensor|radio|gps|gnss|media|permissions|init|vintf',re.I)
for p in sorted(dump.rglob('*')):
    if p.is_symlink() or not p.is_file():continue
    rel=p.relative_to(dump); key=str(rel)
    if rel.parts[0] in partitions:
        stock_paths.add(key)
        if len(rel.parts)>2 and rel.parts[0]==rel.parts[1]:stock_paths.add('/'.join(rel.parts[1:]))
    if p.suffix=='.prop':
        props.extend([key+'\t'+l for l in p.read_text(errors='replace').splitlines() if '=' in l and not l.startswith('#')])
    if p.suffix=='.ko':
        try:
            proc=subprocess.run(['modinfo',p],capture_output=True,text=True,errors='replace',timeout=10)
            modules.append('===== '+key+' =====\n'+proc.stdout+proc.stderr)
        except Exception as e:errors.append([key,str(e)])
    try:
        with p.open('rb') as f:
            if f.read(4)==b'\x7fELF':
                f.seek(0);e=ELFFile(f);needed=[];soname='';runpath=''
                sec=e.get_section_by_name('.dynamic')
                if sec:
                    for tag in sec.iter_tags():
                        t=tag.entry.d_tag
                        if t=='DT_NEEDED':needed.append(tag.needed)
                        elif t=='DT_SONAME':soname=tag.soname
                        elif t=='DT_RUNPATH':runpath=tag.runpath
                elf.append([key,e.elfclass,e.header.e_machine,soname,','.join(needed),runpath])
    except Exception as e:errors.append([key,str(e)])
    if config_re.search(key) and p.stat().st_size<=2*1024*1024 and (p.suffix in ('.xml','.conf','.cfg','.ini','.rc','.prop','.txt','.json','.cil','.te','.csv') or 'contexts' in p.name or p.name.startswith(('fstab','modules.'))):
        data=p.read_bytes()
        if b'\0' not in data:
            dest=report/'hardware-configs'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            hardware.append(key)
write('properties-by-source.tsv','source\tproperty\n'+'\n'.join(props))
write('hardware-config-index.txt','\n'.join(hardware))
write('module-details.txt','\n'.join(modules))
table('elf-dependencies.tsv',['path','bits','machine','soname','needed','runpath'],elf)
# Compare stock path candidates against actual sky blob list, without copying blobs.
matched=[];missing=[]
ref=base/'reference/proprietary-files.txt'
for line in ref.read_text().splitlines():
    line=line.strip()
    if not line or line.startswith('#'):continue
    source=line.lstrip('-').split('|')[0].split(';')[0].split(':')[0]
    (matched if source in stock_paths else missing).append(line)
write('sky-matched-blobs.txt','\n'.join(matched))
write('sky-missing-blobs.txt','\n'.join(missing))
write('stock-file-paths.txt','\n'.join(sorted(stock_paths)))
for n in ('BoardConfig.mk','device.mk','lineage.dependencies','extract-files.py','AndroidProducts.mk'):
    p=base/'reference'/n
    if p.is_file():write('reference/'+n,p.read_text(errors='replace'))
# Explicitly distinguish raw archive inventory from successful filesystem extraction.
status=[]
for n,p in sorted(images.items()):
    if p.suffix not in ('.img','.bin','.mbn','.elf','.fv'):continue
    d=dump/p.stem
    count=sum(1 for x in d.rglob('*') if x.is_file()) if d.is_dir() else 0
    status.append([n,p.stat().st_size,count,'files present; completeness unverified' if count else 'raw only or not decoded'])
table('partition-extraction-status.tsv',['image','archive_bytes','extracted_files','status'],status)
write('analysis-errors.json',json.dumps(errors,indent=2))
summary={'physical_partition_rows':len(rows),'dt_candidates':len(dtrows),'elf_files':len(elf),'kernel_modules':len(modules),'hardware_configs':len(hardware),'sky_matched':len(matched),'sky_missing':len(missing),'diagnostics':len(errors),'note':'No source trees generated. Raw-only images and extraction failures require review.'}
write('deep-summary.json',json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
