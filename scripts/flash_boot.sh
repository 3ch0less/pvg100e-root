#!/bin/sh
# Flash a (verified) patched boot image to the PVG100E via edl.
# Usage: flash_boot.sh magisk_patched.img
set -e
LOADER=${LOADER:-pepito_vdf_fh.bin}
EDL=${EDL:-./edl.py}
IMG=$1
[ -f "$IMG" ] || { echo "no such image: $IMG"; exit 1; }

python3 "$(dirname "$0")/check_patched_boot.py" "$IMG"
echo "Entering EDL..."
adb reboot edl || true
sleep 12
python3 "$EDL" w boot "$IMG" --memory=eMMC --loader="$LOADER"
python3 "$EDL" reset --loader="$LOADER" 2>&1 | tail -2 || true
echo "Flashed and reset. If the phone had a lockscreen PIN, see README Step 7 (FDE)."
