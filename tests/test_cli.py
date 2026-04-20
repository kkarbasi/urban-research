"""Tests for the CLI interface."""

from click.testing import CliRunner

from cityscope.cli import cli


class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Cityscope" in result.output

    def test_sources_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sources"])
        assert result.exit_code == 0
        assert "census_population" in result.output
        assert "bls_employment" in result.output

    def test_status_empty(self, tmp_path):
        runner = CliRunner()
        config_file = tmp_path / "cfg.yaml"
        config_file.write_text(f"storage:\n  db_path: {tmp_path / 'test.db'}\n")

        result = runner.invoke(cli, ["-c", str(config_file), "status"])
        assert result.exit_code == 0
        assert "No data fetched" in result.output

    def test_query_empty(self, tmp_path):
        runner = CliRunner()
        config_file = tmp_path / "cfg.yaml"
        config_file.write_text(f"storage:\n  db_path: {tmp_path / 'test.db'}\n")

        result = runner.invoke(cli, ["-c", str(config_file), "query"])
        assert result.exit_code == 0
        assert "No data found" in result.output

    def test_fetch_no_source(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code == 0
        assert "Specify a source ID" in result.output

    def test_init_config(self, tmp_path):
        runner = CliRunner()
        output_path = tmp_path / "new_config.yaml"
        result = runner.invoke(cli, ["init-config", "--path", str(output_path)])
        assert result.exit_code == 0
        assert output_path.exists()

    def test_init_config_exists(self, tmp_path):
        runner = CliRunner()
        output_path = tmp_path / "existing.yaml"
        output_path.write_text("existing: true")
        result = runner.invoke(cli, ["init-config", "--path", str(output_path)])
        assert "already" in result.output and "exists" in result.output
