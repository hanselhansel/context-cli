"""Base parser interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from aeo_cli.core.models import ProductData


class BaseParser(ABC):
    """Abstract base class for marketplace parsers."""

    @abstractmethod
    def parse(self, html: str) -> ProductData:
        """Parse HTML content into structured product data."""
        ...
