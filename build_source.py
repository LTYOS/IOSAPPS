import json
import os

def main():
    apps_data = json.load(open("apps_data.json", encoding="utf-8"))
    apps = []
    for a in apps_data:
        if not a.get("bundle_id") or not a.get("versions"):
            print(f"skip invalid: {a.get('repo')}")
            continue

        valid_versions = []
        for v in a["versions"]:
            if not v.get("version") or not v.get("downloadURL") or not isinstance(v.get("size"), int):
                continue
            valid_versions.append({
                "version": v["version"],
                "date": v.get("date", ""),
                "downloadURL": v["downloadURL"],
                "size": v["size"],
            })
        if not valid_versions:
            print(f"skip invalid versions: {a.get('repo')}")
            continue

        name = a.get("name") or a.get("repo", "").split("/")[-1] or a.get("bundle_id", "")
        if not name:
            print(f"skip no name: {a.get('repo')}")
            continue

        # subtitle 已包含星标列表名（enrich_apps.py 已处理）
        subtitle = a.get("subtitle") or name
        if len(subtitle) > 200:
            subtitle = subtitle[:200]

        apps.append({
            "repo": a["repo"],
            "name": name,
            "bundleIdentifier": a["bundle_id"],
            "developerName": a["repo"].split("/")[0],
            "subtitle": subtitle,
            "localizedDescription": subtitle,
            "iconURL": a.get("icon_url", ""),
            "category": a.get("category", "utilities"),
            "versions": valid_versions,
        })

    base = f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', '')}/main"
    source = {
        "name": "林太一",
        "identifier": "com.lintaiyi.source",
        # 三个字段兼容：sourceicon（全小写）+ iconURL（驼峰）+ icon（驼峰）
        "sourceicon": f"{base}/source_icon.jpeg",
        "iconURL": f"{base}/source_icon.png",
        "icon": f"{base}/source_icon.jpeg",
        "apps": apps,
    }
    json.dump(source, open("apps.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"built apps.json with {len(apps)} apps")


if __name__ == "__main__":
    main()