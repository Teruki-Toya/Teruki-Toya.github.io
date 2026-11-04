# 鳥谷 輝樹 ホームページ

https://teruki-toya.github.io/ （日本語） / https://teruki-toya.github.io/en/ （English）

業績は [researchmap](https://researchmap.jp/t-toya) から毎日自動で取得して表示します。

## ふだんの更新

| やりたいこと | やること |
|---|---|
| 論文・発表・受賞を追加 | **researchmap に登録するだけ**（DOI を入れると書誌が自動入力されます）。翌朝（03:37 JST）にHPへ反映。すぐ反映したいときは GitHub の **Actions → Build & deploy site → Run workflow** |
| ニュースを追加（メディア掲載・採択など） | `content/news.yaml` に追記 |
| 業績の分類を変える／隠す／PDFリンクを足す | `content/overrides.yaml` |
| プロジェクトの文章・図を変える | `content/projects.yaml`、図は `assets/img/projects/` |
| 氏名・所属・リンク・トップの文言 | `content/site.yaml` |

`content/` のファイルは GitHub の画面上（鉛筆アイコン）で直接編集でき、保存（Commit）すると数分で公開されます。

## 業績の分類ルール

| HPの分類 | researchmap の区分 |
|---|---|
| Journal | 論文：学術雑誌 |
| Book Chapter | 論文：書籍内論文 |
| 国際会議（査読付） | 論文：国際会議プロシーディングス（査読あり） |
| 国際会議（その他） | 論文：国際会議プロシーディングス（査読なし）、MISC：国際会議要旨 |
| 研究会 | MISC：研究発表ペーパー・要旨（研究報告） |
| 国内学会 | 講演・口頭発表等 |
| 書籍／産業財産権／受賞 | 書籍等出版物／産業財産権／受賞 |

例外は `content/overrides.yaml` の `category` で個別に指定します。
業績とプロジェクトの対応は、researchmap の研究課題に紐づけた業績 ＋ `projects.yaml` の `match`（タイトルの正規表現）で自動判定されます。

## 手元で確認する

```sh
pip install -r requirements.txt
python scripts/fetch_researchmap.py   # 最新データ取得（任意）
python build.py                        # _site/ に出力
python -m http.server -d _site 8000    # http://localhost:8000
```

## 構成

```
content/        手で書く情報（YAML）
data/researchmap/  researchmap から取得したデータ（ビルド時に最新化）
templates/      HTML テンプレート（Jinja2）
assets/         CSS・JS・画像
build.py        サイト生成
scripts/fetch_researchmap.py  researchmap API 取得
.github/workflows/deploy.yml  自動ビルド・公開（push 時＋毎日）
```
