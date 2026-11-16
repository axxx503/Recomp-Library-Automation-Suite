# 🤝 Third-Party Credits & Acknowledgments / شكر وتقدير لمطوري الأدوات والبرامج المستخدمة

This repository and its AI Agent Playbooks rely on an ecosystem of standalone applications, freeware utilities, command-line tools, compilers, and open-source libraries — hosted both **on GitHub and on independent official websites**. We gratefully acknowledge all original developers, maintainers, and organizations listed below. All third-party tools and libraries remain the property of their respective authors and are governed by their original licenses.

تعتمد هذه الحزمة وأدلة الوكيل الذكي على منظومة متكاملة من البرامج المستقلة، وأدوات الـ Freeware، وأدوات سطر الأوامر، والمكتبات البرمجية — سواء كانت مستضافة **على منصة GitHub أو عبر مواقعها الرسمية المستقلة خارجه**. نتقدم بخالص الشكر والتقدير لجميع المطورين والفرق البرمجية القائمة عليها، وتظل جميع هذه البرامج والمكتبات خاضعة لتراخيص وحقوق مطوريها الأصليين.

---

## 1. File Indexing & Search Utilities (أدوات الفهرسة والبحث الفوري — خارج GitHub)

| Tool / Utility | Official Website / Repository | Developer / Author | License | Role in This Project / الدور في المشروع |
| :--- | :--- | :--- | :--- | :--- |
| **Everything & Everything Command-line Interface (`es.exe`)** | [https://www.voidtools.com/](https://www.voidtools.com/) | **by David Carpenter / voidtools** | `Freeware License` (CLI `es`: `MIT License`) | Instant NTFS MFT file indexing and sub-second search (`es.exe` / `Everything.db`) for discovering game ROMs, ISOs, NSP/XCI packages, updates, DLCs, and BIOS/keys (`prod.keys`, `title.keys`) across all local and network drives without relying on folder names.<br>محرك الفهرسة الفوري والبحث السريع عن ملفات الألعاب والـ ROMs والـ BIOS والمفاتيح عبر الامتدادات ومعرّفات الألعاب دون التقيد بأسماء المجلدات. |

---

## 2. Display & HDR Management Utilities (أدوات الشاشة وإدارة الـ HDR)

| Tool / Utility | Official Website / Repository | Developer / Author | License | Role in This Project / الدور في المشروع |
| :--- | :--- | :--- | :--- | :--- |
| **SmartHdrManager** | [https://github.com/imniko/SmartHdrManager](https://github.com/imniko/SmartHdrManager) | **by Developer / Maintainer (`imniko`)** | `MIT License` | Automatic Windows HDR state management utility; configured by the agent (`config.json`) to trigger HDR exclusively for Native HDR10 titles while stripping SDR recomp ports to prevent washed-out colors.<br>أداة إدارة تفعيل Windows HDR تلقائياً للألعاب الداعمة (`Native HDR10`) وفصل ألعاب الـ SDR لمنع بهتان الألوان. |

---

## 3. Recompilation & Launcher Ecosystem (منظومة البورتات واللانشر)

| Project / Tool | Official Website / Repository | Developer / Author | License | Role in This Project / الدور في المشروع |
| :--- | :--- | :--- | :--- | :--- |
| **RecompLauncher** | [https://recomplauncher.com](https://recomplauncher.com) | **by Zexyen / RecompLauncher Team** | `Freeware / Proprietary Launcher` | Central management interface for static recompilation ports, catalog updates (`pc-catalog.json`), and library state tracking (`library.json` & `recomplauncher.json`).<br>واجهة إدارة مكتبة البورتات والكتالوج (`library.json` و `recomplauncher.json`). |
| **N64Recomp** | [https://github.com/N64Recomp/N64Recomp](https://github.com/N64Recomp/N64Recomp) | **by Mr-Wiseguy & Contributors** | `MIT License` | Core static recompilation technology translating MIPS binaries into portable C code for native PC execution.<br>نواة إعادة الترجمة الثابتة لتحويل شيفرات الألعاب إلى كود C أصلي للبي سي. |
| **XenonRecomp & UnleashedRecomp** | [https://github.com/hedge-dev/XenonRecomp](https://github.com/hedge-dev/XenonRecomp) / [UnleashedRecomp](https://github.com/hedge-dev/UnleashedRecomp) | **by hedge-dev (Skyth, Sajid, Radfordhound & Contributors)** | `MIT License` / `GPL-3.0 License` | Xbox 360 PowerPC static recompilation toolchain and shader/runtime architecture.<br>سلسلة أدوات إعادة ترجمة معمارية Xbox 360 PowerPC إلى الحاسب الشخصي. |
| **Switch / PS2 / PS3 / GameCube / Wii U / PS1 Recomp Community Ports** | Individual GitHub Repositories indexed via `pc-catalog.json` | **by Community Recomp Developers** *(peiikai, Zexyen, NotRexed, valentderah, jmars125, captainj-sparrow, FelipePrado0, junminlee2004, RenanQueiroz, VirtuaQuest, XiONDiGiTaL & others)* | `GPL-2.0` / `GPL-3.0` / `MIT License` | Game-specific static recompilation ports, C code generators (`gen`), and custom Vulkan/D3D12/OpenGL runtimes.<br>مطورو مجتمع بورتات Switch و PS2 و PS3 و GameCube و Wii U و PS1 مفتوحة المصدر. |

---

## 4. Console Extraction, Decryption & Firmware Tools (أدوات فك التشفير والاستخراج والمترجمات)

| Tool / Utility | Official Website / Repository | Developer / Author | License | Role in This Project / الدور في المشروع |
| :--- | :--- | :--- | :--- | :--- |
| **hactool** | [https://github.com/SciresM/hactool](https://github.com/SciresM/hactool) | **by SciresM** | `ISC License` | Command-line tool for inspecting, decrypting, and merging Nintendo Switch archives (`NSP`/`NCA`/`XCI`: `Base + Update + DLC`) into `exefs` and `romfs` using `prod.keys`.<br>أداة سطر الأوامر لفك وتجميع حزم Nintendo Switch (`Base + Update + DLC`). |
| **nstool** | [https://github.com/jakcron/nstool](https://github.com/jakcron/nstool) | **by jakcron** | `MIT License` | General-purpose reading and extraction tool for Nintendo Switch file formats (`NACP`, `NRO`, `NSO`, `NCA`, `PFS0`, `RomFS`).<br>أداة فحص واستخراج محتويات ملفات Nintendo Switch. |
| **Zig Compiler (`zig cc`) & llvm-mingw** | [https://ziglang.org/](https://ziglang.org/) / [https://github.com/mstorsjo/llvm-mingw](https://github.com/mstorsjo/llvm-mingw) | **by Andrew Kelley, Zig Software Foundation, The LLVM Project & Martin Storsjö** | `MIT License` / `Apache-2.0 WITH LLVM-exception` | High-speed C/C++ compilation backends used by recompilation pipelines to compile generated C translation units into native Windows `.exe` binaries.<br>المترجمات السريعة المستخدمة لتحويل ملفات الـ C المولّدة إلى ملفات تنفيذية `.exe` أصلية للويندوز. |

---

## 5. Storefront, Controller & Platform Integration (التكامل مع المتاجر وأيدي التحكم — خارج GitHub)

| Platform / Tool | Official Website / Repository | Developer / Author | License | Role in This Project / الدور في المشروع |
| :--- | :--- | :--- | :--- | :--- |
| **Valve Steam Client & Steam Input / VDF Format** | [https://store.steampowered.com/](https://store.steampowered.com/) | **by Valve Corporation** | `Proprietary / Free Client` | Non-Steam shortcut integration (`shortcuts.vdf`), custom artwork rendering (`grid`: vertical poster, hero, wide capsule, icon), Cloud Storage library collections (`cloud-storage-namespace-1.json`), and universal controller translation (`Steam Input` / `UseSteamControllerConfig = 2` in `localconfig.vdf`).<br>التكامل مع مكتبة Steam (`shortcuts.vdf`, `localconfig.vdf`, `cloud-storage-namespace-1.json`, `grid`) وتوحيد عمل أيدي التحكم عبر `Steam Input`. |

---

## 6. Runtime, Audio, Graphics, Python & OS Utilities (المكتبات البرمجية والصوتية والرسومية وأدوات النظام)

| Library / Runtime | Official Website / Repository | Developer / Author | License | Role in This Project / الدور في المشروع |
| :--- | :--- | :--- | :--- | :--- |
| **Python 3** | [https://www.python.org/](https://www.python.org/) | **by Python Software Foundation** | `PSF License` | Core scripting runtime executing library audits, binary VDF parsing/generation, INI/TOML/JSON configuration tuning, and automated boot verification.<br>بيئة تشغيل سكربتات الأتمتة والتدقيق وبناء ملفات VDF الثنائية. |
| **Pillow (PIL Fork)** | [https://python-pillow.org/](https://python-pillow.org/) / [GitHub](https://github.com/python-pillow/Pillow) | **by Jeffrey A. Clark / Alex Clark & Contributors** | `HPND / MIT-CMU License` | Image processing library used to generate and convert Steam `grid` assets (`<appid>p.png`, `<appid>_hero.png`, `<appid>.png`, `<appid>_icon.png`).<br>معالجة وتحويل صور الأغلفة والبنرات في مجلد `grid` الخاص بـ Steam. |
| **libopus** | [https://opus-codec.org/](https://opus-codec.org/) | **by Xiph.Org Foundation & Contributors** | `BSD-3-Clause License` | Open-source audio codec library (`opus.dll`) used to resolve silent audio and cutscene decoding issues in recomp ports (e.g., `WT_OPUS_DLL`).<br>مكتبة فك ترميز الصوت المستخدمة في إصلاح صوتيات الألعاب (مثل `WT_OPUS_DLL`). |
| **SDL2 (`Simple DirectMedia Layer`)** | [https://www.libsdl.org/](https://www.libsdl.org/) / [GitHub](https://github.com/libsdl-org/SDL) | **by Sam Lantinga & SDL Contributors** | `zlib License` | Cross-platform windowing, audio, and gamepad input abstraction layer (`SDL2.dll`) powering recomp executables.<br>طبقة النوافذ والصوتيات ومدخلات أيدي التحكم (`SDL2.dll`). |
| **Microsoft Windows Native Utilities (`mklink` / `Robocopy` / `PowerShell` / `Registry` / `schtasks`)** | [https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/) | **by Microsoft Corporation** | `Windows OS Built-in Tools` | Native OS utilities used for creating `NTFS Junctions` (`mklink /J`) and `Directory Symlinks` (`mklink /D`), low-RAM safe server transfers (`robocopy /E /XO /MT:4`), hourly save synchronization (`schtasks`), and High-DPI scaling overrides (`~ HIGHDPIAWARE`).<br>أدوات نظام ويندوز الأساسية لإنشاء وصلات `NTFS Junction` و `Directory Symlinks` ومزامنة ملفات الحفظ وتطبيق توافق `~ HIGHDPIAWARE`. |
