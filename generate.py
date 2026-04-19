#!/usr/bin/env python3
"""assets — 理财笔记公开版静态站生成器。

跨仓读 ~/Dev/international-assets/docs/*.md，只渲染带 frontmatter `public: true` 的文章。
产物：
  site/index.html           — 首页（4 分组卡片）
  site/<slug>/index.html    — 单篇文章页
"""

import html
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: 需要 PyYAML。uv pip install --system --break-system-packages pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import markdown as md_lib
except ImportError:
    print("ERROR: 需要 markdown。uv pip install --system --break-system-packages markdown", file=sys.stderr)
    sys.exit(1)


SCRIPT_DIR = Path(__file__).parent
DOCS_DIR = Path.home() / "Dev" / "international-assets" / "docs"
SITE_DIR = SCRIPT_DIR / "site"

GROUPS = [
    {"key": "forex",    "title": "换汇",       "icon": "💱", "color": "#0071E3"},
    {"key": "invest",   "title": "投资",       "icon": "📈", "color": "#16a34a"},
    {"key": "hk-bank",  "title": "香港银行",   "icon": "🏦", "color": "#ea580c"},
    {"key": "strategy", "title": "策略分析",   "icon": "🧭", "color": "#7c3aed"},
]


def _load(name: str) -> str:
    p = SCRIPT_DIR / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


NAVBAR_HTML = _load("site-navbar.html")
SITE_HEADER_HTML = _load("site-header.html")
SITE_CONTENT_CSS = _load("site-content.css")


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata dict, body). Empty dict if no frontmatter."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    body = text[m.end():]
    return (meta if isinstance(meta, dict) else {}), body


def strip_nav_line(body: str) -> str:
    """Remove '> 隶属：[国际资产配置体系](../README.md)' style navigation line."""
    lines = body.splitlines()
    cleaned = []
    skipped_nav = False
    for line in lines:
        stripped = line.strip()
        if not skipped_nav and stripped.startswith("> 隶属"):
            skipped_nav = True
            continue
        cleaned.append(line)
    # trim leading empty lines
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    return "\n".join(cleaned)


def extract_title(body: str, fallback: str) -> str:
    """Title = first H1 if present, else fallback (frontmatter title / slug)."""
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def rewrite_internal_links(body: str) -> str:
    """Rewrite `](other-doc.md)` / `](other-doc.md#sec)` → `](../other-doc/#sec)`.

    Absolute refs / anchors / external URLs pass through unchanged.
    """
    def _sub(m: re.Match) -> str:
        target = m.group(1)
        if target.startswith(("http://", "https://", "#", "/", "mailto:")):
            return m.group(0)
        # Only handle *.md or *.md#anchor (strip any preceding ../ or ./)
        rel = target.lstrip("./")
        if not rel.endswith(".md") and ".md#" not in rel:
            return m.group(0)
        if ".md#" in rel:
            stem, _, anchor = rel.partition(".md#")
            return f"](../{stem}/#{anchor})"
        stem = rel[:-3]  # drop .md
        return f"](../{stem}/)"
    return re.sub(r"\]\(([^)]+)\)", _sub, body)


def git_last_modified(path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short", "--", str(path.name)],
            cwd=path.parent, capture_output=True, text=True, check=False,
        )
        d = out.stdout.strip()
        if d:
            return d
    except Exception:
        pass
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def md_to_html(body: str) -> str:
    return md_lib.markdown(
        body,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
        output_format="html5",
    )


# ─── Page templates ───────────────────────────────────────────────────────────

BASE_CSS = """
:root{--bg:#f5f5f7;--card:#fff;--border:#e5e7eb;--text:#1f2328;--muted:#6b7280;--accent:#0071E3;}
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--bg);color:var(--text);font:400 15px/1.6 -apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',Helvetica,Arial,sans-serif;min-height:100vh;}
.tlz-container{max-width:1100px;margin:0 auto;padding:24px 20px 60px;}
a{color:var(--accent);}
"""

INDEX_CSS = """
.intro{max-width:720px;margin:20px 0 32px;color:#4b5563;font-size:15px;line-height:1.7;}
.intro strong{color:#1f2328;}
.group{margin-bottom:36px;}
.group-title{display:flex;align-items:center;gap:10px;margin-bottom:14px;padding-left:10px;border-left:3px solid var(--c);}
.group-title h2{font-size:17px;font-weight:700;letter-spacing:-0.01em;color:var(--c);}
.group-title .count{background:#eef0f2;color:var(--muted);font-size:11px;font-weight:600;padding:1px 8px;border-radius:10px;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;}
.card{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--c);border-radius:10px;padding:14px 16px;transition:box-shadow .15s,transform .15s;text-decoration:none;color:inherit;display:flex;flex-direction:column;gap:6px;}
.card:hover{box-shadow:0 6px 16px rgba(0,0,0,.07);transform:translateY(-1px);}
.card .title{font-size:15px;font-weight:600;letter-spacing:-0.01em;color:#1f2328;}
.card .abstract{font-size:13px;color:var(--muted);line-height:1.5;}
.card .meta{font-size:11px;color:#9ca3af;font-family:ui-monospace,monospace;margin-top:auto;padding-top:4px;}
footer{margin-top:36px;padding-top:16px;border-top:1px solid var(--border);text-align:center;color:var(--muted);font-size:12px;}
footer a{text-decoration:none;}
"""

ARTICLE_CSS = """
.article{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:36px 44px;margin-top:18px;}
.article .back{display:inline-block;color:var(--muted);font-size:13px;text-decoration:none;margin-bottom:20px;}
.article .back:hover{color:var(--accent);}
.article .meta-row{color:var(--muted);font-size:12px;margin-bottom:24px;display:flex;gap:12px;flex-wrap:wrap;}
.article .meta-row .group-chip{background:#eef0f2;color:var(--c);padding:1px 8px;border-radius:10px;font-weight:600;font-size:11px;}
.article h1{font-size:26px;font-weight:700;letter-spacing:-0.02em;color:#1f2328;margin:0 0 14px;line-height:1.3;}
.article h2{font-size:19px;font-weight:700;letter-spacing:-0.01em;margin:28px 0 10px;color:#1f2328;border-bottom:1px solid var(--border);padding-bottom:6px;}
.article h3{font-size:16px;font-weight:600;margin:20px 0 8px;color:#1f2328;}
.article h4{font-size:14px;font-weight:600;margin:14px 0 6px;color:#374151;}
.article p{margin:10px 0;}
.article ul,.article ol{margin:8px 0 12px 22px;}
.article li{margin:3px 0;}
.article code{background:#f1f3f5;color:#d6336c;font-family:ui-monospace,SFMono-Regular,monospace;font-size:13px;padding:1px 5px;border-radius:4px;}
.article pre{background:#0d1117;color:#e6edf3;padding:14px 16px;border-radius:8px;overflow-x:auto;font-size:13px;line-height:1.5;margin:12px 0;}
.article pre code{background:transparent;color:inherit;padding:0;font-size:13px;}
.article blockquote{border-left:3px solid #d1d5db;padding:4px 14px;margin:12px 0;color:#4b5563;background:#f9fafb;border-radius:0 6px 6px 0;}
.article blockquote p{margin:4px 0;}
.article table{border-collapse:collapse;margin:14px 0;font-size:13.5px;display:block;overflow-x:auto;max-width:100%;}
.article table thead{background:#f9fafb;}
.article th,.article td{border:1px solid var(--border);padding:8px 12px;text-align:left;}
.article th{font-weight:600;color:#1f2328;}
.article tr:nth-child(even) td{background:#fafbfc;}
.article hr{border:none;border-top:1px solid var(--border);margin:24px 0;}
.article a{color:var(--accent);}
.article img{max-width:100%;border-radius:8px;margin:12px 0;}
@media(max-width:640px){.article{padding:24px 20px;}.article h1{font-size:22px;}}
"""


def render_index(articles: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    by_group = {g["key"]: [] for g in GROUPS}
    for a in articles:
        key = a["group"] if a["group"] in by_group else "strategy"
        by_group[key].append(a)
    # sort each group by order (asc), then by date desc
    for k in by_group:
        by_group[k].sort(key=lambda a: (a.get("order", 100), -int(a["date"].replace("-", "")) if a["date"] else 0))

    sections = []
    for g in GROUPS:
        items = by_group[g["key"]]
        if not items:
            continue
        cards = "\n".join(
            f'''<a class="card" href="{esc(a['slug'])}/" style="--c:{g['color']}">
  <div class="title">{esc(a['title'])}</div>
  <div class="abstract">{esc(a['abstract'])}</div>
  <div class="meta">{esc(a['date'])}</div>
</a>''' for a in items
        )
        sections.append(f'''<section class="group" style="--c:{g['color']}">
  <div class="group-title"><span>{g['icon']}</span><h2>{esc(g['title'])}</h2><span class="count">{len(items)}</span></div>
  <div class="grid">{cards}</div>
</section>''')

    body = "\n".join(sections) if sections else '<p style="color:var(--muted)">暂无公开文章。</p>'
    total = sum(len(v) for v in by_group.values())

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>理财笔记 — tianlizeng.cloud</title>
<meta name="description" content="国际资产配置笔记 · 换汇 / 投资 / 香港银行 / 策略分析">
<style>
{SITE_CONTENT_CSS}
{BASE_CSS}
{INDEX_CSS}
</style>
</head>
<body>
{NAVBAR_HTML}
{SITE_HEADER_HTML}
<div class="tlz-container">
  <p class="intro">国际资产配置的公开笔记。覆盖<strong>换汇链路</strong>（IBKR 枢纽 / 港银 spread）、<strong>投资工具</strong>（BOXX ETF / Carry Trade / 指数 Sharpe）、<strong>香港银行</strong>（HSBC 结构性存款 / Lombard 贷款 / 私行）、以及<strong>策略分析</strong>。共 {total} 篇。</p>
  {body}
  <footer>Generated {now} · <a href="https://github.com/zengtianli/assets">source</a></footer>
</div>
</body>
</html>
"""


def render_article(a: dict) -> str:
    group = next((g for g in GROUPS if g["key"] == a["group"]), GROUPS[-1])
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(a['title'])} — 理财笔记</title>
<meta name="description" content="{esc(a['abstract'])}">
<style>
{SITE_CONTENT_CSS}
{BASE_CSS}
{ARTICLE_CSS}
:root {{ --c: {group['color']}; }}
</style>
</head>
<body>
{NAVBAR_HTML}
{SITE_HEADER_HTML}
<div class="tlz-container">
<article class="article">
<a class="back" href="../">← 返回首页</a>
<div class="meta-row">
  <span class="group-chip">{group['icon']} {esc(group['title'])}</span>
  <span>更新 {esc(a['date'])}</span>
</div>
{a['html']}
</article>
</div>
</body>
</html>
"""


def main():
    if not DOCS_DIR.exists():
        print(f"ERROR: {DOCS_DIR} not found", file=sys.stderr)
        sys.exit(1)

    articles = []
    for md_path in sorted(DOCS_DIR.glob("*.md")):
        raw = md_path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(raw)
        if not meta.get("public"):
            continue

        body = strip_nav_line(body)
        body = rewrite_internal_links(body)
        title = meta.get("title") or extract_title(body, md_path.stem)
        # Drop the first H1 from body (we render title separately via frontmatter? Actually keep — md source has its own H1 which becomes <h1> in article css. Our template doesn't emit separate <h1>. So keep body as-is.)
        html_body = md_to_html(body)

        articles.append({
            "slug": md_path.stem,
            "title": title,
            "group": meta.get("group", "strategy"),
            "abstract": meta.get("abstract", ""),
            "order": meta.get("order", 100),
            "date": git_last_modified(md_path),
            "html": html_body,
        })

    SITE_DIR.mkdir(exist_ok=True)
    # clean stale article dirs
    for child in SITE_DIR.iterdir():
        if child.is_dir():
            import shutil
            shutil.rmtree(child)

    (SITE_DIR / "index.html").write_text(render_index(articles), encoding="utf-8")

    for a in articles:
        art_dir = SITE_DIR / a["slug"]
        art_dir.mkdir(exist_ok=True)
        (art_dir / "index.html").write_text(render_article(a), encoding="utf-8")

    print(f"Generated {len(articles)} articles → {SITE_DIR}")
    for a in articles:
        print(f"  · [{a['group']}] {a['slug']} — {a['title']}")


if __name__ == "__main__":
    main()
