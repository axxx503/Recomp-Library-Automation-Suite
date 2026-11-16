<p align="left"><img src="../../assets/icon-01-storage.svg" width="52" align="absmiddle" alt="01-recomp-server-storage.md"/> &nbsp; <img src="../../assets/agent-master-badge.svg" height="38" align="absmiddle" alt="AI Agent Playbook"/></p>

# Tool 01: Smart Storage, NAS Offloading & Unified Cloud Saves

🌐 **Language / اللغة:** **English** | **[العربية (Arabic)](../ar/01-recomp-server-storage.md)** | **[⬅️ Back to README](../../README.md)**

---

## 🛠️ Prerequisites & Dependencies

| Tool / Dependency | Purpose in This Workflow | Official Link / Setup |
| :--- | :--- | :--- |
| **RecompLauncher** | Reads ROM directories (`rom_dirs`) and game paths (`library.json`). | [recomplauncher.com](https://recomplauncher.com) |
| **Everything (`es.exe`)** | Audits large archives (`.zip`, `.rar`, `.7z`, `.dmg`, `.pkg`) and scattered ROMs across drives. | [voidtools.com](https://www.voidtools.com/) |
| **SmartHdrManager** | Preserved intact during storage migrations. | [GitHub: SmartHdrManager](https://github.com/imniko/SmartHdrManager) |
| **hactool / Key Tools** | Verifies extracted game assets before removing obsolete installer archives. | [GitHub: SciresM/hactool](https://github.com/SciresM/hactool) |
| **Steam Client** | All `Steam`, `SteamLibrary`, and `steamapps` folders are strictly protected from movement or deletion. | [store.steampowered.com](https://store.steampowered.com) |
| **Python 3.10+ & NTFS Links** | Executes verified migrations, creates NTFS Junctions (`_winapi.CreateJunction`) for local drives and Directory Symlinks (`os.symlink`) for SMB shares. | [python.org](https://www.python.org/) |

---

## 🚦 Step 0: Mandatory Hardware & Path Verification Gate (RUN FIRST)

> **CRITICAL AGENT INSTRUCTION:** Before modifying, moving, or deleting any file, you **MUST** run the hardware discovery script below, present the detected specifications (explicitly distinguishing between the **Integrated GPU (iGPU)** and the **Discrete GPU (dGPU)**), and **ask the user to confirm their paths**.

### 0.1 Hardware Discovery Snippet (CPU, RAM, iGPU vs dGPU, & Drives)
```powershell
python -c "
import subprocess, json, shutil, os
ps = '''
$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
$gpus = Get-CimInstance Win32_VideoController | ForEach-Object {
    $name = $_.Name
    $is_dgpu = ($name -match 'NVIDIA|GeForce|RTX|GTX|Radeon RX|Arc A') -and ($name -notmatch 'Radeon\(TM\) Graphics|UHD|Iris')
    [PSCustomObject]@{ Name=$name; Role=$(if ($is_dgpu) {'Discrete dGPU'} else {'Integrated iGPU'}); VRAM_MB=[math]::Round($_.AdapterRAM/1MB,0) }
}
[PSCustomObject]@{ CPU=$cpu; RAM_GB=$ram; GPUs=$gpus } | ConvertTo-Json -Compress
'''
print(subprocess.check_output(['powershell', '-NoProfile', '-Command', ps], text=True).strip())
for d in 'CDEFGHZ':
    p = f'{d}:\\\\'
    if os.path.exists(p):
        u = shutil.disk_usage(p)
        print(f'Drive {d}: Free = {u.free/(1024**3):.2f} GB / Total = {u.total/(1024**3):.2f} GB')
"
```

### 0.2 Mandatory Questions to Ask the User Before Proceeding
Stop and ask the user to confirm:
1. **Hardware Confirmation**: Is the detected **Discrete GPU (dGPU)** (separate from the Integrated iGPU) and RAM capacity accurate?
2. **`<GAMES_ROMS_DIR>`**: Where are your local ROMs, ISOs, and game archives currently stored?
3. **`<KEYS_DIR>`**: Where are your decryption keys (`prod.keys`, `title.keys`) and BIOS files stored?
4. **`<SECONDARY_OR_NAS_DRIVE>`**: What is the target secondary drive or SMB network share (e.g., `\\<LOCAL_NAS_IP>\<SHARE_NAME>` mapped to a drive letter), and how much RAM does the NAS have (to apply `< 8GB RAM` throttling if needed)?
5. **Exclusions**: Which folders must remain untouched on local fast storage (e.g., `SteamLibrary`, modern PC/PS4/PS5 ports, next-gen titles, personal project folders)?

---

## 📦 Step 1: Persistent High-Speed SMB Mapping & Low-RAM NAS Protection

1. **Bind SMB Share via Local IP Only (Never VPN/Tailscale for LAN transfers)**:
   ```powershell
   Test-Connection -ComputerName <LOCAL_NAS_IP> -Count 2
   net use <NAS_DRIVE_LETTER>: "\\<LOCAL_NAS_IP>\<SHARE_NAME>" /persistent:yes
   ```
2. **Low-RAM NAS Protection Rules (`< 8GB RAM` Servers)**:
   - **Never** run massive server-side `SHA256` deduplication or `robocopy /MT:16+` on a 4GB RAM NAS, as SMB cache exhaustion will stall the transfer.
   - Use `robocopy "<SRC>" "<DST>" /E /XO /MT:4 /R:2 /W:2 /NP /NFL /NDL` (`/XO` skips already-transferred files when resuming; `/MT:4` keeps SMB memory overhead low).
   - **Order of Migration**: Always migrate **large-file consoles first** (`3DS`, `Xbox360`, `PS2`, `PS3`, `Wii`, `GameCube`, `Dreamcast`, `PSVita`, `Xbox`) before folders containing tens of thousands of tiny files (such as unpacked `PS1` HD texture replacement packs).
   - Enable Windows Sleep Prevention (`SetThreadExecutionState(0x80000001)`) during active transfers and restore (`0x80000000`) upon completion or cancellation.
   - **100% Verification Before Deletion**: Only delete the local source folder after verifying `dst_file_count >= src_file_count` and `dst_bytes >= src_bytes`. Never delete emulator binaries, `BIOS`, or `Keys`.

---

## 🔗 Step 2: Offloading Heavy Recomp Data (`Junctions` vs `Directory Symlinks`)

To relieve pressure on the system drive `C:\` without breaking `RecompLauncher`:

1. **Critical Rule — Local Drive vs Network Share Links**:
   - **Local Secondary Drive (`<SECONDARY_DRIVE>:\Recomp_GameData\<project>`)**: Use **NTFS Junctions** (`_winapi.CreateJunction(target_dir, link_dir)` or `cmd /c mklink /J "<link>" "<target>"`).
   - **Network SMB Share (`<NAS_DRIVE_LETTER>:\Recomp_Built_Games\<project>`)**: Windows `CreateProcess` rejects NTFS Junctions (`IO_REPARSE_TAG_MOUNT_POINT`) pointing to UNC/network paths with `WinError 2 (FileNotFoundError)`. For network targets, **always** use **Directory Symbolic Links**:
     ```python
     os.symlink(r"<NAS_DRIVE_LETTER>:\Recomp_Built_Games\<project>\game", r"<RECOMP_LIB_DIR>\<project>\game", target_is_directory=True)
     ```
2. **Critical Rule — Keep Shader Caches Local on NVMe**:
   - **Never** place `shader-cache` or `cache` folders (such as `Hookshot\cache` or `Longshot\cache` containing multi-gigabyte `*_vk_pipelines.bin` / `*_programs.bin` files) over a network symlink, as SMB latency causes shader loading to hang at `0%`.
   - Always keep `cache` directories on local NVMe storage (`C:\` or `<SECONDARY_DRIVE>:\`) and remove any stale `.warming` lock files (`*.bin.built.warming`).
3. **Clean Up Obsolete Archives After Verified Extraction**:
   - Once a Recomp project's built executable and extracted data (`GoS_Data`, `CUSA*`, `extracted\*.dll`, `romfs.bin`) are verified and tested, delete the leftover raw `.zip`, `.rar`, `.7z`, `.dmg`, and `.pkg` installer archives and temporary staging folders (`W2xExTmp`, `extracted_tmp`) to reclaim gigabytes of space.

---

## 💾 Step 3: Unified Local Save Hub (`<LOCAL_SAVES_DIR>`) & Automated Hourly NAS Backup

1. **Unify All Emulator & Recomp Saves on Local NVMe**:
   - Create `<LOCAL_SAVES_DIR>` (e.g., `C:\Games Saves`) and `<LOCAL_SAVES_DIR>_PreMove_Backup`.
   - Back up and move save directories for `Yuzu` (`nand\user\save`), `Dolphin` (`Wii` & `GC`), `PCSX2` (`memcards`), `RPCS3` (`dev_hdd0\home\00000001\savedata`), and every `RecompLauncher` project (`save` / `userdata`) into `<LOCAL_SAVES_DIR>\<ProjectOrEmulator>`, linking their original paths back via NTFS Junctions (or mirroring non-NTFS `exFAT` partitions in the sync script).
2. **Register Silent Hourly & Logon Mirroring to NAS (`<NAS_DRIVE_LETTER>:\Games_Saves_Backup`)**:
   ```powershell
   $bat = "$env:LOCALAPPDATA\sync_games_saves.bat"
   @"
   @echo off
   robocopy "<LOCAL_SAVES_DIR>" "<NAS_DRIVE_LETTER>:\Games_Saves_Backup" /MIR /R:1 /W:1 /NP >nul
   "@ | Set-Content -Path $bat -Encoding ASCII

   $vbs = "$env:LOCALAPPDATA\SyncGamesSavesToZ.vbs"
   @"
   CreateObject("Wscript.Shell").Run """$bat""", 0, False
   "@ | Set-Content -Path $vbs -Encoding ASCII

   Copy-Item $vbs "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SyncGamesSavesToZ.vbs" -Force
   schtasks /Create /TN "SyncGamesSavesToNAS" /TR "wscript.exe $vbs" /SC HOURLY /F
   ```

---

---

## 🧠 End-to-End Architecture & Workflow Diagram (Mermaid)

```mermaid
flowchart TD
    A["🚦 Step 0: Hardware & Path Gate<br/>Separate iGPU vs dGPU + Confirm User Paths"] --> B["01. Storage & Server Architecture<br/>Local IP SMB + Low-RAM Robocopy /MT:4"]
    B --> C["NTFS Junctions (mklink /J) for Local Drives<br/>Directory Symlinks (os.symlink) for Network"]
    C --> D["Keep Shader Cache on Local NVMe<br/>Unified Saves + Hourly schtasks Sync"]
    D --> E["02. Everything Index Discovery (es.exe)<br/>Locate ROMs, Title IDs, Updates, DLC & Keys"]
    E --> F["Automated Extraction & Compilation<br/>hactool/nstool + gen + zig cc / llvm-mingw"]
    F --> G["Root-Cause Runtime Fixes<br/>WT_OPUS_DLL + GOW3_DMEM_MB + Clear .warming"]
    G --> H["Bypass First-Run / Set Up Screens<br/>Close Launcher -> Sync recomplauncher.json & library.json"]
    H --> I["Golden 1440p Profile + SmartHdrManager Cleanup<br/>Strip SDR Games / Keep Native HDR10 Only"]
    I --> J["03. Steam & Controller Integration<br/>Detect Active AccountID from loginusers.vdf"]
    J --> K["Close steam.exe -> Update shortcuts.vdf<br/>Format: Real Game Title (Recomp Project Name)"]
    K --> L["Generate 4x Grid Assets + Cloud Collection<br/>Force Steam Input (UseSteamControllerConfig = 2)"]
    L --> M["✅ 04. Final 5-Second Live Boot Verification<br/>100% Playable Library in RecompLauncher & Steam"]
```

---

## 🏗️ System Architecture & Engineering Breakdown (How This Suite Was Built)

1. **Phase 1 — Hardware Isolation & Non-Destructive Storage Virtualization (`01`)**:
   - Many multi-GPU laptops and desktops expose both an integrated GPU (`iGPU`) and a discrete GPU (`dGPU`). Every playbook begins with a mandatory **Step 0 Hardware Gate** that queries `Win32_VideoController` and `nvidia-smi` to explicitly separate `iGPU` from `dGPU` before choosing rendering profiles.
   - To free primary `C:` NVMe space without breaking hardcoded paths in `RecompLauncher`, the suite uses **NTFS Junctions (`mklink /J`)** for local secondary drives and **Directory Symlinks (`os.symlink`)** for SMB network shares (avoiding `WinError 2`), while strictly keeping `shaders/` / `cache/` on local NVMe storage so games never freeze at `0%` shader compilation.
   - For home servers with limited memory (`< 8GB RAM`), transfers are throttled via `robocopy /E /XO /MT:4` starting with large-file directories first to prevent SMB non-paged pool exhaustion.
2. **Phase 2 — Instant ROM Indexing, Automated Recompilation & SDR/HDR Color Integrity (`02`)**:
   - Instead of relying on folder names, the agent queries **Everything (`es.exe`)** and emulator configurations (`Dolphin.ini`, `PCSX2.ini`, `RPCS3 games.yml`, `Cemu`, `Xenia`) by file extension and Console Title ID.
   - It automates `Base + Update + DLC` decryption (`hactool` / `nstool`), C code generation (`gen`), and multi-threaded compilation (`zig cc` / `llvm-mingw`), then applies deterministic fixes for silent audio (`WT_OPUS_DLL`), VRAM/pagefile exhaustion (`error 1450` via `GOW3_STREAM_MEMORY=device`), and stuck `First Run / Set Up` prompts (by closing `recomplauncher.exe` before synchronizing `recomplauncher.json` and `library.json`).
   - Finally, it applies the **Golden 1440p Profile** (`2560x1440`, `DLSS/FSR Quality`, `60 FPS`, `~ HIGHDPIAWARE`) and purges SDR executables from `SmartHdrManager` so Windows HDR activates strictly for true Native HDR10 titles.
3. **Phase 3 — Binary Steam VDF Engineering, Artwork Pipeline & Universal Gamepad Fix (`03`)**:
   - The agent resolves the active Steam user (`MostRecent = 1` in `loginusers.vdf`), gracefully closes `steam.exe`, and updates `shortcuts.vdf` with the canonical naming format `<Real Game Title> (<Recomp Project Name>)` while preserving existing unsigned 32-bit `appid` hashes.
   - It populates all 4 Steam artwork slots in `userdata/<active_id>/config/grid/` (`<appid>p.png`, `<appid>_hero.png`, `<appid>.png`, `<appid>_icon.png`), registers the **`Recomp Library`** collection directly inside Steam's modern Cloud Storage files (`cloud-storage-namespace-1.json` and `.modified.json`), and sets `UseSteamControllerConfig = "2"` inside `localconfig.vdf` so Xbox, DualSense, and Switch Pro controllers work immediately.

---

## 📊 Execution Pipeline Table

| Stage | Primary Inputs | Responsible Tool / Component | Technical Operation Executed | Verified Final Output |
| :--- | :--- | :--- | :--- | :--- |
| **Step 0: Gate** | WMI / `nvidia-smi` / User Paths | PowerShell + Agent Interactive Prompt | Separates `iGPU` vs `dGPU`, measures RAM/VRAM, and asks user to confirm all paths & exclusions | Confirmed environment variables & hardware profile |
| **Stage 01: Storage** | `<RECOMP_LIB_DIR>`, `<GAMES_ROMS_DIR>`, `<SAVES_DIR>` | `robocopy /MT:4`, `mklink /J`, `os.symlink`, `schtasks` | Migrates heavy payloads, links folders back transparently, keeps shaders on NVMe, schedules hourly save sync | Freed `C:` space, `0` broken links, backed-up saves |
| **Stage 02: Builder** | `es.exe` Index, `prod.keys`, `pc-catalog.json` | `Everything`, `hactool`, `nstool`, `zig cc`, `SmartHdrManager` | Extracts ROMs, compiles `.exe`, patches `WT_OPUS_DLL` & `error 1450`, syncs `library.json`, cleans SDR from HDR manager | `verified: true` Playable games at `1440p` with accurate SDR/HDR colors |
| **Stage 03: Steam** | `library.json`, `loginusers.vdf`, Cover Assets | Python Binary VDF Parser, `Pillow (PIL)`, Steam Cloud JSON | Formats `AppName` as `<Real Title> (<Recomp>)`, builds 4x `grid` PNGs, creates `Recomp Library` collection, enables Steam Input | Full-artwork Steam library with working controllers |
| **Stage 04: QA Audit** | All `verified: true` Executables | `04-recomp-all-in-one` + `AGENTS_SYNC.json` | Launches each game for 5 seconds, verifies window stability, checks `0` broken junctions, and locks state | 100% audited end-to-end setup |

---

## 🛠️ Comprehensive Troubleshooting Matrix (Root Causes & Instant Fixes)

| Symptom / Error Encountered | Root Technical Cause | Instant Deterministic Fix |
| :--- | :--- | :--- |
| **`WinError 2` / `Cannot create a file when that file already exists` on Network Share** | Windows `mklink /J` (NTFS Junction) only supports local volume GUIDs and rejects remote UNC/SMB network paths (`Z:\` or `\IP\Share`). | Use `mklink /J` strictly for local drives (`C:`, `D:`, `F:`, `H:`) and use Python `os.symlink(src, dst, target_is_directory=True)` (`mklink /D`) for network paths. |
| **Home Server / NAS Freezes or Drops SMB Connection During Transfer** | High-thread `robocopy /MT:32+` or transferring millions of tiny files floods the SMB cache and exhausts non-paged kernel memory on `< 8GB RAM` servers. | Connect via direct Local IP (`\192.168.x.x\Share`), cap threads to `robocopy /E /XO /MT:4`, and transfer large single-file ISO/NSP/PKG folders before small extracted files. |
| **Game Hangs Indefinitely at `0%` Compiling Shaders on Launch** | Shader cache directory (`shaders/` or `cache/`) was moved to a slow HDD or network share, or an interrupted build left a `.warming` lock file. | Keep shader cache directories on local NVMe storage and delete stale `*.warming` lock files before relaunching. |
| **`error 1450` (`Insufficient System Resources Exist to Complete the Requested Service`)** | Heavy PS3/Xbox recomp ports (e.g., God of War III) exhaust contiguous Win32 virtual memory mapping when streaming everything into host RAM. | Set environment variables `GOW3_STREAM_MEMORY=device` and `GOW3_DMEM_MB=2048` (or `4096`), and ensure Windows Pagefile is system-managed on NVMe. |
| **Game Launches with Silent Audio or Missing Cutscene Voice Tracks** | Recomp runtime cannot locate `opus.dll` (`libopus`) in the default working directory (`witch-time` / Bayonetta / Switch ports). | Point the `WT_OPUS_DLL` environment variable (or copy `opus.dll`) directly to the verified `opus.dll` path inside the game's runtime folder. |
| **Game Still Opens on `First Run / Set Up` or `Insert Your Copy` Screen** | `recomplauncher.exe` was still running in the background when `library.json` was edited, causing its in-memory state to overwrite the file on exit, or `romfs.bin` / `assets` path was not written to `recomplauncher.json`. | Run `taskkill /F /IM recomplauncher.exe` **first**, verify extracted `romfs` / `assets` exist, update both `recomplauncher.json` and `library.json` (`verified: true`, `--play`), then relaunch. |
| **Washed-Out, Gray, or Over-Bright Colors When Launching SDR Games** | `SmartHdrManager` has SDR recomp executables registered in its `config.json`, forcing Windows 11 HDR ON for games that output standard SDR. | Close `SmartHdrManager`, remove all SDR recomp `.exe` entries from `SmartHdrManager/config.json` (retaining only true Native HDR10 titles), and turn Windows HDR off for SDR play. |
| **Steam Collection `Recomp Library` or Custom Covers Do Not Appear** | Modifications were written while `steam.exe` was running, written to an inactive `userdata/<id>` folder, or written only to legacy `localconfig.vdf` instead of `cloud-storage-namespace-1.json`. | Check `MostRecent = 1` in `loginusers.vdf`, close `steam.exe` completely, write collection JSON to both `cloud-storage-namespace-1.json` and `.modified.json`, and place all 4 PNG types in `userdata/<active_id>/config/grid/`. |
| **Controller (Xbox / DualSense / Switch Pro) Does Not Respond Inside Game** | SDL2/XInput hooks in raw recomp executables fail to bind the controller without Steam's virtual gamepad translation layer. | Set `"UseSteamControllerConfig" "2"` for all recomp unsigned `appid` entries inside `userdata/<active_id>/config/localconfig.vdf` while `steam.exe` is closed. |

---

## 🤝 Third-Party Credits & Acknowledgments

All external tools, standalone applications, and libraries referenced in this playbook remain governed by their respective authors' licenses (see [**CREDITS.md**](../../CREDITS.md) for the complete list):
- **File Indexing & Search Utilities**: **Everything & `es.exe`** ([https://www.voidtools.com/](https://www.voidtools.com/)) *(by David Carpenter / voidtools — Freeware License)*.
- **Display & HDR Management**: **SmartHdrManager** ([https://github.com/imniko/SmartHdrManager](https://github.com/imniko/SmartHdrManager)) *(by Developer / Maintainer `imniko` — MIT License)*.
- **Recompilation & Launcher Ecosystem**: **RecompLauncher** ([https://recomplauncher.com](https://recomplauncher.com)) *(by Zexyen / RecompLauncher Team)*, **N64Recomp** ([https://github.com/N64Recomp/N64Recomp](https://github.com/N64Recomp/N64Recomp)) *(by Mr-Wiseguy — MIT)*, **XenonRecomp** / **UnleashedRecomp** ([https://github.com/hedge-dev/XenonRecomp](https://github.com/hedge-dev/XenonRecomp)) *(by hedge-dev — MIT / GPL-3.0)*, and Switch / PS2 / PS3 / GameCube recomp community developers.
- **Console Extraction & Decryption Tools**: **hactool** ([https://github.com/SciresM/hactool](https://github.com/SciresM/hactool)) *(by SciresM — ISC License)* & **nstool** ([https://github.com/jakcron/nstool](https://github.com/jakcron/nstool)) *(by jakcron — MIT License)*.
- **Storefront & Controller Integration**: **Valve Steam Client & Steam Input / VDF Format** ([https://store.steampowered.com/](https://store.steampowered.com/)) *(by Valve Corporation — Proprietary / Free Client)*.
- **Runtime, Audio, Graphics, Python & OS Utilities**: **Python 3** ([https://www.python.org/](https://www.python.org/)) *(by Python Software Foundation — PSF License)*, **Pillow (PIL Fork)** ([https://python-pillow.org/](https://python-pillow.org/)) *(by Jeffrey A. Clark / Alex Clark & Contributors — HPND / MIT-CMU License)*, **libopus** ([https://opus-codec.org/](https://opus-codec.org/)) *(by Xiph.Org Foundation — BSD-3-Clause License)*, **SDL2** ([https://www.libsdl.org/](https://www.libsdl.org/)) *(by Sam Lantinga & SDL Contributors — zlib License)*, and **Microsoft Windows Native Utilities (`mklink` / `Robocopy` / `PowerShell` / `Registry`)** *(by Microsoft Corporation — Windows OS Built-in Tools)*.
- **License & Contact**: Copyright © 2026 **`axxx503`** — Free for personal/non-commercial use; commercial use strictly prohibited without written permission (see [**LICENSE.md**](../../LICENSE.md) | [https://bio.site/V7dt1](https://bio.site/V7dt1) | `v7dtads@gmail.com` | [https://buymeacoffee.com/axxx503](https://buymeacoffee.com/axxx503)).
