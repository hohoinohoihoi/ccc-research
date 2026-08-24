# ccc-research（CCC配布用リサーチスキル＋週次投稿の自動化）

このリポジトリは2つの役割を持ちます。

1. **配布**：調べものスキル `ccc-research` を、メンバーが1クリックでダウンロードできる場所（GitHub Releases）。
2. **半自動投稿**：毎週日曜20:00（JST）に「今週の実践」を ChatWork へ自動投稿（GitHub Actions）。

> 運営の考え方は CCC 本体リポジトリの `docs/ccc-membership-ops-rhythm.md` を参照。

---

## 1. スキルの配布（GitHub Releases）

- 配布物：`ccc-research.zip`（中身は `skills/ccc-research/SKILL.md`）。
- メンバーは Releases の最新版から**緑のボタンでZIPをダウンロード**できます（cloneもログインも不要）。
  - 最新版：`https://github.com/hohoinohoihoi/ccc-research/releases/latest`
  - 直リンク：`https://github.com/hohoinohoihoi/ccc-research/releases/latest/download/ccc-research.zip`
- 入れ方は会員サイトの章「4-5【使う道具】調べものスキル」を参照。

### リリースの作り方（更新時）
```bash
# 例：v0.2 を作り、ZIPを添付
gh release create v0.2 ccc-research.zip --title "ccc-research v0.2" --notes "CCC配布用リサーチスキル v0.2"
# 既存リリースに添付し直す場合
gh release upload v0.2 ccc-research.zip --clobber
```

---

## 2. 週次投稿の半自動化（ChatWork API × GitHub Actions）

ChatWork API には実用的な予約送信機能が無いため、**GitHub Actions の cron で時刻を作り**、その日に割り当てた本文だけを投稿します。

- スケジュール：`.github/workflows/weekly-post.yml`（毎週日曜 11:00 UTC = 20:00 JST。cronは数分の遅延あり）
- 投稿ロジック：`scripts/post_chatwork.py`（`posts/schedule.json` で「今日(JST)の日付」に対応する本文を投稿）
- 本文：`posts/YYYY-MM-DD_*.md`、対応表：`posts/schedule.json`

### セットアップ（リポジトリ管理者＝宮本さんが1回だけ）

GitHub の **Settings → Secrets and variables → Actions** で、次の2つを登録します（値はGitHub側に保存され、コードやログには出ません）。

| 名前 | 種別 | 値 |
|---|---|---|
| `CHATWORK_API_TOKEN` | Secret | ChatWork のAPIトークン |
| `CHATWORK_ROOM_ID` | Secret | 投稿先ルームのID（数字） |

> ⚠️ トークンはここ（GitHub Secrets）にだけ入れる。チャットやコード、コミットに貼らない。

### 安全確認（顧客接点に触れずにテスト・規律0）

いきなり本番ルームに出さず、まず確認します。

1. **Actions → weekly-chatwork-post → Run workflow** を開く。
2. `dry_run = 1`（既定）、`force_date` に schedule.json にある日付（例 `2026-08-24`）を入れて実行 → **投稿されず、本文がログに表示**されるだけ。中身を確認。
3. 実際に1本だけ自分宛に試したいときは、`CHATWORK_ROOM_ID` を一時的に**自分のマイチャット等のルームID**にし、`dry_run = 0`、`force_date` に同じ日付を入れて実行 → 自分にだけ届く。
4. 問題なければ `CHATWORK_ROOM_ID` を**メンバーグループのID**に戻す。以後は毎週日曜20:00に自動投稿。

> ⚠️ **二重投稿に注意**：このスクリプトは投稿履歴を持ちません（同じ日に2回走れば2回投稿します）。同じ日付で、cron の自動実行と手動実行（`dry_run=0`）が重ならないように。手動テストは `dry_run=1`、または `CHATWORK_ROOM_ID` を自分のルームにしてから行ってください。
> API失敗（429/500・接続不可）・`schedule.json` の欠損/破損時は、スクリプトが**非0終了して Actions が赤く失敗**します（沈黙して見逃さないため）。その週の投稿は行われないので、直して再実行してください。
> また、**配信在庫が尽きたとき**（対象日以降の割り当てが `schedule.json` に一つも無いとき）も赤く失敗します。「今日は対象日でない」だけなら正常（緑のまま）です。赤くなったら `posts/` に次の文面を追加してください。

### 投稿を足す・止める
- 足す：`posts/` に本文を追加し、`posts/schedule.json` に `"YYYY-MM-DD": "ファイル名"` を1行足す。
- 止める：そのワークフローを Actions 画面で **Disable**（または該当日付の行を schedule.json から消す）。

### 配信履歴・予定
| 日付(JST 20:00) | 本文 |
|---|---|
| 2026-07-11 | posts/2026-07-11_week1.md（最初の仕事） |
| 2026-07-19 | posts/2026-07-19_week2.md（すり合わせ） |
| 2026-07-26 | posts/2026-07-26_week3.md（情報は全部渡す） |
| 2026-08-02 | posts/2026-08-02_week4.md（ナレッジを育てる＋調べもの道具＝この配布） |
| 2026-08-24 | posts/2026-08-24_week5.md（ワークスペースという作業場） |

---

## 注意
- このリポジトリは**公開**（メンバーがZIPを取得できるようにするため）。トークン等の秘密は必ず Secrets に置き、ファイルには書かない。
- 自動投稿は顧客接点。初回は上の「安全確認」で必ず確かめてから本番ルームへ。
