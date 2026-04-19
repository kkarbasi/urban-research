from __future__ import annotations

import logging

from ..core.config import Config
from ..core.models import FetchResult
from ..core.registry import SourceRegistry
from ..core.storage import Storage

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, config: Config):
        self.config = config
        self.storage = Storage(config.storage.db_path)

    def run(
        self,
        source_ids: list[str] | None = None,
        **kwargs,
    ) -> dict[str, FetchResult]:
        if source_ids is None:
            source_ids = SourceRegistry.list_ids()

        results: dict[str, FetchResult] = {}

        for source_id in source_ids:
            logger.info("Running source: %s", source_id)
            source = SourceRegistry.get(source_id, self.config)
            result = source.fetch(**kwargs)

            geo_count = self.storage.upsert_geographies(result.geographies)
            dp_count = self.storage.upsert_data_points(result.data_points)
            logger.info("Stored %d geographies, %d data points", geo_count, dp_count)

            results[source_id] = result

        return results
