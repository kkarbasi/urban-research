from __future__ import annotations

import logging
import time
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

logger = logging.getLogger(__name__)

CENSUS_BASE = "https://api.census.gov/data"
MAX_RETRIES = 3
RETRY_DELAY = 2.0
TIMEOUT = 120.0
USER_AGENT = "urban-research/0.1.0"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url: str, params: dict[str, str]) -> httpx.Response:
    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    return resp
                if resp.status_code >= 500:
                    logger.warning("Census API %d, retry %d/%d", resp.status_code, attempt + 1, MAX_RETRIES)
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                resp.raise_for_status()
                return resp
        except httpx.TimeoutException:
            logger.warning("Census API timeout, retry %d/%d", attempt + 1, MAX_RETRIES)
            time.sleep(RETRY_DELAY * (attempt + 1))
    raise RuntimeError(f"Census API failed after {MAX_RETRIES} retries: {url}")


def _probe_endpoint(url: str, api_key: str | None) -> bool:
    params: dict[str, str] = {"get": "NAME", "for": "state:01"}
    if api_key:
        params["key"] = api_key
    try:
        resp = _get(url, params)
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Vintage detection
# ---------------------------------------------------------------------------

def _detect_pep_vintage(api_key: str | None) -> int:
    current_year = datetime.now().year
    for year in range(current_year - 1, current_year - 4, -1):
        if _probe_endpoint(f"{CENSUS_BASE}/{year}/pep/charv", api_key):
            logger.info("Detected latest PEP vintage: %d", year)
            return year
    raise RuntimeError("Could not detect PEP vintage — Census API may be down")


def _detect_acs_vintages(api_key: str | None, base_year: int = 2021) -> list[int]:
    """Return available ACS 1-year vintages from base_year to present."""
    current_year = datetime.now().year
    vintages: list[int] = []
    for year in range(base_year, current_year):
        if _probe_endpoint(f"{CENSUS_BASE}/{year}/acs/acs1", api_key):
            vintages.append(year)
    logger.info("Available ACS 1-year vintages: %s", vintages)
    return vintages


# ---------------------------------------------------------------------------
# Metro fetching — PEP charv endpoint
# ---------------------------------------------------------------------------

def _fetch_metros(vintage: int, api_key: str | None) -> tuple[list[Geography], list[DataPoint]]:
    """Fetch metro population from PEP charv (all years, July estimates)."""
    url = f"{CENSUS_BASE}/{vintage}/pep/charv"
    params: dict[str, str] = {
        "get": "POP,NAME,YEAR",
        "for": "metropolitan statistical area/micropolitan statistical area:*",
        "MONTH": "7",
    }
    if api_key:
        params["key"] = api_key

    logger.info("Fetching metro population from PEP charv vintage %d", vintage)
    data = _get(url, params).json()
    headers = data[0]
    rows = data[1:]

    cbsa_field = "metropolitan statistical area/micropolitan statistical area"
    pop_by_geo: dict[str, dict[int, int]] = {}
    name_by_geo: dict[str, str] = {}

    for row in rows:
        rec = dict(zip(headers, row))
        geo_id = rec.get(cbsa_field, "")
        name = rec.get("NAME", "")
        year = int(rec.get("YEAR", 0))
        try:
            pop = int(rec["POP"])
        except (KeyError, ValueError, TypeError):
            continue

        name_by_geo[geo_id] = name
        pop_by_geo.setdefault(geo_id, {})[year] = pop

    return _build_models(pop_by_geo, name_by_geo, GeoType.METRO, f"pep_{vintage}")


# ---------------------------------------------------------------------------
# City fetching — ACS 1-year endpoint (multiple vintages)
# ---------------------------------------------------------------------------

def _fetch_cities(vintages: list[int], api_key: str | None) -> tuple[list[Geography], list[DataPoint]]:
    """Fetch city population from ACS 1-year across multiple vintages."""
    pop_by_geo: dict[str, dict[int, int]] = {}
    name_by_geo: dict[str, str] = {}
    state_by_geo: dict[str, str] = {}

    for vintage in vintages:
        url = f"{CENSUS_BASE}/{vintage}/acs/acs1"
        params: dict[str, str] = {
            "get": "B01003_001E,NAME",
            "for": "place:*",
            "in": "state:*",
        }
        if api_key:
            params["key"] = api_key

        logger.info("Fetching city population from ACS 1-year vintage %d", vintage)
        data = _get(url, params).json()
        headers = data[0]
        rows = data[1:]

        for row in rows:
            rec = dict(zip(headers, row))
            state_fips = rec.get("state", "")
            place_fips = rec.get("place", "")
            geo_id = f"{state_fips}{place_fips}"
            name = rec.get("NAME", "")
            try:
                pop = int(rec["B01003_001E"])
            except (KeyError, ValueError, TypeError):
                continue

            name_by_geo[geo_id] = name
            state_by_geo[geo_id] = state_fips
            pop_by_geo.setdefault(geo_id, {})[vintage] = pop

    geos, points = _build_models(
        pop_by_geo, name_by_geo, GeoType.CITY,
        f"acs_{vintages[0]}-{vintages[-1]}" if vintages else "acs",
    )

    for geo in geos:
        geo.state_fips = state_by_geo.get(geo.geo_id)

    return geos, points


# ---------------------------------------------------------------------------
# Shared model builder
# ---------------------------------------------------------------------------

def _build_models(
    pop_by_geo: dict[str, dict[int, int]],
    name_by_geo: dict[str, str],
    geo_type: GeoType,
    vintage_label: str,
) -> tuple[list[Geography], list[DataPoint]]:
    geos: list[Geography] = []
    points: list[DataPoint] = []
    now = datetime.now(timezone.utc)

    for geo_id, year_pops in pop_by_geo.items():
        if not year_pops:
            continue

        latest_pop = year_pops[max(year_pops)]
        geos.append(Geography(
            geo_id=geo_id,
            name=name_by_geo.get(geo_id, ""),
            geo_type=geo_type,
            population=latest_pop,
        ))

        for year, pop in year_pops.items():
            points.append(DataPoint(
                geo_id=geo_id,
                metric="population",
                year=year,
                value=float(pop),
                source="census_population",
                vintage=vintage_label,
                fetched_at=now,
            ))

        sorted_years = sorted(year_pops)
        for i in range(1, len(sorted_years)):
            prev_y = sorted_years[i - 1]
            curr_y = sorted_years[i]
            prev_pop = year_pops[prev_y]
            curr_pop = year_pops[curr_y]
            change = curr_pop - prev_pop
            pct = (change / prev_pop * 100) if prev_pop > 0 else 0.0

            points.append(DataPoint(
                geo_id=geo_id, metric="population_change", year=curr_y,
                value=float(change), source="census_population",
                vintage=vintage_label, fetched_at=now,
            ))
            points.append(DataPoint(
                geo_id=geo_id, metric="population_change_pct", year=curr_y,
                value=round(pct, 4), source="census_population",
                vintage=vintage_label, fetched_at=now,
            ))

    return geos, points


# ---------------------------------------------------------------------------
# Single-geo lookups (fallback for address lookup)
# ---------------------------------------------------------------------------

def _fetch_single_county(
    state_fips: str, county_fips: str, vintage: int, api_key: str | None,
) -> tuple[list[Geography], list[DataPoint]]:
    """Fetch population for a specific county via PEP charv."""
    url = f"{CENSUS_BASE}/{vintage}/pep/charv"
    params: dict[str, str] = {
        "get": "POP,NAME,YEAR",
        "for": f"county:{county_fips}",
        "in": f"state:{state_fips}",
        "MONTH": "7",
    }
    if api_key:
        params["key"] = api_key

    logger.info("Fetching county %s%s from PEP charv vintage %d", state_fips, county_fips, vintage)
    data = _get(url, params).json()
    headers = data[0]
    rows = data[1:]

    geo_id = f"{state_fips}{county_fips}"
    pop_by_year: dict[int, int] = {}
    name = ""
    for row in rows:
        rec = dict(zip(headers, row))
        try:
            year = int(rec.get("YEAR", 0))
            pop = int(rec["POP"])
        except (KeyError, ValueError, TypeError):
            continue
        pop_by_year[year] = pop
        name = rec.get("NAME", name)

    if not pop_by_year:
        return [], []

    pop_by_geo = {geo_id: pop_by_year}
    name_by_geo = {geo_id: name}
    geos, points = _build_models(pop_by_geo, name_by_geo, GeoType.COUNTY, f"pep_{vintage}")
    for g in geos:
        g.state_fips = state_fips
    return geos, points


def _fetch_single_metro(cbsa: str, vintage: int, api_key: str | None) -> tuple[list[Geography], list[DataPoint]]:
    """Fetch population for one CBSA by reusing the all-metros fetch and filtering.

    PEP charv doesn't support `for=metropolitan...:{CBSA}` with wildcards, but the
    full-metros fetch is cheap (~3,700 rows) and already tested, so we reuse it.
    """
    all_geos, all_points = _fetch_metros(vintage, api_key)
    geos = [g for g in all_geos if g.geo_id == cbsa]
    points = [p for p in all_points if p.geo_id == cbsa]
    return geos, points


def _fetch_single_city(
    place_geo_id: str, vintages: list[int], api_key: str | None,
) -> tuple[list[Geography], list[DataPoint]]:
    """Fetch population for one place via ACS 1-year across multiple vintages."""
    if len(place_geo_id) != 7:
        return [], []
    state_fips = place_geo_id[:2]
    place_fips = place_geo_id[2:]

    pop_by_year: dict[int, int] = {}
    name = ""

    for vintage in vintages:
        url = f"{CENSUS_BASE}/{vintage}/acs/acs1"
        params: dict[str, str] = {
            "get": "B01003_001E,NAME",
            "for": f"place:{place_fips}",
            "in": f"state:{state_fips}",
        }
        if api_key:
            params["key"] = api_key
        try:
            data = _get(url, params).json()
        except Exception as e:
            logger.warning("ACS %d place fetch failed: %s", vintage, e)
            continue
        if len(data) < 2:
            continue
        rec = dict(zip(data[0], data[1]))
        try:
            pop = int(rec["B01003_001E"])
        except (KeyError, ValueError, TypeError):
            continue
        pop_by_year[vintage] = pop
        name = rec.get("NAME", name)

    if not pop_by_year:
        return [], []

    pop_by_geo = {place_geo_id: pop_by_year}
    name_by_geo = {place_geo_id: name}
    label = f"acs_{min(pop_by_year)}-{max(pop_by_year)}"
    geos, points = _build_models(pop_by_geo, name_by_geo, GeoType.CITY, label)
    for g in geos:
        g.state_fips = state_fips
    return geos, points


# ---------------------------------------------------------------------------
# Registered source
# ---------------------------------------------------------------------------

@SourceRegistry.register
class CensusPopulationSource(DataSource):
    source_id = "census_population"
    name = "Census Bureau Population Estimates"
    description = "Annual population estimates and growth rates for metros and cities"
    supported_geo_types_for_lookup = [GeoType.METRO, GeoType.CITY, GeoType.COUNTY]

    def __init__(self, config: Config):
        super().__init__(config)
        self._api_key = config.census.api_key

    def fetch(self, **kwargs) -> FetchResult:
        min_pop = kwargs.get("min_population", self.config.pipeline.min_population)

        pep_vintage = kwargs.get("vintage") or self.config.pipeline.default_vintage or _detect_pep_vintage(self._api_key)
        acs_vintages = _detect_acs_vintages(self._api_key, base_year=2021)

        logger.info("PEP vintage: %d | ACS vintages: %s | min_pop: %s", pep_vintage, acs_vintages, min_pop)

        all_geos: list[Geography] = []
        all_points: list[DataPoint] = []

        metro_geos, metro_pts = _fetch_metros(pep_vintage, self._api_key)
        all_geos.extend(metro_geos)
        all_points.extend(metro_pts)

        if acs_vintages:
            city_geos, city_pts = _fetch_cities(acs_vintages, self._api_key)
            all_geos.extend(city_geos)
            all_points.extend(city_pts)

        if min_pop:
            qualifying = {g.geo_id for g in all_geos if g.population and g.population >= min_pop}
            all_geos = [g for g in all_geos if g.geo_id in qualifying]
            all_points = [p for p in all_points if p.geo_id in qualifying]
            logger.info("Filtered to %d geographies >= %s population", len(all_geos), f"{min_pop:,}")

        years = {p.year for p in all_points}

        return FetchResult(
            geographies=all_geos,
            data_points=all_points,
            metadata=DatasetMetadata(
                source_id=self.source_id,
                name=self.name,
                description=self.description,
                metrics=["population", "population_change", "population_change_pct"],
                geo_types=[GeoType.METRO, GeoType.CITY],
                min_year=min(years) if years else 0,
                max_year=max(years) if years else 0,
                last_fetched=datetime.now(timezone.utc),
                record_count=len(all_points),
            ),
        )

    def fetch_for_geo(self, geo_id: str, geo_type: GeoType) -> FetchResult:
        """Fetch population data for a single geography (lookup fallback)."""
        if geo_type == GeoType.COUNTY:
            if len(geo_id) != 5:
                raise ValueError(f"County geo_id must be 5 digits, got {geo_id!r}")
            state_fips, county_fips = geo_id[:2], geo_id[2:]
            vintage = self.config.pipeline.default_vintage or _detect_pep_vintage(self._api_key)
            geos, points = _fetch_single_county(state_fips, county_fips, vintage, self._api_key)
        elif geo_type == GeoType.METRO:
            vintage = self.config.pipeline.default_vintage or _detect_pep_vintage(self._api_key)
            geos, points = _fetch_single_metro(geo_id, vintage, self._api_key)
        elif geo_type == GeoType.CITY:
            vintages = _detect_acs_vintages(self._api_key, base_year=2021)
            geos, points = _fetch_single_city(geo_id, vintages, self._api_key)
        else:
            raise NotImplementedError(f"Census source does not support {geo_type}")

        years = {p.year for p in points}
        return FetchResult(
            geographies=geos,
            data_points=points,
            metadata=DatasetMetadata(
                source_id=self.source_id,
                name=self.name,
                description=self.description,
                metrics=["population", "population_change", "population_change_pct"],
                geo_types=[geo_type],
                min_year=min(years) if years else 0,
                max_year=max(years) if years else 0,
                last_fetched=datetime.now(timezone.utc),
                record_count=len(points),
            ),
        )
