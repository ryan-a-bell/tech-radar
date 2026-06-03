"""
scrapers/base.py — abstract base class for all tech radar scrapers.
"""

from abc import ABC, abstractmethod


class Scraper(ABC):
    name: str = ""  # short identifier used in item ids and log output

    @abstractmethod
    def discover(self) -> list:
        """Return a list of new_item() dicts found by this source."""
