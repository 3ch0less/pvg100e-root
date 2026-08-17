#!/usr/bin/env python3
"""Verify an edl 'rl --genxml' backup of a Palm PVG100E (Pepito).

Checks every dumped partition file against the GPT in gpt_main0.bin and
spot-checks file signatures. Run this before trusting a backup.

Usage: verify_backup.py /path/to/backup_dir
"""
import os
import struct
import sys

SECTOR = 512


def main(d):
    gpt = open(os.path.join(d, "gpt_main0.bin"), "rb").read()
    hdr = SECTOR  # LBA0 is the protective MBR, GPT header sits at LBA1
    assert gpt[hdr:hdr + 8] == b"EFI PART", "GPT header magic missing, bad dump?"
    part_lba = struct.unpack("<Q", gpt[hdr + 0x48:hdr + 0x50])[0]
    nument = struct.unpack("<I", gpt[hdr + 0x50:hdr + 0x54])[0]
    entsz = struct.unpack("<I", gpt[hdr + 0x54:hdr + 0x58])[0]

    entries = {}
    base = part_lba * SECTOR
    for i in range(nument):
        off = base + i * entsz
        if off + entsz > len(gpt):
            break
        first, last = struct.unpack("<QQ", gpt[off + 0x20:off + 0x30])
        if first == 0:
            continue
        name = gpt[off + 0x38:off + 0x80].decode("utf-16-le").rstrip("\x00")
        entries[name] = (last - first + 1) * SECTOR

    print(f"GPT OK: {len(entries)} partitions")
    fails = 0
    for name, exp in sorted(entries.items()):
        fn = os.path.join(d, name + ".bin")
        if not os.path.exists(fn):
            print(f"MISSING: {name}.bin (expect {exp} B)")
            fails += 1
            continue
        act = os.path.getsize(fn)
        if act != exp:
            print(f"SIZE MISMATCH: {name}.bin expect {exp}, got {act}")
            fails += 1
    print("SIZE CHECK:", "ALL PASS" if fails == 0 else f"{fails} FAILURES")

    def sig(fn, off, n):
        with open(os.path.join(d, fn), "rb") as f:
            f.seek(off)
            return f.read(n)

    checks = [
        ("boot.bin", 0, b"ANDROID!"), ("recovery.bin", 0, b"ANDROID!"),
        ("system.bin", 0x438, b"\x53\xef"), ("vendor.bin", 0x438, b"\x53\xef"),
        ("persist.bin", 0x438, b"\x53\xef"), ("aboot.bin", 0, b"\x7fELF"),
        ("sbl1.bin", 0, b"\x7fELF"), ("tz.bin", 0, b"\x7fELF"), ("rpm.bin", 0, b"\x7fELF"),
    ]
    for fn, off, magic in checks:
        ok = sig(fn, off, len(magic)) == magic
        print(f"SIG {fn}: {'OK' if ok else 'BAD!'}")
        if not ok:
            fails += 1

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
