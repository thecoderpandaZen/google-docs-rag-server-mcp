"""Base extractor interface."""

from abc import ABC, abstractmethod
from typing import Optional


class Extractor(ABC):
    @abstractmethod
    def extract(self, file_id: str, mime_type: str) -> Optional[str]:
        pass
