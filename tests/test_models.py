"""Tests for core data models."""

from datetime import datetime, timezone

from cityscope.core.models import (
    DataPoint,
    DatasetMetadata,
    FetchResult,
    Geography,
    GeoType,
)


class TestGeography:
    def test_create_metro(self):
        geo = Geography(
            geo_id="35620",
            name="New York Metro",
            geo_type=GeoType.METRO,
            population=19_500_000,
        )
        assert geo.geo_id == "35620"
        assert geo.geo_type == GeoType.METRO
        assert geo.state_fips is None
        assert geo.population == 19_500_000

    def test_create_city_with_state(self):
        geo = Geography(
            geo_id="0644000",
            name="Los Angeles city, California",
            geo_type=GeoType.CITY,
            state_fips="06",
            population=3_900_000,
        )
        assert geo.state_fips == "06"
        assert geo.geo_type == GeoType.CITY

    def test_optional_fields_default_none(self):
        geo = Geography(geo_id="1", name="Test", geo_type=GeoType.METRO)
        assert geo.state_fips is None
        assert geo.population is None
        assert geo.latitude is None
        assert geo.longitude is None


class TestDataPoint:
    def test_create_annual(self):
        dp = DataPoint(
            geo_id="35620",
            metric="population",
            year=2024,
            value=19_500_000.0,
            source="census_population",
        )
        assert dp.month == 0
        assert dp.vintage is None
        assert isinstance(dp.fetched_at, datetime)

    def test_create_with_all_fields(self):
        now = datetime.now(timezone.utc)
        dp = DataPoint(
            geo_id="35620",
            metric="unemployment_rate",
            year=2024,
            month=6,
            value=4.2,
            source="bls_employment",
            vintage="laus_2024",
            fetched_at=now,
        )
        assert dp.month == 6
        assert dp.vintage == "laus_2024"
        assert dp.fetched_at == now


class TestFetchResult:
    def test_create(self):
        result = FetchResult(
            geographies=[
                Geography(geo_id="1", name="Test", geo_type=GeoType.METRO),
            ],
            data_points=[
                DataPoint(
                    geo_id="1", metric="population", year=2024,
                    value=100_000.0, source="test",
                ),
            ],
            metadata=DatasetMetadata(
                source_id="test",
                name="Test Source",
                description="Testing",
                metrics=["population"],
                geo_types=[GeoType.METRO],
                min_year=2024,
                max_year=2024,
                record_count=1,
            ),
        )
        assert len(result.geographies) == 1
        assert len(result.data_points) == 1
        assert result.metadata.record_count == 1


class TestGeoType:
    def test_string_values(self):
        assert GeoType.METRO == "metro"
        assert GeoType.CITY == "city"
        assert GeoType.STATE == "state"

    def test_all_types_exist(self):
        expected = {"nation", "state", "metro", "county", "city", "tract", "zip", "block_group"}
        actual = {t.value for t in GeoType}
        assert actual == expected
