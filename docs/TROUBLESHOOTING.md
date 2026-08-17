# Troubleshooting

Every entry here was observed on real hardware during the root of my PVG100E. If your
failure is not listed, the pattern to remember is: almost everything that goes wrong is
recoverable from EDL, and EDL is always reachable from the recovery menu.

## edl hangs right after "Loader successfully uploaded"

Cause 1: your loader filename contains the substring `nprg` (the authentic file is called
`Pepito_VDF_NPRG.bin`). edl.py sees that and switches to the legacy streaming protocol,
which this loader does not speak. Rename the file, e.g. `pepito_vdf_fh.bin`.

Cause 2: unpatched edl. This loader sends payload data before the XML response, and stock
edl waits for the response first. Apply `patches/edl-firehose-oldloader-read.patch`.

## TypeError: a bytes-like object is required, not 'str'

You passed `--skipresponse`. It is broken in edl V3.62 (empty response objects come back as
raw bytes and crash the NAK check). Older guides recommend the flag. Do not use it.

## "Device is in Sahara error state, please reboot the device"

The on-device loader is wedged, usually because a previous edl session was killed
mid-transfer or left idle too long (this phone drops idle EDL sessions). No software reset
fixes it. Hold power about 15 s until the phone reboots, then re-enter EDL (recovery menu
path if adb is unavailable).

## Phone enumerates as 05c6:900e instead of 9008

It fell into the bulk/DLOAD trap. Hold power ~11 s to reset. In stubborn cases clamp the
button for 2 to 3 minutes. Then re-enter EDL.

## adb gone after entering EDL

Expected. EDL is a different USB personality. `adb devices` shows nothing while the phone
is in 9008 mode. It comes back on the next normal boot.

## Flashed Magisk boot, now my PIN is rejected

The FDE/verified-boot binding problem, see README Step 7. Short version: nothing is wrong
with your PIN and nothing is lost. Boot to recovery, into EDL, flash the stock boot from
your backup if you need data first, otherwise erase userdata and let it re-encrypt against
the rooted boot. Do not keep retrying the PIN into a cooldown.

## "Please connect to the internet, upgrading to full Magisk required"

The ramdisk ships a stub manager. Skip the download: `adb install Magisk-v30.7.apk`
replaces it with the full app offline.

## su prompt never appears / su hangs

The Magisk manager app is missing (fresh userdata wipe). Install the APK over adb, open it
once, then retry `adb shell su -c id` and watch the phone for the grant dialog.

## Boot takes long after the userdata erase

Normal. First boot formats and re-encrypts userdata, then does app optimization. Give it a
few minutes before deciding anything is wrong.

## mm-qcamera-daemon crash in tombstones

Pre-existing stock quirk on this build, visible before any modification. One SIGABRT at
boot, camera still works. Not caused by root, not dangerous.

## General EDL hygiene

- Use a good cable and a direct port, not a hub.
- Run one continuous edl session per goal; do not let it sit idle between commands.
- If a run dies mid-way, assume the loader is wedged: power-cycle, re-enter EDL, retry.
- Battery drains in EDL even on the charger. Start sessions above 60%.
