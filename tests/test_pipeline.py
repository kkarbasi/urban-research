"""Tests for the pipeline runner."""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from urban_research.core.config import Config
from urban_research.core.models import DataPoint, DatasetMetadata, FetchResult, Geography, GeoType
from urban_research.pipeline.runner import Pipeline


class TestPipeline:
    def test_run_stores_results(self, config, storage, sample_geographies, sample_data_points):
        result = FetchResult(
            geographies=sample_geographies,
            data_points=sample_data_points,
            metadata=DatasetMetadata(
                source_id="test_source",
                name="Test",
                description="Test source",
                metrics=["population"],
                geo_types=[GeoType.METRO],
                min_year=2022,
                max_year=2024,
                record_count=len(sample_data_points),
            ),
        )

        mock_source = MagicMock()
        mock_source.fetch.return_value = result

        with patch("urban_research.pipeline.runner.SourceRegistry") as mock_registry:
            mock_registry.get.return_value = mock_source

            pipeline = Pipeline(config)
            results = pipeline.run(["test_source"])

        assert "test_source" in results
        assert results["test_source"].metadata.record_count == len(sample_data_points)

        # Verify data was stored
        geos = storage.get_geographies()
        assert len(geos) == 5

        data = storage.query_data(metric="population")
        assert len(data) > 0

    def test_run_all_sources(self, config):
        with patch("urban_research.pipeline.runner.SourceRegistry") as mock_registry:
            mock_registry.list_ids.return_value = ["source_a", "source_b"]

            mock_source = MagicMock()
            mock_source.fetch.return_value = FetchResult(
                geographies=[],
                data_points=[],
                metadata=DatasetMetadata(
                    source_id="mock", name="Mock", description="",
                    metrics=[], geo_types=[], min_year=0, max_year=0,
                ),
            )
            mock_registry.get.return_value = mock_source

            pipeline = Pipeline(config)
            results = pipeline.run(None)  # None means all

        assert mock_registry.list_ids.called
        assert mock_registry.get.call_count == 2
