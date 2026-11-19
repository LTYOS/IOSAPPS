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

        subtitle = a.get("subtitle") or a["name"]
        if len(subtitle) > 200:
            subtitle = subtitle[:200]

        apps.append({
            "repo": a["repo"],
            "bundleIdentifier": a["bundle_id"],
            "developerName": a["repo"].split("/")[0],
            "subtitle": subtitle,
            "localizedDescription": subtitle,
            "iconURL": a["icon_url"],
            "category": a.get("category", "utilities"),
            "versions": valid_versions,
        })

    base = f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', '')}/main"
    source = {
        "name": "林太一",
        "identifier": "com.lintaiyi.source",
        "iconURL": f"{base}/source_icon.png",
        "sourceIcon": f"{base}/source_icon.jpeg",
        "icon": f"{base}/source_icon.jpeg",
        "apps": apps,
    }
    json.dump(source, open("apps.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"built apps.json with {len(apps)} apps")


if __name__ == "__main__":
    main()