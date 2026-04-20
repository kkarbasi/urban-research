"""Tests for SQLite storage layer."""

import sqlite3

from cityscope.core.models import DataPoint, Geography, GeoType
from cityscope.core.storage import Storage


class TestStorageInit:
    def test_creates_database_file(self, tmp_path):
        db_path = tmp_path / "subdir" / "test.db"
        storage = Storage(db_path)
        assert db_path.exists()

    def test_creates_tables(self, storage, tmp_db):
        conn = sqlite3.connect(tmp_db)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}
        assert "geographies" in table_names
        assert "data_points" in table_names

    def test_idempotent_init(self, tmp_db):
        Storage(tmp_db)
        Storage(tmp_db)  # Should not raise


class TestUpsertGeographies:
    def test_insert_new(self, storage, sample_geographies):
        count = storage.upsert_geographies(sample_geographies)
        assert count == 5

    def test_upsert_updates_existing(self, storage):
        geo = Geography(geo_id="1", name="Old Name", geo_type=GeoType.METRO, population=100)
        storage.upsert_geographies([geo])

        geo_updated = Geography(geo_id="1", name="New Name", geo_type=GeoType.METRO, population=200)
        storage.upsert_geographies([geo_updated])

        results = storage.get_geographies()
        assert len(results) == 1
        assert results[0]["name"] == "New Name"
        assert results[0]["population"] == 200

    def test_empty_list(self, storage):
        count = storage.upsert_geographies([])
        assert count == 0


class TestUpsertDataPoints:
    def test_insert_new(self, storage, sample_geographies, sample_data_points):
        storage.upsert_geographies(sample_geographies)
        count = storage.upsert_data_points(sample_data_points)
        assert count == len(sample_data_points)

    def test_upsert_replaces_value(self, storage, sample_geographies):
        from datetime import datetime, timezone

        storage.upsert_geographies(sample_geographies)
        now = datetime.now(timezone.utc)

        dp1 = DataPoint(
            geo_id="35620", metric="population", year=2024,
            value=100.0, source="test", fetched_at=now,
        )
        storage.upsert_data_points([dp1])

        dp2 = DataPoint(
            geo_id="35620", metric="population", year=2024,
            value=200.0, source="test", fetched_at=now,
        )
        storage.upsert_data_points([dp2])

        rows = storage.query_data(metric="population", year=2024)
        values = [r["value"] for r in rows if r["geo_id"] == "35620"]
        assert values == [200.0]


class TestQueryData:
    def test_filter_by_metric(self, storage, sample_geographies, sample_data_points):
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        rows = storage.query_data(metric="population")
        assert all(r["metric"] == "population" for r in rows)

    def test_filter_by_geo_type(self, storage, sample_geographies, sample_data_points):
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        rows = storage.query_data(geo_type="metro")
        assert all(r["geo_type"] == "metro" for r in rows)

    def test_filter_by_year(self, storage, sample_geographies, sample_data_points):
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        rows = storage.query_data(year=2024)
        assert all(r["year"] == 2024 for r in rows)

    def test_filter_by_min_population(self, storage, sample_geographies, sample_data_points):
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        rows = storage.query_data(min_population=10_000_000)
        geo_ids = {r["geo_id"] for r in rows}
        assert "35620" in geo_ids  # NYC (19.5M)
        assert "31080" in geo_ids  # LA (13M)
        assert "19100" not in geo_ids  # Dallas (7.6M)

    def test_limit(self, storage, sample_geographies, sample_data_points):
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        rows = storage.query_data(limit=3)
        assert len(rows) == 3

    def test_empty_result(self, storage):
        rows = storage.query_data(metric="nonexistent")
        assert rows == []


class TestGetGeographies:
    def test_all(self, storage, sample_geographies):
        storage.upsert_geographies(sample_geographies)
        results = storage.get_geographies()
        assert len(results) == 5

    def test_filter_by_type(self, storage, sample_geographies):
        storage.upsert_geographies(sample_geographies)
        metros = storage.get_geographies(geo_type="metro")
        assert len(metros) == 4
        assert all(r["geo_type"] == "metro" for r in metros)

    def test_filter_by_min_pop(self, storage, sample_geographies):
        storage.upsert_geographies(sample_geographies)
        large = storage.get_geographies(min_population=10_000_000)
        assert len(large) == 2  # NYC + LA


class TestGetSourcesSummary:
    def test_returns_summary(self, storage, sample_geographies, sample_data_points):
        storage.upsert_geographies(sample_geographies)
        storage.upsert_data_points(sample_data_points)

        summary = storage.get_sources_summary()
        assert len(summary) > 0
        sources = {r["source"] for r in summary}
        assert "census_population" in sources

    def test_empty_database(self, storage):
        summary = storage.get_sources_summary()
        assert summary == []
