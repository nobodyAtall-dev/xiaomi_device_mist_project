#!/usr/bin/env python3
"""Prepare isolated Mist bring-up candidates; never publish from this script."""
import collections, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile

work, root = map(lambda x: Path(x).resolve(), sys.argv[1:3])
dump=work/'dump'; reports=work/'reports'
device=root/'device/xiaomi/mist'; vendor=root/'vendor/xiaomi/mist'; kernel=root/'kernel/xiaomi/mist-prebuilt'
for p in (device,vendor,kernel,reports): p.mkdir(parents=True,exist_ok=True)
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def record(name,v): write(reports/name,json.dumps(v,indent=2))
def read_props(p):
    return dict(x.split('=',1) for x in p.read_text(errors='replace').splitlines() if x and not x.startswith('#') and '=' in x)
meta=read_props(reports/'metadata')
assert meta.get('pre-device')=='mist' and meta.get('post-sdk-level')=='37', 'Unexpected OTA device/SDK'
assert 'OS4.0.8.0.XPUMIXM' in (reports/'firmware-source.json').read_text(), 'Baseline changed: review before generating'
assert (reports/'archive.md5').read_text().split()[0]=='3695aedf1f96d96bbdac41bb247bc8bf', 'Unexpected OTA checksum'
# Source directory normalization: Dumpyara can expose system/system.
def source(p):
    a=dump/p
    if a.is_file() and not a.is_symlink():return a
    if p.startswith('system/'):
        a=dump/'system'/p
        if a.is_file() and not a.is_symlink():return a
    return None
# Primary list is already based on Mist stock, not Sky binaries.
# Preserve remaps and module directives, discard donor pin hashes. Do not apply signature patches without review.
candidates={}; missing=[]; conflicts=[]; review=[]
for label,ref in [('ravelin',work/'ravelin'),('sky',work/'sky'),('garnet',work/'garnet')]:
    for raw in (ref/'proprietary-files.txt').read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith('#'):continue
        line=line.split('|',1)[0]
        paths=line.lstrip('-').split(';',1)[0].split(':',1)
        src,dst=paths[0],paths[-1]
        if not src.startswith(('vendor/','odm/','system_ext/','product/','system/')) or src.endswith('.ko'):continue
        if not source(src):
            missing.append([label,src]);continue
        if label!='ravelin':
            review.append([label,src,dst]);continue
        if dst in candidates and candidates[dst]!=line:
            conflicts.append([dst,candidates[dst],line]);continue
        candidates[dst]=line
# Review stock-only hardware HAL entries and dependencies; do not indiscriminately add all MIUI files.
stock_elf={}; sonames=collections.defaultdict(list)
for part in ('vendor','odm','system_ext','product','system'):
    for p in (dump/part).rglob('*'):
        if p.is_symlink() or not p.is_file():continue
        rel=str(p.relative_to(dump))
        if rel.startswith('system/system/'):rel=rel[len('system/'):]
        try:
            with p.open('rb') as f:
                if f.read(4)!=b'\x7fELF':continue
                f.seek(0);e=ELFFile(f);needed=[];soname=p.name
                d=e.get_section_by_name('.dynamic')
                if d:
                    for tag in d.iter_tags():
                        if tag.entry.d_tag=='DT_NEEDED':needed.append(tag.needed)
                        if tag.entry.d_tag=='DT_SONAME':soname=tag.soname
                stock_elf[rel]={'needed':needed,'soname':soname,'bits':e.elfclass}
                sonames[(soname,e.elfclass)].append(rel)
        except Exception as e:review.append(['elf-read',rel,str(e)])
selected_sources={x.lstrip('-').split(';',1)[0].split(':',1)[0] for x in candidates.values()}
deps=[]
for p in sorted(selected_sources):
    e=stock_elf.get(p)
    if not e:continue
    for n in e['needed']:
        matches=sonames[(n,e['bits'])]
        if not set(matches)&selected_sources:deps.append({'consumer':p,'needed':n,'stock_candidates':matches})
record('blob-review.json',{'selected':len(candidates),'missing_reference_paths':missing,'conflicts':conflicts,'additional_reference_candidates':review,'unresolved_dependency_review':deps})
assert len(candidates)>500,'Unexpectedly few matching Ravelin blobs'
write(device/'proprietary-files.txt','# Mist Global OS4.0.8.0.XPUMIXM\n# Ravelin-derived candidate list; verify fixups and dependencies before release.\n\n'+'\n'.join(candidates[k] for k in sorted(candidates))+'\n')
# Do not silently import a donor patch set. Keep stock binary contents intact until patch review.
write(device/'extract-files.py','''#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
# SPDX-License-Identifier: Apache-2.0
from extract_utils.main import ExtractUtils, ExtractUtilsModule

module = ExtractUtilsModule(
    'mist', 'xiaomi',
    namespace_imports=['device/xiaomi/mist', 'hardware/xiaomi',
                       'hardware/qcom-caf/sm8450-6.6', 'hardware/qcom-caf/wlan'],
)
if __name__ == '__main__':
    ExtractUtils.device(module).run()
''')
write(device/'setup-makefiles.py','#!/usr/bin/env -S ./extract-files.py --regenerate_makefiles\n# SPDX-License-Identifier: Apache-2.0\n')
for n in ('extract-files.py','setup-makefiles.py'):(device/n).chmod(0o755)
write(device/'Android.bp','// SPDX-License-Identifier: Apache-2.0\nsoong_namespace {\n    imports: ["hardware/xiaomi"],\n}\n')
write(device/'AndroidProducts.mk','PRODUCT_MAKEFILES := $(LOCAL_DIR)/lineage_mist.mk\nCOMMON_LUNCH_CHOICES := lineage_mist-user lineage_mist-userdebug lineage_mist-eng\n')
write(device/'lineage_mist.mk','''# SPDX-License-Identifier: Apache-2.0
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product, device/xiaomi/mist/device.mk)
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)

PRODUCT_NAME := lineage_mist
PRODUCT_DEVICE := mist
PRODUCT_BRAND := Redmi
PRODUCT_MODEL := Redmi Note 17 5G
PRODUCT_MANUFACTURER := Xiaomi
PRODUCT_GMS_CLIENTID_BASE := android-xiaomi
''')
write(device/'lineage.dependencies',json.dumps([{'repository':'android_hardware_xiaomi','target_path':'hardware/xiaomi'}],indent=2)+'\n')
# Physical geometry cross-checked against Phase 1B fastboot and Phase 2 OTA.
# The stock MIUI-only partitions remain unmodified; confirm OTA metadata and lpmake layout in build review.
write(device/'BoardConfig.mk','''# SPDX-License-Identifier: Apache-2.0
DEVICE_PATH := device/xiaomi/mist
KERNEL_PATH := kernel/xiaomi/mist-prebuilt
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-2a-dotprod
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := kryo300
TARGET_BOARD_PLATFORM := parrot
TARGET_BOOTLOADER_BOARD_NAME := mist
TARGET_NO_BOOTLOADER := true
BOARD_USES_QCOM_HARDWARE := true

BOARD_BOOT_HEADER_VERSION := 4
BOARD_INIT_BOOT_HEADER_VERSION := 4
BOARD_KERNEL_PAGESIZE := 4096
BOARD_KERNEL_BASE := 0x00000000
BOARD_RAMDISK_USE_LZ4 := true
BOARD_USES_GENERIC_KERNEL_IMAGE := true
TARGET_KERNEL_ARCH := arm64
TARGET_NO_KERNEL := false
TARGET_PREBUILT_KERNEL := $(KERNEL_PATH)/Image
BOARD_PREBUILT_DTBOIMAGE := $(KERNEL_PATH)/dtbo.img
BOARD_PREBUILT_DTBIMAGE_DIR := $(KERNEL_PATH)/dtb
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
TARGET_NEEDS_DTBOIMAGE := true
BOARD_MKBOOTIMG_ARGS := --header_version 4
BOARD_KERNEL_CMDLINE := video=vfb:640x400,bpp=32,memsize=3072000 erofs.reserved_pages=64 bootconfig
BOARD_BOOTCONFIG := androidboot.hardware=qcom androidboot.memcg=1 androidboot.usbcontroller=a600000.dwc3
BOARD_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE := 8388608
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 104857600
BOARD_DTBOIMG_PARTITION_SIZE := 25165824
BOARD_FLASH_BLOCK_SIZE := 262144

BOARD_SUPER_PARTITION_SIZE := 10200547328
BOARD_SUPER_PARTITION_GROUPS := qti_dynamic_partitions
BOARD_QTI_DYNAMIC_PARTITIONS_SIZE := 10190061568
BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST := odm product system system_ext system_dlkm vendor vendor_dlkm
BOARD_USES_METADATA_PARTITION := true
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS := boot init_boot dtbo odm product recovery system system_ext system_dlkm vbmeta vbmeta_system vendor vendor_boot vendor_dlkm
-include vendor/lineage/config/BoardConfigReservedSize.mk
BOARD_ODMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDOR_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_COPY_OUT_ODM := odm
TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_VENDOR_DLKM := vendor_dlkm
TARGET_COPY_OUT_SYSTEM_DLKM := system_dlkm
TARGET_COPY_OUT_SYSTEM_EXT := system_ext
TARGET_COPY_OUT_PRODUCT := product

BOARD_VENDOR_RAMDISK_KERNEL_MODULES := $(wildcard $(KERNEL_PATH)/vendor_ramdisk/*.ko)
BOARD_VENDOR_RAMDISK_KERNEL_MODULES_LOAD := $(strip $(shell cat $(KERNEL_PATH)/vendor_ramdisk/modules.load))
BOARD_VENDOR_RAMDISK_RECOVERY_KERNEL_MODULES_LOAD := $(strip $(shell cat $(KERNEL_PATH)/vendor_ramdisk/modules.load.recovery))
BOARD_VENDOR_KERNEL_MODULES := $(wildcard $(KERNEL_PATH)/vendor_dlkm/*.ko)
BOARD_VENDOR_KERNEL_MODULES_LOAD := $(strip $(shell cat $(KERNEL_PATH)/vendor_dlkm/modules.load))
BOARD_SYSTEM_KERNEL_MODULES := $(wildcard $(KERNEL_PATH)/system_dlkm/*.ko)
BOARD_SYSTEM_KERNEL_MODULES_LOAD := $(strip $(shell cat $(KERNEL_PATH)/system_dlkm/modules.load))

BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/init/fstab.qcom
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
TARGET_USERIMAGES_USE_F2FS := true
BOARD_AVB_ENABLE := true
BOARD_MOVE_GSI_AVB_KEYS_TO_VENDOR_BOOT := true
BOARD_AVB_VBMETA_SYSTEM := system system_ext product
VENDOR_SECURITY_PATCH := 2026-05-05
DEVICE_MATRIX_FILE := hardware/qcom-caf/common/compatibility_matrix_aidl.xml
DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE += hardware/xiaomi/vintf/xiaomi_framework_compatibility_matrix.xml hardware/qcom-caf/common/vendor_framework_compatibility_matrix.xml
BOARD_SHIPPING_API_LEVEL := 202404
BOARD_VENDOR_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy/vendor
include device/qcom/sepolicy_vndr/SEPolicy.mk
include vendor/xiaomi/mist/BoardConfigVendor.mk
''')
# Fstab from stock, retain storage encryption and genuine partitions, exclude MIUI overlay mounts.
p=dump/'vendor_boot/ramdisk/first_stage_ramdisk/fstab.default'
fstab=[]
for line in p.read_text().splitlines():
    fields=line.split()
    if not fields or line.lstrip().startswith('#'):fstab.append(line);continue
    if len(fields)<5:continue
    if fields[0]=='overlay' or fields[1] in ('/mi_ext','/mnt/vendor/mi_ext','/mi_product','/mnt/vendor/mi_product'):continue
    fstab.append(line)
write(device/'init/fstab.qcom','\n'.join(fstab)+'\n')
write(device/'init/Android.bp','''// SPDX-License-Identifier: Apache-2.0
prebuilt_etc {
    name: "fstab.qcom",
    src: "fstab.qcom",
    vendor: true,
}
prebuilt_etc {
    name: "fstab.qcom.vendor_ramdisk",
    src: "fstab.qcom",
    filename: "fstab.qcom",
    vendor_ramdisk: true,
    relative_install_path: "first_stage_ramdisk",
}
''')
write(device/'device.mk','''# SPDX-License-Identifier: Apache-2.0
LOCAL_PATH := device/xiaomi/mist
$(call inherit-product, hardware/qcom-caf/common/common.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/launch_with_vendor_ramdisk.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/generic_ramdisk.mk)
PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_SHIPPING_API_LEVEL := 36
PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 4096
PRODUCT_SOONG_NAMESPACES += $(LOCAL_PATH) hardware/xiaomi
PRODUCT_PACKAGES += fstab.qcom fstab.qcom.vendor_ramdisk fastbootd update_engine update_engine_sideload update_verifier
$(call inherit-product, vendor/xiaomi/mist/mist-vendor.mk)
''')
# Policy needs device-specific review. Only use the primary reference policy as candidate, retaining original headers.
policy=work/'ravelin/sepolicy/vendor'
if policy.is_dir():shutil.copytree(policy,device/'sepolicy/vendor',dirs_exist_ok=True)
# Separate prebuilt repository, never embed kernel/DT images in device/vendor.
def copy(src,dst):
    assert src.is_file(),str(src)+' missing'
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
copy(dump/'boot/kernel',kernel/'Image')
copy(dump/'vendor_boot/dtb.img',kernel/'dtb/dtb.img')
copy(dump/'temp_raw_images/dtbo.img',kernel/'dtbo.img')
# Exclude obsolete parallel system module directories; exact boot version selection.
ver='6.6.118-android15-8-gc4127a25dcf3-ab15863337-4k'
sets={'system_dlkm':dump/'system_dlkm/lib/modules'/ver,'vendor_dlkm':dump/'vendor_dlkm/lib/modules','vendor_ramdisk':dump/'vendor_boot/ramdisk/lib/modules'}
modreport={}
for label,src in sets.items():
    assert src.is_dir(),str(src)+' missing'
    dest=kernel/label;dest.mkdir()
    for p in src.rglob('*.ko'):
        if p.is_symlink():continue
        q=dest/p.name
        if q.exists() and hashlib.sha256(q.read_bytes()).digest()!=hashlib.sha256(p.read_bytes()).digest():raise RuntimeError('Module name collision: '+label+'/'+p.name)
        copy(p,q)
    for n in ('modules.load','modules.load.recovery','modules.blocklist','modules.options','modules.softdep'):
        if not (src/n).is_file():continue
        if n.startswith('modules.load'):
            entries=[Path(x.split()[0]).name for x in (src/n).read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
            write(dest/n,'\n'.join(entries)+'\n')
        else:copy(src/n,dest/n)
    assert (dest/'modules.load').is_file(),'Missing load list: '+label
    load=[Path(x.split()[0]).name for x in (dest/'modules.load').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
    missing_load=[x for x in load if not (dest/x).is_file()]
    recovery_missing=[]
    if (dest/'modules.load.recovery').is_file():
        recovery_missing=[x for x in (dest/'modules.load.recovery').read_text().splitlines() if x and not (dest/x).is_file()]
    modreport[label]={'modules':len(list(dest.glob('*.ko'))),'missing_load_entries':missing_load,'missing_recovery_load_entries':recovery_missing,'vermagic':dict(collections.Counter(subprocess.run(['modinfo','-F','vermagic',p],capture_output=True,text=True).stdout.strip() for p in dest.glob('*.ko')))}
record('kernel-module-review.json',modreport)
# Binary contents are kept in the temporary private staging directory only.
record('kernel-file-hashes.json',{str(p.relative_to(kernel)):hashlib.sha256(p.read_bytes()).hexdigest() for p in kernel.rglob('*') if p.is_file()})
record('stage-summary.json',{'firmware':'OS4.0.8.0.XPUMIXM','device_files':sum(p.is_file() for p in device.rglob('*')),'blob_candidates':len(candidates),'kernel_module_sets':modreport,'draft_only':True,'blocking_reviews':['HAL and VINTF integration','review Ravelin blob fixups and dependency closure','SELinux and device init review','verify prebuilt board flags and module ABI','AVB signing and MIUI partition coexistence','compile and boot validation']})
print('Prepared isolated device and kernel candidates; vendor generation follows.')
