# R-issue13: /record の利用条件と録音機能の実装ギャップ

## 要約

/record は VoiceRecorder を有効化したことで利用可能になったが、実音声のキャプチャは未実装。
現在はボイスチャンネル接続とプレースホルダー音声保存のみで、実録音は不可。

## Agent

Codex

## 日付

2026-01-18

---

## 背景

- テスト時に `/record` が「録音機能は現在利用できません」と表示
- VoiceRecorder が初期化されておらず、コマンドが無効状態だった
- さらに、録音開始にはユーザーがVC接続している必要がある

---

## 現状の挙動

- `/record on` 実行時:
  - VC接続が無いと「ボイスチャンネルに接続してから…」と案内
  - 接続後は録音セッションを作成し、**プレースホルダーWAV**を保存
- 実際の音声キャプチャは未実装（`src/bot/voice_recorder.py` に明記）

---

## 対応内容（反映済み）

- VoiceRecorder を Bot 初期化で生成し、`/record` に渡すよう修正
  - これにより「録音機能は現在利用できません」の表示は解消

---

## 改善点（Codex実装予定）

| 優先度 | タスク | ステータス |
|--------|--------|------------|
| P1 | ユーザー向けメッセージの明確化 | 未着手 |
| P2 | `config.yaml` に `voice_recording.enabled` フラグ追加 | 未着手 |
| P3 | VC未接続時エラー、録音開始/停止フローのテスト追加 | 未着手 |
| P4 | 実音声キャプチャ実装（py-cord/ffmpeg導入） | 将来課題 |

### P1: メッセージ明確化

- `/record on` 成功時のメッセージを変更:
  - `⚠️ 録音セッションを開始しました。`
  - `**注意**: 現在は録音メタデータの管理のみで、実際の音声キャプチャは未実装です。`

### P2: 設定フラグ

- `config.yaml` に以下を追加:
  ```yaml
  voice_recording:
    enabled: false
  ```
- `_register_record_command` で `enabled: false` なら登録をスキップ

---

## 参考

- `src/bot/commands.py`（/record のハンドラ）
- `src/bot/voice_recorder.py`（プレースホルダー録音）
- `src/bot/initializer.py`（VoiceRecorder初期化）
