from .base_state_lookup import BaseStateLookup

class HawaiiLookup(BaseStateLookup):
    STATE_CODE = 'HI'
    STATE_NAME = 'Hawaii'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Hawaii',
            'cities': ['honolulu', 'hilo', 'kailua-kona', 'kahului', 'lihue', 'pearl city', 'kailua', 'kaneohe']
        }
    }