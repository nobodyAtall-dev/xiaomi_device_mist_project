import csv,json,re,sys
from pathlib import Path
base,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
def read(version):
    root=base/('mist-full-stock-'+version)
    with (root/'all-files.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    # Normalize top-level logical partition names; preserve ramdisk and nested image identities.
    result={}
    for r in rows:
        label=r['container']
        if label=='archive':continue
        leaf=label.split('!')[-1]
        if re.search(r'\.img$',leaf):
            label=Path(leaf).stem
            label=re.sub(r'_[ab]$','',label)
        key=(label,r['path'])
        result.setdefault(key,set()).add((r['mode'],r['sha256'],r['symlink']))
    return result,json.loads((root/'summary.json').read_text())
a,sa=read('hyperos3');b,sb=read('hyperos4')
counts={}
with (out/'file-differences.tsv').open('w',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['container','path','status','hyperos3','hyperos4'])
    for k in sorted(a.keys()|b.keys()):
        x,y=a.get(k),b.get(k)
        status='only-hyperos4' if x is None else 'only-hyperos3' if y is None else 'identical' if x==y else 'changed'
        counts[status]=counts.get(status,0)+1
        w.writerow([*k,status,json.dumps(sorted(x or [])),json.dumps(sorted(y or []))])
(out/'summary.json').write_text(json.dumps({'counts':counts,'hyperos3':sa,'hyperos4':sb,'warning':'Presence and absence refer to decoded inventories only; OTA may omit unchanged partitions. Multiple slot variants are retained as sets.'},indent=2))
