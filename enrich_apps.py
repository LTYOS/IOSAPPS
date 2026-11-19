import json
import os
import re
import plistlib
import tempfile
import tomllib
import time
import urllib.error
import urllib.request
import zipfile

TOKEN = os.environ.get("GH_TOKEN", "")
MAX_BYTES = 300 * 1024 * 1024


def api_get(url, retries=3):
    req = urllib.request.Request(url)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                reset = e.headers.get("X-RateLimit-Reset")
                wait = 30 if not reset else max(5, int(reset) - int(time.time()))
                print(f"rate limited ({e.code}) on {url}, retrying in {wait}s")
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    return None


def extract(ipa_url):
    with tempfile.NamedTemporaryFile(suffix=".ipa", delete=False) as tmp:
        p = tmp.name
    try:
        req = urllib.request.Request(ipa_url)
        if TOKEN:
            req.add_header("Authorization", f"Bearer {TOKEN}")
        with urllib.request.urlopen(req, timeout=180) as r:
            size = int(r.headers.get("Content-Length", 0) or 0)
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


def get_recent_ipa_releases(repo, limit=3):
    """返回该仓库最近 limit 个带 IPA 附件的 Release (按发布时间倒序)。"""
    releases = api_get(f"https://api.github.com/repos/{repo}/releases?per_page=10") or []
    result = []
    for rel in releases:
        if rel.get("draft"):
            continue
        ipa = next((a for a in rel.get("assets", []) if a["name"].lower().endswith(".ipa")), None)
        if not ipa:
            continue
        result.append((rel, ipa))
        if len(result) >= limit:
            break
    return result


def find_repo_icon(repo):
    """在仓库根目录找常见图标文件作为兜底"""
    try:
        contents = api_get(f"https://api.github.com/repos/{repo}/contents")
    except Exception:
        return ""
    names = {item["name"].lower(): item["path"] for item in contents if item["type"] == "file"}
    for candidate in ("icon.png", "appicon.png", "logo.png", "icon.jpg"):
        if candidate in names:
            return f"https://raw.githubusercontent.com/{repo}/main/{names[candidate]}"
    return ""


def get_repo_meta(repo):
    """一次 API 调用拿 repo 的 description（用于简介）。"""
    try:
        repo_info = api_get(f"https://api.github.com/repos/{repo}")
        return (repo_info.get("description") or "").strip() if repo_info else ""
    except Exception:
        return ""


def main():
    cfg = tomllib.load(open("config.toml", "rb"))
    os.makedirs("icons", exist_ok=True)
    out = []
    for a in cfg.get("app", []):
        repo = a["repo"]
        rels = get_recent_ipa_releases(repo, limit=3)
        if not rels:
            print(f"no ipa {repo}")
            continue

        # 用最新那个 Release 提取名称、Bundle ID、图标
        latest_rel, latest_ipa = rels[0]
        try:
            bid, name, ver, icon = extract(latest_ipa["browser_download_url"])
        except Exception as e:
            print(f"extract fail {repo}: {e}")
            continue

        # 图标：优先 IPA 内部提取，失败则去仓库根目录找
        icon_url = ""
        if icon:
            fn = re.sub(r"[^A-Za-z0-9._-]", "_", bid) + ".png"
            open(f"icons/{fn}", "wb").write(icon)
            icon_url = f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', '')}/main/icons/{fn}"
        else:
            icon_url = find_repo_icon(repo) or a.get("icon_url", "")

        # 简介：星标列表名 + 仓库描述
        star_list = a.get("star_list", "")
        repo_desc = get_repo_meta(repo) or (latest_rel.get("body") or "").strip().replace("\n", " ")[:200]
        if star_list and repo_desc:
            subtitle = f"📋 {star_list} | {repo_desc}"
        elif star_list:
            subtitle = f"📋 {star_list}"
        elif repo_desc:
            subtitle = repo_desc
        else:
            subtitle = a.get("subtitle", "")

        versions = []
        for rel, ipa in rels:
            v = re.search(r"(\d+\.\d+(?:\.\d+)?)", ipa["name"])
            version = v.group(1) if v else rel.get("tag_name", "").lstrip("v")
            if not version:
                continue
            versions.append({
                "version": version,
                "date": rel.get("published_at", ""),
                "downloadURL": ipa["browser_download_url"],
                "size": ipa["size"],
            })

        if not versions:
            continue

        out.append({
            "repo": repo,
            "bundle_id": bid or a.get("bundle_id", ""),
            "name": name or a.get("name", ""),
            "icon_url": icon_url or a.get("icon_url", ""),
            "subtitle": subtitle,
            "category": a.get("category", "utilities"),
            "versions": versions,
        })
        print(f"ok {repo} -> {name} ({len(versions)} versions)")

    json.dump(out, open("apps_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"enriched {len(out)} apps")


if __name__ == "__main__":
    main()