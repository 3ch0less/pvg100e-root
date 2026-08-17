#!/usr/bin/env python3
"""Sanity-check a Magisk-patched boot image for the PVG100E before flashing.

Catches truncated/corrupt patch outputs: verifies the ANDROID! magic, checks
the header ramdisk size against the actual gzip stream, and confirms the
Magisk payload is inside the ramdisk.

Usage: check_patched_boot.py magisk_patched.img
"""
import struct
import sys
import zlib


def main(path):
    d = open(path, "rb").read()
    assert d[:8] == b"ANDROID!", "not a boot image"
    page = 2048
    k = struct.unpack("<I", d[8:12])[0]
    r = struct.unpack("<I", d[16:20])[0]
    kpad = (k + page - 1) // page * page
    roff = page + kpad
    if roff >= len(d):
        print("FAIL: file too small for declared kernel (truncated?)")
        sys.exit(1)
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = dec.decompress(d[roff:])
    consumed = len(d[roff:]) - len(dec.unused_data)
    ok_size = r == consumed
    print(f"kernel={k} ramdisk_header={r} ramdisk_stream={consumed} match={ok_size}")
    has_magisk = b"magisk.xz" in out
    print("magisk.xz in ramdisk:", has_magisk)
    if not ok_size:
        print("FAIL: header/content mismatch (do not flash; re-run boot_patch.sh)")
        sys.exit(1)
    if not has_magisk:
        print("FAIL: no Magisk payload in ramdisk")
        sys.exit(1)
    print("PASS: safe to flash")


if __name__ == "__main__":
    main(sys.argv[1])
