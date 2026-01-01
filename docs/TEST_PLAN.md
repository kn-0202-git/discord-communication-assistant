# テスト計画

## 1. テスト方針

- テスト駆動開発（TDD）
- Red → Green → Refactor
- PRマージ前に全テスト通過必須
- **テスト結果で品質を判断できるようにする**

## 2. テストレベル

| レベル | 対象 | ツール |
|--------|------|--------|
| ユニットテスト | 各関数・クラス | pytest |
| 統合テスト | 複数モジュール連携 | pytest |
| E2Eテスト | Bot全体動作 | 手動 + dpytest |

## 3. テスト環境

- テスト用DB: SQLite（インメモリ）
- モック: pytest-mock, unittest.mock
- Discord: dpytest
- AI: モック化（実際のAPI呼び出しなし）
- CI: GitHub Actions（mac/win/linux）

## 4. テストケース一覧

### 4.1 DB（tests/test_db.py）

| ID | テスト名 | 内容 | Phase |
|----|----------|------|-------|
| DB-01 | test_create_workspace | Workspace作成 | 1 |
| DB-02 | test_create_room | Room作成 | 1 |
| DB-03 | test_save_message | メッセージ保存 | 1 |
| DB-04 | test_save_message_with_attachment | 添付ファイル付き保存 | 1 |
| DB-05 | test_get_messages_by_room | Room別メッセージ取得 | 1 |
| DB-06 | test_search_messages_in_workspace | Workspace内検索 | 1 |
| DB-07 | test_workspace_isolation | Workspace A↔B分離 | 1 |
| DB-08 | test_room_link | Room間情報共有設定 | 1 |

### 4.2 Bot（tests/test_bot.py）

| ID | テスト名 | 内容 | Phase |
|----|----------|------|-------|
| BOT-01 | test_on_message_saves | メッセージ受信で保存 | 1 |
| BOT-02 | test_attachment_saved | 添付ファイル保存 | 1 |
| BOT-03 | test_bot_ignores_own_message | Bot自身の発言は無視 | 1 |
| BOT-04 | test_workspace_created_on_join | サーバー参加時Workspace作成 | 1 |
| BOT-05 | test_room_created_on_channel | チャンネル検出時Room作成 | 1 |

### 4.3 Storage（tests/test_storage.py）

| ID | テスト名 | 内容 | Phase |
|----|----------|------|-------|
| STR-01 | test_save_file_local | ローカル保存 | 1 |
| STR-02 | test_get_file_local | ローカル取得 | 1 |
| STR-03 | test_directory_structure | ディレクトリ構成確認 | 1 |
| STR-04 | test_cross_platform_path | mac/win両対応パス | 1 |
| STR-05 | test_save_file_drive | Google Drive保存 | 2 |
| STR-06 | test_create_folder_drive | Driveフォルダ作成 | 2 |

### 4.4 AI Router（tests/test_ai_router.py）

| ID | テスト名 | 内容 | Phase |
|----|----------|------|-------|
| RTR-01 | test_get_default_provider | デフォルト設定で取得 | 1 |
| RTR-02 | test_workspace_override | Workspace別上書き | 1 |
| RTR-03 | test_room_override | Room別上書き | 1 |
| RTR-04 | test_provider_not_configured | 未設定プロバイダーでエラー | 1 |
| RTR-05 | test_fallback_on_error | エラー時フォールバック | 1 |

### 4.5 AI Providers（tests/test_ai_providers.py）

| ID | テスト名 | 内容 | Phase |
|----|----------|------|-------|
| PRV-01 | test_openai_generate | OpenAI生成（モック） | 1 |
| PRV-02 | test_openai_embed | OpenAI埋め込み（モック） | 1 |
| PRV-03 | test_anthropic_generate | Anthropic生成（モック） | 1 |
| PRV-04 | test_google_generate | Google生成（モック） | 1 |
| PRV-05 | test_groq_generate | Groq生成（モック） | 1 |
| PRV-06 | test_local_generate | ローカルLLM生成（モック） | 1 |
| PRV-07 | test_whisper_transcribe | Whisper文字起こし（モック） | 2 |

### 4.6 AI機能（tests/test_ai.py）

| ID | テスト名 | 内容 | Phase |
|----|----------|------|-------|
| AI-01 | test_summarize_messages | メッセージ群を要約 | 1 |
| AI-02 | test_summarize_empty | 空の場合のハンドリング | 1 |
| AI-03 | test_summarize_with_workspace_config | Workspace設定で要約 | 1 |
| AI-04 | test_search_similar | 類似メッセージ検索 | 1 |
| AI-05 | test_search_no_result | 該当なしの場合 | 1 |
| AI-06 | test_transcribe_audio | 音声文字起こし | 2 |

### 4.7 コマンド（tests/test_commands.py）

| ID | テスト名 | 内容 | Phase |
|----|----------|------|-------|
| CMD-01 | test_summary_command | /summary実行 | 1 |
| CMD-02 | test_search_command | /search実行 | 1 |
| CMD-03 | test_search_other_workspace | 他Workspaceは検索不可 | 1 |
| CMD-04 | test_ai_config_command | /ai-config表示 | 1 |
| CMD-05 | test_remind_command | /remind実行 | 2 |
| CMD-06 | test_ask_command | /ask実行 | 3 |

## 5. AIモックの実装
```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_ai_provider():
    """AIプロバイダーのモック"""
    provider = AsyncMock()
    provider.generate.return_value = "これはモックの応答です"
    provider.embed.return_value = [0.1] * 1536
    return provider

@pytest.fixture
def mock_ai_router(mock_ai_provider):
    """AIルーターのモック"""
    router = AsyncMock()
    router.get_provider.return_value = mock_ai_provider
    return router
```

## 6. カバレッジ目標

| Phase | 目標 |
|-------|------|
| Phase 1 | 70%以上 |
| Phase 2 | 75%以上 |
| Phase 3 | 80%以上 |

## 7. テスト結果の読み方

### 成功時
```
tests/test_db.py::test_create_workspace PASSED
tests/test_ai_router.py::test_get_default_provider PASSED
======================== 2 passed in 0.52s ========================
```

### 失敗時
```
tests/test_ai_router.py::test_workspace_override FAILED

>       assert provider.model == "gemini-1.5-flash"
E       AssertionError: assert "gpt-4o-mini" == "gemini-1.5-flash"

======================== 1 failed, 1 passed ========================
```

**対応方法：**
1. どのテストが失敗したか確認
2. Claude Codeに「test_workspace_overrideが失敗している。修正して」と依頼
3. 再度テスト実行
