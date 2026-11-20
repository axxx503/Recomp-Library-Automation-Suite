import json
import shutil
import sys
import time
from pathlib import Path

sys.path.append(r"C:\Users\<USER>\scripts")
import fix_steam_vdf

cfg = Path(r"C:\Program Files (x86)\Steam\userdata\<STEAM_ACCOUNT_ID>\config")
sc_path = cfg / "shortcuts.vdf"
d, _ = fix_steam_vdf.parse_vdf(sc_path.read_bytes())
sc = d["shortcuts"][1]

appids = [
    e["appid"][1] & 0xFFFFFFFF
    for _, (_, e) in sc.items()
    if e.get("tags", (0, {}))[1]
]
print(f"Collected {len(appids)} Recomp appids from shortcuts.vdf")

cs_dir = cfg / "cloudstorage"
cs_path = cs_dir / "cloud-storage-namespace-1.json"
mod_path = cs_dir / "cloud-storage-namespace-1.modified.json"

shutil.copy2(cs_path, cs_dir / "cloud-storage-namespace-1.json.bak_phase4")
cs_data = json.loads(cs_path.read_text(encoding="utf-8"))

# Remove any existing recomp-library entry and insert fresh one
cs_data = [item for item in cs_data if item[0] != "user-collections.recomp-library"]

now_ts = int(time.time())
max_ver = 1
for _, meta in cs_data:
    if isinstance(meta, dict) and "version" in meta:
        try:
            max_ver = max(max_ver, int(meta["version"]))
        except Exception:
            pass

col_value = json.dumps(
    {
        "id": "recomp-library",
        "name": "Recomp Library",
        "added": appids,
        "removed": [],
    },
    separators=(",", ":"),
)

new_entry = [
    "user-collections.recomp-library",
    {
        "key": "user-collections.recomp-library",
        "timestamp": now_ts,
        "value": col_value,
        "version": str(max_ver + 1),
        "conflictResolutionMethod": "custom",
        "strMethodId": "union-collections",
    },
]
cs_data.append(new_entry)
cs_path.write_text(json.dumps(cs_data, separators=(",", ":")), encoding="utf-8")

# Also update .modified.json
mod_data = []
if mod_path.exists():
    try:
        mod_data = json.loads(mod_path.read_text(encoding="utf-8"))
        if not isinstance(mod_data, list):
            mod_data = []
    except Exception:
        mod_data = []
mod_data = [x for x in mod_data if x != "user-collections.recomp-library"]
mod_data.append("user-collections.recomp-library")
mod_path.write_text(json.dumps(mod_data, separators=(",", ":")), encoding="utf-8")

print("Updated cloud-storage-namespace-1.json & .modified.json with Recomp Library collection!")
