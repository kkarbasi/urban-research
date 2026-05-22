"""BLS QCEW Industry Mix source.

Downloads single-area QCEW CSV files to extract NAICS supersector employment
and location quotients (LQs) for metros and counties.

Endpoint: https://data.bls.gov/cew/data/api/{year}/a/area/{area_fips}.csv
- For metros: area_fips is the 5-digit CBSA code directly (e.g., "41940").
  This differs from the aggregate industry file in bls_employment.py which uses
  a C{4-digit} prefix; the single-area endpoint accepts the raw CBSA.
- For counties: area_fips is the 5-digit state+county FIPS directly.
"""

from __future__ import annotations

import csv
import io
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

TIMEOUT = 120.0
USER_AGENT = "cityscope/0.4.0"

QCEW_AREA_URL = "https://data.bls.gov/cew/data/api/{year}/a/area/{area_fips}.csv"

SECTORS: dict[str, str] = {
    "11":    "Agriculture, Forestry, Fishing",
    "21":    "Mining, Quarrying, Oil & Gas",
    "22":    "Utilities",
    "23":    "Construction",
    "31-33": "Manufacturing",
    "42":    "Wholesale Trade",
    "44-45": "Retail Trade",
    "48-49": "Transportation & Warehousing",
    "51":    "Information",
    "52":    "Finance & Insurance",
    "53":    "Real Estate, Rental & Leasing",
    "54":    "Professional, Scientific & Technical Services",
    "55":    "Management of Companies",
    "56":    "Admin, Support, Waste Management",
    "61":    "Educational Services",
    "62":    "Health Care & Social Assistance",
    "71":    "Arts, Entertainment & Recreation",
    "72":    "Accommodation & Food Services",
    "81":    "Other Services",
    "92":    "Public Administration",
}

# Metric-safe key: replace "-" with "_" so keys are valid identifier fragments.
def _metric_key(industry_code: str) -> str:
    return industry_code.replace("-", "_")


# First numeric part of a compound code (e.g., "31-33" → 31.0, "44-45" → 44.0).
def _code_to_float(industry_code: str) -> float:
    return float(industry_code.split("-")[0])


def _fetch_area_industry_data(area_fips: str, year: int) -> dict | None:
    """Download and parse QCEW single-area CSV for one area-year.

    Returns a dict mapping sector code → {"emp": float, "lq": float}, or None
    on HTTP error. Only private-sector rows (own_code "5") are kept; falls back
    to total (own_code "0") when no private row exists for a given sector.
    """
    url = QCEW_AREA_URL.format(year=year, area_fips=area_fips)
    try:
        with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning(
                    "QCEW area %s year %d: HTTP %d", area_fips, year, resp.status_code
                )
                return None
    except httpx.HTTPError as exc:
        logger.warning("QCEW area %s year %d failed: %s", area_fips, year, exc)
        return None

    sector_codes = set(SECTORS.keys())
    # Accumulate rows per sector; prefer own_code "5" over "0".
    # private_rows: sector_code → row dict (own_code == "5")
    # total_rows:   sector_code → row dict (own_code == "0")
    private_rows: dict[str, dict] = {}
    total_rows: dict[str, dict] = {}

    reader = csv.DictReader(io.StringIO(resp.text))
    for row in reader:
        industry_code = row.get("industry_code", "").strip('"').strip()
        if industry_code not in sector_codes:
            continue
        own_code = row.get("own_code", "").strip('"').strip()
        if own_code == "5":
            private_rows[industry_code] = row
        elif own_code == "0":
            total_rows[industry_code] = row

    result: dict[str, dict[str, float]] = {}
    for code in sector_codes:
        row = private_rows.get(code) or total_rows.get(code)
        if row is None:
            continue
        try:
            emp = float(row.get("annual_avg_emplvl", "") or 0)
            lq = float(row.get("lq_annual_avg_emplvl", "") or 0)
        except (ValueError, TypeError):
            continue
        result[code] = {"emp": emp, "lq": lq}

    return result


def _build_points_from_sector_data(
    sector_data: dict,
    geo_id: str,
    year: int,
    source_id: str,
    now: datetime,
) -> list[DataPoint]:
    """Convert sector_data dict into DataPoint list including derived top-industry metrics."""
    vintage = f"qcew_industry_{year}"
    points: list[DataPoint] = []

    for code, vals in sector_data.items():
        key = _metric_key(code)
        points.append(DataPoint(
            geo_id=geo_id,
            metric=f"emp_naics_{key}",
            year=year,
            value=vals["emp"],
            source=source_id,
            vintage=vintage,
            fetched_at=now,
        ))
        points.append(DataPoint(
            geo_id=geo_id,
            metric=f"lq_naics_{key}",
            year=year,
            value=vals["lq"],
            source=source_id,
            vintage=vintage,
            fetched_at=now,
        ))

    # Derive top-industry metrics — only sectors with employment > 0.
    candidates = {
        code: vals for code, vals in sector_data.items() if vals["emp"] > 0
    }
    if candidates:
        top_code = max(candidates, key=lambda c: candidates[c]["lq"])
        top_vals = candidates[top_code]
        total_emp = sum(v["emp"] for v in candidates.values())
        emp_share = top_vals["emp"] / total_emp if total_emp > 0 else 0.0

        points.append(DataPoint(
            geo_id=geo_id,
            metric="top_industry_naics_code",
            year=year,
            value=_code_to_float(top_code),
            source=source_id,
            vintage=vintage,
            fetched_at=now,
        ))
        points.append(DataPoint(
            geo_id=geo_id,
            metric="top_industry_lq",
            year=year,
            value=top_vals["lq"],
            source=source_id,
            vintage=vintage,
            fetched_at=now,
        ))
        points.append(DataPoint(
            geo_id=geo_id,
            metric="top_industry_emp_share",
            year=year,
            value=emp_share,
            source=source_id,
            vintage=vintage,
            fetched_at=now,
        ))

    return points


@SourceRegistry.register
class BLSQCEWIndustrySource(DataSource):
    source_id = "bls_qcew_industry"
    name = "BLS QCEW Industry Mix (NAICS supersector employment + location quotients)"
    description = (
        "Industry concentration by NAICS sector for metros and counties — "
        "identifies dominant industries via location quotient"
    )
    supported_geo_types_for_lookup = [GeoType.METRO, GeoType.COUNTY]

    def __init__(self, config: Config):
        super().__init__(config)

    def fetch(self, **kwargs) -> FetchResult:
        storage = Storage(self.config.storage.db_path)
        metros = storage.get_geographies(
            geo_type="metro",
            min_population=kwargs.get("min_population", self.config.pipeline.min_population),
        )
        if not metros:
            raise RuntimeError("No metros in database. Run 'fetch census_population' first.")

        start_year = kwargs.get("start_year", 2020)
        end_year = kwargs.get("end_year", datetime.now().year - 1)
        now = datetime.now(timezone.utc)
        all_points: list[DataPoint] = []

        for metro in metros:
            geo_id = metro["geo_id"]
            # For metros, area_fips is the 5-digit CBSA code used directly.
            area_fips = geo_id
            for year in range(start_year, end_year + 1):
                sector_data = _fetch_area_industry_data(area_fips, year)
                if sector_data is None:
                    continue
                all_points.extend(
                    _build_points_from_sector_data(sector_data, geo_id, year, self.source_id, now)
                )

        all_metrics = sorted({p.metric for p in all_points})
        years = {p.year for p in all_points}
        logger.info(
            "bls_qcew_industry: %d data points, %d metrics", len(all_points), len(all_metrics)
        )

        return FetchResult(
            geographies=[],
            data_points=all_points,
            metadata=DatasetMetadata(
                source_id=self.source_id,
                name=self.name,
                description=self.description,
                metrics=all_metrics,
                geo_types=[GeoType.METRO],
                min_year=min(years) if years else 0,
                max_year=max(years) if years else 0,
                last_fetched=now,
                record_count=len(all_points),
            ),
        )

    def fetch_for_geo(self, geo_id: str, geo_type: GeoType) -> FetchResult:
        if geo_type not in (GeoType.METRO, GeoType.COUNTY):
            raise NotImplementedError(f"bls_qcew_industry does not support {geo_type}")
        if len(geo_id) != 5:
            raise ValueError(f"geo_id must be 5 digits, got {geo_id!r}")

        # Both metros and counties use their 5-digit code directly as area_fips
        # on the single-area endpoint.
        area_fips = geo_id
        current_year = datetime.now().year
        start_year = current_year - 3
        end_year = current_year - 1

        now = datetime.now(timezone.utc)
        points: list[DataPoint] = []

        for year in range(start_year, end_year + 1):
            sector_data = _fetch_area_industry_data(area_fips, year)
            if sector_data is None:
                # Tolerate per-year 404s silently.
                continue
            points.extend(
                _build_points_from_sector_data(sector_data, geo_id, year, self.source_id, now)
            )

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
