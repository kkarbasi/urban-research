"""Tests for the Census Geocoder wrapper."""

from unittest.mock import patch

import pytest

from cityscope.geocoding import (
    GeocodingError,
    GeocodingResult,
    _parse_match,
    geocode_address,
)

# ---------------------------------------------------------------------------
# Sample geocoder responses
# ---------------------------------------------------------------------------

FULL_MATCH_RESPONSE = {
    "result": {
        "addressMatches": [{
            "matchedAddress": "1600 AMPHITHEATRE PKWY, MOUNTAIN VIEW, CA, 94043",
            "coordinates": {"x": -122.083521, "y": 37.423120},
            "geographies": {
                "States": [{"STATE": "06", "GEOID": "06", "NAME": "California"}],
                "Counties": [{
                    "STATE": "06", "COUNTY": "085", "GEOID": "06085",
                    "NAME": "Santa Clara County",
                }],
                "Incorporated Places": [{
                    "STATE": "06", "PLACE": "49670", "GEOID": "0649670",
                    "NAME": "Mountain View city",
                }],
                "Metropolitan Statistical Areas": [{
                    "CBSA": "41940", "GEOID": "41940",
                    "NAME": "San Jose-Sunnyvale-Santa Clara, CA Metro Area",
                }],
                "Census Tracts": [{
                    "STATE": "06", "COUNTY": "085", "TRACT": "504601",
                    "GEOID": "06085504601",
                }],
            },
        }]
    }
}


RURAL_RESPONSE = {
    "result": {
        "addressMatches": [{
            "matchedAddress": "RURAL RT, SMALLTOWN, NM, 87827",
            "coordinates": {"x": -107.0, "y": 34.0},
            "geographies": {
                "States": [{"STATE": "35", "GEOID": "35"}],
                "Counties": [{"STATE": "35", "COUNTY": "051", "GEOID": "35051"}],
                # No incorporated place, no metro
            },
        }]
    }
}


NO_MATCH_RESPONSE = {"result": {"addressMatches": []}}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseMatch:
    def test_full_match(self):
        match = FULL_MATCH_RESPONSE["result"]["addressMatches"][0]
        result = _parse_match("test address", match)

        assert result.matched_address == "1600 AMPHITHEATRE PKWY, MOUNTAIN VIEW, CA, 94043"
        assert result.latitude == pytest.approx(37.423120)
        assert result.longitude == pytest.approx(-122.083521)
        assert result.state_fips == "06"
        assert result.county_fips == "085"
        assert result.county_geo_id == "06085"
        assert result.place_fips == "49670"
        assert result.place_geo_id == "0649670"
        assert result.cbsa_code == "41940"
        assert result.tract_geoid == "06085504601"

    def test_rural_match_no_place_no_metro(self):
        match = RURAL_RESPONSE["result"]["addressMatches"][0]
        result = _parse_match("rural address", match)

        assert result.state_fips == "35"
        assert result.county_geo_id == "35051"
        assert result.place_geo_id is None
        assert result.cbsa_code is None

    def test_place_geo_id_construction(self):
        """Verify that place_geo_id is state_fips + place_fips (7 digits)."""
        match = FULL_MATCH_RESPONSE["result"]["addressMatches"][0]
        result = _parse_match("test", match)
        assert result.place_geo_id == result.state_fips + result.place_fips
        assert len(result.place_geo_id) == 7


class TestGeocodeAddress:
    def test_full_match(self):
        with patch("cityscope.geocoding._api_get", return_value=FULL_MATCH_RESPONSE):
            result = geocode_address("1600 Amphitheatre Pkwy, Mountain View, CA")
        assert isinstance(result, GeocodingResult)
        assert result.address == "1600 Amphitheatre Pkwy, Mountain View, CA"
        assert result.cbsa_code == "41940"

    def test_no_match_raises(self):
        with patch("cityscope.geocoding._api_get", return_value=NO_MATCH_RESPONSE):
            with pytest.raises(GeocodingError, match="No match found"):
                geocode_address("Fake address")

    def test_rural_returns_partial(self):
        with patch("cityscope.geocoding._api_get", return_value=RURAL_RESPONSE):
            result = geocode_address("rural")
        assert result.state_fips == "35"
        assert result.cbsa_code is None
        assert result.place_geo_id is None
