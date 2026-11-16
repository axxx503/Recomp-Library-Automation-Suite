<p align="right"><img src="../../assets/icon-03-steam.svg" width="52" align="absmiddle" alt="03-recomp-steam-sync.md"/> &nbsp; <img src="../../assets/agent-master-badge.svg" height="38" align="absmiddle" alt="AI Agent Playbook"/></p>

# الأداة 03: الربط الشامل مع Steam، توحيد الأسماء، توليد الأغلفة، وتفعيل Steam Input

🌐 **اللغة / Language:** **[English](../en/03-recomp-steam-sync.md)** | **العربية (Arabic)** | **[⬅️ العودة إلى الصفحة الرئيسية](../../README.ar.md)**

---

## 🛠️ الأدوات والاعتماديات المطلوبة (Prerequisites)

| الأداة / البرنامج | دورها في هذه الأداة | الرابط الرسمي / التثبيت |
| :--- | :--- | :--- |
| **Steam Client** | المنصة المستهدفة لإضافة اختصارات الألعاب، صور `grid`، مجموعة `Recomp Library`، وتفعيل `Steam Input`. | [store.steampowered.com](https://store.steampowered.com) |
| **RecompLauncher** | مصدر قائمة الألعاب الجاهزة (`library.json`) وكتالوج الأسماء والصور الرسمية (`cache/pc-catalog.json`). | [recomplauncher.com](https://recomplauncher.com) |
| **Everything (`es.exe`)** | يُستخدم عند الحاجة للتحقق السريع من مسارات الأيقونات أو الملفات التنفيذية. | [voidtools.com](https://www.voidtools.com/) |
| **SmartHdrManager** | يبقى خالياً من ألعاب الـ SDR لضمان ألوان طبيعية عند التشغيل من داخل Steam. | [GitHub: SmartHdrManager](https://github.com/imniko/SmartHdrManager) |
| **hactool وأدوات المفاتيح** | تُستخدم في مرحلة البناء السابقة قبل التصدير إلى Steam. | [GitHub: SciresM/hactool](https://github.com/SciresM/hactool) |
| **Python 3.10+** | قراءة وكتابة `shortcuts.vdf` الثنائي، وتحديث `localconfig.vdf` و `cloud-storage-namespace-1.json`، وتحميل الأغلفة توازيّاً. | [python.org](https://www.python.org/) |

---

## 🚦 الخطوة 0 (Step 0): بوابة التحقق التفاعلي من العتاد وحساب Steam النشط (تُنفَّذ أولاً)

> **تعليمات إلزامية للوكيل الذكي:** قبل لمس أي ملف من ملفات Steam، شغّل سكربت الفحص أدناه لعرض المعالج والرام و**الفصل الصريح بين كرت الشاشة المدمج iGPU والكرت المنفصل dGPU** مع عرض معرّف حساب Steam النشط (`AccountID`)، ثم **اطلب تأكيد المستخدم**. ممنوع لمس مجلد `steamapps\common` أو حذف أي اختصار موجود مسبقاً.

### 0.1 سكربت فحص العتاد واكتشاف حساب Steam النشط (`loginusers.vdf`)
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

### 0.2 الأسئلة الإلزامية للمستخدم قبل البدء
1. **تأكيد العتاد والحساب**: تأكيد **كرت الشاشة المنفصل (dGPU)** ومعرّف حساب Steam النشط (`AccountID`).
2. **`<RECOMP_LIB_DIR>` و `library.json`**: تأكيد مسار مكتبة `RecompLauncher`.
3. **صيغة التسمية والمجموعة**: تأكيد إضافة الألعاب تحت مجموعة **`Recomp Library`** بالصيغة الموحدة **`<الاسم الحقيقي الكامل للعبة> (<اسم مشروع الريكومب>)`**.

---

## 🔒 الخطوة 1: إغلاق Steam بالكامل وأخذ نسخ احتياطية (`.bak`)

يعيد Steam كتابة ملفاته من الذاكرة عند الإغلاق؛ لذا يجب إغلاقه أولاً:
1. إيقاف `steam.exe` و `steamwebhelper.exe`:
   ```powershell
   taskkill /F /IM steam.exe
   taskkill /F /IM steamwebhelper.exe
   ```
2. حفظ نسخ احتياطية (`.bak_recomp`) من:
   - `C:\Program Files (x86)\Steam\userdata\<ACTIVE_ACCOUNT_ID>\config\shortcuts.vdf`
   - `C:\Program Files (x86)\Steam\userdata\<ACTIVE_ACCOUNT_ID>\config\localconfig.vdf`
   - `C:\Program Files (x86)\Steam\userdata\<ACTIVE_ACCOUNT_ID>\config\cloudstorage\cloud-storage-namespace-1.json`

---

## 🏷️ الخطوة 2: توحيد الأسماء `<الاسم الحقيقي للعبة> (<اسم الريكومب>)` وتحديث `shortcuts.vdf`

1. **استخراج الأسماء الرسمية من كتالوج `pc-catalog.json`**:
   - اقرأ `%APPDATA%\com.recomplauncher.app\cache\pc-catalog.json` لاستخراج اسم اللعبة الكامل (`game` أو `about.name`) واسم مشروع الريكومب (`name`).
   - وحّد حقل `AppName` لجميع الألعاب بالصيغة: **`<Real Game Title> (<Recomp Project Name>)`** (مثل: `Pokémon Legends: Arceus (Arceuszada)`، `Bayonetta 3 (Witch Time)`، `Gravity Rush 2 (GR2port)`، `The Legend of Zelda: Breath of the Wild (Savage Wind)`).
2. **الحفاظ على معرّف `appid` وبنية VDF الثنائية القياسية**:
   - يُحسب `appid` القياسي بـ CRC32 للـ `Exe` المقتبس + `AppName` مع رفع البت الأعلى (`| 0x80000000`).
   - إذا كان الاختصار موجوداً مسبقاً في `shortcuts.vdf`، **حافظ على نفس الـ `appid` المسجل له** حتى لا ينكسر ربطه في `localconfig.vdf` والمجموعات، مع تسجيل المعرّف الجديد أيضاً للأغلفة والـ Steam Input.
   - اضبط `StartDir` بدون علامات تنصيص ومنتهياً بـ `\`، و `AllowOverlay = 1`، و `AllowDesktopConfig = 1`، و `sortas = full_name`، و `tags = {'0': 'Recomp Library'}`.

---

## 🖼️ الخطوة 3: توليد صور الأغلفة والبنرات والأيقونات في مجلد `grid`

لإزالة المربعات الزرقاء الفارغة في مكتبة Steam:
1. افحص كاش الصور المحلي `%APPDATA%\com.recomplauncher.app\cache\img\<sha256(url)[:32]>` أولاً، وحمّل أي صورة غير موجودة من روابط `cover` و `hero` و `logo` و `icon` في `pc-catalog.json` توازيّاً (`ThreadPoolExecutor(16)`).
2. احفظ الصور داخل `C:\Program Files (x86)\Steam\userdata\<ACTIVE_ACCOUNT_ID>\config\grid\` لكل `appid` (بصيغة Unsigned 32-bit integer):
   - `<appid>p.png`: الغلاف الطولي الأساسي في شبكة المكتبة (الأهم).
   - `<appid>_hero.png`: البانر العريض في صفحة اللعبة.
   - `<appid>.png`: الصورة الأفقية المصغرة.
   - `<appid>_logo.png`: الشعار الشفاف.
   - `<appid>_icon.png`: أيقونة اللعبة (مع كتابة مسارها الكامل في حقل `icon` داخل `shortcuts.vdf`).

---

## 🎮 الخطوة 4: إنشاء مجموعة `Recomp Library` السحابية وتفعيل `Steam Input` إجبارياً

1. **إنشاء المجموعة في `cloud-storage-namespace-1.json` و `cloud-storage-namespace-1.modified.json`**:
   - في واجهة Steam الحديثة (بعد تفعيل `collection-bootstrap-complete`)، يتجاهل Steam حقل `tags` في `shortcuts.vdf` ويقرأ المجموعات حصراً من `cloud-storage-namespace-1.json`.
   - وإذا لم تُسجَّل المجموعة أيضاً في `cloud-storage-namespace-1.modified.json` مع رفع رقم النسخة في `cloud-storage-namespaces.json`، فسيقوم Steam Cloud بمسح التعديل المحلي عند تسجيل الدخول!
   - **الحل**: أضف المفتاح `user-collections.rl-recomplauncher` (`"name": "Recomp Library"`) متضمناً جميع معرّفات `appid` (بالصيغتين Unsigned `u32` و Signed `i32`) في **كلا الملفين** `cloud-storage-namespace-1.json` و `cloud-storage-namespace-1.modified.json` وارفَع رقم الإصدار في `cloud-storage-namespaces.json`.
2. **تفعيل `Steam Input` (`UseSteamControllerConfig = 2`) في `localconfig.vdf`**:
   - فعّل دعم جميع الأيدي على مستوى النظام في `localconfig.vdf`:
     ```
     "SteamController_XBoxSupport"		"1"
     "SteamController_SwitchSupport"		"1"
     "SteamController_GenericGamepadSupport"		"1"
     "SteamController_PSSupport"		"2"
     ```
   - تحت قسم `"apps"` في `localconfig.vdf`، أضف `"UseSteamControllerConfig" "2"` لكل `appid` خاص بألعاب `Recomp Library`.
3. **إعادة التشغيل والتحقق بعد 5 ثوانٍ**:
   - شغّل `steam.exe` وانتظر 5 ثوانٍ، ثم تحقق برمجياً من بقاء `shortcuts.vdf` ومجموعة `Recomp Library` وملفات `<appid>p.png` سليمة 100%.

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
