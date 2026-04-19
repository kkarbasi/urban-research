from __future__ import annotations

from abc import ABC, abstractmethod

from .config import Config
from .models import FetchResult


class DataSource(ABC):
    source_id: str
    name: str
    description: str

    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def fetch(self, **kwargs) -> FetchResult: ...
