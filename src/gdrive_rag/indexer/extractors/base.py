"""Base extractor interface."""

from abc import ABC, abstractmethod


class Extractor(ABC):
    @abstractmethod
    def extract(self, file_id: str, mime_type: str) -> str | None:
        pass
