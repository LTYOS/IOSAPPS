# 林太一 · IOSAPPS

一个自动更新的 AltStore / SideStore 源。星标一个 GitHub 仓库，源里就会自动出现它的 IPA；取消星标，源里就移除。全流程由 GitHub Actions 定时驱动，无需人工干预。

- **源地址**：`https://raw.githubusercontent.com/LTYOS/IOSAPPS/main/apps.json`
- **源标识**：`com.lintaiyi.source`
- **当前收录**：23 个应用（随星标实时变动）
- **更新频率**：每 6 小时一次（`0 */6 * * *`），也可在 Actions 页面手动触发

---

## 整体架构

### 数据流

```
GitHub 星标列表
      │
      │  ①  sync_stars.py
      ▼
config.toml  ──────────┐    previous_stars.json（星标快照，用于 diff）
      │                │
      │  ②  enrich_apps.py
      │     ├─ 下载 IPA，解析 Info.plist 拿 Bundle ID / 名称 / 版本 / 图标
      │     ├─ 抓 repo description 作为简介
      │     └─ 收集最近 3 个带 IPA 附件的 Release
      ▼
apps_data.json  +  icons/*.png
      │
      │  ③  build_source.py
      │     └─ 过滤无效条目，组装 AltStore 源格式
      ▼
apps.json  ──────────►  签名工具 / AltStore 读取
      │
      │  ④  Git Commit & Push
      ▼
main 分支
```

### 三层职责分离

| 层 | 脚本 | 职责 | 特点 |
|---|---|---|---|
| **同步层** | `sync_stars.py` | 星标 ↔ `config.toml` 增删同步 | 轻量，只 diff 不下载；幂等 |
| **富化层** | `enrich_apps.py` | IPA 元数据提取、图标归档、简介生成 | 最重，要下载 IPA；失败可跳过重试 |
| **输出层** | `build_source.py` | 数据校验 + AltStore 格式序列化 | 纯计算，无网络 |

这种分层的好处是：星标列表变化频繁但轻量，IPA 提取缓慢但可缓存。任何一层失败都不会污染其他层的数据。

### 配置驱动的设计

`config.toml` 是唯一的手工可编辑文件，也是整个流水线的事实数据源：

- 星标新增的仓库会自动写入这里（占位条目）
- 想给某个 app 加 `bundle_id`、`name`、`category`、`icon_url` 等元数据，在这里改
- `enrich_apps.py` 会自动补全占位条目，已有值不被覆盖
- 取消星标的仓库从这里自动删除

### 容错策略

| 环节 | 失败表现 | 处理方式 |
|---|---|---|
| GitHub API 403/429 | 限流 | 读取 `X-RateLimit-Reset`，最多重试 3 次 |
| 网络抖动 | 超时 | 指数退避重试（1s / 2s / 4s） |
| IPA 超过 300 MB | 跳过 | 该 app 本轮不更新，下次再试 |
| Release 无 IPA 附件 | 跳过 | 继续尝试更早的 Release（最多 3 个） |
| 图标提取失败 | 降级 | 回退到仓库根目录找 `icon.png` 等候选文件 |
| 单 app 数据无效 | 跳过 | `build_source.py` 过滤，`apps.json` 其余部分正常输出 |
| 工作流整体失败 | 开 issue | `⚠️ Auto-sync failed: <workflow> #<run_number>`，带 `automation` + `sync-failure` 标签 |

---

## 文件说明

### 脚本

| 文件 | 作用 |
|---|---|
| **`sync_stars.py`** | 拉取 GitHub 星标列表（分页），与 `previous_stars.json` 快照 diff，把新增/移除同步到 `config.toml` 的 `[[app]]` 条目。新增的仓库写入占位条目（只有 `repo` + `category`），后续由 `enrich_apps.py` 补全。最后更新快照。 |
| **`enrich_apps.py`** | 遍历 `config.toml` 里的每个 app：下载最新 IPA 到临时文件 → 用 `plistlib` 解析 `Payload/*.app/Info.plist` 拿 `CFBundleIdentifier` / `CFBundleDisplayName` / `CFBundleShortVersionString` → 从 IPA 内提取最大尺寸的 `AppIcon*.png` 存入 `icons/` → 抓 repo description 或 Release body 作为简介 → 收集最近 3 个带 IPA 附件的 Release（含 `version` / `date` / `downloadURL` / `size`）→ 输出 `apps_data.json`。 |
| **`build_source.py`** | 读取 `apps_data.json`，校验 `bundle_id` / `versions` / `name` 非空，过滤掉无效条目 → 序列化成 AltStore / SideStore 源格式（含 `name` / `bundleIdentifier` / `subtitle` / `localizedDescription` / `iconURL` / `versions[]`）→ 输出 `apps.json`。 |

### 数据文件

| 文件 | 作用 |
|---|---|
| **`config.toml`** | 核心配置。`[source]` 定义源名称与标识；每个 `[[app]]` 描述一个应用的仓库与可选元数据（`bundle_id` / `name` / `subtitle` / `category` / `icon_url`）。由 `sync_stars.py` 维护，可手工编辑补全元数据。 |
| **`previous_stars.json`** | 上一次同步的星标快照（仓库全名数组）。用于 diff 判断本次是新增还是移除，避免每次全量重写。 |
| **`apps_data.json`** | `enrich_apps.py` 的中间产物。每个 app 的完整富化结果（bundle id、名称、图标路径、简介、全部版本列表）。`build_source.py` 的输入。 |
| **`apps.json`** | **最终交付物**。AltStore / SideStore 源文件，签名工具直接读取这个地址。 |
| **`icons/`** | 从 IPA 内提取的应用图标（PNG），文件名是清洗后的 bundle id。同时作为 `apps.json` 里 `iconURL` 的引用目标。 |
| **`source_icon.png`** / **`source_icon.jpeg`** | 源图标，供签名工具在源列表里展示。 |

### 工作流

| 文件 | 作用 |
|---|---|
| **`.github/workflows/sync.yml`** | 定时任务编排。触发条件：`cron: 0 */6 * * *` 或手动 `workflow_dispatch`。步骤：checkout → 装 Python 3.11 → 同步星标 → 富化 IPA → 构建源 → 提交推送 → （失败时）自动开 issue 通知。需要 Actions secret `PAT_TOKEN`（`read:user` scope）用于读取星标列表，`GH_TOKEN` 由 `github.token` 自动提供。 |

---

## 使用方式

### 添加应用

在 GitHub 上星标目标仓库即可。最多 6 小时内源里就会出现（手动触发更快）。

### 移除应用

取消星标即可，下一个同步周期自动移除。

### 补充元数据

`sync_stars.py` 新增的条目只有 `repo` 字段，`enrich_apps.py` 会自动从 IPA 里提取 bundle id、名称、图标。如果想手动指定，在 `config.toml` 里加对应字段：

```toml
[[app]]
repo = "owner/repo"
bundle_id = "com.example.app"
name = "示例应用"
category = "games"
icon_url = "https://example.com/icon.png"
```

已有的值不会被 `enrich_apps.py` 覆盖。

### 手动触发更新

Actions 页面 → **Sync stars** → **Run workflow** → 选择 `main` 分支 → 确认。

---

## 前置条件

1. **Actions secret `PAT_TOKEN`**：一个带 `read:user` scope 的 Personal Access Token。没有它 `sync_stars.py` 会因 401 失败。
2. **源仓库 public**：`apps.json` 通过 `raw.githubusercontent.com` 提供，签名工具要能匿名访问。

---

## 变更历史

| 时间 | 变更 |
|---|---|
| 2026-11 | 初始化：星标自动同步 + IPA 富化 + AltStore 源生成 |
| 2026-11 | `build_source.py` 补充 `name` 字段（修复签名工具显示"未命名应用"） |
| 2026-11 | `sync.yml` 移除无用的 `pip install freetrans-py` 步骤 |