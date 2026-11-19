# 我的软件源

## 订阅地址
**林太一**
```
https://raw.githubusercontent.com/LTYOS/IOSAPPS/main/apps.json
```

##整体架构

| 文件 | 说明 |
|---|---|
| `.github/workflows/sync.yml` |   ← 定时任务，串联三个脚本 |
| `sync_stars.py` |                ← 脚本1：同步星标增删 → 更新 config.toml |
| `enrich_apps.py` |               ← 脚本2：下载 IPA 读信息 → 生成 apps_data.json + icons/ |
| `build_source.py` |              ← 脚本3：翻译简介 + 组装源 → 生成 apps.json |
| `config.toml` |                 ← 仓库清单（由 sync_stars.py 自动维护） |
| `previous_stars.json` |          ← 上次星标快照（由 sync_stars.py 自动维护） |
| `apps_data.json` |               ← 富化后的应用数据（由 enrich_apps.py 自动生成） |
| `apps.json` |                    ← 最终源文件（由 build_source.py 自动生成） |
| `icons/` |                       ← 从 IPA 提取的图标（由 enrich_apps.py 自动生成） |
| `source_icon.png` |              ← 源主图标（你需要手动放一张） |

##每个文件的作用总结

| 文件 | 谁生成 |	作用 |
|---|---|
| `config.toml` |	你创建初始段，sync_stars.py 自动维护	` |源信息 + 追踪的仓库清单|
| `previous_stars.json` |	sync_stars.py` |	上次星标快照，用于对比增删|
| `sync_stars.py` |	你创建` |	星标增删同步|
| `enrich_apps.py` |	你创建` |	下载 IPA，提取名称/ID/版本/图标|
| `build_source.py` |	你创建` |	翻译简介，组装最终源文件|
| `apps_data.json` |	enrich_apps.py` |	中间数据，供 build 使用|
| `apps.json` |	build_source.py` |	最终源文件，签名工具读这个|
| `icons/` |	enrich_apps.py` |	从 IPA 提取的图标|
| `source_icon.png` |	你手动上传` |	源主图标|
| `.github/workflows/sync.yml` |	你创建` |	定时串联三个脚本并提交|
