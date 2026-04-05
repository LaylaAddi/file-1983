from .base_state_lookup import BaseStateLookup

class SouthDakotaLookup(BaseStateLookup):
    STATE_CODE = 'SD'
    STATE_NAME = 'South Dakota'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of South Dakota',
            'cities': ['sioux falls', 'rapid city', 'aberdeen', 'brookings', 'watertown', 'mitchell', 'yankton', 'pierre']
        }
    }