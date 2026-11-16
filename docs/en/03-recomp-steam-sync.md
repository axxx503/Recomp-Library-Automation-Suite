<p align="left"><img src="../../assets/icon-03-steam.svg" width="52" align="absmiddle" alt="03-recomp-steam-sync.md"/> &nbsp; <img src="../../assets/agent-master-badge.svg" height="38" align="absmiddle" alt="AI Agent Playbook"/></p>

# Tool 03: Full Steam Library, Grid Artwork & Steam Input Integration

🌐 **Language / اللغة:** **English** | **[العربية (Arabic)](../ar/03-recomp-steam-sync.md)** | **[⬅️ Back to README](../../README.md)**

---

## 🛠️ Prerequisites & Dependencies

| Tool / Dependency | Purpose in This Workflow | Official Link / Setup |
| :--- | :--- | :--- |
| **Steam Client** | Target platform for Non-Steam shortcuts, Grid artwork, Cloud Collections, and Steam Input. | [store.steampowered.com](https://store.steampowered.com) |
| **RecompLauncher** | Source of `library.json` (verified games) and `cache/pc-catalog.json` (official titles & artwork URLs). | [recomplauncher.com](https://recomplauncher.com) |
| **Everything (`es.exe`)** | Used if any custom executable or icon path needs fast resolution. | [voidtools.com](https://www.voidtools.com/) |
| **SmartHdrManager** | Kept clean of SDR titles while Steam launches games. | [GitHub: SmartHdrManager](https://github.com/imniko/SmartHdrManager) |
| **hactool / Key Tools** | Not invoked directly during Steam sync (used in prior build stage). | [GitHub: SciresM/hactool](https://github.com/SciresM/hactool) |
| **Python 3.10+** | Parses/writes binary `shortcuts.vdf`, updates `localconfig.vdf` and `cloud-storage-namespace-1.json`, and fetches artwork in parallel. | [python.org](https://www.python.org/) |

---

## 🚦 Step 0: Mandatory Hardware & Path Verification Gate (RUN FIRST)

> **CRITICAL AGENT INSTRUCTION:** Before modifying any Steam file, run the hardware and active Steam account check below, display the CPU, RAM, **Discrete GPU (dGPU) vs Integrated GPU (iGPU)**, and the detected active Steam account (`PersonaName` + 32-bit `AccountID`), and **ask the user for confirmation**. Never touch `steamapps\common` or delete existing user shortcuts.

### 0.1 Hardware & Active Steam Account Discovery Snippet
```powershell
python -c "
import subprocess, os, re
ps = '''
$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
$gpus = Get-CimInstance Win32_VideoController | ForEach-Object {
    $name = $_.Name
    $is_dgpu = ($name -match 'NVIDIA|GeForce|RTX|GTX|Radeon RX|Arc A') -and ($name -notmatch 'Radeon\(TM\) Graphics|UHD|Iris')
    [PSCustomObject]@{ Name=$name; Role=$(if ($is_dgpu) {'Discrete dGPU'} else {'Integrated iGPU'}) }
}
[PSCustomObject]@{ CPU=$cpu; RAM_GB=$ram; GPUs=$gpus } | ConvertTo-Json -Compress
'''
print(subprocess.check_output(['powershell', '-NoProfile', '-Command', ps], text=True).strip())

lu = r'C:\Program Files (x86)\Steam\config\loginusers.vdf'
if os.path.exists(lu):
    txt = open(lu, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'\"(7656119\d+)\"\s*\{([^}]+)\}', txt):
        sid64 = int(m.group(1))
        body = m.group(2)
        if '\"AutoLogin\"\t\t\"1\"' in body or '\"MostRecent\"\t\t\"1\"' in body:
            acc_id = sid64 - 76561197960265728
            print(f'Active Steam AccountID: {acc_id} (SteamID64: {sid64})')
"
```

### 0.2 Mandatory Questions to Ask the User Before Proceeding
1. **Hardware & Account Confirmation**: Confirm the detected **Discrete GPU (dGPU)** and active Steam `AccountID`.
2. **`<RECOMP_LIB_DIR>` & `library.json`**: Confirm the path to `RecompLauncher`'s `library.json`.
3. **Collection Name & Naming Format**: Confirm adding all verified games under the **`Recomp Library`** collection using the **`<Real Game Title> (<Recomp Project Name>)`** format.

---

## 🔒 Step 1: Close Steam & Back Up Configuration Files

Steam overwrites `shortcuts.vdf`, `localconfig.vdf`, and `cloud-storage-namespace-1.json` from memory when running or exiting.
1. Terminate `steam.exe` and `steamwebhelper.exe` completely:
   ```powershell
   taskkill /F /IM steam.exe
   taskkill /F /IM steamwebhelper.exe
   ```
2. Create `.bak_recomp` backups of:
   - `C:\Program Files (x86)\Steam\userdata\<ACTIVE_ACCOUNT_ID>\config\shortcuts.vdf`
   - `C:\Program Files (x86)\Steam\userdata\<ACTIVE_ACCOUNT_ID>\config\localconfig.vdf`
   - `C:\Program Files (x86)\Steam\userdata\<ACTIVE_ACCOUNT_ID>\config\cloudstorage\cloud-storage-namespace-1.json`

---

## 🏷️ Step 2: Standardized Naming `<Real Game Title> (<Recomp Project Name>)` & Binary `shortcuts.vdf`

1. **Map Project IDs to Official Game Titles**:
   - Read `%APPDATA%\com.recomplauncher.app\cache\pc-catalog.json` (`apps` and `apps_min`).
   - Extract `real_title = app['game']` (or `app['about']['name']`) and `recomp_name = installed_entry['name']` (or `app['name']`).
   - Format `AppName` as: **`<Real Game Title> (<Recomp Project Name>)`** (e.g., `Pokémon Legends: Arceus (Arceuszada)`, `Bayonetta 3 (Witch Time)`, `Gravity Rush 2 (GR2port)`, `The Legend of Zelda: Breath of the Wild (Savage Wind)`).
2. **Write Binary VDF Entry Without Breaking Existing `appid` Links**:
   - Compute the 32-bit unsigned CRC32 shortcut AppID:
     ```python
     def shortcut_appid(exe_quoted: str, app_name: str) -> int:
         return (binascii.crc32((exe_quoted + app_name).encode('utf-8')) & 0xffffffff) | 0x80000000
     ```
   - If the shortcut already exists in `shortcuts.vdf` (matched by `Exe` path or previous `appid`), **preserve its existing `appid`** so controller configs and collection memberships never break, while also registering the new CRC `appid` for artwork and Steam Input.
   - Format `Exe` WITH quotes (`"C:\...\game.exe"`), `StartDir` WITHOUT quotes and ending with a trailing backslash (`C:\...\`), `AllowOverlay = 1`, `AllowDesktopConfig = 1`, `sortas = full_name`, and `tags = {'0': 'Recomp Library'}`.

---

## 🖼️ Step 3: Populate Steam `grid` Artwork (`<appid>p.png`, `_hero.png`, `.png`, `_icon.png`)

To eliminate blank blue placeholders in Steam's library view:
1. Check `%APPDATA%\com.recomplauncher.app\cache\img\<sha256(url)[:32]>` first; if not cached locally, download `cover`, `hero`, `logo`, and `icon` URLs from `pc-catalog.json` in parallel (`ThreadPoolExecutor(16)`).
2. Save the artwork into `C:\Program Files (x86)\Steam\userdata\<ACTIVE_ACCOUNT_ID>\config\grid\` for each shortcut's `appid` (unsigned 32-bit integer):
   - `<appid>p.png`: Vertical box-art capsule (main library grid cover).
   - `<appid>_hero.png`: Wide hero banner (game detail page header).
   - `<appid>.png`: Horizontal header capsule.
   - `<appid>_logo.png`: Transparent title logo.
   - `<appid>_icon.png`: Game icon (also set its full path in the shortcut's `icon` field in `shortcuts.vdf`).

---

## 🎮 Step 4: Native Steam Cloud Collection (`Recomp Library`) & Forced `Steam Input`

1. **Why `tags` in `shortcuts.vdf` Are Not Enough in Modern Steam**:
   - Once `collection-bootstrap-complete` is `"true"`, Steam ignores `shortcuts.vdf` `tags` and reads collections exclusively from `userdata/<ACTIVE_ACCOUNT_ID>/config/cloudstorage/cloud-storage-namespace-1.json`.
   - Furthermore, if you only edit `cloud-storage-namespace-1.json` while `cloud-storage-namespace-1.modified.json` is empty (`[]`), Steam Cloud will overwrite your local collection on startup!
   - **Solution**: Write the collection key `user-collections.rl-recomplauncher` (`"name": "Recomp Library"`, containing both unsigned `u32` and signed `i32` representations of every shortcut's `appid` in `"added"`) into **BOTH** `cloud-storage-namespace-1.json` **AND** `cloud-storage-namespace-1.modified.json`, and increment namespace `1`'s version counter in `cloud-storage-namespaces.json`.
2. **Force Enable `Steam Input` (`UseSteamControllerConfig = 2`) in `localconfig.vdf`**:
   - Enable global controller support in `localconfig.vdf`:
     ```
     "SteamController_XBoxSupport"		"1"
     "SteamController_SwitchSupport"		"1"
     "SteamController_GenericGamepadSupport"		"1"
     "SteamController_PSSupport"		"2"
     ```
   - Under `"apps"` in `localconfig.vdf`, add per-app override `"UseSteamControllerConfig" "2"` (Forced On) for every Recomp shortcut `appid`.
3. **Restart & Verify**:
   - Start `steam.exe`, wait 5 seconds, and verify that `shortcuts.vdf`, `cloud-storage-namespace-1.json`, and all `<appid>p.png` files in `grid\` remain intact.

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
