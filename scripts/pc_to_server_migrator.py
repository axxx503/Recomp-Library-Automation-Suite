#!/usr/bin/env python3
"""
pc_to_server_migrator.py — Migrate Server-Bound Consoles from Windows PC to Z:\\
with 100% SHA-256 Verification Before Local PC Cleanup.

STRICT BOUNDARY:
- NEVER touches Windows PC games, SteamLibrary, Epic Games, XboxGames, C:\\Recomp Library,
  PlayStation 4 (PS4), PlayStation 5 (PS5), or Nintendo Switch 2 (ns2games).
- Migrates ONLY server-bound consoles (PS3, PS2, PS1, PSP, PS Vita, Switch 1, Wii, Wii U,
  3DS, DS, GBA, Retro_Arcade) into Z:\\<Console>\\{keys,texture,saves,games}\\.
- Verifies full SHA-256 hash match between PC source and Z:\\ destination before deleting PC file.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

CHUNK_SIZE = 1024 * 1024  # 1 MB
SERVER_ROOT = Path(r"Z:\\")
UNC_ROOT = Path(r"\\<SERVER_IP>\<SHARE_NAME>")

FORBIDDEN_PC_KEYWORDS = {
    "ps4",
    "ps5",
    "ps5e",
    "ps5g",
    "ns2games",
    "switch 2",
    "switch2",
    "bloodborn",
    "infamous",
    "steamlibrary",
    "epic games",
    "xboxgames",
    "recomp library",
    "gow3port",
}

HOMEWORK_EXTS = {".docx", ".pdf", ".pptx", ".xlsx", ".bat", ".exe"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while c := f.read(CHUNK_SIZE):
            h.update(c)
    return h.hexdigest()


def resolve_server_root() -> Path:
    if SERVER_ROOT.exists():
        return SERVER_ROOT
    if UNC_ROOT.exists():
        return UNC_ROOT
    raise RuntimeError("Neither Z:\\ nor \\\\<SERVER_IP>\\<SHARE_NAME> is reachable.")


def build_migration_plan(dest_root: Path) -> list[tuple[Path, Path, str]]:
    """Return list of (pc_src_file, server_dest_file, console_role_label)."""
    plan: list[tuple[Path, Path, str]] = []

    def add_tree(src_dir: Path, console: str, role: str, skip_exts: set[str] | None = None):
        if not src_dir.exists():
            return
        for dp, dns, fns in os.walk(src_dir):
            dns[:] = [d for d in dns if d.lower() not in FORBIDDEN_PC_KEYWORDS and not d.startswith(".")]
            for fn in fns:
                if fn.startswith("."):
                    continue
                fp = Path(dp) / fn
                if skip_exts and fp.suffix.lower() in skip_exts:
                    continue
                if any(k in str(fp).lower() for k in ("ps4", "ps5", "ns2games", "switch 2")):
                    continue
                rel = fp.relative_to(src_dir)
                # Preserve game folder name if migrating a game directory
                dst = dest_root / console / role / src_dir.name / rel if role == "games" and src_dir.parent.name.lower() in {"ps3", "<LOCAL_ROMS_DIR>"} else dest_root / console / role / rel
                plan.append((fp, dst, f"{console}/{role}"))

    # 1. D:\Keys & Firmware
    kf = Path(r"D:\Keys & Firmware")
    kf_map = {
        "3DS": "Nintendo 3DS",
        "Dreamcast": "Retro_Arcade",
        "GameCube": "Retro_Arcade",
        "PS Vita": "PS_Vita",
        "PS1": "PlayStation 1",
        "PS2": "PlayStation 2",
        "PS3": "PlayStation 3",
        "Switch": "Nintendo Switch",
        "Xbox": "Retro_Arcade",
    }
    for sub, console in kf_map.items():
        add_tree(kf / sub, console, "keys")

    # 2. D:\<LOCAL_ROMS_DIR> (STRICTLY EXCLUDING ps4!)
    ng = Path(r"D:\<LOCAL_ROMS_DIR>")
    ng_map = {
        "3ds": ("Nintendo 3DS", "games"),
        "Dreamcast": ("Retro_Arcade", "games"),
        "GameCube": ("Retro_Arcade", "games"),
        "PS1": ("PlayStation 1", "games"),
        "ps2": ("PlayStation 2", "games"),
        "psvita": ("PS_Vita", "games"),
        "switch": ("Nintendo Switch", "games"),
        "The Legend of Zelda - Breath of the Wild": ("Nintendo Wii U", "games"),
        "keys_2": ("Nintendo Switch", "keys"),
    }
    for sub, (console, role) in ng_map.items():
        add_tree(ng / sub, console, role)

    # 3. F:\ps3 (only actual PS3 game directories, skip unrelated .docx/.pdf/.pptx/.exe)
    ps3_root = Path(r"F:\ps3")
    if ps3_root.exists():
        for child in ps3_root.iterdir():
            if child.is_dir() and child.name in {
                "Blur",
                "Driver - San Francisco",
                "Metal Gear Solid 4 - Guns of the Patriots (USA) (EnFrDeEsIt) (v02.00)",
                "Midnight Club - Los Angeles - Complete Edition (USA) (EnFrDeEsIt)",
                "Midnight Club Los Angeles",
            }:
                add_tree(child, "PlayStation 3", "games", skip_exts=HOMEWORK_EXTS)

    # 4. F:\PCSX2 & F:\PSX2
    add_tree(Path(r"F:\PCSX2\bios"), "PlayStation 2", "keys")
    add_tree(Path(r"F:\PCSX2\memcards"), "PlayStation 2", "saves")
    add_tree(Path(r"F:\PSX2\saves"), "PlayStation 2", "saves")
    add_tree(Path(r"F:\PSX2\system"), "PlayStation 2", "keys")

    # 5. AppData Switch keys/textures/saves (yuzu & eden) -> Nintendo Switch
    appdata = Path(os.environ.get("APPDATA", ""))
    for emu in ("yuzu", "eden"):
        add_tree(appdata / emu / "keys", "Nintendo Switch", "keys")
        add_tree(appdata / emu / "load", "Nintendo Switch", "texture")
        add_tree(appdata / emu / "nand" / "user" / "save", "Nintendo Switch", "saves")

    return plan


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True)
    g.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    dest_root = resolve_server_root()
    plan = build_migration_plan(dest_root)

    by_bucket = defaultdict(lambda: [0, 0])
    ps4_ps5_sw2_hits = 0
    total_bytes = 0

    for src, dst, label in plan:
        low = str(src).lower()
        if any(k in low for k in ("\\ps4\\", "\\ps5\\", "\\ns2games\\", "switch 2")):
            ps4_ps5_sw2_hits += 1
        sz = src.stat().st_size if src.exists() else 0
        by_bucket[label][0] += 1
        by_bucket[label][1] += sz
        total_bytes += sz

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"=== PC -> Z:\\ Console Migration [{mode}] ===")
    print(f"Destination Root:        {dest_root}")
    print(f"PS4/PS5/Switch 2 files:  {ps4_ps5_sw2_hits} (MUST BE 0)")
    print(f"Total PC files to move:  {len(plan)} ({total_bytes / (1024**3):.2f} GB)")
    for label, (cnt, b) in sorted(by_bucket.items()):
        print(f"  {label:<28} {cnt:>6} files  ({b / (1024**3):.2f} GB)")

    if not args.execute:
        print("\n[DRY-RUN] No PC files copied or deleted. Re-run with --execute after confirmation.")
        return 0

    confirm = input("Type CONFIRM to copy, SHA-256 verify, and delete verified PC originals: ").strip()
    if confirm != "CONFIRM":
        print("Aborted.")
        return 1

    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    log_path = Path(r"C:\Users\<USER>\scripts\pc_migration.log")
    lock = threading.Lock()
    stats = {"migrated": 0, "freed": 0, "errors": 0}

    with log_path.open("a", encoding="utf-8") as lf:
        def process_one(item: tuple[Path, Path, str]):
            src, dst, _ = item
            if not src.exists():
                return
            for attempt in range(4):
                try:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    src_hash = sha256_file(src)
                    src_size = src.stat().st_size
                    if dst.exists() and dst.stat().st_size == src_size and sha256_file(dst) == src_hash:
                        src.unlink()
                        with lock:
                            stats["migrated"] += 1
                            stats["freed"] += src_size
                            lf.write(f"[ALREADY_ON_Z_VERIFIED_DELETED_PC] {src} == {dst} ({src_hash})\n")
                        return
                    tmp_dst = dst.with_name(f".{dst.name}.migrating.tmp")
                    shutil.copy2(src, tmp_dst)
                    if sha256_file(tmp_dst) != src_hash or tmp_dst.stat().st_size != src_size:
                        tmp_dst.unlink(missing_ok=True)
                        with lock:
                            stats["errors"] += 1
                            lf.write(f"[HASH_MISMATCH_ABORTED] {src}\n")
                        return
                    tmp_dst.replace(dst)
                    src.unlink()
                    with lock:
                        stats["migrated"] += 1
                        stats["freed"] += src_size
                        lf.write(f"[MIGRATED_VERIFIED] {src} -> {dst} ({src_hash})\n")
                    return
                except OSError as exc:
                    if attempt < 3:
                        time.sleep(3)
                        continue
                    with lock:
                        stats["errors"] += 1
                        lf.write(f"[ERROR_AFTER_RETRIES] {src} -> {exc}\n")

        # Transfer largest files first for maximum Gigabit throughput
        plan.sort(key=lambda it: it[0].stat().st_size if it[0].exists() else 0, reverse=True)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(process_one, plan))

    print(
        f"[DONE] Migrated & verified {stats['migrated']} files "
        f"({stats['freed'] / (1024**3):.2f} GB freed on PC, errors={stats['errors']}). Log: {log_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
