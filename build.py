#!/usr/bin/env python3
"""サイト生成スクリプト。

  data/researchmap/*.json  … researchmap から取得した業績（scripts/fetch_researchmap.py）
  content/*.yaml           … 手で書く情報（サイト設定・プロジェクト・ニュース・上書き設定）
  templates/*.html         … Jinja2 テンプレート
  assets/                  … CSS / JS / 画像

  → _site/ に日本語版（/）と英語版（/en/）を出力する。

使い方:  python build.py
"""
from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import re
import shutil
from collections import OrderedDict, defaultdict

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data" / "researchmap"
CONTENT = ROOT / "content"
OUT = ROOT / "_site"
LANGS = ["ja", "en"]

CATEGORIES = OrderedDict([
    ("journal", {"ja": "Journal", "en": "Journal", "long_ja": "原著論文（Journal）", "long_en": "Journal Papers"}),
    ("chapter", {"ja": "Book Chapter", "en": "Book Chapter", "long_ja": "原著論文（Book Chapter）", "long_en": "Book Chapters"}),
    ("intl_reviewed", {"ja": "国際会議（査読付）", "en": "Peer-Reviewed Proc.", "long_ja": "国際会議（査読付き論文）", "long_en": "Peer-Reviewed Conference Proceedings"}),
    ("intl_other", {"ja": "国際会議（その他）", "en": "Other Proc.", "long_ja": "国際会議（その他）", "long_en": "Other Proceedings / Abstracts"}),
    ("research_meeting", {"ja": "研究会", "en": "Domestic Meetings", "long_ja": "国内発表（研究会）", "long_en": "Domestic Research Meetings"}),
    ("domestic", {"ja": "国内学会", "en": "Domestic Conf.", "long_ja": "国内発表（国内学会）", "long_en": "Domestic Conferences"}),
    ("books", {"ja": "書籍", "en": "Books", "long_ja": "書籍", "long_en": "Books"}),
    ("patents", {"ja": "産業財産権", "en": "Patents", "long_ja": "産業財産権", "long_en": "Industrial Property Rights"}),
    ("awards", {"ja": "受賞", "en": "Awards", "long_ja": "受賞", "long_en": "Awards"}),
])
PAPER_CATS = {"journal", "chapter", "intl_reviewed", "intl_other", "research_meeting"}
CJK = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")
MONTHS_EN = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]

T = {  # UI 文言
    "ja": {
        "nav_news": "NEWS", "nav_research": "RESEARCH", "nav_pubs": "PUBLICATIONS", "nav_grants": "GRANTS", "nav_about": "ABOUT",
        "news_sub": "お知らせ", "research_sub": "研究プロジェクト", "pubs_sub": "研究業績（researchmap から自動更新）",
        "grants_sub": "研究費", "about_sub": "プロフィール",
        "all": "ALL", "news_more": "ニュース一覧 →", "pubs_more": "すべての業績を見る →", "research_more": "すべてのプロジェクト →",
        "kind_paper": "論文", "kind_talk": "発表", "kind_award": "受賞", "kind_other": "その他",
        "badge_lead": "研究代表", "badge_collab": "共同研究", "badge_ongoing": "進行中",
        "fy": "年度", "fy_fmt": "{}年度", "search": "検索", "search_ph": "タイトル・著者・会議名",
        "project": "プロジェクト", "none_found": "該当する業績はありません。",
        "related_pubs": "関連業績", "related_grants": "関連する研究費", "back_research": "← 研究プロジェクト一覧",
        "role_pi": "代表", "role_co": "分担", "period": "期間",
        "recent_pubs": "最近の主な業績", "invited": "招待", "detail": "詳しく見る →",
        "degrees": "学位", "career": "経歴", "education": "学歴", "memberships": "所属学会", "interests": "研究キーワード", "areas": "研究分野",
        "contact": "連絡先", "updated": "業績データ: researchmap（自動更新）", "last_build": "最終更新",
        "count_suffix": "件", "lang_label": "言語",
    },
    "en": {
        "nav_news": "NEWS", "nav_research": "RESEARCH", "nav_pubs": "PUBLICATIONS", "nav_grants": "GRANTS", "nav_about": "ABOUT",
        "news_sub": "Latest updates", "research_sub": "Research projects", "pubs_sub": "Publications (synced from researchmap)",
        "grants_sub": "Research grants", "about_sub": "Profile",
        "all": "ALL", "news_more": "All news →", "pubs_more": "All publications →", "research_more": "All projects →",
        "kind_paper": "Paper", "kind_talk": "Talk", "kind_award": "Award", "kind_other": "Other",
        "badge_lead": "Principal Investigator", "badge_collab": "Joint research", "badge_ongoing": "Ongoing",
        "fy": "Fiscal year", "fy_fmt": "FY{}", "search": "Search", "search_ph": "Title, author, venue",
        "project": "Project", "none_found": "No matching items.",
        "related_pubs": "Related publications", "related_grants": "Related grants", "back_research": "← All projects",
        "role_pi": "PI", "role_co": "Co-I", "period": "Period",
        "recent_pubs": "Selected recent publications", "invited": "Invited", "detail": "Read more →",
        "degrees": "Degrees", "career": "Career", "education": "Education", "memberships": "Memberships", "interests": "Keywords", "areas": "Research areas",
        "contact": "Contact", "updated": "Publication data: researchmap (auto-synced)", "last_build": "Last update",
        "count_suffix": "", "lang_label": "Language",
    },
}


# ------------------------------------------------------------------ helpers
def load_yaml(name):
    return yaml.safe_load((CONTENT / name).read_text(encoding="utf-8")) or {}


def load_rm(cat):
    p = DATA / f"{cat}.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("items", [])


def L(d, lang, fallback=True):
    """{"ja":..,"en":..} から言語を選ぶ。"""
    if d is None or not isinstance(d, (dict, str, list)):
        return ""
    if isinstance(d, (str, list)):
        return d
    v = d.get(lang)
    if (v is None or v == "" or v == []) and fallback:
        v = d.get("ja") if lang == "en" else d.get("en")
    return v if v is not None else ""


def esc(s):
    return html.escape(str(s or ""), quote=False)


def parse_date(s):
    if not s or str(s).startswith("9999"):
        return None
    parts = [int(x) for x in re.findall(r"\d+", str(s))[:3]]
    if not parts:
        return None
    y = parts[0]
    m = parts[1] if len(parts) > 1 else 1
    d = parts[2] if len(parts) > 2 else 1
    return dt.date(y, m, d), len(parts)


def fmt_date(s, lang, precision=None):
    p = parse_date(s)
    if not p:
        return ""
    d, n = p
    n = precision or n
    if lang == "en":
        return f"{MONTHS_EN[d.month-1]} {d.year}" if n >= 2 else str(d.year)
    return f"{d.year}年{d.month}月" if n >= 2 else f"{d.year}年"


def dot_date(s):
    p = parse_date(s)
    if not p:
        return ""
    d, n = p
    return [f"{d.year}", f"{d.year}.{d.month:02d}", f"{d.year}.{d.month:02d}.{d.day:02d}"][min(n, 3) - 1]


def fiscal_year(s):
    p = parse_date(s)
    if not p:
        return None
    d, _ = p
    return d.year if d.month >= 4 else d.year - 1


class Ctx:
    self_re: re.Pattern


def names(lst, lang, ctx, limit=None):
    if not lst:
        return ""
    arr = L(lst, lang) or []
    out = []
    for a in arr:
        n = (a.get("name") or "").strip()
        n = re.sub(r"^\s*([^,]+),\s*([^,]+)$", r"\1 \2", n) if CJK.search(n) else n
        e = esc(n)
        if ctx.self_re.search(n):
            e = f"<strong>{e}</strong>"
        out.append(e)
    if limit and len(out) > limit:
        out = out[:limit] + (["他"] if lang == "ja" else ["et al."])
    sep = "，" if lang == "ja" and any(CJK.search(a.get("name", "")) for a in arr) else ", "
    return sep.join(out)


def pages(it):
    a, b = it.get("starting_page"), it.get("ending_page")
    if a and b and a != b:
        return f"pp. {a}–{b}"
    if a:
        return f"p. {a}"
    return ""


def links_for(it, cat_key, rm_id, ctx):
    links = []
    ids = it.get("identifiers") or {}
    doi = (ids.get("doi") or [None])[0]
    if doi:
        links.append({"label": "DOI", "url": f"https://doi.org/{doi}"})
    for sa in it.get("see_also") or []:
        if not doi and sa.get("label") in ("url", "url2"):
            links.append({"label": "URL", "url": sa["@id"]})
            break
    for x in ctx.overrides.get("extra_links", {}).get(rm_id, []) or []:
        links.append(x)
    links.append({"label": "researchmap", "url": f"https://researchmap.jp/{ctx.rid}/{cat_key}/{rm_id}"})
    return links


# ------------------------------------------------------------ normalization
def classify(cat_key, it):
    if cat_key == "published_papers":
        t = it.get("published_paper_type")
        if t == "scientific_journal":
            return "journal"
        if t == "in_book":
            return "chapter"
        if t in ("international_conference_proceedings", None):
            return "intl_reviewed" if it.get("referee") else "intl_other"
        if t in ("research_society", "symposium"):
            return "research_meeting"
        return "intl_other"
    if cat_key == "misc":
        t = it.get("misc_type")
        if t in ("summary_international_conference",):
            return "intl_other"
        if t in ("technical_report", "summary_national_conference", "research_society"):
            return "research_meeting"
        return None  # 解説記事など（現状は表示しない）
    if cat_key == "presentations":
        return "domestic"
    if cat_key == "books_etc":
        return "books"
    if cat_key == "industrial_property_rights":
        return "patents"
    if cat_key == "awards":
        return "awards"
    return None


def cite(item, lang, ctx):
    """1件分の書誌を HTML で返す。"""
    it, c = item["raw"], item["cat"]
    title = L(it.get("paper_title") or it.get("presentation_title") or it.get("book_title")
              or it.get("industrial_property_right_title") or it.get("award_name"), lang)
    jp = bool(CJK.search(title or ""))
    q1, q2, sep = ("“", "”", "，") if jp else ("“", "”", ", ")
    date = fmt_date(item["date"], "ja" if jp else "en")
    parts = []
    if c in PAPER_CATS:
        venue = L(it.get("publication_name"), lang)
        vol = it.get("volume")
        no = it.get("number")
        parts = [names(it.get("authors"), lang, ctx), f"{q1}{esc(title)}{q2}", f"<em>{esc(venue)}</em>" if venue else ""]
        if vol:
            parts.append(f"Vol. {esc(vol)}")
        if no:
            parts.append(f"No. {esc(no)}")
        parts += [pages(it), date]
    elif c == "domestic":
        ev = L(it.get("event"), lang)
        parts = [names(it.get("presenters"), lang, ctx), f"{q1}{esc(title)}{q2}", f"<em>{esc(ev)}</em>", date]
        if it.get("invited"):
            parts.insert(0, f"<span class=\"inv\">[{T[lang]['invited']}]</span>")
    elif c == "books":
        parts = [names(it.get("authors"), lang, ctx), f"<em>{esc(title)}</em>"]
        if it.get("book_owner_range"):
            parts.append(("担当：" if jp else "Part: ") + esc(L(it.get("book_owner_range"), lang)))
        parts += [esc(L(it.get("publisher"), lang)), date]
    elif c == "patents":
        parts = [names(it.get("inventors"), lang, ctx), esc(it.get("application_number")), f"{q1}{esc(title)}{q2}",
                 fmt_date(it.get("application_date"), "ja" if jp else "en")]
    elif c == "awards":
        award = esc(title)
        assoc = esc(L(it.get("association"), lang))
        target = L(it.get("award_title"), lang)
        parts = [f"<strong class=\"award\">{award}</strong>", assoc, date]
        if target:
            parts.append(f"{q1}{esc(target)}{q2}")
        win = names(it.get("winners"), lang, ctx)
        if win:
            parts.append(win)
    parts = [p for p in parts if p]
    if jp:  # 和文は斜体にしない
        parts = [p.replace("<em>", "").replace("</em>", "") for p in parts]
    end = "．" if jp else "."
    return Markup(sep.join(parts) + end)


def build_items(ctx):
    items = []
    ov = ctx.overrides
    for cat_key in ["published_papers", "misc", "presentations", "books_etc", "industrial_property_rights", "awards"]:
        for it in load_rm(cat_key):
            rid = str(it.get("rm:id"))
            if rid in set(map(str, ov.get("hide") or [])):
                continue
            c = str((ov.get("category") or {}).get(rid) or classify(cat_key, it) or "")
            if not c:
                continue
            date = it.get("publication_date") or it.get("award_date") or it.get("application_date") or it.get("from_event_date") or ""
            title_any = " ".join(str(v) for v in (it.get("paper_title") or it.get("presentation_title") or it.get("book_title")
                                                  or it.get("industrial_property_right_title") or it.get("award_name") or {}).values())
            venue_any = " ".join(str(v) for v in (it.get("publication_name") or it.get("event") or it.get("association") or {}).values())
            item = {"id": rid, "rm_cat": cat_key, "cat": c, "raw": it, "date": date, "fy": fiscal_year(date),
                    "sort": (parse_date(date) or (dt.date(1900, 1, 1), 0))[0], "title_any": title_any, "venue_any": venue_any,
                    "projects": []}
            item["links"] = links_for(it, cat_key, rid, ctx)
            items.append(item)
    items.sort(key=lambda x: x["sort"], reverse=True)
    return items


def link_projects(items, projects, ctx):
    by_id = {i["id"]: i for i in items}
    grants = {str(g["rm:id"]): g for g in load_rm("research_projects")}
    for p in projects:
        ids = set()
        for gid in p.get("grants") or []:
            g = grants.get(str(gid))
            for sa in (g or {}).get("see_also") or []:
                m = re.search(r"/(\d+)$", sa.get("@id", ""))
                if m and sa.get("label", "").startswith("rm:"):
                    ids.add(m.group(1))
        if p.get("match"):
            rx = re.compile(p["match"], re.I)
            for i in items:
                if i["cat"] in ("awards", "books"):
                    continue
                if rx.search(i["title_any"]):
                    ids.add(i["id"])
        for k, v in (ctx.overrides.get("project_add") or {}).items():
            if v == p["slug"]:
                ids.add(str(k))
        for k, v in (ctx.overrides.get("project_remove") or {}).items():
            if v == p["slug"]:
                ids.discard(str(k))
        for i in ids:
            if i in by_id and p["slug"] not in by_id[i]["projects"]:
                by_id[i]["projects"].append(p["slug"])


# ------------------------------------------------------------------- news
def auto_news(items, ctx):
    months = int(ctx.site.get("auto_news_months", 24))
    cutoff = dt.date.today() - dt.timedelta(days=months * 30)
    hide = set(map(str, ctx.overrides.get("news_hide") or []))
    groups = OrderedDict()
    for i in items:
        if i["sort"] < cutoff or i["id"] in hide or i["sort"] > dt.date.today() + dt.timedelta(days=60):
            continue
        if i["cat"] in ("patents", "books"):
            kind = "other"
        elif i["cat"] == "awards":
            kind = "award"
        elif i["cat"] in ("journal", "chapter"):
            kind = "paper"
        else:
            kind = "talk"
        if kind == "talk":
            key = ("talk", i["venue_any"], i["date"][:7])
        else:
            key = (kind, i["id"])
        groups.setdefault(key, []).append(i)
    news = []
    for key, grp in groups.items():
        i = grp[0]
        it = i["raw"]
        e = {"date": i["date"], "kind": key[0], "sort": i["sort"], "url": None, "auto": True, "text": {}}
        for lang in LANGS:
            title = L(it.get("paper_title") or it.get("presentation_title") or it.get("book_title")
                      or it.get("industrial_property_right_title") or it.get("award_name"), lang)
            venue = L(it.get("publication_name") or it.get("event") or it.get("association") or it.get("publisher"), lang)
            if key[0] == "talk":
                n = len(grp)
                if lang == "ja":
                    e["text"][lang] = (f"{venue} で{n}件の発表を行いました。" if n > 1 else f"{venue} にて「{title}」を発表しました。")
                else:
                    e["text"][lang] = (f"{n} presentations at {venue}." if n > 1 else f"Presented “{title}” at {venue}.")
            elif key[0] == "paper":
                e["text"][lang] = (f"論文「{title}」が {venue} に掲載されました。" if lang == "ja" else f"Paper “{title}” published in {venue}.")
            elif key[0] == "award":
                e["text"][lang] = (f"{venue}より「{title}」を受賞しました。" if lang == "ja" else f"Received the {title} from {venue}.")
            else:
                e["text"][lang] = (f"「{title}」" + ("を出版しました。" if i["cat"] == "books" else "を出願しました。")) if lang == "ja" else (f"Published “{title}”." if i["cat"] == "books" else f"Filed patent application “{title}”.")
        doi = next((l["url"] for l in i["links"] if l["label"] in ("DOI", "URL")), None)
        e["url"] = doi if len(grp) == 1 else None
        news.append(e)
    return news


def manual_news(ctx):
    out = []
    for n in load_yaml("news.yaml") or []:
        p = parse_date(n.get("date"))
        if not p:
            continue
        txt = n.get("text") or {}
        if isinstance(txt, str):
            txt = {"ja": txt}
        out.append({"date": str(n["date"]), "kind": n.get("kind", "other"), "sort": p[0], "url": n.get("url"),
                    "image": n.get("image"), "auto": False, "text": txt})
    return out


# ------------------------------------------------------------------ grants
def build_grants(ctx):
    out = []
    for g in load_rm("research_projects"):
        role = g.get("research_project_owner_role")
        inv = [x.get("name", "") for x in (L(g.get("investigators"), "ja") or [])]
        if not role:
            role = "principal_investigator" if inv and ctx.self_re.search(inv[0]) else "coinvestigator"
        kaken = next((sa["@id"] for sa in g.get("see_also") or [] if sa.get("label") == "kaken"), None)
        out.append({
            "id": str(g["rm:id"]), "raw": g, "role": "pi" if role == "principal_investigator" else "co",
            "from": dot_date(g.get("from_date")), "to": dot_date(g.get("to_date")),
            "sort": (parse_date(g.get("from_date")) or (dt.date(1900, 1, 1), 0))[0],
            "active": (parse_date(g.get("to_date")) or (dt.date(2999, 1, 1), 0))[0] >= dt.date.today(),
            "kaken": kaken,
        })
    out.sort(key=lambda x: (not x["active"], x["role"] != "pi", -x["sort"].toordinal()))
    return out


# ------------------------------------------------------------------- build
def main():
    ctx = Ctx()
    ctx.site = load_yaml("site.yaml")
    ctx.rid = ctx.site["researchmap_id"]
    ctx.overrides = load_yaml("overrides.yaml")
    ctx.self_re = re.compile("|".join(ctx.site.get("self_name_patterns") or ["Toya"]), re.I)
    projects = load_yaml("projects.yaml")
    items = build_items(ctx)
    link_projects(items, projects, ctx)
    news = sorted(auto_news(items, ctx) + manual_news(ctx), key=lambda n: n["sort"], reverse=True)
    grants = build_grants(ctx)
    profile = json.loads((DATA / "profile.json").read_text(encoding="utf-8")) if (DATA / "profile.json").exists() else {}
    proj_by_slug = {p["slug"]: p for p in projects}

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / ".nojekyll").write_text("")

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.globals.update(L=L, CATEGORIES=CATEGORIES, dot_date=dot_date, fmt_date=fmt_date)
    today = dt.date.today()

    for lang in LANGS:
        prefix = "" if lang == "ja" else "en/"
        for i in items:
            i[f"cite_{lang}"] = cite(i, lang, ctx)
        fys = sorted({i["fy"] for i in items if i["fy"]}, reverse=True)
        counts = {c: sum(1 for i in items if i["cat"] == c) for c in CATEGORIES}
        top_pubs = [i for i in items if i["cat"] in ("journal", "chapter", "intl_reviewed")][:5]

        def render(tpl, path, **kw):
            depth = path.count("/")
            root = "../" * depth
            other = ("en/" + path) if lang == "ja" else path[3:]
            other_root = root + ("" if lang == "en" else "")
            html_ = env.get_template(tpl).render(
                lang=lang, t=T[lang], site=ctx.site, root=root, home=root + prefix if lang == "en" else root,
                lang_root=root + prefix, alt_href=(root + other), path=path, today=today, projects=projects,
                proj_by_slug=proj_by_slug, **kw)
            out = OUT / path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html_, encoding="utf-8")

        render("index.html", prefix + "index.html", news=news[: int(ctx.site.get("top_news_count", 5))], top_pubs=top_pubs, items=items)
        render("news.html", prefix + "news.html", news=news)
        render("research.html", prefix + "research/index.html")
        for p in projects:
            rel = [i for i in items if p["slug"] in i["projects"]]
            pg = [g for g in grants if g["id"] in set(map(str, p.get("grants") or []))]
            render("project.html", prefix + f"research/{p['slug']}.html", p=p, rel=rel, pgrants=pg)
        render("publications.html", prefix + "publications.html", items=items, fys=fys, counts=counts)
        render("grants.html", prefix + "grants.html", grants=grants)
        render("about.html", prefix + "about.html", profile=profile,
               career=sorted(load_rm("research_experience"), key=lambda x: x.get("from_date", ""), reverse=True),
               education=sorted(load_rm("education"), key=lambda x: x.get("from_date", ""), reverse=True),
               memberships=load_rm("association_memberships"), interests=load_rm("research_interests"),
               areas=load_rm("research_areas"), awards=[i for i in items if i["cat"] == "awards"])
    print(f"built: {len(items)} items, {len(news)} news, {len(projects)} projects, {len(grants)} grants -> {OUT}")


if __name__ == "__main__":
    main()
