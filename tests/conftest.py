"""Shared test fixtures."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from cityscope.core.config import Config
from cityscope.core.models import DataPoint, Geography, GeoType
from cityscope.core.storage import Storage


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def storage(tmp_db):
    """Provide a Storage instance backed by a temp database."""
    return Storage(tmp_db)


@pytest.fixture
def config(tmp_db):
    """Provide a Config pointing to a temp database."""
    return Config(
        storage={"db_path": tmp_db},
        pipeline={"min_population": 200_000},
    )


@pytest.fixture
def sample_geographies():
    """Sample metro geographies for testing."""
    return [
        Geography(
            geo_id="35620",
            name="New York-Newark-Jersey City, NY-NJ-PA Metro Area",
            geo_type=GeoType.METRO,
            population=19_500_000,
        ),
        Geography(
            geo_id="31080",
            name="Los Angeles-Long Beach-Anaheim, CA Metro Area",
            geo_type=GeoType.METRO,
            population=13_000_000,
        ),
        Geography(
            geo_id="16980",
            name="Chicago-Naperville-Elgin, IL-IN-WI Metro Area",
            geo_type=GeoType.METRO,
            population=9_400_000,
        ),
        Geography(
            geo_id="19100",
            name="Dallas-Fort Worth-Arlington, TX Metro Area",
            geo_type=GeoType.METRO,
            population=7_600_000,
        ),
        Geography(
            geo_id="0644000",
            name="Los Angeles city, California",
            geo_type=GeoType.CITY,
            state_fips="06",
            population=3_900_000,
        ),
    ]


@pytest.fixture
def sample_data_points():
    """Sample data points for testing."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    points = []
    metros = [
        ("35620", 19_500_000, 19_600_000, 19_700_000),
        ("31080", 13_200_000, 13_100_000, 13_000_000),
        ("16980", 9_500_000, 9_450_000, 9_400_000),
        ("19100", 7_200_000, 7_400_000, 7_600_000),
    ]

    for geo_id, pop_2022, pop_2023, pop_2024 in metros:
        for year, pop in [(2022, pop_2022), (2023, pop_2023), (2024, pop_2024)]:
            points.append(DataPoint(
                geo_id=geo_id, metric="population", year=year,
                value=float(pop), source="census_population",
                vintage="test", fetched_at=now,
            ))

        # Growth rates
        change_23 = pop_2023 - pop_2022
        pct_23 = change_23 / pop_2022 * 100
        change_24 = pop_2024 - pop_2023
        pct_24 = change_24 / pop_2023 * 100

        for year, change, pct in [(2023, change_23, pct_23), (2024, change_24, pct_24)]:
            points.append(DataPoint(
                geo_id=geo_id, metric="population_change", year=year,
                value=float(change), source="census_population",
                vintage="test", fetched_at=now,
            ))
            points.append(DataPoint(
                geo_id=geo_id, metric="population_change_pct", year=year,
                value=round(pct, 4), source="census_population",
                vintage="test", fetched_at=now,
            ))

    return points
