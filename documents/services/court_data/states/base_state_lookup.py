class BaseStateLookup:
    """Base class for state-specific federal district court lookups."""

    STATE_CODE = None
    STATE_NAME = None
    DISTRICTS = {}
    IS_SINGLE_DISTRICT = False  # Override to True for single-district states

    @classmethod
    def lookup_court_by_city(cls, city):
        """Look up federal district court by city name."""
        if not city or not cls.DISTRICTS:
            return None

        city = city.strip().lower()

        # Check each district for exact city match
        for district_key, district_info in cls.DISTRICTS.items():
            if city in district_info.get('cities', []):
                return {
                    'court_name': district_info['name'],
                    'confidence': 'high',
                    'method': 'city_match',
                    'district': district_key,
                    'state': cls.STATE_CODE
                }

        # For single-district states, return the only court with medium confidence
        # since any city in the state goes to the same court
        if cls.IS_SINGLE_DISTRICT and len(cls.DISTRICTS) == 1:
            district_info = list(cls.DISTRICTS.values())[0]
            return {
                'court_name': district_info['name'],
                'confidence': 'medium',
                'method': 'single_district_state',
                'state': cls.STATE_CODE,
                'note': f'{cls.STATE_NAME} has only one federal district court for the entire state.'
            }

        return None