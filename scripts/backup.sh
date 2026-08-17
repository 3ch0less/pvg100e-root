#!/bin/sh
# Full PVG100E backup via edl. Run right after `adb reboot edl`, in one session.
# Requires: patched edl (see ../patches/), loader renamed to not contain "nprg".
set -e
LOADER=${LOADER:-pepito_vdf_fh.bin}
OUT=${1:-backup-$(date +%Y%m%d-%H%M%S)}
EDL=${EDL:-./edl.py}

echo "Entering EDL..."
adb reboot edl || true
sleep 12
echo "Dumping all partitions to $OUT (about 40-60 min, do not touch the cable)..."
python3 "$EDL" rl "$OUT" --memory=eMMC --genxml --loader="$LOADER"
echo "Verifying..."
python3 "$(dirname "$0")/verify_backup.py" "$OUT"
echo "Checksumming..."
(cd "$OUT" && shasum -a 256 *.bin rawprogram0.xml > SHA256SUMS.txt)
echo "Done. Backup at $OUT"
