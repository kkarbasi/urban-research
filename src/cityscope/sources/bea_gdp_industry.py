"""BEA Regional GDP by Industry source.

Pulls GDP-by-industry data for metros (MAGDP2) and counties (CAGDP2) from the
BEA Regional Data API. Identifies dominant industries by dollar contribution to GDP.

Values from BEA are in thousands of dollars; we store as millions of dollars.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from ..core.config import Config
from ..core.models import (
    DataPoint,
    DatasetMetadata,
    FetchResult,
    GeoType,
)
from ..core.registry import SourceRegistry
from ..core.source import DataSource
from ..core.storage import Storage

logger = logging.getLogger(__name__)

BEA_API_BASE = "https://apps.bea.gov/api/data/"
TIMEOUT = 120.0
USER_AGENT = "cityscope/0.4.0"

# LineCode → industry name (shared by CAGDP2 and MAGDP2)
INDUSTRIES: dict[int, str] = {
    1:  "All industry total",
    2:  "Private industries",
    3:  "Agriculture, forestry, fishing and hunting",
    6:  "Mining, quarrying, and oil and gas extraction",
    10: "Utilities",
    11: "Construction",
    12: "Manufacturing",
    34: "Wholesale trade",
    35: "Retail trade",
    36: "Transportation and warehousing",
    45: "Information",
    51: "Finance and insurance",
    56: "Real estate and rental and leasing",
    60: "Professional, scientific, and technical services",
    64: "Management of companies and enterprises",
    65: "Administrative and support and waste management services",
    69: "Educational services",
    70: "Health care and social assistance",
    75: "Arts, entertainment, and recreation",
    78: "Accommodation and food services",
    82: "Other services (except government and government enterprises)",
    83: "Government and government enterprises",
}

# Aggregate line codes excluded when finding the top single industry
_AGGREGATE_CODES = {1, 2}


def _fetch_bea_area_gdp(table: str, geo_fips: str, api_key: str) -> list[dict] | None:
    """Fetch BEA GDP data for one area. Returns normalized records or None on HTTP error.

    Each record: {"year": int, "line_code": int, "value_thousands": float}
    Suppressed values ("(D)", "(NA)") are omitted.
    """
    params = {
        "UserID": api_key,
        "method": "GetData",
        "DatasetName": "Regional",
        "TableName": table,
        "GeoFips": geo_fips,
        "LineCode": "ALL",
        "Year": "ALL",
        "ResultFormat": "JSON",
    }

    try:
        with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(BEA_API_BASE, params=params)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("BEA API request failed for %s %s: %s", table, geo_fips, e)
        return None

    try:
        payload = resp.json()
        rows = payload["BEAAPI"]["Results"]["Data"]
    except (KeyError, ValueError) as e:
        logger.warning("BEA API unexpected response for %s %s: %s", table, geo_fips, e)
        return None

    records: list[dict] = []
    for row in rows:
        raw_value = row.get("DataValue", "")
        # Skip suppressed or missing values
        if not raw_value or raw_value.strip() in {"(D)", "(NA)", ""}:
            continue

        try:
            year = int(row["TimePeriod"])
            # LineCode is embedded in the Code field as "TABLE-<code>" or directly
            code_field = row.get("Code", "")
            line_code = int(code_field.split("-")[-1]) if "-" in code_field else int(code_field)
            # Strip thousands separators before converting
            value_thousands = float(raw_value.replace(",", ""))
        except (KeyError, ValueError, TypeError):
            continue

        if line_code not in INDUSTRIES:
            continue

        records.append({
            "year": year,
            "line_code": line_code,
            "value_thousands": value_thousands,
        })

    return records


def _build_data_points(
    geo_id: str,
    source_id: str,
    records: list[dict],
    year_filter: set[int] | None = None,
) -> list[DataPoint]:
    """Convert raw BEA records into DataPoints.

    Emits per year × industry:
      - gdp_total (line_code=1)
      - gdp_industry_<code> in millions of USD
      - gdp_share_industry_<code> as fraction 0-1
      - top_gdp_industry_code
      - top_gdp_industry_share
    """
    now = datetime.now(timezone.utc)
    points: list[DataPoint] = []

    # Group by year
    by_year: dict[int, dict[int, float]] = {}
    for rec in records:
        year = rec["year"]
        if year_filter is not None and year not in year_filter:
            continue
        by_year.setdefault(year, {})[rec["line_code"]] = rec["value_thousands"]

    for year, industry_map in by_year.items():
        vintage = f"bea_regional_{year}"
        total_thousands = industry_map.get(1)

        # gdp_total — value in millions
        if total_thousands is not None:
            points.append(DataPoint(
                geo_id=geo_id,
                metric="gdp_total",
                year=year,
                value=total_thousands / 1000.0,
                source=source_id,
                vintage=vintage,
                fetched_at=now,
            ))

        # Per-industry metrics (skip aggregate codes 1 and 2 for individual breakdown)
        top_code: int | None = None
        top_share: float | None = None

        for line_code, val_thousands in industry_map.items():
            if line_code in _AGGREGATE_CODES:
                continue

            # gdp_industry_<code> in millions
            points.append(DataPoint(
                geo_id=geo_id,
                metric=f"gdp_industry_{line_code}",
                year=year,
                value=val_thousands / 1000.0,
                source=source_id,
                vintage=vintage,
                fetched_at=now,
            ))

            # gdp_share_industry_<code> — fraction of total GDP
            if total_thousands and total_thousands > 0:
                share = val_thousands / total_thousands
                points.append(DataPoint(
                    geo_id=geo_id,
                    metric=f"gdp_share_industry_{line_code}",
                    year=year,
                    value=share,
                    source=source_id,
                    vintage=vintage,
                    fetched_at=now,
                ))

                if top_share is None or share > top_share:
                    top_share = share
                    top_code = line_code

        if top_code is not None and top_share is not None:
            points.append(DataPoint(
                geo_id=geo_id,
                metric="top_gdp_industry_code",
                year=year,
                value=float(top_code),
                source=source_id,
                vintage=vintage,
                fetched_at=now,
            ))
            points.append(DataPoint(
                geo_id=geo_id,
                metric="top_gdp_industry_share",
                year=year,
                value=top_share,
                source=source_id,
                vintage=vintage,
                fetched_at=now,
            ))

    return points


@SourceRegistry.register
class BEAGDPIndustrySource(DataSource):
    source_id = "bea_gdp_industry"
    name = "BEA Regional GDP by Industry"
    description = "GDP contribution by industry for metros and counties — identifies dominant industries by dollar value"
    supported_geo_types_for_lookup = [GeoType.METRO, GeoType.COUNTY]

    def __init__(self, config: Config):
        super().__init__(config)
        self._api_key = config.bea.api_key

    def fetch(self, **kwargs) -> FetchResult:
        if self._api_key is None:
            raise RuntimeError(
                "BEA API key required. Get one free at https://apps.bea.gov/api/signup/ "
                "and set bea.api_key in config."
            )

        storage = Storage(self.config.storage.db_path)
        metros = storage.get_geographies(
            geo_type="metro",
            min_population=kwargs.get("min_population", self.config.pipeline.min_population),
        )
        if not metros:
            raise RuntimeError("No metros in database. Run 'fetch census_population' first.")

        start_year = kwargs.get("start_year", 2020)
        end_year = kwargs.get("end_year", datetime.now().year - 1)
        year_filter = set(range(start_year, end_year + 1))

        all_points: list[DataPoint] = []

        for metro in metros:
            cbsa = metro["geo_id"]
            records = _fetch_bea_area_gdp("MAGDP2", cbsa, self._api_key)
            if records is None:
                logger.warning("Skipping metro %s — BEA fetch failed", cbsa)
                continue

            points = _build_data_points(cbsa, self.source_id, records, year_filter=year_filter)
            all_points.extend(points)

        years = {p.year for p in all_points}
        all_metrics = sorted({p.metric for p in all_points})
        logger.info("BEA GDP: %d data points across %d metros", len(all_points), len(metros))

        return FetchResult(
            geographies=[],
            data_points=all_points,
            metadata=DatasetMetadata(
                source_id=self.source_id,
                name=self.name,
                description=self.description,
                metrics=all_metrics,
                geo_types=[GeoType.METRO, GeoType.COUNTY],
                min_year=min(years) if years else 0,
                max_year=max(years) if years else 0,
                last_fetched=datetime.now(timezone.utc),
                record_count=len(all_points),
            ),
        )

    def fetch_for_geo(self, geo_id: str, geo_type: GeoType) -> FetchResult:
        if geo_type not in (GeoType.METRO, GeoType.COUNTY):
            raise NotImplementedError(f"bea_gdp_industry does not support {geo_type}")
        if len(geo_id) != 5:
            raise ValueError(f"geo_id must be 5 digits, got {geo_id!r}")

        now = datetime.now(timezone.utc)

        # Degrade gracefully when no API key is configured (address lookup path)
        if self._api_key is None:
            return FetchResult(
                geographies=[],
                data_points=[],
                metadata=DatasetMetadata(
                    source_id=self.source_id,
                    name=self.name,
                    description=self.description,
                    metrics=[],
                    geo_types=[geo_type],
                    min_year=0,
                    max_year=0,
                    last_fetched=now,
                ),
            )

        table = "MAGDP2" if geo_type == GeoType.METRO else "CAGDP2"
        records = _fetch_bea_area_gdp(table, geo_id, self._api_key)
        if records is None:
            records = []

        # Keep only the latest 3 years of data
        all_years = sorted({r["year"] for r in records}, reverse=True)
        keep_years = set(all_years[:3])

        points = _build_data_points(geo_id, self.source_id, records, year_filter=keep_years)
        years = {p.year for p in points}

        return FetchResult(
            geographies=[],
            data_points=points,
            metadata=DatasetMetadata(
                source_id=self.source_id,
                name=self.name,
                description=self.description,
                metrics=sorted({p.metric for p in points}),
                geo_types=[geo_type],
                min_year=min(years) if years else 0,
                max_year=max(years) if years else 0,
                last_fetched=now,
                record_count=len(points),
            ),
        )
