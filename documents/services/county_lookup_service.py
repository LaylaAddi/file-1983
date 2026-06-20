import json
from functools import lru_cache
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent / 'county_data' / 'us_city_county.json'


@lru_cache(maxsize=1)
def _load_data():
    with open(_DATA_PATH) as f:
        return json.load(f)


class CountyLookupService:
    """
    Static city+state -> county lookup, backed by a bundled dataset of
    ~29.7k US cities (MIT-licensed, github.com/kelvins/US-Cities-Database).

    This exists because GPT's county guess from the story text alone is
    unreliable for small/obscure towns — there's no real data behind it.
    The court lookup already does this same static-data-first pattern
    (see CourtLookupService); this mirrors it for county.
    """

    @classmethod
    def lookup_county(cls, city, state):
        """Return the county name for a city/state, or None if not found."""
        if not city or not state:
            return None

        data = _load_data()
        state_data = data.get(state.strip().upper())
        if not state_data:
            return None

        return state_data.get(city.strip().lower())
