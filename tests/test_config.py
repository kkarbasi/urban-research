"""Tests for configuration management."""

from pathlib import Path

from urban_research.core.config import Config


class TestConfigDefaults:
    def test_default_values(self):
        config = Config()
        assert config.census.api_key is None
        assert config.bls.api_key is None
        assert config.storage.db_path == "data/urban_research.db"
        assert config.pipeline.min_population == 200_000
        assert config.pipeline.default_vintage is None


class TestConfigLoad:
    def test_load_from_yaml(self, tmp_path):
        yaml_content = """
census:
  api_key: test_census_key
bls:
  api_key: test_bls_key
storage:
  db_path: custom/path.db
pipeline:
  min_population: 100000
  default_vintage: 2023
"""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(yaml_content)

        config = Config.load(config_file)
        assert config.census.api_key == "test_census_key"
        assert config.bls.api_key == "test_bls_key"
        assert config.storage.db_path == "custom/path.db"
        assert config.pipeline.min_population == 100_000
        assert config.pipeline.default_vintage == 2023

    def test_load_nonexistent_returns_defaults(self):
        config = Config.load(Path("/nonexistent/path.yaml"))
        assert config.pipeline.min_population == 200_000

    def test_load_empty_file(self, tmp_path):
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        config = Config.load(config_file)
        assert config.pipeline.min_population == 200_000

    def test_partial_config(self, tmp_path):
        yaml_content = """
pipeline:
  min_population: 50000
"""
        config_file = tmp_path / "partial.yaml"
        config_file.write_text(yaml_content)

        config = Config.load(config_file)
        assert config.pipeline.min_population == 50_000
        assert config.census.api_key is None  # default


class TestConfigSave:
    def test_save_and_reload(self, tmp_path):
        config = Config()
        config.census.api_key = "saved_key"
        config.pipeline.min_population = 300_000

        path = tmp_path / "output.yaml"
        config.save(path)

        loaded = Config.load(path)
        assert loaded.census.api_key == "saved_key"
        assert loaded.pipeline.min_population == 300_000

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "config.yaml"
        Config().save(path)
        assert path.exists()
