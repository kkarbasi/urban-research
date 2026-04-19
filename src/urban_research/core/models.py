from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class GeoType(str, Enum):
    NATION = "nation"
    STATE = "state"
    METRO = "metro"
    COUNTY = "county"
    CITY = "city"
    TRACT = "tract"
    ZIP = "zip"
    BLOCK_GROUP = "block_group"


class Geography(BaseModel):
    geo_id: str
    name: str
    geo_type: GeoType
    state_fips: str | None = None
    population: int | None = None
    latitude: float | None = None
    longitude: float | None = None


class DataPoint(BaseModel):
    geo_id: str
    metric: str
    year: int
    month: int = 0
    value: float
    source: str
    vintage: str | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DatasetMetadata(BaseModel):
    source_id: str
    name: str
    description: str
    metrics: list[str]
    geo_types: list[GeoType]
    min_year: int
    max_year: int
    last_fetched: datetime | None = None
    record_count: int = 0


class FetchResult(BaseModel):
    geographies: list[Geography]
    data_points: list[DataPoint]
    metadata: DatasetMetadata
