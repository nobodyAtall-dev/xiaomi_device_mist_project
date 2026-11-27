import csv,json,sys
from pathlib import Path
base,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
a,b=[base/('mist-deep-analysis-'+x) for x in ('hyperos3','hyperos4')]
def lines(p):return set(p.read_text(errors='replace').splitlines()) if p.exists() else set()
def diff(name,x,y):
    (out/(name+'-added.txt')).write_text('\n'.join(sorted(y-x)))
    (out/(name+'-removed.txt')).write_text('\n'.join(sorted(x-y)))
    return {'added':len(y-x),'removed':len(x-y),'shared':len(x&y)}
summary={}
for n in ('stock-file-paths.txt','hardware-config-index.txt','properties-by-source.tsv','sky-matched-blobs.txt','sky-missing-blobs.txt'):
    if not (a/n).exists() or not (b/n).exists():raise SystemExit('Missing required report: '+n)
    summary[n]=diff(n,lines(a/n),lines(b/n))
def elf(p):
    with p.open() as f:return {r['path']:r for r in csv.DictReader(f,delimiter='\t')}
ea,eb=elf(a/'elf-dependencies.tsv'),elf(b/'elf-dependencies.tsv')
summary['elf_paths']=diff('elf-paths',set(ea),set(eb))
changes=[{'path':k,'old':ea[k],'new':eb[k]} for k in sorted(ea.keys()&eb.keys()) if ea[k]!=eb[k]]
(out/'elf-changes.json').write_text(json.dumps(changes,indent=2))
summary['elf_changed']=len(changes)
for n in ('deep-summary.json','analysis-errors.json','firmware-source.json'):
    for label,p in [('hyperos3',a),('hyperos4',b)]:
        if (p/n).exists():(out/(label+'-'+n)).write_bytes((p/n).read_bytes())
(out/'comparison-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
