<p align="right"><img src="../../assets/icon-04-allinone.svg" width="52" align="absmiddle" alt="04-recomp-all-in-one.md"/> &nbsp; <img src="../../assets/agent-master-badge.svg" height="38" align="absmiddle" alt="AI Agent Playbook"/></p>

# الأداة 04: الأداة الشاملة الكاملة (التخزين والسيرفر + البناء الآلي والـ HDR + الربط مع Steam)

🌐 **اللغة / Language:** **[English](../en/04-recomp-all-in-one.md)** | **العربية (Arabic)** | **[⬅️ العودة إلى الصفحة الرئيسية](../../README.ar.md)**

---

## 🛠️ الأدوات والاعتماديات المطلوبة (Prerequisites)

| الأداة / البرنامج | دورها في المنظومة الشاملة | الرابط الرسمي / التثبيت |
| :--- | :--- | :--- |
| **RecompLauncher** | إدارة مشاريع الـ Recomp (`library.json`, `recomplauncher.json`, `pc-catalog.json`). | [recomplauncher.com](https://recomplauncher.com) |
| **Everything (`es.exe`)** | الفهرسة اللحظية للعثور على الرومات والأقراص عبر الامتدادات ومعرّفات الألعاب. | [voidtools.com](https://www.voidtools.com/) |
| **SmartHdrManager** | التحكم التلقائي في Windows HDR؛ يُنقّى من ألعاب SDR لمنع بهتان الألوان. | [GitHub: SmartHdrManager](https://github.com/imniko/SmartHdrManager) |
| **hactool والمترجمات المدمجة** | فك ودمج `Base + Update + DLC` (`--basenca`) وترجمة الكود عبر `zig` و `clang`. | [GitHub: SciresM/hactool](https://github.com/SciresM/hactool) |
| **Steam Client** | توحيد استجابة اليد (`Steam Input`)، والـ Overlay، والأغلفة، ومجموعة `Recomp Library`. | [store.steampowered.com](https://store.steampowered.com) |
| **Python 3.10+ & NTFS Links** | قيادة الأتمتة الشاملة، ملف التنسيق `AGENTS_SYNC.json`، وكتابة ملفات VDF/JSON. | [python.org](https://www.python.org/) |

---

## 🚦 الخطوة 0 (Step 0): بوابة التحقق التفاعلي من العتاد والمسارات (تُنفَّذ أولاً)

> **تعليمات إلزامية للوكيل الذكي:** يُمنع منعاً باتاً لمس أو تعديل أي ملف قبل تنفيذ الخطوة 0: افحص عتاد الجهاز (مع **الفصل الصريح بين كرت الشاشة المدمج iGPU والكرت المنفصل dGPU**)، وافحص `<RECOMP_LIB_DIR>\AGENTS_SYNC.json` لمنع التعارض مع أي وكيل آخر، ثم توقف واسأل المستخدم لتأكيد المواصفات والمسارات.

### 0.1 سكربت الفحص الشامل للعتاد والأقراص وحساب Steam النشط
```powershell
python -c "
import subprocess, os, re, shutil
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

### 0.2 قائمة التأكيد التفاعلي الإلزامية من المستخدم
اطلب من المستخدم تأكيد الآتي قبل بدء المرحلة 1:
1. **المواصفات المرصودة**: تأكيد المعالج، الرام، واسم **كرت الشاشة المنفصل (dGPU)** (المستقل عن الكرت المدمج iGPU).
2. **`<GAMES_ROMS_DIR>`**: مسار مجلدات الألعاب والـ ROMs.
3. **`<KEYS_DIR>`**: مسار ملفات المفاتيح (`prod.keys`, `title.keys`) والـ `BIOS`.
4. **`<SECONDARY_OR_NAS_DRIVE>`**: مسار القرص الإضافي أو السيرفر الشبكي (`\\<LOCAL_NAS_IP>\<SHARE_NAME>`) وحجم رام السيرفر.
5. **`<RECOMP_LIB_DIR>` و `<LOCAL_SAVES_DIR>`**: مسار مكتبة `Recomp Library` ومجلد التخزينات الموحد.
6. **قائمة الحماية والاستثناءات**: تأكيد عدم لمس مجلدات `Steam` / `SteamLibrary` / `steamapps`، والبورتات الحديثة، والمجلدات الشخصية.

---

## 🔄 الترتيب الهندسي الصارم للتنفيذ (المراحل 1 ← 4)

### المرحلة 1: هيكلة التخزين، النقل للسيرفر، وتوحيد التخزينات ([التفاصيل في الأداة 01](./01-recomp-server-storage.md))
1. اربط السيرفر المنزلي بشكل دائم عبر العنوان المحلي (`net use <NAS_DRIVE_LETTER>: "\\<LOCAL_NAS_IP>\<SHARE_NAME>" /persistent:yes`).
2. خفف الضغط عن `C:` بنقل مجلدات البيانات الثقيلة إلى `<SECONDARY_DRIVE>:\Recomp_GameData` (بوصلات **NTFS Junction** `_winapi.CreateJunction`) أو `<NAS_DRIVE_LETTER>:\Recomp_Built_Games` (بروابط **Directory Symbolic Links** `os.symlink(..., target_is_directory=True)` لتفادي خطأ `WinError 2`).
3. أبقِ جميع مجلدات **كاش الشيدرز (`cache\`, `shader-cache\`)** محلية على الـ NVMe واحذف أي ملفات قفل عالقة `*.warming`.
4. انقل رومات المحاكيات الكلاسيكية عبر `robocopy /E /XO /MT:4` (المجلدات ذات الملفات الكبيرة أولاً لحماية السيرفرات ذات الرام `< 8GB`)، ولا تحذف النسخة المحلية إلا بعد تطابق عدد الملفات والحجم بالبايت بنسبة 100%.
5. وحّد جميع تخزينات المحاكيات ومشاريع الـ Recomp في `<LOCAL_SAVES_DIR>` بوصلات `NTFS Junction` وسجّل المهمة المجدولة الصامتة (`robocopy /MIR` كل ساعة وعند تسجيل الدخول إلى `<NAS_DRIVE_LETTER>:\Games_Saves_Backup`).

### المرحلة 2: اكتشاف الرومات، البناء الآلي، إنهاء شاشات `Set Up`، وضبط الـ HDR ([التفاصيل في الأداة 02](./02-recomp-auto-builder.md))
1. نسّق عبر `<RECOMP_LIB_DIR>\AGENTS_SYNC.json` لمنع تكرار العمل على أي مشروع جاهز أو قيد المعالجة.
2. اكتشف الرومات والأقراص عبر **Everything (`es.exe` / `Everything.db`)** وإعدادات المحاكيات (`Dolphin.ini`, `PCSX2.ini`, `RPCS3 games.yml`, `Cemu`, `Xenia`).
3. استخرج وادمج `Base + Update + DLC` (`hactool`)، وابنِ المشاريع القابلة للبناء عبر سطر الأوامر (`lasgen`/`swgen` + `zig cc` + `zig lld-link`).
4. طبّق الإصلاحات الخاصة بالبورتات:
   - `WT_OPUS_DLL` و `WITCHTIME_REPO` ومسار `"dump"` في `setup_state.json` للعبة *Witch Time (Bayonetta 3)*.
   - `GOW3_STREAM_MEMORY=device` و `GOW3_DMEM_MB=6144` لحل خطأ الذاكرة `error 1450` في *SpartanPort (God of War III)*.
   - مطابقة أسماء مجلدات التشغيل في `recomplauncher.json` (`Astral Chain/astralchain.exe`, `game/cadence.exe`, `extracted --play`) وحذف مرحلة `"prepare"`.
5. أغلق `recomplauncher.exe` قبل تحديث `library.json` (`verified: true`, `setup_done: true`, `files_in_place: true`, `auto_update: false`, `--play`).
6. طبّق **التوازن الذهبي** (`2560x1440`، `DLSS/FSR Quality`، `60 FPS`، إيقاف Motion Blur و Frame Gen، وتفعيل `~ HIGHDPIAWARE`)، و**أزل جميع ألعاب SDR من `SmartHdrManager\config.json`** مع إبقاء الألعاب الداعمة لـ Native HDR10 فقط.

### المرحلة 3: الربط مع Steam، الأغلفة، وتفعيل Steam Input ([التفاصيل في الأداة 03](./03-recomp-steam-sync.md))
1. أغلق `steam.exe` بالكامل وخذ نسخاً احتياطية من `shortcuts.vdf` و `localconfig.vdf` و `cloud-storage-namespace-1.json`.
2. حدد `AccountID` النشط من `Steam\config\loginusers.vdf`.
3. أضف/حدّث جميع الألعاب المفعّلة في `shortcuts.vdf` بالصيغة الموحدة **`<الاسم الحقيقي الكامل للعبة> (<اسم مشروع الريكومب>)`** من `pc-catalog.json` مع الحفاظ على `appid` وتفعيل `AllowOverlay = 1`.
4. ولّد صور `<appid>p.png` و `<appid>_hero.png` و `<appid>.png` و `<appid>_logo.png` و `<appid>_icon.png` داخل `userdata/<ACTIVE_ACCOUNT_ID>/config/grid/`.
5. سجّل مجموعة `Recomp Library` (`user-collections.rl-recomplauncher`) في **كلا الملفين** `cloud-storage-namespace-1.json` و `cloud-storage-namespace-1.modified.json` (مع رفع رقم النسخة في `cloud-storage-namespaces.json`)، وفعّل **`Steam Input` (`UseSteamControllerConfig = 2`)** إجبارياً في `localconfig.vdf`.

### المرحلة 4: اختبار الإقلاع الفعلي (5 ثوانٍ) والمراجعة الختامية
1. اختبر إقلاع الألعاب لمدة 5 ثوانٍ (`alive_after_5s=True`).
2. أعد تشغيل `steam.exe` و `recomplauncher.exe`، وتأكد من عدم وجود أي وصلة مكسورة (`broken_links = 0`)، ووثّق النتيجة في `AGENTS_SYNC.json`.

---

---

## 🧠 المخطط الانسيابي والهيكلي الكامل للمنظومة (Mermaid Workflow)

```mermaid
flowchart TD
    A["🚦 بوابة التحقق (Step 0)<br/>فصل كرت الشاشة المدمج iGPU عن المنفصل dGPU + تأكيد المسارات"] --> B["01. هندسة التخزين والسيرفر<br/>ربط Local IP SMB + نقل آمن لرام أقل من 8GB عبر Robocopy /MT:4"]
    B --> C["وصلات NTFS Junctions للأقراص المحلية<br/>وروابط Directory Symlinks لمسارات الشبكة"]
    C --> D["إبقاء كاش الشيدرز على NVMe المحلي<br/>توحيد ملفات الحفظ + مزامنة مجدولة كل ساعة"]
    D --> E["02. الاكتشاف الفوري عبر Everything (es.exe)<br/>إيجاد الرومات والتحديثات والإضافات والمفاتيح بالامتدادات"]
    E --> F["الاستخراج والبناء الآلي<br/>hactool/nstool + gen + zig cc / llvm-mingw"]
    F --> G["الحلول الجذرية لأعطال التشغيل<br/>إصلاح صوت WT_OPUS_DLL + ذاكرة error 1450 + إزالة أقفال .warming"]
    G --> H["إنهاء شاشات First Run / Set Up نهائياً<br/>إغلاق اللانشر أولاً ثم مزامنة recomplauncher.json و library.json"]
    H --> I["ضبط التوازن الذهبي 1440p + تنقية SmartHdrManager<br/>إزالة ألعاب SDR لمنع بهتان الألوان وإبقاء Native HDR10 فقط"]
    I --> J["03. التكامل الشامل مع Steam وأيدي التحكم<br/>اكتشاف الحساب النشط تلقائياً من loginusers.vdf"]
    J --> K["إغلاق steam.exe ثم تحديث shortcuts.vdf<br/>بصيغة: الاسم الحقيقي الكامل للعبة (اسم مشروع الريكومب)"]
    K --> L["توليد الأغلفة الأربعة في grid + مجموعة Recomp Library<br/>تفعيل Steam Input الإجباري (UseSteamControllerConfig = 2)"]
    L --> M["✅ 04. الفحص النهائي واختبار الإقلاع الفعلي (5 ثوانٍ)<br/>مكتبة جاهزة 100% في RecompLauncher و Steam"]
```

---

## 🏗️ كيف تم بناء وتجميع هذه المنظومة (System Architecture & Engineering Breakdown)

1. **المرحلة الأولى — العزل الدقيق للعتاد وافتراضية التخزين الآمنة (`01-recomp-server-storage`)**:
   - تحتوي أغلب الأجهزة الحديثة على كرت شاشة مدمج (`iGPU`) وكرت منفصل (`dGPU`)؛ لذلك تبدأ كل أداة ببوابة **Step 0** التي تفحص العتاد وتفصل صراحةً بين الكرتين قبل اختيار إعدادات الريندر.
   - لتفريغ قرص النظام `C:` دون كسر المسارات الثابتة في `RecompLauncher`، صممنا المنظومة لتستخدم **وصلات `NTFS Junction` (`mklink /J`)** للأقراص المحلية، و**الروابط الرمزية (`os.symlink` / `mklink /D`)** لمسارات الشبكة والسيرفر لتجنب خطأ `WinError 2`، مع إبقاء مجلدات **كاش الشيدرز (`Shader Cache`)** محلياً على قرص الـ NVMe لمنع تعليق الألعاب عند `0%`.
   - لحماية السيرفرات المنزلية ذات الرام المحدود (`< 8GB RAM`) من الاختناق، يتم النقل عبر عنوان الـ IP المحلي المباشر باستخدام `robocopy /E /XO /MT:4` مع البدء بالمجلدات ذات الملفات الكبيرة الموحدة أولاً.
2. **المرحلة الثانية — الفهرسة الفورية، البناء التلقائي، وحماية دقة ألوان الـ SDR/HDR (`02-recomp-auto-builder`)**:
   - بدلاً من البحث اليدوي أو الاعتماد على أسماء المجلدات، يستعلم الوكيل مباشرة من محرك **Everything (`es.exe`)** وملفات إعدادات المحاكيات (`Dolphin`, `PCSX2`, `RPCS3`, `Cemu`, `Xenia`) بالامتدادات ومعرّفات الألعاب (`Title IDs`).
   - يقوم السكربت بفك ودمج `Base + Update + DLC` عبر `hactool` / `nstool`، وتوليد شيفرة الـ C وبنائها عبر `zig cc` / `llvm-mingw`، ثم يطبق الحلول الجذرية لأعطال الصوت (`WT_OPUS_DLL`) والذاكرة (`error 1450` عبر `GOW3_STREAM_MEMORY=device`)، ويلغي نوافذ `First Run / Set Up` عبر إغلاق `recomplauncher.exe` أولاً ثم توحيد `recomplauncher.json` و `library.json`.
   - يضبط الوكيل جميع الألعاب على **معيار التوازن الذهبي (`1440p` / `60 FPS` / `~ HIGHDPIAWARE`)** وينظف قائمة `SmartHdrManager` من ألعاب الـ SDR لمنع بهتان الألوان.
3. **المرحلة الثالثة — الهندسة الثنائية لملفات Steam VDF، الأغلفة، وتفعيل يد التحكم (`03-recomp-steam-sync`)**:
   - يحدد الوكيل الحساب النشط (`MostRecent = 1` في `loginusers.vdf`)، ويغلق `steam.exe` بالكامل، ثم يحدث `shortcuts.vdf` بالصيغة الموحدة `<الاسم الحقيقي الكامل للعبة> (<اسم مشروع الريكومب>)` مع الحفاظ على معرّف `appid` لكل لعبة.
   - يولّد الصور الأربع لكل لعبة داخل مجلد `grid` (`<appid>p.png`, `<appid>_hero.png`, `<appid>.png`, `<appid>_icon.png`)، وينشئ مجموعة **`Recomp Library`** في ملفات التخزين السحابي (`cloud-storage-namespace-1.json` و `.modified.json`)، ويفعّل **`Steam Input` (`UseSteamControllerConfig = 2`)** في `localconfig.vdf` لتعمل جميع أيدي التحكم فوراً.

---

## 📊 جدول مراحل التنفيذ الهندسي (Execution Pipeline Table)

| المرحلة | المدخلات الأساسية (Inputs) | الأداة المسؤولة (Tool) | العملية التقنية المنفذة (Technical Operation) | المخرج النهائي الموثّق (Output) |
| :--- | :--- | :--- | :--- | :--- |
| **Step 0: بوابة الفحص** | بيانات `WMI` و `nvidia-smi` ومسارات المستخدم | PowerShell + بوابة الحوار التفاعلي | فصل `iGPU` عن `dGPU`، قراءة الرام والـ VRAM، وأخذ تأكيد المستخدم على المسارات والمستثنيات | متغيرات بيئة مؤكدة وملف عتاد دقيق |
| **المرحلة 01: التخزين** | `<RECOMP_LIB_DIR>`, `<GAMES_ROMS_DIR>`, `<SAVES_DIR>` | `robocopy /MT:4`, `mklink /J`, `os.symlink`, `schtasks` | ترحيل المجلدات الضخمة، ربط المسارات شفافياً، إبقاء الشيدرز على NVMe، وجدولة مزامنة الحفظ كل ساعة | تفريغ قرص `C:`، صفر روابط مكسورة، وحفظ مؤمّن |
| **المرحلة 02: البناء والـ HDR** | فهرس `es.exe`، مفاتيح `prod.keys`، `pc-catalog.json` | `Everything`, `hactool`, `nstool`, `zig cc`, `SmartHdrManager` | استخراج الرومات، ترجمة الـ `.exe`، إصلاح `WT_OPUS_DLL` و `error 1450`، مزامنة `library.json`، وتنقية الـ HDR | ألعاب جاهزة (`Play`) بدقة `1440p` وألوان SDR/HDR صحيحة |
| **المرحلة 03: الربط مع Steam** | `library.json`, `loginusers.vdf`، صور المشاريع | محلل VDF الثنائي بـ Python، مكتبة `Pillow`، ملفات Cloud JSON | تسمية `<Real Title> (<Recomp>)`، توليد 4 صور `grid`، إنشاء مجموعة `Recomp Library`، وتفعيل `Steam Input` | مكتبة Steam متكاملة بالأغلفة واستجابة فورية لليد |
| **المرحلة 04: التدقيق الشامل** | جميع الألعاب المفعّلة (`verified: true`) | `04-recomp-all-in-one` + `AGENTS_SYNC.json` | اختبار إقلاع فعلي لمدة 5 ثوانٍ لكل لعبة، فحص سلامة الوصلات، وتثبيت الحالة النهائية | منظومة مدققة وشغالة بنسبة 100% |

---

## 🛠️ جدول استكشاف الأخطاء وحلولها الفورية (Comprehensive Troubleshooting Matrix)

| المشكلة / الخطأ الذي قد يواجهك | السبب الجذري التقني (Root Cause) | الحل الفوري الحاسم (Instant Deterministic Fix) |
| :--- | :--- | :--- |
| **خطأ `WinError 2` عند إنشاء وصلة لمجلد على السيرفر (`Z:\`)** | أمر `mklink /J` (`NTFS Junction`) يدعم الأقراص المحلية فقط ويرفض مسارات الشبكة `SMB/UNC`. | استخدم `mklink /J` للأقراص المحلية فقط، واستخدم `os.symlink` (`mklink /D`) لمسارات الشبكة والسيرفر. |
| **تعليق السيرفر المنزلي أو انقطاع اتصال SMB أثناء النقل** | استخدام خيوط عالية (`MT:32+`) أو نقل آلاف الملفات الصغيرة دفعة واحدة يستنزف ذاكرة الكاش والـ Non-paged Pool في السيرفرات ذات رام `< 8GB`. | اربط السيرفر عبر `Local IP` مباشر، واستخدم `robocopy /E /XO /MT:4`، وانقل مجلدات الملفات الكبيرة الموحدة أولاً. |
| **تعليق اللعبة عند `0%` أثناء بناء الشيدرز (Shader Compiling)** | نقل مجلد `shaders/` أو `cache/` إلى قرص بطيء أو مسار شبكة، أو وجود ملف قفل `.warming` من عملية سابقة مقاطعة. | أبقِ مجلدات الشيدرز محلياً على قرص NVMe، واحذف أي ملفات `*.warming` عالقة قبل التشغيل. |
| **ظهور خطأ الذاكرة `error 1450` (`Insufficient System Resources`)** | استنزاف الذاكرة الافتراضية المتصلة في ألعاب PS3/Xbox الثقيلة (مثل `God of War III`) عند محاولة حجز كامل البيانات في الرام. | عيّن متغيرات البيئة `GOW3_STREAM_MEMORY=device` و `GOW3_DMEM_MB=2048` (أو `4096`) وتأكد من تفعيل Pagefile على قرص NVMe. |
| **اختفاء الصوت في اللعبة أو صمت العروض السينمائية** | عدم عثور المحرك على مكتبة فك ترميز الصوت `opus.dll` (`libopus`) في مسار التشغيل (مثل `witch-time`). | مرّر المسار الكامل لملف `opus.dll` عبر المتغير `WT_OPUS_DLL` أو انسخ `opus.dll` بجانب الملف التنفيذي للعبة. |
| **استمرار ظهور نافذة `First Run / Set Up` أو `Insert Your Copy`** | تعديل `library.json` بينما `recomplauncher.exe` يعمل في الخلفية (مما يعيد كتابة الحالة القديمة عند إغلاقه) أو عدم ربط مسار `romfs`/`assets` في `recomplauncher.json`. | أغلق اللانشر فوراً (`taskkill /F /IM recomplauncher.exe`)، وتأكد من وجود `romfs.bin`/`assets`، وحدّث `recomplauncher.json` و `library.json` معاً (`verified: true` و `--play`). |
| **بهتان الألوان أو تحولها للرمادي الباهت عند تشغيل ألعاب الـ Recomp** | إدراج ألعاب SDR داخل قائمة `SmartHdrManager/config.json` مما يجبر ويندوز على تفعيل HDR لألعاب لا تدعمه. | أغلق `SmartHdrManager`، وأزل جميع ألعاب الـ SDR من `config.json` (أبقِ ألعاب Native HDR10 فقط)، وأطفئ Windows HDR أثناء تشغيل ألعاب الـ SDR. |
| **عدم ظهور مجموعة `Recomp Library` أو الأغلفة في Steam** | التعديل أثناء عمل `steam.exe`، أو التعديل في حساب غير نشط، أو الاكتفاء بملف `localconfig.vdf` دون تحديث ملفات التخزين السحابي الجديدة. | حدد الحساب النشط (`MostRecent = 1` في `loginusers.vdf`)، وأغلق `steam.exe` بالكامل، وحدّث `cloud-storage-namespace-1.json` و `.modified.json`، وضع الصور الأربع في `grid/`. |
| **عدم استجابة يد التحكم (Xbox / DualSense / Switch Pro) داخل اللعبة** | عدم تفعيل طبقة ترجمة المدخلات `Steam Input` للألعاب المضافة كـ Non-Steam Games. | اضبط `"UseSteamControllerConfig" "2"` لجميع معرّفات `appid` الخاصة بألعاب الـ Recomp داخل `localconfig.vdf` بعد إغلاق `steam.exe`. |

---

## 🤝 شكر وتقدير لمطوري الأدوات والبرامج المستخدمة (Third-Party Credits)

جميع البرامج والأدوات الجانبية والمكتبات المشار إليها في هذا الدليل تخضع لتراخيص مطوريها وجهاتها الأصلية (راجع ملف [**CREDITS.md**](../../CREDITS.md) للقائمة الكاملة):
- **أدوات الفهرسة والبحث خارج GitHub**: `Everything` & `es.exe` ([https://www.voidtools.com/](https://www.voidtools.com/)) *(by David Carpenter / voidtools — Freeware License)*.
- **أدوات الشاشة والـ HDR**: `SmartHdrManager` ([https://github.com/imniko/SmartHdrManager](https://github.com/imniko/SmartHdrManager)) *(by Developer / Maintainer `imniko` — MIT License)*.
- **منظومة البورتات واللانشر**: `RecompLauncher` ([https://recomplauncher.com](https://recomplauncher.com)) *(by Zexyen / RecompLauncher Team)*، و `N64Recomp` ([https://github.com/N64Recomp/N64Recomp](https://github.com/N64Recomp/N64Recomp)) *(by Mr-Wiseguy — MIT)*، و `XenonRecomp` / `UnleashedRecomp` ([https://github.com/hedge-dev/XenonRecomp](https://github.com/hedge-dev/XenonRecomp)) *(by hedge-dev — MIT / GPL-3.0)*، ومطورو مجتمع بورتات Switch / PS2 / PS3 / GameCube.
- **أدوات فك التشفير والاستخراج**: `hactool` ([https://github.com/SciresM/hactool](https://github.com/SciresM/hactool)) *(by SciresM — ISC License)* و `nstool` ([https://github.com/jakcron/nstool](https://github.com/jakcron/nstool)) *(by jakcron — MIT License)*.
- **التكامل مع المتاجر وأيدي التحكم**: `Valve Steam Client & Steam Input / VDF Format` ([https://store.steampowered.com/](https://store.steampowered.com/)) *(by Valve Corporation — Proprietary / Free Client)*.
- **المكتبات البرمجية والصوتية والرسومية وأدوات النظام**: `Python 3` ([https://www.python.org/](https://www.python.org/)) *(by Python Software Foundation — PSF License)*، و `Pillow (PIL Fork)` ([https://python-pillow.org/](https://python-pillow.org/)) *(by Jeffrey A. Clark / Alex Clark & Contributors — HPND / MIT-CMU License)*، و `libopus` ([https://opus-codec.org/](https://opus-codec.org/)) *(by Xiph.Org Foundation — BSD-3-Clause License)*، و `SDL2` ([https://www.libsdl.org/](https://www.libsdl.org/)) *(by Sam Lantinga & SDL Contributors — zlib License)*، و `Microsoft Windows Native Utilities (mklink / Robocopy / PowerShell / Registry)` *(by Microsoft Corporation — Windows OS Built-in Tools)*.
- **الترخيص والتواصل**: جميع الحقوق محفوظة © 2026 للمطور **`axxx503`** — مسموح ومجاني للاستخدام الشخصي غير الربحي، ويُمنع الاستخدام التجاري منعاً باتاً إلا بترخيص مكتوب (راجع [**LICENSE.md**](../../LICENSE.md) | [https://bio.site/V7dt1](https://bio.site/V7dt1) | `v7dtads@gmail.com` | [https://buymeacoffee.com/axxx503](https://buymeacoffee.com/axxx503)).
