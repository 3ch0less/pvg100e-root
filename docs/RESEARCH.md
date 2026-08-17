# Research notes

What applies to this exact device (PVG100E, Android 8.1.0 O11019, SPL 2019-12-05, kernel
3.18.71-perf, MSM8937/MSM8940), with sources. Compiled before touching the phone.

## Exploit landscape vs. SPL 2019-12-05

**Dead on this patch level:**

- CVE-2019-2215 (Bad Binder). Patched in the October 2019 ASB. Historic interest: this was
  the original Palm Phone temp-root in 2019.
  Sources: [Oct 2019 ASB](https://source.android.com/security/bulletin/2019-10-01),
  [Project Zero write-up](https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2019/CVE-2019-2215.html),
  [arpruss/cve2019-2215-3.18](https://github.com/arpruss/cve2019-2215-3.18)
- Dirty COW (CVE-2016-5195), QualPwn (CVE-2019-10538/39/40), QuadRooter, PingPong: all
  patched long before this SPL.

**Still unpatched (fixed only after 2019-12):**

- CVE-2020-0041 (binder OOB write, March 2020 ASB). Public exploit exists
  ([bluefrostsecurity](https://github.com/bluefrostsecurity/CVE-2020-0041)); needs per-build
  kernel offsets.
- CVE-2020-0423 (binder UAF, October 2020 ASB). Multiple public PoCs.
- CVE-2019-14040 / CVE-2019-14041 (qseecom UAF/race, Zimperium; MSM8937 explicitly affected;
  fixed Feb/Apr 2020). PoCs: [tamirzb/CVE-2019-14040](https://github.com/tamirzb/CVE-2019-14040).
  SELinux blocks /dev/qseecom from untrusted apps, so these need a chain link.

None were needed: EDL is strictly stronger than any of them.

## EDL and boot-chain research

- MSM8937 requires a signed firehose programmer; Sahara verifies the cert chain against the
  fused Qualcomm root. Cross-OEM signed programmers authenticate fine on this generation
  (no per-device VIP auth like SDM855+).
- Aleph Research, "Exploiting Qualcomm EDL Programmers" (2018), covers MSM8937 including a
  Nokia 6 secure-boot bypass; the full chain there was device-specific and does not apply,
  but the signed-loader mechanics and peek/poke loader concepts do.
  [Part 1](https://alephsecurity.com/2018/01/22/qualcomm-edl-1/)
- Boot chain background: [Quarkslab on Qualcomm secure boot](https://blog.quarkslab.com/analysis-of-qualcomm-secure-boot-chains.html).

## The modding scene for this phone

- **Original root (Dec 2019):** deadman96385's Sugar QCT_SP method. The tool pulled official
  firmware from TCL servers over EDL; root came from swapping in a Magisk-patched boot image
  mid-flow. Dead since ~2021 (server credentials revoked).
  [XDA thread](https://xdaforums.com/t/release-root-the-palm-phone.4021201/)
- **Key fact from that thread, still true:** this phone's aboot does not rigorously verify
  boot.img, which is why a Magisk-patched boot works on a locked bootloader.
- **Loaders:** `Pepito_VDF_NPRG.bin` (PVG100E, "PepitoVDF Attestation Cert") and the US
  `PEPITO.bin`, both in
  [programmer-collection/alcatel](https://github.com/programmer-collection/alcatel).
  bkerler/Loaders also carries exact-hash matches under `TCL/0006b0e1...`.
- **2025 Linux guides by KyleCascade:** the modern no-Sugar flow.
  [edl backup guide](https://xdaforums.com/t/guide-using-edl-to-backup-a-palm-pvg-100-pepito-on-linux.4719549/),
  [qdl flash guide](https://xdaforums.com/t/guide-using-qdl-to-flash-a-palm-pvg-100-pepito-on-linux.4720206/)
  (needs the [xerootg/qdl](https://github.com/xerootg/qdl) pepito branch).
- **2024 no-Sugar root + GSI guide:** [XDA](https://xdaforums.com/t/guide-treble-gsi-root-on-palm-phone-without-sugar_qct.4680864/)
- **The neko.ink Pepito page** (Chinese): variant/firehose map, Sugar protocol crack, EDL
  test-point photos, and the finding that PVG100E's aboot contains OEM unlock commands.
  [neko.ink](https://www.neko.ink/2022/04/12/palm-phone-pepito/)
- **TWRP:** `twrp-3.3.1-0-pepito-nofirmwaremount.img` (snoopy20). Only the nofirmwaremount
  build; the earlier fstab mounted the modem partition as sdcard and cost someone an IMEI.
- **ROMs:** Treble GSIs historically (Lineage 16 to 18.1, ceiling Android 11 on kernel
  3.18); native [LineageOS 23.2](https://github.com/solarkennedy/lineageos-pepito)
  (Android 16, kernel 4.19) since July 2026, EDL packages include PVG100E support.
- **Stock dumps:** a PVG100E Vodafone DE dump (v3BDA-0) circulates on XDA/4pda. My unit is
  v3BCT-0; region builds differ, so the local backup stays authoritative.
- **Palm GPL drop:** [sourceforge palmopensource](https://sourceforge.net/projects/palmopensource/)
  (incomplete kernel/UEFI tree, still useful).

## Hardware entry points

- `adb reboot edl` works unauthenticated on stock.
- Recovery has an "Emergency download mode" entry (one-button navigation: hold power through
  restart cycles, short-press to move, long-press to select).
- 900e trap recovery: hold power ~11 s.
- Hard brick escape: test points under the rear-camera flash (photos on neko.ink).
