import json
import os
import re
import tomllib
import urllib.error
import urllib.request
import time

TOKEN = os.environ.get("GH_TOKEN", "")
SNAPSHOT = "previous_stars.json"
CONFIG = "config.toml"


def api_get(url):
    req = urllib.request.Request(url)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                reset = e.headers.get("X-RateLimit-Reset")
                wait = 30 if not reset else max(5, int(reset) - int(time.time()))
                print(f"rate limited ({e.code}), retrying in {wait}s")
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise
    return None


def get_starred():
    repos, page = [], 1
    while True:
        resp = api_get(f"https://api.github.com/user/starred?per_page=100&page={page}")
        if not resp:
            break
        repos.extend(r["full_name"] for r in resp)
        page += 1
    return repos


def dump_config(cfg, apps):
    lines = [
        "[source]",
        f'name = "{cfg["source"]["name"]}"',
        f'identifier = "{cfg["source"]["identifier"]}"',
        f'icon_url = "{cfg["source"].get("icon_url", "")}"',
        "",
    ]
    for a in apps:
        lines.append("[[app]]")
        for k in ("repo", "bundle_id", "name", "subtitle", "category", "icon_url", "star_list"):
            v = str(a.get(k, "")).replace("\\", "\\\\").replace('"', '\\"')
            if v:
                lines.append(f'{k} = "{v}"')
        lines.append("")
    return "\n".join(lines)


def main():
    current = get_starred()
    prev = set(json.load(open(SNAPSHOT))) if os.path.exists(SNAPSHOT) else set()
    current_set = set(current)
    added = current_set - prev
    removed = prev - current_set

    with open(CONFIG, "rb") as f:
        cfg = tomllib.load(f)
    apps = {a["repo"]: a for a in cfg.get("app", [])}

    for repo in added:
        apps[repo] = {
            "repo": repo,
            "bundle_id": "",
            "name": "",
            "subtitle": "",
            "category": "utilities",
            "icon_url": "",
            "star_list": "",  # 手动在 config.toml 里配置
        }
        print(f"+ {repo}")
    for repo in removed:
        apps.pop(repo, None)
        print(f"- {repo}")

    with open(CONFIG, "w", encoding="utf-8") as f:
        f.write(dump_config(cfg, list(apps.values())))
    json.dump(sorted(current), open(SNAPSHOT, "w"), indent=2)
    print(f"added={len(added)} removed={len(removed)} total={len(apps)}")


if __name__ == "__main__":
    main()