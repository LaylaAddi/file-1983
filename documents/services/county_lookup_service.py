import json
import re
from functools import lru_cache
from pathlib import Path

_CITY_DATA_PATH = Path(__file__).resolve().parent / 'county_data' / 'us_city_county.json'
_ZIP_DATA_PATH = Path(__file__).resolve().parent / 'county_data' / 'us_zip_county.json'


@lru_cache(maxsize=1)
def _load_city_data():
    with open(_CITY_DATA_PATH) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_zip_data():
    with open(_ZIP_DATA_PATH) as f:
        return json.load(f)


class CountyLookupService:
    """
    Static county lookup, backed by two bundled public datasets:

    - city+state -> county (~29.7k incorporated US cities, MIT-licensed,
      github.com/kelvins/US-Cities-Database)
    - ZIP -> county (~33k ZCTAs derived from US Census data,
      github.com/scpike/us-state-county-zip)

    This exists because GPT's county guess from the story text alone has
    no real data behind it and is unreliable, especially for small or
    unincorporated places. ZIP is checked first when available since it
    also covers unincorporated communities (e.g. Van Wert, GA, ZIP 30153)
    that the incorporated-city dataset misses; city+state is the fallback
    for when no ZIP was given. The court lookup already does this same
    static-data-first pattern (see CourtLookupService); this mirrors it
    for county.
    """

    @classmethod
    def lookup_county(cls, city=None, state=None, zip_code=None):
        """Return the county name for a location, or None if not found."""
        if zip_code:
            county = cls._lookup_by_zip(zip_code, state)
            if county:
                return county

        if city and state:
            return cls._lookup_by_city(city, state)

        return None

    @classmethod
    def _lookup_by_zip(cls, zip_code, state=None):
        digits = re.sub(r'\D', '', zip_code or '')[:5]
        if len(digits) != 5:
            return None

        entry = _load_zip_data().get(digits)
        if not entry:
            return None

        # Guard against a typo'd ZIP that happens to exist but is in a
        # different state than the one the user selected.
        if state and entry.get('state') != state.strip().upper():
            return None

        return entry.get('county')

    @classmethod
    def _lookup_by_city(cls, city, state):
        state_data = _load_city_data().get(state.strip().upper())
        if not state_data:
            return None

        return state_data.get(city.strip().lower())
