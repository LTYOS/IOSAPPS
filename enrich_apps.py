import json
import os
import re
import plistlib
import tempfile
import tomllib
import urllib.request
import zipfile

TOKEN = os.environ.get("GH_TOKEN", "")
MAX_BYTES = 300 * 1024 * 1024

def api_get(url):
    req = urllib.request.Request(url)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def extract(ipa_url):
    with tempfile.NamedTemporaryFile(suffix=".ipa", delete=False) as tmp:
        p = tmp.name
    try:
        req = urllib.request.Request(ipa_url)
        if TOKEN:
            req.add_header("Authorization", f"Bearer {TOKEN}")
        with urllib.request.urlopen(req, timeout=120) as r:
            size = int(r.headers.get("Content-Length", 0))
            if size and size > MAX_BYTES:
                raise ValueError("too large")
            open(p, "wb").write(r.read())
        with zipfile.ZipFile(p) as z:
            pl = next(n for n in z.namelist()
                      if n.startswith("Payload/") and n.endswith(".app/Info.plist")
                      and n.count("/") == 2)
            info = plistlib.load(z.open(pl))
            bid = info.get("CFBundleIdentifier", "")
            name = info.get("CFBundleDisplayName") or info.get("CFBundleName", "")
            ver = info.get("CFBundleShortVersionString", "")
            icons = [n for n in z.namelist() if re.search(r"AppIcon.*\.png$", n, re.I)]
            if not icons:
                icons = [n for n in z.namelist() if re.search(r"icon.*\.png$", n, re.I)]
            icon_data = None
            if icons:
                icons.sort(key=lambda n: z.getinfo(n).file_size, reverse=True)
                icon_data = z.read(icons[0])
            return bid, name, ver, icon_data
    finally:
        if os.path.exists(p):
            os.unlink(p)

def main():
    cfg = tomllib.load(open("config.toml", "rb"))
    os.makedirs("icons", exist_ok=True)
    out = []
    for a in cfg.get("app", []):
        repo = a["repo"]
        try:
            rel = api_get(f"https://api.github.com/repos/{repo}/releases/latest")
        except Exception as e:
            print(f"skip {repo}: {e}")
            continue
        ipa = next((x for x in rel.get("assets", []) if x["name"].lower().endswith(".ipa")), None)
        if not ipa:
            print(f"no ipa {repo}")
            continue
        try:
            bid, name, ver, icon = extract(ipa["browser_download_url"])
        except Exception as e:
            print(f"extract fail {repo}: {e}")
            continue
        icon_url = ""
        if icon:
            fn = re.sub(r"[^A-Za-z0-9._-]", "_", bid) + ".png"
            open(f"icons/{fn}", "wb").write(icon)
            icon_url = f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', '')}/main/icons/{fn}"
        out.append({
            "repo": repo,
            "bundle_id": bid or a.get("bundle_id", ""),
            "name": name or a.get("name", ""),
            "version": ver,
            "date": rel.get("published_at", ""),
            "downloadURL": ipa["browser_download_url"],
            "size": ipa["size"],
            "icon_url": icon_url or a.get("icon_url", ""),
            "subtitle": (rel.get("body") or "").strip().replace("\n", " ")[:200],
            "category": a.get("category", "utilities"),
        })
        print(f"ok {repo} -> {name} {ver} ({bid})")
    json.dump(out, open("apps_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"enriched {len(out)} apps")

if __name__ == "__main__":
    main()
