from __future__ import annotations

import csv
import io
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

import httpx

from ..core.config import Config
from ..core.models import (
    DataPoint,
    DatasetMetadata,
    FetchResult,
    Geography,
    GeoType,
)
from ..core.registry import SourceRegistry
from ..core.source import DataSource
from ..core.storage import Storage

logger = logging.getLogger(__name__)

TIMEOUT = 120.0
USER_AGENT = "urban-research/0.1.0"

# QCEW CSV download (no rate limits, no key needed)
QCEW_URL = "https://data.bls.gov/cew/data/api/{year}/a/industry/10.csv"

# BLS LAUS API (25 req/day v1, 500 req/day v2 with key)
BLS_API_V1 = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_API_V2 = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
LAUS_BATCH_DELAY = 0.5

STATE_ABBR_TO_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "PR": "72",
    "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48",
    "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54",
    "WI": "55", "WY": "56",
}


def _cbsa_to_qcew_fips(cbsa: str) -> str:
    """Convert 5-digit CBSA code to QCEW area_fips (C + first 4 digits)."""
    return f"C{cbsa[:4]}"


def _qcew_fips_to_cbsa(qcew_fips: str) -> str:
    """Convert QCEW area_fips back to 5-digit CBSA code (append 0)."""
    return qcew_fips[1:] + "0"


def _parse_principal_state_fips(metro_name: str) -> str | None:
    """Extract the first state abbreviation from a Census metro name."""
    match = re.search(r",\s*([A-Z]{2})", metro_name)
    if match:
        return STATE_ABBR_TO_FIPS.get(match.group(1))
    return None


# ---------------------------------------------------------------------------
# QCEW: Employment data (reliable, no rate limits)
# ---------------------------------------------------------------------------

def _fetch_qcew_year(year: int) -> dict[str, dict]:
    """Download QCEW annual data for all-industries and return metro employment."""
    url = QCEW_URL.format(year=year)
    logger.info("Downloading QCEW data for %d", year)

    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(url)
        resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    metros: dict[str, dict] = {}

    for row in reader:
        area_fips = row.get("area_fips", "").strip('"')
        own_code = row.get("own_code", "").strip('"')
        agglvl_code = row.get("agglvl_code", "").strip('"')

        # Filter: metro-level total (all ownerships)
        if not area_fips.startswith("C") or own_code != "0" or agglvl_code != "40":
            continue

        cbsa = _qcew_fips_to_cbsa(area_fips)
        try:
            metros[cbsa] = {
                "employment": int(row.get("annual_avg_emplvl", 0)),
                "establishments": int(row.get("annual_avg_estabs", 0)),
                "avg_weekly_wage": int(row.get("annual_avg_wkly_wage", 0)),
                "avg_annual_pay": int(row.get("avg_annual_pay", 0)),
                "total_wages": int(row.get("total_annual_wages", 0)),
                "emp_change": int(row.get("oty_annual_avg_emplvl_chg", 0) or 0),
                "emp_change_pct": float(row.get("oty_annual_avg_emplvl_pct_chg", 0) or 0),
                "wage_change_pct": float(row.get("oty_annual_avg_wkly_wage_pct_chg", 0) or 0),
            }
        except (ValueError, TypeError):
            continue

    logger.info("Parsed %d metros from QCEW %d", len(metros), year)
    return metros


# ---------------------------------------------------------------------------
# LAUS: Unemployment rate (API, rate-limited)
# ---------------------------------------------------------------------------

def _fetch_laus_unemployment(
    metros: list[dict],
    start_year: int,
    end_year: int,
    api_key: str | None,
) -> dict[str, dict[int, float]]:
    """Fetch unemployment rates via BLS LAUS API. Returns {geo_id: {year: rate}}."""
    url = BLS_API_V2 if api_key else BLS_API_V1
    batch_size = 50 if api_key else 25

    # Build series IDs
    series_map: dict[str, str] = {}  # sid -> geo_id
    for metro in metros:
        state_fips = _parse_principal_state_fips(metro["name"])
        if not state_fips:
            continue
        cbsa = metro["geo_id"]
        sid = f"LAUMT{state_fips}{cbsa}000000003"
        series_map[sid] = cbsa

    series_ids = list(series_map.keys())
    result: dict[str, dict[int, float]] = defaultdict(dict)
    total_batches = (len(series_ids) + batch_size - 1) // batch_size

    for i in range(0, len(series_ids), batch_size):
        batch = series_ids[i : i + batch_size]
        batch_num = i // batch_size + 1

        payload: dict = {
            "seriesid": batch,
            "startyear": str(start_year),
            "endyear": str(end_year),
        }
        if api_key:
            payload["registrationkey"] = api_key

        logger.info("LAUS API batch %d/%d (%d series)", batch_num, total_batches, len(batch))

        try:
            resp = httpx.post(
                url, json=payload, timeout=TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "REQUEST_SUCCEEDED":
                msg = data.get("message", [])
                logger.warning("LAUS API batch %d: %s — %s", batch_num, data["status"], msg)
                if "threshold" in str(msg).lower():
                    logger.error("BLS API daily limit reached. Stopping LAUS fetch.")
                    break
                continue

            for series in data.get("Results", {}).get("series", []):
                sid = series["seriesID"]
                geo_id = series_map.get(sid)
                if not geo_id:
                    continue

                yearly_values: dict[int, list[float]] = defaultdict(list)
                for obs in series.get("data", []):
                    period = obs.get("period", "")
                    if not period.startswith("M") or period == "M13":
                        continue
                    try:
                        year = int(obs["year"])
                        value = float(obs["value"])
                        yearly_values[year].append(value)
                    except (KeyError, ValueError):
                        continue

                for year, values in yearly_values.items():
                    result[geo_id][year] = round(sum(values) / len(values), 1)

        except httpx.HTTPError as e:
            logger.warning("LAUS API batch %d failed: %s", batch_num, e)
            continue

        if i + batch_size < len(series_ids):
            time.sleep(LAUS_BATCH_DELAY)

    logger.info("LAUS: got unemployment rates for %d metros", len(result))
    return dict(result)


# ---------------------------------------------------------------------------
# Registered source
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Single-geo QCEW fetch (for address lookup fallback)
# ---------------------------------------------------------------------------

def _fetch_qcew_single_area(area_fips: str) -> dict[int, dict]:
    """Download QCEW data for a single area (metro or county) across available years.

    area_fips: 5-digit state+county FIPS for counties, or 5-digit CBSA code for metros
               (QCEW uses the 5-digit CBSA directly as area_fips for metros in the
               single-area endpoint — different from the industry-level file which
               uses C{4-digit} prefix).
    Returns dict of year -> data fields.
    """
    results: dict[int, dict] = {}
    current_year = datetime.now().year
    for year in range(current_year - 5, current_year):
        url = f"https://data.bls.gov/cew/data/api/{year}/a/area/{area_fips}.csv"
        try:
            with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    continue
        except httpx.HTTPError as e:
            logger.warning("QCEW area %s %d failed: %s", area_fips, year, e)
            continue

        reader = csv.DictReader(io.StringIO(resp.text))
        for row in reader:
            own_code = row.get("own_code", "").strip('"')
            industry_code = row.get("industry_code", "").strip('"')
            # Total across all ownerships + all industries
            if own_code != "0" or industry_code != "10":
                continue
            try:
                results[year] = {
                    "employment": int(row.get("annual_avg_emplvl", 0) or 0),
                    "avg_annual_pay": int(row.get("avg_annual_pay", 0) or 0),
                    "avg_weekly_wage": int(row.get("annual_avg_wkly_wage", 0) or 0),
                    "emp_change": int(row.get("oty_annual_avg_emplvl_chg", 0) or 0),
                    "emp_change_pct": float(row.get("oty_annual_avg_emplvl_pct_chg", 0) or 0),
                }
            except (ValueError, TypeError):
                continue
            break

    return results


# ---------------------------------------------------------------------------
# Registered source
# ---------------------------------------------------------------------------

@SourceRegistry.register
class BLSEmploymentSource(DataSource):
    source_id = "bls_employment"
    name = "BLS Employment & Unemployment (QCEW + LAUS)"
    description = "Employment, wages, and unemployment rate for metro areas"
    supported_geo_types_for_lookup = [GeoType.METRO, GeoType.COUNTY]

    def __init__(self, config: Config):
        super().__init__(config)
        self._api_key = config.bls.api_key

    def fetch(self, **kwargs) -> FetchResult:
        storage = Storage(self.config.storage.db_path)
        metros = storage.get_geographies(
            geo_type="metro",
            min_population=kwargs.get("min_population", self.config.pipeline.min_population),
        )
        if not metros:
            raise RuntimeError("No metros in database. Run 'fetch census_population' first.")

        metro_ids = {m["geo_id"] for m in metros}
        start_year = kwargs.get("start_year", 2020)
        end_year = kwargs.get("end_year", datetime.now().year - 1)
        skip_laus = kwargs.get("skip_laus", False)

        now = datetime.now(timezone.utc)
        all_points: list[DataPoint] = []

        # --- QCEW: employment, wages ---
        for year in range(start_year, end_year + 1):
            try:
                year_data = _fetch_qcew_year(year)
            except httpx.HTTPError as e:
                logger.warning("QCEW %d failed: %s", year, e)
                continue

            for cbsa, d in year_data.items():
                if cbsa not in metro_ids:
                    continue

                vintage = f"qcew_{year}"
                all_points.append(DataPoint(
                    geo_id=cbsa, metric="employment", year=year,
                    value=float(d["employment"]), source=self.source_id,
                    vintage=vintage, fetched_at=now,
                ))
                all_points.append(DataPoint(
                    geo_id=cbsa, metric="avg_annual_pay", year=year,
                    value=float(d["avg_annual_pay"]), source=self.source_id,
                    vintage=vintage, fetched_at=now,
                ))
                all_points.append(DataPoint(
                    geo_id=cbsa, metric="avg_weekly_wage", year=year,
                    value=float(d["avg_weekly_wage"]), source=self.source_id,
                    vintage=vintage, fetched_at=now,
                ))
                if d["emp_change_pct"] != 0 or d["emp_change"] != 0:
                    all_points.append(DataPoint(
                        geo_id=cbsa, metric="employment_change", year=year,
                        value=float(d["emp_change"]), source=self.source_id,
                        vintage=vintage, fetched_at=now,
                    ))
                    all_points.append(DataPoint(
                        geo_id=cbsa, metric="employment_change_pct", year=year,
                        value=d["emp_change_pct"], source=self.source_id,
                        vintage=vintage, fetched_at=now,
                    ))

        # --- LAUS: unemployment rate (optional, API rate limited) ---
        if not skip_laus:
            laus_data = _fetch_laus_unemployment(
                metros, start_year, end_year, self._api_key,
            )
            for geo_id, year_rates in laus_data.items():
                for year, rate in year_rates.items():
                    all_points.append(DataPoint(
                        geo_id=geo_id, metric="unemployment_rate", year=year,
                        value=rate, source=self.source_id,
                        vintage=f"laus_{year}", fetched_at=now,
                    ))

        years = {p.year for p in all_points}
        all_metrics = sorted({p.metric for p in all_points})
        logger.info("Total: %d data points, metrics: %s", len(all_points), all_metrics)

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
        """Fetch QCEW employment/wage data for a single geography (lookup fallback).

        Note: does NOT fetch LAUS unemployment rate (requires BLS API key and is
        rate-limited). Use the main fetch() method for that.
        """
        if geo_type not in (GeoType.METRO, GeoType.COUNTY):
            raise NotImplementedError(f"BLS source does not support {geo_type}")

        if len(geo_id) != 5:
            raise ValueError(f"geo_id must be 5 digits, got {geo_id!r}")

        now = datetime.now(timezone.utc)
        points: list[DataPoint] = []

        year_data = _fetch_qcew_single_area(geo_id)

        for year, d in sorted(year_data.items()):
            vintage = f"qcew_{year}"
            points.append(DataPoint(
                geo_id=geo_id, metric="employment", year=year,
                value=float(d["employment"]), source=self.source_id,
                vintage=vintage, fetched_at=now,
            ))
            points.append(DataPoint(
                geo_id=geo_id, metric="avg_annual_pay", year=year,
                value=float(d["avg_annual_pay"]), source=self.source_id,
                vintage=vintage, fetched_at=now,
            ))
            points.append(DataPoint(
                geo_id=geo_id, metric="avg_weekly_wage", year=year,
                value=float(d["avg_weekly_wage"]), source=self.source_id,
                vintage=vintage, fetched_at=now,
            ))
            if d["emp_change_pct"] != 0 or d["emp_change"] != 0:
                points.append(DataPoint(
                    geo_id=geo_id, metric="employment_change", year=year,
                    value=float(d["emp_change"]), source=self.source_id,
                    vintage=vintage, fetched_at=now,
                ))
                points.append(DataPoint(
                    geo_id=geo_id, metric="employment_change_pct", year=year,
                    value=d["emp_change_pct"], source=self.source_id,
                    vintage=vintage, fetched_at=now,
                ))

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
