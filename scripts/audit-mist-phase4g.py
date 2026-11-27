#!/usr/bin/env python3
import collections,json,re,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
import xml.etree.ElementTree as ET
root=Path(sys.argv[1]); d=root/'device'; v=root/'vendor'; out=root/'reports'; out.mkdir(exist_ok=True)
def save(n,x): (out/n).write_text(json.dumps(x,indent=2,sort_keys=True))
providers=collections.defaultdict(list); consumers=[]; errors=[]
for p in (v/'proprietary').rglob('*'):
    if not p.is_file() or p.is_symlink(): continue
    with p.open('rb') as f:
        if f.read(4)!=b'\x7fELF':continue
        f.seek(0)
        try:
            e=ELFFile(f); tags=[t for s in e.iter_segments() if s.header.p_type=='PT_DYNAMIC' for t in s.iter_tags()]
            key=(e.elfclass,e.header.e_machine); path=str(p.relative_to(v/'proprietary')); soname=next((t.soname for t in tags if t.entry.d_tag=='DT_SONAME'),p.name)
            exports=set(); imports=set(); dyn=e.get_section_by_name('.dynsym')
            if dyn:
                for sym in dyn.iter_symbols():
                    if not sym.name:continue
                    if sym.entry.st_shndx=='SHN_UNDEF':
                        if sym.entry.st_info.bind=='STB_GLOBAL':imports.add(sym.name)
                    elif sym.entry.st_info.bind in ('STB_GLOBAL','STB_WEAK') and sym.entry.st_other.visibility in ('STV_DEFAULT','STV_PROTECTED'):exports.add(sym.name)
            row={'path':path,'key':key,'soname':soname,'needed':[t.needed for t in tags if t.entry.d_tag=='DT_NEEDED'],'exports':exports,'imports':imports}
            providers[(key,soname)].append(row);consumers.append(row)
        except Exception as exc:errors.append([str(p),str(exc)])
missing=collections.defaultdict(list); ambiguous=collections.defaultdict(list); symbols={}
for c in consumers:
    if c['key'][1] not in ('EM_AARCH64','EM_ARM','EM_386','EM_X86_64'):continue
    exp=set(c['exports']); absent=[]
    for n in c['needed']:
        ps=providers.get((c['key'],n),[])
        if not ps:missing[str(c['key'])+':'+n].append(c['path']);absent.append(n)
        else:
            for p in ps:exp.update(p['exports'])
            if len(ps)>1:ambiguous[n].append(c['path'])
    remaining=c['imports']-exp
    if remaining:symbols[c['path']]={'unmatched_direct_symbols':sorted(remaining),'external_needed':absent}
save('elf.json',{'parsed':len(consumers),'parse_errors':errors,'missing_from_blob_inventory':missing,'multiple_candidates':ambiguous,'symbol_review':symbols,'caveat':'Direct dependency symbol comparison only; transitive exports, symbol versions, linker namespaces and source-built providers require further resolution.'})
instances=collections.defaultdict(list); xml_errors=[]
for base in (d/'configs/vintf',v/'proprietary'):
    for p in base.rglob('*.xml'):
        if 'vintf' not in p.parts:continue
        try:r=ET.parse(p).getroot()
        except ET.ParseError as e:xml_errors.append([str(p),str(e)]);continue
        if r.tag!='manifest':continue
        for h in r.findall('hal'):
            name=h.findtext('name',''); fmt=h.get('format','hidl'); versions=[x.text for x in h.findall('version')] or (['1'] if fmt=='aidl' else ['unspecified'])
            for fq in h.findall('fqname'):
                instances[fmt+':'+name+':'+str(fq.text)].append(str(p.relative_to(root)))
            for interface in h.findall('interface'):
                for instance in interface.findall('instance'):
                    for version in versions:
                        fq=interface.findtext('name','')+'/'+str(instance.text)
                        if fmt=='hidl':fq='@'+str(version)+'::'+fq
                        instances[fmt+':'+name+':'+fq].append(str(p.relative_to(root)))
save('vintf.json',{'instances':instances,'duplicate_candidates':{k:x for k,x in instances.items() if len(x)>1},'parse_errors':xml_errors})
contexts=collections.defaultdict(list)
for p in (d/'sepolicy/vendor').glob('*contexts'):
    for i,l in enumerate(p.read_text().splitlines(),1):
        l=l.strip()
        if l and not l.startswith('#'):
            k=l.split()[0];contexts[p.name+':'+k].append([i,l])
save('policy.json',{'duplicate_local_contexts':{k:x for k,x in contexts.items() if len(x)>1},'context_count':len(contexts)})
print('ELF parsed',len(consumers),'missing inventory keys',len(missing),'VINTF instances',len(instances),'XML errors',len(xml_errors),'ELF errors',len(errors))
for k,x in instances.items():
    if len(x)>1:print('VINTF duplicate candidate:',k,x)
for n in sorted(missing):print('ELF provider review:',n)
if errors or xml_errors:sys.exit(1)
