#!/usr/bin/env python3
"""Inventory stock images independently of Dumpyara, with explicit coverage."""
import csv, hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile
from pathlib import Path
base=Path(sys.argv[1]).resolve()
report=base/'reports'; report.mkdir(exist_ok=True)
work=base/'decoded'; work.mkdir(exist_ok=True)
rows=[]; coverage=[]; errors=[]; seen=set()
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(args, log):
    with (report/log).open('ab') as f:
        f.write(('\n$ '+repr([str(x) for x in args])+'\n').encode())
        return subprocess.run([str(x) for x in args],stdout=f,stderr=subprocess.STDOUT).returncode
def inventory(root,label):
    n=0
    for d,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(d)/name; s=p.lstat(); kind=stat.filemode(s.st_mode)
            rel=p.relative_to(root).as_posix()
            try:
                h=digest(p) if stat.S_ISREG(s.st_mode) else ''
                link=os.readlink(p) if p.is_symlink() else ''
                rows.append([label,rel,kind,s.st_uid,s.st_gid,s.st_size,h,link]);n+=1
            except Exception as e:errors.append([label,rel,str(e)])
    return n
def decode(p,label,depth=0):
    if depth>12: errors.append([label,'nesting limit']);return
    if label in seen:return
    seen.add(label)
    dest=work/hashlib.sha256(label.encode()).hexdigest()[:24];dest.mkdir()
    typ=subprocess.check_output(['file','-b',str(p)],text=True).strip()
    with p.open('rb') as f:
        magic=f.read(8);f.seek(1024);ero=f.read(4);f.seek(1080);ext=f.read(2);f.seek(4096);lp=f.read(4)
    status='opaque';count=0;rc=0
    try:
        if magic[:4]==bytes.fromhex('3aff26ed'):
            raw=dest/'raw.img';rc=run(['simg2img',p,raw],'decode.log')
            status='sparse' if rc==0 else 'failed'
            if not rc:decode(raw,label+'!raw',depth+1)
        elif lp==b'gDla':
            status='super';rc=run(['lpdump',p],'decode.log')
            out=dest/'logical';out.mkdir()
            rc2=run(['lpunpack',p,out],'decode.log');rc=rc or rc2
            for q in sorted(out.glob('*.img')):decode(q,label+'!'+q.name,depth+1)
            if not list(out.glob('*.img')):rc=1
        elif ero==bytes.fromhex('e2e1f5e0') or ext==b'\\x53\\xef' or 'FAT' in typ or 'F2FS' in typ or 'Squashfs' in typ:
            # Mount read-only without journal replay; report original metadata.
            out=dest/'fs';out.mkdir()
            fs='erofs' if ero==bytes.fromhex('e2e1f5e0') else 'ext4' if ext==b'\\x53\\xef' else 'vfat' if 'FAT' in typ else 'f2fs' if 'F2FS' in typ else 'squashfs'
            opts='loop,ro,noload' if fs=='ext4' else 'loop,ro'
            rc=run(['mount','-t',fs,'-o',opts,p,out],'decode.log')
            if not rc:
                try:
                    count=inventory(out,label);status='filesystem'
                    for d,dirs,files in os.walk(out,followlinks=False):
                        for n in files:
                            q=Path(d)/n
                            if q.is_symlink():continue
                            rel=q.relative_to(out).as_posix()
                            if n.lower().endswith(('.img','.img.gz','.img.lz4','.img.xz','.img.zst')):decode(q,label+'!'+rel,depth+1)
                            if re.search(r'(^|/)(fstab[^/]*|[^/]+\\.rc|[^/]+\\.prop|modules\\.[^/]+|[^/]*contexts[^/]*|[^/]*manifest[^/]*\\.xml|[^/]*compatibility_matrix[^/]*\\.xml)$',rel) and q.stat().st_size<8*1024*1024:
                                data=q.read_bytes()
                                if b'\\0' not in data:
                                    cfg=report/'configs'/hashlib.sha256(label.encode()).hexdigest()[:24]/rel;cfg.parent.mkdir(parents=True,exist_ok=True);cfg.write_bytes(data)
                finally:
                    if run(['umount',out],'decode.log'):errors.append([label,'unmount failed'])
        elif magic in (b'ANDROID!',b'VNDRBOOT'):
            status='boot';out=dest/'boot';out.mkdir()
            rc=run(['python3',base/'mkbootimg/unpack_bootimg.py','--boot_img',p,'--out',out],'decode.log')
            if not rc:
                count=inventory(out,label+'!components')
                for q in sorted(out.iterdir()):
                    if q.is_file() and 'ramdisk' in q.name and q.stat().st_size:
                        rd=dest/('rd-'+q.name);rd.mkdir()
                        # bsdtar detects gzip/lz4/cpio; legacy lz4 uses explicit decompression.
                        raw=dest/(q.name+'.cpio')
                        with q.open('rb') as f:m=f.read(4)
                        if m in (bytes.fromhex('02214c18'),bytes.fromhex('04224d18')):
                            rc2=run(['lz4','-d','-f',q,raw],'decode.log')
                        elif m[:2]==b'\\x1f\\x8b':
                            with raw.open('wb') as f:rc2=subprocess.run(['gzip','-dc',q],stdout=f).returncode
                        else:raw=q;rc2=0
                        if not rc2:rc2=run(['bsdtar','-xf',raw,'-C',rd],'decode.log')
                        if rc2:errors.append([label,q.name,'ramdisk extraction failed']);rc=1
                        else:
                            count+=inventory(rd,label+'!'+q.name)
                            for x in rd.rglob('*'):
                                if x.is_file() and not x.is_symlink() and (x.name.startswith(('fstab','modules.')) or x.suffix in ('.rc','.prop')):
                                    if x.stat().st_size<8*1024*1024:
                                        cfg=report/'configs'/hashlib.sha256((label+'!'+q.name).encode()).hexdigest()[:24]/x.relative_to(rd);cfg.parent.mkdir(parents=True,exist_ok=True);cfg.write_bytes(x.read_bytes())
                for q in out.glob('*bootconfig*'):
                    if q.is_file():shutil.copyfile(q,report/(dest.name+'-bootconfig.txt'))
        elif label.lower().endswith(('.gz','.lz4','.xz','.zst')):
            raw=dest/'decompressed.img';tool={'gz':'gzip','lz4':'lz4','xz':'xz','zst':'zstd'}[label.rsplit('.',1)[1]]
            with raw.open('wb') as f:rc=subprocess.run([tool,'-dc',p],stdout=f).returncode
            status='compressed'
            if not rc:decode(raw,label+'!decompressed',depth+1)
        if p.name.startswith(('boot','init_boot','vendor_boot','recovery','dtbo','vbmeta','pvmfw')):
            run(['python3',base/'avb/avbtool.py','info_image','--image',p],'avb.log')
        if rc:errors.append([label,'decoder exit',rc]);status='failed'
    except Exception as e:errors.append([label,str(e)]);status='failed'
    coverage.append([label,p.stat().st_size,digest(p),typ,status,count])
    # Free decoded temporary files only after all children have been inventoried.
    if not os.path.ismount(dest/'fs'):shutil.rmtree(dest)
def table(name,head,data):
    with (report/name).open('w',newline='') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(head);w.writerows(data)
try:
    stock=base/'stock'
    inventory(stock,'archive')
    images=[p for p in stock.rglob('*') if p.is_file() and not p.is_symlink() and re.search(r'\\.img(?:\\.(?:gz|lz4|xz|zst))?$',p.name,re.I)]
    if not images:errors.append(['archive','no images found'])
    for p in sorted(images):decode(p,p.relative_to(stock).as_posix())
finally:
    table('all-files.tsv',['container','path','mode','uid','gid','bytes','sha256','symlink'],rows)
    table('image-coverage.tsv',['image','bytes','sha256','file_type','status','entries'],coverage)
    (report/'errors.json').write_text(json.dumps(errors,indent=2))
    (report/'summary.json').write_text(json.dumps({'images':len(coverage),'entries':len(rows),'errors':len(errors),'opaque_images':sum(x[4]=='opaque' for x in coverage),'complete':not errors and all(x[4]!='opaque' for x in coverage)},indent=2))
if errors:sys.exit(1)
