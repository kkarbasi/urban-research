from __future__ import annotations

from abc import ABC, abstractmethod

from .config import Config
from .models import FetchResult, GeoType


class DataSource(ABC):
    source_id: str
    name: str
    description: str

    # Geo types this source can fetch on-demand via fetch_for_geo().
    # Sources that support targeted single-geo lookups (e.g., for address lookup)
    # should override this.
    supported_geo_types_for_lookup: list[GeoType] = []

    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def fetch(self, **kwargs) -> FetchResult: ...

    def fetch_for_geo(self, geo_id: str, geo_type: GeoType) -> FetchResult:
        """Fetch data for a single geography (fallback path for address lookup).

        Default implementation raises NotImplementedError. Sources that want to
        support single-geo enrichment should override this and list the
        supported types in `supported_geo_types_for_lookup`.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support fetch_for_geo"
        )
