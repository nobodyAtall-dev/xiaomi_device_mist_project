#!/usr/bin/env python3
"""Select verified Mist stock configuration additions, preserving existing blob directives."""
import sys,json,re
from pathlib import Path
work=Path(sys.argv[1]); dump=work/'dump'; dev=work/'android/device/xiaomi/mist'
plist=dev/'proprietary-files.txt'
old=plist.read_text()
def paths(line):
    return line.strip().lstrip('-').split('|',1)[0].split(';',1)[0].split(':')
existing={p for l in old.splitlines() if l.strip() and not l.lstrip().startswith('#') for p in paths(l)}
# Explicit hardware assets, not factory tests, stock framework replacements, or donor binaries.
exact=[
 'vendor/bin/hw/android.hardware.biometrics.fingerprint-service.odm',
 'vendor/etc/init/fingerprint-odm.rc',
 'vendor/etc/vintf/manifest/fingerprint-odm.xml',
 'vendor/etc/permissions/android.hardware.fingerprint.xml',
 'vendor/lib64/hw/fingerprint.goodix_fod.so',
 'vendor/lib64/hw/fingerprint.jiiov.so',
 'vendor/lib64/vendor.xiaomi.hardware.fingerprintextension-V1-ndk.so',
 'vendor/etc/audio/audio_module_config_primary.xml',
 'vendor/etc/audio/vendor_audio_interfaces.xml',
 'vendor/etc/sensors/hals.conf',
]
patterns=[
 'vendor/etc/audio/sku_ravelin/*.xml',
 'vendor/etc/sensors/config/*.json',
]
# Exclude effects configuration until software effects compatibility is established.
excluded={'audio_effects.xml','audio_effects_config.xml','audio_effects_config_stub.xml'}
selected=set(exact)
for pattern in patterns:
    selected.update(str(p.relative_to(dump)) for p in dump.glob(pattern) if p.is_file() and not p.is_symlink() and p.name not in excluded)
missing=[p for p in exact if not (dump/p).is_file()]
if missing: raise SystemExit(f'Expected stock assets missing: {missing}')
added=sorted(p for p in selected-existing if (dump/p).is_file() and not (dump/p).is_symlink())
if added:
    plist.write_text(old.rstrip()+'\n\n# Mist stock hardware configuration and fingerprint\n'+'\n'.join(added)+'\n')
(work/'reports/hardware-additions.json').write_text(json.dumps({'added':added,'already_listed':sorted(selected&existing),'note':'Stock fingerprint dependencies, audio policy includes and sensors runtime compatibility still need review.'},indent=2))
print(f'Added {len(added)} stock paths')
