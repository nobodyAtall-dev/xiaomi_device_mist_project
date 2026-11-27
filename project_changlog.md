# Mist LineageOS 24.0 — project changelog
Updated 2026-11-27 (Malaysia time).

## Rules for future chats
Read this file first. Update it after every project change or reviewed run: date, commit, run/artifact links, verified findings, errors, fixes, remaining work. Target LineageOS 24.0 / Android 17 directly for Redmi Note 17 5G / POCO M8 Power 5G (mist). Keep automation and findings here only; android_device_xiaomi_mist and android_vendor_xiaomi_mist must remain clean source trees (normal Lineage extraction scripts allowed). Vendor private recommended. Git identity nobodyAtall-dev / hashynaa@gmail.com; GH_PAT secret already configured, never expose it. Downloads use aria2 -x16 -s16 -k1M. Do not flash or publish during research. Never equate green CI with complete extraction or bootability.

## History
- Initial workflow 6d2783f0cc2a317994a38cd4aeaadebb8964a196 generated draft trees; replaced by analysis-only at user request.
- Run 45916919483 failed because bn.d.miui.com missing from allowlist. Fixed automatic discovery and removed tree generation/publishing in 502df2e49187abdc2438dcce6acc6f1792cb34e6.
- Run 45917251860 failed on OS3 version parser. Fixed a8220e510ae4d6be70c1cef3d62567d552c7b8d8.
- Phase 1 success: https://github.com/nobodyAtall-dev/xiaomi_device_mist_project/actions/runs/45917382922 ; artifact 15162409622. 13 reports. HyperOS 3 OS3.0.304.0.WPUMIXM Android 16, 7.5 GiB, 16 connections, peak 251 MiB/s. Rescue/modem extraction errors; A/B duplicate names skipped.
- Phase 1B success: https://github.com/nobodyAtall-dev/xiaomi_device_mist_project/actions/runs/45918710446 ; artifact 15164370694. 1283 files, 131 physical metadata rows, 33 DT candidates, 5312 ELF files, 757 module entries, 1193 configs, 977 sky path matches and 495 missing, six diagnostics. Previous chat reported parrot, ARM64-only vendor, virtual A/B, init_boot, recovery, system_dlkm, kernel 6.6.118 android15-8, super 10200547328 bytes, group 10190061568 bytes; recheck actual artifact before using these values. Rescue remains unresolved; modem completeness unverified. Node 20 deprecation warning nonblocking. Artifacts expire after 30 days.

## References
- https://github.com/sky-lineage/android_device_xiaomi_sky/tree/lineage-23.2 and https://github.com/sky-lineage/android_vendor_xiaomi_sky/tree/lineage-23.2 — parrot, useful blob paths/fixups.
- https://github.com/xiaomi-ravelin/android_device_xiaomi_sm4450-common/tree/lineage-24.0 — parrot, kernel 6.6, ARM64-only, system_dlkm. Strong structural reference; matching populated common vendor not verified.
- https://github.com/xiaomi-ravelin/android_device_xiaomi_sky/tree/lineage-24.0 and https://github.com/xiaomi-sm4450-sky/android_vendor_xiaomi_sky/tree/lineage-24.0 — not verified matched pair.
- https://github.com/LineageOS/android_device_xiaomi_garnet/tree/lineage-24.0 and lineage-23.2 — parrot/SM7435, HAL/SELinux patterns, not binary donor.
- xiaomi-ravelin/android_kernel_xiaomi_sm4450, android_kernel_xiaomi_sm4450-devicetrees, android_kernel_xiaomi_sm4450-modules, lineage-24.0; mist support unverified.

## Current phase 2 — dual firmware comparison
HyperOS 3 Global fastboot baseline OS3.0.304.0.WPUMIXM (Android 16). HyperOS 4 Global full OTA OS4.0.8.0.XPUMIXM (Android 17), listed Nov 23, 5.2 GB, mist_global-ota_full-OS4.0.8.0.XPUMIXM-user-17.0-3695aedf1f.zip; published MD5 3695aedf1f96d96bbdac41bb247bc8bf. No matching fastboot listed. Source https://mirom.ezbox.idv.tw/en/phone/mist/roms-global-stable/
- Workflow .github/workflows/mist-phase2.yml commit 1c6eb26fe326c405571e088e2096fcbbc1bbce53.
- OTA discovery scripts/discover-mist-ota.py df10d5bc2e51566c7aec409b59b1fa084761c2a8.
- Comparison scripts/compare-mist-firmware.py e8254c1108da18e040b2295388ff1c134cd42b09.
- OTA raw image retention attempt 9f06eaf032f64b405d85e7d47231a60526851a4b.
Separate runners, artifacts mist-deep-analysis-hyperos3, mist-deep-analysis-hyperos4, mist-dual-comparison. Not runtime tested. Compare paths/properties/config indexes/ELF changes and sky blob list. OTA may omit physical/super metadata. Do not mix incompatible firmware/kernel/modules. Prefer coherent HyperOS 4 baseline after validation.

## Next actions
1. Run Phase 2 from main; inspect all three artifacts and logs, verify payload image retention and identity; record fixes here.
2. Compare actual HALs, VINTF, module ABI, kernel/AVB, partition sizes, and Ravelin/Garnet reference fixups; broader multi-reference comparisons and content hashing still needed.
3. Decide prebuilt mist kernel vs source-supported kernel. Use actual mist DTB/DTBO and modules.
4. Create separate tree generation workflow using Lineage extract-utils, reviewed proprietary list, correct Soong/SELinux/AVB/partition/init configs and upstream licensing. No overwrites without approval.
5. Compile LineageOS 24.0 and debug; test boot and hardware. No compile or boot success claimed yet.
