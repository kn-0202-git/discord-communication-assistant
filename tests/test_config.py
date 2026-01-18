"""AppConfig テスト."""

from pathlib import Path

from src.config import AppConfig


class TestAppConfig:
    """AppConfigのテスト."""

    def test_from_yaml_loads_config(self, tmp_path: Path) -> None:
        """YAMLファイルから設定を読み込める."""
        config_content = """
google_drive:
  enabled: true
  auto_upload: false
  root_folder_id: "test-folder-id"

attachments:
  max_size_bytes: 10485760

ai_providers:
  openai:
    api_key: "test-key"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = AppConfig.from_yaml(config_file)

        assert config.google_drive["enabled"] is True
        assert config.google_drive["root_folder_id"] == "test-folder-id"
        assert config.attachments["max_size_bytes"] == 10485760

    def test_from_yaml_returns_empty_for_missing_file(self) -> None:
        """存在しないファイルの場合、空の設定を返す."""
        config = AppConfig.from_yaml(Path("/nonexistent/config.yaml"))

        assert config.raw == {}
        assert config.google_drive == {}
        assert config.attachments == {}

    def test_from_yaml_returns_empty_for_invalid_yaml(self, tmp_path: Path) -> None:
        """不正なYAMLの場合、空の設定を返す."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        config = AppConfig.from_yaml(config_file)

        assert config.raw == {}

    def test_google_drive_property_returns_empty_dict_if_not_set(self) -> None:
        """google_driveが未設定の場合、空のdictを返す."""
        config = AppConfig({})

        assert config.google_drive == {}

    def test_attachments_property_returns_empty_dict_if_not_set(self) -> None:
        """attachmentsが未設定の場合、空のdictを返す."""
        config = AppConfig({})

        assert config.attachments == {}

    def test_ai_providers_property(self) -> None:
        """ai_providersプロパティが正しく動作する."""
        config = AppConfig(
            {
                "ai_providers": {
                    "openai": {"api_key": "test"},
                },
            }
        )

        assert config.ai_providers["openai"]["api_key"] == "test"

    def test_ai_routing_property(self) -> None:
        """ai_routingプロパティが正しく動作する."""
        config = AppConfig(
            {
                "ai_routing": {
                    "summary": {"provider": "openai", "model": "gpt-4o"},
                },
            }
        )

        assert config.ai_routing["summary"]["provider"] == "openai"

    def test_get_method_returns_value(self) -> None:
        """getメソッドが値を返す."""
        config = AppConfig({"key": "value"})

        assert config.get("key") == "value"

    def test_get_method_returns_default_for_missing_key(self) -> None:
        """getメソッドが未設定キーにデフォルト値を返す."""
        config = AppConfig({})

        assert config.get("missing", "default") == "default"

    def test_bool_returns_true_for_non_empty_config(self) -> None:
        """設定があればTrueを返す."""
        config = AppConfig({"key": "value"})

        assert bool(config) is True

    def test_bool_returns_false_for_empty_config(self) -> None:
        """設定が空ならFalseを返す."""
        config = AppConfig({})

        assert bool(config) is False
