"""Tests for bea_gdp_industry source.

Mock _fetch_bea_area_gdp to avoid network calls.
"""

from unittest.mock import patch

import pytest

from cityscope.core.config import Config
from cityscope.core.models import GeoType
from cityscope.sources.bea_gdp_industry import BEAGDPIndustrySource


def _make_config_with_key(tmp_db: str) -> Config:
    return Config(
        storage={"db_path": tmp_db},
        pipeline={"min_population": 200_000},
        bea={"api_key": "fake_key"},
    )


def _make_records(
    year: int,
    industry_values: dict[int, float],
    total_value: float,
) -> list[dict]:
    """Build a list of raw BEA records for a single year."""
    records = [{"year": year, "line_code": 1, "value_thousands": total_value}]
    for code, val in industry_values.items():
        records.append({"year": year, "line_code": code, "value_thousands": val})
    return records


class TestBEAGDPIndustrySource:
    def test_metadata(self, config):
        source = BEAGDPIndustrySource(config)
        assert source.source_id == "bea_gdp_industry"
        assert GeoType.METRO in source.supported_geo_types_for_lookup
        assert GeoType.COUNTY in source.supported_geo_types_for_lookup
        assert "GDP" in source.description

    def test_fetch_without_api_key_raises_in_bulk_fetch(self, config):
        # config fixture has no bea.api_key
        source = BEAGDPIndustrySource(config)
        with pytest.raises(RuntimeError, match="BEA API key required"):
            source.fetch()

    def test_fetch_for_geo_without_api_key_returns_empty(self, config):
        source = BEAGDPIndustrySource(config)
        result = source.fetch_for_geo("41940", GeoType.METRO)
        assert result.data_points == []

    def test_fetch_for_geo_emits_gdp_metrics(self, tmp_db):
        config = _make_config_with_key(tmp_db)
        source = BEAGDPIndustrySource(config)

        # 3 industries + total, one year
        records = _make_records(
            year=2023,
            industry_values={12: 180_000.0, 51: 90_000.0, 60: 60_000.0},
            total_value=400_000.0,
        )

        with patch(
            "cityscope.sources.bea_gdp_industry._fetch_bea_area_gdp",
            return_value=records,
        ):
            result = source.fetch_for_geo("41940", GeoType.METRO)

        metrics = {p.metric: p.value for p in result.data_points}

        # gdp_total: 400_000 thousands / 1000 = 400.0 millions
        assert metrics["gdp_total"] == pytest.approx(400.0)

        # per-industry in millions
        assert metrics["gdp_industry_12"] == pytest.approx(180.0)
        assert metrics["gdp_industry_51"] == pytest.approx(90.0)
        assert metrics["gdp_industry_60"] == pytest.approx(60.0)

        # shares
        assert metrics["gdp_share_industry_12"] == pytest.approx(180_000 / 400_000)
        assert metrics["gdp_share_industry_51"] == pytest.approx(90_000 / 400_000)
        assert metrics["gdp_share_industry_60"] == pytest.approx(60_000 / 400_000)

    def test_fetch_for_geo_computes_top_industry(self, tmp_db):
        config = _make_config_with_key(tmp_db)
        source = BEAGDPIndustrySource(config)

        # code 51 (Finance) has the largest non-aggregate value
        records = _make_records(
            year=2023,
            industry_values={12: 100_000.0, 51: 200_000.0, 60: 50_000.0},
            total_value=500_000.0,
        )

        with patch(
            "cityscope.sources.bea_gdp_industry._fetch_bea_area_gdp",
            return_value=records,
        ):
            result = source.fetch_for_geo("41940", GeoType.METRO)

        metrics = {p.metric: p.value for p in result.data_points}
        assert metrics["top_gdp_industry_code"] == 51.0
        assert metrics["top_gdp_industry_share"] == pytest.approx(200_000 / 500_000)

    def test_fetch_for_geo_excludes_aggregates_from_top(self, tmp_db):
        config = _make_config_with_key(tmp_db)
        source = BEAGDPIndustrySource(config)

        # codes 1 (All industry total) and 2 (Private industries) have huge values
        # but must be excluded; code 51 should win
        records = [
            {"year": 2023, "line_code": 1, "value_thousands": 1_000_000.0},
            {"year": 2023, "line_code": 2, "value_thousands": 900_000.0},
            {"year": 2023, "line_code": 51, "value_thousands": 200_000.0},
        ]

        with patch(
            "cityscope.sources.bea_gdp_industry._fetch_bea_area_gdp",
            return_value=records,
        ):
            result = source.fetch_for_geo("41940", GeoType.METRO)

        metrics = {p.metric: p.value for p in result.data_points}
        assert metrics["top_gdp_industry_code"] == 51.0

    def test_fetch_for_geo_uses_correct_table_per_geo_type(self, tmp_db):
        config = _make_config_with_key(tmp_db)
        source = BEAGDPIndustrySource(config)

        records = _make_records(
            year=2023,
            industry_values={12: 100_000.0},
            total_value=200_000.0,
        )

        with patch(
            "cityscope.sources.bea_gdp_industry._fetch_bea_area_gdp",
            return_value=records,
        ) as mock_fn:
            source.fetch_for_geo("41940", GeoType.METRO)
            table_used_metro = mock_fn.call_args[0][0]

            source.fetch_for_geo("06085", GeoType.COUNTY)
            table_used_county = mock_fn.call_args[0][0]

        assert table_used_metro == "MAGDP2"
        assert table_used_county == "CAGDP2"

    def test_fetch_for_geo_handles_suppressed_values(self, tmp_db):
        config = _make_config_with_key(tmp_db)
        source = BEAGDPIndustrySource(config)

        # None value_thousands means the record was already filtered by the helper;
        # simulate by simply omitting that industry from the records
        records = [
            {"year": 2023, "line_code": 1, "value_thousands": 300_000.0},
            {"year": 2023, "line_code": 12, "value_thousands": 100_000.0},
            # code 51 suppressed — not present
        ]

        with patch(
            "cityscope.sources.bea_gdp_industry._fetch_bea_area_gdp",
            return_value=records,
        ):
            result = source.fetch_for_geo("41940", GeoType.METRO)

        # Should not crash; code 51 simply absent
        metrics = {p.metric for p in result.data_points}
        assert "gdp_industry_12" in metrics
        assert "gdp_industry_51" not in metrics

    def test_fetch_for_geo_rejects_non_metro_or_county(self, tmp_db):
        config = _make_config_with_key(tmp_db)
        source = BEAGDPIndustrySource(config)
        with pytest.raises(NotImplementedError):
            source.fetch_for_geo("0644000", GeoType.CITY)

    def test_fetch_for_geo_rejects_bad_geo_id_length(self, tmp_db):
        config = _make_config_with_key(tmp_db)
        source = BEAGDPIndustrySource(config)
        with pytest.raises(ValueError, match="5 digits"):
            source.fetch_for_geo("12345678", GeoType.METRO)
