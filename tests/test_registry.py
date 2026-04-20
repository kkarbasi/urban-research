"""Tests for source registry."""

from urban_research.core.config import Config
from urban_research.core.registry import SourceRegistry

import urban_research.sources  # noqa: F401


class TestSourceRegistry:
    def test_census_registered(self):
        assert "census_population" in SourceRegistry.list_ids()

    def test_bls_registered(self):
        assert "bls_employment" in SourceRegistry.list_ids()

    def test_get_source(self, config):
        source = SourceRegistry.get("census_population", config)
        assert source.source_id == "census_population"
        assert source.name == "Census Bureau Population Estimates"

    def test_get_unknown_raises(self, config):
        import pytest
        with pytest.raises(KeyError, match="Unknown source"):
            SourceRegistry.get("nonexistent", config)

    def test_get_all(self, config):
        sources = SourceRegistry.get_all(config)
        assert len(sources) >= 2
        ids = {s.source_id for s in sources}
        assert "census_population" in ids
        assert "bls_employment" in ids
