#!/usr/bin/env python3
"""ChatWork へ「今週の実践」メッセージを投稿する（スケジューラから呼ばれる）。

- ChatWork API には実用的な予約送信エンドポイントが無いため、
  GitHub Actions の cron（毎週日曜 11:00 UTC = 20:00 JST）から本スクリプトを起動し、
  posts/schedule.json で「今日（JST）の日付」に割り当てられたメッセージを投稿する。
- トークン・ルームIDは環境変数（GitHub Secrets）から読む。コードには絶対に書かない。
- DRY_RUN=1 のときは投稿せず内容を表示するだけ（顧客接点に触れない安全確認用）。

環境変数:
  CHATWORK_API_TOKEN  ... ChatWork APIトークン（Secret）
  CHATWORK_ROOM_ID    ... 投稿先ルームID（Secret or Variable）
  DRY_RUN             ... "1" なら投稿しない（既定: 投稿する）
  FORCE_DATE          ... "YYYY-MM-DD" を指定すると、その日付のメッセージを対象にする（手動テスト用）
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
SCHEDULE = ROOT / "posts" / "schedule.json"
CHATWORK_ENDPOINT = "https://api.chatwork.com/v2/rooms/{room_id}/messages"


def today_jst() -> str:
    forced = os.environ.get("FORCE_DATE", "").strip()
    if forced:
        return forced
    return datetime.now(JST).strftime("%Y-%m-%d")


def load_message_for(date_str: str) -> tuple[str, str] | None:
    """schedule.json から date_str に対応する (ファイル名, 本文) を返す。
    その日の割り当てが無ければ None（＝正常にスキップ）。
    設定ファイルの欠損・JSON破損・参照先メッセージの欠損、および
    「対象日以降の割り当てが一つも無い（＝配信在庫が尽きた）」状態は「異常」として例外を投げ、
    呼び出し側が exit 1 にする（無人運用で沈黙して見逃さないため）。"""
    if not SCHEDULE.exists():
        raise FileNotFoundError(f"必須ファイルがありません: {SCHEDULE}（誤削除・rebase等を疑う）")
    try:
        schedule = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"schedule.json のJSONが不正です: {e}") from e
    if not isinstance(schedule, dict):
        raise ValueError(f"schedule.json は日付→ファイル名の対応表（オブジェクト）である必要があります: {type(schedule).__name__}")
    entry = schedule.get(date_str)
    if not entry:
        # 「対象日の割り当てが無い」だけなら正常なスキップ。
        # ただし対象日以降の割り当てが一つも無い＝配信在庫が尽きているなら、
        # 沈黙させず異常として知らせる（在庫切れの検知。無人運用で涸れたまま気づかないのを防ぐ）。
        if not any(k >= date_str for k in schedule):
            last = max(schedule) if schedule else "なし"
            raise ValueError(
                f"配信在庫が尽きています（最後の割り当て: {last}）。"
                f"posts/ に次の文面を追加し、schedule.json に登録してください。"
            )
        return None
    msg_path = ROOT / "posts" / entry
    if not msg_path.exists():
        raise FileNotFoundError(f"スケジュール済みのメッセージファイルがありません: {msg_path}")
    return entry, msg_path.read_text(encoding="utf-8")


def post_to_chatwork(room_id: str, token: str, body: str) -> None:
    url = CHATWORK_ENDPOINT.format(room_id=urllib.parse.quote(str(room_id)))
    data = urllib.parse.urlencode({"body": body, "self_unread": "0"}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"X-ChatWorkToken": token, "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"[ok] posted (HTTP {resp.status}): {resp.read().decode('utf-8', 'replace')[:200]}")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        # 429/500 等。無人運用でも失敗が Actions 上で赤くなるよう非0終了。
        raise SystemExit(f"[error] ChatWork API がエラーを返しました (HTTP {e.code} {e.reason}): {detail}")
    except urllib.error.URLError as e:
        raise SystemExit(f"[error] ChatWork API へ接続できませんでした: {e.reason}")


def main() -> int:
    date_str = today_jst()
    try:
        found = load_message_for(date_str)
    except (FileNotFoundError, ValueError) as e:
        # 設定欠損・破損は「異常」→ 非0終了で Actions に赤アラートを出す
        print(f"[error] {e}", file=sys.stderr)
        return 1
    if found is None:
        print(f"[skip] {date_str} に割り当てられた投稿はありません。何もしません。")
        return 0  # 何もしないのは正常（毎週日曜に走っても、対象日でなければスキップ）

    entry, body = found
    dry = os.environ.get("DRY_RUN", "").strip() == "1"
    print(f"[info] 対象日: {date_str} / メッセージ: {entry} / DRY_RUN={dry}")

    if dry:
        print("----- 投稿せず内容のみ表示（DRY_RUN）-----")
        print(body)
        print("----- ここまで -----")
        return 0

    token = os.environ.get("CHATWORK_API_TOKEN", "").strip()
    room_id = os.environ.get("CHATWORK_ROOM_ID", "").strip()
    if not token or not room_id:
        print("[error] CHATWORK_API_TOKEN / CHATWORK_ROOM_ID が未設定です。", file=sys.stderr)
        return 1

    post_to_chatwork(room_id, token, body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
