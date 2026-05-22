"""Tests for bls_qcew_industry source.

Network calls are intercepted by patching _fetch_area_industry_data so tests
run without hitting BLS servers.
"""

from unittest.mock import MagicMock, patch

import pytest

from cityscope.core.models import GeoType
from cityscope.sources.bls_qcew_industry import BLSQCEWIndustrySource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_sector_data():
    """Three sectors: Info (high LQ), Finance, Construction."""
    return {
        "51": {"emp": 80_000.0, "lq": 3.2},   # Information — highest LQ
        "52": {"emp": 50_000.0, "lq": 1.8},   # Finance & Insurance
        "23": {"emp": 30_000.0, "lq": 0.9},   # Construction
    }


def _make_fake_sector_data_with_manufacturing():
    """Sectors where Manufacturing (31-33) wins on LQ."""
    return {
        "31-33": {"emp": 120_000.0, "lq": 4.5},  # Manufacturing — highest LQ
        "51":    {"emp":  80_000.0, "lq": 3.2},
        "23":    {"emp":  30_000.0, "lq": 0.9},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBLSQCEWIndustrySource:
    def test_metadata(self, config):
        source = BLSQCEWIndustrySource(config)
        assert source.source_id == "bls_qcew_industry"
        assert GeoType.METRO in source.supported_geo_types_for_lookup
        assert GeoType.COUNTY in source.supported_geo_types_for_lookup

    def test_fetch_for_geo_emits_per_sector_metrics(self, config):
        """fetch_for_geo emits emp_naics_* and lq_naics_* for each sector returned."""
        fake = _make_fake_sector_data()
        source = BLSQCEWIndustrySource(config)

        with patch(
            "cityscope.sources.bls_qcew_industry._fetch_area_industry_data",
            return_value=fake,
        ):
            result = source.fetch_for_geo("41940", GeoType.METRO)

        metrics = {p.metric: p.value for p in result.data_points}

        assert metrics["emp_naics_51"] == 80_000.0
        assert metrics["lq_naics_51"] == 3.2
        assert metrics["emp_naics_52"] == 50_000.0
        assert metrics["lq_naics_52"] == 1.8
        assert metrics["emp_naics_23"] == 30_000.0
        assert metrics["lq_naics_23"] == 0.9

        # All points belong to the requested geo
        assert all(p.geo_id == "41940" for p in result.data_points)
        assert all(p.source == "bls_qcew_industry" for p in result.data_points)

    def test_fetch_for_geo_computes_top_industry(self, config):
        """top_industry_naics_code should be the sector with highest LQ (emp > 0)."""
        fake = _make_fake_sector_data()
        source = BLSQCEWIndustrySource(config)

        with patch(
            "cityscope.sources.bls_qcew_industry._fetch_area_industry_data",
            return_value=fake,
        ):
            result = source.fetch_for_geo("41940", GeoType.METRO)

        metrics = {p.metric: p.value for p in result.data_points}

        # Sector "51" (Information) has highest LQ (3.2)
        assert metrics["top_industry_naics_code"] == 51.0
        assert metrics["top_industry_lq"] == 3.2

        total_emp = 80_000 + 50_000 + 30_000
        expected_share = 80_000 / total_emp
        assert abs(metrics["top_industry_emp_share"] - expected_share) < 1e-9

    def test_fetch_for_geo_compound_code_normalized(self, config):
        """Compound codes like '31-33' → metric 'emp_naics_31_33'; top code is 31.0."""
        fake = _make_fake_sector_data_with_manufacturing()
        source = BLSQCEWIndustrySource(config)

        with patch(
            "cityscope.sources.bls_qcew_industry._fetch_area_industry_data",
            return_value=fake,
        ):
            result = source.fetch_for_geo("26420", GeoType.METRO)

        metrics = {p.metric: p.value for p in result.data_points}

        # Metric name uses underscore, not hyphen
        assert "emp_naics_31_33" in metrics
        assert "lq_naics_31_33" in metrics
        assert metrics["emp_naics_31_33"] == 120_000.0

        # top_industry_naics_code uses first part of compound code as float
        assert metrics["top_industry_naics_code"] == 31.0
        assert metrics["top_industry_lq"] == 4.5

    def test_fetch_for_geo_rejects_non_metro_or_county(self, config):
        source = BLSQCEWIndustrySource(config)
        with pytest.raises(NotImplementedError):
            source.fetch_for_geo("12345", GeoType.CITY)

    def test_fetch_for_geo_rejects_bad_geo_id_length(self, config):
        source = BLSQCEWIndustrySource(config)
        with pytest.raises(ValueError, match="5 digits"):
            source.fetch_for_geo("12345678", GeoType.METRO)

    def test_fetch_for_geo_handles_empty_area(self, config):
        """Helper returning empty dict → zero data points, no crash."""
        source = BLSQCEWIndustrySource(config)

        with patch(
            "cityscope.sources.bls_qcew_industry._fetch_area_industry_data",
            return_value={},
        ):
            result = source.fetch_for_geo("41940", GeoType.METRO)

        assert result.data_points == []

    def test_fetch_for_geo_handles_none_from_helper(self, config):
        """Helper returning None (HTTP error) → zero data points, no crash."""
        source = BLSQCEWIndustrySource(config)

        with patch(
            "cityscope.sources.bls_qcew_industry._fetch_area_industry_data",
            return_value=None,
        ):
            result = source.fetch_for_geo("41940", GeoType.METRO)

        assert result.data_points == []

    def test_bulk_fetch_emits_points_for_metros(self, config):
        """Bulk fetch() should emit data points for each metro × year."""
        fake_metros = [
            {"geo_id": "41940", "name": "San Jose Metro"},
            {"geo_id": "35620", "name": "New York Metro"},
        ]
        fake_sector_data = {
            "51": {"emp": 50_000.0, "lq": 2.5},
            "52": {"emp": 30_000.0, "lq": 1.2},
        }

        source = BLSQCEWIndustrySource(config)

        with (
            patch(
                "cityscope.sources.bls_qcew_industry.Storage"
            ) as MockStorage,
            patch(
                "cityscope.sources.bls_qcew_industry._fetch_area_industry_data",
                return_value=fake_sector_data,
            ),
        ):
            mock_storage_instance = MagicMock()
            mock_storage_instance.get_geographies.return_value = fake_metros
            MockStorage.return_value = mock_storage_instance

            result = source.fetch(start_year=2022, end_year=2022)

        geo_ids = {p.geo_id for p in result.data_points}
        assert "41940" in geo_ids
        assert "35620" in geo_ids

        # 2 sectors × 2 metrics (emp + lq) + 3 derived = 7 per metro × year
        assert len(result.data_points) == 7 * 2  # 2 metros, 1 year
        assert result.metadata.source_id == "bls_qcew_industry"
        assert GeoType.METRO in result.metadata.geo_types
