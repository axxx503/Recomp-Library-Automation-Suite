#!/usr/bin/env python3
"""
nvidia_15day_archiver.py — 15-Day Tiered Local NVIDIA ShadowPlay Archiver for Windows.

Features:
- Auto-detects local NVIDIA GeForce / ShadowPlay capture folders across C:, D:, F:, G:, H:
  (plus Windows Registry ShadowPlay settings if available).
- Only processes files modified >= 15 days ago.
- Checks exclusive Windows file lock (skips files open in DaVinci Resolve, players, etc.).
- Copies to Z:\\Organized\\NVIDIA_GeForce\\<Game_Or_App> (or UNC \\\\<SERVER_IP>\\<SHARE_NAME>\\Organized\\NVIDIA_GeForce).
- Verifies full SHA-256 cryptographic match between local and remote copy BEFORE deleting local file.
- Logs all actions to C:\\Users\\<USER>\\scripts\\nvidia_archiver.log.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import logging
import os
import re
import shutil
import sys
import time
import winreg
from pathlib import Path

DAYS_15_SECONDS = 15 * 24 * 60 * 60
CHUNK_SIZE = 1024 * 1024  # 1 MB

DEFAULT_TARGET_DRIVE = Path(r"Z:\NVIDIA_GeForce")
DEFAULT_TARGET_UNC = Path(r"\\<SERVER_IP>\<SHARE_NAME>\NVIDIA_GeForce")
DEFAULT_LOG_PATH = Path(r"C:\Users\<USER>\scripts\nvidia_archiver.log")

CAPTURE_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".jxr",
    ".hdr",
}

SHADOWPLAY_NAME_RE = re.compile(
    r"^(.+?)[\s_]+\d{4}\.\d{2}\.\d{2}\s*-\s*\d{2}\.\d{2}\.\d{2}(?:\.\d+)?(?:\.DVR)?$",
    re.IGNORECASE,
)

GENERIC_PARENTS = {"nvidia", "geforce", "shadowplay", "videos", "captures", "pictures"}


def setup_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("nvidia_archiver")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger


def detect_local_nvidia_folders() -> list[Path]:
    """Detect active local NVIDIA ShadowPlay / GeForce capture folders across C:, D:, F:, G:, H:."""
    candidates: list[Path] = []

    # 1. Check Windows Registry for configured ShadowPlay save path
    reg_paths = [
        r"Software\NVIDIA Corporation\Global\ShadowPlay\NVSPCAPS",
        r"Software\NVIDIA Corporation\NVIDIA Share\Highlights",
    ]
    for rp in reg_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rp) as key:
                for val_name in ("DefaultPathW", "DefaultPath", "SavePath"):
                    try:
                        val, _ = winreg.QueryValueEx(key, val_name)
                        if isinstance(val, bytes):
                            val = val.decode("utf-16-le", errors="ignore").rstrip("\x00")
                        if isinstance(val, str) and val.strip():
                            p = Path(val.strip())
                            if p.exists() and p.is_dir():
                                candidates.append(p)
                    except OSError:
                        continue
        except OSError:
            continue

    # 2. Scan standard paths across C:, D:, F:, G:, H:
    user_home = Path.home()
    candidates.extend(
        [
            user_home / "Videos" / "NVIDIA",
            user_home / "Videos" / "GeForce",
            user_home / "Videos" / "ShadowPlay",
            user_home / "Pictures" / "NVIDIA",
        ]
    )

    for drive in ("C:", "D:", "F:", "G:", "H:"):
        root = Path(f"{drive}\\")
        if not root.exists():
            continue
        for sub in (
            r"Videos\NVIDIA",
            r"Videos\ShadowPlay",
            r"NVIDIA",
            r"ShadowPlay",
            r"Captures\NVIDIA",
            r"Games\NVIDIA",
        ):
            p = root / sub
            if p.exists() and p.is_dir():
                candidates.append(p)

    # Deduplicate resolved paths
    unique: list[Path] = []
    seen: set[str] = set()
    for c in candidates:
        try:
            rc = str(c.resolve()).lower()
            if c.exists() and c.is_dir() and rc not in seen:
                seen.add(rc)
                unique.append(c.resolve())
        except OSError:
            continue
    return unique


def resolve_network_target() -> Path | None:
    """Resolve Z:\\Organized\\NVIDIA_GeForce or UNC fallback."""
    for candidate in (DEFAULT_TARGET_DRIVE, DEFAULT_TARGET_UNC):
        try:
            share_root = Path(candidate.anchor)
            if share_root.exists():
                return candidate
        except OSError:
            continue
    return None


def is_file_locked_windows(file_path: Path) -> bool:
    """Check if file is exclusively locked / open in another app (e.g. DaVinci Resolve, VLC)."""
    GENERIC_READ = 0x80000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateFileW(
        str(file_path),
        GENERIC_READ,
        0,  # dwShareMode = 0 -> fail if ANY other process has the file open
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        return True
    kernel32.CloseHandle(handle)
    return False


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def extract_game_folder_name(file_path: Path) -> str:
    m = SHADOWPLAY_NAME_RE.match(file_path.stem)
    if m:
        candidate = m.group(1).strip(" ._-")
        if candidate:
            return re.sub(r'[<>:"/\\|?*]', "_", candidate)
    parent = file_path.parent.name.strip()
    if parent and parent.lower() not in GENERIC_PARENTS:
        return re.sub(r'[<>:"/\\|?*]', "_", parent)
    return "Uncategorized_NVIDIA"


def run_archiver(execute: bool, days: int, log_path: Path) -> int:
    logger = setup_logger(log_path)
    mode = "EXECUTE" if execute else "DRY-RUN"
    logger.info(f"=== NVIDIA {days}-Day Tiered Archiver [{mode}] ===")

    local_folders = detect_local_nvidia_folders()
    if not local_folders:
        logger.info("No local NVIDIA ShadowPlay/GeForce folders found on C:/D:/F:/G:/H:. Exiting.")
        return 0

    logger.info(f"Detected local NVIDIA folders: {[str(p) for p in local_folders]}")

    target_root = resolve_network_target()
    if target_root is None:
        logger.warning(
            f"Network target unreachable ({DEFAULT_TARGET_DRIVE} / {DEFAULT_TARGET_UNC}). Skipping run."
        )
        return 1

    logger.info(f"Network destination: {target_root}")
    cutoff_seconds = days * 24 * 60 * 60
    now_ts = time.time()

    eligible = 0
    skipped_recent = 0
    skipped_locked = 0
    archived_ok = 0
    freed_bytes = 0

    for folder in local_folders:
        for dirpath, _, filenames in os.walk(folder):
            for fname in filenames:
                if fname.startswith(".") or fname.lower().endswith((".tmp", ".part", ".crdownload")):
                    continue
                src = Path(dirpath) / fname
                if src.suffix.lower() not in CAPTURE_EXTENSIONS:
                    continue

                try:
                    st = src.stat()
                except OSError:
                    continue

                if (now_ts - st.st_mtime) < cutoff_seconds:
                    skipped_recent += 1
                    continue

                if is_file_locked_windows(src):
                    skipped_locked += 1
                    logger.warning(f"[SKIP-LOCKED] File in use: {src}")
                    continue

                eligible += 1
                game_name = extract_game_folder_name(src)
                dest_dir = target_root / game_name
                dest_file = dest_dir / src.name

                if not execute:
                    logger.info(
                        f"[DRY-RUN] Would archive ({st.st_size / (1024**2):.1f} MB): {src} -> {dest_file}"
                    )
                    continue

                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    local_hash = compute_sha256(src)

                    # Handle filename collisions cleanly
                    if dest_file.exists():
                        remote_hash = compute_sha256(dest_file)
                        if remote_hash == local_hash and dest_file.stat().st_size == st.st_size:
                            # Exact match already exists on server
                            src.unlink()
                            archived_ok += 1
                            freed_bytes += st.st_size
                            logger.info(
                                f"[ALREADY_ARCHIVED_VERIFIED] sha256={local_hash} | deleted local: {src} (kept remote: {dest_file})"
                            )
                            continue
                        # Different content with same name -> _copyN
                        stem, suffix = dest_file.stem, dest_file.suffix
                        idx = 1
                        while True:
                            alt = dest_dir / f"{stem}_copy{idx}{suffix}"
                            if not alt.exists():
                                dest_file = alt
                                break
                            idx += 1

                    # Copy to temporary staging name on server, verify SHA-256, then rename
                    tmp_dest = dest_dir / f".{dest_file.name}.archiving.tmp"
                    shutil.copy2(src, tmp_dest)
                    remote_hash = compute_sha256(tmp_dest)

                    if remote_hash != local_hash or tmp_dest.stat().st_size != st.st_size:
                        tmp_dest.unlink(missing_ok=True)
                        logger.error(
                            f"[HASH_MISMATCH] Aborted delete for {src} (local={local_hash} != remote={remote_hash})"
                        )
                        continue

                    tmp_dest.replace(dest_file)
                    src.unlink()
                    archived_ok += 1
                    freed_bytes += st.st_size
                    logger.info(
                        f"[ARCHIVED_VERIFIED] {src} -> {dest_file} | sha256={local_hash} | freed={st.st_size / (1024**2):.2f} MB"
                    )
                except OSError as exc:
                    logger.error(f"[ERROR] Failed archiving {src}: {exc}")

    logger.info(
        f"Summary [{mode}]: eligible(>={days}d)={eligible}, skipped_recent={skipped_recent}, "
        f"skipped_locked={skipped_locked}, archived_verified={archived_ok}, "
        f"freed={freed_bytes / (1024**3):.2f} GB"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="15-Day Tiered Local NVIDIA ShadowPlay Archiver with SHA-256 Verification."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True, help="Preview without copying/deleting (default).")
    mode.add_argument("--execute", action="store_true", help="Copy, SHA-256 verify, and delete local originals >= 15 days.")
    parser.add_argument("--days", type=int, default=15, help="Age threshold in days (default: 15).")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG_PATH, help="Log file path.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_archiver(execute=args.execute, days=args.days, log_path=args.log))
