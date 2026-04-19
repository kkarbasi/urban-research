from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config
    from .source import DataSource


class SourceRegistry:
    _sources: dict[str, type[DataSource]] = {}

    @classmethod
    def register(cls, source_class: type[DataSource]) -> type[DataSource]:
        cls._sources[source_class.source_id] = source_class
        return source_class

    @classmethod
    def get(cls, source_id: str, config: Config) -> DataSource:
        if source_id not in cls._sources:
            available = ", ".join(cls._sources) or "(none)"
            raise KeyError(f"Unknown source '{source_id}'. Available: {available}")
        return cls._sources[source_id](config)

    @classmethod
    def get_all(cls, config: Config) -> list[DataSource]:
        return [src_cls(config) for src_cls in cls._sources.values()]

    @classmethod
    def list_ids(cls) -> list[str]:
        return list(cls._sources.keys())
