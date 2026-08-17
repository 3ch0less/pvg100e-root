# Rooting the Palm Phone PVG100E (Pepito) via EDL

A complete, tested guide to permanently rooting the international Palm Phone (PVG100E,
codename Pepito, Snapdragon 435) using Qualcomm EDL mode and Magisk. No fastboot flashes,
no Sugar QCT, no sketchy one-click tools. Written after doing it on my own unit, including
every failure I hit so you do not have to.

Works on: PVG100E (Vodafone/international, TCL-built). The US PVG100 is similar but uses a
different firehose loader (see [Resources](#resources)). Do not cross-flash full firmware
between variants; the community has bricked units that way.

**Fair warning about what this took:** nothing here went smoothly the first time. edl broke
on this phone's loader in three different ways, one of them an actual protocol bug I had to
read off the USB traffic and patch myself. The phone rejected my own PIN after the first
flash and locked me out (the FDE trap, Step 7). I power-cycled this thing more times than I
can count. This guide is the short version with all of that already dealt with, so you do
not repeat it.

## Table of contents

- [Device facts](#device-facts)
- [What you end up with](#what-you-end-up-with)
- [Warnings, read these first](#warnings-read-these-first)
- [Requirements](#requirements)
- [Step 0: How this works](#step-0-how-this-works)
- [Step 1: Patch the edl tool](#step-1-patch-the-edl-tool)
- [Step 2: Get the loader](#step-2-get-the-loader)
- [Step 3: Enter EDL mode](#step-3-enter-edl-mode)
- [Step 4: Full backup (do not skip)](#step-4-full-backup-do-not-skip)
- [Step 5: Patch boot with Magisk](#step-5-patch-boot-with-magisk)
- [Step 6: Flash the patched boot](#step-6-flash-the-patched-boot)
- [Step 7: The FDE problem and the fix](#step-7-the-fde-problem-and-the-fix)
- [Step 8: Verify root](#step-8-verify-root)
- [Post-root hardening](#post-root-hardening)
- [Troubleshooting](#troubleshooting)
- [Restore and unbrick](#restore-and-unbrick)
- [Extras: diag port, engineering apps, debloat](#extras-diag-port-engineering-apps-debloat)
- [What is next: LineageOS 23.2](#what-is-next-lineageos-232)
- [Resources](#resources)
- [Credits](#credits)

## Device facts

| | |
|---|---|
| Model | Palm PVG100E "Pepito" |
| SoC | Snapdragon 435 (reports as MSM8940, HWID 0x0006b0e100420046) |
| RAM / storage | 3 GB / 32 GB eMMC |
| Stock OS | Android 8.1.0, kernel 3.18.71, last patch 2019-12-05 |
| Bootloader | Locked. A hidden fastboot mode exists in aboot (observed working: reports itself unlockable; never flash-tested, EDL is what this guide uses) |
| Low-level access | Qualcomm EDL (USB 05c6:9008) |
| userdata | FDE encrypted, and this matters a lot, see Step 7 |

## What you end up with

- Permanent Magisk root (survives reboots, verified)
- A full partition-level backup of the entire eMMC, so the phone is unbrickable by software
- Carrier bloat and telemetry removed, OTA updater disabled (it would stomp root)
- The hidden engineering/factory menus and the Qualcomm diag port
- A clean base for the LineageOS 23.2 (Android 16) port, if you want to go further

## Warnings, read these first

- **Backup before any write.** There is no official firmware download for this exact region
  build. Your own EDL dump is the only guaranteed recovery image. Step 4 is mandatory.
- **The stock boot image is FDE-bound.** If you flash a Magisk-patched boot and your phone
  has a lockscreen PIN, the PIN will stop validating and you will be locked out of your data.
  The fix is wiping userdata (it re-encrypts against the new boot). On a daily driver with
  data you care about, back up everything first or remove the lockscreen before you start.
  Full story in [Step 7](#step-7-the-fde-problem-and-the-fix).
- **EDL sessions on this phone are fragile.** The loader dies if left idle, and a killed
  session can leave the phone needing a power-cycle. Follow the timing notes in each step.
- This voids nothing (it is all software and reversible) but it will trip SafetyNet-era
  integrity checks. Banking apps on a 2019-patch phone are a bad idea anyway.

## Requirements

- A Mac or Linux box (this guide uses macOS, everything maps 1:1 to Linux)
- Python 3 with a virtualenv, `libusb` (`brew install libusb`)
- [bkerler's edl tool](https://github.com/bkerler/edl) cloned locally, with its
  [Loaders](https://github.com/bkerler/Loaders) submodule fetched
- The PVG100E firehose loader (Step 2)
- A decent USB cable. Seriously. A flaky cable during EDL is how you meet the recovery menu.
- Phone charged above 60%

## Step 0: How this works

This model is usually described as having no fastboot. Not quite true: there is a hidden
fastboot mode inside aboot (boot menu, details in [docs/EXTRAS.md](docs/EXTRAS.md)). I have
seen it work with my own eyes and it answers the full command vocabulary, but I never
flashed or unlocked through it, so treat it as an observed bonus, not a tested path. The
proven low-level door is EDL: the Snapdragon boot ROM (PBL) always listens on USB for the
Sahara protocol in EDL mode. Sahara accepts one thing: a cryptographically signed
firehose programmer. TCL signed one for this exact device and it leaked years ago. Once the
loader runs, it exposes the whole eMMC for raw read/write over the firehose protocol. That
is the entire trick: signed loader, then read everything, then write one partition.

Three things make this guide different from the old XDA posts:

1. The **Sugar QCT method is dead** (TCL revoked the tool's server credentials around 2021).
2. **edl V3.62 is broken against this specific loader** in three separate ways. I patched
   the tool; the patch is in `patches/`.
3. The **FDE/PIN interaction** (Step 7) is not documented anywhere for this phone and it
   will bite you if you have a lockscreen set.

## Step 1: Patch the edl tool

Clone and set up:

```sh
git clone https://github.com/bkerler/edl && cd edl
git submodule update --init
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
mkdir -p logs   # edl debugmode crashes without this dir
```

Apply the patch from this repo:

```sh
git apply /path/to/pvg100e-root/patches/edl-firehose-oldloader-read.patch
```

What it fixes (all three were verified against the live device):

- **The loader streams payload before the XML response.** This Pepito firehose is an
  old-style programmer: on a `<read>` it pushes raw sectors immediately, then sends the log
  and response. Stock edl waits for the response first and eats your payload, then hangs
  forever. The patch rewrites `cmd_read()` and `cmd_read_buffer()` in
  `edlclient/Library/firehose.py` to do byte-counted raw reads and parse the trailer after.
- **`--skipresponse` is broken in V3.62** (returns empty bytes and dies with a TypeError).
  Do not use that flag, despite older guides recommending it.
- **Filename trap:** `edl.py` checks if the loader filename contains `nprg` and misroutes to
  the legacy streaming protocol if so. The authentic Pepito file is literally called
  `Pepito_VDF_NPRG.bin`. Rename your copy to something without that substring, e.g.
  `pepito_vdf_fh.bin`.

## Step 2: Get the loader

Download the PVG100E programmer from the community collection:

```sh
curl -LO https://raw.githubusercontent.com/programmer-collection/alcatel/master/Pepito_VDF/Pepito_VDF_NPRG.bin
mv Pepito_VDF_NPRG.bin pepito_vdf_fh.bin   # see filename note above
```

Expected: 421,736 bytes, ELF 32-bit ARM. Its certificate chain reads "PepitoVDF Attestation
Cert" (TCLMOBILE). If the link ever dies, bkerler's Loaders repo has the same signer under
`TCL/0006b0e100420046_*` (the PK_HASH matches this exact device).

## Step 3: Enter EDL mode

Easiest way, from a booted phone with USB debugging on:

```sh
adb reboot edl
```

The screen goes black and stays black. That is normal: the phone is parked in the boot ROM
and only answers USB. Short power presses do nothing. Do not hold the power button unless
you want to force it out (about 15 s).

No-adb path (needed after a bad flash, for example): power off, hold power through 3 to 4
restart cycles until the one-button menu appears, short-press to highlight **recovery**,
long-press to select, then choose **Emergency download mode**.

Verify the Mac sees it: `system_profiler SPUSBDataType | grep -i qualcomm` should show a
device, or check for VID `05c6` PID `9008`.

## Step 4: Full backup (do not skip)

One uninterrupted session, straight after entering EDL:

```sh
python edl.py rl backup --memory=eMMC --genxml --loader=pepito_vdf_fh.bin
```

This dumps the GPT, generates a `rawprogram0.xml` restore manifest, and reads all 52
partitions (about 28 GB, 40 to 60 minutes). Do not touch the cable, do not let the Mac
sleep.

Then verify before you trust it:

- every `.bin` file size must match its GPT partition size exactly
- `boot.bin` starts with `ANDROID!`, `system.bin`/`vendor.bin` have the ext4 magic at
  0x438, `aboot.bin`/`sbl1.bin`/`tz.bin` are ELF
- `sha256sum *` the directory and store the list with the backup

My verification script is in `scripts/verify_backup.py`. If anything mismatches, redo the
dump with a better cable. Do not proceed on a suspect backup.

## Step 5: Patch boot with Magisk

On-device patching needs no UI and no internet on the phone:

1. Download the official Magisk APK from
   [github.com/topjohnwu/Magisk/releases](https://github.com/topjohnwu/Magisk/releases).
2. Extract the patching kit from the APK (`unzip` it): you need `assets/boot_patch.sh`,
   `assets/util_functions.sh`, `assets/stub.apk`, and from `lib/arm64-v8a/`:
   `libmagiskboot.so`, `libmagiskinit.so`, `libmagisk.so`, `libinit-ld.so`,
   `libmagiskpolicy.so`, `libbusybox.so`.
3. Push to the phone and patch (phone booted normally):

```sh
adb shell mkdir -p /data/local/tmp/magiskpatch
adb push boot_patch.sh util_functions.sh stub.apk /data/local/tmp/magiskpatch/
adb push libmagiskboot.so  /data/local/tmp/magiskpatch/magiskboot
adb push libmagiskinit.so  /data/local/tmp/magiskpatch/magiskinit
adb push libmagisk.so      /data/local/tmp/magiskpatch/magisk
adb push libinit-ld.so     /data/local/tmp/magiskpatch/init-ld
adb push libmagiskpolicy.so /data/local/tmp/magiskpatch/magiskpolicy
adb push libbusybox.so     /data/local/tmp/magiskpatch/busybox
adb push backup/boot.bin   /data/local/tmp/magiskpatch/boot.bin
adb shell "cd /data/local/tmp/magiskpatch && chmod 755 magiskboot magiskinit magisk init-ld magiskpolicy busybox && KEEPVERITY=true KEEPFORCEENCRYPT=true sh boot_patch.sh boot.bin"
adb pull /data/local/tmp/magiskpatch/new-boot.img magisk_patched.img
```

The `KEEPVERITY=true KEEPFORCEENCRYPT=true` flags matter: they keep the stock dm-verity
flags and encryption hooks in place. The output should be a full 64 MB image.

Sanity-check the result before flashing (this is how I caught a truncated write once):
`magisk_patched.img` must start with `ANDROID!`, its header ramdisk size must match the
actual gzip stream, and the ramdisk must contain `overlay.d/sbin/magisk.xz`. A tiny checker
is in `scripts/check_patched_boot.py`.

## Step 6: Flash the patched boot

```sh
adb reboot edl
sleep 12
python edl.py w boot magisk_patched.img --memory=eMMC --loader=pepito_vdf_fh.bin
python edl.py reset --loader=pepito_vdf_fh.bin   # prints a USB error, but resets fine
```

`w` writes the file at the boot partition's start sector. Writes with this loader work with
stock edl, no patch needed on that path.

## Step 7: The FDE problem and the fix

This is the part nobody wrote down for this phone, so here it is.

The userdata partition uses full-disk encryption, and the key unwrap is bound to the stock
verified-boot state. Consequence: **with any modified boot image, the phone boots fine but
your lockscreen PIN stops working.** Not "wrong PIN" as in you forgot it. The gatekeeper
path refuses to validate because the boot state changed. Keeping the verity flags in the
ramdisk (KEEPVERITY=true) does not save you. Clearing the PIN via `locksettings` just moves
the pre-boot prompt to `default_password`, which also fails. I tested all of these so you
do not have to.

The fix, since the binding must be rebuilt against the rooted boot anyway:

1. Accept that userdata gets wiped. (You have the EDL dump of it anyway.)
2. With the patched boot flashed, enter EDL and erase userdata:

   ```sh
   python edl.py e userdata --memory=eMMC --loader=pepito_vdf_fh.bin
   python edl.py reset --loader=pepito_vdf_fh.bin
   ```

   The erase streams in chunks and takes about 15 minutes for 23 GB. Let it finish.
3. Boot. The phone formats and re-encrypts userdata fresh, bound to the rooted boot image.
   Walk through the setup wizard, skip accounts, and do not set a lockscreen PIN.
4. Re-enable USB debugging (developer options), re-authorize your computer.

If you rely on a lockscreen day-to-day, set it up after rooting and test a reboot before
trusting it. I have not mapped exactly which credential types survive on this build.

## Step 8: Verify root

```sh
adb install Magisk-v30.7.apk   # full manager, replaces the stub, works offline
adb shell su -c id
```

Expected: `uid=0(root) gid=0(root) context=u:r:magisk:s0`. Open the Magisk app once and let
it finish its "additional setup" (it reboots the phone once). After that, root survives
reboots. That is it. You are done with the core guide.

## Post-root hardening

What I did on my unit, all reversible:

- **Kill the OTA updater** so an update can never stomp the patched boot:
  `pm disable-user --user 0 com.tcl.vodafone.fota` (and its `.overlay`)
- **Debloat:** Facebook's background installer trio, partner bookmark/browser/email cruft,
  Google apps you do not use. `pm uninstall --user 0 <pkg>` removes without touching the
  system partition; `pm install-existing <pkg>` brings anything back.
- **Kill the ATFWD daemon.** This phone ships Qualcomm's AT-command forwarder running by
  default (remote AT commands over BT/USB, factory resets, the works; it has real CVEs).
  Stop it forever: `su -c 'setprop persist.radio.atfwd.start false'`.
- **Systemwide tracker blocklist:** StevenBlack hosts file bind-mounted over
  `/system/etc/hosts` via a Magisk service script. Ready-made bits in `scripts/`.
- **Telemetry agents:** disabled `StatsPollManager`, `qti.autoregistration`,
  `dpmserviceapp`, `qapp.secprotect`.

Full command list in [docs/EXTRAS.md](docs/EXTRAS.md).

## Troubleshooting

Everything here happened to me on real hardware. Full table with fixes:
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md). The short version:

- edl hangs after "Loader successfully uploaded" -> loader filename contains `nprg`, or you
  are on an unpatched edl. See Step 1.
- "Device is in Sahara error state, please reboot" -> the loader wedged after a killed
  session. Hold power 15 s, re-enter EDL via recovery.
- Phone stuck at 05c6:900e -> hold power ~11 s.
- Booted but PIN rejected after flashing -> Step 7, you need the userdata wipe.
- Magisk app wants to download the full manager -> install the APK over adb instead.

## Restore and unbrick

You have a full dump, so every state is recoverable. Detailed procedures:
[docs/RESTORE.md](docs/RESTORE.md).

Quick version: enter EDL (recovery menu path works even with a dead system), then either
flash single partitions (`edl w boot backup/boot.bin ...`) or the whole set with
`rawprogram0.xml`. A truly dead unit needs the test points under the rear-camera flash;
see the community links in [Resources](#resources).

## Extras: diag port, engineering apps, debloat

- **Qualcomm diag port** (modem-level introspection with SCAT/qcsuper):
  `adb shell su -c 'setprop sys.usb.config diag,adb'`. Verified: device re-enumerates as
  05c6:901d, interface 0 is DIAG, adb keeps working. Resets at reboot unless you also set
  `persist.sys.usb.config`. The stock DiagProtector activity renders blank on this build,
  use the setprop route.
- **Factory/engineering menus** (present on the stock ROM, launch with `am start`):
  `com.EngineeringMode/.ManuList` (Qualcomm test suite), `com.tcl.engineermode`,
  `com.qualcomm.qti.qmmi` (QMMI hardware tests), `com.tcl.TctRFM`, `com.tcl.ygps`.
- Details and exact commands in [docs/EXTRAS.md](docs/EXTRAS.md).

## What is next: LineageOS 23.2

There is a native, actively maintained LineageOS 23.2 (Android 16, kernel 4.19) port for
this phone: [solarkennedy/lineageos-pepito](https://github.com/solarkennedy/lineageos-pepito).
The release EDL packages include per-variant loaders and XMLs, and PVG100E is supported
since the 20260802 build. With the backup from Step 4 you can try it and roll back in
minutes. That is the real fix for the 2019 patch level, and the only way this hardware gets
current security updates.

## Resources

- Loader (PVG100E): [programmer-collection/alcatel](https://github.com/programmer-collection/alcatel) (`Pepito_VDF/Pepito_VDF_NPRG.bin`)
- edl tool: [bkerler/edl](https://github.com/bkerler/edl), loaders: [bkerler/Loaders](https://github.com/bkerler/Loaders)
- Magisk: [topjohnwu/Magisk](https://github.com/topjohnwu/Magisk)
- qdl fork that works on this phone: [xerootg/qdl](https://github.com/xerootg/qdl) (`pepito` branch)
- LineageOS port: [solarkennedy/lineageos-pepito](https://github.com/solarkennedy/lineageos-pepito)
- The single best Pepito page on the internet (Chinese): [neko.ink Palm Phone notes](https://www.neko.ink/2022/04/12/palm-phone-pepito/)
- XDA: [root release thread](https://xdaforums.com/t/release-root-the-palm-phone.4021201/),
  [edl backup guide](https://xdaforums.com/t/guide-using-edl-to-backup-a-palm-pvg-100-pepito-on-linux.4719549/),
  [qdl flash guide](https://xdaforums.com/t/guide-using-qdl-to-flash-a-palm-pvg-100-pepito-on-linux.4720206/),
  [no-Sugar root guide (2024)](https://xdaforums.com/t/guide-treble-gsi-root-on-palm-phone-without-sugar_qct.4680864/)
- Aleph Research Qualcomm EDL series: [part 1](https://alephsecurity.com/2018/01/22/qualcomm-edl-1/)
- Palm GPL source drop: [sourceforge.net/projects/palmopensource](https://sourceforge.net/projects/palmopensource/)

## Credits

- bkerler for the edl tool and the loader collection
- deadman96385 for the original root release and the programmer collection
- KyleCascade (xkyle) for the 2025 Linux backup/flash guides that proved the flow
- MlgmXyysd for the neko.ink Pepito bible (variant map, test points, unlock findings)
- solarkennedy for keeping this phone alive with LineageOS 23.2
- topjohnwu for Magisk
