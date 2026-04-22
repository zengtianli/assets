# CLAUDE.md — assets

静态站点 `assets.tianlizeng.cloud` · 理财笔记公开版。

## 仓库性质

- **内容源**：`~/Dev/content/investment/docs/*.md`（private repo）
- **过滤规则**：frontmatter `public: true` 才被渲染。防误泄 PII
- **产物**：`site/index.html` + `site/<slug>/index.html` 静态 HTML
- **部署**：VPS `/var/www/assets` (nginx)
- **URL**：https://assets.tianlizeng.cloud

## 目录

| 文件 | 作用 |
|---|---|
| `generate.py` | 跨仓读 md → 渲染。按 frontmatter `group` 在首页分 4 组 |
| `deploy.sh` | rsync 到 VPS + 验证 |
| `site-navbar.html` | 从 `~/Dev/devtools/lib/templates/` 同步（`/navbar-refresh`） |
| `site-content.css` | 同上 |
| `site-header.html` | 本站专属面包屑/标题 |
| `site/` | 生成产物（gitignore? 这里暂时 track） |

## 常用命令

```bash
# 本地预览
cd ~/Dev/assets && python3 generate.py && open site/index.html

# 部署
bash deploy.sh

# 新增一篇公开文
# 1. 在 ~/Dev/content/investment/docs/<slug>.md 顶部加 frontmatter：
#    ---
#    public: true
#    title: 文章标题
#    group: forex | invest | hk-bank | strategy
#    abstract: 一句话摘要（首页卡片显示）
#    order: 10  # 可选，首页排序
#    ---
# 2. cd ~/Dev/assets && bash deploy.sh
```

## 新增分组

改 `generate.py` 中的 `GROUPS` 常量，或在 group yaml 里加一行（视实现而定）。

## SSOT

- 分组 key（forex / invest / hk-bank / strategy）与首页分组标题在本 repo `generate.py` 定义
- navbar 入口在 `~/Dev/tools/configs/menus/navbar.yaml` → content / 投资 section
- 子域登记在 `~/Dev/website/lib/services.ts` → "内容" group
