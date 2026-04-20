"""Tests for Census population source with mocked API responses."""

import json

import httpx
import pytest

from cityscope.core.config import Config
from cityscope.core.models import GeoType
from cityscope.sources.census_population import (
    CensusPopulationSource,
    _build_models,
)


class TestParseStateFips:
    """Test extraction of state FIPS from Census API metro names."""

    # This is used by the BLS source too — tested here at the origin.

    def test_single_state(self):
        from cityscope.sources.bls_employment import _parse_principal_state_fips as parse
        assert parse("Dallas-Fort Worth-Arlington, TX Metro Area") == "48"

    def test_multi_state_returns_first(self):
        from cityscope.sources.bls_employment import _parse_principal_state_fips as parse
        assert parse("New York-Newark-Jersey City, NY-NJ-PA Metro Area") == "36"
        assert parse("Washington-Arlington-Alexandria, DC-VA-MD-WV Metro Area") == "11"

    def test_dc(self):
        from cityscope.sources.bls_employment import _parse_principal_state_fips as parse
        assert parse("Washington-Arlington-Alexandria, DC-VA-MD-WV Metro Area") == "11"

    def test_no_match_returns_none(self):
        from cityscope.sources.bls_employment import _parse_principal_state_fips as parse
        assert parse("Some random string") is None


class TestBuildModels:
    """Test the shared model builder used by both metro and city fetch paths."""

    def test_basic_population(self):
        pop_by_geo = {
            "12345": {2022: 100_000, 2023: 102_000, 2024: 105_000},
        }
        name_by_geo = {"12345": "Test Metro"}
        geos, points = _build_models(pop_by_geo, name_by_geo, GeoType.METRO, "test")

        assert len(geos) == 1
        assert geos[0].geo_id == "12345"
        assert geos[0].population == 105_000  # latest year
        assert geos[0].geo_type == GeoType.METRO

        metrics = {p.metric for p in points}
        assert "population" in metrics
        assert "population_change" in metrics
        assert "population_change_pct" in metrics

    def test_population_counts(self):
        pop_by_geo = {
            "A": {2022: 100_000, 2023: 110_000, 2024: 120_000},
        }
        geos, points = _build_models(pop_by_geo, {"A": "Test"}, GeoType.METRO, "v")

        pop_points = [p for p in points if p.metric == "population"]
        change_points = [p for p in points if p.metric == "population_change"]
        pct_points = [p for p in points if p.metric == "population_change_pct"]

        assert len(pop_points) == 3  # 2022, 2023, 2024
        assert len(change_points) == 2  # 2023, 2024
        assert len(pct_points) == 2

    def test_growth_rate_calculation(self):
        pop_by_geo = {
            "A": {2022: 100_000, 2023: 110_000},
        }
        _, points = _build_models(pop_by_geo, {"A": "Test"}, GeoType.METRO, "v")

        pct = [p for p in points if p.metric == "population_change_pct" and p.year == 2023]
        assert len(pct) == 1
        assert pct[0].value == 10.0  # (110k - 100k) / 100k * 100

        change = [p for p in points if p.metric == "population_change" and p.year == 2023]
        assert change[0].value == 10_000.0

    def test_declining_population(self):
        pop_by_geo = {
            "A": {2022: 100_000, 2023: 95_000},
        }
        _, points = _build_models(pop_by_geo, {"A": "Test"}, GeoType.METRO, "v")

        pct = [p for p in points if p.metric == "population_change_pct"]
        assert pct[0].value == -5.0

    def test_empty_input(self):
        geos, points = _build_models({}, {}, GeoType.METRO, "v")
        assert geos == []
        assert points == []

    def test_single_year_no_changes(self):
        pop_by_geo = {"A": {2024: 500_000}}
        geos, points = _build_models(pop_by_geo, {"A": "Test"}, GeoType.METRO, "v")

        assert len(geos) == 1
        pop_points = [p for p in points if p.metric == "population"]
        change_points = [p for p in points if p.metric == "population_change"]
        assert len(pop_points) == 1
        assert len(change_points) == 0  # no change with single year

    def test_multiple_geos(self):
        pop_by_geo = {
            "A": {2023: 100_000, 2024: 110_000},
            "B": {2023: 200_000, 2024: 190_000},
        }
        names = {"A": "Growing City", "B": "Shrinking City"}
        geos, points = _build_models(pop_by_geo, names, GeoType.CITY, "v")

        assert len(geos) == 2
        a_pct = [p for p in points if p.geo_id == "A" and p.metric == "population_change_pct"]
        b_pct = [p for p in points if p.geo_id == "B" and p.metric == "population_change_pct"]
        assert a_pct[0].value == 10.0
        assert b_pct[0].value == -5.0


class TestCensusPopulationSource:
    def test_has_correct_metadata(self, config):
        source = CensusPopulationSource(config)
        assert source.source_id == "census_population"
        assert source.name == "Census Bureau Population Estimates"
