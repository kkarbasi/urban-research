"""Tests for the public Python API."""

import pytest

from cityscope import api
from cityscope.core.config import Config
from cityscope.core.storage import Storage


@pytest.fixture(autouse=True)
def reset_api_state():
    """Reset global API state between tests."""
    api._config = None
    api._storage = None
    yield
    api._config = None
    api._storage = None


class TestConfigure:
    def test_returns_config(self, tmp_db):
        config = api.configure(db_path=tmp_db)
        assert isinstance(config, Config)
        assert config.storage.db_path == tmp_db

    def test_sets_min_population(self, tmp_db):
        config = api.configure(db_path=tmp_db, min_population=100_000)
        assert config.pipeline.min_population == 100_000

    def test_sets_api_keys(self, tmp_db):
        config = api.configure(
            db_path=tmp_db,
            census_api_key="census123",
            bls_api_key="bls456",
        )
        assert config.census.api_key == "census123"
        assert config.bls.api_key == "bls456"

    def test_loads_from_yaml(self, tmp_path):
        yaml = tmp_path / "test.yaml"
        yaml.write_text("pipeline:\n  min_population: 50000\n")

        config = api.configure(config_path=yaml)
        assert config.pipeline.min_population == 50_000


class TestListSources:
    def test_returns_list(self):
        sources = api.list_sources()
        assert isinstance(sources, list)
        assert len(sources) >= 2

    def test_source_dict_structure(self):
        sources = api.list_sources()
        for s in sources:
            assert "id" in s
            assert "name" in s
            assert "description" in s

    def test_contains_expected_sources(self):
        ids = {s["id"] for s in api.list_sources()}
        assert "census_population" in ids
        assert "bls_employment" in ids


class TestQuery:
    def test_empty_database(self, tmp_db):
        api.configure(db_path=tmp_db)
        rows = api.query()
        assert rows == []

    def test_with_data(self, tmp_db, sample_geographies, sample_data_points):
        api.configure(db_path=tmp_db)
        storage = Storage(tmp_db)
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        rows = api.query(metric="population", year=2024)
        assert len(rows) > 0
        assert all(r["metric"] == "population" for r in rows)
        assert all(r["year"] == 2024 for r in rows)

    def test_filter_by_geo_type(self, tmp_db, sample_geographies, sample_data_points):
        api.configure(db_path=tmp_db)
        storage = Storage(tmp_db)
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        rows = api.query(geo_type="metro")
        assert all(r["geo_type"] == "metro" for r in rows)

    def test_limit(self, tmp_db, sample_geographies, sample_data_points):
        api.configure(db_path=tmp_db)
        storage = Storage(tmp_db)
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        rows = api.query(limit=5)
        assert len(rows) == 5


class TestGetGeographies:
    def test_empty(self, tmp_db):
        api.configure(db_path=tmp_db)
        assert api.get_geographies() == []

    def test_with_data(self, tmp_db, sample_geographies):
        api.configure(db_path=tmp_db)
        storage = Storage(tmp_db)
        storage.upsert_geographies(sample_geographies)

        geos = api.get_geographies()
        assert len(geos) == 5

    def test_filter_metro(self, tmp_db, sample_geographies):
        api.configure(db_path=tmp_db)
        storage = Storage(tmp_db)
        storage.upsert_geographies(sample_geographies)

        metros = api.get_geographies(geo_type="metro")
        assert len(metros) == 4


class TestStatus:
    def test_empty(self, tmp_db):
        api.configure(db_path=tmp_db)
        assert api.status() == []

    def test_with_data(self, tmp_db, sample_geographies, sample_data_points):
        api.configure(db_path=tmp_db)
        storage = Storage(tmp_db)
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        summary = api.status()
        assert len(summary) > 0
        assert any(r["source"] == "census_population" for r in summary)


class TestToDataframe:
    def test_returns_dataframe(self, tmp_db, sample_geographies, sample_data_points):
        import pandas as pd

        api.configure(db_path=tmp_db)
        storage = Storage(tmp_db)
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        df = api.to_dataframe(metric="population")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "geo_id" in df.columns
        assert "value" in df.columns
        assert "name" in df.columns

    def test_empty_result(self, tmp_db):
        import pandas as pd

        api.configure(db_path=tmp_db)
        df = api.to_dataframe(metric="nonexistent")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestFetch:
    def test_raises_without_source(self, tmp_db):
        api.configure(db_path=tmp_db)
        with pytest.raises(ValueError, match="Provide source_id"):
            api.fetch()
