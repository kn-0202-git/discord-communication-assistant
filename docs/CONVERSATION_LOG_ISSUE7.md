# Issue #7 会話ログ: AI基盤（base, router）

## 概要
- **日付**: 2025-01-05
- **Issue**: #7 AI基盤（base, router）
- **目標**: AIプロバイダーの抽象化レイヤーとルーティング機能を実装

---

## 会話の流れ

### 1. 開始
**ユーザー**: Issue #7（AI基盤）に進む

**Claude**: Issue #7の実装を開始。以下を確認:
- DEVELOPMENT_PLAN.md: Issue #7は「AI基盤（base, router）」
- ARCHITECTURE.md: AI設計の詳細
- config.yaml: AI設定の構造
- TEST_PLAN.md: RTR-01〜RTR-05のテストケース定義

### 2. 実装計画
TodoWriteで以下のタスクを作成:
1. ブランチ作成 (feature/issue-7)
2. テスト作成 (tests/test_ai_router.py)
3. base.py実装 (AIProvider抽象クラス)
4. router.py実装 (AIRouter)
5. テスト実行・修正
6. ruff/pyright チェック
7. コミット・プッシュ
8. DEVELOPMENT_LOG.md 更新
9. CONVERSATION_LOG_ISSUE7.md 作成
10. DEVELOPMENT_PLAN.md / ISSUES_STATUS.md 更新
11. mainにマージ

### 3. TDDでテスト先行実装
18件のテストケースを作成:

```python
# TEST_PLAN.md の RTR-01〜RTR-05 に対応
- test_get_default_provider (RTR-01)
- test_workspace_override (RTR-02)
- test_room_override (RTR-03)
- test_provider_not_configured (RTR-04)
- test_get_fallback_providers (RTR-05)
# 追加テスト
- test_room_override_priority
- test_provider_not_in_providers
- test_empty_config
- test_router_from_yaml_file
- test_router_from_yaml_with_env_vars
```

### 4. base.py 実装
AIProvider抽象基底クラスとエラークラスを実装:

```python
class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str: ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...
```

エラークラス:
- `AIProviderError` - 基底エラー
- `AIProviderNotConfiguredError` - プロバイダー未設定
- `AIQuotaExceededError` - API制限超過
- `AIConnectionError` - 接続エラー
- `AIResponseError` - 応答エラー

### 5. router.py 実装
AIRouterクラスを実装:

```python
class AIRouter:
    def get_provider_info(
        self,
        purpose: str,
        workspace_id: str | None = None,
        room_id: str | None = None,
    ) -> dict[str, str]:
        # 優先順位: Room > Workspace > グローバル
        ...

    def get_fallback_info(self, purpose: str) -> list[dict[str, str]]: ...

    @classmethod
    def from_yaml(cls, file_path: str) -> "AIRouter": ...
```

### 6. テスト実行
```
$ python -m pytest tests/test_ai_router.py -v
============================== 18 passed in 0.03s ==============================
```

### 7. リントチェックでエラー発見
```
F541 f-string without any placeholders
F401 unused imports
```

**修正**:
- `f"provider lookup"` → `"provider lookup"`
- 未使用インポートを削除

### 8. 全テスト成功
```
$ python -m pytest tests/ -v
============================== 60 passed in 0.33s ==============================
```

### 9. コミット
```
[feature/issue-7 38a76e1] feat: implement AI base layer and router (Issue #7)
 4 files changed, 846 insertions(+)
 create mode 100644 src/ai/base.py
 create mode 100644 src/ai/router.py
 create mode 100644 tests/test_ai_router.py
```

---

## 技術的なポイント

### 1. 抽象化設計
- `AIProvider` を抽象基底クラスとして定義
- 各プロバイダー（OpenAI, Anthropic等）は共通インターフェースを実装
- プロバイダーの差し替えが容易

### 2. ルーティングの優先順位
```
1. Room設定（room_overrides）    ← 最優先
2. Workspace設定（workspace_overrides）
3. グローバル設定（ai_routing）   ← デフォルト
```

例: 特定のRoomだけローカルLLMを使いたい場合
```yaml
room_overrides:
  room_123:
    summary:
      provider: local
      model: llama3
```

### 3. 環境変数展開
config.yamlで環境変数を参照可能:
```yaml
ai_providers:
  openai:
    api_key: ${OPENAI_API_KEY}  # 環境変数から取得
```

### 4. 責務の分離
- `AIRouter`: ルーティング判断（どのプロバイダーを使うか決める）
- `AIProvider`: 実際のAI呼び出し（Issue #8以降で実装）

---

## まとめ

### 実装の流れ
1. TEST_PLAN.md のテストケースを確認
2. TDDでテストを先に書く
3. base.py で抽象クラスとエラークラスを定義
4. router.py でルーティングロジックを実装
5. テスト実行 → リント修正 → 全テスト成功
6. コミット

### 成果物
| ファイル | 行数 | 内容 |
|----------|------|------|
| src/ai/base.py | 210 | 抽象クラス、エラークラス |
| src/ai/router.py | 255 | ルーター |
| src/ai/__init__.py | 35 | エクスポート |
| tests/test_ai_router.py | 280 | 18テストケース |

### 学んだこと
1. 抽象基底クラスで共通インターフェースを定義
2. ルーティングの優先順位設計
3. 環境変数展開でシークレット管理
4. TDDでテスト先行実装
5. 責務の分離（ルーティング vs インスタンス生成）

### 今後の改善
- Issue #8 でOpenAIプロバイダーを実装し、実際のAI呼び出しを追加
- Issue #9 で/summaryコマンドを実装し、ルーターと連携
