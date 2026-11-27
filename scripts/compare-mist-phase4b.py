#!/usr/bin/env python3
"""Compare Phase 4B reports from the exact two stock releases."""
import json
import sys
from pathlib import Path

base, out = map(Path, sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
a,b = (base / ("mist-phase4b-"+x) for x in ("hyperos3","hyperos4"))
def load(root,name):
    return json.loads((root/name).read_text())
def save(name,value):
    (out/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def changes(x,y):
    return {"added": sorted(y.keys()-x.keys()), "removed": sorted(x.keys()-y.keys()),
            "changed": [{"path":k,"hyperos3":x[k],"hyperos4":y[k]} for k in sorted(x.keys()&y.keys()) if x[k]!=y[k]]}
for p in (a,b):
    for name in ("phase4b-summary.json","stock-inventory.json","elf-stock.json","stock-symlinks.json","camera-closure.json","vintf-stock.json","init-stock.json","media-codec-stock.json","wlan.json","stock-permissions-properties.json","current-tree-commits.txt"):
        if not (p/name).is_file():
            raise SystemExit("Missing required report: "+str(p/name))
if (a/"current-tree-commits.txt").read_text() != (b/"current-tree-commits.txt").read_text():
    raise SystemExit("The current Mist trees changed between firmware jobs; rerun with stable branches")
summary={}
for name in ("stock-inventory.json","elf-stock.json","stock-symlinks.json","stock-permissions-properties.json"):
    diff=changes(load(a,name),load(b,name))
    save("comparison-"+name,diff)
    summary[name]={k:len(v) for k,v in diff.items()}
# Compare normalized records rather than relying on ordering.
for name in ("vintf-stock.json","media-codec-stock.json"):
    x={json.dumps(v,sort_keys=True):v for v in load(a,name)}
    y={json.dumps(v,sort_keys=True):v for v in load(b,name)}
    diff={"added":[y[k] for k in sorted(y.keys()-x.keys())],"removed":[x[k] for k in sorted(x.keys()-y.keys())]}
    save("comparison-"+name,diff)
    summary[name]={k:len(v) for k,v in diff.items()}
for name, field in (("camera-closure.json","closure"),("wlan.json","stock_paths")):
    x=set(load(a,name)[field]); y=set(load(b,name)[field])
    diff={"added":sorted(y-x),"removed":sorted(x-y),"shared":sorted(x&y)}
    save("comparison-"+name,diff)
    summary[name]={k:len(v) for k,v in diff.items()}
x,y=load(a,"init-stock.json"),load(b,"init-stock.json")
for field in ("services","imports","actions"):
    ax={json.dumps(v,sort_keys=True):v for v in x[field]}
    by={json.dumps(v,sort_keys=True):v for v in y[field]}
    diff={"added":[by[k] for k in sorted(by.keys()-ax.keys())],"removed":[ax[k] for k in sorted(ax.keys()-by.keys())]}
    save("comparison-init-"+field+".json",diff)
    summary["init-"+field]={k:len(v) for k,v in diff.items()}
summary["hyperos3"]=load(a,"phase4b-summary.json")
summary["hyperos4"]=load(b,"phase4b-summary.json")
summary["note"]="HyperOS 4 is the preferred baseline; differences do not establish ABI compatibility or authorize mixing blobs."
save("comparison-summary.json",summary)
(out/"current-tree-commits.txt").write_bytes((b/"current-tree-commits.txt").read_bytes())
print(json.dumps(summary,indent=2))
