# Mist — LineageOS 24.0

Redmi Note 17 5G / POCO M8 Power 5G (mist)  
Target: LineageOS 24.0 (Android 17)  
Last updated: 27 November 2026

## 1. Project status

| Phase | Description | Status |
| --- | --- | --- |
| 1 | HyperOS 3 firmware extraction | Completed |
| 1B | Deep hardware analysis | Completed; limitations below |
| 2 | Reference research and dual-firmware comparison | In progress |
| 3 | Device and vendor tree bring-up | Pending |
| 4 | ROM compilation and debugging | Pending |
| 5 | Boot and hardware testing | Pending |

**Current task:** Phase 2 workflow is running, as reported by the user. Review its results before creating the trees.

## 2. Firmware

| Firmware | Version | Package |
| --- | --- | --- |
| HyperOS 3 Global | OS3.0.304.0.WPUMIXM (Android 16) | Fastboot TGZ |
| HyperOS 4 Global | OS4.0.8.0.XPUMIXM (Android 17) | Full OTA ZIP (payload.bin) |

Use HyperOS 3 for factory partition information and HyperOS 4 as the preferred Android 17 baseline after validation. Keep kernel, modules and vendor binaries compatible; do not mix releases blindly.

HyperOS 4 package: `mist_global-ota_full-OS4.0.8.0.XPUMIXM-user-17.0-3695aedf1f.zip`  
Published MD5: `3695aedf1f96d96bbdac41bb247bc8bf`  
[Global firmware source](https://mirom.ezbox.idv.tw/en/phone/mist/roms-global-stable/)

## 3. Findings

| Item | HyperOS 3 baseline |
| --- | --- |
| Platform | parrot |
| Vendor architecture | ARM64-only |
| Kernel | 6.6.118, android15-8 |
| Partition scheme | Virtual A/B, dynamic partitions |
| Boot partitions | init_boot, vendor_boot, recovery |
| Kernel modules | system_dlkm and vendor_dlkm |
| Super size | 10,200,547,328 bytes |
| Dynamic group size | 10,190,061,568 bytes |

These values were recorded in previous analysis; verify them against the original artifacts before using them in build configuration. HyperOS 4 values are pending.

Phase 1B logged 131 physical partition metadata rows, 33 DT candidates, 5,312 ELF files, 757 module entries, 1,193 hardware configurations, 977 matching Sky blob paths and 495 missing paths. Path matches do not establish binary compatibility.

## 4. Reference trees

| Reference | Branch | Purpose |
| --- | --- | --- |
| [Ravelin SM4450 common](https://github.com/xiaomi-ravelin/android_device_xiaomi_sm4450-common/tree/lineage-24.0) | 24.0 | Primary structure: Parrot, Linux 6.6, ARM64, system_dlkm |
| [Sky device](https://github.com/sky-lineage/android_device_xiaomi_sky/tree/lineage-23.2) / [vendor](https://github.com/sky-lineage/android_vendor_xiaomi_sky/tree/lineage-23.2) | 23.2 | Blob selection and fixups |
| [Ravelin Sky](https://github.com/xiaomi-ravelin/android_device_xiaomi_sky/tree/lineage-24.0) / [Sky vendor](https://github.com/xiaomi-sm4450-sky/android_vendor_xiaomi_sky/tree/lineage-24.0) | 24.0 | Android 17 device structure; pairing unverified |
| [Garnet](https://github.com/LineageOS/android_device_xiaomi_garnet/tree/lineage-24.0) / [23.2](https://github.com/LineageOS/android_device_xiaomi_garnet/tree/lineage-23.2) | 24.0 / 23.2 | HAL and SELinux patterns; different SoC |

Ravelin kernel references: [kernel](https://github.com/xiaomi-ravelin/android_kernel_xiaomi_sm4450), [DT](https://github.com/xiaomi-ravelin/android_kernel_xiaomi_sm4450-devicetrees), [modules](https://github.com/xiaomi-ravelin/android_kernel_xiaomi_sm4450-modules), all lineage-24.0. Mist support and a matching populated common vendor tree are not verified.

## 5. Development history

| Change | Result |
| --- | --- |
| Initial workflow ([commit](../../commit/6d2783f0cc2a317994a38cd4aeaadebb8964a196)) | Draft generation superseded by research-only approach |
| [First failed run](../../actions/runs/45916919483) | Missing Xiaomi CDN; fixed in [502df2e](../../commit/502df2e49187abdc2438dcce6acc6f1792cb34e6) |
| [Second failed run](../../actions/runs/45917251860) | Version parsing error; fixed in [a8220e5](../../commit/a8220e510ae4d6be70c1cef3d62567d552c7b8d8) |
| [Phase 1 run](../../actions/runs/45917382922) | Passed; 7.5 GiB, 16 connections, peak 251 MiB/s; [13 reports](../../actions/runs/45917382922/artifacts/15162409622) |
| [Phase 1B run](../../actions/runs/45918710446) | Passed with six diagnostics; [1,283 reports](../../actions/runs/45918710446/artifacts/15164370694) |
| Phase 2 | [Workflow](.github/workflows/mist-phase2.yml), [OTA discovery](scripts/discover-mist-ota.py), [comparison](scripts/compare-mist-firmware.py); runtime results pending |
| 27 November 2026 | Simplified this changelog; no workflow or source tree changes |

Phase 2 outputs: `mist-deep-analysis-hyperos3`, `mist-deep-analysis-hyperos4`, `mist-dual-comparison`. Separate runners limit disk usage. Artifacts expire after 30 days.

## 6. Open issues and next steps

- [ ] Review Phase 2 results and verify full OTA identity and payload extraction, including raw image retention.
- [ ] Review rescue extraction failure, modem extraction completeness, duplicate A/B names and kernel extraction diagnostics. Node 20 deprecation warning is nonblocking.
- [ ] Compare HyperOS 4 HALs, VINTF, ELF dependencies, kernel ABI, AVB and partition layout. Broader reference comparisons and binary content hashes remain to implement. OTA may omit physical partition metadata.
- [ ] Choose a coherent Mist kernel strategy (stock prebuilt or verified source) and matching DTB/DTBO/modules.
- [ ] Generate clean device and vendor trees using Lineage extract-utils, reviewed blobs, Soong definitions, SELinux and init configuration; preserve licensing.
- [ ] Compile LineageOS 24.0 and debug; validate boot and hardware.

No compilation or boot success has been established.

## 7. Project conventions

- Automation and reports stay in this repository. Output repositories: `android_device_xiaomi_mist` and `android_vendor_xiaomi_mist` (private vendor recommended). Only legitimate source/build files belong there.
- Automatic firmware discovery and downloads: `aria2c -x16 -s16 -k1M`.
- Git identity: `nobodyAtall-dev` / `hashynaa@gmail.com`. Use existing `GH_PAT` secret for authorized publishing; never expose it.
- No flashing, publishing during research, or overwriting existing trees without approval.
- Future chats: read this file first; update status, findings, fixes, relevant links and next steps after each change or reviewed run. Keep entries concise, factual and chronological.
