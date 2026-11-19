import json
import os
import urllib.parse
import urllib.request

def translate(text):
    if not text or not text.strip():
        return ""
    try:
        q = urllib.parse.quote(text[:400])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=zh-CN&dt=t&q={q}"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
        return "".join(seg[0] for seg in data[0] if seg[0])
    except Exception as e:
        print(f"translate fail: {e}")
        return text

def main():
    apps_data = json.load(open("apps_data.json", encoding="utf-8"))
    apps = []
    for a in apps_data:
        subtitle = translate(a["subtitle"])[:120]
        apps.append({
            "name": a["name"],
            "bundleIdentifier": a["bundle_id"],
            "developerName": a["repo"].split("/")[0],
            "subtitle": subtitle,
            "localizedDescription": subtitle,
            "iconURL": a["icon_url"],
            "category": a.get("category", "utilities"),
            "versions": [{
                "version": a["version"],
                "date": a["date"],
                "downloadURL": a["downloadURL"],
                "size": a["size"],
            }],
        })
    source = {
        "name": "林太一",
        "identifier": "com.lintaiyi.source",
        "iconURL": f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', '')}/main/source_icon.png",
        "apps": apps,
    }
    json.dump(source, open("apps.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"built apps.json with {len(apps)} apps")

if __name__ == "__main__":
    main()
