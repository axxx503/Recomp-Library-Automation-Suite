#!/usr/bin/env python3
"""
relink_phase4.py — Post-Migration Relinking & Verification for:
1. Recomp Launcher (C:\\Recomp Library symlinks + library.json)
2. Emulators (yuzu, eden, PCSX2, Cemu, Dolphin, RPCS3, RetroArch)
3. Steam (shortcuts.vdf for active account <STEAM_ACCOUNT_ID>)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

APPDATA = Path(os.environ["APPDATA"])
DOCS = Path.home() / "Documents"


def find_new_target_for_recomp_link(old_target: str) -> Path | None:
    clean = old_target.lstrip("\\\\?\\")
    low = clean.lower()

    replacements = [
        (r"d:\<LOCAL_ROMS_DIR>\ps2\games", r"Z:\PlayStation 2\games\ps2\games"),
        (r"d:\<LOCAL_ROMS_DIR>\ps2", r"Z:\PlayStation 2\games\ps2"),
        (r"d:\<LOCAL_ROMS_DIR>\ps1\games", r"Z:\PlayStation 1\games\PS1\games"),
        (r"d:\<LOCAL_ROMS_DIR>\ps1", r"Z:\PlayStation 1\games\PS1"),
        (r"d:\<LOCAL_ROMS_DIR>\3ds", r"Z:\Nintendo 3DS\games\3ds"),
        (r"z:\the legend of zelda", r"Z:\<SHARE_NAME>\The Legend of Zelda"),
    ]
    for old_pref, new_pref in replacements:
        if low.startswith(old_pref):
            tail = clean[len(old_pref) :].lstrip("\\/")
            cand = Path(new_pref) / tail if tail else Path(new_pref)
            if cand.exists():
                return cand
            # Also try without extra subfolder duplication
            alt = Path(new_pref).parent / tail if tail else Path(new_pref).parent
            if alt.exists():
                return alt
    return None


def relink_recomp_library() -> tuple[int, int]:
    print("=== 1. RELINKING C:\\Recomp Library ===")
    root = Path(r"C:\Recomp Library")
    fixed = 0
    still_broken = 0

    for p in list(root.rglob("*")):
        if p.is_symlink() and not p.exists():
            old_t = os.readlink(p)
            new_t = find_new_target_for_recomp_link(old_t)
            if new_t and new_t.exists():
                p.unlink()
                os.symlink(str(new_t), str(p), target_is_directory=new_t.is_dir())
                print(f"  [RELINKED] {p} -> {new_t}")
                fixed += 1
            else:
                print(f"  [UNRESOLVED] {p} (was -> {old_t})")
                still_broken += 1

    # Verify total symlinks/junctions
    broken_after = [str(p) for p in root.rglob("*") if p.is_symlink() and not p.exists()]
    print(f"C:\\Recomp Library: relinked={fixed}, remaining_broken={len(broken_after)}")
    return fixed, len(broken_after)


def relink_emulators() -> int:
    print("\n=== 2. RELINKING EMULATORS ===")
    updated = 0

    # A. yuzu & eden keys/load symlinks + qt-config.ini
    for emu in ("yuzu", "eden"):
        emu_dir = APPDATA / emu
        if not emu_dir.exists():
            continue
        # Ensure keys & load point to Z:\Nintendo Switch\{keys,texture}
        for sub, z_sub in [("keys", r"Z:\Nintendo Switch\keys"), ("load", r"Z:\Nintendo Switch\texture")]:
            local_p = emu_dir / sub
            z_p = Path(z_sub)
            if z_p.exists():
                if not local_p.exists() and not local_p.is_symlink():
                    os.symlink(str(z_p), str(local_p), target_is_directory=True)
                    print(f"  [{emu}] Linked {local_p} -> {z_p}")
                    updated += 1
        cfg = emu_dir / "config" / "qt-config.ini"
        if cfg.exists():
            txt = cfg.read_text(encoding="utf-8", errors="ignore")
            new_txt = txt.replace(r"D:/<LOCAL_ROMS_DIR>/switch", r"Z:/Nintendo Switch/games")
            new_txt = new_txt.replace(r"D:\<LOCAL_ROMS_DIR>\switch", r"Z:\Nintendo Switch\games")
            if new_txt != txt:
                cfg.write_text(new_txt, encoding="utf-8")
                print(f"  [{emu}] Updated qt-config.ini game paths -> Z:/Nintendo Switch/games")
                updated += 1

    # B. PCSX2.ini
    pcsx2_ini = DOCS / "PCSX2" / "inis" / "PCSX2.ini"
    if pcsx2_ini.exists():
        txt = pcsx2_ini.read_text(encoding="utf-8", errors="ignore")
        new_txt = txt
        for old_p, new_p in [
            (r"F:\PCSX2\bios", r"Z:\PlayStation 2\keys"),
            (r"D:\Keys & Firmware\PS2", r"Z:\PlayStation 2\keys"),
            (r"D:\<LOCAL_ROMS_DIR>\ps2", r"Z:\PlayStation 2\games"),
        ]:
            new_txt = new_txt.replace(old_p, new_p)
        if new_txt != txt:
            pcsx2_ini.write_text(new_txt, encoding="utf-8")
            print(f"  [PCSX2] Updated {pcsx2_ini}")
            updated += 1

    # C. Cemu settings.xml
    cemu_xml = APPDATA / "Cemu" / "settings.xml"
    if cemu_xml.exists():
        txt = cemu_xml.read_text(encoding="utf-8", errors="ignore")
        new_txt = re.sub(
            r"<GamePaths>.*?</GamePaths>",
            lambda _: "<GamePaths><Entry>Z:\\Nintendo Wii U\\games</Entry></GamePaths>",
            txt,
            flags=re.DOTALL,
        )
        if new_txt != txt:
            cemu_xml.write_text(new_txt, encoding="utf-8")
            print(f"  [Cemu] Updated <GamePaths> -> Z:\\Nintendo Wii U\\games")
            updated += 1

    # D. Dolphin.ini
    dolphin_ini = DOCS / "Dolphin Emulator" / "Config" / "Dolphin.ini"
    if dolphin_ini.exists():
        txt = dolphin_ini.read_text(encoding="utf-8", errors="ignore")
        new_txt = txt.replace(r"D:\<LOCAL_ROMS_DIR>\GameCube", r"Z:\Retro_Arcade\games\GameCube")
        new_txt = new_txt.replace(r"Z:\Emulators_ROMs\Wii", r"Z:\Nintendo Wii\games")
        new_txt = new_txt.replace(r"Z:\Emulators_ROMs\GameCube", r"Z:\Retro_Arcade\games\GameCube")
        if new_txt != txt:
            dolphin_ini.write_text(new_txt, encoding="utf-8")
            print(f"  [Dolphin] Updated {dolphin_ini}")
            updated += 1

    # E. RetroArch
    ra_cfg = APPDATA / "RetroArch" / "retroarch.cfg"
    if ra_cfg.exists():
        txt = ra_cfg.read_text(encoding="utf-8", errors="ignore")
        new_txt = txt.replace(r"D:\<LOCAL_ROMS_DIR>\PS1", r"Z:\PlayStation 1\games")
        if new_txt != txt:
            ra_cfg.write_text(new_txt, encoding="utf-8")
            print(f"  [RetroArch] Updated {ra_cfg}")
            updated += 1

    print(f"Emulators updated: {updated} config/link updates applied.")
    return updated


def verify_steam_shortcuts() -> None:
    print("\n=== 3. STEAM SHORTCUTS AUDIT ===")
    sc_path = Path(r"C:\Program Files (x86)\Steam\userdata\<STEAM_ACCOUNT_ID>\config\shortcuts.vdf")
    if not sc_path.exists():
        print("  [Steam] shortcuts.vdf not found")
        return
    raw = sc_path.read_bytes()
    exes = re.findall(b'\x01Exe\x00([^\x00]+)\x00', raw)
    ok = 0
    broken = []
    for eb in exes:
        s = eb.decode("utf-8", errors="ignore").strip('"')
        if Path(s).exists():
            ok += 1
        else:
            broken.append(s)
    print(f"  Steam shortcuts.vdf: total={len(exes)}, valid={ok}, broken={len(broken)}")
    for b in broken:
        print(f"    [BROKEN] {b}")


if __name__ == "__main__":
    relink_recomp_library()
    relink_emulators()
    verify_steam_shortcuts()
