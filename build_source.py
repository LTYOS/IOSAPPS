import json
import os
import re
import time
import urllib.parse
import urllib.request

def clean_text(text):
    if not text:
        return ""
    # 去掉 Markdown 标题符号
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    # 去掉 Markdown 列表符号
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.M)
    # 去掉 Markdown 加粗、斜体、行内代码符号
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"`+", "", text)
    # 把回车、换行、制表符全部换成空格
    text = re.sub(r"[\r\n\t]+", " ", text)
    # 合并连续空格
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

from freetrans import SyncTranslator

def translate(text):
    if not text or not text.strip():
        return ""
    for attempt in range(2):
        try:
            with SyncTranslator() as t:
                result = t.translate(text[:300], dest="zh-CN")
                time.sleep(1)  # 每次成功后等 1 秒，降低限流概率
                return result.text
        except Exception as e:
            print(f"translate fail (attempt {attempt+1}): {e}")
            if attempt == 0:
                time.sleep(3)  # 失败后等 3 秒再重试
    return ""  # 两次都失败，返回空，由调用方兜底

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

        subtitle = translate(clean_text(a["subtitle"]))[:120]
        if not subtitle:
            subtitle = a["name"]

        apps.append({
            "name": a["name"],
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
