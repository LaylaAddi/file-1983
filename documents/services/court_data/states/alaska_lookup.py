from .base_state_lookup import BaseStateLookup

class AlaskaLookup(BaseStateLookup):
    """Federal district court lookup for Alaska state."""

    STATE_CODE = 'AK'
    STATE_NAME = 'Alaska'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Alaska',
            'cities': [
                'anchorage', 'fairbanks', 'juneau', 'wasilla', 'sitka',
                'ketchikan', 'kenai', 'kodiak', 'bethel', 'nome'
            ]
        }
    }