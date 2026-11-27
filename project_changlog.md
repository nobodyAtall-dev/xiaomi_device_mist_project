# Mist — LineageOS 24.0

Redmi Note 17 5G / POCO M8 Power 5G (mist)  
Target: LineageOS 24.0 (Android 17)  
Last updated: 27 November 2026

## 1. Project status

| Phase | Description | Status |
| --- | --- | --- |
| 1 | HyperOS 3 firmware extraction | Completed |
| 1B | Deep hardware analysis | Completed; limitations below |
| 2 | Reference research and dual-firmware comparison | Completed; integration review pending |
| 3 | Device, vendor and standalone kernel bring-up | Initial candidates published; build integration pending |
| 4 | ROM compilation and debugging | Local Linux build planned; integration and runtime checks pending |
| 5 | Boot and hardware testing | Pending |

**Current task:** Complete tree integration and validate by compiling LineageOS locally on Linux. GitHub Actions are for firmware research and tree maintenance, not ROM compilation.

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

These values were recorded in previous analysis; verify them against the original artifacts before using them in build configuration. HyperOS 4 values are summarized below.

Phase 1B logged 131 physical partition metadata rows, 33 DT candidates, 5,312 ELF files, 757 module entries, 1,193 hardware configurations, 977 matching Sky blob paths and 495 missing paths. Path matches do not establish binary compatibility.

### Phase 2 findings (verified from artifacts)

| Item | HyperOS 4 |
| --- | --- |
| OTA identity | mist, Android 17, SDK 37; published MD5 matches |
| System security patch | 2026-10-01 |
| Vendor SDK / security patch | 35 (Android 15) / 2026-05-05 |
| Kernel | 6.6.118-android15-8-gc4127a25dcf3-ab15863337-4k |
| Boot / vendor boot headers | v4 / v4; 4096-byte page size |
| Boot / init_boot / vendor_boot / recovery image sizes | 100663296 / 8388608 / 100663296 / 104857600 bytes |
| DTBO image size | 25165824 bytes |
| New OTA image | mi_product.img (348160 bytes; not decoded) |
| Modem | FAT retry succeeded; extracted file list available |

Compared with HyperOS 3: 1603 added and 806 removed stock paths; 483 added and 328 removed ELF paths; 389 shared ELF metadata changes; 53 added and 36 removed config paths. Sky matches decreased from 977 to 973. These are path/metadata comparisons, not binary hashes or ABI guarantees.

HyperOS 4 diagnostics: super metadata absent (expected for individual payload images), init_boot/recovery kernel version/config unavailable, qupfw ELF read error. Module vermagic includes multiple versions, including two distinct GKI build identifiers; verify per-partition ABI before selecting modules. Rescue remains unresolved in HyperOS 3. Prefer the matched HyperOS 4 boot, DTB/DTBO and module set; do not combine with Sky binaries.

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
| Phase 2 | [Workflow](.github/workflows/mist-phase2.yml), [OTA discovery](scripts/discover-mist-ota.py), [comparison](scripts/compare-mist-firmware.py); [Passed run](../../actions/runs/45922255689); [HyperOS 3](../../actions/runs/45922255689/artifacts/15164584468), [HyperOS 4](../../actions/runs/45922255689/artifacts/15164732386), [comparison](../../actions/runs/45922255689/artifacts/15165082696) |
| 27 November 2026 | Simplified this changelog; no workflow or source tree changes |

Phase 2 outputs: `mist-deep-analysis-hyperos3`, `mist-deep-analysis-hyperos4`, `mist-dual-comparison`. Separate runners limit disk usage. Artifacts expire after 30 days.

## 6. Open issues and next steps

- [x] Review Phase 2 results, verify OTA identity/checksum and confirm boot image retention.
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
- Use developer-oriented wording (e.g. 'The project developer confirmed') for developer confirmations. Future sessions: read this file first; update status, findings, fixes, relevant links and next steps after each change or reviewed run. Keep entries concise, factual and chronological.

### Repository and branch decision — 27 November 2026
The project developer confirmed the exact target branch name `lineage-24` for both Mist source trees (not `lineage-24.0`). Both destination repositories are currently empty: device public, vendor private; GitHub reports `main` as their default branch. Initialize directly on `lineage-24` during first authorized publication and verify it is the default branch. Do not create or retain an unnecessary `main` branch. Initial bring-up uses matching Mist HyperOS 4 prebuilt kernel/DTB/DTBO/modules in a separate private repository. Do not place kernel binaries or modules in the device/vendor repositories. If building a source kernel later, evaluate the Ravelin SM4450 kernel, devicetrees and modules repositories before creating Mist-specific forks. Keep project automation here; no extra common tree for a single device.

### Phase 3 — 27 November 2026
- The project developer confirmed that additional repositories must remain separate; do not merge kernel or other independent components into device/vendor trees.
- Ravelin common proprietary list explicitly references Mist OS3.0.306.0.WPUINXM. Its kernel DT repository contains Mist-specific base, overlays, camera, audio, display, fingerprint, charger and 4 GB variant sources. Source build support remains untested.
- New required repository: `android_kernel_xiaomi_mist-prebuilt` (private, empty, branch `lineage-24` on first publication; checkout path `kernel/xiaomi/mist-prebuilt`). Device and vendor retain their separate repositories. No source kernel forks required initially.
- Added [candidate workflow](.github/workflows/mist-phase3.yml) ([commit](../../commit/560b71a3b9fb280800323320058b3a52b2b382c7)) and [generator](scripts/prepare-mist-trees.py) ([commit](../../commit/8ed1d8e6945f31a760d7e0acec8e38671aa59ca3)). [Module load normalization and hashes](../../commit/cba071325a196254dee67acb3354ed33f0f5d017).
- Uses the exact reviewed HyperOS 4 OTA identity and MD5, selects Ravelin-derived blob candidates from Mist, reports Sky/Garnet alternatives and missing ELF dependencies, generates initial device configuration and vendor makefiles through Lineage extract-utils, stages boot kernel/DTB/DTBO/modules separately. System modules selected from matching GKI build directory.
- Workflow is NOT runtime-tested. Only diagnostic reports are uploaded to the public automation repo; generated tree files remain on temporary runner storage. Publication is intentionally disabled until review; source repos unchanged. No compile/boot claim. The draft still needs HAL/VINTF, blob fixups and dependency closure, SELinux/init, prebuilt build flags, AVB, dynamic partition coexistence and ABI validation. Next: review `mist-phase3-review` artifact, resolve blockers and prepare explicit separate publication workflow.

### Official Xiaomi kernel sources — 27 November 2026
The project developer identified MiCode's `mist-w-oss` release. Branch checks across 24 kernel/device/vendor-related repositories in the 80-repository organization found ten matching repositories: Xiaomi_Kernel_OpenSource, kernel_devicetree, kernel_build, vendor_qcom_opensource_wlan, vendor_qcom_opensource_audio-kernel, vendor_qcom_opensource_data-kernel, vendor_qcom_opensource_camera-kernel, vendor_qcom_proprietary_display-devicetree, vendor_opensource_display-drivers, vendor_qcom_proprietary_camera-devicetree (all under https://github.com/MiCode/). Remaining unrelated repositories were not branch-checked. Main Makefile confirms Linux 6.6.118; build.config.msm.mist confirms 4K pages, boot header v4, init_boot and system/vendor DLKM; mist.bzl contains device-specific module definitions. Source build and ABI compatibility are not yet validated. Potential source repositories (deferred pending MIHW investigation): android_kernel_xiaomi_mist, android_kernel_xiaomi_mist-devicetrees, android_kernel_xiaomi_mist-modules; use upstream kernel_build if a source build is pursued. Keep prebuilt repo for fallback; preserve upstream licenses and history, and keep DT and modules separate from Android device/vendor. Phase 3 staging unchanged. Next: map official external module dependencies and compare with Ravelin before implementing a source build.

### Kernel strategy decision — 27 November 2026
The project developer confirmed previous Mist kernel builds encountered MIHW issues. MiCode `drivers/mihw` is a symlink to `../../../vendor/xiaomi/proprietary/mihw`; target sources were not located. `drivers/Kconfig` unconditionally sources `drivers/mihw/Kconfig`, `drivers/Makefile` references CONFIG_MIHW, and mist.bzl lists metis.ko, mi_schedule.ko and migt.ko. Ravelin removes the MIHW Kconfig/Makefile references; Mist boot compatibility remains untested. Third-party slakkystar/mihw only contains mi_sched on its default garnet branch, not a verified complete Mist replacement. Decision: use coherent HyperOS 4 prebuilt kernel/DTB/DTBO/modules for initial LineageOS 24 bring-up; defer source-kernel forks. Device, vendor and prebuilt repositories exist and are empty; prebuilt visibility was subsequently changed to private. No new repository is required now. All three output branches must be lineage-24. No workflow or source tree changes in this review.

- Repository setup: The project developer confirmed the prebuilt repository was made private; GitHub metadata verified this. No further repositories required. Phase 3 candidate generation subsequently passed; integration validation remains pending.

### Phase 3 result — 27 November 2026
- [Successful run](../../actions/runs/45924118844), [review artifact](../../actions/runs/45924118844/artifacts/15166235908). All steps passed; archive contents reviewed.
- Device: 36 files (65,063 bytes); vendor: 988 files (302,374,661 bytes), including 984 selected blob candidates; standalone kernel: 674 files (181,112,432 bytes). No files at or above 100 MiB and no unexpected kernel files in device/vendor.
- Kernel modules: 96 system_dlkm, 269 vendor_dlkm, 297 vendor ramdisk. All load-list entries present. System modules match selected GKI vermagic; vendor/ramdisk show mixed 6.6.118 identifiers and seven vendor modules report 6.6.98. Preserve original stock sets and check module symbol CRCs/dependencies before claiming ABI compatibility.
- Blob review: 1,607 missing reference-path entries across three donors, 1,899 additional reference candidates, 4,714 dependency edges requiring classification (includes standard Android libraries; not 4,714 missing blobs), zero destination conflicts. Vendor makefile generation passed; three SONAME fixups logged.
- Modem FAT extraction still warns about truncated image; not needed for current tree generation, do not flash extracted modem. Remaining integration gaps: HAL/VINTF, dependency closure, blob fixups, SELinux/init, prebuilt flags, AVB and partition coexistence. No compilation or boot validation.
- Next: integration review and explicit gated publication workflow; candidate files were temporary and must be regenerated. No source repositories published or modified.

### Phase 3B — Integration and initial publication
- Added [integration review](scripts/review-mist-integration.py), commit 8144bef8090d02098014f80f8a5e78c270a3c241: groups ELF dependency names, inventories stock VINTF and init services, records module dependencies and hashes, checks required build files.
- Added [Phase 3B workflow](.github/workflows/mist-phase3b.yml), commit d074303e1f9cf7fb0960318fc459293c68883744, and [publication script](scripts/publish-mist-candidates.sh), commit da58a1dfd6c01ee8c2fe8bd37eaec5366e0d5cf7.
- Workflow regenerates candidates from the same pinned firmware. Default publish=false; review artifact mist-phase3b-review contains diagnostics only. Explicit publish=true permits initial candidate pushes after checks, requires GH_PAT with access to all three empty repositories, private vendor and prebuilt repositories, and verifies lineage-24 default branches. No force pushes or replacement of existing branches. Pushes are independent; if interrupted, review destinations before retrying.
- Integration reports are not a full Android build or a symbol CRC/VINTF/SELinux/AVB validation. No publication or runtime test performed yet. Next: run Phase 3B in review mode, evaluate findings, then authorize candidate publication and compile LineageOS 24.

### Phase 3B result — 27 November 2026
- [Successful review run](../../actions/runs/45925399629), [artifact](../../actions/runs/45925399629/artifacts/15166182803) (20 reports). Log summary: 188 unique dependency names requiring review, 116 VINTF XML files with zero parse errors, 320 stock init services, 662 kernel modules. Candidate file counts and sizes unchanged from Phase 3; separation passed.
- Publication correctly skipped (publish=false). XML parsing does not establish VINTF compatibility; dependency providers, SELinux compilation, module symbol CRCs, AVB/partition layout and boot/hardware remain unvalidated. Internal artifact reports not independently reviewed in this update.
- Next: publish initial development candidates using Phase 3B with publish=true, then review actual committed files and resolve integration gaps through build testing. No new repositories required; no source repositories modified by this run.

### Initial tree publication — 27 November 2026
- [Successful publication run](../../actions/runs/45926322741), [review artifact](../../actions/runs/45926322741/artifacts/15167180788). All steps passed with publish=true. Separate repositories verified via GitHub metadata and branch listing; each has only lineage-24, also the default branch.
- Device (public): nobodyAtall-dev/android_device_xiaomi_mist, commit 84bfc7262d9084c2f0a8de70237030a0b9bdffcb.
- Vendor (private): nobodyAtall-dev/android_vendor_xiaomi_mist, commit 1eda755fa7217ad4f146c4a36e8d79cdbb03c1e9.
- Prebuilt kernel (private): nobodyAtall-dev/android_kernel_xiaomi_mist-prebuilt, commit 257be77478c517543fafc30af0cb9bce2139fbbc.
- GH_PAT publication and branch verification succeeded. No main branches remain in source repositories. No additional repositories required. These are initial development candidates, not build- or boot-validated trees. Next: review committed build configuration, integrate actual HALs/SELinux/init, resolve dependency providers, verify prebuilt flags and AVB/partition layout, then run LineageOS 24 build checks. Do not rerun initial publication; subsequent changes should be incremental commits.

### Phase 4 integration — 27 November 2026
- Cross-checked Ravelin common/Sky and Garnet lineage-24.0 BoardConfig/product definitions and LineageOS android_build core/Makefile, board_config.mk and vendor_lineage kernel tasks.
- Device commits `076406a6a40a232f08cc25fd39703b79795468de` (prebuilt force, init_boot pagesize, module blocklists/no-strip, AVB development keys, audio/WLAN/RIL flags) and `039b10684aee861a2da994d2d66bad8f196000d5` (Ravelin-derived platform HAL package candidates, shipping API 35). Package availability, audio and hardware-specific configuration still need validation; API 35 is reference/vendor-derived and actual factory shipping API requires verification.
- Kernel commit `adb7f5ea0f3b408f2baccbb69be56db4f65ea286` renames dtb/dtb.img to dtb/dtb.dtb with identical blob SHA, because Android build concatenates *.dtb. No kernel binaries modified. Vendor unchanged.
- Added [local manifest](manifests/mist.xml) and [Phase 4 build workflow](.github/workflows/mist-phase4.yml), commits fc977fd2312f05d7d407203d61b0da59150b7701 and 3501186acad45c01c002ef24ac6696bafce25016. Uses upstream lineage-24.0, Mist lineage-24; self-hosted Linux default, minimum 400 GiB free and approximately 32 GiB RAM, selectable check/bootimages/bacon. Runtime untested; diagnostics only. Private source checkout uses GH_PAT. Restrict runner to trusted workflow execution.
- Still outstanding: Mist-specific audio configs, fingerprint/camera/sensor details, VINTF manifests, init services, SELinux, ELF provider closure/fixups, stock bootconfig and AVB/partition layout. Do not flash. No additional repositories required. First configuration build is needed; no compile/boot success claimed.

### Build environment correction
The project developer confirmed LineageOS 24 will be synchronized and compiled locally on Linux. GitHub Actions remain for firmware research, extraction and tree maintenance only. The Phase 4 GitHub build workflow is not required and should not be dispatched. The local manifest remains useful. No source-tree changes in this correction.

### Phase 4A stock hardware integration — 27 November 2026
- The project developer started local LineageOS 24.0 source synchronization using manifests/mist.xml. No additional repository is needed; ROM compilation remains local.
- Independently inspected publication artifact 15167180788 and HyperOS 4 deep-analysis files. Stock fingerprint uses AIDL service android.hardware.biometrics.fingerprint-service.odm with Goodix/Jiiov libraries. Its RC declares a virtual interface while its manifest declares default; actual service registration and permissive stock device-node permissions require review before publication. Stock audio uses sku_ravelin, camera provider is 64-bit, display composer3/allocator and sensors multihal are AIDL. Many of 188 dependency names are platform libraries; 39 distinct module dependency names are absent from the collected module names, potentially built-in or naming differences. No ABI claim.
- Device commits: 7e457403c59b8b5d4a9d7eb0181a961a43cee4bc adds Ravelin-compatible extraction namespaces and vendor suffix fixups; 8726c9544cea44e8d916ad0851bdc67ffcc280ca restores product shipping API 36 based on stock ODM first_api_level (vendor platform first_api_level remains 35). No donor firmware signature patches copied.
- Added scripts/extend-mist-hardware.py (f55020c3de3ff82c8d77c3b0a3afe8d8838dcc1b) and .github/workflows/mist-phase4a.yml (3111a39ad4eb1c981c4ff888920fb58f1aa08b00). Review-only stock OTA download with 16 connections, exact checksum/device check, checkout existing published trees, add narrowly scoped fingerprint/audio/sensor stock assets, regenerate vendor candidate via official extract-utils, check added files and repo separation. Reports only; no ROM build or pushes. Runtime untested. Review fingerprint permissions/instance and ELF providers before applying candidate changes. Vendor and kernel repositories unchanged this session. Next: run Phase 4A stock hardware review and assess the artifact; continue local build configuration after source sync.

### Phase 4A hardware result and SELinux integration
- Run 45929022411 passed; artifact 15167514406 inspected. 38 new stock paths (fingerprint service/manifest/RC and libraries, audio configurations, sensor calibration and HAL config), vendor makefiles regenerated. No publication in that run. Modem FAT warning remains nonblocking.
- Public search found no independently verified complete Mist LineageOS SELinux tree; primary Ravelin policy already present. Official LineageOS/android_system_sepolicy lineage-24.0 defines hal_fingerprint_default and executable type. android_hardware_interfaces lineage-24.0 fingerprint AIDL retains V4 and V5. Official android snippets/lineage.xml includes Qualcomm sm8450 and sm8450-6.6 HAL source repos and vendor policy on lineage-24.0-caf-sm8450; no duplicate repositories required.
- Device commit a11ce6c03a1f5910b61eb9b491c8decdd445862e adds stock .odm fingerprint executable label, /dev/xiaomi-fp, fingerprint data and sysfs contexts, property labels and self socket permission. Enforcing policy remains enabled; compilation and duplicate type/context checks are incomplete. Stock fingerprint RC virtual/default discrepancy, permissive DAC modes and dependency closure remain open; no claim of runtime correctness.
- Phase 4A workflow commit fedbcba6c4a1e05d5dbdf8f594a0731403c87773 changes successful extraction to incremental publication of device blob list and vendor generated files; checks private vendor, branch heads and file size, no force push. New publication step untested. Next: run updated Phase 4A to publish stock assets, then compile locally and resolve actual policy and HAL build errors. Vendor/kernel not modified directly in this session.

### Phase 4A publication result
- [Run 45930179997](../../actions/runs/45930179997) passed every step, including publication. Artifact 15168092402. 38 new stock paths extracted; vendor commit 8d73bc8 (40 changed files), device commit 4ef9d6a (proprietary list). Kernel unchanged. No repeat extraction needed.
- Verified published fingerprint RC and VINTF XML. Corrected init interface virtual to default to match the V4 VINTF declaration in vendor commit 073b5fdb43fdb27c654bcaa04eafdca9e55003a3; persistent extraction fixup in device commit 830801efa6c58774175ace11963212f4450b72ec. Actual service registration untested. Stock permissive DAC modes, sensor touch-detect library, full SELinux and dependency closure still require validation. No ROM compile or boot test. Next: sync locally and run build configuration checks; fix actual errors incrementally.

### Additional source integration
- Device commit 5091e944100416d8ad1463cb37cdb34e113464ad adds boot control and OTA postinstall packages, seven audio support copy entries checked against vendor destinations, Ravelin-derived base VINTF manifest and framework matrix, and upstream Qualcomm audio manifest.
- Static comparison of generated vendor Android.bp found 695 named modules, no duplicate names within the file and no exact overlap with the device package list. This is not a full upstream namespace or installed-path collision check.
- Device commit 0962348b27c5127daa8f7de6bc434bfaf8eafe09 adds persistent Bluetooth audio DT_NEEDED fixups for renamed proprietary libraries. Vendor binaries have not yet been regenerated with these fixups. Run existing Phase 4A publication workflow to apply, then sync locally. SELinux, complete dependency closure and VINTF validation remain outstanding. No full build or hardware validation performed.

### Bluetooth fixup publication
- Run 45932750335 completed successfully; artifact 15170060569. Zero new stock paths; fingerprint and four Bluetooth/audio fixups logged. Vendor commit e697312 published (three changed files); device and kernel unchanged. No repeat extraction required for these changes. Full build, policy compilation, ELF symbol and VINTF validation remain untested.

### Init, properties and fingerprint integration
- Device commit 5b0a692beafb334cd9d599a5105f8db756f79b8f adds Mist init, recovery init and Ravelin GKI module loading script, with package definitions. Device commit 5de512fd916befb7d3d2364b17c5a6247be89a6b adds Qualcomm AIDs, selected platform properties and audio flags. Device commit bb07eff7a8eb0a21fe33976a82b142a5f117f406 adds fingerprint persistent calibration/socket policy and lists five additional stock boot/sensor files. Workflow commit e4b46cdf01f8dd57aee16ff49f840d6e33066220 requires these assets before publishing. Their actual presence in the firmware dump has not yet been confirmed; the workflow must verify them. No vendor/kernel changes in this batch. Full policy compilation, dependency closure and VINTF compatibility unverified. No ROM build or boot test.

### Stock dependency correction
- Run 45934257847 failed before publication: vendor/bin/init.kernel.init_boot-memory.sh absent. Downloaded artifact 15169393462 and inspected full extracted-files.txt. Both legacy memory scripts absent; start_subsys.sh, init.kernel.post_boot.sh, sensors.touch.detect.so and five fingerprint-related libraries confirmed present at exact paths. No vendor or kernel change in failed run.
- Device commit ad6e795373f65e7fd9cfdf0770d2a7b2f09c8f71 removes nonexistent memory scripts from list and adds persistent RC fixup removing their service declarations/start commands; lists eight verified missing vendor assets, including fingerprint dependency providers. Workflow commit acd182110439d1dc12a4bcf0aa3017c347576b88 checks all eight before publication. New run required; full dependency closure and compilation remain unverified.

### Boot and fingerprint dependency publication
- Run 45935171332 passed extraction and publication, artifact 15170676119. Vendor commit a715273 contains eight new stock assets, regenerated build files and corrected kernel RC; 11 changed files. Device and kernel unchanged. No repeat extraction needed for these eight. Full upstream policy compilation, VINTF and ELF closure remain unverified.

### First local Soong validation
- The project developer confirmed source sync complete and lunch lineage_mist cp2a userdebug successful (Android 17, CP2A.260605.016). m nothing completed 295/296 bootstrap steps then failed on libmifpext_fod mixing sensors AIDL V2 and V3 via android.frameworks.sensorservice-V1-ndk. RAM warning was not the reported failure.
- Vendor commit 20bf85ad9e73ebe16383070d813c8985c4df147b patches actual ELF64 little-endian DT_NEEDED string from android.hardware.sensors-V2-ndk.so to same-length V3, and updates matching Android.bp dependency atomically. Device commit 323860b2fd9f2757847eb0081ff8a1ca38d8727e persists replace_needed fixup. No extraction rerun required. Sync device/vendor and rerun m nothing. ABI/symbol compatibility and runtime remain untested; no claim of full build success.

### Batch AIDL conflict corrections
- The project developer's second local m nothing log confirms fingerprint sensors conflict no longer reported. Three new conflicts: WFD audio common V2/V3, Qualcomm display config V5/V12 through libqti-perfd, graphics common V5/V7 through libqcodec2_core.
- Vendor commit 034a68761a825c30090e36d7285d0253a890fad2 directly patches actual ELF DT_NEEDED and Android.bp for WFD audio and codec graphics. Scanned entire generated Android.bp for the three old interfaces; identified eleven additional display V5 consumers. Device commit cf87f039adb88ec72fb1715bc835573fcddd7700 persists all thirteen fixups. Display V5 to V12 requires longer SONAME and patchelf via existing Phase 4A workflow; not yet published. Run one new extraction workflow, then sync and validate locally. No dependency checks disabled; ABI and runtime unverified.

### Android 17 init_boot generation
- The project developer's latest local validation log no longer reports the earlier AIDL conflicts; Soong now fails on lineage_mist_generated_init_boot_image: header_version must be set. Source verification against LineageOS/android_build_soong lineage-24.0 fsgen/boot_imgs.go and android_build core/soong_config.mk confirms BOARD_INIT_BOOT_HEADER_VERSION is independently exported and consumed. Stock init_boot header is v4. Device commit 4496f40c8679a3820c4e885742ed85f769c6c2a5 sets BOARD_INIT_BOOT_HEADER_VERSION := 4. Sync device and rerun local validation; no extraction needed. Memory stalls also logged but not the explicit failure. Full build and boot remain unverified.

### Vendor image packaging conflict
- The project developer's local validation after init_boot header correction progressed to vendor image packaging. Soong reported duplicate lib64/libar-pal.so from Qualcomm source PAL and the Mist proprietary prebuilt. Vendor commit c006ede69a7ef040fc9095fcc553134eeb892d49 removes the redundant prebuilt binary, Android.bp module and package entry. Device commit 6931e30b2558975f597f2d0f3a985224e5a913ce removes its extraction entry so future extraction preserves the correction. Source PAL remains the provider. No firmware re-extraction required. Audio ABI/runtime and full packaging still require local validation. Memory stalls observed during Soong; no OOM reported.

### Qualcomm platform namespace selection
- The project developer's latest local m nothing log confirms Soong succeeded (19m39s); Kati then reports missing manifest_audiocorehal_default.xml and audioeffectservice_qti.xml. PRODUCT_SOONG_NAMESPACES incorrectly selects sm8450 and legacy sound trigger despite stock kernel 6.6. Verified upstream LineageOS android_hardware_qcom-caf_common qcom_defs.mk and BoardConfigQcom.mk select sm8450-6.6 for parrot when TARGET_KERNEL_VERSION is 6.6; verified both exact manifest modules in audio-ar lineage-24.0-caf-sm8450-6.6 hal/default and hal/effects Android.bp. Device commit 09b10e7441e85ce5aa384c82b4c1a397ab2988e8 adds TARGET_KERNEL_VERSION := 6.6. This aligns namespace selection instead of duplicating manifests or bypassing required checks. Vendor unchanged. Retest full configuration; switching namespace can expose additional packaging/ABI conflicts. SELinux/VINTF not yet reached.

### Recovery-first validation
- The project developer chose to test recovery before full ROM compilation. Latest local log confirms m nothing passed on correct sm8450-6.6 namespace; recovery build initiated, VINTF completion not confirmed.
- Compared official LineageOS garnet and xiaomi-ravelin sm4450-common lineage-24.0 recovery RC and BoardConfig. Both use panel0-backlight brightness 200, a600000.dwc3 UDC, a600000.ssusb fallback peripheral mode, RGBX_8888, dedicated 100 MiB kernel-less recovery. Mist already matches Ravelin RC including firmware fallback. Garnet additionally mounts modem firmware and starts ADSP for PMIC; Ravelin sets recovery UI margin 104. Neither additional setting is proven necessary on Mist. No device changes during active recovery build. Verify actual stock recovery hardware nodes, module loading and generated image before flashing; do not assume fastboot boot works for kernel-less recovery.

### First recovery image built and inspected
- The project developer confirmed local recovery compilation successful after installing missing host rsync. Final incremental build 1m52s; recovery.img 104857600 bytes, SHA256 8d9e9e6574700e27db8162149c87f2247eaeb18be2bdebd2359e7fdb5bd2e8bf. Inspection: header v4, kernel size 0, ramdisk 17837296 bytes, Android 17 November 2026 patch, AVB SHA256_RSA4096 test key, recovery hash descriptor; recovery.fstab and init.mist.recovery.rc included. Fastboot reports mist, unlocked yes, slot b, recovery_a and recovery_b each 0x6400000; has-slot query unsupported. First boot remains untested. Confirm installed firmware matches stock kernel/vendor_boot and obtain matching stock recovery backup before flashing only active recovery_b. Do not alter vbmeta, boot, vendor_boot or slot merely for initial test. AVB chain acceptance not verified.

### First successful recovery boot — 2026-11-27
- The project developer confirmed LineageOS 24.0 recovery boots on physical Mist hardware. Display, brightness, volume/power buttons, ADB, fastbootd and partition detection all passed. Touchscreen response and battery percentage remain unconfirmed, not classified as failures.
- First recovery boot validates the recovery image and existing stock boot chain on the tested device. Full Android boot, generated boot/vendor_boot images, normal-mode HALs, encryption and VINTF remain unverified. Preserve the known-good recovery configuration; proceed to local full ROM compilation and collect recovery diagnostics for touch and battery if needed.

### Recovery hardware diagnostics
- Recovery runtime log confirms no touchscreen input device and no battery power supply node. Health HAL starts, qti_pmic_glink and qti_battery_charger modules load, ADSP remoteproc enumerates but no successful firmware boot logged. Device commit a21e486723d9d88856df87b3da91afb218d2f9af adopts verified Garnet recovery modem firmware mount (read-only) and ADSP startup trigger. Battery correction requires physical retest. Touch drivers focaltech_fts, goodix_ts, nt36xxx-i2c and xiaomi_tp exist in vendor_dlkm, not vendor ramdisk recovery list; no touchscreen driver initialization in log. Need identify actual panel driver, dependencies and firmware before adding to recovery; no blind module loading. Full ROM build remains possible; recovery touch/battery not verified.

### Recovery-only priority and touchscreen diagnosis refinement
- The project developer confirmed full ROM compilation is deferred until recovery hardware is fixed. Latest hardware diagnostic lists all five touch controller modules plus xiaomi_tp, lct_tp and qts loaded; this contradicts the earlier missing-module hypothesis for the environment sampled. SPI/I2C devices enumerate, but compatible strings, binding status and current boot mode were not collected. KernelSU module is also present, so verify the sampled environment is the intended recovery rather than normal Android. No touch module changes made. Test existing ADSP recovery fix first and collect boot mode, bus aliases/driver bindings, current input devices and filtered kernel diagnostics in one run.

### Recovery touchscreen module integration
- The project developer confirmed stock HyperOS remains bootable; latest broad module snapshot may be from HyperOS. Original Lineage recovery runtime log has no touch driver names and no touch input. Verified Garnet lineage-24.0 includes touch drivers in recovery first+second stage modules; Ravelin common list lacks touch-specific drivers. Verified all eight Mist touch module files and ELF modinfo dependencies; qts depends on panel notifier/Gunyah/pinctrl, xiaomi_tp on miev, SPI FocalTech on charger/lct_tp/xiaomi_tp/panel notifier/hardware_info, Goodix SPI on lct_tp/panel notifier/xiaomi_tp, legacy Goodix/FocalTech on qts, Novatek on panel notifier. All named external dependencies present in stock recovery load list. Upstream android_build core/Makefile supports BOARD_RECOVERY_KERNEL_MODULES in recovery root. Device commit 5fe3ec9a8fa8925511c14f192dc8648e52cea6cc packages stock recovery module set plus eight stock touch modules in recovery itself, preserving stock order and appending dependencies first. This avoids modifying installed vendor_boot for initial recovery test; image layout, module loading, ABI/firmware and actual touch remain to validate. No full ROM build. Repo PATH failure is local shell issue.

### Recovery V2 compilation successful
- Local recovery-only rebuild after device commit 5fe3ec9 succeeded in 2m02s; Ninja completed 356 actions. Image size 100 MiB, SHA256 18c0016dfcbac3db1c16b7f5dd96ae89bf8ee29b29f44cc7e432cd7964c52100. All eight touchscreen/support modules copied to recovery/root/lib/modules; modules.load.recovery, modules.dep, modules.alias and modules.softdep generated; updated ADSP recovery init installed. Nonfatal depmod warnings for absent modules.order, modules.builtin and modules.builtin.modinfo. Verify recovery module load list and physical V2 boot, touch and battery; retain V1 and matching stock recovery backups. No boot/vendor_boot or vbmeta flashing; full ROM remains deferred.

### Recovery V2 physical runtime validation
- V2 boot log confirms all eight touch modules loaded, FocalTech SPI probe succeeds on spi0.0, chip ID 0x5572, reported FT3610 Sanxing FW 0x33; fts_ts direct input registers 10 slots and actual DOWN/UP events recorded. Firmware update request focaltech_ts_fw_sanxing4.bin fails ENOENT, but installed controller firmware operates. UI navigation remains to be confirmed. ADSP remains offline and no battery power supply nodes exist despite firmware mount property dev.mnt.blk.firmware=sde36 and init trigger executing. Need verify firmware path/content and stock ADSP start semantics before changing again. KernelSU present in actual recovery log as well, so its presence alone does not identify HyperOS. Full ROM deferred.

### Recovery V3 ADSP loader correction
- Recovery battery diagnostic confirms modem_b mounted read-only at /firmware, adsp.mdt and segments present under /firmware/image, firmware_class path empty, ADSP offline, /sys/kernel/boot_adsp absent. Verified stock adsp_loader_dlkm ELF contains boot_adsp sysfs creation and adsp_boot_store. Verified dependency chain: adsp_loader -> spf_core -> gpr -> q6_notifier and snd_event -> q6_pdr -> existing pdr_interface; q6_notifier also depends on existing rproc_qcom_common. All six added stock modules have matching vendor module vermagic. Garnet second-stage recovery list contains same ADSP chain (except snd_event provided via dependencies). Device commit 24cd36be07b69f3938d3c1be40fdae7cb56bda4d packages six modules in recovery only and sets firmware_class path /firmware/image after firmware mount, waits for boot interface then starts ADSP. Physical boot and battery detection not yet verified; keep V2 backup. Full ROM remains deferred.

### Additional recovery runtime defects
- The project developer confirmed approximately four seconds of black screen during recovery entry, then normal display, and Power off in recovery reboots into HyperOS instead of remaining off. V2 log shows display panel bound at ~0.973s kernel uptime and recovery brightness set to 2047 (50%) at ~2.011s; no shutdown event captured. Need capture shutdown path and persistent kernel logs, retest with V3 ADSP/battery initialization before altering power-off or display configuration. Full ROM deferred.

### Recovery power-off trace
- Shutdown trace at 21.927s confirms recovery clears BCB and requests sys.powerctl=shutdown,userrequested,recovery; init enters shutdown mode, hands off to kernel, storage caches synchronize, FocalTech shutdown completes at 21.962s. ADB trace terminates before final kernel power-off, so actual reset/poweroff reason remains unknown. Battery devices still absent in this trace. Retest V3 with USB disconnected to distinguish charger-triggered restart from hardware shutdown defect, and collect previous-boot pstore and boot reason if HyperOS restarts. No speculative shutdown changes. Full ROM deferred.

### Recovery V3 runtime success — 2026-11-27
- Recovery V3 runtime confirms all six ADSP modules loaded, boot interface present, ADSP remoteproc running at 2.283s, battery charger probe at 2.473s, healthd reports battery 95%, 4341 mV, 34 C at 2.567s, USB and wireless power supplies registered. FocalTech SPI touchscreen remains registered; missing optional requested firmware focaltech_ts_fw_sanxing4.bin (-2) persists. The project developer marked all nine recovery V3 checklist tests passed including touch UI, battery display, ADB, fastbootd, power off with and without USB and startup black screen resolved. These physical observations are distinct from runtime log evidence; final shutdown trace not captured in V3. Preserve V3 as known-good recovery, no additional tree changes. V3 build log not supplied. Full ROM remains deferred until project developer authorizes proceeding.

### Recovery V4 touchscreen firmware research and extraction
- The project developer confirmed V3 power off and all functions work. Runtime lines 2954–2964 show FocalTech automatic upgrade work selects old CG glass 4, requests focaltech_ts_fw_sanxing4.bin at 1.234874s, fails ENOENT, re-enables IRQ. Stock extracted inventories from Android 16 and Android 17 confirm five vendor/firmware/focaltech_ts_fw_sanxing{,1,2,3,4}.bin files each 122624 bytes. No exact public download verified; current vendor tree lacks them. Phase4A now selects all five, verifies extracted bytes against pinned stock OTA and records SHA256, then publishes vendor before device recovery copy rules to recovery/root/lib/firmware (early kernel direct lookup). Firmware request is an automatic controller upgrade routine; do not substitute donor files or force upgrades. V3 remains known-good; V4 runtime and firmware version/compatibility must be checked before declaring complete. Full ROM deferred.

### Recovery V4 stock touch firmware publication
- Phase4A run 45958048743 / job 140369029003 completed successfully; five stock binaries extracted, size and byte-equality checks passed, SHA256 report uploaded in artifact 15179583411. Vendor 9c299837756d867dd3dc0e4a77cfff488c43b10c; device 3bf538b6e205f911b4684ebbed8cbc131dfa3751. Verified branch tree contains 5 firmware binaries and device.mk recovery copy rules and proprietary-files entries. Nonfatal modem.img filesystem extraction error unrelated to vendor touch firmware; modem is already mounted from device in V3. Next: local incremental recovery build, inspect packaged firmware and test automatic firmware behavior; preserve V3. Full ROM deferred.

### Recovery V4 build successful
- Local recovery-only build completed in 20m12s (Soong 18m05.66s; final Ninja 52.18s, 28 steps). All five FocalTech stock firmware files copied to recovery/root/lib/firmware; identical SHA256 49f5812612b80c4c0d613cb2555ede1106b24cc6fbc3f3ecf04c22879f365149. Recovery image 100 MiB, SHA256 7b91b35d7325abb8f028e77afb8b3083685c58d4eb36480099885c718740c73f. Nonfatal memory stalls, identical duplicate BoardPlatform/ProductModel keys and prebuilt kernel warning. V4 runtime not yet verified. Preserve V3 and avoid interrupting any automatic touchscreen firmware operation; verify touch, battery and shutdown afterward. Full ROM deferred.

### Recovery V4 runtime validated — 2026-11-27
- The project developer marked all eight V4 physical tests passed: recovery boot, touchscreen navigation, battery percentage, display/brightness, ADB, fastbootd, power off and no startup black-screen delay. Runtime confirms all five 122624-byte firmware files at /lib/firmware with SHA256 49f5812612b80c4c0d613cb2555ede1106b24cc6fbc3f3ecf04c22879f365149. At 1.283694s sanxing4 firmware request succeeded, length 122624, controller and host versions 0x33 match, upgrade flag 0, no controller rewrite required. FocalTech FT3610 input and actual touch down/up events present. ADSP running and healthd reports 94%, 32 C, 4339 mV initially after registration at 2.478s; USB plug/unplug events observed. Transient early no-battery messages clear after ADSP startup; optional health metadata absent, dummy AVDD regulator and missing virtualkeys warning remain nonblocking for tested functions. No further recovery patches required for tested scope. Preserve V4 known-good image (SHA256 7b91b35d7325abb8f028e77afb8b3083685c58d4eb36480099885c718740c73f). Other physical panel variants and actual OTA installation not validated. Full ROM deferred pending developer authorization.

### Recovery V4 residual warning investigation
- The project developer requested correction of remaining warnings where appropriate. V4 shows AVDD dummy regulator but explicit AVDD/IOVDD GPIO power sequence; virtualkeys sysfs absent; nine optional health metadata paths absent; health HAL retries from 2.050s until successful initialization at 2.457s after ADSP starts at 2.210s. ADSP segment direct lookup also falls back successfully to ueventd. Compare stock HyperOS sysfs and boot logs before modifying stock DTB, Health HAL or service ordering. No fake regulator, virtual key definitions or fabricated battery data. No tree changes in this step; V4 remains known-good.
