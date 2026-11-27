#!/usr/bin/env python3
"""Phase 4C: bounded stock camera/media integration; preserve existing entries."""
import collections, json, re, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
import xml.etree.ElementTree as ET

work=Path(sys.argv[1])
dump=work/'dump'
dev=work/'android/device/xiaomi/mist'
vendor=work/'android/vendor/xiaomi/mist'
reports=work/'reports'
def save(n,d): (reports/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
plist=dev/'proprietary-files.txt'
old=plist.read_text()
existing={part for line in old.splitlines() if line.strip() and not line.lstrip().startswith('#') for part in line.strip().lstrip('-').split('|',1)[0].split(';',1)[0].split(':')}
stock={str(p.relative_to(dump)):p for p in (dump/'vendor').rglob('*') if p.is_file() and not p.is_symlink()}
required={'vendor/lib64/hw/camera.qcom.so','vendor/lib64/hw/com.qti.chi.override.so','vendor/lib64/camx.provider-impl.so','vendor/lib64/camx.device-impl.so','vendor/etc/camera/camxoverridesettings.txt','vendor/firmware/CAMERA_ICP.mdt','vendor/firmware/CAMERA_ICP.mbn'}
assert required <= stock.keys(), sorted(required-stock.keys())
# Camera HAL loadable modules, sensor/tuning variants, firmware, and camera configuration.
# Do not include the stock camera app, framework JARs or other partitions.
selected={n for n in stock if n.startswith(('vendor/lib64/camera/','vendor/etc/camera/','vendor/firmware/CAMERA_ICP.')) or re.match(r'vendor/lib64/(?:hw/)?(?:camx\.|libcamx|camera\.qcom\.|com\.qti\.chi|libmmcamera|libcamerapostproc|libcamera_nn|libqshcamera)',n)}
selected |= required
# Only explicit proprietary libraries from the Phase 4B closure. Platform AIDL,
# HIDL, libc, graphics source libraries etc are deliberately NOT copied.
approved=set('com.qti.feature2.generic.so com.qti.stats.common.so libMiPhotoFilter.so libSNPE.so libanc_night.so libanc_single_rt_bokeh.so libarcsoft_beautyshot.so libbitmlenginev2.so libchilog.so libcom.qti.chinodeutils.so libmialgo_ai_vision.so libmialgo_sd.so libmialgo_utils.so libmorpho_HdrChecker.so libmpbase.so libopencv.so libopencv3a.so libsynx.so libvmmem.so vendor.qti.hardware.camera.postproc-V1-ndk.so vendor.qti.hardware.camera.postproc@1.0-service-impl.so'.split())
def needed(p):
    with p.open('rb') as f:
        if f.read(4)!=b'\x7fELF':return []
        f.seek(0)
        e=ELFFile(f)
        return [t.needed for s in e.iter_segments() if s.header.p_type=='PT_DYNAMIC' for t in s.iter_tags() if t.entry.d_tag=='DT_NEEDED']
idx=collections.defaultdict(list)
for n in stock:
    if n.startswith('vendor/lib64/') and n.endswith('.so'):idx[Path(n).name].append(n)
have={Path(n).name for n in existing}
queue=list(selected|{'vendor/bin/hw/vendor.qti.camera.provider-service_64'})
seen=set(); unresolved=collections.defaultdict(set)
while queue:
    n=queue.pop()
    if n in seen:continue
    seen.add(n)
    for dep in needed(stock[n]):
        if dep in have:continue
        matches=idx[dep]
        if dep in approved and len(matches)==1:
            selected.add(matches[0]);queue.append(matches[0])
        elif not any(x in selected for x in matches):
            unresolved[dep].add(n)
# Retain existing source Codec2 rule. All other Google software codec XMLs
# are supplied by the matching frameworks/av source, not Xiaomi copies.
# Source media_codecs_vendor_audio.xml comes from matching audio HAL.
# Validate the stock include graph and report any unexplained includes.
source_names={'media_codecs_c2_audio.xml','media_codecs_vendor_audio.xml','media_codecs_google_audio.xml','media_codecs_google_telephony.xml','media_codecs_google_c2.xml','media_codecs_google_c2_audio.xml','media_codecs_google_c2_video.xml','media_codecs_google_c2_telephony.xml'}
codec_graph={}
for name in ['media_codecs_ravelin.xml','media_codecs.xml']+sorted(source_names):
    p=dump/'vendor/etc'/name
    if p.is_file():
        codec_graph[name]=[x.get('href') for x in ET.parse(p).getroot().iter('Include')]
save('codec-stock-include-graph.json',codec_graph)
# Existing rules already install ravelin XML. Do not duplicate destinations
# with the stock media_codecs.xml; verify SKU selection separately.
new=sorted(selected-existing)
assert all(n.startswith('vendor/') and n in stock for n in new)
assert all(stock[n].stat().st_size<104857600 for n in new)
if new:
    plist.write_text(old.rstrip()+'\n\n# Mist Phase 4C camera hardware closure\n'+'\n'.join(new)+'\n')
save('phase4c-selection.json',{'added':new,'already_listed':sorted(selected&existing),'unresolved_source_or_blob':{k:sorted(v) for k,v in unresolved.items()},'note':'Candidate integration; full source build and runtime still required.'})
print('Selected',len(new),'new assets;',len(unresolved),'unresolved SONAMEs to classify')

# Source copy rules use the exact files verified in the upstream branch.
mk=dev/'device.mk'
text=mk.read_text()
entries={name:'frameworks/av/media/libstagefright/data/'+name for name in sorted(source_names) if name.startswith('media_codecs_google_') and name!='media_codecs_google_c2_telephony.xml'}
entries['media_codecs_vendor_audio.xml']='hardware/qcom-caf/sm8450-6.6/audio/primary-hal/configs/common/media_codecs_vendor_audio.xml'
rules=[]
for name,src in entries.items():
    dest='$(TARGET_COPY_OUT_VENDOR)/etc/'+name
    if dest not in text:rules.append('PRODUCT_COPY_FILES += '+src+':'+dest)
if rules:mk.write_text(text.rstrip()+'\n\n# Phase 4C codec include closure\n'+'\n'.join(rules)+'\n')
# Stock exact labels, missing from the checked Qualcomm common/parrot policies.
fc=dev/'sepolicy/vendor/file_contexts'
sc=dev/'sepolicy/vendor/service_contexts'
for path, key, line in [
    (fc,r'/vendor/bin/hw/vendor\.qti\.camera\.provider-service_64',r'/vendor/bin/hw/vendor\.qti\.camera\.provider-service_64 u:object_r:hal_camera_default_exec:s0'),
    (sc,'android.hardware.camera.provider.ICameraProvider/vendor_qti/0','android.hardware.camera.provider.ICameraProvider/vendor_qti/0 u:object_r:hal_camera_service:s0')]:
    content=path.read_text()
    if key not in content:path.write_text(content.rstrip()+'\n\n# Mist stock AIDL camera provider\n'+line+'\n')
# Review HAL declarations and init without wholesale importing stock RC or manifests.
manifest=vendor/'proprietary/vendor/etc/vintf/manifest/vendor.qti.camera.provider.xml'
rc=vendor/'proprietary/vendor/etc/init/vendor.qti.camera.provider-service_64.rc'
assert 'ICameraProvider/vendor_qti/0' in manifest.read_text() and 'ICameraProvider/vendor_qti/0' in rc.read_text()
save('phase4c-hal-init-review.json',{'camera_instance':'android.hardware.camera.provider.ICameraProvider/vendor_qti/0','manifest_and_rc_agree':True,'pending':['VINTF compatibility against assembled build','camera postproc and AON service provider verification','normal boot module readiness and charger triggers','SELinux enforcing build and runtime denials','battery metadata runtime validation']})
