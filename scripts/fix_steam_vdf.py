#!/usr/bin/env python3
"""
fix_steam_vdf.py — Restore shortcuts.vdf from shortcuts.vdf.bak_phase4,
safely parse & update only moved Exe/StartDir paths in binary VDF without
touching appid or tags, and verify cloud-storage collection & RecompLauncher library.json.
"""

from __future__ import annotations

import json
import shutil
import struct
from pathlib import Path

STEAM_CFG = Path(r"C:\Program Files (x86)\Steam\userdata\<STEAM_ACCOUNT_ID>\config")
SC_PATH = STEAM_CFG / "shortcuts.vdf"
BAK_PATH = STEAM_CFG / "shortcuts.vdf.bak_phase4"


def parse_vdf(data: bytes, idx: int = 0) -> tuple[dict, int]:
    obj: dict = {}
    while idx < len(data):
        t = data[idx]
        idx += 1
        if t == 0x08:  # end of map
            return obj, idx
        end = data.index(0, idx)
        key = data[idx:end].decode("utf-8", errors="replace")
        idx = end + 1
        if t == 0x00:  # nested map
            val, idx = parse_vdf(data, idx)
            obj[key] = (0x00, val)
        elif t == 0x01:  # string
            end_v = data.index(0, idx)
            val = data[idx:end_v].decode("utf-8", errors="replace")
            idx = end_v + 1
            obj[key] = (0x01, val)
        elif t == 0x02:  # int32/uint32
            (val,) = struct.unpack_from("<i", data, idx)
            idx += 4
            obj[key] = (0x02, val)
        else:
            raise ValueError(f"Unsupported VDF type 0x{t:02x} for key {key}")
    return obj, idx


def serialize_vdf(obj: dict) -> bytes:
    out = bytearray()
    for k, (t, val) in obj.items():
        out.append(t)
        out.extend(k.encode("utf-8") + b"\x00")
        if t == 0x00:
            out.extend(serialize_vdf(val))
        elif t == 0x01:
            out.extend(val.encode("utf-8") + b"\x00")
        elif t == 0x02:
            out.extend(struct.pack("<i", val))
    out.append(0x08)
    return bytes(out)


def map_moved_path(val: str) -> str:
    replacements = [
        (r"D:\<LOCAL_ROMS_DIR>\ps2\\", r"Z:\PlayStation 2\games\ps2\\"),
        (r"D:\<LOCAL_ROMS_DIR>\ps2", r"Z:\PlayStation 2\games\ps2"),
        (r"D:\<LOCAL_ROMS_DIR>\PS1\\", r"Z:\PlayStation 1\games\PS1\\"),
        (r"D:\<LOCAL_ROMS_DIR>\PS1", r"Z:\PlayStation 1\games\PS1"),
        (r"D:\<LOCAL_ROMS_DIR>\3ds\\", r"Z:\Nintendo 3DS\games\3ds\\"),
        (r"D:\<LOCAL_ROMS_DIR>\3ds", r"Z:\Nintendo 3DS\games\3ds"),
    ]
    for old, new in replacements:
        if old in val:
            return val.replace(old, new)
    return val


def main() -> None:
    if not BAK_PATH.exists():
        raise FileNotFoundError(f"Backup not found: {BAK_PATH}")

    # 1. Restore from bak_phase4
    shutil.copy2(BAK_PATH, SC_PATH)
    raw = SC_PATH.read_bytes()
    parsed, _ = parse_vdf(raw)

    # Verify round-trip fidelity before editing
    re_serialized = serialize_vdf(parsed)
    assert re_serialized == raw, f"Round-trip mismatch: {len(re_serialized)} != {len(raw)}"

    shortcuts_map = parsed["shortcuts"][1]
    updated_fields = 0
    tags_count = 0
    recomp_tagged = 0

    for idx_k, (t, entry) in shortcuts_map.items():
        for field in ("Exe", "StartDir"):
            if field in entry and entry[field][0] == 0x01:
                old_v = entry[field][1]
                new_v = map_moved_path(old_v)
                if new_v != old_v:
                    # Only apply if target exists on Z:\
                    check_p = new_v.strip('"')
                    if Path(check_p).exists():
                        entry[field] = (0x01, new_v)
                        updated_fields += 1
                        print(f"  [UPDATED {idx_k}.{field}] {old_v} -> {new_v}")
        if "tags" in entry and entry["tags"][0] == 0x00 and entry["tags"][1]:
            tags_count += 1
            for _, (_, tv) in entry["tags"][1].items():
                if "recomp" in tv.lower():
                    recomp_tagged += 1

    new_bytes = serialize_vdf(parsed)
    SC_PATH.write_bytes(new_bytes)
    print(
        f"Restored & updated shortcuts.vdf: entries={len(shortcuts_map)}, "
        f"updated_fields={updated_fields}, entries_with_tags={tags_count}, "
        f"recomp_tagged={recomp_tagged}, bytes={len(new_bytes)}"
    )

    # 2. Check cloud-storage-namespace-1.json for Recomp Library
    cs_dir = STEAM_CFG / "cloudstorage"
    for fn in ("cloud-storage-namespace-1.json", "cloud-storage-namespace-1.modified.json"):
        p = cs_dir / fn
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="ignore")
            print(f"Cloud storage {fn}: Recomp Library present = {'Recomp Library' in txt}")

    # 3. Check RecompLauncher library.json
    lib_p = Path(r"C:\Users\<USER>\AppData\Roaming\com.recomplauncher.app\library.json")
    if lib_p.exists():
        ltxt = lib_p.read_text(encoding="utf-8", errors="ignore")
        has_stale = any(s in ltxt for s in (r"D:\\<LOCAL_ROMS_DIR>\\", r"D:/<LOCAL_ROMS_DIR>/"))
        print(f"RecompLauncher library.json stale local paths: {has_stale}")


if __name__ == "__main__":
    main()
