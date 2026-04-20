"""Tests for BLS employment source."""

import pytest

from cityscope.core.config import Config
from cityscope.sources.bls_employment import (
    BLSEmploymentSource,
    _cbsa_to_qcew_fips,
    _parse_principal_state_fips,
    _qcew_fips_to_cbsa,
)


class TestQCEWFipsConversion:
    def test_cbsa_to_qcew(self):
        assert _cbsa_to_qcew_fips("31080") == "C3108"
        assert _cbsa_to_qcew_fips("35620") == "C3562"
        assert _cbsa_to_qcew_fips("10180") == "C1018"

    def test_qcew_to_cbsa(self):
        assert _qcew_fips_to_cbsa("C3108") == "31080"
        assert _qcew_fips_to_cbsa("C3562") == "35620"
        assert _qcew_fips_to_cbsa("C1018") == "10180"

    def test_roundtrip(self):
        cbsa = "47900"
        assert _qcew_fips_to_cbsa(_cbsa_to_qcew_fips(cbsa)) == cbsa


class TestParseStateFips:
    def test_simple_metros(self):
        assert _parse_principal_state_fips("Austin-Round Rock-Georgetown, TX Metro Area") == "48"
        assert _parse_principal_state_fips("Phoenix-Mesa-Chandler, AZ Metro Area") == "04"
        assert _parse_principal_state_fips("Miami-Fort Lauderdale-Pompano Beach, FL Metro Area") == "12"

    def test_multi_state(self):
        assert _parse_principal_state_fips("New York-Newark-Jersey City, NY-NJ-PA Metro Area") == "36"
        assert _parse_principal_state_fips("Chicago-Naperville-Elgin, IL-IN-WI Metro Area") == "17"

    def test_dc(self):
        assert _parse_principal_state_fips("Washington-Arlington-Alexandria, DC-VA-MD-WV Metro Area") == "11"

    def test_puerto_rico(self):
        assert _parse_principal_state_fips("San Juan-Bayamón-Caguas, PR Metro Area") == "72"

    def test_no_state(self):
        assert _parse_principal_state_fips("Some Random String") is None
        assert _parse_principal_state_fips("") is None


class TestBLSEmploymentSource:
    def test_has_correct_metadata(self, config):
        source = BLSEmploymentSource(config)
        assert source.source_id == "bls_employment"

    def test_raises_without_metros(self, config):
        source = BLSEmploymentSource(config)
        with pytest.raises(RuntimeError, match="No metros in database"):
            source.fetch()
