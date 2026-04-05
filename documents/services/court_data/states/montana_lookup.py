from .base_state_lookup import BaseStateLookup

class MontanaLookup(BaseStateLookup):
    STATE_CODE = 'MT'
    STATE_NAME = 'Montana'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Montana',
            'cities': ['billings', 'missoula', 'great falls', 'bozeman', 'butte', 'helena', 'kalispell', 'havre']
        }
    }