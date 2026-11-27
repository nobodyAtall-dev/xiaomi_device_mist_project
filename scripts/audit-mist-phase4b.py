#!/usr/bin/env python3
"""Phase 4B: read-only stock/current-tree integration evidence, not a build."""
import argparse, collections, csv, hashlib, json, os, re, subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from elftools.elf.elffile import ELFFile

ap = argparse.ArgumentParser()
ap.add_argument("work", type=Path)
args = ap.parse_args()
work = args.work.resolve()
out = work / "reports"
out.mkdir(exist_ok=True)
dump = work / "dump"
dev = work / "android/device/xiaomi/mist"
vendor = work / "android/vendor/xiaomi/mist/proprietary"
kernel = work / "android/kernel/xiaomi/mist-prebuilt"
errors = []
parts = {"vendor", "odm", "system", "system_ext", "product", "vendor_dlkm", "system_dlkm", "odm_dlkm", "mi_ext", "mi_product"}
def save(name, data):
    (out / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()
def inventory(root):
    result = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            p = Path(base) / name
            rel = p.relative_to(root)
            if rel.parts[0] not in parts:
                continue
            if len(rel.parts) > 2 and rel.parts[0] == rel.parts[1]:
                rel = Path(*rel.parts[1:])
            if p.is_symlink() or p.is_file():
                result.setdefault(str(rel), p)
    return result
stock = inventory(dump)
current = inventory(vendor)
if not stock or not current or not any(k.startswith("vendor/lib64/") for k in stock):
    raise SystemExit("Missing stock or current vendor extraction")
def read(p):
    return p.read_text(errors="replace")
def xml(p):
    try:
        return ET.parse(p).getroot()
    except (OSError, ET.ParseError) as e:
        errors.append({"file": str(p), "error": str(e)})
        return None
def elf_inventory(files):
    result = {}
    for name, p in sorted(files.items()):
        if p.is_symlink():
            continue
        try:
            with p.open("rb") as f:
                if f.read(4) != b"\x7fELF":
                    continue
                f.seek(0)
                e = ELFFile(f)
                row = {"bits": e.elfclass, "machine": e.header["e_machine"], "needed": [], "soname": None, "runpath": []}
                for seg in e.iter_segments():
                    if seg.header.p_type != "PT_DYNAMIC":
                        continue
                    for t in seg.iter_tags():
                        if t.entry.d_tag == "DT_NEEDED":
                            row["needed"].append(t.needed)
                        elif t.entry.d_tag == "DT_SONAME":
                            row["soname"] = t.soname
                        elif t.entry.d_tag == "DT_RUNPATH":
                            row["runpath"].append(t.runpath)
                        elif t.entry.d_tag == "DT_RPATH":
                            row["runpath"].append(t.rpath)
                result[name] = row
        except Exception as e:
            errors.append({"file": name, "error": str(e)})
    return result
se, ce = elf_inventory(stock), elf_inventory(current)
def providers(elf):
    idx = collections.defaultdict(list)
    for name, row in elf.items():
        for soname in {Path(name).name, row["soname"]} - {None}:
            idx[(row["bits"], soname)].append(name)
    return idx
sp, cp = providers(se), providers(ce)
gaps = []
for name, row in sorted(ce.items()):
    for n in sorted(set(row["needed"])):
        key = row["bits"], n
        if not cp[key]:
            gaps.append({"consumer": name, "bits": row["bits"], "needed": n,
                         "stock_candidates": sorted(sp[key]), "status": "source provider or missing; linker namespace and ABI not established"})
save("elf-stock.json", se)
save("elf-current.json", ce)
save("elf-unresolved.json", gaps)
# Follow the stock camera provider and camera-related libraries recursively.
camera = re.compile(r"camera|camx|chi-cdk|chromatix|com\.qti\.chi|com\.qti\.sensor|mmcamera", re.I)
roots = sorted(n for n in se if camera.search(n))
seen = set()
queue = collections.deque(roots)
while queue:
    n = queue.popleft()
    if n in seen:
        continue
    seen.add(n)
    for needed in se[n]["needed"]:
        # Limit traversal to vendor/odm providers; system source providers are separately reported.
        queue.extend(p for p in sp[(se[n]["bits"], needed)] if p.startswith(("vendor/", "odm/")) and p not in seen)
camera_edges = []
for n in sorted(seen):
    for needed in se[n]["needed"]:
        key = se[n]["bits"], needed
        camera_edges.append({"consumer": n, "needed": needed, "stock": sorted(sp[key]), "current": sorted(cp[key])})
save("camera-closure.json", {"roots": roots, "closure": sorted(seen), "not_in_current_tree": sorted(seen-current.keys()), "edges": camera_edges,
    "stock_assets": sorted(n for n in stock if camera.search(n)), "note": "Candidate closure, not a recommendation to copy every blob; DT_NEEDED misses dlopen dependencies."})
def vintf(files):
    rows = []
    for name, p in sorted(files.items()):
        if "/etc/vintf/" not in name or not name.endswith(".xml") or p.is_symlink():
            continue
        t = xml(p)
        if t is None:
            continue
        for h in t.findall("hal"):
            rows.append({"file": name, "type": t.tag, "attributes": t.attrib,
                         "name": h.findtext("name"), "format": h.get("format", "hidl"), "hal_attributes": h.attrib,
                         "versions": [v.text for v in h.findall("version")],
                         "fqnames": [v.text for v in h.findall("fqname")],
                         "interfaces": [{"name": i.findtext("name"), "instances": [j.text for j in i.findall("instance")],
                                         "regex_instances": [j.text for j in i.findall("regex-instance")]} for i in h.findall("interface")]})
    return rows
save("vintf-stock.json", vintf(stock))
save("vintf-current.json", vintf(current))
def init_data(files):
    services, imports, actions = [], [], []
    for name, p in sorted(files.items()):
        if not name.endswith(".rc") or p.is_symlink() or not ("/etc/init/" in name or name.startswith("device/init/") or Path(name).name.startswith("init")):
            continue
        block = None
        for line in read(p).splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line[0].isspace():
                fields = line.split()
                block = None
                if fields[0] == "service" and len(fields) >= 3:
                    block = {"file": name, "name": fields[1], "command": fields[2:], "options": []}
                    services.append(block)
                elif fields[0] == "import" and len(fields) >= 2:
                    imports.append({"file": name, "path": fields[1]})
                elif fields[0] == "on":
                    actions.append({"file": name, "trigger": line[3:], "commands": []})
                    block = actions[-1]
            elif block is not None:
                block["options" if "options" in block else "commands"].append(line.strip())
    return {"services": services, "imports": imports, "actions": actions}
si = init_data(stock)
ci = init_data({**current, **{"device/init/" + p.name: p for p in (dev / "init").glob("*.rc") if "recovery" not in p.name}})
groups = collections.defaultdict(list)
for s in ci["services"]:
    groups[s["name"]].append(s)
save("init-stock.json", si)
save("init-current.json", ci)
save("init-conflicts.json", {"potential_duplicate_services": {k:v for k,v in groups.items() if len(v)>1},
    "note": "Nested init/hw files may not be imported. Follow imports and source-generated rc before deciding conflicts."})
def codecs(files):
    rows = []
    for name, p in sorted(files.items()):
        if not re.search(r"/etc/(?:[^/]+/)*media_(?:codecs|profiles).*\.xml$", name) or p.is_symlink():
            continue
        t = xml(p)
        if t is None:
            continue
        for e in t.iter():
            if e.tag.split("}")[-1].lower() == "include":
                href = e.get("href") or e.get("file")
                if href:
                    target = str(Path(name).parent / href)
                    rows.append({"file": name, "include": href, "same_directory_exists": target in files,
                                 "stock_matches": sorted(n for n in stock if Path(n).name == Path(href).name),
                                 "current_matches": sorted(n for n in current if Path(n).name == Path(href).name)})
    return rows
save("media-codec-stock.json", codecs(stock))
save("media-codec-current.json", codecs(current))
def links(files):
    return {n: os.readlink(p) for n,p in sorted(files.items()) if p.is_symlink()}
sl, cl = links(stock), links(current)
save("stock-symlinks.json", sl)
save("current-symlinks.json", cl)
wifi = re.compile(r"wlan|wifi|wcnss|adrastea|cnss|wpss", re.I)
save("wlan.json", {"stock_symlinks": {n:t for n,t in sl.items() if wifi.search(n+" "+t)},
    "stock_paths": sorted(n for n in stock if wifi.search(n)), "current_paths": sorted(n for n in current if wifi.search(n)),
    "current_symlinks": {n:t for n,t in cl.items() if wifi.search(n+" "+t)}})
# Structured stock text evidence for permissions, properties, startup and charging.
pattern = re.compile(r"battery|health|charg|gatekeeper|keymint|fingerprint|sensor|thermal|power|radio|audio|camera|wlan|wifi|display|graphics|bluetooth|gnss|usb|module|adsp|cdsp|firmware", re.I)
config = {}
for n,p in sorted(stock.items()):
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 4*1024*1024:
        continue
    if n.endswith(".prop") or re.search(r"(?:^|/)(?:ueventd[^/]*\.rc|fstab[^/]*|(?:plat_|vendor_|odm_)?(?:file|property|service|hwservice|genfs)_contexts)$", n):
        lines = [l for l in read(p).splitlines() if not l.lstrip().startswith("#") and (pattern.search(l) or "fstab" in n)]
        if lines:
            config[n] = lines
save("stock-permissions-properties.json", config)
# Preserve current tree build definitions as evidence, not a generated product image.
build = {}
for root in (dev, vendor.parent):
    for p in root.rglob("*"):
        if not p.is_file() or p.is_symlink() or ".git" in p.parts or "proprietary" in p.parts:
            continue
        if p.name in ("Android.bp", "Android.mk", "BoardConfig.mk", "BoardConfigVendor.mk", "device.mk", "mist-vendor.mk", "proprietary-files.txt", "extract-files.py") or "sepolicy" in p.parts or "vintf" in p.parts:
            build[str(p.relative_to(work))] = read(p)
save("current-build-definitions.json", build)
# Compare stock bytes only for already selected files; fixups may explain changes.
hashes = []
for n in sorted(stock.keys() & current.keys()):
    if stock[n].is_symlink() or current[n].is_symlink():
        continue
    try:
        a,b = sha(stock[n]),sha(current[n])
        hashes.append({"path": n, "stock_sha256": a, "current_sha256": b, "identical": a==b})
    except OSError as e:
        errors.append({"file": n, "error": str(e)})
save("selected-blob-hashes.json", hashes)
def module_info(p):
    def cmd(*a):
        res = subprocess.run(a, capture_output=True, text=True, errors="replace", timeout=30)
        return res.stdout.strip() if not res.returncode else None
    return {"sha256": sha(p), "name": cmd("modinfo","-F","name",str(p)),
            "vermagic": cmd("modinfo","-F","vermagic",str(p)), "depends": cmd("modinfo","-F","depends",str(p)),
            "required_symbol_versions": cmd("modprobe","--dump-modversions",str(p))}
mods = {}
for section in ("vendor_ramdisk","vendor_dlkm","system_dlkm"):
    path = kernel / section
    mods[section] = {"lists": {p.name: read(p) for p in path.glob("modules.*") if p.is_file() and not p.is_symlink()},
                     "modules": {p.name: module_info(p) for p in sorted(path.glob("*.ko"))}}
save("prebuilt-modules.json", mods)
save("stock-module-paths.json", {n: module_info(p) for n,p in stock.items() if n.endswith(".ko") and not p.is_symlink()})
save("stock-inventory.json", {n: {"type":"symlink","target":sl[n]} if n in sl else {"type":"file","size":p.stat().st_size} for n,p in stock.items()})
save("analysis-errors.json", errors)
summary = {"stock_files":len(stock),"current_files":len(current),"stock_elf":len(se),"current_elf":len(ce),
           "unresolved_elf_edges":len(gaps),"camera_candidates":len(seen),"stock_symlinks":len(sl),
           "errors":len(errors),"limitations":["No Android source module resolution, linker namespace or symbol ABI validation",
              "No live sysfs values, HAL transaction tests or physical hardware validation",
              "Symlink retention depends on extractor; compare raw filesystem if links absent",
              "No full build, flashing, or source changes"]}
save("phase4b-summary.json", summary)
print(json.dumps(summary,indent=2))
