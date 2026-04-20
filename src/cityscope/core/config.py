from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class CensusConfig(BaseModel):
    api_key: str | None = None


class BLSConfig(BaseModel):
    api_key: str | None = None


class StorageConfig(BaseModel):
    db_path: str = "data/cityscope.db"


class PipelineConfig(BaseModel):
    min_population: int = 200_000
    default_vintage: int | None = None


class Config(BaseModel):
    census: CensusConfig = CensusConfig()
    bls: BLSConfig = BLSConfig()
    storage: StorageConfig = StorageConfig()
    pipeline: PipelineConfig = PipelineConfig()

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        if path and path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return cls.model_validate(data)
        return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)
