#!/usr/bin/env python3
"""
server_organizer.py — Full Server Reorganization & Standardized Console Layout (ZERO DELETION).

Enforces:
1. STRICT ZERO DELETION on /media/storage.
2. Standardized 4-folder console layout at /media/storage/<Console>/{keys,texture,saves,games}/
   for PlayStation 3, PlayStation 2, PlayStation 1, PSP, PS_Vita,
   Nintendo Switch, Nintendo Wii, Nintendo Wii U, Nintendo 3DS, Nintendo DS, GBA, Retro_Arcade.
   (Never moves PS4, PS5, or Switch 2 into server console folders; never disassembles atomic game dirs).
3. Consolidates NVIDIA GeForce captures into /media/storage/NVIDIA_GeForce/<Game>/
   and duplicates into /media/storage/NVIDIA_GeForce/Duplicate_Videos/<Game>/.
4. Moves non-NVIDIA, non-console duplicates >= 5 MB into /media/storage/Duplicates_Archive/<Category>/
   with adjacent .root_source.txt files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

COOLDOWN_SECONDS = 15 * 60
PARTIAL_CHUNK_SIZE = 64 * 1024
FULL_HASH_CHUNK_SIZE = 1024 * 1024

CONSOLES = [
    "PlayStation 3",
    "PlayStation 2",
    "PlayStation 1",
    "PSP",
    "PS_Vita",
    "Nintendo Switch",
    "Nintendo Wii",
    "Nintendo Wii U",
    "Nintendo 3DS",
    "Nintendo DS",
    "GBA",
    "Retro_Arcade",
]

CONSOLE_SUBFOLDERS = ("keys", "texture", "saves", "games")

EXCLUDED_TOP_DIRS = {
    "SteamLibrary",
    "PS4",
    "PS5",
    "System Volume Information",
    "$RECYCLE.BIN",
    "msdownld.tmp",
    "lost+found",
    "Recomp_Built_Games",
    "Games_Saves_Backup",
}

EXCLUDED_NAMES = {
    "docker",
    "overlay2",
    "containers",
    "volumes",
    "casaos",
    "@eaDir",
    "#recycle",
    ".Trash",
    ".Trash-1000",
    "__pycache__",
}

NVIDIA_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".png", ".jpg", ".jpeg", ".webp", ".jxr", ".hdr"}
NVIDIA_KW = {"nvidia", "geforce", "shadowplay", "nvidia_geforce"}
SHADOWPLAY_RE = re.compile(
    r"^(.+?)[\s_]+\d{4}\.\d{2}\.\d{2}\s*-\s*\d{2}\.\d{2}\.\d{2}(?:\.\d+)?(?:\.DVR)?$",
    re.IGNORECASE,
)

DUP_SUBDIRS = [
    "Videos",
    "Photos_and_Images",
    "Games_and_ROMs",
    "Documents_and_Books",
    "Unknown_Unrecognized",
]

EXT_MAP = {
    "Videos": {".mkv", ".mp4", ".avi", ".mov", ".srt", ".ass"},
    "Photos_and_Images": {".jpg", ".jpeg", ".png", ".webp", ".heic", ".raw", ".cr2"},
    "Games_and_ROMs": {".pkg", ".iso", ".nsp", ".xci", ".bin", ".cue", ".chd", ".rom", ".vpk", ".wbfs", ".rvz", ".3ds", ".cia", ".nds", ".gba"},
    "Documents_and_Books": {".pdf", ".epub", ".docx", ".xlsx", ".pptx", ".txt", ".md"},
}


def detect_console_from_path(p: Path) -> str | None:
    s = str(p).lower()
    parts = [x.lower() for x in p.parts]
    # Never classify PS4 / PS5 / Switch 2 as server-bound console
    if any(k in parts for k in ("ps4", "ps5", "ps5g", "ns2games", "switch 2", "switch2")):
        return None
    if any(k in s for k in ("ps3", "playstation 3", "ps3_game", "ps3_discs")):
        return "PlayStation 3"
    if any(k in s for k in ("ps2", "playstation 2", "pcsx2", "psx2")):
        return "PlayStation 2"
    if any(k in s for k in ("ps1", "playstation 1", "psx")):
        return "PlayStation 1"
    if any(k in parts for k in ("psp",)):
        return "PSP"
    if any(k in s for k in ("psvita", "ps vita", "ps_vita")):
        return "PS_Vita"
    if any(k in s for k in ("wii u", "wiiu", "cemu", "botw wii u")):
        return "Nintendo Wii U"
    if any(k in parts for k in ("wii", "nintendo wii")):
        return "Nintendo Wii"
    if any(k in parts for k in ("3ds", "nintendo 3ds")) or p.suffix.lower() in {".3ds", ".cia"}:
        return "Nintendo 3DS"
    if any(k in parts for k in ("ds", "nds", "nintendo ds")) or p.suffix.lower() == ".nds":
        return "Nintendo DS"
    if any(k in parts for k in ("gba",)) or p.suffix.lower() == ".gba":
        return "GBA"
    if any(k in parts for k in ("switch", "nintendo switch")) or p.suffix.lower() in {".nsp", ".xci"}:
        return "Nintendo Switch"
    if any(k in parts for k in ("dreamcast", "gamecube", "xbox360", "xbox", "retro_arcade", "retroarch")):
        return "Retro_Arcade"
    return None


def detect_console_role(p: Path) -> str:
    s = str(p).lower()
    name = p.name.lower()
    if name.endswith((".keys", ".rap")) or any(k in s for k in ("/keys", "firmware", "bios")):
        return "keys"
    if name.endswith((".dds", ".htc", ".hts")) or any(k in s for k in ("/texture", "/textures", "/load", "/mods", "/patches")):
        return "texture"
    if any(k in s for k in ("/saves", "/save", "games_saves_backup")):
        return "saves"
    return "games"


def is_nvidia(p: Path) -> bool:
    if p.suffix.lower() not in NVIDIA_EXTS:
        return False
    if any(any(kw in part.lower() for kw in NVIDIA_KW) for part in p.parts[:-1]):
        return True
    return bool(SHADOWPLAY_RE.match(p.stem) or "shadowplay" in p.stem.lower())


def nvidia_game_name(p: Path) -> str:
    m = SHADOWPLAY_RE.match(p.stem)
    if m and m.group(1).strip(" ._-"):
        return re.sub(r'[<>:"/\\|?*]', "_", m.group(1).strip(" ._-"))
    par = p.parent.name.strip()
    if par.lower() not in {"nvidia", "geforce", "shadowplay", "nvidia_geforce", "duplicate_videos", "videos", "<SHARE_NAME>", "organized"}:
        return re.sub(r'[<>:"/\\|?*]', "_", par)
    return "Uncategorized_NVIDIA"


def partial_blake2b(p: Path, sz: int) -> str | None:
    h = hashlib.blake2b(digest_size=32)
    try:
        with p.open("rb") as f:
            if sz <= PARTIAL_CHUNK_SIZE * 2:
                h.update(f.read())
            else:
                h.update(f.read(PARTIAL_CHUNK_SIZE))
                f.seek(sz - PARTIAL_CHUNK_SIZE)
                h.update(f.read(PARTIAL_CHUNK_SIZE))
        return h.hexdigest()
    except OSError:
        return None


def full_sha256(p: Path) -> str | None:
    h = hashlib.sha256()
    try:
        with p.open("rb") as f:
            while c := f.read(FULL_HASH_CHUNK_SIZE):
                h.update(c)
        return h.hexdigest()
    except OSError:
        return None


def dup_category(p: Path) -> str:
    ext = p.suffix.lower()
    for cat, exts in EXT_MAP.items():
        if ext in exts:
            return cat
    return "Unknown_Unrecognized"


def unique_dest(dest_dir: Path, name: str, copy_style: bool = True) -> Path:
    cand = dest_dir / name
    if not cand.exists():
        return cand
    stem, suf = Path(name).stem, Path(name).suffix
    i = 1
    while True:
        alt = dest_dir / (f"{stem}_copy{i}{suf}" if copy_style else f"{stem}_{i}{suf}")
        if not alt.exists():
            return alt
        i += 1


def run_server(target: Path, execute: bool, min_size_mb: float, log_dir: Path) -> int:
    target = target.resolve()
    min_bytes = int(min_size_mb * 1024 * 1024)
    now_ts = time.time()
    mode = "EXECUTE" if execute else "DRY-RUN"

    print(f"=== Server Full Reorganizer [{mode}] (ZERO DELETION) ===")
    print(f"Target: {target}")

    # Atomic game units to move cleanly as whole directories
    atomic_console_moves: list[tuple[Path, Path, str, str]] = []
    console_file_counts: dict[str, int] = defaultdict(int)
    nvidia_files: list[tuple[Path, int, float]] = []
    nvidia_size_groups: dict[int, list[tuple[Path, float]]] = defaultdict(list)
    regular_size_groups: dict[int, list[tuple[Path, float]]] = defaultdict(list)

    # Identify known console game/rom folders inside <SHARE_NAME> & Emulators_ROMs & ps3
    mgs_root = target / "<SHARE_NAME>"
    scanned_files = 0

    for dirpath, dirnames, filenames in os.walk(target, followlinks=False):
        dp = Path(dirpath)
        # Prune excluded top-level / system dirs
        pruned = []
        for d in dirnames:
            if d.startswith(".") or d in EXCLUDED_NAMES:
                continue
            if dp == target and d in EXCLUDED_TOP_DIRS:
                continue
            if dp == mgs_root and d in ("PS4", "PS5", "ps5g", "inFAMOUS Second Son port", "Recomp_Built_Games", "Games_Saves_Backup"):
                continue
            # If this subdir is already a standardized console folder at /media/storage/<Console>, keep it
            if dp == target and d in CONSOLES:
                pruned.append(d)
                continue
            # Check if subdir is an atomic console game/emulator directory to move intact
            sub_p = dp / d
            console = detect_console_from_path(sub_p)
            if console and dp != target and not any(c in sub_p.parts for c in CONSOLES):
                # Check if inside Emulators_ROMs/<Console>/<Game> or <SHARE_NAME>/ps3/<Game> or <SHARE_NAME>/The Legend of Zelda
                if dp.name in {"Emulators_ROMs", "ps3"} or d in {"The Legend of Zelda", "Super Mario 3D All-Stars", "ZELDA BOTW Wii U v2"}:
                    role = detect_console_role(sub_p)
                    dest = target / console / role / d
                    atomic_console_moves.append((sub_p, dest, console, role))
                    cnt = sum(len(fs) for _, _, fs in os.walk(sub_p))
                    console_file_counts[f"{console}/{role}"] += cnt
                    scanned_files += cnt
                    continue
            pruned.append(d)
        dirnames[:] = pruned

        for fn in filenames:
            if fn.startswith(".") or fn.endswith(".root_source.txt") or fn.lower().endswith((".tmp", ".part", ".crdownload", ".!qb")):
                continue
            fp = dp / fn
            if fp.is_symlink():
                continue
            scanned_files += 1
            try:
                st = fp.stat()
            except OSError:
                continue
            if st.st_size == 0 or (now_ts - st.st_mtime) < COOLDOWN_SECONDS:
                continue

            if is_nvidia(fp):
                nvidia_files.append((fp, st.st_size, st.st_mtime))
                nvidia_size_groups[st.st_size].append((fp, st.st_mtime))
            else:
                console = detect_console_from_path(fp)
                if console:
                    role = detect_console_role(fp)
                    dest = target / console / role / fn
                    if fp.parent != dest.parent:
                        atomic_console_moves.append((fp, dest, console, role))
                    console_file_counts[f"{console}/{role}"] += 1
                elif st.st_size >= min_bytes:
                    regular_size_groups[st.st_size].append((fp, st.st_mtime))

    # Deduplicate NVIDIA (ZERO DELETION -> Duplicate_Videos)
    nv_dups: set[Path] = set()
    nv_dup_bytes = 0
    for sz, grp in nvidia_size_groups.items():
        if len(grp) < 2:
            continue
        pb = defaultdict(list)
        for p, mt in grp:
            h = partial_blake2b(p, sz)
            if h:
                pb[h].append((p, mt))
        for p_grp in pb.values():
            if len(p_grp) < 2:
                continue
            fb = defaultdict(list)
            for p, mt in p_grp:
                fh = full_sha256(p)
                if fh:
                    fb[fh].append((p, mt))
            for f_grp in fb.values():
                if len(f_grp) < 2:
                    continue
                f_grp.sort(key=lambda x: (0 if "/NVIDIA_GeForce/" in str(x[0]) else 1, x[1], len(str(x[0]))))
                for d, _ in f_grp[1:]:
                    nv_dups.add(d)
                    nv_dup_bytes += sz

    # Deduplicate regular >= min_bytes (ZERO DELETION -> Duplicates_Archive)
    dup_archive_moves: list[dict] = []
    dup_bytes = 0
    for sz, grp in regular_size_groups.items():
        if len(grp) < 2:
            continue
        pb = defaultdict(list)
        for p, mt in grp:
            h = partial_blake2b(p, sz)
            if h:
                pb[h].append((p, mt))
        for p_grp in pb.values():
            if len(p_grp) < 2:
                continue
            fb = defaultdict(list)
            for p, mt in p_grp:
                fh = full_sha256(p)
                if fh:
                    fb[fh].append((p, mt))
            for fh, f_grp in fb.items():
                if len(f_grp) < 2:
                    continue
                f_grp.sort(key=lambda x: (x[1], len(str(x[0])), str(x[0])))
                master = str(f_grp[0][0])
                for d, _ in f_grp[1:]:
                    if "/Duplicates_Archive/" in str(d):
                        continue
                    cat = dup_category(d)
                    dup_archive_moves.append({
                        "source": str(d),
                        "master": master,
                        "sha256": fh,
                        "size_bytes": sz,
                        "category": cat,
                        "dest_dir": str(target / "Duplicates_Archive" / cat),
                    })
                    dup_bytes += sz

    nv_primary = len(nvidia_files) - len(nv_dups)
    print(f"\n================ SERVER AUDIT SUMMARY [{mode}] ================")
    print(f"Total files scanned:               {scanned_files}")
    print(f"Files deleted (ZERO DELETION):     0")
    print(f"Console items -> 4-folder layout:  {len(atomic_console_moves)} moves")
    for k, v in sorted(console_file_counts.items()):
        print(f"  {k:<32} {v} files")
    print(f"NVIDIA GeForce primary captures:   {nv_primary} -> /media/storage/NVIDIA_GeForce/")
    print(f"NVIDIA GeForce duplicate captures: {len(nv_dups)} ({nv_dup_bytes/(1024**3):.2f} GB) -> NVIDIA_GeForce/Duplicate_Videos/")
    print(f"Non-NVIDIA duplicates (>={min_size_mb:g}MB):   {len(dup_archive_moves)} ({dup_bytes/(1024**3):.2f} GB) -> /media/storage/Duplicates_Archive/")

    if not execute:
        print("\n[DRY-RUN] No files moved. Re-run with --execute to apply.")
        return 0

    confirm = input("Type CONFIRM to execute server reorganization: ").strip()
    if confirm != "CONFIRM":
        print("Aborted.")
        return 1

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "server_reorg_execute.log"
    moved = 0

    # Ensure all 12 standardized console 4-folder trees exist
    for c in CONSOLES:
        for sub in CONSOLE_SUBFOLDERS:
            (target / c / sub).mkdir(parents=True, exist_ok=True)

    # Also relocate Recomp_Built_Games & Games_Saves_Backup to /media/storage/ root if inside <SHARE_NAME>
    for special in ("Recomp_Built_Games", "Games_Saves_Backup"):
        src_sp = mgs_root / special
        dst_sp = target / special
        if src_sp.exists() and not dst_sp.exists():
            shutil.move(str(src_sp), str(dst_sp))

    with log_path.open("a", encoding="utf-8") as lf:
        lf.write(f"\n=== RUN {datetime.now(timezone.utc).isoformat()} ===\n")
        for src, dst, c, r in atomic_console_moves:
            if not src.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            final_dst = unique_dest(dst.parent, dst.name, copy_style=False) if dst.exists() else dst
            shutil.move(str(src), str(final_dst))
            moved += 1
            lf.write(f"[CONSOLE] {src} -> {final_dst}\n")

        for fp, _, _ in nvidia_files:
            if not fp.exists():
                continue
            g = nvidia_game_name(fp)
            ddir = (target / "NVIDIA_GeForce" / "Duplicate_Videos" / g) if fp in nv_dups else (target / "NVIDIA_GeForce" / g)
            if fp.parent == ddir:
                continue
            ddir.mkdir(parents=True, exist_ok=True)
            fdst = unique_dest(ddir, fp.name, copy_style=True)
            shutil.move(str(fp), str(fdst))
            moved += 1
            lf.write(f"[NVIDIA] {fp} -> {fdst}\n")

        for item in dup_archive_moves:
            src = Path(item["source"])
            if not src.exists():
                continue
            ddir = Path(item["dest_dir"])
            ddir.mkdir(parents=True, exist_ok=True)
            fdst = unique_dest(ddir, src.name, copy_style=True)
            shutil.move(str(src), str(fdst))
            fdst.with_name(fdst.name + ".root_source.txt").write_text(
                f"Master/Root Source Path: {item['master']}\n"
                f"Original Duplicate Path: {item['source']}\n"
                f"SHA-256: {item['sha256']}\n"
                f"Size (bytes): {item['size_bytes']}\n",
                encoding="utf-8",
            )
            moved += 1
            lf.write(f"[DUP_ARCHIVE] {src} -> {fdst} (master={item['master']})\n")

    print(f"[DONE] Moved {moved} items (0 deletions). Log: {log_path}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=Path, default=Path("/media/storage"))
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True)
    g.add_argument("--execute", action="store_true")
    ap.add_argument("--min-size-mb", type=float, default=5.0)
    ap.add_argument("--log-dir", type=Path, default=Path(__file__).resolve().parent / "logs")
    a = ap.parse_args()
    sys.exit(run_server(a.target, a.execute, a.min_size_mb, a.log_dir))
