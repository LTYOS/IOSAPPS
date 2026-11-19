import json
import os
import re
import urllib.parse
import urllib.request

def clean_text(text):
    if not text:
        return ""
    # 去掉 Markdown 标题符号
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    # 去掉 Markdown 列表符号
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.M)
    # 把回车、换行、制表符全部换成空格
    text = re.sub(r"[\r\n\t]+", " ", text)
    # 合并连续空格
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

from freetrans import SyncTranslator

def translate(text):
    if not text or not text.strip():
        return ""
    try:
        with SyncTranslator() as t:
            result = t.translate(text[:300], dest="zh-CN")
            return result.text
    except Exception as e:
        print(f"translate fail: {e}")
        return ""

def main():
    apps_data = json.load(open("apps_data.json", encoding="utf-8"))
    apps = []
    for a in apps_data:
        # 过滤无效条目
        if not a.get("bundle_id") or not a.get("version") or not a.get("downloadURL"):
            print(f"skip invalid: {a.get('repo')}")
            continue
        if not isinstance(a.get("size"), int):
            print(f"skip invalid size: {a.get('repo')}")
            continue

        subtitle = translate(clean_text(a["subtitle"]))[:120]
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
        "sourceIcon": f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', '')}/main/source_icon.png",
        "apps": apps,
    }
    json.dump(source, open("apps.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"built apps.json with {len(apps)} apps")

if __name__ == "__main__":
    main()
