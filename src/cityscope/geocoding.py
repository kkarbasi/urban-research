"""Address → FIPS codes via the Census Geocoder.

The Census Geocoder is a free public service with no API key required.
It returns all the geographic identifiers we need in a single call:
state FIPS, county FIPS, place FIPS, CBSA code, census tract GEOID,
plus the matched address and coordinates.
"""

from __future__ import annotations

import logging
import time

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

GEOCODER_URL = (
    "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
)
TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAY = 1.5
USER_AGENT = "cityscope/0.2.0"


class GeocodingResult(BaseModel):
    """Structured result from the Census Geocoder."""

    address: str  # original input
    matched_address: str
    latitude: float
    longitude: float

    # FIPS / geographic identifiers (all optional — not every address hits every layer)
    state_fips: str | None = None
    county_fips: str | None = None  # 3-digit county code (within state)
    county_geo_id: str | None = None  # 5-digit state+county FIPS
    place_fips: str | None = None  # 5-digit place code (within state)
    place_geo_id: str | None = None  # 7-digit state+place (matches cityscope city geo_id)
    cbsa_code: str | None = None  # 5-digit CBSA (matches cityscope metro geo_id)
    tract_geoid: str | None = None  # 11-digit state+county+tract


class GeocodingError(Exception):
    """Raised when an address cannot be geocoded."""


def _api_get(params: dict[str, str]) -> dict:
    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(
                timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}
            ) as client:
                resp = client.get(GEOCODER_URL, params=params)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code >= 500:
                    logger.warning(
                        "Geocoder %d, retry %d/%d",
                        resp.status_code, attempt + 1, MAX_RETRIES,
                    )
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException:
            logger.warning("Geocoder timeout, retry %d/%d", attempt + 1, MAX_RETRIES)
            time.sleep(RETRY_DELAY * (attempt + 1))
    raise GeocodingError(f"Census Geocoder failed after {MAX_RETRIES} retries")


def geocode_address(address: str) -> GeocodingResult:
    """Look up FIPS codes for a US address using the Census Geocoder.

    Raises GeocodingError if the address cannot be matched.
    """
    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json",
        "layers": "all",
    }

    data = _api_get(params)
    matches = data.get("result", {}).get("addressMatches", [])
    if not matches:
        raise GeocodingError(f"No match found for address: {address!r}")

    return _parse_match(address, matches[0])


def _parse_match(original_address: str, match: dict) -> GeocodingResult:
    coords = match.get("coordinates", {})
    geos = match.get("geographies", {})

    def first(layer: str) -> dict:
        entries = geos.get(layer, [])
        return entries[0] if entries else {}

    state = first("States")
    county = first("Counties")
    place = first("Incorporated Places")
    cbsa = first("Metropolitan Statistical Areas")
    tract = first("Census Tracts")

    state_fips = state.get("STATE") or None
    county_fips = county.get("COUNTY") or None
    county_geo_id = county.get("GEOID") or None  # 5-digit state+county
    place_fips = place.get("PLACE") or None
    # Build 7-digit state+place to match cityscope's city geo_id convention
    place_geo_id = None
    if state_fips and place_fips:
        place_geo_id = f"{state_fips}{place_fips}"
    cbsa_code = cbsa.get("CBSA") or cbsa.get("GEOID") or None
    tract_geoid = tract.get("GEOID") or None

    return GeocodingResult(
        address=original_address,
        matched_address=match.get("matchedAddress", ""),
        latitude=float(coords.get("y", 0.0)),
        longitude=float(coords.get("x", 0.0)),
        state_fips=state_fips,
        county_fips=county_fips,
        county_geo_id=county_geo_id,
        place_fips=place_fips,
        place_geo_id=place_geo_id,
        cbsa_code=cbsa_code,
        tract_geoid=tract_geoid,
    )
