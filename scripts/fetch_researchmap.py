#!/usr/bin/env python3
"""researchmap API から業績データを取得して data/researchmap/ に保存する。

使い方:  python scripts/fetch_researchmap.py
取得に失敗したカテゴリは既存のファイルをそのまま残す（ビルドは前回のデータで続行できる）。
"""
import json
import pathlib
import sys
import time
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "researchmap"
CATEGORIES = [
    "published_papers", "presentations", "misc", "books_etc", "awards",
    "industrial_property_rights", "research_projects", "research_experience",
    "education", "association_memberships", "research_interests", "research_areas",
    "committee_memberships", "teaching_experience", "social_contribution", "media_coverage",
]
UA = "teruki-toya.github.io site builder (+https://github.com/Teruki-Toya/teruki-toya.github.io)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_all(rid, cat):
    items, start = [], 1
    while True:
        d = get(f"https://api.researchmap.jp/{rid}/{cat}?limit=1000&start={start}")
        got = d.get("items", [])
        items += got
        total = d.get("total_items", len(items))
        if not got or len(items) >= total:
            break
        start += len(got)
        time.sleep(0.5)
    return {"total_items": len(items), "items": items}


def main():
    site = yaml.safe_load((ROOT / "content" / "site.yaml").read_text(encoding="utf-8"))
    rid = site["researchmap_id"]
    OUT.mkdir(parents=True, exist_ok=True)
    failed = []
    try:
        (OUT / "profile.json").write_text(json.dumps(get(f"https://api.researchmap.jp/{rid}"), ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        failed.append(("profile", e))
    for cat in CATEGORIES:
        try:
            data = fetch_all(rid, cat)
            (OUT / f"{cat}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{cat}: {data['total_items']}")
        except urllib.error.HTTPError as e:
            if e.code == 404:  # カテゴリにデータがない
                (OUT / f"{cat}.json").write_text('{"total_items": 0, "items": []}', encoding="utf-8")
                print(f"{cat}: 0")
            else:
                failed.append((cat, e))
        except Exception as e:  # noqa: BLE001
            failed.append((cat, e))
        time.sleep(0.5)
    for cat, e in failed:
        print(f"WARNING: {cat} の取得に失敗（前回のデータを使用）: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
